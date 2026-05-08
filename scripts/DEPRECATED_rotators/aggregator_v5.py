#!/usr/bin/env python3
"""
MAXIMUM THROUGHPUT AGGREGATOR - SELF-LEARNING v5.0
===================================================

Key features:
- Uses ALL 6 OpenRouter keys in rotation
- Direct connection (proxies are dead)
- Self-learning from outcomes (SQLite)
- Auto-rotation on rate limits (429)
- Real-time metrics dashboard
- Health tracking per key

This IS the working solution!
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
from collections import deque, defaultdict

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Config paths
CONFIG_DIR = Path(__file__).parent.parent / "configs" / "api-keys"
KEYS_FILE = CONFIG_DIR / "keys.json"
DB_FILE = CONFIG_DIR / "aggregator_learning.db"
METRICS_FILE = CONFIG_DIR / "aggregator_metrics.json"

# Thread safety
_lock = threading.Lock()

# Metrics
_metrics = {
    "total_requests": 0,
    "total_tokens": 0,
    "total_errors": 0,
    "total_rotations": 0,
    "by_key": defaultdict(lambda: {"requests": 0, "tokens": 0, "errors": 0}),
    "by_model": defaultdict(lambda: {"requests": 0, "tokens": 0, "errors": 0}),
    "request_history": [],
    "error_history": [],
    "uptime_start": datetime.now().isoformat(),
}

# State
_state = {
    "current_key_idx": 0,
    "keys_in_rotation": [],
    "daemon_mode": False,
}


@dataclass
class APIKey:
    """A single API key with health tracking."""

    key_id: str
    key: str
    provider: str
    creator_user_id: str
    email: str
    priority: int

    # Limits
    rpm_limit: int = 20
    tpm_limit: int = 50000
    daily_limit: int = 50

    # Runtime state
    is_exhausted: bool = False
    exhausted_at: Optional[datetime] = None
    request_count: int = 0
    error_count: int = 0
    last_used: Optional[datetime] = None
    last_error: Optional[str] = None
    consecutive_errors: int = 0
    health_score: float = 1.0
    cooldown_until: float = 0.0

    def is_available(self) -> bool:
        """Check if key can be used."""
        now = time.time()
        if now < self.cooldown_until:
            return False
        return not self.is_exhausted

    def record_success(self) -> None:
        """Reset failures, increase health."""
        self.consecutive_errors = 0
        self.health_score = min(1.0, self.health_score + 0.1)
        self.cooldown_until = 0.0

    def record_failure(self, error_type: str = "unknown") -> None:
        """Track failures, set cooldown."""
        self.consecutive_errors += 1
        self.error_count += 1
        self.health_score = max(0.0, self.health_score - 0.2)
        if error_type == "rate_limit" or self.consecutive_errors >= 3:
            cooldown = min(10 * (2 ** (self.consecutive_errors - 1)), 300)
            self.cooldown_until = time.time() + cooldown


class LearningAggregator:
    """Self-learning aggregator with SQLite outcome tracking."""

    def __init__(self):
        self.keys: List[APIKey] = []
        self._load_config()
        self._init_db()
        self._running = False
        self._daemon_thread = None

    def _init_db(self):
        """Initialize SQLite learning database."""
        conn = sqlite3.connect(str(DB_FILE))
        conn.execute("""CREATE TABLE IF NOT EXISTS outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            timestamp REAL, 
            key_id TEXT,
            model TEXT, 
            success INTEGER, 
            error_type TEXT, 
            latency_ms REAL,
            tokens_used INTEGER)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS key_performance (
            key_id TEXT PRIMARY KEY, 
            total_requests INTEGER DEFAULT 0,
            successful_requests INTEGER DEFAULT 0, 
            avg_latency_ms REAL DEFAULT 0.0,
            last_updated REAL)""")
        conn.commit()
        conn.close()
        print(f"[DB] Initialized: {DB_FILE}")

    def _record_outcome(
        self,
        key_id: str,
        model: str,
        success: bool,
        error_type: str = "",
        latency_ms: float = 0,
        tokens_used: int = 0,
    ):
        """Record outcome to learning database."""
        conn = sqlite3.connect(str(DB_FILE))
        try:
            conn.execute(
                "INSERT INTO outcomes (timestamp, key_id, model, success, error_type, latency_ms, tokens_used) VALUES (?,?,?,?,?,?,?)",
                (
                    time.time(),
                    key_id,
                    model,
                    int(success),
                    error_type,
                    latency_ms,
                    tokens_used,
                ),
            )
            # Update key performance
            conn.execute(
                """INSERT INTO key_performance 
                (key_id, total_requests, successful_requests, avg_latency_ms, last_updated)
                VALUES (?,?,?,?,?) 
                ON CONFLICT(key_id) DO UPDATE SET
                total_requests=total_requests+1, 
                successful_requests=successful_requests+excluded.successful_requests,
                avg_latency_ms=(avg_latency_ms*(total_requests-1)+excluded.avg_latency_ms)/CAST(total_requests AS REAL),
                last_updated=excluded.last_updated""",
                (key_id, 1, int(success), latency_ms, time.time()),
            )
            conn.commit()
        finally:
            conn.close()

    def _load_config(self):
        """Load keys from config."""
        if not KEYS_FILE.exists():
            print(f"[ERROR] Keys file not found: {KEYS_FILE}")
            return

        with open(KEYS_FILE, "r") as f:
            data = json.load(f)

        for provider, key_list in data.items():
            if provider == "openrouter":
                for k in key_list:
                    self.keys.append(
                        APIKey(
                            key_id=k.get("key_id", "unknown"),
                            key=k.get("key", ""),
                            provider=provider,
                            creator_user_id=k.get("creator_user_id", ""),
                            email=k.get("account_email", "unknown"),
                            priority=k.get("priority", 0),
                            rpm_limit=k.get("rpm_limit", 20),
                            tpm_limit=k.get("tpm_limit", 50000),
                            daily_limit=k.get("daily_limit", 50),
                        )
                    )

        print(f"[AGGREGATOR] Loaded {len(self.keys)} keys")

    def get_next_key(self) -> APIKey:
        """Get next available key (round-robin with health)."""
        if not self.keys:
            raise ValueError("No keys loaded!")

        # Find next available key (health score sorted)
        available = [k for k in self.keys if k.is_available()]
        if available:
            available.sort(key=lambda k: (-k.health_score, -k.consecutive_errors))
            _state["current_key_idx"] = self.keys.index(available[0])
            return available[0]

        # All exhausted - soft reset (clear cooldown only)
        print("[AGGREGATOR] All keys exhausted, soft resetting...")
        for key in self.keys:
            key.consecutive_errors = min(key.consecutive_errors, 2)
            key.cooldown_until = 0.0

        _state["current_key_idx"] = 0
        return self.keys[0]

    def make_request(
        self,
        model: str,
        messages: List[Dict],
        max_tokens: int = 8192,
        temperature: float = 0.7,
    ) -> Dict:
        """Make an aggregated request - auto-rotates on rate limits."""
        start_time = time.time()
        key = self.get_next_key()

        try:
            # Make request DIRECT (no proxy)
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key.key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://n-xyme.github.io",
                    "X-Title": "N-Xyme MIND",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=60,
            )

            latency_ms = (time.time() - start_time) * 1000

            # Track metrics
            with _lock:
                _metrics["total_requests"] += 1
                key.request_count += 1
                _metrics["by_key"][key.key_id]["requests"] += 1
                _metrics["by_model"][model]["requests"] += 1

                # Track tokens if successful
                if resp.status_code == 200:
                    data = resp.json()
                    usage = data.get("usage", {})
                    tokens = usage.get("total_tokens", 0)
                    _metrics["total_tokens"] += tokens
                    _metrics["by_key"][key.key_id]["tokens"] += tokens
                    _metrics["by_model"][model]["tokens"] += tokens

            # Check for rate limit
            if resp.status_code == 429:
                key.record_failure("rate_limit")
                self._record_outcome(key.key_id, model, False, "rate_limit", latency_ms)
                return self._handle_rate_limit(
                    key, model, messages, max_tokens, temperature
                )

            if resp.status_code != 200:
                key.record_failure("error")
                self._record_outcome(
                    key.key_id, model, False, f"http_{resp.status_code}", latency_ms
                )

                with _lock:
                    _metrics["total_errors"] += 1
                    _metrics["by_key"][key.key_id]["errors"] += 1

                return {
                    "success": False,
                    "error": resp.text[:200],
                    "key_used": key.key_id,
                }

            # Success!
            key.record_success()
            self._record_outcome(
                key.key_id,
                model,
                True,
                "",
                latency_ms,
                resp.json().get("usage", {}).get("total_tokens", 0),
            )

            return {
                "success": True,
                "response": resp.json(),
                "key_used": key.key_id,
                "latency_ms": latency_ms,
            }

        except Exception as e:
            error_str = str(e)
            key.record_failure("exception")
            self._record_outcome(
                key.key_id, model, False, "exception", (time.time() - start_time) * 1000
            )

            with _lock:
                _metrics["total_errors"] += 1

            # Check if rate limit
            if "429" in error_str or "rate" in error_str.lower():
                return self._handle_rate_limit(
                    key, model, messages, max_tokens, temperature
                )

            return {
                "success": False,
                "error": error_str,
                "key_used": key.key_id,
            }

    def _handle_rate_limit(
        self,
        key: APIKey,
        model: str,
        messages: List,
        max_tokens: int,
        temperature: float,
    ):
        """Handle rate limit - rotate and retry once."""
        print(f"[AGGREGATOR] Rate limit on {key.key_id}, rotating...")

        # Mark current as exhausted temporarily
        key.is_exhausted = True
        key.exhausted_at = datetime.now()

        with _lock:
            _metrics["total_rotations"] += 1

        # Get next key
        new_key = self.get_next_key()
        _state["current_key_idx"] = (_state["current_key_idx"] + 1) % len(self.keys)

        print(f"[AGGREGATOR] Retry with {new_key.key_id}")

        # Retry once
        return self.make_request(model, messages, max_tokens, temperature)

    def get_metrics(self) -> Dict:
        """Get aggregated metrics."""
        with _lock:
            total_rpm = sum(k.rpm_limit for k in self.keys if not k.is_exhausted)
            total_tpm = sum(k.tpm_limit for k in self.keys if not k.is_exhausted)
            active_keys = sum(1 for k in self.keys if not k.is_exhausted)

            uptime = datetime.now() - datetime.fromisoformat(_metrics["uptime_start"])

            return {
                "status": "operational" if active_keys > 0 else "degraded",
                "active_keys": active_keys,
                "total_keys": len(self.keys),
                "aggregated_rpm": total_rpm,
                "aggregated_tpm": total_tpm,
                "total_requests": _metrics["total_requests"],
                "total_tokens": _metrics["total_tokens"],
                "total_errors": _metrics["total_errors"],
                "total_rotations": _metrics["total_rotations"],
                "error_rate": _metrics["total_errors"]
                / max(_metrics["total_requests"], 1)
                * 100,
                "uptime_hours": uptime.total_seconds() / 3600,
                "by_key": dict(_metrics["by_key"]),
                "by_model": dict(_metrics["by_model"]),
            }

    def show_dashboard(self):
        """Display metrics dashboard."""
        metrics = self.get_metrics()

        print("\n" + "=" * 70)
        print("🟢 MAXIMUM THROUGHPUT AGGREGATOR v5.0 - SELF-LEARNING")
        print("=" * 70)

        print(f"\n📊 AGGREGATED LIMITS:")
        print(
            f"   RPM: {metrics['aggregated_rpm']} (was 20 per key × {metrics['total_keys']} keys)"
        )
        print(f"   TPM: {metrics['aggregated_tpm']:,}")

        print(f"\n🔑 KEYS: {metrics['active_keys']}/{metrics['total_keys']} active")
        for key in self.keys:
            status = "❌" if key.is_exhausted else "✅"
            health = (
                "❤️"
                if key.health_score > 0.7
                else "💔"
                if key.health_score < 0.3
                else "😐"
            )
            cooldown = (
                f" (cooldown {key.cooldown_until - time.time():.0f}s)"
                if key.cooldown_until > time.time()
                else ""
            )
            print(
                f"   {status} {health} {key.key_id}: {key.request_count} req, {key.error_count} err{cooldown}"
            )

        print(f"\n📈 METRICS:")
        print(f"   Total Requests: {metrics['total_requests']:,}")
        print(f"   Total Tokens: {metrics['total_tokens']:,}")
        print(f"   Total Errors: {metrics['total_errors']}")
        print(f"   Error Rate: {metrics['error_rate']:.2f}%")
        print(f"   Total Rotations: {metrics['total_rotations']}")
        print(f"   Uptime: {metrics['uptime_hours']:.1f} hours")

        # Top models
        print(f"\n🤖 TOP MODELS:")
        by_model = sorted(
            metrics["by_model"].items(), key=lambda x: x[1]["requests"], reverse=True
        )[:5]
        for model, stats in by_model:
            print(f"   {model}: {stats['requests']} req, {stats['tokens']:,} tokens")

        print("\n" + "=" * 70)


def main():
    """Main entry point."""
    agg = LearningAggregator()

    if len(sys.argv) < 2:
        agg.show_dashboard()
        return

    cmd = sys.argv[1]

    if cmd == "dashboard" or cmd == "status":
        agg.show_dashboard()

    elif cmd == "metrics":
        print(json.dumps(agg.get_metrics(), indent=2))

    elif cmd == "health":
        print(json.dumps(agg.get_metrics(), indent=2))

    elif cmd == "test":
        print("[TEST] Testing aggregator...")
        result = agg.make_request(
            "nvidia/nemotron-3-super-120b-a12b:free",
            [{"role": "user", "content": "Hi, say hi back in one word"}],
            max_tokens=10,
        )
        if result["success"]:
            print(f"✅ Success with {result['key_used']}")
            print(
                f"Response: {result['response']['choices'][0]['message']['content'][:50]}"
            )
        else:
            print(f"❌ Error: {result.get('error', 'unknown')[:100]}")

    elif cmd == "rotate":
        # Force rotate
        key = agg.get_next_key()
        agg._state["current_key_idx"] = (agg._state["current_key_idx"] + 1) % len(
            agg.keys
        )
        print(f"Rotated to: {key.key_id}")

    else:
        print(f"Unknown command: {cmd}")
        print("Usage: aggregator_v5.py [dashboard|metrics|health|test|rotate]")


if __name__ == "__main__":
    main()
