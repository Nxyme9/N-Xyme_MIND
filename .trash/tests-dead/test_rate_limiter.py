"""Unit tests for rate_limiter module."""

import sys
import os
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.infrastructure.rate_limiter import RateLimiter, RateLimiterRegistry, get_rate_limiter


class TestRateLimiter:
    """Tests for the token bucket rate limiter."""

    def test_allows_requests_within_limit(self):
        """Requests within burst size should be allowed."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=5)
        for _ in range(5):
            assert limiter.allow() is True

    def test_blocks_requests_after_burst(self):
        """Requests exceeding burst size should be blocked."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=3)
        assert limiter.allow() is True
        assert limiter.allow() is True
        assert limiter.allow() is True
        assert limiter.allow() is False

    def test_wait_time_when_tokens_available(self):
        """Wait time should be 0 when tokens are available."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=10)
        assert limiter.wait_time() == 0.0

    def test_wait_time_when_tokens_exhausted(self):
        """Wait time should be positive when tokens are exhausted."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=1)
        limiter.allow()  # Exhaust the single token
        wait = limiter.wait_time()
        assert wait > 0

    def test_get_stats(self):
        """Stats should return current rate limiter state."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=10)
        limiter.allow()
        stats = limiter.get_stats()
        assert stats["requests_per_minute"] == 60
        assert stats["burst_size"] == 10
        assert stats["current_rate"] >= 0
        assert stats["available_tokens"] >= 0


class TestRateLimiterRegistry:
    """Tests for the rate limiter registry."""

    def test_creates_new_limiter(self):
        """Registry should create new limiter for unknown service."""
        registry = RateLimiterRegistry()
        limiter = registry.get_or_create("test-service")
        assert isinstance(limiter, RateLimiter)

    def test_returns_existing_limiter(self):
        """Registry should return existing limiter for known service."""
        registry = RateLimiterRegistry()
        limiter1 = registry.get_or_create("test-service")
        limiter2 = registry.get_or_create("test-service")
        assert limiter1 is limiter2

    def test_get_all_stats(self):
        """Should return stats for all registered limiters."""
        registry = RateLimiterRegistry()
        registry.get_or_create("service-a")
        registry.get_or_create("service-b")
        stats = registry.get_all_stats()
        assert "service-a" in stats
        assert "service-b" in stats


def test_get_rate_limiter_global():
    """Global helper should return limiter from global registry."""
    limiter = get_rate_limiter("test-global", requests_per_minute=30)
    assert isinstance(limiter, RateLimiter)
