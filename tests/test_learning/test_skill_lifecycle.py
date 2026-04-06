#!/usr/bin/env python3
"""Unit tests for skill_lifecycle module."""

import pytest
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.learning.skill_lifecycle import (
    SkillLifecycleManager,
    Skill,
    SkillState,
    SkillMetrics,
    _VALID_TRANSITIONS,
)


class TestSkillState:
    """Tests for SkillState enum."""

    def test_all_states_exist(self):
        """Verify all expected states exist."""
        assert SkillState.PROPOSED.value == "proposed"
        assert SkillState.EXPERIMENTAL.value == "experimental"
        assert SkillState.ACTIVE.value == "active"
        assert SkillState.DEPRECATED.value == "deprecated"
        assert SkillState.ARCHIVED.value == "archived"


class TestSkillMetrics:
    """Tests for SkillMetrics dataclass."""

    def test_initial_values(self):
        """Test default metric values."""
        metrics = SkillMetrics()
        assert metrics.success_rate == 0.0
        assert metrics.avg_latency_ms == 0.0
        assert metrics.total_cost == 0.0
        assert metrics.invocation_count == 0

    def test_update_success(self):
        """Test updating metrics with successful invocation."""
        metrics = SkillMetrics()
        metrics.update(success=True, latency_ms=100.0, cost=0.01)

        assert metrics.success_rate == 1.0
        assert metrics.avg_latency_ms == 100.0
        assert metrics.total_cost == 0.01
        assert metrics.invocation_count == 1

    def test_update_failure(self):
        """Test updating metrics with failed invocation."""
        metrics = SkillMetrics()
        metrics.update(success=False, latency_ms=50.0, cost=0.005)

        assert metrics.success_rate == 0.0
        assert metrics.avg_latency_ms == 50.0
        assert metrics.total_cost == 0.005

    def test_update_running_average(self):
        """Test running average calculations."""
        metrics = SkillMetrics()
        metrics.update(success=True, latency_ms=100.0, cost=0.01)
        metrics.update(success=False, latency_ms=200.0, cost=0.02)

        assert metrics.success_rate == 0.5
        assert metrics.avg_latency_ms == 150.0
        assert metrics.invocation_count == 2


class TestValidTransitions:
    """Tests for valid state transitions."""

    def test_proposed_transitions(self):
        """Test transitions from PROPOSED state."""
        assert SkillState.EXPERIMENTAL in _VALID_TRANSITIONS[SkillState.PROPOSED]
        assert SkillState.ARCHIVED in _VALID_TRANSITIONS[SkillState.PROPOSED]

    def test_experimental_transitions(self):
        """Test transitions from EXPERIMENTAL state."""
        valid = _VALID_TRANSITIONS[SkillState.EXPERIMENTAL]
        assert SkillState.ACTIVE in valid
        assert SkillState.DEPRECATED in valid
        assert SkillState.ARCHIVED in valid

    def test_active_transitions(self):
        """Test transitions from ACTIVE state."""
        valid = _VALID_TRANSITIONS[SkillState.ACTIVE]
        assert SkillState.DEPRECATED in valid
        assert SkillState.EXPERIMENTAL in valid


class TestSkillLifecycleManager:
    """Tests for SkillLifecycleManager."""

    @pytest.fixture
    def manager(self):
        """Create manager with in-memory database."""
        return SkillLifecycleManager(db_path=":memory:")

    def test_register_new_skill(self, manager):
        """Test registering a new skill."""
        skill = manager.register("code_review", "Automated code review")

        assert skill.name == "code_review"
        assert skill.description == "Automated code review"
        assert skill.state == SkillState.PROPOSED

    def test_register_duplicate_raises(self, manager):
        """Test that registering duplicate skill raises ValueError."""
        manager.register("test_skill", "Test description")

        with pytest.raises(ValueError, match="already exists"):
            manager.register("test_skill", "Duplicate")

    def test_get_existing_skill(self, manager):
        """Test retrieving an existing skill."""
        manager.register("test_skill", "Test")
        skill = manager.get("test_skill")

        assert skill is not None
        assert skill.name == "test_skill"

    def test_get_nonexistent_skill(self, manager):
        """Test retrieving non-existent skill returns None."""
        skill = manager.get("nonexistent")
        assert skill is None

    def test_valid_transition(self, manager):
        """Test valid state transition."""
        manager.register("test_skill", "Test")
        skill = manager.transition("test_skill", SkillState.EXPERIMENTAL)

        assert skill.state == SkillState.EXPERIMENTAL

    def test_invalid_transition_raises(self, manager):
        """Test that invalid transition raises ValueError."""
        manager.register("test_skill", "Test")

        with pytest.raises(ValueError, match="Cannot transition"):
            manager.transition(
                "test_skill", SkillState.ACTIVE
            )  # Cannot go directly from proposed to active

    def test_record_outcome(self, manager):
        """Test recording skill invocation outcome."""
        manager.register("test_skill", "Test")
        metrics = manager.record_outcome(
            "test_skill", success=True, latency_ms=100.0, cost=0.01
        )

        assert metrics.invocation_count == 1
        assert metrics.success_rate == 1.0

    def test_evaluate_promotion_experimental_to_active(self, manager):
        """Test auto-promotion from EXPERIMENTAL to ACTIVE."""
        manager.register("test_skill", "Test")
        manager.transition("test_skill", SkillState.EXPERIMENTAL)

        # Record 10 successful outcomes
        for _ in range(10):
            manager.record_outcome(
                "test_skill", success=True, latency_ms=100.0, cost=0.01
            )

        promoted = manager.evaluate_promotion("test_skill")
        assert promoted is True

        skill = manager.get("test_skill")
        assert skill.state == SkillState.ACTIVE

    def test_evaluate_promotion_insufficient_invocations(self, manager):
        """Test that promotion requires minimum invocations."""
        manager.register("test_skill", "Test")
        manager.transition("test_skill", SkillState.EXPERIMENTAL)

        # Record only 5 successful outcomes (need 10)
        for _ in range(5):
            manager.record_outcome(
                "test_skill", success=True, latency_ms=100.0, cost=0.01
            )

        promoted = manager.evaluate_promotion("test_skill")
        assert promoted is False

    def test_list_skills_all(self, manager):
        """Test listing all skills."""
        manager.register("skill1", "Desc1")
        manager.register("skill2", "Desc2")

        skills = manager.list_skills()
        assert len(skills) == 2

    def test_list_skills_filtered(self, manager):
        """Test filtering skills by state."""
        manager.register("skill1", "Desc1")
        manager.register("skill2", "Desc2")
        manager.transition("skill2", SkillState.EXPERIMENTAL)

        proposed = manager.list_skills(state=SkillState.PROPOSED)
        experimental = manager.list_skills(state=SkillState.EXPERIMENTAL)

        assert len(proposed) == 1
        assert len(experimental) == 1

    def test_get_transition_history(self, manager):
        """Test retrieving transition history."""
        manager.register("test_skill", "Test")
        manager.transition("test_skill", SkillState.EXPERIMENTAL, reason="Initial test")

        history = manager.get_transition_history("test_skill")
        assert len(history) == 1
        assert history[0]["from"] == "proposed"
        assert history[0]["to"] == "experimental"

    def test_delete_skill(self, manager):
        """Test deleting a skill."""
        manager.register("test_skill", "Test")
        manager.delete("test_skill")

        skill = manager.get("test_skill")
        assert skill is None
