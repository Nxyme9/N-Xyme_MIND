"""Token Budget Tracker - Phase 2.2 of masterplan.

Per-agent token budgets to prevent runaway consumption by single agent.

Config: Defaults are hardcoded. Override via configs/agent_budgets.json

Usage:
    from packages.orchestration.token_budget import TokenBudgetTracker

    tracker = TokenBudgetTracker()
    tracker.track_usage("hephaestus", 15000)
    allowed, remaining = tracker.check_budget("hephaestus")
"""

import json
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


# Default budgets per agent type (from opencode.json background_task config)
DEFAULT_BUDGETS: Dict[str, int] = {
    "sisyphus": 50000,
    "oracle": 50000,
    "prometheus": 50000,
    "metis": 50000,
    "momus": 50000,
    "hephaestus": 80000,
    "atlas": 80000,
    "explore": 30000,
    "librarian": 30000,
    "sisyphus-junior": 10000,
}


class TokenBudgetTracker:
    """Tracks token usage per agent and enforces budget limits.

    Acts as middleware - does not break existing delegation, just
    prevents new tasks when budget exceeded.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize tracker with optional config override.

        Args:
            config_path: Path to config file for budget config (optional).
                         Defaults to configs/agent_budgets.json in project root.
        """
        self._usage: Dict[str, int] = {}
        self._budgets = DEFAULT_BUDGETS.copy()

        # Try to load from custom config if exists
        if config_path:
            self._load_from_config(config_path)
        else:
            # Try default location: configs/agent_budgets.json
            default_path = Path.cwd() / "configs" / "agent_budgets.json"
            if default_path.exists():
                self._load_from_config(str(default_path))

    def _load_from_config(self, config_path: str) -> None:
        """Load per_agent_budgets from config file.

        Supports both:
        - New format: configs/agent_budgets.json with {"per_agent_budgets": {...}}
        - Legacy format: opencode.json with {"background_task": {"per_agent_budgets": {...}}}
        """
        try:
            with open(config_path, "r") as f:
                config = json.load(f)

            # Try new format first (configs/agent_budgets.json)
            budgets = config.get("per_agent_budgets", {})

            # Fallback to legacy format (opencode.json)
            if not budgets:
                bg_task = config.get("background_task", {})
                budgets = bg_task.get("per_agent_budgets", {})

            if budgets:
                self._budgets.update(budgets)
                logger.info(f"Loaded budgets from {config_path}: {budgets}")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Could not load budgets from {config_path}: {e}")

    def track_usage(self, agent: str, tokens_used: int) -> None:
        """Track token usage for an agent.

        Args:
            agent: Agent name (e.g., "hephaestus", "explore")
            tokens_used: Number of tokens consumed
        """
        if agent not in self._usage:
            self._usage[agent] = 0

        self._usage[agent] += tokens_used
        logger.debug(
            f"Agent '{agent}' used {tokens_used} tokens. Total: {self._usage[agent]}"
        )

    def check_budget(self, agent: str) -> Tuple[bool, int]:
        """Check if agent can be dispatched (budget not exceeded).

        Args:
            agent: Agent name to check

        Returns:
            Tuple of (allowed: bool, remaining: int)
            - allowed: True if agent can be dispatched
            - remaining: Remaining budget tokens (0 if exceeded)
        """
        budget = self._budgets.get(agent, 50000)  # Default fallback
        used = self._usage.get(agent, 0)
        remaining = max(0, budget - used)

        allowed = remaining > 0
        return allowed, remaining

    def get_status(self, agent: str) -> Dict[str, any]:
        """Get full budget status for an agent.

        Args:
            agent: Agent name

        Returns:
            Dict with budget, used, remaining, percentage
        """
        budget = self._budgets.get(agent, 50000)
        used = self._usage.get(agent, 0)
        remaining = max(0, budget - used)
        percentage = (used / budget * 100) if budget > 0 else 0

        return {
            "agent": agent,
            "budget": budget,
            "used": used,
            "remaining": remaining,
            "percentage": round(percentage, 1),
            "exceeded": used > budget,
        }

    def reset_budget(self, agent: str) -> None:
        """Reset budget for a specific agent.

        Args:
            agent: Agent name to reset
        """
        if agent in self._usage:
            self._usage[agent] = 0
            logger.info(f"Reset budget for agent '{agent}'")

    def reset_all(self) -> None:
        """Reset all agent budgets."""
        self._usage.clear()
        logger.info("Reset all agent budgets")

    def get_all_status(self) -> Dict[str, Dict[str, any]]:
        """Get status for all agents with usage.

        Returns:
            Dict mapping agent name to status dict
        """
        status = {}
        for agent in self._budgets:
            status[agent] = self.get_status(agent)
        return status

    def is_paused(self, agent: str) -> bool:
        """Check if agent is paused due to budget exceeded.

        Args:
            agent: Agent name

        Returns:
            True if agent should be paused/queued
        """
        allowed, _ = self.check_budget(agent)
        return not allowed


# Global singleton instance for easy import
_global_tracker: Optional[TokenBudgetTracker] = None


def get_tracker() -> TokenBudgetTracker:
    """Get or create global TokenBudgetTracker instance."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = TokenBudgetTracker()
    return _global_tracker


def track_usage(agent: str, tokens_used: int) -> None:
    """Convenience function to track usage via global tracker."""
    get_tracker().track_usage(agent, tokens_used)


def check_budget(agent: str) -> Tuple[bool, int]:
    """Convenience function to check budget via global tracker."""
    return get_tracker().check_budget(agent)


def is_paused(agent: str) -> bool:
    """Convenience function to check if agent is paused via global tracker."""
    return get_tracker().is_paused(agent)


# Export public API
__all__ = [
    "TokenBudgetTracker",
    "DEFAULT_BUDGETS",
    "get_tracker",
    "track_usage",
    "check_budget",
    "is_paused",
]
