"""Health Schema — Standardized health score definitions for self-healing system."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class HealthStatus(Enum):
    """Overall health status derived from composite score."""

    HEALTHY = "healthy"  # 80-100
    DEGRADED = "degraded"  # 60-79
    IMPAIRED = "impaired"  # 40-59
    CRITICAL = "critical"  # 20-39
    DOWN = "down"  # 0-19


class MetricType(Enum):
    """Types of health metrics."""

    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    RESOURCE = "resource"
    QUALITY = "quality"


# Default metric weights (sum to 1.0)
DEFAULT_WEIGHTS = {
    MetricType.RESPONSE_TIME: 0.25,
    MetricType.ERROR_RATE: 0.30,
    MetricType.RESOURCE: 0.25,
    MetricType.QUALITY: 0.20,
}


@dataclass
class ComponentMetrics:
    """Individual metrics for a single component."""

    component: str
    response_time: float = 100.0  # ms, lower is better (0-100 normalized)
    error_rate: float = 0.0  # %, lower is better (0-100 normalized)
    resource: float = 100.0  # %, higher is better (0-100 normalized)
    quality: float = 100.0  # %, higher is better (0-100 normalized)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    stale: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ComponentMetrics:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class HealthThresholds:
    """Configurable thresholds for health status determination."""

    warning: float = 60.0  # Below this = warning/degraded
    critical: float = 40.0  # Below this = critical
    down: float = 20.0  # Below this = down

    def get_status(self, score: float) -> HealthStatus:
        """Determine health status from composite score."""
        if score >= self.warning:
            return HealthStatus.HEALTHY
        elif score >= self.critical:
            return HealthStatus.DEGRADED
        elif score >= self.down:
            return HealthStatus.IMPAIRED
        elif score > 0:
            return HealthStatus.CRITICAL
        else:
            return HealthStatus.DOWN


@dataclass
class HealthScore:
    """Standardized health score for a component or the overall system."""

    component: str
    total: float = 100.0  # 0-100 composite score
    metrics: Optional[ComponentMetrics] = None
    thresholds: Optional[HealthThresholds] = None
    status: Optional[str] = None
    trend: str = "stable"  # improving, degrading, stable
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Clamp score to 0-100
        self.total = max(0.0, min(100.0, self.total))
        # Determine status if not set
        if self.status is None:
            thresholds = self.thresholds or HealthThresholds()
            self.status = thresholds.get_status(self.total).value

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        if self.metrics:
            result["metrics"] = self.metrics.to_dict()
        if self.thresholds:
            result["thresholds"] = asdict(self.thresholds)
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> HealthScore:
        metrics = None
        if data.get("metrics"):
            metrics = ComponentMetrics.from_dict(data["metrics"])
        thresholds = None
        if data.get("thresholds"):
            thresholds = HealthThresholds(**data["thresholds"])
        return cls(
            component=data["component"],
            total=data.get("total", 100.0),
            metrics=metrics,
            thresholds=thresholds,
            status=data.get("status"),
            trend=data.get("trend", "stable"),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            details=data.get("details", {}),
        )


@dataclass
class SystemHealth:
    """Overall system health composed of component scores."""

    components: dict[str, HealthScore] = field(default_factory=dict)
    composite_score: float = 100.0
    status: str = "healthy"
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    weights: dict[str, float] = field(default_factory=dict)

    def add_component(self, score: HealthScore, weight: float = 1.0):
        """Add a component health score with optional weight."""
        self.components[score.component] = score
        self.weights[score.component] = weight
        self._recalculate()

    def _recalculate(self):
        """Recalculate composite score from weighted components."""
        if not self.components:
            self.composite_score = 100.0
            self.status = "healthy"
            return

        total_weight = sum(self.weights.values())
        if total_weight == 0:
            self.composite_score = 100.0
            self.status = "healthy"
            return

        weighted_sum = sum(
            self.components[name].total * self.weights.get(name, 1.0)
            for name in self.components
        )
        self.composite_score = weighted_sum / total_weight

        # Determine overall status
        thresholds = HealthThresholds()
        self.status = thresholds.get_status(self.composite_score).value
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "composite_score": round(self.composite_score, 2),
            "status": self.status,
            "timestamp": self.timestamp,
            "components": {
                name: score.to_dict() for name, score in self.components.items()
            },
        }
