"""Unit tests for tools.learning.self_learning."""

import pytest
import tempfile
import os
from src.tools.learning.self_learning import (
    OutcomeStatus,
    LearningOutcome,
    ExtractedPattern,
    Adaptation,
    SelfLearner,
    _context_signature,
    _coerce,
)


class TestOutcomeStatus:
    """Test OutcomeStatus enum."""

    def test_outcome_status_values(self):
        """Test OutcomeStatus has expected values."""
        assert OutcomeStatus.LEARNING.value == "learning"
        assert OutcomeStatus.STABLE.value == "stable"
        assert OutcomeStatus.REGRESSING.value == "regressing"
        assert OutcomeStatus.OPTIMIZED.value == "optimized"


class TestLearningOutcome:
    """Test LearningOutcome dataclass."""

    def test_learning_outcome_creation(self):
        """Test LearningOutcome creation."""
        outcome = LearningOutcome(
            task_id="test_task",
            action="test_action",
            success=True,
            reward=1.0,
            latency_ms=100.0,
            cost=0.5,
        )
        assert outcome.task_id == "test_task"
        assert outcome.action == "test_action"
        assert outcome.success is True
        assert outcome.reward == 1.0

    def test_learning_outcome_to_dict(self):
        """Test LearningOutcome serialization."""
        outcome = LearningOutcome(
            task_id="test_task",
            action="test_action",
            success=True,
        )
        result = outcome.to_dict()
        assert isinstance(result, dict)
        assert result["task_id"] == "test_task"
        assert result["success"] is True


class TestExtractedPattern:
    """Test ExtractedPattern dataclass."""

    def test_extracted_pattern_creation(self):
        """Test ExtractedPattern creation."""
        pattern = ExtractedPattern(
            pattern_id="pattern_1",
            task="test_task",
            action="test_action",
            success_count=10,
            failure_count=2,
        )
        assert pattern.pattern_id == "pattern_1"
        assert pattern.success_count == 10

    def test_extracted_pattern_total_trials(self):
        """Test total_trials property."""
        pattern = ExtractedPattern(
            pattern_id="pattern_1",
            task="test",
            action="test",
            success_count=5,
            failure_count=3,
        )
        assert pattern.total_trials == 8

    def test_extracted_pattern_success_rate(self):
        """Test success_rate property."""
        pattern = ExtractedPattern(
            pattern_id="pattern_1",
            task="test",
            action="test",
            success_count=7,
            failure_count=3,
        )
        assert pattern.success_rate == 0.7

    def test_extracted_pattern_success_rate_zero(self):
        """Test success_rate when no trials."""
        pattern = ExtractedPattern(
            pattern_id="pattern_1",
            task="test",
            action="test",
        )
        assert pattern.success_rate == 0.0

    def test_extracted_pattern_update(self):
        """Test pattern update with outcome."""
        pattern = ExtractedPattern(
            pattern_id="pattern_1",
            task="test",
            action="test",
            success_count=1,
            failure_count=1,
        )
        outcome = LearningOutcome(
            task_id="test",
            action="test",
            success=True,
            reward=1.0,
            latency_ms=100.0,
            cost=0.5,
        )
        pattern.update(outcome)
        assert pattern.success_count == 2
        assert pattern.total_trials == 3

    def test_extracted_pattern_to_dict(self):
        """Test ExtractedPattern serialization."""
        pattern = ExtractedPattern(
            pattern_id="pattern_1",
            task="test",
            action="test",
        )
        result = pattern.to_dict()
        assert isinstance(result, dict)
        assert result["pattern_id"] == "pattern_1"


class TestAdaptation:
    """Test Adaptation dataclass."""

    def test_adaptation_creation(self):
        """Test Adaptation creation."""
        adaptation = Adaptation(
            task_id="test_task",
            old_action="old_action",
            new_action="new_action",
            reason="better performance",
            expected_improvement=0.2,
        )
        assert adaptation.task_id == "test_task"
        assert adaptation.old_action == "old_action"
        assert adaptation.new_action == "new_action"

    def test_adaptation_to_dict(self):
        """Test Adaptation serialization."""
        adaptation = Adaptation(
            task_id="test_task",
            old_action="old",
            new_action="new",
            reason="reason",
        )
        result = adaptation.to_dict()
        assert isinstance(result, dict)
        assert result["task_id"] == "test_task"


class TestHelperFunctions:
    """Test helper functions."""

    def test_context_signature_empty(self):
        """Test context signature with empty dict."""
        assert _context_signature({}) == "empty"

    def test_context_signature_with_values(self):
        """Test context signature with values."""
        ctx = {"key1": "value1", "key2": 123}
        sig = _context_signature(ctx)
        assert "key1" in sig
        assert "key2" in sig

    def test_coerce_bool(self):
        """Test coerce with bool."""
        assert _coerce(True) == "1"
        assert _coerce(False) == "0"

    def test_coerce_numeric(self):
        """Test coerce with numeric."""
        assert _coerce(42) == "42"
        assert _coerce(3.14) == "3.14"

    def test_coerce_string(self):
        """Test coerce with string."""
        assert _coerce("hello") == "hello"


class TestSelfLearner:
    """Test SelfLearner class."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def learner(self, temp_db):
        """Create SelfLearner instance."""
        return SelfLearner(db_path=temp_db)

    def test_self_learner_init(self, learner):
        """Test SelfLearner initialization."""
        assert learner is not None

    def test_record_outcome(self, learner):
        """Test recording an outcome."""
        learner.record_outcome(
            task_id="test_task",
            action="test_action",
            success=True,
            reward=1.0,
            latency_ms=100.0,
            cost=0.5,
        )

    def test_record_outcome_with_context(self, learner):
        """Test recording outcome with context."""
        learner.record_outcome(
            task_id="test_task",
            action="test_action",
            success=True,
            context={"key": "value"},
        )

    def test_get_outcomes(self, learner):
        """Test retrieving outcomes."""
        learner.record_outcome(
            task_id="test_task",
            action="test_action",
            success=True,
        )
        outcomes = learner.get_outcomes(limit=10)
        assert isinstance(outcomes, list)

    def test_outcome_count(self, learner):
        """Test outcome count."""
        learner.record_outcome(
            task_id="test_task",
            action="test_action",
            success=True,
        )
        count = learner.outcome_count()
        assert count >= 1

    def test_get_best_action(self, learner):
        """Test getting best action."""
        # Record multiple outcomes to establish a pattern
        learner.record_outcome(
            task_id="test_task",
            action="good_action",
            success=True,
            reward=1.0,
        )
        learner.record_outcome(
            task_id="test_task",
            action="good_action",
            success=True,
            reward=1.0,
        )
        learner.record_outcome(
            task_id="test_task",
            action="bad_action",
            success=False,
            reward=-1.0,
        )
        best = learner.get_best_action("test_task")
        assert best == "good_action"

    def test_task_status(self, learner):
        """Test task status."""
        learner.record_outcome(
            task_id="test_task",
            action="test_action",
            success=True,
            reward=1.0,
        )
        status = learner.task_status("test_task")
        assert isinstance(status, dict)


class TestSelfLearnerImports:
    """Test module imports."""

    def test_import_self_learner(self):
        """Test SelfLearner can be imported."""
        from src.tools.learning.self_learning import SelfLearner

        assert SelfLearner is not None

    def test_import_learning_outcome(self):
        """Test LearningOutcome can be imported."""
        from src.tools.learning.self_learning import LearningOutcome

        assert LearningOutcome is not None

    def test_import_outcome_status(self):
        """Test OutcomeStatus can be imported."""
        from src.tools.learning.self_learning import OutcomeStatus

        assert OutcomeStatus is not None
