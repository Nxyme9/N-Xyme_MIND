"""
Rate Limiter — Token bucket algorithm with thread-safe blocking acquire.

Usage:
    rl = RateLimiter(max_requests=8, window_seconds=60)
    rl.acquire()        # blocks until token available
    if rl.try_acquire(): # non-blocking
        # proceed
    wait = rl.get_wait_time()  # seconds until next request allowed
"""

import threading
import time


class RateLimiter:
    """Token bucket rate limiter with thread-safe blocking acquire."""

    MODEL_COST_MAP = {
        "opencode": 1.0,
        "openrouter": 1.5,
        "ollama": 0.1,
    }

    def __init__(self, max_requests: int = 8, window_seconds: float = 60.0):
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if max_requests <= 0:
            raise ValueError("max_requests must be positive")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._tokens = float(max_requests)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()
        self._total_consumed = 0

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        tokens_to_add = elapsed * (self.max_requests / self.window_seconds)
        self._tokens = min(self.max_requests, self._tokens + tokens_to_add)
        self._last_refill = now

    def consume(self, tokens: int = 1) -> None:
        """Block until tokens are available, then consume them."""
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= float(tokens):
                    self._tokens -= float(tokens)
                    self._total_consumed += tokens
                    return
                wait_time = (float(tokens) - self._tokens) / (
                    self.max_requests / self.window_seconds
                )
            time.sleep(min(wait_time, 1.0))

    def acquire(self) -> None:
        """Block until a token is available, then consume it."""
        self.consume(1)

    def try_acquire(self, tokens: int = 1) -> bool:
        """Non-blocking attempt to acquire tokens. Returns True if successful."""
        with self._lock:
            self._refill()
            if self._tokens >= float(tokens):
                self._tokens -= float(tokens)
                self._total_consumed += tokens
                return True
            return False

    def get_wait_time(self, tokens: int = 1) -> float:
        """Return seconds until specified tokens are available."""
        with self._lock:
            self._refill()
            if self._tokens >= float(tokens):
                return 0.0
            return (float(tokens) - self._tokens) / (
                self.max_requests / self.window_seconds
            )

    def get_stats(self) -> dict:
        """Return current rate limiter statistics."""
        with self._lock:
            self._refill()
            return {
                "max_requests": self.max_requests,
                "window_seconds": self.window_seconds,
                "available_tokens": self._tokens,
                "total_consumed": self._total_consumed,
            }

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token estimate: 1 token ≈ 4 chars for English."""
        if not text:
            return 0
        return max(1, len(text) // 4)
