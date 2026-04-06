"""Elastic Weight Consolidation — Prevent catastrophic forgetting in continual learning."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Configuration
DEFAULT_LAMBDA = 0.01  # EWC regularization strength


@dataclass
class EWCParams:
    """Elastic Weight Consolidation parameters."""

    fisher_diagonal: dict[str, float] = field(default_factory=dict)
    optimal_params: dict[str, float] = field(default_factory=dict)
    lambda_reg: float = DEFAULT_LAMBDA


class EWCEngine:
    """Elastic Weight Consolidation for continual learning.

    Prevents catastrophic forgetting by penalizing changes to
    important parameters (Fisher information).
    """

    def __init__(self, lambda_reg: float = DEFAULT_LAMBDA):
        self.lambda_reg = lambda_reg
        self._fisher_diagonal: dict[str, float] = {}
        self._optimal_params: dict[str, float] = {}
        self._task_count = 0

    def compute_penalty(self, current_params: dict[str, float]) -> float:
        """Compute EWC penalty for current parameters."""
        if not self._optimal_params:
            return 0.0

        penalty = 0.0
        for key, current in current_params.items():
            if key in self._fisher_diagonal:
                optimal = self._optimal_params.get(key, 0.0)
                penalty += self._fisher_diagonal[key] * (current - optimal) ** 2

        return 0.5 * self.lambda_reg * penalty

    def update_after_task(
        self, task_params: dict[str, float], outcomes: list[dict[str, Any]]
    ) -> None:
        """Update Fisher information after completing a task."""
        self._task_count += 1

        self._optimal_params = dict(task_params)

        if outcomes:
            rewards = [o.get("reward", 0) for o in outcomes]
            variance = sum(
                (r - sum(rewards) / len(rewards)) ** 2 for r in rewards
            ) / len(rewards)

            for key in task_params:
                self._fisher_diagonal[key] = variance + 0.01


__all__ = [
    "EWCParams",
    "EWCEngine",
    "DEFAULT_LAMBDA",
]
