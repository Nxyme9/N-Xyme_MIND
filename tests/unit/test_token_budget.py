#!/usr/bin/env python3
"""Unit tests for TokenBudgetTracker - Phase 2.2.

Tests verify token budget enforcement actually works:
- Budget tracking and increments
- Pause/queue behavior when exceeded
- Reset functionality
- Status reporting
"""

import pytest
import sys
import os

# Add project root to path - use absolute path to avoid path issues
# tests/unit/test_token_budget.py -> tests/unit -> tests -> /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
PROJECT_ROOT = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
packages_dir = os.path.join(PROJECT_ROOT, "packages")
assert os.path.exists(os.path.join(packages_dir, "orchestration/token_budget.py")), (
    f"Missing: {packages_dir}"
)

# Import directly to avoid package namespace issues
import importlib.util

spec = importlib.util.spec_from_file_location(
    "token_budget", os.path.join(packages_dir, "orchestration/token_budget.py")
)
token_budget_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(token_budget_module)

TokenBudgetTracker = token_budget_module.TokenBudgetTracker
DEFAULT_BUDGETS = token_budget_module.DEFAULT_BUDGETS


class TestTokenBudgetTrackerInit:
    """Test TokenBudgetTracker initialization."""

    def test_default_initialization(self):
        """Test tracker initializes with default budgets."""
        tracker = TokenBudgetTracker()

        assert tracker._budgets is not None
        assert "hephaestus" in tracker._budgets
        assert "explore" in tracker._budgets
        assert "sisyphus" in tracker._budgets

    def test_default_budgets_values(self):
        """Test default budgets are correctly set."""
        assert DEFAULT_BUDGETS["hephaestus"] == 80000
        assert DEFAULT_BUDGETS["explore"] == 30000
        assert DEFAULT_BUDGETS["sisyphus"] == 50000
        assert DEFAULT_BUDGETS["sisyphus-junior"] == 10000

    def test_usage_starts_empty(self):
        """Test usage dict starts empty."""
        tracker = TokenBudgetTracker()
        assert tracker._usage == {}
        assert len(tracker._usage) == 0


class TestTrackUsage:
    """Test track_usage increments correctly."""

    def test_track_usage_new_agent(self):
        """Test tracking usage for new agent."""
        tracker = TokenBudgetTracker()
        tracker.track_usage("hephaestus", 15000)

        assert tracker._usage["hephaestus"] == 15000

    def test_track_usage_increments(self):
        """Test tracking multiple usages increments correctly."""
        tracker = TokenBudgetTracker()
        tracker.track_usage("hephaestus", 15000)
        tracker.track_usage("hephaestus", 10000)

        assert tracker._usage["hephaestus"] == 25000

    def test_track_usage_multiple_agents(self):
        """Test tracking multiple agents independently."""
        tracker = TokenBudgetTracker()
        tracker.track_usage("hephaestus", 20000)
        tracker.track_usage("explore", 5000)

        assert tracker._usage["hephaestus"] == 20000
        assert tracker._usage["explore"] == 5000


class TestCheckBudget:
    """Test check_budget returns correct allowed/remaining."""

    def test_check_budget_under_limit(self):
        """Test check returns allowed when under budget."""
        tracker = TokenBudgetTracker()
        tracker.track_usage("hephaestus", 50000)

        allowed, remaining = tracker.check_budget("hephaestus")

        assert allowed is True
        assert remaining == 30000  # 80000 - 50000

    def test_check_budget_at_limit(self):
        """Test check returns not allowed at exact limit."""
        tracker = TokenBudgetTracker()
        tracker.track_usage("hephaestus", 80000)

        allowed, remaining = tracker.check_budget("hephaestus")

        assert allowed is False
        assert remaining == 0

    def test_check_budget_over_limit(self):
        """Test check returns not allowed when exceeded."""
        tracker = TokenBudgetTracker()
        tracker.track_usage("hephaestus", 90000)

        allowed, remaining = tracker.check_budget("hephaestus")

        assert allowed is False
        assert remaining == 0

    def test_check_budget_unknown_agent(self):
        """Test default fallback for unknown agent."""
        tracker = TokenBudgetTracker()

        allowed, remaining = tracker.check_budget("unknown-agent")

        # Should use default fallback (50000)
        assert allowed is True
        assert remaining == 50000


class TestIsPaused:
    """Test is_paused returns true when exceeded."""

    def test_is_paused_under_budget(self):
        """Test not paused when under budget."""
        tracker = TokenBudgetTracker()
        tracker.track_usage("hephaestus", 50000)

        is_paused = tracker.is_paused("hephaestus")

        assert is_paused is False

    def test_is_paused_exceeded(self):
        """Test paused when budget exceeded."""
        tracker = TokenBudgetTracker()
        tracker.track_usage("hephaestus", 90000)

        is_paused = tracker.is_paused("hephaestus")

        assert is_paused is True

    def test_is_paused_zero_usage(self):
        """Test not paused with zero usage."""
        tracker = TokenBudgetTracker()

        is_paused = tracker.is_paused("hephaestus")

        assert is_paused is False


class TestResetBudget:
    """Test reset_budget clears usage."""

    def test_reset_budget_specific_agent(self):
        """Test resetting specific agent clears usage."""
        tracker = TokenBudgetTracker()
        tracker.track_usage("hephaestus", 50000)
        tracker.reset_budget("hephaestus")

        assert tracker._usage.get("hephaestus", 0) == 0

    def test_reset_budget_others_unaffected(self):
        """Test reset doesn't affect other agents."""
        tracker = TokenBudgetTracker()
        tracker.track_usage("hephaestus", 50000)
        tracker.track_usage("explore", 10000)
        tracker.reset_budget("hephaestus")

        assert tracker._usage["hephaestus"] == 0
        assert tracker._usage["explore"] == 10000  # Unchanged

    def test_reset_all_clears_all(self):
        """Test reset_all clears all usages."""
        tracker = TokenBudgetTracker()
        tracker.track_usage("hephaestus", 50000)
        tracker.track_usage("explore", 10000)
        tracker.reset_all()

        assert len(tracker._usage) == 0


class TestGetStatus:
    """Test get_status returns full status."""

    def test_get_status_under_budget(self):
        """Test status returns correct values under budget."""
        tracker = TokenBudgetTracker()
        tracker.track_usage("hephaestus", 32000)

        status = tracker.get_status("hephaestus")

        assert status["agent"] == "hephaestus"
        assert status["budget"] == 80000
        assert status["used"] == 32000
        assert status["remaining"] == 48000
        assert status["percentage"] == 40.0
        assert status["exceeded"] is False

    def test_get_status_exceeded(self):
        """Test status shows exceeded when over budget."""
        tracker = TokenBudgetTracker()
        tracker.track_usage("hephaestus", 90000)

        status = tracker.get_status("hephaestus")

        assert status["used"] == 90000
        assert status["remaining"] == 0
        assert status["percentage"] == 112.5
        assert status["exceeded"] is True

    def test_get_status_unknown_agent(self):
        """Test status for unknown agent uses default."""
        tracker = TokenBudgetTracker()

        status = tracker.get_status("new-agent")

        assert status["budget"] == 50000  # Default
        assert status["used"] == 0
        assert status["remaining"] == 50000


class TestGetAllStatus:
    """Test get_all_status returns all agents."""

    def test_get_all_status_returns_budget_keys(self):
        """Test returns status for all known agents."""
        tracker = TokenBudgetTracker()

        all_status = tracker.get_all_status()

        # Should have all budget keys
        for agent in DEFAULT_BUDGETS:
            assert agent in all_status


class TestIntegration:
    """Integration tests - real budget enforcement."""

    def test_full_budget_lifecycle(self):
        """Test complete budget lifecycle."""
        tracker = TokenBudgetTracker()
        agent = "hephaestus"

        # Start: allowed
        allowed, _ = tracker.check_budget(agent)
        assert allowed is True

        # Track usage up to limit
        tracker.track_usage(agent, 80000)

        # At limit: not allowed
        allowed, _ = tracker.check_budget(agent)
        assert allowed is False

        # is_paused should be true
        assert tracker.is_paused(agent) is True

        # Reset
        tracker.reset_budget(agent)

        # After reset: allowed again
        allowed, _ = tracker.check_budget(agent)
        assert allowed is True
        assert tracker.is_paused(agent) is False

    def test_all_agent_types_track(self):
        """Test all agent types can track usage."""
        tracker = TokenBudgetTracker()

        for agent in DEFAULT_BUDGETS:
            budget = DEFAULT_BUDGETS[agent]
            tracker.track_usage(agent, budget // 2)  # Use half

            allowed, remaining = tracker.check_budget(agent)
            assert allowed is True
            assert remaining == budget // 2


if __name__ == "__main__":
    # Run with pytest
    sys.exit(pytest.main([__file__, "-v"]))
