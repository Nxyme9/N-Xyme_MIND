"""
Circuit Breaker — Fault tolerance for service calls (ported from SPINE)

Prevents cascading failures by stopping calls to failing services.

Usage:
    breaker = CircuitBreaker("ollama", failure_threshold=3, reset_timeout=60)
    try:
        result = breaker.call(make_ollama_request)
    except CircuitBreakerOpen:
        print("Service unavailable")
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Service failing, block calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""

    pass


@dataclass
class CircuitBreaker:
    """Circuit breaker for fault tolerance."""

    name: str
    failure_threshold: int = 3
    reset_timeout: float = 60.0  # seconds
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0
    success_count: int = 0
    total_calls: int = 0

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        self.total_calls += 1

        # Check if circuit is open
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info(f"CircuitBreaker[{self.name}]: Entering HALF_OPEN")
            else:
                raise CircuitBreakerOpen(f"Circuit breaker '{self.name}' is OPEN")

        try:
            result = func(*args, **kwargs)

            # Success - reset failure count
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"CircuitBreaker[{self.name}]: Recovered, CLOSED")
            elif self.state == CircuitState.CLOSED:
                self.failure_count = max(0, self.failure_count - 1)

            self.success_count += 1
            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.error(f"CircuitBreaker[{self.name}]: OPEN ({self.failure_count} failures)")

            raise

    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "success_count": self.success_count,
            "total_calls": self.total_calls,
            "last_failure": self.last_failure_time,
        }

    def reset(self):
        """Manually reset circuit breaker."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        logger.info(f"CircuitBreaker[{self.name}]: Manually reset")


class CircuitBreakerRegistry:
    """Registry for multiple circuit breakers."""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 3,
        reset_timeout: float = 60.0,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                reset_timeout=reset_timeout,
            )
        return self._breakers[name]

    def get_all_states(self) -> Dict[str, Dict]:
        """Get states of all circuit breakers."""
        return {name: b.get_state() for name, b in self._breakers.items()}

    def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()


# Global registry
_global_registry = CircuitBreakerRegistry()


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Get a circuit breaker from global registry."""
    return _global_registry.get_or_create(name, **kwargs)
