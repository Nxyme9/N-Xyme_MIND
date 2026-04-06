"""
Distributed Circuit Breaker — Resilience4j/Netflix Hystrix patterns for N-Xyme MIND

Implements sliding window metrics, state machine transitions, configurable thresholds,
recovery actions, and audit trail for distributed fault tolerance.

State Machine: CLOSED → OPEN → HALF_OPEN → CLOSED
  CLOSED:    Normal operation, tracking metrics in sliding window
  OPEN:      Circuit tripped, all calls rejected immediately
  HALF_OPEN: Testing recovery, limited probe calls allowed

MIT-licensed patterns only. Thread-safe. Python 3.10+.

Usage:
    config = CircuitBreakerConfig(
        name="ollama",
        failure_rate_threshold=50.0,
        slow_call_rate_threshold=80.0,
        slow_call_duration_ms=2000,
        sliding_window_size=20,
        minimum_calls=5,
        wait_duration_in_open_state_ms=30000,
        permitted_calls_in_half_open=3,
    )
    breaker = DistributedCircuitBreaker(config)

    try:
        result = breaker.execute(lambda: call_ollama())
    except CircuitOpenError:
        # Circuit is open, use fallback
        result = fallback_response()
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CircuitOpenError(Exception):
    """Raised when circuit breaker is OPEN and rejecting calls."""

    def __init__(self, name: str, state: str, wait_remaining_ms: float = 0):
        self.name = name
        self.state = state
        self.wait_remaining_ms = wait_remaining_ms
        msg = (
            f"CircuitBreaker[{name}] is {state}"
            f"{f', retry after {wait_remaining_ms:.0f}ms' if wait_remaining_ms > 0 else ''}"
        )
        super().__init__(msg)


class MaxRetriesExceededError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, name: str, attempts: int, last_error: Exception):
        self.name = name
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"CircuitBreaker[{name}] exhausted {attempts} retries: {last_error}"
        )


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class StateTransitionReason(Enum):
    INITIAL = "initial"
    FAILURE_RATE_EXCEEDED = "failure_rate_exceeded"
    SLOW_CALL_RATE_EXCEEDED = "slow_call_rate_exceeded"
    RECOVERY_PROBE_SUCCESS = "recovery_probe_success"
    RECOVERY_PROBE_FAILED = "recovery_probe_failed"
    MANUAL_RESET = "manual_reset"
    HALF_OPEN_PROBE_GRANTED = "half_open_probe_granted"


# ---------------------------------------------------------------------------
# Audit record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuditEntry:
    timestamp: float
    breaker_name: str
    from_state: str
    to_state: str
    reason: str
    metrics_snapshot: Dict[str, Any]


# ---------------------------------------------------------------------------
# Sliding window metrics
# ---------------------------------------------------------------------------


@dataclass
class CallRecord:
    """Single call observation stored in the sliding window."""

    timestamp: float
    duration_ms: float
    success: bool
    error: Optional[str] = None


class SlidingWindowMetrics:
    """Thread-safe sliding window tracking call success/failure and latency."""

    def __init__(self, max_size: int = 100) -> None:
        self._max_size = max_size
        self._records: deque[CallRecord] = deque(maxlen=max_size)
        self._lock = threading.Lock()

    # -- mutations ----------------------------------------------------------

    def record_success(self, duration_ms: float) -> None:
        with self._lock:
            self._records.append(
                CallRecord(timestamp=time.time(), duration_ms=duration_ms, success=True)
            )

    def record_failure(self, duration_ms: float, error: str) -> None:
        with self._lock:
            self._records.append(
                CallRecord(
                    timestamp=time.time(),
                    duration_ms=duration_ms,
                    success=False,
                    error=error,
                )
            )

    # -- queries (snapshot under lock) --------------------------------------

    def total_calls(self) -> int:
        with self._lock:
            return len(self._records)

    def failure_rate(self) -> float:
        with self._lock:
            if not self._records:
                return 0.0
            failures = sum(1 for r in self._records if not r.success)
            return (failures / len(self._records)) * 100.0

    def slow_call_rate(self, threshold_ms: float) -> float:
        with self._lock:
            if not self._records:
                return 0.0
            slow = sum(1 for r in self._records if r.duration_ms > threshold_ms)
            return (slow / len(self._records)) * 100.0

    def avg_response_time_ms(self) -> float:
        with self._lock:
            if not self._records:
                return 0.0
            total = sum(r.duration_ms for r in self._records)
            return total / len(self._records)

    def snapshot(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of current metrics."""
        with self._lock:
            records = list(self._records)
        total = len(records)
        failures = sum(1 for r in records if not r.success)
        durations = [r.duration_ms for r in records]
        return {
            "total_calls": total,
            "failure_count": failures,
            "failure_rate_pct": (failures / total * 100.0) if total else 0.0,
            "avg_response_time_ms": (sum(durations) / total) if total else 0.0,
            "max_response_time_ms": max(durations) if durations else 0.0,
            "min_response_time_ms": min(durations) if durations else 0.0,
        }


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class CircuitBreakerConfig:
    """Configuration for a single circuit breaker instance.

    Mirrors Resilience4j defaults where sensible.
    """

    name: str

    # Thresholds
    failure_rate_threshold: float = 50.0  # % failures before opening
    slow_call_rate_threshold: float = 80.0  # % slow calls before opening
    slow_call_duration_ms: float = 2000.0  # ms threshold for "slow"

    # Sliding window
    sliding_window_size: int = 20  # max records in window
    minimum_calls: int = 5  # min calls before evaluating thresholds

    # State machine timing
    wait_duration_in_open_state_ms: float = 30000  # how long to stay OPEN
    permitted_calls_in_half_open: int = 3  # probe calls allowed in HALF_OPEN

    # Retry / recovery
    max_retries: int = 0  # 0 = no automatic retry
    retry_backoff_base_ms: float = 500.0  # base backoff for retries
    retry_backoff_multiplier: float = 2.0  # multiplier per retry

    # Recovery action hooks (populated at runtime)
    on_open: Optional[Callable[[str, Dict], None]] = None  # callback when circuit opens
    on_close: Optional[Callable[[str, Dict], None]] = (
        None  # callback when circuit closes
    )
    on_half_open: Optional[Callable[[str, Dict], None]] = None  # callback on half-open


# ---------------------------------------------------------------------------
# Distributed Circuit Breaker
# ---------------------------------------------------------------------------


class DistributedCircuitBreaker:
    """Thread-safe circuit breaker with sliding window metrics and audit trail.

    State transitions:
        CLOSED → OPEN       when failure_rate or slow_call_rate exceeds threshold
        OPEN → HALF_OPEN    after wait_duration_in_open_state_ms elapses
        HALF_OPEN → CLOSED  when all permitted probe calls succeed
        HALF_OPEN → OPEN    when any probe call fails
    """

    def __init__(self, config: CircuitBreakerConfig) -> None:
        self._config = config
        self._state = CircuitState.CLOSED
        self._metrics = SlidingWindowMetrics(max_size=config.sliding_window_size)
        self._audit_log: List[AuditEntry] = []
        self._lock = threading.RLock()

        # HALF_OPEN probe accounting
        self._half_open_calls_granted = 0
        self._half_open_calls_in_flight = 0

        # OPEN state timing
        self._opened_at: float = 0.0

        # Initial audit entry
        self._append_audit(
            from_state="NONE",
            to_state=CircuitState.CLOSED.value,
            reason=StateTransitionReason.INITIAL.value,
        )

    # -- public API ---------------------------------------------------------

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._check_open_timeout()
            return self._state

    def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        fallback: Optional[Callable[..., Any]] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute *func* through the circuit breaker.

        Parameters
        ----------
        func :
            The protected callable.
        fallback :
            Optional fallback called when circuit is OPEN or all retries exhausted.

        Returns
        -------
        Return value of *func* (or *fallback*).

        Raises
        ------
        CircuitOpenError :
            When circuit is OPEN and no fallback is provided.
        MaxRetriesExceededError :
            When retries are exhausted and no fallback is provided.
        """
        # --- check state (may raise CircuitOpenError) ---
        if not self._try_enter():
            if fallback is not None:
                logger.warning("CircuitBreaker[%s] OPEN — invoking fallback", self.name)
                return fallback(*args, **kwargs)
            with self._lock:
                wait = self._remaining_open_ms()
            raise CircuitOpenError(self.name, self._state.value, wait)

        # --- execute with retries ---
        last_error: Optional[Exception] = None
        max_attempts = max(1, self._config.max_retries + 1)

        for attempt in range(max_attempts):
            if attempt > 0:
                backoff = self._backoff_ms(attempt)
                logger.info(
                    "CircuitBreaker[%s] retry %d/%d, backing off %.0fms",
                    self.name,
                    attempt,
                    self._config.max_retries,
                    backoff,
                )
                time.sleep(backoff / 1000.0)

            start = time.monotonic()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.monotonic() - start) * 1000.0
                self._on_success(duration_ms)
                return result
            except Exception as exc:
                duration_ms = (time.monotonic() - start) * 1000.0
                self._on_failure(duration_ms, str(exc))
                last_error = exc

        # All retries exhausted — re-raise original if no retries were configured
        if self._config.max_retries == 0:
            raise last_error  # type: ignore[misc]

        if fallback is not None:
            logger.warning(
                "CircuitBreaker[%s] retries exhausted — invoking fallback", self.name
            )
            return fallback(*args, **kwargs)

        raise MaxRetriesExceededError(self.name, max_attempts, last_error)  # type: ignore[arg-type]

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED."""
        with self._lock:
            old = self._state
            self._state = CircuitState.CLOSED
            self._half_open_calls_granted = 0
            self._half_open_calls_in_flight = 0
            self._append_audit(
                from_state=old.value,
                to_state=CircuitState.CLOSED.value,
                reason=StateTransitionReason.MANUAL_RESET.value,
            )
            logger.info("CircuitBreaker[%s] manually reset to CLOSED", self.name)
            if self._config.on_close:
                self._config.on_close(self.name, self._metrics.snapshot())

    def get_state(self) -> Dict[str, Any]:
        """Return full state + metrics snapshot."""
        with self._lock:
            self._check_open_timeout()
            return {
                "name": self.name,
                "state": self._state.value,
                "metrics": self._metrics.snapshot(),
                "config": {
                    "failure_rate_threshold": self._config.failure_rate_threshold,
                    "slow_call_rate_threshold": self._config.slow_call_rate_threshold,
                    "slow_call_duration_ms": self._config.slow_call_duration_ms,
                    "sliding_window_size": self._config.sliding_window_size,
                    "minimum_calls": self._config.minimum_calls,
                    "wait_duration_ms": self._config.wait_duration_in_open_state_ms,
                    "permitted_half_open_calls": self._config.permitted_calls_in_half_open,
                    "max_retries": self._config.max_retries,
                },
            }

    def get_audit_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent audit entries (most recent first)."""
        with self._lock:
            entries = self._audit_log[-limit:]
        return [
            {
                "timestamp": e.timestamp,
                "breaker_name": e.breaker_name,
                "from_state": e.from_state,
                "to_state": e.to_state,
                "reason": e.reason,
                "metrics": e.metrics_snapshot,
            }
            for e in reversed(entries)
        ]

    # -- internal: state machine --------------------------------------------

    def _check_open_timeout(self) -> None:
        """If OPEN and wait duration elapsed, transition to HALF_OPEN.

        Must be called under _lock.
        """
        if self._state == CircuitState.OPEN:
            elapsed_ms = (time.time() - self._opened_at) * 1000.0
            if elapsed_ms >= self._config.wait_duration_in_open_state_ms:
                self._transition_to(
                    CircuitState.HALF_OPEN,
                    StateTransitionReason.HALF_OPEN_PROBE_GRANTED,
                )

    def _try_enter(self) -> bool:
        """Check if a call is permitted. Returns True if allowed.

        Must be called under _lock.
        """
        self._check_open_timeout()

        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.HALF_OPEN:
            if (
                self._half_open_calls_granted
                < self._config.permitted_calls_in_half_open
            ):
                self._half_open_calls_granted += 1
                self._half_open_calls_in_flight += 1
                return True
            return False

        # OPEN
        return False

    def _on_success(self, duration_ms: float) -> None:
        """Record a successful call. May trigger state transition."""
        self._metrics.record_success(duration_ms)
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls_in_flight = max(
                    0, self._half_open_calls_in_flight - 1
                )
                # If all permitted probes succeeded, close the circuit
                if (
                    self._half_open_calls_granted
                    >= self._config.permitted_calls_in_half_open
                    and self._half_open_calls_in_flight == 0
                ):
                    self._transition_to(
                        CircuitState.CLOSED,
                        StateTransitionReason.RECOVERY_PROBE_SUCCESS,
                    )
            elif self._state == CircuitState.CLOSED:
                self._evaluate_thresholds()

    def _on_failure(self, duration_ms: float, error: str) -> None:
        """Record a failed call. May trigger state transition."""
        self._metrics.record_failure(duration_ms, error)
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls_in_flight = max(
                    0, self._half_open_calls_in_flight - 1
                )
                # Any failure in HALF_OPEN → back to OPEN
                self._transition_to(
                    CircuitState.OPEN,
                    StateTransitionReason.RECOVERY_PROBE_FAILED,
                )
                return

            if self._state == CircuitState.CLOSED:
                self._evaluate_thresholds()

    def _evaluate_thresholds(self) -> None:
        """Check if thresholds are breached in CLOSED state.

        Must be called under _lock.
        """
        total = self._metrics.total_calls()
        if total < self._config.minimum_calls:
            return

        failure_rate = self._metrics.failure_rate()
        if failure_rate >= self._config.failure_rate_threshold:
            self._transition_to(
                CircuitState.OPEN,
                StateTransitionReason.FAILURE_RATE_EXCEEDED,
            )
            return

        slow_rate = self._metrics.slow_call_rate(self._config.slow_call_duration_ms)
        if slow_rate >= self._config.slow_call_rate_threshold:
            self._transition_to(
                CircuitState.OPEN,
                StateTransitionReason.SLOW_CALL_RATE_EXCEEDED,
            )

    def _transition_to(
        self, new_state: CircuitState, reason: StateTransitionReason
    ) -> None:
        """Perform a state transition with audit logging.

        Must be called under _lock.
        """
        old = self._state
        if old == new_state:
            return

        self._state = new_state
        if new_state == CircuitState.OPEN:
            self._opened_at = time.time()

        snapshot = self._metrics.snapshot()
        self._append_audit(
            from_state=old.value,
            to_state=new_state.value,
            reason=reason.value,
        )
        logger.info(
            "CircuitBreaker[%s] %s → %s (%s)",
            self.name,
            old.value,
            new_state.value,
            reason.value,
        )

        # Fire callbacks
        if new_state == CircuitState.OPEN and self._config.on_open:
            self._config.on_open(self.name, snapshot)
        elif new_state == CircuitState.CLOSED and self._config.on_close:
            self._config.on_close(self.name, snapshot)
        elif new_state == CircuitState.HALF_OPEN and self._config.on_half_open:
            self._config.on_half_open(self.name, snapshot)

    # -- internal: helpers --------------------------------------------------

    def _remaining_open_ms(self) -> float:
        """Milliseconds remaining before OPEN → HALF_OPEN transition."""
        if self._state != CircuitState.OPEN:
            return 0.0
        elapsed_ms = (time.time() - self._opened_at) * 1000.0
        return max(0.0, self._config.wait_duration_in_open_state_ms - elapsed_ms)

    def _backoff_ms(self, attempt: int) -> float:
        """Exponential backoff in milliseconds for retry *attempt* (1-based)."""
        return self._config.retry_backoff_base_ms * (
            self._config.retry_backoff_multiplier ** (attempt - 1)
        )

    def _append_audit(self, from_state: str, to_state: str, reason: str) -> None:
        """Append an audit entry. Must be called under _lock."""
        self._audit_log.append(
            AuditEntry(
                timestamp=time.time(),
                breaker_name=self.name,
                from_state=from_state,
                to_state=to_state,
                reason=reason,
                metrics_snapshot=self._metrics.snapshot(),
            )
        )


# ---------------------------------------------------------------------------
# Registry — manages multiple breakers (drop-in for existing registry)
# ---------------------------------------------------------------------------


class DistributedCircuitBreakerRegistry:
    """Thread-safe registry for named circuit breakers."""

    def __init__(self) -> None:
        self._breakers: Dict[str, DistributedCircuitBreaker] = {}
        self._lock = threading.Lock()

    def get_or_create(self, config: CircuitBreakerConfig) -> DistributedCircuitBreaker:
        with self._lock:
            if config.name not in self._breakers:
                self._breakers[config.name] = DistributedCircuitBreaker(config)
            return self._breakers[config.name]

    def get(self, name: str) -> Optional[DistributedCircuitBreaker]:
        with self._lock:
            return self._breakers.get(name)

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {name: b.get_state() for name, b in self._breakers.items()}

    def reset_all(self) -> None:
        with self._lock:
            for b in self._breakers.values():
                b.reset()

    def remove(self, name: str) -> bool:
        with self._lock:
            return self._breakers.pop(name, None) is not None


# ---------------------------------------------------------------------------
# Global registry — convenience for existing AGENTS.md circuit breakers
# ---------------------------------------------------------------------------

_global_registry = DistributedCircuitBreakerRegistry()


def get_distributed_breaker(
    name: str,
    *,
    failure_rate_threshold: float = 50.0,
    slow_call_rate_threshold: float = 80.0,
    slow_call_duration_ms: float = 2000.0,
    sliding_window_size: int = 20,
    minimum_calls: int = 5,
    wait_duration_in_open_state_ms: float = 30000.0,
    permitted_calls_in_half_open: int = 3,
    max_retries: int = 0,
    retry_backoff_base_ms: float = 500.0,
    retry_backoff_multiplier: float = 2.0,
    on_open: Optional[Callable[[str, Dict], None]] = None,
    on_close: Optional[Callable[[str, Dict], None]] = None,
    on_half_open: Optional[Callable[[str, Dict], None]] = None,
) -> DistributedCircuitBreaker:
    """Get or create a distributed circuit breaker from the global registry.

    Maps to the 8 existing circuit breakers in AGENTS.md:
      - token-budget, step-limit, timeout, failure-limit,
        stuck-detection, trigger-budget, attempt-counter, progress-check
    """
    config = CircuitBreakerConfig(
        name=name,
        failure_rate_threshold=failure_rate_threshold,
        slow_call_rate_threshold=slow_call_rate_threshold,
        slow_call_duration_ms=slow_call_duration_ms,
        sliding_window_size=sliding_window_size,
        minimum_calls=minimum_calls,
        wait_duration_in_open_state_ms=wait_duration_in_open_state_ms,
        permitted_calls_in_half_open=permitted_calls_in_half_open,
        max_retries=max_retries,
        retry_backoff_base_ms=retry_backoff_base_ms,
        retry_backoff_multiplier=retry_backoff_multiplier,
        on_open=on_open,
        on_close=on_close,
        on_half_open=on_half_open,
    )
    return _global_registry.get_or_create(config)
