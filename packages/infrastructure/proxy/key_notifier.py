"""API Key/Token Notifier — Alerts when keys are near limits."""

import threading
import time
from typing import Dict, List, Optional
from collections import defaultdict


class KeyNotifier:
    def __init__(self, warning_threshold: float = 0.8, critical_threshold: float = 0.95):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self._lock = threading.Lock()
        self._alerts: List[dict] = []
        self._key_usage: Dict[str, dict] = defaultdict(lambda: {"requests": 0, "tokens": 0, "last_reset": time.time()})

    def record_usage(self, key_prefix: str, requests: int = 1, tokens: int = 0) -> None:
        """Record API key usage."""
        with self._lock:
            usage = self._key_usage[key_prefix]
            usage["requests"] += requests
            usage["tokens"] += tokens
            # Check thresholds
            if usage["requests"] > 100:  # Example RPM limit
                usage["requests"] = 0
                usage["last_reset"] = time.time()

    def record_rate_limit(self, key_prefix: str) -> None:
        """Record a rate limit hit for a key."""
        with self._lock:
            usage = self._key_usage[key_prefix]
            usage["rate_limits"] = usage.get("rate_limits", 0) + 1
            self._alerts.append({
                "time": time.time(),
                "severity": "WARNING",
                "key": key_prefix,
                "message": f"Rate limit hit for key {key_prefix}"
            })

    def check_limits(self) -> List[dict]:
        """Check all keys for limit warnings."""
        alerts = []
        with self._lock:
            for key_prefix, usage in self._key_usage.items():
                rpm = usage["requests"] / max(1, time.time() - usage["last_reset"]) * 60
                if rpm > self.critical_threshold * 100:
                    alerts.append({"key": key_prefix, "severity": "CRITICAL", "rpm": round(rpm, 1), "message": f"Key {key_prefix} near rate limit: {rpm:.1f} RPM"})
                elif rpm > self.warning_threshold * 100:
                    alerts.append({"key": key_prefix, "severity": "WARNING", "rpm": round(rpm, 1), "message": f"Key {key_prefix} approaching rate limit: {rpm:.1f} RPM"})
        self._alerts.extend(alerts)
        return alerts

    def get_alerts(self, limit: int = 20) -> List[dict]:
        """Get recent alerts."""
        with self._lock:
            return self._alerts[-limit:]

    def clear_alerts(self) -> None:
        """Clear all alerts."""
        with self._lock:
            self._alerts.clear()


# Global instance
key_notifier = KeyNotifier()
