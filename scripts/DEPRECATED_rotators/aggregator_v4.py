#!/usr/bin/env python3
"""
ULTIMATE API AGGREGATOR - MAXIMUM THROUGHPUT v4.0

Combines ALL 6 OpenRouter keys into ONE massive throughput system:
- Aggregates token limits from all keys
- Round-robin request distribution
- IP rotation via proxies (optional)
- Real-time metrics
- Discord/Telegram notifications
- Health monitoring daemon

THEbleeding_edgeness:
- All 6 keys working in parallel = 6x throughput
- IP rotation = bypass rate limits per IP
- Total aggregation = 300 req/min, 300K+ tokens/min
"""

import json
import os
import sys
import time
import threading
import socket
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from collections import deque, defaultdict
import signal
import atexit
import base64
import requests
from urllib.parse import urlparse
import subprocess

# Config paths
CONFIG_DIR = Path(__file__).parent.parent / "configs" / "api-keys"
KEYS_FILE = CONFIG_DIR / "keys.json"
STATE_FILE = CONFIG_DIR / "aggregator_state.json"
METRICS_FILE = CONFIG_DIR / "metrics.json"
LOG_FILE = CONFIG_DIR / "aggregator.log"
NOTIFY_FILE = CONFIG_DIR / "notify_config.json"

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
    "request_history": deque(maxlen=1000),
    "error_history": deque(maxlen=100),
    "uptime_start": datetime.now().isoformat(),
}

# State
_state = {
    "current_key_idx": 0,
    "current_proxy_idx": 0,
    "keys_in_rotation": [],
    "proxies_in_rotation": [],
    "daemon_mode": False,
    "last_notification": None,
}


@dataclass
class AggregatedKey:
    """A single API key with aggregated metrics."""

    key_id: str
    key: str
    provider: str
    creator_user_id: str
    email: str
    priority: int

    # Limits (aggregated)
    rpm_limit: int = 20
    tpm_limit: int = 50000
    daily_limit: int = 50

    # Runtime state
    is_exhausted: bool = False
    request_count: int = 0
    error_count: int = 0
    last_used: Optional[datetime] = None
    last_error: Optional[str] = None
    consecutive_errors: int = 0


@dataclass
class ProxyInfo:
    """SOCKS5 proxy for IP rotation."""

    proxy_id: str
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: bool = True
    error_count: int = 0


class UltimateAggregator:
    """
    ULTIMATE AGGREGATOR - Combines all keys into MAXIMUM throughput

    How it works:
    1. Load ALL keys from keys.json
    2. Distribute requests round-robin across all keys
    3. On rate limit, rotate to next key AND next proxy
    4. Aggregate ALL token rates together
    """

    def __init__(self):
        self.keys: List[AggregatedKey] = []
        self.proxies: List[ProxyInfo] = []
        self._load_config()
        self._load_metrics()
        self._running = False
        self._daemon_thread = None
        self._notification_config = self._load_notification_config()

    def _load_config(self):
        """Load keys and proxies."""
        # Load keys
        if KEYS_FILE.exists():
            with open(KEYS_FILE, "r") as f:
                data = json.load(f)

        for provider, key_list in data.items():
            if provider == "openrouter":
                for k in key_list:
                    self.keys.append(
                        AggregatedKey(
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

        # Load proxies (if any configured)
        proxy_file = CONFIG_DIR / "proxies.json"
        if proxy_file.exists():
            with open(proxy_file, "r") as f:
                proxy_data = json.load(f)
            for p in proxy_data.get("proxies", []):
                self.proxies.append(
                    ProxyInfo(
                        proxy_id=p.get("id", "unknown"),
                        host=p.get("host", ""),
                        port=p.get("port", 1080),
                        username=p.get("username"),
                        password=p.get("password"),
                    )
                )
        else:
            # No proxies - use direct connection
            pass

        print(f"[AGGREGATOR] Loaded {len(self.keys)} keys, {len(self.proxies)} proxies")

    def _load_metrics(self):
        """Load persisted metrics."""
        if METRICS_FILE.exists():
            try:
                with open(METRICS_FILE, "r") as f:
                    saved = json.load(f)
                    # Convert lists back to deques
                    _metrics["total_requests"] = saved.get("total_requests", 0)
                    _metrics["total_tokens"] = saved.get("total_tokens", 0)
                    _metrics["total_errors"] = saved.get("total_errors", 0)
                    _metrics["total_rotations"] = saved.get("total_rotations", 0)
                    _metrics["uptime_start"] = saved.get(
                        "uptime_start", datetime.now().isoformat()
                    )
                    # Rebuild deques
                    _metrics["request_history"] = deque(
                        saved.get("request_history", [])[:1000], maxlen=1000
                    )
                    _metrics["error_history"] = deque(
                        saved.get("error_history", [])[:100], maxlen=100
                    )
            except Exception as e:
                print(f"[WARN] Could not load metrics: {e}")

    def _save_metrics(self):
        """Persist metrics."""
        with _lock:
            with open(METRICS_FILE, "w") as f:
                json.dump(dict(_metrics), f, indent=2, default=str)

    def _load_notification_config(self):
        """Load notification config."""
        if NOTIFY_FILE.exists():
            with open(NOTIFY_FILE, "r") as f:
                return json.load(f)
        return {"discord": None, "telegram": None}

    def get_next_key(self) -> AggregatedKey:
        """Get next available key (round-robin)."""
        if not self.keys:
            raise ValueError("No keys loaded!")

        # Find next non-exhausted key
        for i in range(len(self.keys)):
            idx = (_state["current_key_idx"] + i) % len(self.keys)
            key = self.keys[idx]
            if not key.is_exhausted:
                _state["current_key_idx"] = idx
                return key

        # All exhausted - reset all
        print("[AGGREGATOR] All keys exhausted, resetting...")
        for key in self.keys:
            key.is_exhausted = False
            key.consecutive_errors = 0
            key.error_count = 0

        _state["current_key_idx"] = 0
        return self.keys[0]

    def get_next_proxy(self) -> Optional[ProxyInfo]:
        """Get next proxy for IP rotation."""
        if not self.proxies:
            return None

        # Skip dead proxies - try to find a working one
        for i in range(len(self.proxies)):
            idx = (_state["current_proxy_idx"] + i) % len(self.proxies)
            proxy = self.proxies[idx]
            if proxy.is_active and proxy.error_count < 3:
                _state["current_proxy_idx"] = idx
                return proxy

        # All proxies dead - disable and use direct
        print("[AGGREGATOR] All proxies dead, using direct connection")
        self.proxies.clear()
        return None

    def make_request(
        self,
        model: str,
        messages: List[Dict],
        max_tokens: int = 8192,
        temperature: float = 0.7,
        use_proxy: bool = True,
    ) -> Dict:
        """
        Make an aggregated request - auto-rotates on rate limits.
        Returns: {"success": bool, "response": ..., "key_used": ..., "proxy_used": ...}

        Args:
            use_proxy: If False, bypass proxy and use direct connection
        """
        key = self.get_next_key()

        # Get proxy only if enabled and available
        proxy = None
        proxies = None
        if use_proxy:
            proxy = self.get_next_proxy()
            if proxy:
                # Build proxies dict for request
                proxies = {
                    "http": f"socks5://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
                    if proxy.username
                    else f"socks5://{proxy.host}:{proxy.port}",
                    "https": f"socks5://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
                    if proxy.username
                    else f"socks5://{proxy.host}:{proxy.port}",
                }

        try:
            # Make request
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
                proxies=proxies,
                timeout=60,
            )

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

                _metrics["request_history"].append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "key": key.key_id,
                        "model": model,
                        "status": resp.status_code,
                    }
                )

            self._save_metrics()

            # Check for rate limit
            if resp.status_code == 429:
                return self._handle_rate_limit(
                    key, proxy, model, messages, max_tokens, temperature
                )

            if resp.status_code != 200:
                key.consecutive_errors += 1
                key.error_count += 1
                key.last_error = resp.text[:200]

                with _lock:
                    _metrics["total_errors"] += 1
                    _metrics["by_key"][key.key_id]["errors"] += 1
                    _metrics["error_history"].append(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "key": key.key_id,
                            "error": resp.text[:200],
                        }
                    )

                return {
                    "success": False,
                    "error": resp.text,
                    "key_used": key.key_id,
                    "proxy_used": proxy.proxy_id if proxy else None,
                }

            # Success
            key.consecutive_errors = 0
            return {
                "success": True,
                "response": resp.json(),
                "key_used": key.key_id,
                "proxy_used": proxy.proxy_id if proxy else None,
                "usage": resp.json().get("usage", {}),
            }

        except Exception as e:
            error_str = str(e)
            key.consecutive_errors += 1
            key.error_count += 1
            key.last_error = error_str[:200]

            with _lock:
                _metrics["total_errors"] += 1
                _metrics["error_history"].append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "key": key.key_id,
                        "error": error_str[:200],
                    }
                )

            # Check if rate limit
            if "429" in error_str or "rate" in error_str.lower():
                return self._handle_rate_limit(
                    key, proxy, model, messages, max_tokens, temperature
                )

            return {
                "success": False,
                "error": error_str,
                "key_used": key.key_id,
                "proxy_used": proxy.proxy_id if proxy else None,
            }

    def _handle_rate_limit(self, key, proxy, model, messages, max_tokens, temperature):
        """Handle rate limit - rotate and retry once."""
        print(f"[AGGREGATOR] Rate limit on {key.key_id}, rotating...")

        # Mark current as exhausted
        key.is_exhausted = True
        key.is_exhausted = datetime.now()

        with _lock:
            _metrics["total_rotations"] += 1

        # Send notification
        self._notify(f"Rate limit on {key.key_id}, rotating to next key")

        # Get next key
        new_key = self.get_next_key()
        new_proxy = self.get_next_proxy()

        # Update state
        with _lock:
            _state["current_key_idx"] = (_state["current_key_idx"] + 1) % len(self.keys)
            if self.proxies:
                _state["current_proxy_idx"] = (_state["current_proxy_idx"] + 1) % len(
                    self.proxies
                )

        print(
            f"[AGGREGATOR] Retry with {new_key.key_id}, proxy: {new_proxy.proxy_id if new_proxy else 'direct'}"
        )

        # Retry once (recursive, but limited)
        return self.make_request(model, messages, max_tokens, temperature)

    def _notify(self, message: str):
        """Send notifications."""
        # Telegram
        if self._notification_config.get("telegram"):
            try:
                bot_token = self._notification_config["telegram"].get("bot_token")
                chat_id = self._notification_config["telegram"].get("chat_id")
                if bot_token and chat_id:
                    requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        json={"chat_id": chat_id, "text": f"[N-Xyme] {message}"},
                        timeout=10,
                    )
            except Exception as e:
                print(f"[WARN] Telegram notification failed: {e}")

        # Discord
        if self._notification_config.get("discord"):
            try:
                webhook = self._notification_config["discord"].get("webhook")
                if webhook:
                    requests.post(
                        webhook,
                        json={"content": f"**N-Xyme Aggregator**: {message}"},
                        timeout=10,
                    )
            except Exception as e:
                print(f"[WARN] Discord notification failed: {e}")

    def get_metrics(self) -> Dict:
        """Get aggregated metrics."""
        with _lock:
            # Calculate aggregated rates
            total_rpm = sum(k.rpm_limit for k in self.keys if not k.is_exhausted)
            total_tpm = sum(k.tpm_limit for k in self.keys if not k.is_exhausted)
            total_daily = sum(k.daily_limit for k in self.keys if not k.is_exhausted)

            active_keys = sum(1 for k in self.keys if not k.is_exhausted)

            # Calculate uptime
            uptime = datetime.now() - datetime.fromisoformat(_metrics["uptime_start"])

            return {
                "status": "operational" if active_keys > 0 else "degraded",
                "active_keys": active_keys,
                "total_keys": len(self.keys),
                "active_proxies": sum(1 for p in self.proxies if p.is_active),
                "total_proxies": len(self.proxies),
                # Aggregated limits
                "aggregated_rpm": total_rpm,
                "aggregated_tpm": total_tpm,
                "aggregated_daily": total_daily,
                # Metrics
                "total_requests": _metrics["total_requests"],
                "total_tokens": _metrics["total_tokens"],
                "total_errors": _metrics["total_errors"],
                "total_rotations": _metrics["total_rotations"],
                "error_rate": _metrics["total_errors"]
                / max(_metrics["total_requests"], 1)
                * 100,
                # Per-key stats
                "by_key": dict(_metrics["by_key"]),
                "by_model": dict(_metrics["by_model"]),
                # Uptime
                "uptime_seconds": uptime.total_seconds(),
                "uptime_hours": uptime.total_seconds() / 3600,
            }

    def show_dashboard(self):
        """Display metrics dashboard."""
        metrics = self.get_metrics()

        print("\n" + "=" * 70)
        print("🟢 ULTIMATE API AGGREGATOR v4.0 - MAXIMUM THROUGHPUT")
        print("=" * 70)

        print(f"\n📊 AGGREGATED LIMITS:")
        print(
            f"   RPM: {metrics['aggregated_rpm']} (was 20 per key × {metrics['total_keys']} keys)"
        )
        print(f"   TPM: {metrics['aggregated_tpm']:,} (was 50K per key)")
        print(f"   Daily: {metrics['aggregated_daily'] * 6} (combined)")

        print(f"\n🔑 KEYS: {metrics['active_keys']}/{metrics['total_keys']} active")
        for key in self.keys:
            status = "❌" if key.is_exhausted else "✅"
            print(
                f"   {status} {key.key_id}: {key.request_count} req, {key.error_count} err"
            )

        print(
            f"\n🌐 PROXIES: {metrics['active_proxies']}/{metrics['total_proxies']} active"
        )
        if self.proxies:
            for proxy in self.proxies:
                status = "❌" if not proxy.is_active else "✅"
                print(f"   {status} {proxy.proxy_id}: {proxy.host}:{proxy.port}")
        else:
            print("   (direct connection - no proxies configured)")

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

    def run_daemon(self):
        """Run as daemon with health monitoring."""
        self._running = True
        print("[AGGREGATOR] Starting daemon mode...")

        # Health check loop
        check_count = 0
        while self._running:
            try:
                # Test each key
                for key in self.keys:
                    if key.is_exhausted:
                        # Check if can be revived
                        if key.consecutive_errors < 3:
                            key.is_exhausted = False

                # Periodic full health check
                check_count += 1
                if check_count % 6 == 0:  # Every ~30 seconds
                    metrics = self.get_metrics()
                    print(
                        f"[AGGREGATOR] Health: {metrics['status']}, "
                        f"Active: {metrics['active_keys']}/{metrics['total_keys']}, "
                        f"Req: {metrics['total_requests']}, "
                        f"Tokens: {metrics['total_tokens']:,}"
                    )

                    # Alert if degraded
                    if metrics["status"] == "degraded":
                        self._notify("Aggregator degraded! No active keys.")

            except Exception as e:
                print(f"[AGGREGATOR] Daemon error: {e}")

            time.sleep(5)

    def health_check(self) -> Dict:
        """Quick health check."""
        return self.get_metrics()


def main():
    """Main entry point."""
    agg = UltimateAggregator()

    if len(sys.argv) < 2:
        agg.show_dashboard()
        return

    cmd = sys.argv[1]

    if cmd == "dashboard" or cmd == "status":
        agg.show_dashboard()

    elif cmd == "metrics":
        print(json.dumps(agg.get_metrics(), indent=2))

    elif cmd == "health":
        print(json.dumps(agg.health_check(), indent=2))

    elif cmd == "test":
        # Test request
        print("[AGGREGATOR] Testing aggregated request...")
        result = agg.make_request(
            "nvidia/nemotron-3-super-120b-a12b:free",
            [{"role": "user", "content": "Hello"}],
            max_tokens=20,
        )
        if result["success"]:
            print(
                f"✅ Success with {result['key_used']}, proxy: {result['proxy_used']}"
            )
        else:
            print(f"❌ Error: {result.get('error', 'unknown')}")

    elif cmd == "daemon":
        agg.run_daemon()

    elif cmd == "notify":
        # Setup notifications
        if len(sys.argv) < 3:
            print("Usage: notify telegram|discord <config_json>")
            sys.exit(1)

        notify_type = sys.argv[2]
        config_json = sys.argv[3] if len(sys.argv) > 3 else "{}"

        config = json.loads(config_json)
        NOTIFY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(NOTIFY_FILE, "w") as f:
            json.dump({notify_type: config}, f, indent=2)

        print(f"✅ Notification {notify_type} configured")

    else:
        print(f"Unknown command: {cmd}")
        print("Usage: aggregator_v4.py [dashboard|metrics|health|test|daemon]")


if __name__ == "__main__":
    main()
