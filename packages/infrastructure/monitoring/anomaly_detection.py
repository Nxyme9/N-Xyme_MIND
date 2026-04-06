"""
Anomaly Detection Module — Ported from N-Xyme ECOSYSTEM SPINE

Predictive failure detection and prevention for Catalyst services.
Implements statistical anomaly detection (Z-score, IQR, moving average).

Usage:
    detector = AnomalyDetector(window_size=50, sensitivity=3.0)
    detector.record_metric("ollama", "response_time_ms", 150)
    anomalies = detector.check_anomalies("ollama", "response_time_ms")
"""

import logging
import math
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AnomalyType(Enum):
    SPIKE = "spike"
    DROP = "drop"
    TREND = "trend"
    LEVEL = "level"


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """A single metric data point."""

    timestamp: float
    value: float


@dataclass
class Anomaly:
    """Detected anomaly."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    service: str = ""
    metric: str = ""
    anomaly_type: AnomalyType = AnomalyType.SPIKE
    severity: Severity = Severity.LOW
    value: float = 0.0
    expected_value: float = 0.0
    deviation: float = 0.0
    timestamp: float = field(default_factory=time.time)
    description: str = ""


@dataclass
class Forecast:
    """Metric forecast prediction."""

    metric: str
    current_value: float
    predicted_value: float
    confidence: float
    horizon_minutes: int
    trend: str  # "up", "down", "stable"


class AnomalyDetector:
    """
    Statistical anomaly detector for Catalyst services.

    Uses Z-score, IQR, and moving average for anomaly detection.
    """

    def __init__(
        self,
        window_size: int = 50,
        sensitivity: float = 3.0,
        min_data_points: int = 10,
    ):
        self.window_size = window_size
        self.sensitivity = sensitivity  # Z-score threshold
        self.min_data_points = min_data_points

        # Metrics: service_name -> metric_name -> list of points
        self.metrics: Dict[str, Dict[str, List[MetricPoint]]] = defaultdict(
            lambda: defaultdict(list)
        )

        # Anomaly history
        self.anomaly_history: List[Anomaly] = []
        self._event_bus = None

        logger.info(
            f"AnomalyDetector: Initialized (window={window_size}, sensitivity={sensitivity})"
        )

    def wire_event_bus(self, event_bus) -> None:
        """Wire event bus for anomaly notifications."""
        self._event_bus = event_bus
        logger.info("AnomalyDetector: Event bus wired")

    def record_metric(self, service: str, metric: str, value: float) -> None:
        """Record a metric data point."""
        point = MetricPoint(timestamp=time.time(), value=value)
        points = self.metrics[service][metric]

        points.append(point)

        # Keep only window_size points
        if len(points) > self.window_size:
            points.pop(0)

    def check_anomalies(self, service: str, metric: str) -> List[Anomaly]:
        """
        Check for anomalies in a metric.

        Returns list of detected anomalies.
        """
        points = self.metrics.get(service, {}).get(metric, [])

        if len(points) < self.min_data_points:
            return []

        values = [p.value for p in points]
        current = values[-1]

        anomalies = []

        # Z-score check
        z_score = self._calculate_z_score(current, values)
        if abs(z_score) > self.sensitivity:
            anomaly_type = AnomalyType.SPIKE if z_score > 0 else AnomalyType.DROP
            severity = self._zscore_to_severity(abs(z_score))

            anomaly = Anomaly(
                service=service,
                metric=metric,
                anomaly_type=anomaly_type,
                severity=severity,
                value=current,
                expected_value=self._mean(values),
                deviation=abs(z_score),
                description=f"{metric} {anomaly_type.value}: {current:.2f} (z-score: {z_score:.2f})",
            )
            anomalies.append(anomaly)

        # Trend detection (simple linear regression)
        trend = self._detect_trend(values)
        if trend != "stable":
            forecast = self._forecast(values, horizon_minutes=5)
            if forecast and forecast.confidence > 0.7:
                anomaly = Anomaly(
                    service=service,
                    metric=metric,
                    anomaly_type=AnomalyType.TREND,
                    severity=Severity.MEDIUM,
                    value=current,
                    expected_value=forecast.predicted_value,
                    deviation=abs(current - forecast.predicted_value),
                    description=f"{metric} trending {trend}: {current:.2f} → {forecast.predicted_value:.2f}",
                )
                anomalies.append(anomaly)

        # Store in history
        self.anomaly_history.extend(anomalies)

        # Publish to event bus
        if anomalies and self._event_bus:
            for anomaly in anomalies:
                self._event_bus.publish(
                    "anomaly.detected",
                    {
                        "service": anomaly.service,
                        "metric": anomaly.metric,
                        "type": anomaly.anomaly_type.value,
                        "severity": anomaly.severity.value,
                        "value": anomaly.value,
                        "description": anomaly.description,
                    },
                )

        if anomalies:
            logger.warning(
                f"AnomalyDetector: {len(anomalies)} anomalies detected for {service}.{metric}"
            )

        return anomalies

    def _calculate_z_score(self, value: float, values: List[float]) -> float:
        """Calculate Z-score for a value."""
        mean = self._mean(values)
        std = self._std(values)
        if std == 0:
            return 0
        return (value - mean) / std

    def _mean(self, values: List[float]) -> float:
        """Calculate mean of values."""
        return sum(values) / len(values) if values else 0

    def _std(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0
        mean = self._mean(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)

    def _zscore_to_severity(self, z_score: float) -> Severity:
        """Convert Z-score to severity level."""
        if z_score > 5:
            return Severity.CRITICAL
        elif z_score > 4:
            return Severity.HIGH
        elif z_score > 3:
            return Severity.MEDIUM
        else:
            return Severity.LOW

    def _compute_regression(self, values: List[float]) -> Optional[Dict]:
        """Compute linear regression once for reuse."""
        if len(values) < 5:
            return None

        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = self._mean(values)

        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return None

        slope = numerator / denominator
        intercept = y_mean - slope * x_mean

        # Calculate R²
        ss_res = sum((y - (intercept + slope * i)) ** 2 for i, y in enumerate(values))
        ss_tot = sum((y - y_mean) ** 2 for y in values)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        return {
            "slope": slope,
            "intercept": intercept,
            "r_squared": r_squared,
            "x_mean": x_mean,
            "y_mean": y_mean,
        }

    def _detect_trend(self, values: List[float]) -> str:
        """Detect trend using linear regression."""
        reg = self._compute_regression(values)
        if reg is None:
            return "stable"

        slope = reg["slope"]
        y_mean = reg["y_mean"]

        if y_mean == 0:
            return "stable"

        normalized_slope = slope / y_mean

        if normalized_slope > 0.01:
            return "up"
        elif normalized_slope < -0.01:
            return "down"
        else:
            return "stable"

    def _forecast(self, values: List[float], horizon_minutes: int = 5) -> Optional[Forecast]:
        """Simple linear regression forecast."""
        reg = self._compute_regression(values)
        if reg is None:
            return None

        n = len(values)
        slope = reg["slope"]
        intercept = reg["intercept"]
        r_squared = reg["r_squared"]

        # Predict future value
        future_x = n + (horizon_minutes * 60 / 10)  # Assume 10s intervals
        predicted = intercept + slope * future_x

        trend = "up" if slope > 0 else "down" if slope < 0 else "stable"

        return Forecast(
            metric="",
            current_value=values[-1],
            predicted_value=predicted,
            confidence=max(0, min(1, r_squared)),
            horizon_minutes=horizon_minutes,
            trend=trend,
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get anomaly detection summary."""
        return {
            "services_tracked": list(self.metrics.keys()),
            "total_anomalies": len(self.anomaly_history),
            "by_severity": {
                s.value: sum(1 for a in self.anomaly_history if a.severity == s) for s in Severity
            },
            "by_type": {
                t.value: sum(1 for a in self.anomaly_history if a.anomaly_type == t)
                for t in AnomalyType
            },
        }


# ============================================
# CONVENIENCE: Create detector for Catalyst
# ============================================


def create_catalyst_detector() -> AnomalyDetector:
    """Create an AnomalyDetector configured for Catalyst."""
    return AnomalyDetector(
        window_size=50,
        sensitivity=3.0,
        min_data_points=10,
    )
