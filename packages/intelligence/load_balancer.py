"""Predictive load balancing — predict queue depth, auto-scale workers, load shedding."""

from __future__ import annotations

import json
import logging
import math
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    from packages.intelligence.message_queue import MessageQueue
    HAS_MESSAGE_QUEUE = True
except ImportError:
    HAS_MESSAGE_QUEUE = False
    MessageQueue = None

logger = logging.getLogger(__name__)

DEFAULT_MAX_QUEUE_DEPTH = 100
DEFAULT_LOAD_SHED_THRESHOLD = 0.85
DEFAULT_SCALE_UP_THRESHOLD = 0.7
DEFAULT_SCALE_DOWN_THRESHOLD = 0.3
DEFAULT_PREDICTION_WINDOW = 5
DEFAULT_HISTORY_SIZE = 1000
DEFAULT_MIN_WORKERS = 1
DEFAULT_MAX_WORKERS = 10


@dataclass
class QueueMetrics:
    """Snapshot of queue metrics."""

    current_depth: int
    enqueue_rate: float
    dequeue_rate: float
    avg_wait_time: float
    peak_depth: int
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_depth": self.current_depth,
            "enqueue_rate": round(self.enqueue_rate, 2),
            "dequeue_rate": round(self.dequeue_rate, 2),
            "avg_wait_time": round(self.avg_wait_time, 2),
            "peak_depth": self.peak_depth,
            "timestamp": self.timestamp,
        }


@dataclass
class LoadPrediction:
    """Prediction of future queue state."""

    predicted_depth: int
    confidence: float
    time_horizon_minutes: float
    recommendation: str
    risk_level: str
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "predicted_depth": self.predicted_depth,
            "confidence": round(self.confidence, 3),
            "time_horizon_minutes": self.time_horizon_minutes,
            "recommendation": self.recommendation,
            "risk_level": self.risk_level,
            "metrics": self.metrics,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class ScalingDecision:
    """Decision about worker pool scaling."""

    action: str
    current_workers: int
    target_workers: int
    reason: str
    confidence: float
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "current_workers": self.current_workers,
            "target_workers": self.target_workers,
            "reason": self.reason,
            "confidence": round(self.confidence, 3),
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class SheddingDecision:
    """Decision about load shedding."""

    should_shed: bool
    shed_percentage: float
    reason: str
    affected_tasks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "should_shed": self.should_shed,
            "shed_percentage": round(self.shed_percentage, 2),
            "reason": self.reason,
            "affected_tasks": self.affected_tasks,
        }


class PredictiveLoadBalancer:
    """Predicts queue depth, auto-scales workers, and handles load shedding."""

    def __init__(
        self,
        message_queue: Any = None,
        max_queue_depth: int = DEFAULT_MAX_QUEUE_DEPTH,
        load_shed_threshold: float = DEFAULT_LOAD_SHED_THRESHOLD,
        scale_up_threshold: float = DEFAULT_SCALE_UP_THRESHOLD,
        scale_down_threshold: float = DEFAULT_SCALE_DOWN_THRESHOLD,
        prediction_window: int = DEFAULT_PREDICTION_WINDOW,
        history_size: int = DEFAULT_HISTORY_SIZE,
        min_workers: int = DEFAULT_MIN_WORKERS,
        max_workers: int = DEFAULT_MAX_WORKERS,
    ):
        self._message_queue = message_queue
        self._max_queue_depth = max_queue_depth
        self._load_shed_threshold = load_shed_threshold
        self._scale_up_threshold = scale_up_threshold
        self._scale_down_threshold = scale_down_threshold
        self._prediction_window = prediction_window
        self._history_size = history_size
        self._min_workers = min_workers
        self._max_workers = max_workers

        self._lock = threading.Lock()
        self._enqueue_history: deque[tuple[float, int]] = deque(maxlen=history_size)
        self._dequeue_history: deque[tuple[float, int]] = deque(maxlen=history_size)
        self._depth_history: deque[tuple[float, int]] = deque(maxlen=history_size)
        self._wait_times: deque[float] = deque(maxlen=history_size)
        self._peak_depth = 0
        self._scaling_decisions: list[ScalingDecision] = []
        self._shedding_decisions: list[SheddingDecision] = []
        self._current_workers = 3
        self._last_enqueue_count = 0
        self._last_dequeue_count = 0
        self._last_metrics_time = time.time()

    def record_enqueue(self, queue_depth: int | None = None) -> None:
        """Record an enqueue event."""
        now = time.time()
        with self._lock:
            self._enqueue_history.append((now, 1))
            if queue_depth is not None:
                self._depth_history.append((now, queue_depth))
                if queue_depth > self._peak_depth:
                    self._peak_depth = queue_depth

    def record_dequeue(self, wait_time: float = 0.0) -> None:
        """Record a dequeue event."""
        now = time.time()
        with self._lock:
            self._dequeue_history.append((now, 1))
            if wait_time > 0:
                self._wait_times.append(wait_time)

    def get_queue_metrics(self) -> QueueMetrics:
        """Get current queue metrics."""
        now = time.time()
        current_depth = self._get_current_depth()
        enqueue_rate = self._calculate_rate(self._enqueue_history, now)
        dequeue_rate = self._calculate_rate(self._dequeue_history, now)
        avg_wait = (
            sum(self._wait_times) / len(self._wait_times)
            if self._wait_times else 0.0
        )

        return QueueMetrics(
            current_depth=current_depth,
            enqueue_rate=enqueue_rate,
            dequeue_rate=dequeue_rate,
            avg_wait_time=avg_wait,
            peak_depth=self._peak_depth,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def predict_load(self, horizon_minutes: float | None = None) -> LoadPrediction:
        """Predict queue depth at a future time horizon."""
        horizon = horizon_minutes or self._prediction_window
        now = time.time()
        metrics = self.get_queue_metrics()

        trend = self._calculate_trend(self._depth_history, now)
        predicted_depth = max(0, int(metrics.current_depth + (trend * horizon * 60)))

        confidence = self._calculate_prediction_confidence(horizon)
        utilization = predicted_depth / self._max_queue_depth if self._max_queue_depth > 0 else 0

        if utilization >= self._load_shed_threshold:
            risk_level = "critical"
            recommendation = f"URGENT: Predicted queue depth {predicted_depth} exceeds threshold. Initiate load shedding immediately."
        elif utilization >= self._scale_up_threshold:
            risk_level = "high"
            recommendation = f"Queue depth approaching capacity ({predicted_depth}/{self._max_queue_depth}). Scale up workers."
        elif utilization <= self._scale_down_threshold and metrics.current_depth < self._max_queue_depth * 0.2:
            risk_level = "low"
            recommendation = f"Low utilization. Consider scaling down workers to save resources."
        else:
            risk_level = "normal"
            recommendation = "Queue depth within normal parameters. No action needed."

        return LoadPrediction(
            predicted_depth=predicted_depth,
            confidence=confidence,
            time_horizon_minutes=horizon,
            recommendation=recommendation,
            risk_level=risk_level,
            metrics=metrics.to_dict(),
        )

    def decide_scaling(self, current_workers: int | None = None) -> ScalingDecision:
        """Decide whether to scale workers up or down."""
        workers = current_workers or self._current_workers
        metrics = self.get_queue_metrics()
        now = time.time()

        utilization = metrics.current_depth / self._max_queue_depth if self._max_queue_depth > 0 else 0
        target_workers = workers
        action = "none"
        reason = "Current worker count is optimal"

        if utilization >= self._scale_up_threshold:
            scale_factor = math.ceil(utilization / self._scale_up_threshold)
            target_workers = min(self._max_workers, workers + scale_factor)
            action = "scale_up"
            reason = f"High utilization ({utilization:.0%}). Scaling from {workers} to {target_workers} workers."
        elif utilization <= self._scale_down_threshold and workers > self._min_workers:
            target_workers = max(self._min_workers, workers - 1)
            action = "scale_down"
            reason = f"Low utilization ({utilization:.0%}). Scaling from {workers} to {target_workers} workers."

        confidence = min(1.0, max(0.3, abs(utilization - 0.5) * 2))

        decision = ScalingDecision(
            action=action,
            current_workers=workers,
            target_workers=target_workers,
            reason=reason,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        with self._lock:
            self._scaling_decisions.append(decision)
            self._current_workers = target_workers

        return decision

    def decide_load_shedding(
        self,
        current_queue_depth: int | None = None,
        priority_tasks: list[str] | None = None,
    ) -> SheddingDecision:
        """Decide whether to shed load under heavy queue pressure."""
        depth = current_queue_depth if current_queue_depth is not None else self._get_current_depth()
        utilization = depth / self._max_queue_depth if self._max_queue_depth > 0 else 0
        priority_tasks = priority_tasks or []

        if utilization < self._load_shed_threshold:
            return SheddingDecision(
                should_shed=False,
                shed_percentage=0.0,
                reason=f"Utilization {utilization:.0%} below threshold {self._load_shed_threshold:.0%}",
            )

        shed_percentage = min(0.5, (utilization - self._load_shed_threshold) * 2)
        affected = [t for t in priority_tasks if t.startswith("low_")]

        decision = SheddingDecision(
            should_shed=True,
            shed_percentage=shed_percentage,
            reason=f"Critical utilization {utilization:.0%}. Shedding {shed_percentage:.0%} of low-priority tasks.",
            affected_tasks=affected,
        )

        with self._lock:
            self._shedding_decisions.append(decision)

        return decision

    def get_scaling_history(self) -> list[dict[str, Any]]:
        """Get history of scaling decisions."""
        with self._lock:
            return [d.to_dict() for d in self._scaling_decisions]

    def get_shedding_history(self) -> list[dict[str, Any]]:
        """Get history of load shedding decisions."""
        with self._lock:
            return [d.to_dict() for d in self._shedding_decisions]

    def get_status(self) -> dict[str, Any]:
        """Get comprehensive load balancer status."""
        metrics = self.get_queue_metrics()
        prediction = self.predict_load()
        scaling = self.decide_scaling()
        shedding = self.decide_load_shedding()

        return {
            "metrics": metrics.to_dict(),
            "prediction": prediction.to_dict(),
            "scaling": scaling.to_dict(),
            "shedding": shedding.to_dict(),
            "configuration": {
                "max_queue_depth": self._max_queue_depth,
                "load_shed_threshold": self._load_shed_threshold,
                "scale_up_threshold": self._scale_up_threshold,
                "scale_down_threshold": self._scale_down_threshold,
                "min_workers": self._min_workers,
                "max_workers": self._max_workers,
                "current_workers": self._current_workers,
            },
        }

    def reset(self) -> None:
        """Reset all load balancer state."""
        with self._lock:
            self._enqueue_history.clear()
            self._dequeue_history.clear()
            self._depth_history.clear()
            self._wait_times.clear()
            self._peak_depth = 0
            self._scaling_decisions.clear()
            self._shedding_decisions.clear()
            self._current_workers = 3

    def _get_current_depth(self) -> int:
        """Get current queue depth."""
        if self._message_queue is not None and HAS_MESSAGE_QUEUE:
            try:
                return self._message_queue.get_queue_depth()
            except Exception:
                pass

        if self._depth_history:
            return self._depth_history[-1][1]
        return 0

    def _calculate_rate(
        self, history: deque[tuple[float, int]], now: float
    ) -> float:
        """Calculate events per second over the last 60 seconds."""
        if not history:
            return 0.0

        cutoff = now - 60
        recent = [(t, c) for t, c in history if t >= cutoff]
        if not recent:
            return 0.0

        total = sum(c for _, c in recent)
        duration = now - recent[0][0]
        if duration <= 0:
            return 0.0

        return total / duration

    def _calculate_trend(
        self, history: deque[tuple[float, int]], now: float
    ) -> float:
        """Calculate depth trend (change per second)."""
        if len(history) < 2:
            return 0.0

        recent = [(t, d) for t, d in history if t >= now - 300]
        if len(recent) < 2:
            return 0.0

        first_t, first_d = recent[0]
        last_t, last_d = recent[-1]
        duration = last_t - first_t
        if duration <= 0:
            return 0.0

        return (last_d - first_d) / duration

    def _calculate_prediction_confidence(self, horizon_minutes: float) -> float:
        """Calculate confidence for a prediction."""
        data_points = len(self._depth_history)
        data_confidence = min(1.0, data_points / 100)

        horizon_penalty = max(0.3, 1.0 - (horizon_minutes / 60))

        return data_confidence * horizon_penalty


def create_load_balancer(
    message_queue: Any = None,
    max_queue_depth: int = DEFAULT_MAX_QUEUE_DEPTH,
) -> PredictiveLoadBalancer:
    """Create a new predictive load balancer."""
    return PredictiveLoadBalancer(
        message_queue=message_queue,
        max_queue_depth=max_queue_depth,
    )
