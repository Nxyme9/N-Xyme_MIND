"""Tests for AgentOptimizer."""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.state.db import StateDB
from src.state.models import AgentPerformance
from src.intelligence.agent_optimizer import (
    AgentOptimizer,
    AgentScore,
    SelectionResult,
    optimize_agent_selection,
    create_optimizer,
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
def optimizer():
    return AgentOptimizer()


@pytest.fixture
def populated_optimizer(temp_db):
    opt = AgentOptimizer(db=temp_db)
    now = datetime.now(timezone.utc).isoformat()

    for i in range(10):
        perf = AgentPerformance(
            agent_name="hephaestus",
            task_type="implementation",
            success=8 if i < 8 else 0,
            failure=2 if i >= 8 else 0,
            last_failure_reason="timeout" if i >= 8 else "",
            last_updated=now,
        )
        temp_db.upsert_agent_performance(perf)

    for i in range(5):
        perf = AgentPerformance(
            agent_name="explore",
            task_type="research",
            success=5,
            failure=0,
            last_failure_reason="",
            last_updated=now,
        )
        temp_db.upsert_agent_performance(perf)

    for i in range(3):
        perf = AgentPerformance(
            agent_name="oracle",
            task_type="review",
            success=1,
            failure=2,
            last_failure_reason="missed edge case",
            last_updated=now,
        )
        temp_db.upsert_agent_performance(perf)

    return opt


class TestAgentScore:
    def test_to_dict(self):
        score = AgentScore(
            agent_name="hephaestus",
            task_type="implementation",
            score=0.85,
            success_rate=0.9,
            total_tasks=10,
            success_count=9,
            failure_count=1,
            last_updated="2024-01-01T00:00:00Z",
            decay_detected=False,
        )
        d = score.to_dict()
        assert d["agent_name"] == "hephaestus"
        assert d["score"] == 0.85
        assert d["decay_detected"] is False

    def test_to_json(self):
        score = AgentScore(
            agent_name="explore",
            task_type="research",
            score=0.7,
            success_rate=0.8,
            total_tasks=5,
            success_count=4,
            failure_count=1,
            last_updated="2024-01-01T00:00:00Z",
            decay_detected=True,
            decay_amount=0.1,
        )
        j = score.to_json()
        assert '"decay_detected": true' in j
        assert '"decay_amount": 0.1' in j


class TestSelectionResult:
    def test_to_dict(self):
        result = SelectionResult(
            selected_agent="hephaestus",
            confidence=0.85,
            alternatives=[{"agent": "explore", "score": 0.7}],
            reason="Best performer",
            scores=[],
        )
        d = result.to_dict()
        assert d["selected_agent"] == "hephaestus"
        assert d["confidence"] == 0.85
        assert len(d["alternatives"]) == 1

    def test_to_json(self):
        result = SelectionResult(
            selected_agent="oracle",
            confidence=0.9,
            alternatives=[],
            reason="Only option",
            scores=[],
        )
        j = result.to_json()
        assert '"selected_agent": "oracle"' in j


class TestAgentOptimizer:
    def test_select_agent_no_data(self, temp_db):
        opt = AgentOptimizer(db=temp_db)
        result = opt.select_agent("implementation")
        assert result.selected_agent in ("hephaestus", "explore")
        assert result.confidence == 0.5

    def test_select_agent_with_data(self, populated_optimizer):
        result = populated_optimizer.select_agent("implementation")
        assert result.selected_agent == "hephaestus"
        assert len(result.scores) > 0

    def test_select_agent_with_exclude(self, populated_optimizer):
        result = populated_optimizer.select_agent("implementation", exclude=["hephaestus"])
        if result.scores:
            assert result.selected_agent != "hephaestus"
        else:
            assert result.selected_agent in ("hephaestus", "explore")

    def test_record_result(self, temp_db):
        opt = AgentOptimizer(db=temp_db)
        opt.record_result("hephaestus", "implementation", True)
        perf = temp_db.get_all_agent_performance()
        assert "hephaestus" in perf

    def test_record_multiple_results(self, temp_db):
        opt = AgentOptimizer(db=temp_db)
        for _ in range(5):
            opt.record_result("explore", "research", True)
        opt.record_result("explore", "research", False)

        perf = temp_db.get_all_agent_performance()
        explore_data = perf.get("explore", {}).get("research", {})
        assert explore_data.get("success", 0) == 5
        assert explore_data.get("failure", 0) == 1

    def test_get_performance_empty(self, optimizer):
        perf = optimizer.get_performance("unknown_agent")
        assert perf == {}

    def test_get_performance_with_data(self, populated_optimizer):
        perf = populated_optimizer.get_performance("hephaestus")
        assert "implementation" in perf

    def test_get_all_performance(self, populated_optimizer):
        all_perf = populated_optimizer.get_all_performance()
        assert "hephaestus" in all_perf
        assert "explore" in all_perf
        assert "oracle" in all_perf

    def test_detect_decay(self, temp_db):
        opt = AgentOptimizer(db=temp_db)
        now = datetime.now(timezone.utc).isoformat()

        for _ in range(5):
            perf = AgentPerformance(
                agent_name="struggling_agent",
                task_type="implementation",
                success=1,
                failure=4,
                last_failure_reason="timeout",
                last_updated=now,
            )
            temp_db.upsert_agent_performance(perf)

        decays = opt.detect_decay("struggling_agent")
        assert len(decays) > 0
        assert decays[0]["agent"] == "struggling_agent"
        assert decays[0]["decay_amount"] > 0

    def test_detect_decay_no_decay(self, populated_optimizer):
        decays = populated_optimizer.detect_decay("hephaestus")
        assert len(decays) == 0

    def test_get_rankings(self, populated_optimizer):
        rankings = populated_optimizer.get_rankings("implementation")
        assert len(rankings) > 0
        assert rankings[0]["rank"] == 1

    def test_get_recommendations_empty(self, optimizer):
        recs = optimizer.get_recommendations()
        assert isinstance(recs, list)

    def test_get_recommendations_with_data(self, populated_optimizer):
        recs = populated_optimizer.get_recommendations()
        assert isinstance(recs, list)

    def test_reset(self, populated_optimizer):
        populated_optimizer.reset()
        assert len(populated_optimizer._performance_cache) == 0
        assert len(populated_optimizer._decay_history) == 0


class TestConvenienceFunctions:
    def test_optimize_agent_selection(self):
        result = optimize_agent_selection("implementation")
        assert isinstance(result, SelectionResult)
        assert result.selected_agent is not None

    def test_create_optimizer(self):
        opt = create_optimizer()
        assert isinstance(opt, AgentOptimizer)
