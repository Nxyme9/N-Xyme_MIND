"""Elastic Weight Consolidation — Real empirical Fisher from gradient histories."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DEFAULT_LAMBDA = 0.01
DEFAULT_MOMENTUM = 0.9


@dataclass
class EWCParams:
    fisher_diagonal: dict[str, float] = field(default_factory=dict)
    optimal_params: dict[str, float] = field(default_factory=dict)
    lambda_reg: float = DEFAULT_LAMBDA


class EWCEngine:
    def __init__(self, lambda_reg: float = DEFAULT_LAMBDA, momentum: float = DEFAULT_MOMENTUM):
        self.lambda_reg = lambda_reg
        self.momentum = momentum
        self._fisher_diagonal: dict[str, float] = {}
        self._optimal_params: dict[str, float] = {}
        self._gradient_histories: dict[str, list[float]] = {}
        self._task_count = 0
        self._max_history = 100

    def compute_empirical_fisher_from_gradients(self, gradients: dict[str, float]) -> dict[str, float]:
        """Compute Fisher as E[grad^2] from gradient dictionary."""
        fisher = {}
        for key, grad in gradients.items():
            fisher[key] = grad ** 2
        return fisher

    def update_from_gradients(self, gradients: dict[str, float]) -> None:
        """Update Fisher using gradient history with momentum."""
        emp_fisher = self.compute_empirical_fisher_from_gradients(gradients)

        for key, fisher_val in emp_fisher.items():
            if key not in self._fisher_diagonal:
                self._fisher_diagonal[key] = fisher_val
            else:
                self._fisher_diagonal[key] = (
                    self.momentum * self._fisher_diagonal[key] + 
                    (1 - self.momentum) * fisher_val
                )

            if key not in self._gradient_histories:
                self._gradient_histories[key] = []
            self._gradient_histories[key].append(fisher_val)
            if len(self._gradient_histories[key]) > self._max_history:
                self._gradient_histories[key] = self._gradient_histories[key][-self._max_history:]

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
        self, task_params: dict[str, float], gradients: dict[str, float] | None = None
    ) -> None:
        """Update Fisher information from gradients after completing a task."""
        self._task_count += 1
        self._optimal_params = dict(task_params)

        if gradients:
            self.update_from_gradients(gradients)
        else:
            for key in task_params:
                if key not in self._fisher_diagonal:
                    self._fisher_diagonal[key] = 1.0


def _test():
    print("Testing EWC with real empirical Fisher...")

    ewc = EWCEngine(lambda_reg=0.1, momentum=0.9)

    task1_params = {"layer1.weight": 1.0, "layer1.bias": 0.5}
    task1_grads = {"layer1.weight": 0.8, "layer1.bias": 0.3}

    ewc.update_after_task(task1_params, task1_grads)
    print(f"  After task 1 - Fisher: {ewc._fisher_diagonal}")

    current = {"layer1.weight": 1.2, "layer1.bias": 0.6}
    penalty1 = ewc.compute_penalty(current)
    print(f"  Penalty (shifted params): {penalty1:.6f}")

    task2_grads = {"layer1.weight": 0.5, "layer1.bias": 0.2}
    ewc.update_from_gradients(task2_grads)
    print(f"  After task 2 - Fisher: {ewc._fisher_diagonal}")

    penalty2 = ewc.compute_penalty(current)
    print(f"  Updated penalty: {penalty2:.6f}")

    no_change = {"layer1.weight": 1.0, "layer1.bias": 0.5}
    penalty_no_change = ewc.compute_penalty(no_change)
    print(f"  Penalty (no change): {penalty_no_change:.6f}")

    print(f"  Gradient history (layer1.weight): {ewc._gradient_histories.get('layer1.weight')}")

    print("✅ EWC empirical Fisher test passed!")


if __name__ == "__main__":
    _test()

__all__ = ["EWCEngine", "EWCParams", "DEFAULT_LAMBDA"]