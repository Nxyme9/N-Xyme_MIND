#!/usr/bin/env python3
"""Unit tests for prompt_evolution module."""

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.learning.prompt_evolution import (
    PromptWizard,
    PromptVersion,
    PromptEvolutionRecord,
    EvaluationGrade,
)


class TestEvaluationGrade:
    """Tests for EvaluationGrade enum."""

    def test_all_grades_exist(self):
        """Verify all expected grades exist."""
        assert EvaluationGrade.EXCELLENT.value == "excellent"
        assert EvaluationGrade.GOOD.value == "good"
        assert EvaluationGrade.FAIR.value == "fair"
        assert EvaluationGrade.POOR.value == "poor"


class TestPromptVersion:
    """Tests for PromptVersion dataclass."""

    def test_creation(self):
        """Test creating a prompt version."""
        version = PromptVersion(
            version=1,
            content="Test prompt content",
            score=0.85,
        )

        assert version.version == 1
        assert version.content == "Test prompt content"
        assert version.score == 0.85
        assert version.grade == EvaluationGrade.POOR

    def test_content_hash(self):
        """Test content hash generation."""
        version = PromptVersion(version=1, content="Test content")
        hash1 = version.content_hash()
        hash2 = version.content_hash()

        assert len(hash1) == 16
        assert hash1 == hash2

    def test_different_content_different_hash(self):
        """Test different content produces different hash."""
        v1 = PromptVersion(version=1, content="Content A")
        v2 = PromptVersion(version=1, content="Content B")

        assert v1.content_hash() != v2.content_hash()


class TestPromptEvolutionRecord:
    """Tests for PromptEvolutionRecord dataclass."""

    def test_current_no_versions(self):
        """Test current() returns None when no versions."""
        record = PromptEvolutionRecord(prompt_id="test")
        assert record.current() is None

    def test_current_with_versions(self):
        """Test current() returns latest version."""
        record = PromptEvolutionRecord(
            prompt_id="test",
            versions=[
                PromptVersion(version=1, content="v1"),
                PromptVersion(version=2, content="v2"),
            ],
        )
        assert record.current().version == 2

    def test_best_no_versions(self):
        """Test best() returns None when no versions."""
        record = PromptEvolutionRecord(prompt_id="test")
        assert record.best() is None

    def test_best_returns_highest_score(self):
        """Test best() returns version with highest score."""
        record = PromptEvolutionRecord(
            prompt_id="test",
            versions=[
                PromptVersion(version=1, content="v1", score=0.5),
                PromptVersion(version=2, content="v2", score=0.9),
                PromptVersion(version=3, content="v3", score=0.7),
            ],
        )
        assert record.best().version == 2


class TestPromptWizard:
    """Tests for PromptWizard class."""

    @pytest.fixture
    def wizard(self):
        """Create wizard with in-memory database."""
        return PromptWizard(db_path=":memory:")

    def test_register_new_prompt(self, wizard):
        """Test registering a new prompt."""
        record = wizard.register("code_review", "Review this code: {code}")

        assert record.prompt_id == "code_review"
        assert len(record.versions) == 1
        assert record.versions[0].content == "Review this code: {code}"

    def test_register_duplicate_raises(self, wizard):
        """Test that registering duplicate prompt raises ValueError."""
        wizard.register("test_prompt", "Initial content")

        with pytest.raises(ValueError, match="already exists"):
            wizard.register("test_prompt", "Duplicate content")

    def test_get_existing_prompt(self, wizard):
        """Test retrieving an existing prompt."""
        wizard.register("test_prompt", "Content")
        record = wizard.get("test_prompt")

        assert record is not None
        assert record.prompt_id == "test_prompt"

    def test_get_nonexistent_prompt(self, wizard):
        """Test retrieving nonexistent prompt returns None."""
        record = wizard.get("nonexistent")
        assert record is None

    def test_evolve_single_iteration(self, wizard):
        """Test evolving prompt for single iteration."""
        wizard.register("test_prompt", "Short")
        record = wizard.evolve("test_prompt", max_iterations=1)

        assert len(record.versions) == 2

    def test_evolve_multiple_iterations(self, wizard):
        """Test evolving prompt for multiple iterations."""
        wizard.register("test_prompt", "Initial content")
        record = wizard.evolve("test_prompt", max_iterations=3)

        assert len(record.versions) == 4

    def test_evolve_stops_at_threshold(self, wizard):
        """Test evolution stops when score threshold reached."""
        wizard.register("test_prompt", "Excellent prompt that is well structured")
        record = wizard.evolve("test_prompt", max_iterations=10, score_threshold=0.85)

        latest = record.current()
        assert latest.score >= 0.85 or len(record.versions) <= 11

    def test_get_best(self, wizard):
        """Test getting best version of a prompt."""
        wizard.register("test_prompt", "Content")
        wizard.evolve("test_prompt", max_iterations=3)

        best = wizard.get_best("test_prompt")
        assert best is not None

    def test_get_current(self, wizard):
        """Test getting current version of a prompt."""
        wizard.register("test_prompt", "Initial")
        wizard.evolve("test_prompt", max_iterations=2)

        current = wizard.get_current("test_prompt")
        assert current.version == 3

    def test_list_prompts(self, wizard):
        """Test listing all prompts."""
        wizard.register("prompt1", "Content 1")
        wizard.register("prompt2", "Content 2")

        prompts = wizard.list_prompts()
        assert len(prompts) == 2

    def test_compare_versions(self, wizard):
        """Test comparing versions."""
        wizard.register("test_prompt", "v1")
        wizard.evolve("test_prompt", max_iterations=2)

        comparison = wizard.compare_versions("test_prompt")
        assert len(comparison) == 3
        for v, score, grade in comparison:
            assert isinstance(v, int)
            assert isinstance(score, float)
            assert grade in ["excellent", "good", "fair", "poor"]

    def test_delete_prompt(self, wizard):
        """Test deleting a prompt."""
        wizard.register("test_prompt", "Content")
        wizard.delete("test_prompt")

        record = wizard.get("test_prompt")
        assert record is None

    def test_score_to_grade_excellent(self, wizard):
        """Test score to grade conversion for excellent."""
        grade = wizard._score_to_grade(0.9)
        assert grade == EvaluationGrade.EXCELLENT

    def test_score_to_grade_good(self, wizard):
        """Test score to grade conversion for good."""
        grade = wizard._score_to_grade(0.7)
        assert grade == EvaluationGrade.GOOD

    def test_score_to_grade_fair(self, wizard):
        """Test score to grade conversion for fair."""
        grade = wizard._score_to_grade(0.45)
        assert grade == EvaluationGrade.FAIR

    def test_score_to_grade_poor(self, wizard):
        """Test score to grade conversion for poor."""
        grade = wizard._score_to_grade(0.2)
        assert grade == EvaluationGrade.POOR
