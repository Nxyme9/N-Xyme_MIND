"""
Circuit Breaker — Exponential backoff with state persistence.

Tracks per-model failure counts and enforces backoff delays.
State is persisted to .cache/circuit-breaker.json for cross-session recovery.

Usage:
    cb = CircuitBreaker()
    cb.record_failure("model-1")
    if cb.is_available("model-1"):
        ...
    cb.record_success("model-1")
"""

import fcntl
import json
import logging
import os
import random
import threading
import time

from enum import Enum

logger = logging.getLogger(__name__)


class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker pattern for model fallback with per-model tracking."""

    def __init__(
        self,
        failure_threshold: int = 3,
        reset_timeout: int = 300,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        state_file: str = ".cache/circuit-breaker.json",
        half_open_max_calls: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.state_file = state_file
        self.half_open_max_calls = half_open_max_calls
        self.failures: dict[str, int] = {}
        self.last_failure_time: dict[str, float] = {}
        self._states: dict[str, State] = {}
        self._half_open_calls: dict[str, int] = {}
        self._lock = threading.Lock()
        self._load_state()

    def get_delay(self, failure_count: int) -> float:
        """Calculate exponential backoff delay with optional jitter."""
        delay = min(self.base_delay * (2**failure_count), self.max_delay)
        if self.jitter:
            delay *= 1 + random.uniform(0, 0.5)
        return delay

    def record_failure(self, model: str) -> None:
        """Record a failure for a model."""
        with self._lock:
            current_state = self._states.get(model, State.CLOSED)
            if current_state == State.HALF_OPEN:
                self._states[model] = State.OPEN
                self.last_failure_time[model] = time.time()
                delay = self.get_delay(self.failures.get(model, 0))
                logger.warning(
                    f"Circuit breaker: {model} probe failed in HALF_OPEN, "
                    f"transitioning to OPEN (backoff={delay:.1f}s)"
                )
            else:
                self.failures[model] = self.failures.get(model, 0) + 1
                self.last_failure_time[model] = time.time()
                self._states[model] = (
                    State.OPEN
                    if self.failures[model] >= self.failure_threshold
                    else State.CLOSED
                )
                logger.warning(
                    f"Circuit breaker: {model} now has {self.failures[model]} consecutive failures"
                )
                self._save_state()

    def record_success(self, model: str) -> None:
        """Record a success and reset failure counter."""
        with self._lock:
            current_state = self._states.get(model, State.CLOSED)
            if current_state == State.HALF_OPEN:
                self._states[model] = State.CLOSED
                self.failures[model] = 0
                self._half_open_calls.pop(model, None)
                logger.info(
                    f"Circuit breaker: {model} probe succeeded in HALF_OPEN, "
                    f"transitioning to CLOSED"
                )
            else:
                if model in self.failures:
                    logger.info(
                        f"Circuit breaker: {model} succeeded, resetting failure counter"
                    )
                self.failures[model] = 0
                self._states[model] = State.CLOSED
                self._save_state()

    def is_available(self, model: str) -> bool:
        """Check if a model is available (not in circuit open state)."""
        with self._lock:
            if model not in self.failures:
                return True

            current_state = self._states.get(model, State.CLOSED)
            if current_state == State.HALF_OPEN:
                calls = self._half_open_calls.get(model, 0)
                if calls < self.half_open_max_calls:
                    self._half_open_calls[model] = calls + 1
                    logger.info(
                        f"Circuit breaker: {model} allowing probe call "
                        f"({calls + 1}/{self.half_open_max_calls}) in HALF_OPEN"
                    )
                    return True
                logger.warning(
                    f"Circuit breaker: {model} HALF_OPEN probe limit reached, "
                    f"remaining in HALF_OPEN"
                )
                return False

            if self.failures[model] >= self.failure_threshold:
                elapsed = time.time() - self.last_failure_time.get(model, 0)
                delay = self.get_delay(self.failures[model])
                if elapsed >= delay:
                    self._states[model] = State.HALF_OPEN
                    self._half_open_calls[model] = 0
                    logger.info(
                        f"Circuit breaker: {model} backoff expired (delay={delay:.1f}s), "
                        f"transitioning to HALF_OPEN for probe"
                    )
                    return True
                remaining = int(delay - elapsed)
                logger.warning(
                    f"Circuit breaker: {model} is open, skipping for {remaining}s more (backoff delay={delay:.1f}s)"
                )
                return False
            return True

    def state(self, model: str) -> dict:
        """Get current circuit breaker state for a model."""
        with self._lock:
            failures = self.failures.get(model, 0)
            last_failure = self.last_failure_time.get(model, 0)
            current_state = self._states.get(model, State.CLOSED)
            is_open = current_state != State.CLOSED
            return {
                "model": model,
                "failures": failures,
                "last_failure_time": last_failure,
                "is_open": is_open,
                "threshold": self.failure_threshold,
                "state": current_state.value,
            }

    def reset(self, model: str) -> None:
        """Reset circuit breaker state for a specific model."""
        with self._lock:
            self.failures.pop(model, None)
            self.last_failure_time.pop(model, None)
            self._states.pop(model, None)
            self._half_open_calls.pop(model, None)
            self._save_state()

    def batch_state(self, models: list[str] | None = None) -> dict[str, dict]:
        """Get circuit breaker state for multiple models in a single lock acquisition."""
        with self._lock:
            target_models = models if models is not None else list(self.failures.keys())
            result: dict[str, dict] = {}
            for model in target_models:
                failures = self.failures.get(model, 0)
                last_failure = self.last_failure_time.get(model, 0)
                current_state = self._states.get(model, State.CLOSED)
                is_open = current_state != State.CLOSED
                result[model] = {
                    "model": model,
                    "failures": failures,
                    "last_failure_time": last_failure,
                    "is_open": is_open,
                    "threshold": self.failure_threshold,
                    "state": current_state.value,
                }
            return result

    def _ensure_cache_dir(self) -> None:
        """Ensure the cache directory exists."""
        cache_dir = os.path.dirname(self.state_file)
        if cache_dir and not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

    def _save_state(self) -> None:
        """Save circuit breaker state to JSON file with atomic write and file locking."""
        self._ensure_cache_dir()
        state = {
            "failures": self.failures,
            "last_failure_time": self.last_failure_time,
            "states": {k: v.value for k, v in self._states.items()},
        }
        tmp_file = self.state_file + ".tmp"
        try:
            fd = os.open(tmp_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                with os.fdopen(fd, "w") as f:
                    fcntl.flock(f, fcntl.LOCK_EX)
                    json.dump(state, f)
                    f.flush()
                    os.fsync(f.fileno())
            except Exception:
                os.close(fd)
                raise
            os.chmod(tmp_file, 0o600)
            os.replace(tmp_file, self.state_file)
        except (IOError, OSError) as e:
            logger.warning(f"Failed to save circuit breaker state: {e}")
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except OSError:
                    pass

    def _load_state(self) -> None:
        """Load circuit breaker state from JSON file with shared file lock."""
        if not os.path.exists(self.state_file):
            return
        try:
            with open(self.state_file, "r") as f:
                fcntl.flock(f, fcntl.LOCK_SH)
                state = json.load(f)
                # Assign ALL state fields inside both file lock AND thread lock
                with self._lock:
                    self.failures = state.get("failures", {})
                    self.last_failure_time = state.get("last_failure_time", {})
                    self._states = {
                        k: State(v) for k, v in state.get("states", {}).items()
                    }
                    self._half_open_calls = {
                        k: 0 for k, v in self._states.items() if v == State.HALF_OPEN
                    }
                fcntl.flock(f, fcntl.LOCK_UN)
            logger.info(f"Loaded circuit breaker state from {self.state_file}")
        except json.JSONDecodeError as e:
            logger.warning(f"Corrupted circuit breaker state file: {e}, starting fresh")
        except (IOError, OSError) as e:
            logger.warning(f"Failed to load circuit breaker state: {e}")
