"""
Plugin Health ML — ML-based crash prediction (ported from LIVE)

Predicts plugin/service crashes based on historical patterns.

Usage:
    predictor = PluginHealthPredictor()
    predictor.record("ollama", success=True, response_time=0.5)
    predictor.record("ollama", success=False, response_time=5.0)
    health = predictor.predict("ollama")
    print(health)  # {"risk": "high", "confidence": 0.8}
"""

import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class HealthMetric:
    """Health metric for a service."""

    timestamp: float
    success: bool
    response_time: float
    error: Optional[str] = None


@dataclass
class HealthPrediction:
    """Health prediction for a service."""

    service: str
    risk_level: str  # low, medium, high, critical
    confidence: float
    total_checks: int
    success_rate: float
    avg_response_time: float
    recent_failures: int
    trend: str  # improving, stable, degrading


class PluginHealthPredictor:
    """ML-based service health prediction."""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._metrics: Dict[str, List[HealthMetric]] = defaultdict(list)
        logger.info("PluginHealthPredictor: Initialized")

    def record(
        self,
        service: str,
        success: bool,
        response_time: float,
        error: Optional[str] = None,
    ) -> None:
        """Record a health check."""
        metric = HealthMetric(
            timestamp=time.time(),
            success=success,
            response_time=response_time,
            error=error,
        )
        self._metrics[service].append(metric)

        # Keep only window_size metrics
        if len(self._metrics[service]) > self.window_size:
            self._metrics[service] = self._metrics[service][-self.window_size :]

    def predict(self, service: str) -> HealthPrediction:
        """Predict health for a service."""
        metrics = self._metrics.get(service, [])

        if not metrics:
            return HealthPrediction(
                service=service,
                risk_level="unknown",
                confidence=0.0,
                total_checks=0,
                success_rate=0.0,
                avg_response_time=0.0,
                recent_failures=0,
                trend="unknown",
            )

        total = len(metrics)
        successes = sum(1 for m in metrics if m.success)
        failures = total - successes
        success_rate = successes / total if total > 0 else 0

        # Recent failures (last 10)
        recent = metrics[-10:]
        recent_failures = sum(1 for m in recent if not m.success)

        # Average response time
        avg_response = sum(m.response_time for m in metrics) / total

        # Trend analysis
        trend = self._analyze_trend(metrics)

        # Risk calculation
        risk_level = self._calculate_risk(success_rate, recent_failures, avg_response, trend)
        confidence = self._calculate_confidence(total, recent_failures)

        return HealthPrediction(
            service=service,
            risk_level=risk_level,
            confidence=confidence,
            total_checks=total,
            success_rate=round(success_rate * 100, 1),
            avg_response_time=round(avg_response, 3),
            recent_failures=recent_failures,
            trend=trend,
        )

    def _analyze_trend(self, metrics: List[HealthMetric]) -> str:
        """Analyze trend of service health."""
        if len(metrics) < 10:
            return "unknown"

        # Split into two halves
        mid = len(metrics) // 2
        first_half = metrics[:mid]
        second_half = metrics[mid:]

        first_success = sum(1 for m in first_half if m.success) / len(first_half)
        second_success = sum(1 for m in second_half if m.success) / len(second_half)

        diff = second_success - first_success
        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "degrading"
        else:
            return "stable"

    def _calculate_risk(
        self,
        success_rate: float,
        recent_failures: int,
        avg_response: float,
        trend: str,
    ) -> str:
        """Calculate risk level."""
        score = 0

        # Success rate
        if success_rate < 0.5:
            score += 4
        elif success_rate < 0.8:
            score += 2
        elif success_rate < 0.95:
            score += 1

        # Recent failures
        if recent_failures >= 5:
            score += 3
        elif recent_failures >= 3:
            score += 2
        elif recent_failures >= 1:
            score += 1

        # Response time
        if avg_response > 5.0:
            score += 2
        elif avg_response > 2.0:
            score += 1

        # Trend
        if trend == "degrading":
            score += 2

        # Risk level
        if score >= 7:
            return "critical"
        elif score >= 5:
            return "high"
        elif score >= 3:
            return "medium"
        else:
            return "low"

    def _calculate_confidence(self, total: int, recent_failures: int) -> float:
        """Calculate prediction confidence."""
        if total < 5:
            return 0.3
        elif total < 20:
            return 0.6
        else:
            return 0.9

    def get_all_predictions(self) -> Dict[str, HealthPrediction]:
        """Get predictions for all services."""
        return {service: self.predict(service) for service in self._metrics.keys()}

    def get_at_risk(self) -> List[HealthPrediction]:
        """Get services at risk."""
        predictions = self.get_all_predictions()
        return [p for p in predictions.values() if p.risk_level in ("high", "critical")]
