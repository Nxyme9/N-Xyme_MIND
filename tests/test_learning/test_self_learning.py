#!/usr/bin/env python3
"""Unit tests for self_learning module."""

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.learning.self_learning import (
    SelfLearner,
    LearningOutcome,
    ExtractedPattern,
    Adaptation,
    OutcomeStatus,
)


class TestLearningOutcome:
    """Tests for LearningOutcome dataclass."""

    def test_creation(self):
        """Test creating a learning outcome."""
        outcome = LearningOutcome(
            task_id="task1",
            action="action1",
            success=True,
            reward=1.0,
            latency_ms=100.0,
            cost=0.01,
        )

        assert outcome.task_id == "task1"
        assert outcome.action == "action1"
        assert outcome.success is True
        assert outcome.reward == 1.0

    def test_to_dict(self):
        """Test serialization to dictionary."""
        outcome = LearningOutcome(
            task_id="task1",
            action="action1",
            success=True,
        )
        d = outcome.to_dict()

        assert isinstance(d, dict)
        assert d["task_id"] == "task1"
        assert d["success"] is True


class TestExtractedPattern:
    """Tests for ExtractedPattern dataclass."""

    def test_initial_values(self):
        """Test default pattern values."""
        pattern = ExtractedPattern(
            pattern_id="test:action",
            task="test",
            action="action",
        )

        assert pattern.success_count == 0
        assert pattern.failure_count == 0
        assert pattern.total_trials == 0

    def test_total_trials(self):
        """Test total_trials property."""
        pattern = ExtractedPattern(
            pattern_id="test:action",
            task="test",
            action="action",
            success_count=5,
            failure_count=3,
        )

        assert pattern.total_trials == 8

    def test_success_rate(self):
        """Test success_rate property."""
        pattern = ExtractedPattern(
            pattern_id="test:action",
            task="test",
            action="action",
            success_count=7,
            failure_count=3,
        )

        assert pattern.success_rate == 0.7

    def test_success_rate_zero_trials(self):
        """Test success_rate with no trials."""
        pattern = ExtractedPattern(
            pattern_id="test:action",
            task="test",
            action="action",
        )

        assert pattern.success_rate == 0.0


class TestSelfLearner:
    """Tests for SelfLearner class."""

    @pytest.fixture
    def learner(self):
        """Create learner with in-memory database."""
        return SelfLearner(db_path=":memory:")

    def test_record_outcome(self, learner):
        """Test recording an outcome."""
        outcome = learner.record_outcome(
            task_id="code_review",
            action="static_analysis",
            success=True,
            reward=1.0,
            latency_ms=150.0,
            cost=0.02,
        )

        assert outcome.task_id == "code_review"
        assert outcome.action == "static_analysis"
        assert outcome.success is True

    def test_get_outcomes_all(self, learner):
        """Test retrieving all outcomes."""
        learner.record_outcome("task1", "action1", True)
        learner.record_outcome("task2", "action2", False)

        outcomes = learner.get_outcomes()
        assert len(outcomes) == 2

    def test_get_outcomes_filter_task(self, learner):
        """Test filtering outcomes by task_id."""
        learner.record_outcome("task1", "action1", True)
        learner.record_outcome("task2", "action2", False)
        learner.record_outcome("task1", "action3", True)

        outcomes = learner.get_outcomes(task_id="task1")
        assert len(outcomes) == 2

    def test_get_outcomes_filter_success(self, learner):
        """Test filtering outcomes by success."""
        learner.record_outcome("task1", "action1", True)
        learner.record_outcome("task2", "action2", False)

        successes = learner.get_outcomes(success=True)
        failures = learner.get_outcomes(success=False)

        assert len(successes) == 1
        assert len(failures) == 1

    def test_outcome_count(self, learner):
        """Test outcome counting."""
        learner.record_outcome("task1", "action1", True)
        learner.record_outcome("task1", "action2", False)

        count = learner.outcome_count()
        assert count == 2

    def test_extract_patterns(self, learner):
        """Test pattern extraction."""
        learner.record_outcome("task1", "action1", True)
        learner.record_outcome("task1", "action1", True)
        learner.record_outcome("task1", "action1", False)

        patterns = learner.extract_patterns(min_occurrences=2)
        assert len(patterns) == 1
        assert patterns[0].success_rate == 2 / 3

    def test_get_pattern(self, learner):
        """Test retrieving specific pattern."""
        learner.record_outcome("task1", "action1", True)

        pattern = learner.get_pattern("task1", "action1")
        assert pattern is not None
        assert pattern.task == "task1"

    def test_get_pattern_nonexistent(self, learner):
        """Test retrieving nonexistent pattern."""
        pattern = learner.get_pattern("nonexistent", "action")
        assert pattern is None

    def test_get_best_action(self, learner):
        """Test getting best action for a task."""
        learner.record_outcome("task1", "good_action", True)
        learner.record_outcome("task1", "good_action", True)
        learner.record_outcome("task1", "bad_action", False)

        best = learner.get_best_action("task1")
        assert best == "good_action"

    def test_get_best_action_no_patterns(self, learner):
        """Test getting best action with no patterns."""
        best = learner.get_best_action("nonexistent")
        assert best is None

    def test_adapt(self, learner):
        """Test adaptation creation."""
        learner.record_outcome("task1", "action1", True)
        learner.record_outcome("task1", "action1", True)
        learner.record_outcome("task1", "action2", False)

        adaptation = learner.adapt("task1", current_action="action2")
        assert adaptation is not None
        assert adaptation.new_action == "action1"

    def test_adapt_no_improvement(self, learner):
        """Test adaptation returns None when no improvement."""
        learner.record_outcome("task1", "action1", True)
        learner.record_outcome("task1", "action1", True)
        learner.record_outcome("task1", "action2", True)

        adaptation = learner.adapt("task1", current_action="action1")
        assert adaptation is None

    def test_task_status_learning(self, learner):
        """Test task status when still learning."""
        for _ in range(3):
            learner.record_outcome("task1", "action1", True)

        status = learner.task_status("task1")
        assert status["status"] == OutcomeStatus.LEARNING.value

    def test_task_status_stable(self, learner):
        """Test task status when stable."""
        for _ in range(10):
            learner.record_outcome("task1", "action1", True)

        status = learner.task_status("task1")
        assert status["status"] == OutcomeStatus.STABLE.value

    def test_clear_outcomes_all(self, learner):
        """Test clearing all outcomes."""
        learner.record_outcome("task1", "action1", True)
        learner.record_outcome("task2", "action2", False)

        count = learner.clear_outcomes()
        assert count == 2
        assert learner.outcome_count() == 0

    def test_clear_outcomes_specific(self, learner):
        """Test clearing outcomes for specific task."""
        learner.record_outcome("task1", "action1", True)
        learner.record_outcome("task2", "action2", False)

        count = learner.clear_outcomes("task1")
        assert count == 1
        assert learner.outcome_count() == 1
