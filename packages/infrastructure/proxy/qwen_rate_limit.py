"""
Qwen-specific rate limiter - minimal fix for qwen3.6-plus-free rate limits.

Safe starting point: 3-5 RPM based on community research.
"""

import time
import threading
from collections import deque
from dataclasses import dataclass, field


@dataclass
class QwenRateLimiter:
    """Rate limiter specifically for qwen3.6-plus-free model."""
    
    # SAFE STARTING POINT: 3-5 RPM (community research)
    rpm: int = 3
    burst: int = 1
    _tokens: float = field(default=1.0, init=False)
    _last_refill: float = field(default_factory=time.time)
    _recent_requests: deque = field(default_factory=deque)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    @property
    def tuple_key(self) -> str:
        return "opencode|qwen3.6-plus-free"
    
    def allow(self) -> bool:
        """Check if request allowed."""
        with self._lock:
            now = time.time()
            
            # Refill tokens based on time passed
            time_passed = now - self._last_refill
            tokens_to_add = time_passed * (self.rpm / 60.0)
            self._tokens = min(self.burst, self._tokens + tokens_to_add)
            self._last_refill = now
            
            # Check token bucket
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                self._recent_requests.append(now)
                return True
            
            return False
    
    def wait_time(self) -> float:
        """Seconds to wait before next request."""
        if self._tokens >= 1.0:
            return 0.0
        tokens_needed = 1.0 - self._tokens
        return tokens_needed / (self.rpm / 60.0)
    
    def record_success(self) -> None:
        """Called on successful request - could increase rate slightly."""
        # Simple: no increase on success (keep conservative)
        pass
    
    def record_rate_limit(self) -> None:
        """Called on 429 - decrease rate."""
        with self._lock:
            # Multiplicative decrease: cut rate in half on rate limit
            self.rpm = max(1, self.rpm // 2)
            self.burst = max(1, self.burst // 2)
            self._tokens = 0.0  # Reset tokens on rate limit
    
    def get_stats(self) -> dict:
        """Get current stats."""
        now = time.time()
        recent = [t for t in self._recent_requests if now - t < 60]
        return {
            "model": "qwen3.6-plus-free",
            "rpm": self.rpm,
            "burst": self.burst,
            "current_rate_60s": len(recent),
            "tokens_available": self._tokens,
            "wait_time_seconds": self.wait_time(),
        }


# Global instance
_qwen_limiter = QwenRateLimiter()


def get_qwen_limiter() -> QwenRateLimiter:
    """Get the global qwen rate limiter."""
    return _qwen_limiter


def check_qwen_rate() -> bool:
    """Check if qwen request is allowed."""
    return _qwen_limiter.allow()


def wait_for_qwen() -> float:
    """Wait for qwen rate limit and return wait time."""
    return _qwen_limiter.wait_time()


def record_qwen_success() -> None:
    """Record qwen success."""
    _qwen_limiter.record_success()


def record_qwen_rate_limit() -> None:
    """Record qwen rate limit hit."""
    _qwen_limiter.record_rate_limit()


if __name__ == "__main__":
    # Test it
    print("Qwen Rate Limiter Test")
    limiter = QwenRateLimiter(rpm=3)
    
    print(f"Stats: {limiter.get_stats()}")
    print(f"Allow: {limiter.allow()}")
    print(f"Stats after allow: {limiter.get_stats()}")