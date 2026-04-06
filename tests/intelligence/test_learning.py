"""Tests for DelegationLearner — learning from past delegations."""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.state.db import StateDB
from src.state.models import Delegation, Result, AgentPerformance
from src.intelligence.learning import (
    DelegationLearner,
    PatternInsight,
    LearningReport,
    learn_from_delegations,
    get_routing_recommendations,
    generate_learning_report,
    HAS_STATE_DB,
)


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = StateDB(Path(path))
    yield db
    db.close()
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def learner(temp_db):
    return DelegationLearner(db=temp_db)


@pytest.fixture
def populated_db(temp_db):
    now = datetime.now(timezone.utc).isoformat()
    for i in range(20):
        agent = "hephaestus" if i % 2 == 0 else "explore"
        status = "success" if i % 3 != 0 else "failure"
        level = f"L{(i % 5) + 1}"
        delegation = Delegation(
            task_id=f"task-{i}",
            agent=agent,
            level=level,
            status=status,
            tokens=100 + i * 10,
            timestamp=now,
        )
        temp_db.add_delegation(delegation)
    return temp_db


class TestPatternInsight:
    def test_to_dict(self):
        insight = PatternInsight(
            pattern_type="agent_success",
            description="Test pattern",
            confidence=0.85,
            recommendation="Use agent X",
            evidence_count=10,
            metadata={"key": "value"},
        )
        d = insight.to_dict()
        assert d["pattern_type"] == "agent_success"
        assert d["confidence"] == 0.85
        assert d["evidence_count"] == 10
        assert d["metadata"]["key"] == "value"

    def test_to_json(self):
        insight = PatternInsight(
            pattern_type="level_struggle",
            description="L3 tasks failing",
            confidence=0.7,
            recommendation="Review L3 scoring",
            evidence_count=5,
        )
        j = insight.to_json()
        assert '"pattern_type": "level_struggle"' in j
        assert '"confidence": 0.7' in j


class TestLearningReport:
    def test_to_dict(self):
        report = LearningReport(
            total_delegations=50,
            success_rate=80.0,
            agent_performance={"hephaestus": {"success_rate": 85.0}},
            level_accuracy={"L1": {"success_rate": 90.0}},
            patterns=[],
            recommendations=["Test recommendation"],
            generated_at="2024-01-01T00:00:00Z",
        )
        d = report.to_dict()
        assert d["total_delegations"] == 50
        assert d["success_rate"] == 80.0
        assert len(d["recommendations"]) == 1

    def test_to_json(self):
        report = LearningReport(
            total_delegations=10,
            success_rate=70.0,
            agent_performance={},
            level_accuracy={},
            patterns=[],
            recommendations=[],
            generated_at="2024-01-01T00:00:00Z",
        )
        j = report.to_json()
        assert '"total_delegations": 10' in j


class TestDelegationLearner:
    def test_init_no_db(self):
        learner = DelegationLearner(db=None)
        if HAS_STATE_DB:
            assert learner._db is not None
        else:
            assert learner._db is None

    def test_analyze_empty_db(self, learner):
        result = learner.analyze_delegations()
        assert "error" in result

    def test_analyze_populated_db(self, populated_db):
        learner = DelegationLearner(db=populated_db)
        result = learner.analyze_delegations()
        assert "error" not in result
        assert result["total_delegations"] >= 20
        assert "agent_performance" in result
        assert "level_performance" in result

    def test_success_rate_calculation(self, populated_db):
        learner = DelegationLearner(db=populated_db)
        result = learner.analyze_delegations()
        assert 0 < result["success_rate"] <= 100
        assert result["success_count"] + result["failure_count"] >= 20

    def test_agent_performance_breakdown(self, populated_db):
        learner = DelegationLearner(db=populated_db)
        result = learner.analyze_delegations()
        perf = result["agent_performance"]
        assert "hephaestus" in perf
        assert "explore" in perf
        for agent, stats in perf.items():
            assert "success_rate" in stats
            assert "total" in stats
            assert stats["total"] > 0

    def test_identify_patterns_empty(self, learner):
        patterns = learner.identify_patterns()
        assert len(patterns) == 0

    def test_identify_patterns_with_data(self, populated_db):
        learner = DelegationLearner(db=populated_db)
        patterns = learner.identify_patterns()
        assert len(patterns) > 0
        assert all(isinstance(p, PatternInsight) for p in patterns)

    def test_recommend_routing_empty(self, learner):
        result = learner.recommend_routing()
        assert "error" in result

    def test_recommend_routing_with_data(self, populated_db):
        learner = DelegationLearner(db=populated_db)
        result = learner.recommend_routing()
        assert "error" not in result
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)

    def test_get_agent_success_patterns(self, populated_db):
        learner = DelegationLearner(db=populated_db)
        patterns = learner.get_agent_success_patterns()
        assert isinstance(patterns, dict)
        assert "hephaestus" in patterns or "explore" in patterns

    def test_get_level_accuracy(self, populated_db):
        learner = DelegationLearner(db=populated_db)
        accuracy = learner.get_level_accuracy()
        assert isinstance(accuracy, dict)

    def test_generate_report(self, populated_db):
        learner = DelegationLearner(db=populated_db)
        report = learner.generate_report()
        assert isinstance(report, LearningReport)
        assert report.total_delegations >= 20
        assert len(report.patterns) > 0
        assert len(report.recommendations) > 0

    def test_record_feedback(self, populated_db):
        learner = DelegationLearner(db=populated_db)
        learner.record_feedback(
            task_id="test-task",
            expected_agent="hephaestus",
            actual_agent="explore",
            success=True,
        )
        perf = populated_db.get_all_agent_performance()
        assert "explore" in perf

    def test_clear_cache(self, learner):
        learner._cache["key"] = "value"
        learner._cache_time = 12345
        learner.clear_cache()
        assert len(learner._cache) == 0
        assert learner._cache_time == 0

    def test_convenience_learn_from_delegations(self, populated_db):
        result = learn_from_delegations(db=populated_db)
        assert "total_delegations" in result
        assert result["total_delegations"] >= 20

    def test_convenience_get_routing_recommendations(self, populated_db):
        result = get_routing_recommendations(db=populated_db)
        assert "recommendations" in result

    def test_convenience_generate_learning_report(self, populated_db):
        report = generate_learning_report(db=populated_db)
        assert isinstance(report, LearningReport)
