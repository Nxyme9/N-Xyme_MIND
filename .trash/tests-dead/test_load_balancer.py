"""Tests for PredictiveLoadBalancer."""

import pytest
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.intelligence.load_balancer import (
    PredictiveLoadBalancer,
    QueueMetrics,
    LoadPrediction,
    ScalingDecision,
    SheddingDecision,
    create_load_balancer,
)


@pytest.fixture
def balancer():
    return PredictiveLoadBalancer(max_queue_depth=100)


@pytest.fixture
def populated_balancer():
    b = PredictiveLoadBalancer(max_queue_depth=100)
    for _ in range(50):
        b.record_enqueue(queue_depth=50)
    for _ in range(30):
        b.record_dequeue(wait_time=0.5)
    return b


class TestQueueMetrics:
    def test_to_dict(self):
        metrics = QueueMetrics(
            current_depth=10,
            enqueue_rate=5.0,
            dequeue_rate=3.0,
            avg_wait_time=0.5,
            peak_depth=20,
            timestamp="2024-01-01T00:00:00Z",
        )
        d = metrics.to_dict()
        assert d["current_depth"] == 10
        assert d["enqueue_rate"] == 5.0
        assert d["avg_wait_time"] == 0.5
        assert d["peak_depth"] == 20

    def test_default_values(self):
        metrics = QueueMetrics(
            current_depth=0, enqueue_rate=0, dequeue_rate=0,
            avg_wait_time=0, peak_depth=0, timestamp="",
        )
        d = metrics.to_dict()
        assert d["current_depth"] == 0


class TestLoadPrediction:
    def test_to_dict(self):
        pred = LoadPrediction(
            predicted_depth=50,
            confidence=0.8,
            time_horizon_minutes=5.0,
            recommendation="Scale up",
            risk_level="high",
            metrics={"depth": 40},
        )
        d = pred.to_dict()
        assert d["predicted_depth"] == 50
        assert d["risk_level"] == "high"
        assert d["metrics"]["depth"] == 40

    def test_to_json(self):
        pred = LoadPrediction(
            predicted_depth=30,
            confidence=0.9,
            time_horizon_minutes=10.0,
            recommendation="No action",
            risk_level="normal",
        )
        j = pred.to_json()
        assert '"predicted_depth": 30' in j
        assert '"risk_level": "normal"' in j


class TestScalingDecision:
    def test_to_dict(self):
        decision = ScalingDecision(
            action="scale_up",
            current_workers=3,
            target_workers=5,
            reason="High load",
            confidence=0.85,
            timestamp="2024-01-01T00:00:00Z",
        )
        d = decision.to_dict()
        assert d["action"] == "scale_up"
        assert d["current_workers"] == 3
        assert d["target_workers"] == 5

    def test_to_json(self):
        decision = ScalingDecision(
            action="scale_down",
            current_workers=5,
            target_workers=3,
            reason="Low load",
            confidence=0.7,
            timestamp="2024-01-01T00:00:00Z",
        )
        j = decision.to_json()
        assert '"action": "scale_down"' in j


class TestSheddingDecision:
    def test_to_dict_no_shed(self):
        decision = SheddingDecision(
            should_shed=False,
            shed_percentage=0.0,
            reason="Under threshold",
        )
        d = decision.to_dict()
        assert d["should_shed"] is False
        assert d["shed_percentage"] == 0.0

    def test_to_dict_with_shed(self):
        decision = SheddingDecision(
            should_shed=True,
            shed_percentage=0.3,
            reason="Over threshold",
            affected_tasks=["low_priority_task"],
        )
        d = decision.to_dict()
        assert d["should_shed"] is True
        assert d["shed_percentage"] == 0.3
        assert "low_priority_task" in d["affected_tasks"]


class TestPredictiveLoadBalancer:
    def test_init_defaults(self, balancer):
        assert balancer._max_queue_depth == 100
        assert balancer._current_workers == 3
        assert balancer._min_workers == 1
        assert balancer._max_workers == 10

    def test_record_enqueue(self, balancer):
        balancer.record_enqueue(queue_depth=10)
        assert len(balancer._enqueue_history) == 1
        assert len(balancer._depth_history) == 1
        assert balancer._peak_depth == 10

    def test_record_enqueue_updates_peak(self, balancer):
        balancer.record_enqueue(queue_depth=10)
        balancer.record_enqueue(queue_depth=25)
        balancer.record_enqueue(queue_depth=15)
        assert balancer._peak_depth == 25

    def test_record_dequeue(self, balancer):
        balancer.record_dequeue(wait_time=1.5)
        assert len(balancer._dequeue_history) == 1
        assert len(balancer._wait_times) == 1

    def test_get_queue_metrics_empty(self, balancer):
        metrics = balancer.get_queue_metrics()
        assert isinstance(metrics, QueueMetrics)
        assert metrics.current_depth == 0
        assert metrics.enqueue_rate == 0.0

    def test_get_queue_metrics_with_data(self, populated_balancer):
        metrics = populated_balancer.get_queue_metrics()
        assert isinstance(metrics, QueueMetrics)
        assert metrics.current_depth > 0

    def test_predict_load_empty(self, balancer):
        pred = balancer.predict_load()
        assert isinstance(pred, LoadPrediction)
        assert pred.predicted_depth >= 0
        assert 0.0 <= pred.confidence <= 1.0

    def test_predict_load_with_data(self, populated_balancer):
        pred = populated_balancer.predict_load(horizon_minutes=10.0)
        assert isinstance(pred, LoadPrediction)
        assert pred.time_horizon_minutes == 10.0
        assert pred.risk_level in ("normal", "low", "high", "critical")

    def test_predict_load_custom_horizon(self, balancer):
        pred = balancer.predict_load(horizon_minutes=30.0)
        assert pred.time_horizon_minutes == 30.0

    def test_decide_scaling_no_load(self, balancer):
        decision = balancer.decide_scaling(current_workers=3)
        assert isinstance(decision, ScalingDecision)
        assert decision.action in ("none", "scale_up", "scale_down")

    def test_decide_scaling_high_load(self, balancer):
        for _ in range(90):
            balancer.record_enqueue(queue_depth=90)
        decision = balancer.decide_scaling(current_workers=3)
        assert isinstance(decision, ScalingDecision)
        assert decision.current_workers == 3

    def test_decide_load_shedding_under_threshold(self, balancer):
        decision = balancer.decide_load_shedding(current_queue_depth=50)
        assert isinstance(decision, SheddingDecision)
        assert decision.should_shed is False

    def test_decide_load_shedding_over_threshold(self, balancer):
        decision = balancer.decide_load_shedding(current_queue_depth=95)
        assert isinstance(decision, SheddingDecision)
        assert decision.should_shed is True
        assert decision.shed_percentage > 0

    def test_get_scaling_history_empty(self, balancer):
        history = balancer.get_scaling_history()
        assert history == []

    def test_get_scaling_history_with_decisions(self, balancer):
        balancer.decide_scaling(current_workers=3)
        balancer.decide_scaling(current_workers=5)
        history = balancer.get_scaling_history()
        assert len(history) == 2

    def test_get_shedding_history_empty(self, balancer):
        history = balancer.get_shedding_history()
        assert history == []

    def test_get_status(self, balancer):
        status = balancer.get_status()
        assert "metrics" in status
        assert "prediction" in status
        assert "scaling" in status
        assert "shedding" in status
        assert "configuration" in status

    def test_reset(self, populated_balancer):
        populated_balancer.reset()
        assert len(populated_balancer._enqueue_history) == 0
        assert len(populated_balancer._depth_history) == 0
        assert populated_balancer._peak_depth == 0
        assert populated_balancer._current_workers == 3

    def test_calculate_rate_empty(self, balancer):
        rate = balancer._calculate_rate(balancer._enqueue_history, time.time())
        assert rate == 0.0

    def test_prediction_confidence_decreases_with_horizon(self, balancer):
        for _ in range(50):
            balancer.record_enqueue(queue_depth=50)

        short_pred = balancer.predict_load(horizon_minutes=1.0)
        long_pred = balancer.predict_load(horizon_minutes=60.0)
        assert short_pred.confidence >= long_pred.confidence


class TestConvenienceFunctions:
    def test_create_load_balancer(self):
        lb = create_load_balancer()
        assert isinstance(lb, PredictiveLoadBalancer)
        assert lb._max_queue_depth == 100

    def test_create_load_balancer_custom(self):
        lb = create_load_balancer(max_queue_depth=500)
        assert lb._max_queue_depth == 500
