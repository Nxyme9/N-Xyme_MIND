#!/usr/bin/env python3
"""Intelligence layer integration tests.

Tests:
- DelegationLearner reads from StateDB and identifies patterns
- DynamicComplexityScorer adjusts scores based on history
- AgentOptimizer selects best agent per task type
- LoadBalancer predicts and scales
"""

import json
import os
import tempfile
import time
from pathlib import Path

import pytest

from src.state.db import StateDB
from src.state.models import Delegation, Result, AgentPerformance
from src.intelligence.learning import DelegationLearner, PatternInsight, LearningReport
from src.intelligence.dynamic_scorer import DynamicComplexityScorer, DynamicScoreResult
from src.intelligence.agent_optimizer import AgentOptimizer, SelectionResult
from src.intelligence.load_balancer import PredictiveLoadBalancer, create_load_balancer
from src.message_queue.message_queue import MessageQueue


@pytest.fixture
def temp_db_path(tmp_path):
    return tmp_path / "state.db"


@pytest.fixture
def state_db(temp_db_path):
    db = StateDB(temp_db_path)
    yield db
    db.close()


@pytest.fixture
def temp_mq_path(tmp_path):
    return tmp_path / "mq.db"


@pytest.fixture
def message_queue(temp_mq_path):
    mq = MessageQueue(
        db_path=temp_mq_path, visibility_timeout=1, max_retries=3, default_ttl=60
    )
    yield mq
    mq.close()


class TestDelegationLearnerIntegration:
    """Test DelegationLearner reading from StateDB and identifying patterns."""

    def test_learner_identifies_agent_patterns(self, state_db):
        """DelegationLearner should identify which agents perform best."""
        for i in range(15):
            delegation = Delegation(
                task_id=f"pattern-task-{i}",
                agent="hephaestus" if i < 10 else "explore",
                level="3",
                status="success" if i < 12 else "failure",
                tokens=2000,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            )
            state_db.add_delegation(delegation)

        learner = DelegationLearner(db=state_db)
        patterns = learner.identify_patterns()

        assert len(patterns) > 0
        pattern_types = {p.pattern_type for p in patterns}
        assert any("success" in pt or "struggle" in pt for pt in pattern_types)

    def test_learner_recommends_routing(self, state_db):
        """DelegationLearner should recommend optimal routing based on history."""
        for i in range(10):
            delegation = Delegation(
                task_id=f"routing-task-{i}",
                agent="hephaestus",
                level="2",
                status="success",
                tokens=1500,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            )
            state_db.add_delegation(delegation)

        learner = DelegationLearner(db=state_db)
        routing = learner.recommend_routing()

        assert "recommendations" in routing
        assert routing["best_agent"] == "hephaestus"
        assert routing["best_agent_rate"] == 100.0

    def test_learner_generates_full_report(self, state_db):
        """DelegationLearner should generate a comprehensive learning report."""
        for i in range(8):
            delegation = Delegation(
                task_id=f"report-task-{i}",
                agent="oracle" if i % 2 == 0 else "hephaestus",
                level=str((i % 3) + 1),
                status="success" if i < 6 else "failure",
                tokens=3000,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            )
            state_db.add_delegation(delegation)

        learner = DelegationLearner(db=state_db)
        report = learner.generate_report()

        assert isinstance(report, LearningReport)
        assert report.total_delegations == 8
        assert report.success_rate == 75.0
        assert len(report.patterns) > 0
        assert len(report.recommendations) > 0
        assert report.generated_at is not None

    def test_learner_success_patterns_per_agent(self, state_db):
        """DelegationLearner should return success rates per agent."""
        for i in range(6):
            delegation = Delegation(
                task_id=f"success-pattern-{i}",
                agent="explore",
                level="1",
                status="success" if i < 4 else "failure",
                tokens=500,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            )
            state_db.add_delegation(delegation)

        learner = DelegationLearner(db=state_db)
        patterns = learner.get_agent_success_patterns()

        assert "explore" in patterns
        assert patterns["explore"] == pytest.approx(66.67, rel=0.1)

    def test_learner_level_accuracy(self, state_db):
        """DelegationLearner should track accuracy per complexity level."""
        for level in range(1, 6):
            for i in range(3):
                delegation = Delegation(
                    task_id=f"level-accuracy-{level}-{i}",
                    agent="hephaestus",
                    level=str(level),
                    status="success" if i < 2 else "failure",
                    tokens=1000,
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
                )
                state_db.add_delegation(delegation)

        learner = DelegationLearner(db=state_db)
        accuracy = learner.get_level_accuracy()

        assert len(accuracy) == 5
        for level_str, stats in accuracy.items():
            assert stats["total"] == 3
            assert stats["success"] == 2
            assert stats["failure"] == 1


class TestDynamicComplexityScorerIntegration:
    """Test DynamicComplexityScorer adjusting scores based on history."""

    def test_scorer_adjusts_based_on_misclassifications(self, state_db):
        """DynamicComplexityScorer should adjust scores after recording misclassifications."""
        scorer = DynamicComplexityScorer(db=state_db)

        scorer.record_misclassification(
            "fix typo in variable", predicted_level=4, actual_level=1
        )
        scorer.record_misclassification(
            "fix typo in config", predicted_level=3, actual_level=1
        )
        scorer.record_misclassification(
            "fix typo in name", predicted_level=5, actual_level=1
        )

        result = scorer.score("fix typo in database")
        assert (
            result.base_level != result.adjusted_level
            or result.adjustment_reason != "no historical adjustment needed"
        )

    def test_scorer_keyword_adjustments(self, state_db):
        """DynamicComplexityScorer should learn keyword-level adjustments."""
        scorer = DynamicComplexityScorer(db=state_db)

        for _ in range(5):
            scorer.record_misclassification(
                "rewrite architecture overhaul redesign",
                predicted_level=2,
                actual_level=5,
            )

        adjustments = scorer.get_keyword_adjustments()
        assert (
            "rewrite" in adjustments
            or "architecture" in adjustments
            or "overhaul" in adjustments
        )

    def test_scorer_level_accuracy_tracking(self, state_db):
        """DynamicComplexityScorer should track accuracy per level."""
        scorer = DynamicComplexityScorer(db=state_db)

        scorer.record_misclassification("task A", predicted_level=2, actual_level=2)
        scorer.record_misclassification("task B", predicted_level=2, actual_level=3)
        scorer.record_misclassification("task C", predicted_level=2, actual_level=2)

        accuracy = scorer.get_level_accuracy()
        assert "2" in accuracy
        assert accuracy["2"] == pytest.approx(2 / 3, abs=0.01)

    def test_scorer_training_stats(self, state_db):
        """DynamicComplexityScorer should provide comprehensive training statistics."""
        scorer = DynamicComplexityScorer(db=state_db)

        for i in range(10):
            scorer.record_misclassification(
                f"training task {i}",
                predicted_level=(i % 5) + 1,
                actual_level=((i + 2) % 5) + 1,
            )

        stats = scorer.get_training_stats()
        assert stats["total_misclassifications"] == 10
        assert stats["total_predictions"] == 0
        assert stats["overall_accuracy"] == 0.0
        assert stats["keyword_adjustments_count"] > 0

    def test_scorer_reset_clears_all_state(self, state_db):
        """DynamicComplexityScorer reset should clear all learned adjustments."""
        scorer = DynamicComplexityScorer(db=state_db)

        scorer.record_misclassification("reset test", predicted_level=3, actual_level=1)
        scorer.score("reset test")

        scorer.reset()
        stats = scorer.get_training_stats()
        assert stats["total_misclassifications"] == 0
        assert stats["keyword_adjustments_count"] == 0


class TestAgentOptimizerIntegration:
    """Test AgentOptimizer selecting best agent per task type."""

    def test_optimizer_selects_best_agent(self, state_db):
        """AgentOptimizer should select the best performing agent for a task type."""
        optimizer = AgentOptimizer(db=state_db)

        for i in range(10):
            perf = AgentPerformance(
                agent_name="hephaestus",
                task_type="implementation",
                success=9,
                failure=1,
                last_updated=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            )
            state_db.upsert_agent_performance(perf)

        for i in range(5):
            perf = AgentPerformance(
                agent_name="explore",
                task_type="implementation",
                success=2,
                failure=3,
                last_updated=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            )
            state_db.upsert_agent_performance(perf)

        selection = optimizer.select_agent("implementation")
        assert isinstance(selection, SelectionResult)
        assert selection.selected_agent == "hephaestus"
        assert selection.confidence > 0.5

    def test_optimizer_detects_decay(self, state_db):
        """AgentOptimizer should detect performance decay."""
        optimizer = AgentOptimizer(db=state_db)

        for i in range(5):
            perf = AgentPerformance(
                agent_name="decaying-agent",
                task_type="testing",
                success=1,
                failure=4,
                last_updated=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            )
            state_db.upsert_agent_performance(perf)

        decays = optimizer.detect_decay("decaying-agent", "testing")
        assert len(decays) >= 1
        assert decays[0]["agent"] == "decaying-agent"
        assert decays[0]["task_type"] == "testing"

    def test_optimizer_gets_rankings(self, state_db):
        """AgentOptimizer should provide agent rankings per task type."""
        optimizer = AgentOptimizer(db=state_db)

        agents_data = [
            ("agent-a", "review", 8, 2),
            ("agent-b", "review", 6, 4),
            ("agent-c", "review", 9, 1),
        ]
        for agent, task_type, success, failure in agents_data:
            perf = AgentPerformance(
                agent_name=agent,
                task_type=task_type,
                success=success,
                failure=failure,
                last_updated=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            )
            state_db.upsert_agent_performance(perf)

        rankings = optimizer.get_rankings("review")
        assert len(rankings) == 3
        assert rankings[0]["rank"] == 1
        assert rankings[0]["agent"] == "agent-c"

    def test_optimizer_gets_recommendations(self, state_db):
        """AgentOptimizer should provide optimization recommendations."""
        optimizer = AgentOptimizer(db=state_db)

        perf = AgentPerformance(
            agent_name="struggling-agent",
            task_type="documentation",
            success=1,
            failure=9,
            last_updated=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        )
        state_db.upsert_agent_performance(perf)

        recommendations = optimizer.get_recommendations()
        assert len(recommendations) > 0
        assert any("struggling-agent" in r for r in recommendations)

    def test_optimizer_excludes_agents(self, state_db):
        """AgentOptimizer should respect exclusion lists."""
        optimizer = AgentOptimizer(db=state_db)

        perf = AgentPerformance(
            agent_name="excluded-agent",
            task_type="planning",
            success=10,
            failure=0,
            last_updated=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        )
        state_db.upsert_agent_performance(perf)

        perf2 = AgentPerformance(
            agent_name="included-agent",
            task_type="planning",
            success=5,
            failure=5,
            last_updated=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        )
        state_db.upsert_agent_performance(perf2)

        selection = optimizer.select_agent("planning", exclude=["excluded-agent"])
        assert selection.selected_agent == "included-agent"


class TestLoadBalancerIntegration:
    """Test LoadBalancer predicting and scaling."""

    def test_load_balancer_predicts_queue_depth(self, message_queue):
        """PredictiveLoadBalancer should predict future queue depth."""
        lb = PredictiveLoadBalancer(message_queue=message_queue, max_queue_depth=50)

        for i in range(10):
            message_queue.enqueue(f"predict-task-{i}")
            lb.record_enqueue(queue_depth=i + 1)

        prediction = lb.predict_load(horizon_minutes=5)
        assert prediction.predicted_depth >= 0
        assert 0 <= prediction.confidence <= 1
        assert prediction.time_horizon_minutes == 5

    def test_load_balancer_decides_scaling(self, message_queue):
        """PredictiveLoadBalancer should make scaling decisions."""
        lb = PredictiveLoadBalancer(
            message_queue=message_queue,
            max_queue_depth=10,
            scale_up_threshold=0.5,
            scale_down_threshold=0.2,
        )

        for i in range(7):
            message_queue.enqueue(f"scale-task-{i}")
            lb.record_enqueue(queue_depth=i + 1)

        decision = lb.decide_scaling(current_workers=2)
        assert decision.action in ("none", "scale_up", "scale_down")
        assert decision.current_workers == 2
        assert decision.target_workers >= 1

    def test_load_balancer_decides_load_shedding(self, message_queue):
        """PredictiveLoadBalancer should decide when to shed load."""
        lb = PredictiveLoadBalancer(
            message_queue=message_queue,
            max_queue_depth=10,
            load_shed_threshold=0.7,
        )

        for i in range(8):
            message_queue.enqueue(f"shed-task-{i}")
            lb.record_enqueue(queue_depth=i + 1)

        shedding = lb.decide_load_shedding(
            priority_tasks=["low_priority_task_1", "high_priority_task_2"]
        )
        assert shedding.should_shed is True
        assert shedding.shed_percentage > 0
        assert "low_priority_task_1" in shedding.affected_tasks

    def test_load_balancer_gets_comprehensive_status(self, message_queue):
        """PredictiveLoadBalancer should provide comprehensive status."""
        lb = PredictiveLoadBalancer(message_queue=message_queue, max_queue_depth=100)

        for i in range(5):
            message_queue.enqueue(f"status-task-{i}")
            lb.record_enqueue(queue_depth=i + 1)
            lb.record_dequeue(wait_time=0.1)

        status = lb.get_status()
        assert "metrics" in status
        assert "prediction" in status
        assert "scaling" in status
        assert "shedding" in status
        assert "configuration" in status
        assert status["configuration"]["max_queue_depth"] == 100

    def test_load_balancer_reset_clears_state(self, message_queue):
        """PredictiveLoadBalancer reset should clear all state."""
        lb = PredictiveLoadBalancer(message_queue=message_queue, max_queue_depth=50)

        for i in range(10):
            lb.record_enqueue(queue_depth=i)
            lb.record_dequeue(wait_time=0.5)

        lb.decide_scaling()
        lb.decide_load_shedding()

        lb.reset()

        metrics = lb.get_queue_metrics()
        assert metrics.current_depth == 0
        assert metrics.peak_depth == 0

        scaling_history = lb.get_scaling_history()
        assert len(scaling_history) == 0

        shedding_history = lb.get_shedding_history()
        assert len(shedding_history) == 0
