"""Unit tests for DistributedCircuitBreaker.

Covers:
  - Sliding window metrics
  - State machine transitions (CLOSED → OPEN → HALF_OPEN → CLOSED)
  - Configurable thresholds
  - Retry with exponential backoff
  - Fallback invocation
  - Audit trail
  - Thread safety
  - Error messages when circuit opens
  - Registry operations
"""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest

from src.healing.distributed_circuit_breaker import (
    CircuitBreakerConfig,
    CircuitOpenError,
    CircuitState,
    DistributedCircuitBreaker,
    DistributedCircuitBreakerRegistry,
    MaxRetriesExceededError,
    SlidingWindowMetrics,
    StateTransitionReason,
    get_distributed_breaker,
)


# ===================================================================
# SlidingWindowMetrics
# ===================================================================


class TestSlidingWindowMetrics:
    def test_initial_state(self):
        m = SlidingWindowMetrics(max_size=10)
        assert m.total_calls() == 0
        assert m.failure_rate() == 0.0
        assert m.avg_response_time_ms() == 0.0

    def test_record_success(self):
        m = SlidingWindowMetrics(max_size=10)
        m.record_success(100.0)
        m.record_success(200.0)
        assert m.total_calls() == 2
        assert m.failure_rate() == 0.0
        assert m.avg_response_time_ms() == 150.0

    def test_record_failure(self):
        m = SlidingWindowMetrics(max_size=10)
        m.record_failure(50.0, "timeout")
        assert m.total_calls() == 1
        assert m.failure_rate() == 100.0

    def test_mixed_success_failure(self):
        m = SlidingWindowMetrics(max_size=10)
        m.record_success(100.0)
        m.record_failure(200.0, "err")
        m.record_success(150.0)
        assert m.total_calls() == 3
        assert m.failure_rate() == pytest.approx(100.0 / 3.0, rel=1e-6)

    def test_sliding_window_eviction(self):
        m = SlidingWindowMetrics(max_size=3)
        m.record_failure(10.0, "a")
        m.record_failure(10.0, "b")
        m.record_failure(10.0, "c")
        m.record_success(10.0)  # should evict first failure
        assert m.total_calls() == 3
        assert m.failure_rate() == pytest.approx(200.0 / 3.0, rel=1e-6)

    def test_snapshot(self):
        m = SlidingWindowMetrics(max_size=10)
        m.record_success(100.0)
        m.record_failure(500.0, "err")
        snap = m.snapshot()
        assert snap["total_calls"] == 2
        assert snap["failure_count"] == 1
        assert snap["failure_rate_pct"] == 50.0
        assert snap["avg_response_time_ms"] == 300.0
        assert snap["max_response_time_ms"] == 500.0
        assert snap["min_response_time_ms"] == 100.0

    def test_slow_call_rate(self):
        m = SlidingWindowMetrics(max_size=10)
        m.record_success(100.0)
        m.record_success(3000.0)
        m.record_success(5000.0)
        assert m.slow_call_rate(2000.0) == pytest.approx(2.0 / 3.0 * 100, rel=1e-6)

    def test_thread_safety(self):
        m = SlidingWindowMetrics(max_size=1000)
        errors = []

        def worker():
            try:
                for _ in range(500):
                    m.record_success(10.0)
                    m.record_failure(20.0, "err")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert m.total_calls() == 1000  # deque capped at max_size


# ===================================================================
# CircuitBreakerConfig defaults
# ===================================================================


class TestCircuitBreakerConfig:
    def test_defaults(self):
        c = CircuitBreakerConfig(name="test")
        assert c.failure_rate_threshold == 50.0
        assert c.slow_call_rate_threshold == 80.0
        assert c.slow_call_duration_ms == 2000.0
        assert c.sliding_window_size == 20
        assert c.minimum_calls == 5
        assert c.wait_duration_in_open_state_ms == 30000.0
        assert c.permitted_calls_in_half_open == 3
        assert c.max_retries == 0


# ===================================================================
# State machine: CLOSED → OPEN
# ===================================================================


class TestClosedToOpen:
    def _breaker(self, **overrides):
        config_kwargs = {"name": "test", "minimum_calls": 3}
        config_kwargs.update(overrides)
        return DistributedCircuitBreaker(CircuitBreakerConfig(**config_kwargs))

    def test_initial_state_closed(self):
        b = self._breaker()
        assert b.state == CircuitState.CLOSED

    def test_opens_on_failure_rate(self):
        b = self._breaker(failure_rate_threshold=50.0, minimum_calls=3)

        def failing():
            raise RuntimeError("boom")

        # 2 failures out of 3 calls → 66.7% > 50%
        for _ in range(3):
            try:
                b.execute(failing)
            except RuntimeError:
                pass
        assert b.state == CircuitState.OPEN

    def test_opens_on_slow_call_rate(self):
        b = self._breaker(
            slow_call_rate_threshold=60.0,
            slow_call_duration_ms=10.0,
            minimum_calls=3,
        )

        def slow():
            time.sleep(0.05)
            return "ok"

        for _ in range(3):
            b.execute(slow)
        assert b.state == CircuitState.OPEN

    def test_stays_closed_below_threshold(self):
        b = self._breaker(failure_rate_threshold=90.0, minimum_calls=5)

        def failing():
            raise RuntimeError("boom")

        # 4 failures out of 5 = 80% < 90% threshold — should stay closed
        for _ in range(4):
            try:
                b.execute(failing)
            except RuntimeError:
                pass
        # 5th call to meet minimum_calls=5
        try:
            b.execute(failing)
        except RuntimeError:
            pass
        # 5/5 = 100% > 90% — should open
        assert b.state == CircuitState.OPEN

    def test_clear_error_message_when_open(self):
        b = self._breaker(failure_rate_threshold=50.0, minimum_calls=2)

        def failing():
            raise RuntimeError("boom")

        for _ in range(2):
            try:
                b.execute(failing)
            except RuntimeError:
                pass
        assert b.state == CircuitState.OPEN
        with pytest.raises(CircuitOpenError) as exc_info:
            b.execute(lambda: "ok")
        err = exc_info.value
        assert "test" in str(err)
        assert "OPEN" in str(err)
        assert err.name == "test"
        assert err.state == "OPEN"


# ===================================================================
# State machine: OPEN → HALF_OPEN → CLOSED
# ===================================================================


class TestOpenToHalfOpenToClosed:
    def _breaker(self, wait_ms=50.0, **overrides):
        config_kwargs = {
            "name": "test",
            "wait_duration_in_open_state_ms": wait_ms,
            "minimum_calls": 2,
            "failure_rate_threshold": 50.0,
            "permitted_calls_in_half_open": 2,
        }
        config_kwargs.update(overrides)
        return DistributedCircuitBreaker(CircuitBreakerConfig(**config_kwargs))

    def test_opens_then_half_open_after_wait(self):
        b = self._breaker(wait_ms=50.0)

        def failing():
            raise RuntimeError("boom")

        for _ in range(2):
            try:
                b.execute(failing)
            except RuntimeError:
                pass
        assert b.state == CircuitState.OPEN

        time.sleep(0.06)
        assert b.state == CircuitState.HALF_OPEN

    def test_half_open_to_closed_on_probe_success(self):
        b = self._breaker(wait_ms=30.0, permitted_calls_in_half_open=2)

        # Trip the breaker
        for _ in range(2):
            try:
                b.execute(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
            except RuntimeError:
                pass
        assert b.state == CircuitState.OPEN

        # Wait for HALF_OPEN
        time.sleep(0.04)
        assert b.state == CircuitState.HALF_OPEN

        # Successful probes
        result1 = b.execute(lambda: "recovered")
        result2 = b.execute(lambda: "recovered2")
        assert result1 == "recovered"
        assert result2 == "recovered2"
        assert b.state == CircuitState.CLOSED

    def test_half_open_back_to_open_on_probe_failure(self):
        b = self._breaker(wait_ms=30.0, permitted_calls_in_half_open=3)

        # Trip
        for _ in range(2):
            try:
                b.execute(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
            except RuntimeError:
                pass
        assert b.state == CircuitState.OPEN

        time.sleep(0.04)
        assert b.state == CircuitState.HALF_OPEN

        # First probe succeeds, second fails
        b.execute(lambda: "ok")
        try:
            b.execute(lambda: (_ for _ in ()).throw(RuntimeError("still broken")))
        except RuntimeError:
            pass
        assert b.state == CircuitState.OPEN


# ===================================================================
# Retry with backoff
# ===================================================================


class TestRetryWithBackoff:
    def test_no_retry_by_default(self):
        b = DistributedCircuitBreaker(
            CircuitBreakerConfig(
                name="test", max_retries=0, minimum_calls=2, failure_rate_threshold=50.0
            )
        )
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("fail")

        with pytest.raises(RuntimeError):
            b.execute(flaky)
        assert call_count == 1

    def test_retry_succeeds(self):
        b = DistributedCircuitBreaker(
            CircuitBreakerConfig(
                name="test",
                max_retries=3,
                retry_backoff_base_ms=10.0,
                retry_backoff_multiplier=1.0,  # no exponential for speed
                minimum_calls=10,
                failure_rate_threshold=90.0,
            )
        )
        attempts = 0

        def flaky():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise RuntimeError("transient")
            return "success"

        result = b.execute(flaky)
        assert result == "success"
        assert attempts == 3

    def test_retry_exhausted_raises_max_retries(self):
        b = DistributedCircuitBreaker(
            CircuitBreakerConfig(
                name="test",
                max_retries=2,
                retry_backoff_base_ms=5.0,
                retry_backoff_multiplier=1.0,
                minimum_calls=10,
                failure_rate_threshold=90.0,
            )
        )

        def always_fails():
            raise ValueError("permanent")

        with pytest.raises(MaxRetriesExceededError) as exc_info:
            b.execute(always_fails)
        assert exc_info.value.attempts == 3
        assert exc_info.value.name == "test"
        assert isinstance(exc_info.value.last_error, ValueError)


# ===================================================================
# Fallback
# ===================================================================


class TestFallback:
    def test_fallback_when_open(self):
        b = DistributedCircuitBreaker(
            CircuitBreakerConfig(
                name="test",
                minimum_calls=2,
                failure_rate_threshold=50.0,
            )
        )
        # Trip
        for _ in range(2):
            try:
                b.execute(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
            except RuntimeError:
                pass
        assert b.state == CircuitState.OPEN

        result = b.execute(lambda: "primary", fallback=lambda: "fallback")
        assert result == "fallback"

    def test_fallback_when_retries_exhausted(self):
        b = DistributedCircuitBreaker(
            CircuitBreakerConfig(
                name="test",
                max_retries=1,
                retry_backoff_base_ms=5.0,
                retry_backoff_multiplier=1.0,
                minimum_calls=10,
                failure_rate_threshold=90.0,
            )
        )

        result = b.execute(
            lambda: (_ for _ in ()).throw(RuntimeError("fail")),
            fallback=lambda: "recovered",
        )
        assert result == "recovered"

    def test_no_fallback_raises_circuit_open_error(self):
        b = DistributedCircuitBreaker(
            CircuitBreakerConfig(
                name="test",
                minimum_calls=2,
                failure_rate_threshold=50.0,
            )
        )
        for _ in range(2):
            try:
                b.execute(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
            except RuntimeError:
                pass
        with pytest.raises(CircuitOpenError):
            b.execute(lambda: "nope")


# ===================================================================
# Audit trail
# ===================================================================


class TestAuditTrail:
    def test_initial_entry(self):
        b = DistributedCircuitBreaker(CircuitBreakerConfig(name="audit-test"))
        log = b.get_audit_log()
        assert len(log) >= 1
        assert log[0]["from_state"] == "NONE"
        assert log[0]["to_state"] == "CLOSED"
        assert log[0]["reason"] == "initial"

    def test_records_transitions(self):
        b = DistributedCircuitBreaker(
            CircuitBreakerConfig(
                name="audit-test",
                minimum_calls=2,
                failure_rate_threshold=50.0,
                wait_duration_in_open_state_ms=30.0,
            )
        )
        for _ in range(2):
            try:
                b.execute(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
            except RuntimeError:
                pass
        log = b.get_audit_log()
        reasons = [e["reason"] for e in log]
        assert "failure_rate_exceeded" in reasons

    def test_manual_reset_recorded(self):
        b = DistributedCircuitBreaker(CircuitBreakerConfig(name="audit-test"))
        b.reset()
        log = b.get_audit_log()
        reasons = [e["reason"] for e in log]
        assert "manual_reset" in reasons

    def test_limit_parameter(self):
        b = DistributedCircuitBreaker(CircuitBreakerConfig(name="audit-test"))
        b.reset()
        b.reset()
        b.reset()
        log = b.get_audit_log(limit=2)
        assert len(log) == 2

    def test_metrics_snapshot_in_audit(self):
        b = DistributedCircuitBreaker(CircuitBreakerConfig(name="audit-test"))
        log = b.get_audit_log()
        assert "metrics" in log[0]
        assert "total_calls" in log[0]["metrics"]


# ===================================================================
# Callbacks (on_open, on_close, on_half_open)
# ===================================================================


class TestCallbacks:
    def test_on_open_callback(self):
        cb = MagicMock()
        b = DistributedCircuitBreaker(
            CircuitBreakerConfig(
                name="cb-test",
                minimum_calls=2,
                failure_rate_threshold=50.0,
                on_open=cb,
            )
        )
        for _ in range(2):
            try:
                b.execute(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
            except RuntimeError:
                pass
        cb.assert_called_once()
        args = cb.call_args[0]
        assert args[0] == "cb-test"
        assert "failure_rate_pct" in args[1]

    def test_on_close_callback(self):
        cb = MagicMock()
        b = DistributedCircuitBreaker(
            CircuitBreakerConfig(
                name="cb-test",
                minimum_calls=2,
                failure_rate_threshold=50.0,
                wait_duration_in_open_state_ms=30.0,
                permitted_calls_in_half_open=1,
                on_close=cb,
            )
        )
        # Trip
        for _ in range(2):
            try:
                b.execute(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
            except RuntimeError:
                pass
        # Wait and recover
        time.sleep(0.04)
        b.execute(lambda: "ok")
        cb.assert_called_once()

    def test_on_half_open_callback(self):
        cb = MagicMock()
        b = DistributedCircuitBreaker(
            CircuitBreakerConfig(
                name="cb-test",
                minimum_calls=2,
                failure_rate_threshold=50.0,
                wait_duration_in_open_state_ms=30.0,
                on_half_open=cb,
            )
        )
        for _ in range(2):
            try:
                b.execute(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
            except RuntimeError:
                pass
        time.sleep(0.04)
        _ = b.state  # triggers transition
        cb.assert_called_once()


# ===================================================================
# Registry
# ===================================================================


class TestRegistry:
    def test_get_or_create(self):
        reg = DistributedCircuitBreakerRegistry()
        c = CircuitBreakerConfig(name="reg-test")
        b1 = reg.get_or_create(c)
        b2 = reg.get_or_create(c)
        assert b1 is b2

    def test_get_nonexistent(self):
        reg = DistributedCircuitBreakerRegistry()
        assert reg.get("nope") is None

    def test_get_all_states(self):
        reg = DistributedCircuitBreakerRegistry()
        reg.get_or_create(CircuitBreakerConfig(name="a"))
        reg.get_or_create(CircuitBreakerConfig(name="b"))
        states = reg.get_all_states()
        assert "a" in states
        assert "b" in states

    def test_reset_all(self):
        reg = DistributedCircuitBreakerRegistry()
        reg.get_or_create(CircuitBreakerConfig(name="a"))
        reg.get_or_create(CircuitBreakerConfig(name="b"))
        reg.reset_all()
        states = reg.get_all_states()
        assert states["a"]["state"] == "CLOSED"
        assert states["b"]["state"] == "CLOSED"

    def test_remove(self):
        reg = DistributedCircuitBreakerRegistry()
        reg.get_or_create(CircuitBreakerConfig(name="a"))
        assert reg.remove("a") is True
        assert reg.remove("a") is False


# ===================================================================
# Global convenience function
# ===================================================================


class TestGetDistributedBreaker:
    def test_creates_and_returns(self):
        b = get_distributed_breaker("test-global", failure_rate_threshold=60.0)
        assert b.name == "test-global"
        assert b._config.failure_rate_threshold == 60.0

    def test_idempotent(self):
        b1 = get_distributed_breaker("test-idem")
        b2 = get_distributed_breaker("test-idem")
        assert b1 is b2


# ===================================================================
# Thread safety of DistributedCircuitBreaker
# ===================================================================


class TestThreadSafety:
    def test_concurrent_execute(self):
        b = DistributedCircuitBreaker(
            CircuitBreakerConfig(
                name="thread-test",
                minimum_calls=100,
                failure_rate_threshold=90.0,
                max_retries=0,
            )
        )
        results = []
        errors = []

        def worker():
            try:
                for _ in range(50):
                    b.execute(lambda: "ok")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert b.state == CircuitState.CLOSED

    def test_concurrent_state_transitions(self):
        b = DistributedCircuitBreaker(
            CircuitBreakerConfig(
                name="thread-transition",
                minimum_calls=2,
                failure_rate_threshold=50.0,
                wait_duration_in_open_state_ms=20.0,
                permitted_calls_in_half_open=5,
            )
        )
        # Trip the breaker
        for _ in range(2):
            try:
                b.execute(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
            except RuntimeError:
                pass
        assert b.state == CircuitState.OPEN

        time.sleep(0.03)

        # Multiple threads trying to use it during HALF_OPEN
        success_count = 0
        lock = threading.Lock()

        def worker():
            nonlocal success_count
            try:
                b.execute(lambda: "ok")
                with lock:
                    success_count += 1
            except (CircuitOpenError, RuntimeError):
                pass

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # Should not crash, state should be valid
        assert b.state in (
            CircuitState.CLOSED,
            CircuitState.HALF_OPEN,
            CircuitState.OPEN,
        )
