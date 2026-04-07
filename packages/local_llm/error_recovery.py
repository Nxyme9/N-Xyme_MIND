#!/usr/bin/env python3
"""Error Recovery — Retry with exponential backoff, max iterations, circuit breaker integration."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("local_llm.error_recovery")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    """Circuit breaker for fault tolerance.

    Tracks failures and opens circuit after threshold is reached.
    Allows periodic testing for recovery.
    """

    failure_threshold: int = 5
    recovery_timeout: float = 30.0  # seconds before trying half-open
    half_open_max_calls: int = 3

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _half_open_calls: int = field(default=0, init=False)

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, auto-transitioning if needed."""
        now = time.time()

        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if now - self._last_failure_time >= self.recovery_timeout:
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0

        return self._state

    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.OPEN:
            return False
        # HALF_OPEN - allow limited calls
        return self._half_open_calls < self.half_open_max_calls

    def record_success(self) -> None:
        """Record successful execution."""
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                logger.info("Circuit breaker recovered - CLOSED")
                self._state = CircuitState.CLOSED
                self._failure_count = 0
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record failed execution."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            logger.warning("Circuit breaker test failed - OPEN")
            self._state = CircuitState.OPEN
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                logger.warning(
                    f"Circuit breaker opened after {self._failure_count} failures"
                )
                self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
        self._last_failure_time = 0.0


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 30.0  # seconds
    exponential_base: float = 2.0
    use_jitter: bool = True


class ErrorRecovery:
    """Error recovery with retry and circuit breaker.

    Combines exponential backoff retry with circuit breaker pattern
    for resilient LLM operations.
    """

    def __init__(
        self,
        config: Optional[RetryConfig] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        self.config = config or RetryConfig()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt with optional jitter."""
        delay = self.config.base_delay * (self.config.exponential_base**attempt)
        delay = min(delay, self.config.max_delay)

        if self.config.use_jitter:
            # Add random jitter between 0-25% of delay
            import random

            delay = delay * (0.75 + random.random() * 0.25)

        return delay

    def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute function with retry and circuit breaker.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from successful execution

        Raises:
            Exception: Last exception if all retries exhausted
        """
        if not self.circuit_breaker.can_execute():
            raise CircuitBreakerOpenError(
                f"Circuit breaker is {self.circuit_breaker.state.value}"
            )

        last_error: Optional[Exception] = None

        for attempt in range(self.config.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                self.circuit_breaker.record_success()
                return result

            except Exception as e:
                last_error = e
                self.circuit_breaker.record_failure()

                if attempt < self.config.max_retries:
                    # Check circuit breaker before retrying
                    if not self.circuit_breaker.can_execute():
                        raise CircuitBreakerOpenError(
                            f"Circuit breaker opened during retry"
                        )

                    delay = self.calculate_delay(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.config.max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.config.max_retries + 1} attempts failed")

        if last_error:
            raise last_error
        raise RuntimeError("Unexpected: no error but no result")

    async def execute_async(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Async version of execute with retry and circuit breaker."""
        import asyncio

        if not self.circuit_breaker.can_execute():
            raise CircuitBreakerOpenError(
                f"Circuit breaker is {self.circuit_breaker.state.value}"
            )

        last_error: Optional[Exception] = None

        for attempt in range(self.config.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                self.circuit_breaker.record_success()
                return result

            except Exception as e:
                last_error = e
                self.circuit_breaker.record_failure()

                if attempt < self.config.max_retries:
                    if not self.circuit_breaker.can_execute():
                        raise CircuitBreakerOpenError(
                            f"Circuit breaker opened during retry"
                        )

                    delay = self.calculate_delay(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)

        if last_error:
            raise last_error
        raise RuntimeError("Unexpected: no error but no result")


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and execution is blocked."""

    pass


# Global error recovery instance
_default_recovery: Optional[ErrorRecovery] = None


def get_default_recovery() -> ErrorRecovery:
    """Get or create default ErrorRecovery instance."""
    global _default_recovery
    if _default_recovery is None:
        _default_recovery = ErrorRecovery()
    return _default_recovery


def execute_with_retry(
    func: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Convenience function to execute with default retry settings."""
    return get_default_recovery().execute(func, *args, **kwargs)
