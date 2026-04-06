"""Budget Tracker — Token budget tracking with continuation counting.

Adapted from ant-source-code tokenBudget.ts pattern.
Tracks continuation counts, diminishing returns, and budget thresholds.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BudgetState:
    """Current budget state with tracking metrics."""

    total_budget: int = 0
    used_budget: int = 0
    continuation_count: int = 0
    last_delta_tokens: int = 0
    start_time: float = 0.0
    last_update_time: float = 0.0
    warning_threshold: float = 0.8  # 80% of budget
    diminishing_returns_threshold: int = 3  # After N continuations

    @property
    def remaining_budget(self) -> int:
        """Remaining budget."""
        return max(0, self.total_budget - self.used_budget)

    @property
    def usage_percentage(self) -> float:
        """Budget usage as percentage."""
        if self.total_budget == 0:
            return 0.0
        return self.used_budget / self.total_budget

    @property
    def is_near_limit(self) -> bool:
        """Check if budget is near limit."""
        return self.usage_percentage >= self.warning_threshold

    @property
    def is_diminishing_returns(self) -> bool:
        """Check if we're experiencing diminishing returns."""
        return self.continuation_count >= self.diminishing_returns_threshold

    def record_usage(self, tokens_used: int) -> None:
        """Record token usage.

        Args:
            tokens_used: Number of tokens used
        """
        self.last_delta_tokens = tokens_used
        self.used_budget += tokens_used
        self.last_update_time = time.time()

    def record_continuation(self) -> None:
        """Record a continuation event."""
        self.continuation_count += 1

    def get_nudge_message(self) -> Optional[str]:
        """Get a nudge message if budget is constrained.

        Returns:
            Nudge message or None
        """
        if self.is_near_limit:
            return f"Budget warning: {self.usage_percentage:.0%} used. Consider wrapping up."
        if self.is_diminishing_returns:
            return f"Continuation warning: {self.continuation_count} continuations. Consider stopping."
        return None

    def reset(self) -> None:
        """Reset budget state."""
        self.used_budget = 0
        self.continuation_count = 0
        self.last_delta_tokens = 0
        self.start_time = time.time()
        self.last_update_time = time.time()


class BudgetTracker:
    """Tracks token budgets across sessions and continuations."""

    def __init__(self, default_budget: int = 100000):
        """Initialize budget tracker.

        Args:
            default_budget: Default token budget
        """
        self.default_budget = default_budget
        self._sessions: dict[str, BudgetState] = {}

    def get_session(self, session_id: str) -> BudgetState:
        """Get or create budget state for a session.

        Args:
            session_id: Session ID

        Returns:
            Budget state for session
        """
        if session_id not in self._sessions:
            state = BudgetState(
                total_budget=self.default_budget,
                start_time=time.time(),
                last_update_time=time.time(),
            )
            self._sessions[session_id] = state
        return self._sessions[session_id]

    def record_usage(self, session_id: str, tokens_used: int) -> None:
        """Record token usage for a session.

        Args:
            session_id: Session ID
            tokens_used: Number of tokens used
        """
        state = self.get_session(session_id)
        state.record_usage(tokens_used)

    def record_continuation(self, session_id: str) -> None:
        """Record a continuation for a session.

        Args:
            session_id: Session ID
        """
        state = self.get_session(session_id)
        state.record_continuation()

    def get_status(self, session_id: str) -> dict:
        """Get budget status for a session.

        Args:
            session_id: Session ID

        Returns:
            Budget status dictionary
        """
        state = self.get_session(session_id)
        return {
            "total_budget": state.total_budget,
            "used_budget": state.used_budget,
            "remaining_budget": state.remaining_budget,
            "usage_percentage": round(state.usage_percentage, 4),
            "continuation_count": state.continuation_count,
            "is_near_limit": state.is_near_limit,
            "is_diminishing_returns": state.is_diminishing_returns,
            "nudge_message": state.get_nudge_message(),
        }

    def reset_session(self, session_id: str) -> None:
        """Reset budget for a session.

        Args:
            session_id: Session ID
        """
        if session_id in self._sessions:
            self._sessions[session_id].reset()


# Global tracker
_tracker = BudgetTracker()


def get_budget_tracker() -> BudgetTracker:
    """Get the global budget tracker.

    Returns:
        Global budget tracker instance
    """
    return _tracker
