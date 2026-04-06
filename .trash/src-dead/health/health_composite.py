"""Composite Health Scorer — Weighted health scoring with dependency handling."""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional

from src.health.health_schema import (
    ComponentMetrics,
    HealthScore,
    HealthThresholds,
    MetricType,
    DEFAULT_WEIGHTS,
    SystemHealth,
)

logger = logging.getLogger(__name__)


@dataclass
class MetricRecord:
    """A single metric measurement with timestamp."""

    value: float
    timestamp: float = field(default_factory=time.time)
    stale_after_seconds: float = 300.0  # 5 minutes default

    @property
    def is_stale(self) -> bool:
        return (time.time() - self.timestamp) > self.stale_after_seconds


class CompositeHealthScorer:
    """Calculate weighted composite health scores with dependency handling."""

    def __init__(
        self,
        weights: Optional[dict[MetricType, float]] = None,
        stale_threshold: float = 300.0,
        decay_rate: float = 0.1,
    ):
        """Initialize scorer.

        Args:
            weights: Metric weights (default: DEFAULT_WEIGHTS).
            stale_threshold: Seconds before a metric is considered stale.
            decay_rate: Exponential decay rate for stale metrics (0-1).
        """
        self.weights = weights or DEFAULT_WEIGHTS
        self.stale_threshold = stale_threshold
        self.decay_rate = decay_rate
        self._lock = threading.Lock()

        # Metric history per component
        self._metrics: dict[str, dict[MetricType, list[MetricRecord]]] = defaultdict(
            lambda: defaultdict(list)
        )

        # Component dependency graph (component -> list of dependencies)
        self._dependencies: dict[str, list[str]] = defaultdict(list)

        # Score history for trend calculation
        self._score_history: dict[str, list[tuple[float, float]]] = defaultdict(list)

    def set_dependencies(self, component: str, dependencies: list[str]):
        """Set dependencies for a component."""
        with self._lock:
            self._dependencies[component] = dependencies

    def record_metric(
        self,
        component: str,
        metric_type: MetricType,
        value: float,
        stale_after: Optional[float] = None,
    ):
        """Record a metric measurement."""
        with self._lock:
            record = MetricRecord(
                value=value,
                stale_after_seconds=stale_after or self.stale_threshold,
            )
            self._metrics[component][metric_type].append(record)

            # Keep only recent records (last 100)
            records = self._metrics[component][metric_type]
            if len(records) > 100:
                self._metrics[component][metric_type] = records[-100:]

    def get_latest_metric(
        self, component: str, metric_type: MetricType
    ) -> Optional[float]:
        """Get the latest non-stale metric value."""
        with self._lock:
            records = self._metrics[component].get(metric_type, [])
        if not records:
            return None

        # Find latest non-stale record
        for record in reversed(records):
            if not record.is_stale:
                return record.value

        # All stale — return latest with decay
        latest = records[-1]
        age = time.time() - latest.timestamp
        decay = max(0.0, 1.0 - (age / self.stale_threshold) * self.decay_rate)
        return latest.value * decay

    def calculate(self, component: str) -> HealthScore:
        """Calculate composite health score for a component."""
        metrics = {}
        weighted_sum = 0.0
        total_weight = 0.0

        for metric_type, weight in self.weights.items():
            value = self.get_latest_metric(component, metric_type)
            if value is not None:
                metrics[metric_type.value] = value
                weighted_sum += value * weight
                total_weight += weight

        # Calculate composite score
        if total_weight > 0:
            composite = weighted_sum / total_weight
        else:
            composite = 100.0  # No metrics = assume healthy

        # Apply dependency penalty
        dep_penalty = self._calculate_dependency_penalty(component)
        composite = max(0.0, composite - dep_penalty)

        # Calculate trend
        trend = self._calculate_trend(component, composite)

        # Build metrics object
        component_metrics = ComponentMetrics(
            component=component,
            response_time=metrics.get("response_time", 100.0),
            error_rate=metrics.get("error_rate", 0.0),
            resource=metrics.get("resource", 100.0),
            quality=metrics.get("quality", 100.0),
        )

        score = HealthScore(
            component=component,
            total=round(composite, 2),
            metrics=component_metrics,
            thresholds=HealthThresholds(),
            trend=trend,
        )

        # Record score for trend calculation
        with self._lock:
            self._score_history[component].append((time.time(), composite))
            if len(self._score_history[component]) > 100:
                self._score_history[component] = self._score_history[component][-100:]

        return score

    def calculate_system_health(
        self, weights: Optional[dict[str, float]] = None
    ) -> SystemHealth:
        """Calculate overall system health."""
        system = SystemHealth()

        for component in self._metrics:
            score = self.calculate(component)
            weight = weights.get(component, 1.0) if weights else 1.0
            system.add_component(score, weight)

        return system

    def _calculate_dependency_penalty(self, component: str) -> float:
        """Calculate penalty based on dependency health."""
        deps = self._dependencies.get(component, [])
        if not deps:
            return 0.0

        total_penalty = 0.0
        for dep in deps:
            dep_score = self.calculate(dep)
            if dep_score.total < 60:
                # Penalty proportional to how unhealthy the dependency is
                penalty = (60 - dep_score.total) / 60 * 10  # Max 10 points per dep
                total_penalty += penalty

        return min(20.0, total_penalty)  # Cap at 20 points

    def _calculate_trend(self, component: str, current_score: float) -> str:
        """Calculate score trend (improving, degrading, stable)."""
        with self._lock:
            history = self._score_history.get(component, [])
        if len(history) < 5:
            return "stable"

        # Compare recent average to older average
        recent = [s for _, s in history[-5:]]
        older = [s for _, s in history[-10:-5]]

        if not older:
            return "stable"

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)

        diff = recent_avg - older_avg
        if diff > 5:
            return "improving"
        elif diff < -5:
            return "degrading"
        else:
            return "stable"

    def clear_stale_metrics(self):
        """Remove stale metric records to prevent memory growth."""
        with self._lock:
            for component in list(self._metrics):
                for metric_type in list(self._metrics[component]):
                    records = self._metrics[component][metric_type]
                    self._metrics[component][metric_type] = [
                        r for r in records if not r.is_stale
                    ]
