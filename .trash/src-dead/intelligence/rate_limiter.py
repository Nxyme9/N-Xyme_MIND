"""Rate Limiter for Routing Requests

Implements token bucket rate limiting to prevent abuse and ensure fair usage.
"""

import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("rate-limiter")


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, max_tokens: int = 100, refill_rate: float = 10.0):
        """
        Args:
            max_tokens: Maximum tokens in the bucket
            refill_rate: Tokens added per second
        """
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self._buckets: Dict[str, Dict[str, float]] = {}

    def _get_bucket(self, client_id: str) -> Dict[str, float]:
        """Get or create a token bucket for a client."""
        if client_id not in self._buckets:
            self._buckets[client_id] = {
                "tokens": self.max_tokens,
                "last_refill": time.time(),
            }
        return self._buckets[client_id]

    def _refill(self, bucket: Dict[str, float]):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - bucket["last_refill"]
        tokens_to_add = elapsed * self.refill_rate
        bucket["tokens"] = min(self.max_tokens, bucket["tokens"] + tokens_to_add)
        bucket["last_refill"] = now

    def allow_request(self, client_id: str, tokens: int = 1) -> bool:
        """Check if a request is allowed."""
        bucket = self._get_bucket(client_id)
        self._refill(bucket)

        if bucket["tokens"] >= tokens:
            bucket["tokens"] -= tokens
            return True

        logger.warning(f"Rate limit exceeded for client: {client_id}")
        return False

    def get_status(self, client_id: str) -> Dict[str, Any]:
        """Get rate limit status for a client."""
        bucket = self._get_bucket(client_id)
        self._refill(bucket)

        return {
            "client_id": client_id,
            "tokens_remaining": bucket["tokens"],
            "max_tokens": self.max_tokens,
            "refill_rate": self.refill_rate,
            "utilization": 1 - (bucket["tokens"] / self.max_tokens),
        }

    def reset(self, client_id: Optional[str] = None):
        """Reset rate limit for a client or all clients."""
        if client_id:
            if client_id in self._buckets:
                del self._buckets[client_id]
        else:
            self._buckets.clear()


# Global rate limiter instance
_rate_limiter = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
