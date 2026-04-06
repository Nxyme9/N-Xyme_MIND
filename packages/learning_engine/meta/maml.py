"""Meta-Learning — MAML-style adaptation for fast task learning."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Configuration
META_LR = 0.01  # Meta-learning inner loop LR
META_TASKS = 5  # Tasks per meta-update


@dataclass
class MetaParameters:
    """MAML-style meta-parameters for fast adaptation."""

    inner_lr: float = META_LR
    outer_lr: float = 0.001
    task_gradients: dict[str, list[float]] = field(default_factory=dict)


class MetaLearningEngine:
    """MAML-style meta-learning for fast task adaptation.

    Learns a good initialization that can quickly adapt to new tasks
    with few gradient steps.
    """

    def __init__(self, inner_lr: float = META_LR, outer_lr: float = 0.001):
        self.inner_lr = inner_lr
        self.outer_lr = outer_lr
        self._meta_parameters: dict[str, float] = {}
        self._task_gradients: list[dict[str, float]] = []

    def adaptation_step(
        self, task_id: str, support_outcomes: list[dict[str, Any]]
    ) -> dict[str, float]:
        """Perform inner-loop adaptation (few-shot learning).

        Args:
            task_id: The task being adapted to
            support_outcomes: Few examples from this task

        Returns:
            Adapted parameters
        """
        adapted = dict(self._meta_parameters)

        if not support_outcomes:
            return adapted

        for outcome in support_outcomes:
            reward = outcome.get("reward", 0)
            for param in adapted:
                adapted[param] += self.inner_lr * reward * 0.01

        return adapted

    def meta_update(self, query_outcomes: list[dict[str, Any]]) -> None:
        """Perform outer-loop update (meta-gradients).

        Args:
            query_outcomes: Outcomes from adaptation
        """
        if not query_outcomes:
            return

        avg_reward = sum(o.get("reward", 0) for o in query_outcomes) / len(
            query_outcomes
        )

        if not self._meta_parameters:
            self._meta_parameters = {
                "q_learning_rate": 0.1,
                "epsilon": 0.1,
                "gamma": 0.9,
            }

        for key in self._meta_parameters:
            self._meta_parameters[key] += self.outer_lr * (avg_reward - 0.5)

    def get_parameters(self) -> dict[str, float]:
        return self._meta_parameters


__all__ = [
    "MetaParameters",
    "MetaLearningEngine",
    "META_LR",
    "META_TASKS",
]
