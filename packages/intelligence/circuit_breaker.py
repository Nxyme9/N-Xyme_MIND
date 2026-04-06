"""Circuit Breaker Pattern

Implements circuit breaker pattern for model failure detection and recovery.
State machine: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
"""

import time
import json
import logging
import threading
from typing import Dict, Optional
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("circuit-breaker")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 3
    recovery_timeout_seconds: int = 120
    half_open_max_requests: int = 1


class CircuitBreaker:
    """Circuit breaker for a specific model."""

    def __init__(self, model_name: str, config: CircuitBreakerConfig):
        self.model_name = model_name
        self.config = config
        self._state = CircuitState.CLOSED
        self._failure_count: int = 0
        self._last_failure_time: Optional[float] = None
        self._last_success_time: Optional[float] = None
        self._half_open_requests = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    def record_success(self) -> None:
        """Record a successful execution.

        Resets failure counter and transitions to CLOSED if currently in HALF_OPEN.
        """
        with self._lock:
            now = time.time()
            self._last_success_time = now
            self._failure_count = 0
            self._half_open_requests = 0

            if self._state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.CLOSED)
            elif self._state == CircuitState.CLOSED:
                logger.debug(f"Circuit for '{self.model_name}' success recorded")

    def record_failure(self) -> None:
        """Record a failed execution.

        Increments failure counter and transitions to OPEN if threshold reached.
        """
        with self._lock:
            now = time.time()
            self._last_failure_time = now
            self._failure_count += 1

            if self._state == CircuitState.HALF_OPEN:
                logger.warning(
                    f"Circuit for '{self.model_name}' failed in HALF_OPEN, reopening"
                )
                self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    logger.warning(
                        f"Circuit for '{self.model_name}' threshold reached ({self._failure_count}), opening"
                    )
                    self._transition_to(CircuitState.OPEN)
                else:
                    logger.debug(
                        f"Circuit for '{self.model_name}' failure {self._failure_count}/{self.config.failure_threshold}"
                    )
            elif self._state == CircuitState.OPEN:
                # Already open, just log
                logger.debug(
                    f"Circuit for '{self.model_name}' failure while already OPEN"
                )

    def can_execute(self) -> bool:
        """Check if execution is allowed.

        Returns True if:
        - State is CLOSED, or
        - State is HALF_OPEN with available capacity

        Returns False if state is OPEN (or OPEN waiting for recovery timeout).
        """
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if self._last_failure_time:
                    if (
                        time.time() - self._last_failure_time
                        >= self.config.recovery_timeout_seconds
                    ):
                        logger.info(
                            f"Circuit for '{self.model_name}' timeout expired, transitioning to HALF_OPEN"
                        )
                        self._transition_to(CircuitState.HALF_OPEN)
                        return self._half_open_capacity() > 0
                return False

            elif self._state == CircuitState.HALF_OPEN:
                return self._half_open_capacity() > 0

            return True  # CLOSED

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            # Auto-transition OPEN -> HALF_OPEN on timeout
            if self._state == CircuitState.OPEN and self._last_failure_time:
                if (
                    time.time() - self._last_failure_time
                    >= self.config.recovery_timeout_seconds
                ):
                    self._transition_to(CircuitState.HALF_OPEN)
            return self._state

    def get_state_info(self) -> Dict:
        """Get full state as dictionary."""
        with self._lock:
            return {
                "model_name": self.model_name,
                "state": self._state.value,
                "failures": self._failure_count,
                "failure_threshold": self.config.failure_threshold,
                "last_failure": self._last_failure_time,
                "last_success": self._last_success_time,
                "can_execute": self._can_execute_unlocked(),
                "half_open_capacity": self._half_open_capacity_unlocked(),
            }

    def _can_execute_unlocked(self) -> bool:
        """Check if can execute (must be called with lock held)."""
        if self._state == CircuitState.OPEN:
            if self._last_failure_time:
                if (
                    time.time() - self._last_failure_time
                    >= self.config.recovery_timeout_seconds
                ):
                    return self._half_open_capacity_unlocked() > 0
            return False
        elif self._state == CircuitState.HALF_OPEN:
            return self._half_open_capacity_unlocked() > 0
        return True

    def _transition_to(self, new_state: CircuitState) -> None:
        """Handle state transition with logging."""
        old_state = self._state
        self._state = new_state

        if old_state != new_state:
            logger.info(
                f"Circuit for '{self.model_name}' transitioned: {old_state.value} -> {new_state.value}"
            )

            if new_state == CircuitState.HALF_OPEN:
                self._half_open_requests = 0

    def _half_open_capacity(self) -> int:
        """Get remaining requests allowed in HALF_OPEN state (thread-safe)."""
        with self._lock:
            return self._half_open_capacity_unlocked()

    def _half_open_capacity_unlocked(self) -> int:
        """Get remaining requests allowed in HALF_OPEN state (must be called with lock held)."""
        if self._state != CircuitState.HALF_OPEN:
            return 0
        return max(0, self.config.half_open_max_requests - self._half_open_requests)

    def _consume_half_open_slot(self) -> bool:
        """Consume a half-open slot if available. Returns True if consumed."""
        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_requests < self.config.half_open_max_requests:
                self._half_open_requests += 1
                return True
        return False

    def reset(self) -> None:
        """Force reset circuit to CLOSED state."""
        with self._lock:
            self._transition_to(CircuitState.CLOSED)
            self._failure_count = 0
            self._half_open_requests = 0
            logger.info(f"Circuit for '{self.model_name}' manually reset to CLOSED")


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    def __init__(self, config_path: str = "configs/model_router.json"):
        self.config_path = Path(config_path)
        self.state_file = Path(".sisyphus/circuit_breakers.json")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._config = self._load_config()
        self._lock = threading.Lock()
        self._load_state()

    def _load_config(self) -> CircuitBreakerConfig:
        """Load circuit breaker configuration from JSON."""
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    data = json.load(f)

                cb_config = data.get("circuit_breaker", {})
                return CircuitBreakerConfig(
                    failure_threshold=cb_config.get("failure_threshold", 3),
                    recovery_timeout_seconds=cb_config.get(
                        "recovery_timeout_seconds", 120
                    ),
                    half_open_max_requests=cb_config.get("half_open_max_requests", 1),
                )
            except Exception as e:
                logger.warning(
                    f"Error loading circuit breaker config: {e}, using defaults"
                )

        return CircuitBreakerConfig()

    def _load_state(self):
        """Load saved circuit breaker state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)

                for model_name, state_data in data.items():
                    config = CircuitBreakerConfig(
                        failure_threshold=state_data.get(
                            "failure_threshold", self._config.failure_threshold
                        ),
                        recovery_timeout_seconds=state_data.get(
                            "recovery_timeout_seconds",
                            self._config.recovery_timeout_seconds,
                        ),
                        half_open_max_requests=state_data.get(
                            "half_open_max_requests",
                            self._config.half_open_max_requests,
                        ),
                    )
                    breaker = CircuitBreaker(model_name, config)
                    breaker._state = CircuitState(state_data.get("state", "closed"))
                    breaker._failure_count = state_data.get("failure_count", 0)
                    breaker._last_failure_time = state_data.get("last_failure_time")
                    breaker._last_success_time = state_data.get("last_success_time")
                    breaker._half_open_requests = state_data.get(
                        "half_open_requests", 0
                    )
                    self._breakers[model_name] = breaker

                logger.info(
                    f"Loaded {len(self._breakers)} circuit breakers from state file"
                )
            except Exception as e:
                logger.warning(f"Error loading circuit breaker state: {e}")

    def _save_state(self):
        """Save circuit breaker state to file."""
        data = {}
        for model_name, breaker in self._breakers.items():
            with breaker._lock:
                data[model_name] = {
                    "state": breaker._state.value,
                    "failure_count": breaker._failure_count,
                    "last_failure_time": breaker._last_failure_time,
                    "last_success_time": breaker._last_success_time,
                    "half_open_requests": breaker._half_open_requests,
                    "failure_threshold": breaker.config.failure_threshold,
                    "recovery_timeout_seconds": breaker.config.recovery_timeout_seconds,
                    "half_open_max_requests": breaker.config.half_open_max_requests,
                }

        with open(self.state_file, "w") as f:
            json.dump(data, f, indent=2)

    def get_breaker(self, model_name: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a model."""
        with self._lock:
            if model_name not in self._breakers:
                self._breakers[model_name] = CircuitBreaker(model_name, self._config)
                logger.debug(f"Created new circuit breaker for '{model_name}'")
            return self._breakers[model_name]

    def record_success(self, model_name: str) -> None:
        """Record success for a model."""
        breaker = self.get_breaker(model_name)
        breaker.record_success()
        self._save_state()

    def record_failure(self, model_name: str) -> None:
        """Record failure for a model."""
        breaker = self.get_breaker(model_name)
        breaker.record_failure()
        self._save_state()

    def can_execute(self, model_name: str) -> bool:
        """Check if model can execute."""
        breaker = self.get_breaker(model_name)
        return breaker.can_execute()

    def get_all_states(self) -> Dict:
        """Get state info for all breakers."""
        with self._lock:
            return {
                model_name: breaker.get_state_info()
                for model_name, breaker in self._breakers.items()
            }

    def reset(self, model_name: str) -> None:
        """Reset a specific breaker to CLOSED."""
        breaker = self.get_breaker(model_name)
        breaker.reset()
        self._save_state()

    def reset_all(self) -> None:
        """Reset all breakers to CLOSED."""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()
            self._save_state()
            logger.info("All circuit breakers reset to CLOSED")


# Global registry instance
_registry: Optional[CircuitBreakerRegistry] = None
_registry_lock = threading.Lock()


def get_circuit_breaker_registry(
    config_path: str = "configs/model_router.json",
) -> CircuitBreakerRegistry:
    """Get or create the global circuit breaker registry."""
    global _registry

    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = CircuitBreakerRegistry(config_path)

    return _registry
