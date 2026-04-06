"""
API Key Pool Manager — Intelligent key rotation and health tracking.

Manages pools of API keys per provider, rotates on rate limits,
tracks health, and auto-recovers.
"""

import threading
import time
from typing import Dict, List, Optional


class APIKey:
    """Represents a single API key with health tracking."""

    def __init__(self, provider: str, key: str, rpm_limit: int = 60, tpm_limit: int = 100000):
        self.provider = provider
        self.key = key
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.rpm_current = 0
        self.tpm_current = 0
        self.rpm_reset = time.time() + 60
        self.tpm_reset = time.time() + 60
        self.health_score = 1.0
        self.consecutive_failures = 0
        self.cooldown_until = 0.0
        self.total_requests = 0
        self.total_failures = 0
        self.last_used = 0.0

    def is_available(self) -> bool:
        """Check if key can be used."""
        now = time.time()
        if now < self.cooldown_until:
            return False
        self._reset_usage_if_needed()
        if self.rpm_current >= self.rpm_limit:
            return False
        if self.tpm_current >= self.tpm_limit:
            return False
        return True

    def record_request(self, tokens_used: int = 0) -> None:
        """Track usage."""
        now = time.time()
        self._reset_usage_if_needed()
        self.rpm_current += 1
        self.tpm_current += tokens_used
        self.total_requests += 1
        self.last_used = now

    def record_success(self) -> None:
        """Reset failures, increase health."""
        self.consecutive_failures = 0
        self.health_score = min(1.0, self.health_score + 0.1)
        self.cooldown_until = 0.0

    def record_failure(self, error_type: str = "unknown") -> None:
        """Track failures, set cooldown."""
        self.consecutive_failures += 1
        self.total_failures += 1
        self.health_score = max(0.0, self.health_score - 0.2)
        if error_type == "rate_limit" or self.consecutive_failures >= 3:
            cooldown = min(10 * (2 ** (self.consecutive_failures - 1)), 300)
            self.cooldown_until = time.time() + cooldown

    def _reset_usage_if_needed(self) -> None:
        """Reset RPM/TPM counters if window expired."""
        now = time.time()
        if now >= self.rpm_reset:
            self.rpm_current = 0
            self.rpm_reset = now + 60
        if now >= self.tpm_reset:
            self.tpm_current = 0
            self.tpm_reset = now + 60

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "key_prefix": self.key[:8] + "..." if len(self.key) > 8 else self.key,
            "health_score": round(self.health_score, 2),
            "rpm_current": self.rpm_current,
            "rpm_limit": self.rpm_limit,
            "consecutive_failures": self.consecutive_failures,
            "cooldown_remaining": max(0, round(self.cooldown_until - time.time(), 1)),
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
        }


class APIKeyPool:
    """Manages pools of API keys per provider."""

    def __init__(self):
        self._pools: Dict[str, List[APIKey]] = {}
        self._lock = threading.Lock()

    def add_key(self, provider: str, key: str, rpm: int = 60, tpm: int = 100000) -> None:
        with self._lock:
            if provider not in self._pools:
                self._pools[provider] = []
            self._pools[provider].append(APIKey(provider, key, rpm, tpm))

    def get_best_key(self, provider: str) -> Optional[APIKey]:
        with self._lock:
            pool = self._pools.get(provider, [])
            available = [k for k in pool if k.is_available()]
            if not available:
                return None
            available.sort(key=lambda k: (k.health_score, -k.total_requests), reverse=True)
            return available[0]

    def rotate_on_429(self, provider: str, current_key: APIKey) -> Optional[APIKey]:
        with self._lock:
            current_key.record_failure("rate_limit")
            pool = self._pools.get(provider, [])
            available = [k for k in pool if k.is_available() and k is not current_key]
            if available:
                available.sort(key=lambda k: k.health_score, reverse=True)
                return available[0]
            return None

    def record_usage(self, provider: str, key: APIKey, tokens: int) -> None:
        with self._lock:
            key.record_request(tokens)
            key.record_success()

    def get_pool_status(self, provider: str) -> dict:
        with self._lock:
            pool = self._pools.get(provider, [])
            return {
                "provider": provider,
                "total_keys": len(pool),
                "available_keys": sum(1 for k in pool if k.is_available()),
                "keys": [k.to_dict() for k in pool],
            }

    def get_all_providers(self) -> List[str]:
        with self._lock:
            return list(self._pools.keys())


# Global instance
api_key_pool = APIKeyPool()
