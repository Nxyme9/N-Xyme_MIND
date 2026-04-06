"""
Model Fallback Manager — Automatic model fallback with circuit breakers.

Manages per-model circuit breakers, automatic fallback routing, health checks,
and observability integration for the multi-agent orchestration system.

Circuit Breaker States:
    CLOSED   — Model is healthy, requests flow normally
    OPEN     — Model has exceeded failure threshold, requests blocked
    HALF_OPEN — Recovery timeout expired, allowing probe requests

Usage:
    manager = ModelFallbackManager()
    model = manager.get_model("sisyphus")
    try:
        response = call_model(model)
        manager.record_success("sisyphus")
    except Exception:
        manager.record_failure("sisyphus")
        fallback = manager.get_fallback("sisyphus")
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    from src.observability.metrics import get_metrics_collector
except ImportError:
    get_metrics_collector = None

try:
    from src.tools.observability.logger import get_logger as get_structured_logger
except ImportError:
    get_structured_logger = None


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ModelHealth:
    model: str
    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    total_failures: int = 0
    total_successes: int = 0
    last_failure_time: float = 0.0
    last_success_time: float = 0.0
    last_state_change: float = field(default_factory=time.time)
    last_probe_time: float = 0.0
    half_open_probes: int = 0

    @property
    def success_rate(self) -> float:
        total = self.total_successes + self.total_failures
        return self.total_successes / total if total > 0 else 1.0

    @property
    def is_available(self) -> bool:
        return self.state != CircuitState.OPEN

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "state": self.state.value,
            "consecutive_failures": self.consecutive_failures,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "success_rate": round(self.success_rate, 4),
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "is_available": self.is_available,
        }


@dataclass
class FallbackRoute:
    name: str
    primary: str
    fallbacks: list[str] = field(default_factory=list)

    @property
    def chain(self) -> list[str]:
        return [self.primary] + self.fallbacks

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "primary": self.primary,
            "fallbacks": self.fallbacks,
            "chain": self.chain,
        }


class _ModelCircuitBreaker:
    def __init__(
        self,
        model: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
        half_open_max_probes: int = 1,
    ):
        self.model = model
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_probes = half_open_max_probes

        self.health = ModelHealth(model=model)
        self._lock = threading.Lock()

    def _transition(self, new_state: CircuitState) -> None:
        old = self.health.state
        self.health.state = new_state
        self.health.last_state_change = time.time()
        if new_state == CircuitState.HALF_OPEN:
            self.health.half_open_probes = 0
        logger.info(
            "Circuit breaker transition",
            extra={
                "context": {
                    "model": self.model,
                    "from": old.value,
                    "to": new_state.value,
                }
            },
        )
        if get_structured_logger:
            get_structured_logger("model_fallback").info(
                f"Circuit breaker: {self.model} {old.value} -> {new_state.value}"
            )

    def record_success(self) -> None:
        with self._lock:
            self.health.consecutive_failures = 0
            self.health.total_successes += 1
            self.health.last_success_time = time.time()

            if self.health.state == CircuitState.HALF_OPEN:
                self._transition(CircuitState.CLOSED)

            self._emit_metrics()

    def record_failure(self) -> None:
        with self._lock:
            self.health.consecutive_failures += 1
            self.health.total_failures += 1
            self.health.last_failure_time = time.time()

            current = self.health.state

            if current == CircuitState.HALF_OPEN:
                self._transition(CircuitState.OPEN)
            elif current == CircuitState.CLOSED:
                if self.health.consecutive_failures >= self.failure_threshold:
                    self._transition(CircuitState.OPEN)

            self._emit_metrics()

    def is_available(self) -> bool:
        with self._lock:
            current = self.health.state

            if current == CircuitState.CLOSED:
                return True

            if current == CircuitState.OPEN:
                elapsed = time.time() - self.health.last_failure_time
                if elapsed >= self.recovery_timeout:
                    self._transition(CircuitState.HALF_OPEN)
                    self.health.last_probe_time = time.time()
                    self.health.half_open_probes = 1
                    return True
                return False

            if current == CircuitState.HALF_OPEN:
                if self.health.half_open_probes < self.half_open_max_probes:
                    self.health.half_open_probes += 1
                    self.health.last_probe_time = time.time()
                    return True
                return False

            return False

    def reset(self) -> None:
        with self._lock:
            self.health.consecutive_failures = 0
            self.health.state = CircuitState.CLOSED
            self.health.half_open_probes = 0
            self.health.last_state_change = time.time()
            self._emit_metrics()

    def _emit_metrics(self) -> None:
        if get_metrics_collector is None:
            return
        metrics = get_metrics_collector()
        metrics.counter_inc(f"model.{self.model}.failures", 0)
        metrics.counter_inc(f"model.{self.model}.successes", 0)
        metrics.gauge_set(
            f"model.{self.model}.consecutive_failures",
            self.health.consecutive_failures,
        )
        metrics.gauge_set(
            f"model.{self.model}.state",
            {"closed": 0, "open": 1, "half_open": 2}.get(self.health.state.value, 0),
        )


class ModelFallbackManager:
    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
        half_open_max_probes: int = 1,
        state_file: str | None = None,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_probes = half_open_max_probes

        self._breakers: dict[str, _ModelCircuitBreaker] = {}
        self._routes: dict[str, FallbackRoute] = {}
        self._lock = threading.Lock()

        self._state_file = state_file or str(
            Path(__file__).parent.parent.parent / ".cache" / "model-fallback.json"
        )
        self._ensure_cache_dir()
        self._load_state()

        self._emit_global_metrics()

    def _ensure_cache_dir(self) -> None:
        cache_dir = os.path.dirname(self._state_file)
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)

    def _get_or_create_breaker(self, model: str) -> _ModelCircuitBreaker:
        if model not in self._breakers:
            self._breakers[model] = _ModelCircuitBreaker(
                model=model,
                failure_threshold=self.failure_threshold,
                recovery_timeout=self.recovery_timeout,
                half_open_max_probes=self.half_open_max_probes,
            )
        return self._breakers[model]

    def register_route(
        self,
        name: str,
        primary: str,
        fallbacks: list[str] | None = None,
    ) -> None:
        with self._lock:
            self._routes[name] = FallbackRoute(
                name=name,
                primary=primary,
                fallbacks=fallbacks or [],
            )
            self._get_or_create_breaker(primary)
            for fb in fallbacks or []:
                self._get_or_create_breaker(fb)
            self._save_state()

    def get_model(self, name: str) -> str | None:
        with self._lock:
            route = self._routes.get(name)
            if route is None:
                return None

            for model in route.chain:
                breaker = self._get_or_create_breaker(model)
                if breaker.is_available():
                    if model != route.primary:
                        self._emit_fallback_metric(name, model)
                        logger.warning(
                            "Fallback activated",
                            extra={
                                "context": {
                                    "route": name,
                                    "primary": route.primary,
                                    "active": model,
                                }
                            },
                        )
                        if get_structured_logger:
                            get_structured_logger("model_fallback").warning(
                                f"Route '{name}': primary '{route.primary}' unavailable, "
                                f"falling back to '{model}'"
                            )
                    return model

            logger.error(
                "All models unavailable",
                extra={
                    "context": {
                        "route": name,
                        "chain": route.chain,
                    }
                },
            )
            return None

    def get_fallback(self, name: str) -> str | None:
        with self._lock:
            route = self._routes.get(name)
            if route is None:
                return None

            for model in route.fallbacks:
                breaker = self._get_or_create_breaker(model)
                if breaker.is_available():
                    return model

            return None

    def record_success(self, model: str) -> None:
        breaker = self._get_or_create_breaker(model)
        breaker.record_success()
        self._save_state()

    def record_failure(self, model: str) -> None:
        breaker = self._get_or_create_breaker(model)
        breaker.record_failure()
        self._save_state()

    def reset_model(self, model: str) -> None:
        breaker = self._get_or_create_breaker(model)
        breaker.reset()
        self._save_state()

    def reset_all(self) -> None:
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()
            self._save_state()

    def get_health(self, model: str) -> ModelHealth:
        breaker = self._get_or_create_breaker(model)
        return breaker.health

    def get_all_health(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {
                model: breaker.health.to_dict()
                for model, breaker in self._breakers.items()
            }

    def get_routes(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {name: route.to_dict() for name, route in self._routes.items()}

    def get_summary(self) -> dict[str, Any]:
        with self._lock:
            health = {
                model: breaker.health.to_dict()
                for model, breaker in self._breakers.items()
            }
            routes = {name: route.to_dict() for name, route in self._routes.items()}

            total_failures = sum(h["total_failures"] for h in health.values())
            total_successes = sum(h["total_successes"] for h in health.values())
            open_circuits = sum(1 for h in health.values() if h["state"] == "open")

            return {
                "models": health,
                "routes": routes,
                "summary": {
                    "total_models": len(health),
                    "total_routes": len(routes),
                    "total_failures": total_failures,
                    "total_successes": total_successes,
                    "open_circuits": open_circuits,
                    "overall_success_rate": round(
                        total_successes / (total_successes + total_failures), 4
                    )
                    if (total_successes + total_failures) > 0
                    else 1.0,
                },
                "config": {
                    "failure_threshold": self.failure_threshold,
                    "recovery_timeout": self.recovery_timeout,
                    "half_open_max_probes": self.half_open_max_probes,
                },
            }

    def _emit_fallback_metric(self, route: str, fallback_model: str) -> None:
        if get_metrics_collector is None:
            return
        metrics = get_metrics_collector()
        metrics.counter_inc("model_fallbacks_total")
        metrics.counter_inc(f"model_fallbacks_{route}_total")
        metrics.counter_inc(f"model_fallbacks_{fallback_model}_total")

    def _emit_global_metrics(self) -> None:
        if get_metrics_collector is None:
            return
        metrics = get_metrics_collector()
        metrics.gauge_set("model_fallback_manager.routes", len(self._routes))
        metrics.gauge_set("model_fallback_manager.tracked_models", len(self._breakers))

    def _save_state(self) -> None:
        try:
            state = {
                "breakers": {},
                "routes": {
                    name: {
                        "primary": route.primary,
                        "fallbacks": route.fallbacks,
                    }
                    for name, route in self._routes.items()
                },
            }
            for model, breaker in self._breakers.items():
                h = breaker.health
                state["breakers"][model] = {
                    "consecutive_failures": h.consecutive_failures,
                    "total_failures": h.total_failures,
                    "total_successes": h.total_successes,
                    "last_failure_time": h.last_failure_time,
                    "last_success_time": h.last_success_time,
                    "state": h.state.value,
                    "half_open_probes": h.half_open_probes,
                }

            tmp = self._state_file + ".tmp"
            with open(tmp, "w") as f:
                json.dump(state, f, indent=2)
            os.replace(tmp, self._state_file)
        except (IOError, OSError) as e:
            logger.warning(f"Failed to save model fallback state: {e}")

    def _load_state(self) -> None:
        if not os.path.exists(self._state_file):
            return
        try:
            with open(self._state_file) as f:
                state = json.load(f)

            for model, data in state.get("breakers", {}).items():
                breaker = self._get_or_create_breaker(model)
                h = breaker.health
                h.consecutive_failures = data.get("consecutive_failures", 0)
                h.total_failures = data.get("total_failures", 0)
                h.total_successes = data.get("total_successes", 0)
                h.last_failure_time = data.get("last_failure_time", 0.0)
                h.last_success_time = data.get("last_success_time", 0.0)
                h.half_open_probes = data.get("half_open_probes", 0)
                state_val = data.get("state", "closed")
                h.state = CircuitState(state_val)

            for name, route_data in state.get("routes", {}).items():
                self._routes[name] = FallbackRoute(
                    name=name,
                    primary=route_data["primary"],
                    fallbacks=route_data.get("fallbacks", []),
                )

            logger.info(f"Loaded model fallback state from {self._state_file}")
        except (json.JSONDecodeError, IOError, OSError, KeyError) as e:
            logger.warning(f"Failed to load model fallback state: {e}")
