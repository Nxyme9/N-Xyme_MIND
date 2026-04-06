"""
Rate Limiter — Per-service rate limiting (ported from SPINE)

Prevents API quota exhaustion by limiting request rates.

Usage:
    limiter = RateLimiter(requests_per_minute=60)
    if limiter.allow():
        make_request()
    else:
        print("Rate limited, wait...")
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class RateLimiter:
    """Token bucket rate limiter."""

    requests_per_minute: int = 60
    burst_size: int = 10
    _tokens: float = field(default=10.0, init=False)
    _last_refill: float = field(default_factory=time.time)
    _requests: deque = field(default_factory=deque)

    def allow(self) -> bool:
        """Check if request is allowed."""
        now = time.time()

        # Refill tokens
        time_passed = now - self._last_refill
        tokens_to_add = time_passed * (self.requests_per_minute / 60.0)
        self._tokens = min(self.burst_size, self._tokens + tokens_to_add)
        self._last_refill = now

        # Check token bucket
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            self._requests.append(now)
            return True

        return False

    def wait_time(self) -> float:
        """Get time to wait before next request is allowed."""
        if self._tokens >= 1.0:
            return 0.0
        tokens_needed = 1.0 - self._tokens
        return tokens_needed / (self.requests_per_minute / 60.0)

    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        now = time.time()
        recent = [t for t in self._requests if now - t < 60]
        return {
            "requests_per_minute": self.requests_per_minute,
            "current_rate": len(recent),
            "available_tokens": self._tokens,
            "burst_size": self.burst_size,
        }


class RateLimiterRegistry:
    """Registry for multiple rate limiters."""

    def __init__(self):
        self._limiters: Dict[str, RateLimiter] = {}

    def get_or_create(
        self,
        service: str,
        requests_per_minute: int = 60,
        burst_size: int = 10,
    ) -> RateLimiter:
        """Get or create a rate limiter for a service."""
        if service not in self._limiters:
            self._limiters[service] = RateLimiter(
                requests_per_minute=requests_per_minute,
                burst_size=burst_size,
            )
        return self._limiters[service]

    def get_all_stats(self) -> Dict[str, Dict]:
        """Get stats of all rate limiters."""
        return {name: l.get_stats() for name, l in self._limiters.items()}


# Global registry
_global_limiter_registry = RateLimiterRegistry()


def get_rate_limiter(service: str, **kwargs) -> RateLimiter:
    """Get a rate limiter from global registry."""
    return _global_limiter_registry.get_or_create(service, **kwargs)
