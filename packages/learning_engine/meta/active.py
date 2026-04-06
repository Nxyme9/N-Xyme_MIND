"""Active Learning — Uncertainty-based query selection."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


def _hash_context(context: dict[str, Any]) -> str:
    """Create a deterministic hash from context dict."""
    if not context:
        return "empty"
    s = "|".join(f"{k}:{v}" for k, v in sorted(context.items()))
    return str(abs(hash(s)) % 1000000)


class ActiveLearningEngine:
    """Active Learning for uncertainty-based query selection.

    Uses confidence intervals to identify which decisions need
    more data (high uncertainty).
    """

    def __init__(self, uncertainty_threshold: float = 0.3):
        self.uncertainty_threshold = uncertainty_threshold
        self._context_statistics: dict[str, dict[str, Any]] = {}

    def compute_uncertainty(self, context: dict[str, Any], action: str) -> float:
        """Compute uncertainty for a (context, action) pair.

        Returns 0 = certain, 1 = very uncertain
        """
        key = f"{_hash_context(context)}|{action}"

        if key not in self._context_statistics:
            return 1.0

        stats = self._context_statistics[key]
        if stats.get("count", 0) < 2:
            return 0.8

        return min(1.0, stats.get("variance", 0) / 2.0)

    def should_collect_more_data(self, context: dict[str, Any], action: str) -> bool:
        """Decide if we should gather more data for this decision."""
        uncertainty = self.compute_uncertainty(context, action)
        return uncertainty > self.uncertainty_threshold

    def update_statistics(
        self, context: dict[str, Any], action: str, reward: float
    ) -> None:
        """Update running statistics for a (context, action) pair."""
        key = f"{_hash_context(context)}|{action}"

        if key not in self._context_statistics:
            self._context_statistics[key] = {"count": 0, "sum": 0.0, "sum_sq": 0.0}

        stats = self._context_statistics[key]
        stats["count"] += 1
        stats["sum"] += reward
        stats["sum_sq"] += reward**2

        if stats["count"] >= 2:
            mean = stats["sum"] / stats["count"]
            stats["variance"] = (stats["sum_sq"] / stats["count"]) - (mean**2)


__all__ = [
    "ActiveLearningEngine",
]
