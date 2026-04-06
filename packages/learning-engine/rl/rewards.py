"""Reward function definitions for reinforcement learning."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CompositeReward:
    """Composite reward with multiple components."""

    base: float  # Success/failure reward
    latency_bonus: float  # Faster = better
    cost_penalty: float  # Cheaper = better
    confidence_bonus: float  # High confidence = bonus
    exploration_bonus: float  # Novel action = bonus

    @property
    def total(self) -> float:
        return (
            self.base
            + self.latency_bonus
            + self.cost_penalty
            + self.confidence_bonus
            + self.exploration_bonus
        )

    @staticmethod
    def compute(
        success: bool,
        latency_ms: float,
        cost: float,
        confidence: float,
        is_novel: bool,
        baseline_latency: float = 500.0,
        baseline_cost: float = 0.01,
    ) -> "CompositeReward":
        base = 1.0 if success else -1.0

        # Latency bonus: faster than baseline = positive
        latency_bonus = max(0, (baseline_latency - latency_ms) / baseline_latency)

        # Cost penalty: cheaper = positive
        cost_penalty = (baseline_cost - cost) / baseline_cost

        # Confidence bonus: higher confidence = positive
        confidence_bonus = (confidence - 0.5) * 0.5

        # Exploration bonus: novel actions get a small bonus
        exploration_bonus = 0.1 if is_novel else 0.0

        return CompositeReward(
            base=base,
            latency_bonus=latency_bonus,
            cost_penalty=cost_penalty,
            confidence_bonus=confidence_bonus,
            exploration_bonus=exploration_bonus,
        )

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "components": {
                "base": self.base,
                "latency": self.latency_bonus,
                "cost": self.cost_penalty,
                "confidence": self.confidence_bonus,
                "exploration": self.exploration_bonus,
            },
        }


__all__ = [
    "CompositeReward",
]
