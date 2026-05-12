"""
NxSMS Rotator - Self-Learning SMS API Key Aggregator
=====================================================

Key features:
- Multi-key SMS API rotation (TextBelt, SeaSMS, WiFi Text, etc.)
- SQLite learning from outcomes
- Auto-failover on quota limits
- Per-key health tracking with cooldown
- Circuit breaker pattern per key

Usage:
    from nx_sms import NxSMS

    sms = NxSMS()

    # Send SMS (auto-rotates keys)
    result = sms.send("+15551234567", "Hello from NxSMS!")

    if result.success:
        print("SMS sent!")
    else:
        print(f"Error: {result.error}")
"""

import json
import os
import sys
import time
import threading
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ============================================================
# Configuration
# ============================================================

_PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = _PROJECT_ROOT / "configs" / "nx_sms"
KEYS_FILE = CONFIG_DIR / "keys.json"

DB_FILE = CONFIG_DIR / "nx_sms_learning.db"
METRICS_FILE = CONFIG_DIR / "nx_sms_metrics.json"

_lock = threading.Lock()

# Default SMS services
DEFAULT_SERVICES = {
    "email2sms": {
        "name": "Email to SMS",
        "url": "smtp",
        "param_key": "smtp",
        "param_number": "to",
        "param_message": "body",
        "quota_field": "N/A",
        "error_field": "error",
        "success_field": "success",
        "free_limit": -1,  # Depends on email provider
    },
    "textbelt": {
        "name": "TextBelt",
        "url": "https://textbelt.com/text",
        "param_key": "key",
        "param_number": "number",
        "param_message": "message",
        "quota_field": "quotaRemaining",
        "error_field": "error",
        "success_field": "success",
        "free_key": "textbelt",  # Default free key
        "free_limit": 1,  # 1/day
    },
    "seasms": {
        "name": "SeaSMS",
        "url": "https://api.seasms.com/send",
        "param_key": "apikey",
        "param_number": "to",
        "param_message": "message",
        "quota_field": "credits",
        "error_field": "error",
        "success_field": "status",
        "free_limit": 100,  # 100/new account
    },
    "wifitext": {
        "name": "WiFi Text",
        "url": "https://api.wifitext.com/api/send",
        "param_key": "api_key",
        "param_number": "number",
        "param_message": "message",
        "quota_field": "credits",
        "error_field": "error",
        "success_field": "status",
        "free_limit": -1,  # Daily reload
    },
    "smsmode": {
        "name": "SMSMode",
        "url": "https://api.smsmode.com/sms/send",
        "param_key": "apiKey",
        "param_number": "to",
        "param_message": "message",
        "quota_field": "credits",
        "error_field": "error",
        "success_field": "success",
        "free_limit": 20,  # 20/new account
    },
    "smsto": {
        "name": "SMS.to",
        "url": "https://api.sms.to/v1/sms/send",
        "param_key": "api_key",
        "param_number": "recipient",
        "param_message": "message",
        "quota_field": "credits",
        "error_field": "error",
        "success_field": "status",
    },
    "textlocal": {
        "name": "TextLocal",
        "url": "https://api.textlocal.in/sendsms",
        "param_key": "apikey",
        "param_number": "numbers",
        "param_message": "message",
        "quota_field": "balance",
        "error_field": "errors",
        "success_field": "success",
    },
}

DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_TIMEOUT = 60

# ============================================================
# Data Models
# ============================================================


@dataclass
class CircuitBreaker:
    """Circuit breaker for each SMS key."""
    failures: int = 0
    state: str = "closed"
    opened_at: float = 0.0
    last_failure: float = 0.0

    def should_allow(self) -> bool:
        now = time.time()
        if self.state == "closed":
            return True
        if self.state == "open":
            if now - self.opened_at > CIRCUIT_BREAKER_TIMEOUT:
                self.state = "half-open"
                return True
            return False
        return True

    def record_success(self) -> None:
        self.failures = 0
        self.state = "closed"

    def record_failure(self) -> None:
        self.failures += 1
        self.last_failure = time.time()
        if self.failures >= CIRCUIT_BREAKER_THRESHOLD:
            self.state = "open"
            self.opened_at = time.time()


@dataclass
class SMSResult:
    """Result from SMS send attempt."""
    success: bool
    service: str = ""
    key_used: str = ""
    message: str = ""
    quota_remaining: int = -1
    error: str = ""
    latency_ms: int = 0


# ============================================================
# Database
# ============================================================


def init_db() -> None:
    """Initialize learning database."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Outcomes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service TEXT NOT NULL,
            key_hash TEXT NOT NULL,
            success INTEGER NOT NULL,
            error TEXT,
            latency_ms INTEGER,
            quota_remaining INTEGER,
            timestamp REAL NOT NULL
        )
    """)

    # Key performance table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS key_performance (
            service TEXT PRIMARY KEY,
            total_requests INTEGER DEFAULT 0,
            successful_requests INTEGER DEFAULT 0,
            failed_requests INTEGER DEFAULT 0,
            avg_latency_ms REAL DEFAULT 0,
            last_used REAL DEFAULT 0,
            success_rate REAL DEFAULT 1.0
        )
    """)

    conn.commit()
    conn.close()


def record_outcome(
    service: str,
    key_hash: str,
    success: bool,
    error: str = "",
    latency_ms: int = 0,
    quota_remaining: int = -1,
) -> None:
    with _lock:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Record outcome
        cursor.execute(
            """INSERT INTO outcomes 
               (service, key_hash, success, error, latency_ms, quota_remaining, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (service, key_hash, 1 if success else 0, error, latency_ms, quota_remaining, time.time())
        )

        # Update key performance
        if success:
            cursor.execute(
                """INSERT OR REPLACE INTO key_performance 
                   (service, total_requests, successful_requests, last_used)
                   VALUES (?, 1, 1, ?)
                   ON CONFLICT(service) DO UPDATE SET
                   total_requests = total_requests + 1,
                   successful_requests = successful_requests + 1,
                   last_used = excluded.last_used""",
                (service, time.time())
            )
        else:
            cursor.execute(
                """INSERT OR REPLACE INTO key_performance 
                   (service, total_requests, failed_requests)
                   VALUES (?, 1, 1)
                   ON CONFLICT(service) DO UPDATE SET
                   total_requests = total_requests + 1,
                   failed_requests = failed_requests + 1""",
                (service,)
            )

        conn.commit()
        conn.close()


def get_key_stats(service: str) -> Dict:
    """Get performance stats for a service."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """SELECT total_requests, successful_requests, failed_requests, avg_latency_ms, success_rate
           FROM key_performance WHERE service = ?""",
        (service,)
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "total_requests": row[0],
            "successful_requests": row[1],
            "failed_requests": row[2],
            "avg_latency_ms": row[3],
            "success_rate": row[4] if row[4] is not None else 1.0,
        }
    # Default to 1.0 - allow new services by default
    return {
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "avg_latency_ms": 0,
        "success_rate": 1.0,
    }


# ============================================================
# Main Rotator
# ============================================================


class NxSMS:
    """
    SMS API Key Rotator with self-learning.
    """

    def __init__(self):
        self.config = self._load_config()
        self.keys: Dict[str, str] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.stats: Dict[str, Dict] = {}

        # Initialize
        init_db()
        self._load_keys()

    def _load_config(self) -> Dict:
        """Load configuration."""
        if KEYS_FILE.exists():
            with open(KEYS_FILE) as f:
                return json.load(f)
        return {"services": {}}

    def _load_keys(self) -> None:
        """Load API keys from config."""
        config = self.config

        # Load from keys file
        if KEYS_FILE.exists():
            with open(KEYS_FILE) as f:
                data = json.load(f)
                for service, key_data in data.items():
                    if isinstance(key_data, dict):
                        self.keys[service] = key_data.get("api_key", "")
                    elif isinstance(key_data, str):
                        self.keys[service] = key_data

        # Initialize circuit breakers
        for service in list(self.keys.keys()) + list(DEFAULT_SERVICES.keys()):
            if service not in self.circuit_breakers:
                self.circuit_breakers[service] = CircuitBreaker()
            if service not in self.stats:
                self.stats[service] = get_key_stats(service)

    def add_key(self, service: str, api_key: str) -> bool:
        """Add/update an API key for a service."""
        with _lock:
            self.keys[service] = api_key

            # Save to keys file
            if not KEYS_FILE.exists():
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                KEYS_FILE.touch()

            # Update config
            if "services" not in self.config:
                self.config["services"] = {}

            if isinstance(self.config["services"], dict):
                self.config["services"][service] = {"api_key": api_key}
            else:
                self.config["services"][service] = api_key

            # Initialize circuit breaker
            self.circuit_breakers[service] = CircuitBreaker()
            self.stats[service] = get_key_stats(service)

            with open(KEYS_FILE, "w") as f:
                json.dump(self.config["services"], f, indent=2)

        print(f"[NxSMS] Added key for {service}")
        return True

    def get_available_keys(self) -> List[str]:
        """Get list of available services that can be used."""
        available = []

        for service in list(self.keys.keys()) + list(DEFAULT_SERVICES.keys()):
            cb = self.circuit_breakers.get(service, CircuitBreaker())

            # Skip if circuit breaker is open
            if not cb.should_allow():
                continue

            # Skip if we know quota is exhausted - but allow new services with no data
            stats = self.stats.get(service, {})
            success_rate = stats.get("success_rate", 1.0)  # Default to 1.0 for new services
            if success_rate < 0.3:  # Less than 30% success rate
                continue

            available.append(service)

        return available

    def _send_email2sms(self, phone: str, message: str) -> SMSResult:
        """Send SMS via email-to-SMS gateway."""
        import smtplib
        from email.message import EmailMessage

        config = self.config.get("email2sms", {})
        smtp_host = config.get("smtp_host", "smtp.gmail.com")
        smtp_port = config.get("smtp_port", 587)
        email_addr = config.get("email")
        email_pass = config.get("password")
        carrier_gateway = config.get("carrier_gateway", "vtext.com")

        if not email_addr or not email_pass:
            return SMSResult(success=False, service="email2sms", error="Email credentials not configured. Use add-key email2sms with JSON config.")

        try:
            start_time = time.time()
            to_addr = f"{phone}{carrier_gateway}"

            msg = EmailMessage()
            msg["From"] = email_addr
            msg["To"] = to_addr
            msg.set_content(message)

            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            server.login(email_addr, email_pass)
            server.send_message(msg)
            server.quit()

            latency_ms = int((time.time() - start_time) * 1000)
            key_hash = hashlib.md5(email_addr.encode()).hexdigest()[:8]
            record_outcome("email2sms", key_hash, True, "", latency_ms)

            return SMSResult(success=True, service="email2sms", message=message, latency_ms=latency_ms)

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            key_hash = hashlib.md5(email_addr.encode()).hexdigest()[:8]
            record_outcome("email2sms", key_hash, False, error_msg, latency_ms)
            return SMSResult(success=False, service="email2sms", error=error_msg, latency_ms=latency_ms)

    def _send_sms(self, service: str, phone: str, message: str) -> SMSResult:
        """Send SMS via a specific service."""
        svc = DEFAULT_SERVICES.get(service)
        if not svc:
            return SMSResult(success=False, service=service, error=f"Unknown service: {service}")

        # Email to SMS special handling
        if service == "email2sms":
            return self._send_email2sms(phone, message)

        # Get API key
        api_key = self.keys.get(service, svc.get("free_key", ""))

        if not api_key:
            return SMSResult(success=False, service=service, error=f"No API key for {service}")

        start_time = time.time()

        # Prepare request
        data = {
            svc["param_key"]: api_key,
            svc["param_number"]: phone,
            svc["param_message"]: message,
        }

        # Debug: log request info (mask API key)
        debug_data = data.copy()
        debug_data[svc["param_key"]] = api_key[:8] + "***" if api_key else "***"
        print(f"[NxSMS DEBUG] POST {svc['url']}")
        print(f"[NxSMS DEBUG] Service: {service} ({svc['name']})")
        print(f"[NxSMS DEBUG] Data (key masked): {debug_data}")

        try:
            response = requests.post(svc["url"], data=data, timeout=DEFAULT_TIMEOUT)
            latency_ms = int((time.time() - start_time) * 1000)

            print(f"[NxSMS DEBUG] Response status: {response.status_code}")
            print(f"[NxSMS DEBUG] Response headers: {dict(response.headers)}")

            try:
                result_data = response.json()
            except ValueError:
                # Non-JSON response
                response_text = response.text
                print(f"[NxSMS ERROR] Non-JSON response: {response_text}")
                self.circuit_breakers[service].record_failure()
                key_hash = hashlib.md5(api_key.encode()).hexdigest()[:8]
                record_outcome(service, key_hash, False, f"Non-JSON response: {response_text[:200]}", latency_ms)
                return SMSResult(success=False, service=service, 
                              error=f"Non-JSON response: {response_text[:200]}",
                              key_used=api_key[:8] + "***", latency_ms=latency_ms)

            print(f"[NxSMS DEBUG] Response JSON: {result_data}")

            # Check for errors
            if svc["error_field"] in result_data:
                error = result_data[svc["error_field"]]
                if error:
                    # Handle different error field types (string, list, dict)
                    if isinstance(error, list):
                        error_msg = "; ".join(str(e) for e in error)
                    elif isinstance(error, dict):
                        error_msg = str(error)
                    else:
                        error_msg = str(error)
                    
                    print(f"[NxSMS ERROR] Service {service} error field '{svc['error_field']}': {error_msg}")
                    print(f"[NxSMS ERROR] Full response: {result_data}")
                    
                    self.circuit_breakers[service].record_failure()
                    key_hash = hashlib.md5(api_key.encode()).hexdigest()[:8]
                    record_outcome(service, key_hash, False, error_msg, latency_ms)
                    return SMSResult(success=False, service=service, error=error_msg,
                                  key_used=api_key[:8] + "***", latency_ms=latency_ms)

            # Check success field if present
            if svc.get("success_field") and svc["success_field"] in result_data:
                success_value = result_data[svc["success_field"]]
                # Handle different success field types
                is_success = False
                if isinstance(success_value, bool):
                    is_success = success_value
                elif isinstance(success_value, str):
                    is_success = success_value.lower() in ('true', 'success', 'ok', '1', 'yes')
                elif isinstance(success_value, (int, float)):
                    is_success = success_value > 0
                
                if not is_success:
                    error_msg = f"Service reported failure. Success field '{svc['success_field']}': {success_value}"
                    print(f"[NxSMS ERROR] {error_msg}")
                    print(f"[NxSMS ERROR] Full response: {result_data}")
                    self.circuit_breakers[service].record_failure()
                    key_hash = hashlib.md5(api_key.encode()).hexdigest()[:8]
                    record_outcome(service, key_hash, False, error_msg, latency_ms)
                    return SMSResult(success=False, service=service, error=error_msg,
                                  key_used=api_key[:8] + "***", latency_ms=latency_ms)

            # Get quota
            quota = result_data.get(svc["quota_field"], -1)

            # Record success
            self.circuit_breakers[service].record_success()
            key_hash = hashlib.md5(api_key.encode()).hexdigest()[:8]
            record_outcome(service, key_hash, True, "", latency_ms, quota)

            print(f"[NxSMS DEBUG] SMS sent successfully via {service}. Quota remaining: {quota}")

            return SMSResult(
                success=True,
                service=service,
                key_used=api_key[:8] + "***",
                message=message,
                quota_remaining=quota,
                latency_ms=latency_ms,
            )

        except requests.exceptions.Timeout:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Request timeout after {DEFAULT_TIMEOUT}s"
            print(f"[NxSMS ERROR] {error_msg}")
            self.circuit_breakers[service].record_failure()
            key_hash = hashlib.md5(api_key.encode()).hexdigest()[:8]
            record_outcome(service, key_hash, False, error_msg, latency_ms)
            return SMSResult(success=False, service=service, error=error_msg, latency_ms=latency_ms)

        except requests.exceptions.RequestException as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Request failed: {str(e)}"
            print(f"[NxSMS ERROR] {error_msg}")
            # Print response if available
            if hasattr(e, 'response') and e.response is not None:
                print(f"[NxSMS ERROR] Response status: {e.response.status_code}")
                print(f"[NxSMS ERROR] Response body: {e.response.text[:500]}")
            self.circuit_breakers[service].record_failure()
            key_hash = hashlib.md5(api_key.encode()).hexdigest()[:8]
            record_outcome(service, key_hash, False, error_msg, latency_ms)
            return SMSResult(success=False, service=service, error=error_msg, latency_ms=latency_ms)

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Unexpected error: {str(e)}"
            print(f"[NxSMS ERROR] {error_msg}")
            self.circuit_breakers[service].record_failure()
            key_hash = hashlib.md5(api_key.encode()).hexdigest()[:8]
            record_outcome(service, key_hash, False, error_msg, latency_ms)
            return SMSResult(success=False, service=service, error=error_msg, latency_ms=latency_ms)

    def send(self, phone: str, message: str, prefer_service: Optional[str] = None) -> SMSResult:
        """
        Send SMS with automatic key rotation.

        Args:
            phone: Phone number (with country code, e.g., +15551234567)
            message: Message to send
            prefer_service: Preferred service to try first

        Returns:
            SMSResult with success status
        """
        # Input validation
        if not phone or not phone.strip():
            return SMSResult(success=False, error="Phone number required")
        if not message or not message.strip():
            return SMSResult(success=False, error="Message required")
        
        # Normalize phone (add + if missing)
        phone = phone.strip()
        if not phone.startswith('+'):
            phone = '+' + phone
            
        # Try preferred service first
        if prefer_service:
            result = self._send_sms(prefer_service, phone, message)
            if result.success:
                return result
            # If failed, try other services

        # Get available services
        available = self.get_available_keys()

        if not available:
            return SMSResult(success=False, error="No available SMS services")

        # Try each service in order
        for service in available:
            result = self._send_sms(service, phone, message)
            if result.success:
                return result

            # Check if quota exhausted - skip this service for a while
            if "quota" in result.error.lower() or "limit" in result.error.lower():
                self.circuit_breakers[service].record_failure()

        return SMSResult(success=False, error="All services failed")

    def get_all_stats(self) -> Dict:
        """Get stats for all services."""
        stats = {}
        for service in self.stats:
            stats[service] = get_key_stats(service)
        return stats


# ============================================================
# Convenience
# ============================================================

_sms_instance: Optional[NxSMS] = None


def get_sms() -> NxSMS:
    """Get singleton SMS instance."""
    global _sms_instance
    if _sms_instance is None:
        _sms_instance = NxSMS()
    return _sms_instance


def send_sms(phone: str, message: str) -> SMSResult:
    """Quick send SMS function."""
    return get_sms().send(phone, message)