"""Reward function definitions for reinforcement learning.

Multi-Dimensional Reward System:
- Combines success (task completion), quality (outcome analysis),
  latency (performance), cost (resource usage), and satisfaction (implicit feedback)
- Weights: success=0.4, quality=0.2, latency=0.15, cost=0.15, satisfaction=0.1
- Integrates with signals.py for SATISFACTION signal extraction
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_WEIGHTS = {
    "success": 0.4,
    "quality": 0.2,
    "latency": 0.15,
    "cost": 0.15,
    "satisfaction": 0.1,
}


@dataclass
class CompositeReward:
    """Composite reward with multiple components.

    Multi-dimensional reward combining:
    - base: Success/failure (weighted by success weight)
    - quality: Outcome analysis quality score
    - latency_bonus: Performance bonus for faster execution
    - cost_penalty: Resource usage efficiency
    - satisfaction: Implicit feedback signal (from signals.py SATISFACTION)

    Weights determine contribution to total reward:
    - success: 0.4 (primary driver)
    - quality: 0.2 (outcome quality)
    - latency: 0.15 (speed bonus)
    - cost: 0.15 (resource efficiency)
    - satisfaction: 0.1 (implicit feedback)
    """

    base: float  # Success/failure reward
    quality: float  # Quality score from outcome analysis
    latency_bonus: float  # Faster = better
    cost_penalty: float  # Cheaper = better
    confidence_bonus: float  # High confidence = bonus
    exploration_bonus: float  # Novel action = bonus
    satisfaction_bonus: float  # Implicit feedback satisfaction signal

    @property
    def total(self) -> float:
        return (
            self.base
            + self.quality
            + self.latency_bonus
            + self.cost_penalty
            + self.confidence_bonus
            + self.exploration_bonus
            + self.satisfaction_bonus
        )

    @staticmethod
    def compute(
        success: bool,
        latency_ms: float,
        cost: float,
        confidence: float,
        is_novel: bool,
        quality_score: float | None = None,
        satisfaction_signal: float | None = None,
        baseline_latency: float = 500.0,
        baseline_cost: float = 0.01,
        weights: dict[str, float] | None = None,
    ) -> "CompositeReward":
        """Compute composite reward with optional quality and satisfaction signals.

        Args:
            success: Whether the task succeeded
            latency_ms: Execution latency in milliseconds
            cost: Resource cost
            confidence: Model confidence (0-1)
            is_novel: Whether this was a novel action
            quality_score: Optional quality score from outcome analysis (0-1)
            satisfaction_signal: Optional satisfaction from implicit feedback (0-1)
            baseline_latency: Baseline latency for bonus calculation
            baseline_cost: Baseline cost for penalty calculation
            weights: Optional custom weights (defaults to DEFAULT_WEIGHTS)

        Returns:
            CompositeReward with all components computed
        """
        if weights is None:
            weights = DEFAULT_WEIGHTS

        w_success = weights.get("success", 0.4)
        w_quality = weights.get("quality", 0.2)
        w_latency = weights.get("latency", 0.15)
        w_cost = weights.get("cost", 0.15)
        w_satisfaction = weights.get("satisfaction", 0.1)

        base = (1.0 if success else -1.0) * w_success

        latency_bonus = max(0, (baseline_latency - latency_ms) / baseline_latency) * w_latency

        cost_penalty = (baseline_cost - cost) / baseline_cost * w_cost

        confidence_bonus = (confidence - 0.5) * 0.5

        exploration_bonus = 0.1 if is_novel else 0.0

        quality = (quality_score if quality_score is not None else 0.5) * w_quality

        satisfaction = (satisfaction_signal if satisfaction_signal is not None else 0.0) * w_satisfaction

        return CompositeReward(
            base=base,
            quality=quality,
            latency_bonus=latency_bonus,
            cost_penalty=cost_penalty,
            confidence_bonus=confidence_bonus,
            exploration_bonus=exploration_bonus,
            satisfaction_bonus=satisfaction,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "components": {
                "base": self.base,
                "quality": self.quality,
                "latency": self.latency_bonus,
                "cost": self.cost_penalty,
                "confidence": self.confidence_bonus,
                "exploration": self.exploration_bonus,
                "satisfaction": self.satisfaction_bonus,
            },
        }


__all__ = [
    "CompositeReward",
    "DEFAULT_WEIGHTS",
]
