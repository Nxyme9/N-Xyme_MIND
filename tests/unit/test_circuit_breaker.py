"""Unit tests for circuit_breaker module."""
import sys
import os
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.infrastructure.circuit_breaker import CircuitBreaker, CircuitBreakerOpen, CircuitState


class TestCircuitBreaker:
    """Tests for the circuit breaker fault tolerance."""

    def test_closed_state_allows_calls(self):
        """Closed circuit should allow all calls."""
        breaker = CircuitBreaker(name="test", failure_threshold=3, reset_timeout=1)
        result = breaker.call(lambda: "success")
        assert result == "success"

    def test_opens_after_threshold_failures(self):
        """Circuit should open after failure threshold is reached."""
        breaker = CircuitBreaker(name="test", failure_threshold=3, reset_timeout=60)

        def failing_func():
            raise ValueError("service down")

        for _ in range(3):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        # Circuit should now be open
        with pytest.raises(CircuitBreakerOpen):
            breaker.call(lambda: "success")

    def test_half_open_after_reset_timeout(self):
        """Circuit should transition to half-open after reset timeout."""
        breaker = CircuitBreaker(name="test", failure_threshold=1, reset_timeout=0.1)

        def failing_func():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            breaker.call(failing_func)

        # Wait for reset timeout
        time.sleep(0.2)

        # Should allow one test call (half-open)
        result = breaker.call(lambda: "recovered")
        assert result == "recovered"

    def test_tracks_failure_count(self):
        """Failure count should increment on errors."""
        breaker = CircuitBreaker(name="test", failure_threshold=10, reset_timeout=60)

        def failing_func():
            raise RuntimeError("fail")

        for _ in range(5):
            with pytest.raises(RuntimeError):
                breaker.call(failing_func)

        assert breaker.failure_count == 5

    def test_state_transitions(self):
        """Circuit should transition through states correctly."""
        breaker = CircuitBreaker(name="test", failure_threshold=1, reset_timeout=0.1)
        assert breaker.state == CircuitState.CLOSED
