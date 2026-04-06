"""Counterfactual Learning for 'what-if' analysis.

Estimates what would have happened if a different action
had been taken, without actually taking that action.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CounterfactualResult:
    """Result of counterfactual 'what-if' analysis."""

    hypothetical_action: str
    estimated_reward: float
    confidence: float
    based_on: int  # How many similar contexts this is based on


def _hash_context(context: dict[str, Any]) -> str:
    """Create a deterministic hash from context dict."""
    if not context:
        return "empty"
    # Simple hash based on sorted key-value pairs
    s = "|".join(f"{k}:{v}" for k, v in sorted(context.items()))
    return str(abs(hash(s)) % 1000000)


class CounterfactualEngine:
    """Counterfactual Learning for 'what-if' analysis.

    Estimates what would have happened if a different action
    had been taken, without actually taking that action.
    """

    def __init__(self):
        self._similar_contexts: dict[str, list[dict[str, Any]]] = {}

    def estimate(
        self,
        current_context: dict[str, Any],
        hypothetical_action: str,
        available_actions: list[str],
    ) -> CounterfactualResult:
        """Estimate outcome if hypothetical_action had been taken."""
        ctx_hash = _hash_context(current_context)[:16]

        # Find similar contexts
        similar = []
        for stored_hash, outcomes in self._similar_contexts.items():
            if stored_hash[:16] == ctx_hash:
                similar.extend(outcomes)

        if len(similar) < 3:
            # Not enough data - use general statistics
            return CounterfactualResult(
                hypothetical_action=hypothetical_action,
                estimated_reward=0.5,
                confidence=0.3,
                based_on=len(similar),
            )

        # Compute weighted estimate
        action_outcomes = [o for o in similar if o.get("action") == hypothetical_action]

        if not action_outcomes:
            # Use overall average
            avg_reward = sum(o.get("reward", 0) for o in similar) / len(similar)
            confidence = 0.5
        else:
            avg_reward = sum(o.get("reward", 0) for o in action_outcomes) / len(
                action_outcomes
            )
            confidence = min(1.0, len(action_outcomes) / 10)

        return CounterfactualResult(
            hypothetical_action=hypothetical_action,
            estimated_reward=avg_reward,
            confidence=confidence,
            based_on=len(action_outcomes),
        )

    def store_outcome(
        self, context: dict[str, Any], action: str, reward: float
    ) -> None:
        """Store an outcome for future counterfactual analysis."""
        ctx_hash = _hash_context(context)[:16]

        if ctx_hash not in self._similar_contexts:
            self._similar_contexts[ctx_hash] = []

        self._similar_contexts[ctx_hash].append(
            {"action": action, "reward": reward, "timestamp": time.time()}
        )

        # Limit stored outcomes per context
        if len(self._similar_contexts[ctx_hash]) > 100:
            self._similar_contexts[ctx_hash] = self._similar_contexts[ctx_hash][-100:]