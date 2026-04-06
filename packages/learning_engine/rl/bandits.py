"""Multi-Armed Bandit — Epsilon-Greedy, UCB, and Thompson Sampling strategies."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

# Configuration
DEFAULT_EPSILON = 0.1  # Exploration rate


@dataclass
class BanditArm:
    """A bandit arm representing an action with its statistics."""

    action: str
    pulls: int = 0
    total_reward: float = 0.0
    sum_squared: float = 0.0  # For variance calculation

    @property
    def mean_reward(self) -> float:
        return self.total_reward / self.pulls if self.pulls > 0 else 0.0

    @property
    def variance(self) -> float:
        if self.pulls < 2:
            return float("inf")
        return (self.sum_squared / self.pulls) - (self.mean_reward**2)

    @property
    def confidence_radius(self) -> float:
        if self.pulls < 2:
            return float("inf")
        # 95% confidence interval
        return 1.96 * math.sqrt(self.variance / self.pulls)

    def pull(self, reward: float) -> None:
        self.pulls += 1
        self.total_reward += reward
        self.sum_squared += reward**2


class MultiArmedBandit:
    """Multi-Armed Bandit with Epsilon-Greedy, UCB, and Thompson Sampling.

    Supports:
    - Epsilon-Greedy: Explore with probability ε, exploit otherwise
    - UCB (Upper Confidence Bound): Balance exploration/exploitation
    - Thompson Sampling: Bayesian approach
    """

    def __init__(
        self,
        epsilon: float = DEFAULT_EPSILON,
        ucb_c: float = 2.0,
        strategy: str = "ucb",
    ):
        self.epsilon = epsilon
        self.ucb_c = ucb_c
        self.strategy = strategy
        self._arms: dict[str, BanditArm] = {}
        self._total_pulls = 0

    def select_arm(self, context: str) -> str:
        """Select an arm based on the chosen strategy."""
        if not self._arms:
            return "delegate"

        import random

        if self.strategy == "epsilon":
            if random.random() < self.epsilon:
                return random.choice(list(self._arms.keys()))
            return max(self._arms.keys(), key=lambda a: self._arms[a].mean_reward)

        elif self.strategy == "ucb":
            best_arm = None
            best_value = float("-inf")
            for arm_name, arm in self._arms.items():
                if arm.pulls == 0:
                    return arm_name
                ucb_value = arm.mean_reward + self.ucb_c * math.sqrt(
                    math.log(self._total_pulls) / arm.pulls
                )
                if ucb_value > best_value:
                    best_value = ucb_value
                    best_arm = arm_name
            return best_arm or "delegate"

        elif self.strategy == "thompson":
            samples = {}
            for arm_name, arm in self._arms.items():
                if arm.pulls == 0:
                    samples[arm_name] = float("inf")
                else:
                    samples[arm_name] = random.gauss(
                        arm.mean_reward, arm.confidence_radius
                    )
            return max(samples.keys(), key=lambda a: samples[a])

        return "delegate"

    def update(self, arm_name: str, reward: float) -> None:
        """Update arm statistics with new reward."""
        if arm_name not in self._arms:
            self._arms[arm_name] = BanditArm(action=arm_name)
        self._arms[arm_name].pull(reward)
        self._total_pulls += 1

    def get_statistics(self) -> dict[str, dict[str, float]]:
        """Get statistics for all arms."""
        return {
            name: {
                "pulls": arm.pulls,
                "mean_reward": arm.mean_reward,
                "variance": arm.variance if arm.pulls >= 2 else 0.0,
                "confidence": arm.confidence_radius,
            }
            for name, arm in self._arms.items()
        }


__all__ = [
    "BanditArm",
    "MultiArmedBandit",
    "DEFAULT_EPSILON",
]
