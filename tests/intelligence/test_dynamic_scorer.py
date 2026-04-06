"""Tests for DynamicComplexityScorer."""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.state.db import StateDB
from src.state.models import Delegation, Result
from src.intelligence.dynamic_scorer import (
    DynamicComplexityScorer,
    DynamicScoreResult,
    MisclassificationRecord,
    score_dynamic,
    create_scorer,
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
def scorer():
    return DynamicComplexityScorer()


class TestDynamicScoreResult:
    def test_to_dict(self):
        result = DynamicScoreResult(
            level=3, base_level=2, adjusted_level=3,
            confidence=0.8, historical_confidence=0.7,
            reason="test", adjustment_reason="adjusted",
            metadata={"key": "value"},
        )
        d = result.to_dict()
        assert d["level"] == 3
        assert d["base_level"] == 2
        assert d["adjusted_level"] == 3
        assert d["confidence"] == 0.8
        assert d["metadata"]["key"] == "value"

    def test_to_json(self):
        result = DynamicScoreResult(
            level=4, base_level=3, adjusted_level=4,
            confidence=0.9, historical_confidence=0.8,
            reason="complex task", adjustment_reason="historical adjustment",
        )
        j = result.to_json()
        assert '"level": 4' in j
        assert '"adjusted_level": 4' in j


class TestMisclassificationRecord:
    def test_to_dict(self):
        record = MisclassificationRecord(
            task_description="fix typo in variable",
            predicted_level=2,
            actual_level=1,
            timestamp="2024-01-01T00:00:00Z",
            agent_feedback="was simpler than expected",
        )
        d = record.to_dict()
        assert d["predicted_level"] == 2
        assert d["actual_level"] == 1
        assert d["agent_feedback"] == "was simpler than expected"


class TestDynamicComplexityScorer:
    def test_score_empty_task(self, scorer):
        result = scorer.score("")
        assert 1 <= result.level <= 5
        assert 1 <= result.base_level <= 5
        assert 1 <= result.adjusted_level <= 5

    def test_score_simple_task(self, scorer):
        result = scorer.score("fix typo in config")
        assert 1 <= result.level <= 5
        assert result.confidence >= 0.0
        assert result.confidence <= 1.0

    def test_score_complex_task(self, scorer):
        result = scorer.score("redesign entire authentication system with JWT")
        assert 1 <= result.level <= 5
        assert result.reason != ""

    def test_level_bounds(self, scorer):
        result = scorer.score("test task")
        assert 1 <= result.level <= 5
        assert 1 <= result.adjusted_level <= 5

    def test_record_misclassification(self, scorer):
        scorer.record_misclassification(
            "fix typo in variable",
            predicted_level=2,
            actual_level=1,
            agent_feedback="too complex",
        )
        history = scorer.get_adjustment_history()
        assert len(history) == 1
        assert history[0]["predicted_level"] == 2
        assert history[0]["actual_level"] == 1

    def test_multiple_misclassifications(self, scorer):
        for i in range(5):
            scorer.record_misclassification(
                f"task {i}",
                predicted_level=3,
                actual_level=2,
            )
        history = scorer.get_adjustment_history()
        assert len(history) == 5

    def test_get_confidence_for_level(self, scorer):
        confidence = scorer.get_confidence_for_level(3)
        assert 0.0 <= confidence <= 1.0

    def test_get_confidence_with_data(self, scorer):
        scorer.record_misclassification("task1", 3, 3)
        scorer.record_misclassification("task2", 3, 3)
        scorer.record_misclassification("task3", 3, 2)
        confidence = scorer.get_confidence_for_level(3)
        assert 0.0 <= confidence <= 1.0

    def test_get_keyword_adjustments(self, scorer):
        scorer.record_misclassification("fix auth bug", 2, 3)
        adjustments = scorer.get_keyword_adjustments()
        assert isinstance(adjustments, dict)
        assert len(adjustments) > 0

    def test_get_level_accuracy(self, scorer):
        scorer.record_misclassification("task1", 1, 1)
        scorer.record_misclassification("task2", 1, 2)
        scorer.record_misclassification("task3", 2, 2)
        accuracy = scorer.get_level_accuracy()
        assert "1" in accuracy
        assert "2" in accuracy
        assert 0.0 <= accuracy["1"] <= 1.0

    def test_get_training_stats(self, scorer):
        scorer.record_misclassification("task1", 2, 3)
        scorer.score("test task")
        stats = scorer.get_training_stats()
        assert "total_misclassifications" in stats
        assert "total_predictions" in stats
        assert "overall_accuracy" in stats
        assert stats["total_misclassifications"] >= 1

    def test_reset(self, scorer):
        scorer.record_misclassification("task1", 2, 3)
        scorer.score("test")
        scorer.reset()
        stats = scorer.get_training_stats()
        assert stats["total_misclassifications"] == 0
        assert stats["total_predictions"] == 0
        assert len(scorer.get_keyword_adjustments()) == 0

    def test_adjustment_direction(self, scorer):
        for _ in range(10):
            scorer.record_misclassification("fix auth security issue", 2, 4)
        result = scorer.score("fix auth security issue")
        assert result.adjustment_reason != "no historical adjustment needed"

    def test_no_adjustment_when_accurate(self, scorer):
        for _ in range(5):
            scorer.record_misclassification("simple task", 2, 2)
        result = scorer.score("simple task")
        assert result.base_level == result.adjusted_level or abs(result.base_level - result.adjusted_level) <= 1


class TestConvenienceFunctions:
    def test_score_dynamic(self):
        result = score_dynamic("fix typo")
        assert isinstance(result, DynamicScoreResult)
        assert 1 <= result.level <= 5

    def test_create_scorer(self):
        scorer = create_scorer()
        assert isinstance(scorer, DynamicComplexityScorer)

    def test_score_dynamic_with_custom_scorer(self):
        scorer = create_scorer()
        scorer.record_misclassification("test", 2, 3)
        result = score_dynamic("test", scorer=scorer)
        assert isinstance(result, DynamicScoreResult)
