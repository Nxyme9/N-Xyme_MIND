"""Adaptive router — wraps MemoryRouter with Q-Learning feedback loop."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..outcome_logger import DelegationOutcome, OutcomeLogger
from ..rl.q_learning import ActionType, QLearningEngine, QState
from ...memory_core.router import MemoryRouter, SearchResults, UnifiedMemoryQuery

logger = logging.getLogger(__name__)

# Constants for reward computation
LATENCY_THRESHOLD_MS = 100.0
LATENCY_PENALTY_PER_MS = 0.001
QUALITY_BONUS_THRESHOLD = 0.8
QUALITY_BONUS_VALUE = 0.5


@dataclass
class LearningStats:
    """Statistics showing learning improvement over time."""

    total_decisions: int = 0
    successful_decisions: int = 0
    success_rate: float = 0.0
    average_q_value: float = 0.0
    exploration_count: int = 0
    exploitation_count: int = 0
    recent_rewards: list[float] = field(default_factory=list)
    improvement_trend: float = 0.0


class AdaptiveRouter:
    """Wraps MemoryRouter with Q-Learning feedback loop for real learning.

    This is the CRITICAL FIX that connects OutcomeLogger to Q-Learning.
    Every routing decision is logged, converted to a reward signal, and
    used to update Q-values for future decisions.
    """

    def __init__(
        self,
        router: Optional[MemoryRouter] = None,
        outcome_logger: Optional[OutcomeLogger] = None,
        q_learning: Optional[QLearningEngine] = None,
        db_path: str = ".sisyphus/routing_learning.db",
    ):
        # Use provided instances or create defaults
        self._router = router or MemoryRouter()
        self._outcome_logger = outcome_logger or OutcomeLogger()
        self._q_learning = q_learning or QLearningEngine(db_path=db_path)

        # Track decisions for stats
        self._decision_history: list[dict[str, Any]] = []

    def route(self, task_description: str) -> dict[str, Any]:
        """Route a task to optimal agent using Q-Learning.

        Uses learned routing decisions from past outcomes. Falls back to
        heuristic routing during cold start (first 50 decisions).

        Args:
            task_description: The task to route

        Returns:
            Dict with agent, level, confidence, reason, and learning info
        """
        # Determine available agents for this task
        available_actions = self._get_available_actions(task_description, {})

        # Build state from task description
        state = QState.from_context(task_description, {"task_type": "delegation"})

        # Select action using Q-Learning (epsilon-greedy)
        selected_action = self._q_learning.select_action(state, available_actions)

        # Map action to agent and level
        agent = self._action_to_agent(selected_action)
        level = self._action_to_level(selected_action)

        # Determine confidence based on Q-values
        q_values = self._q_learning.get_q_values(state)
        action_q = q_values.get(selected_action.value, 0.0)
        confidence = min(max(0.5 + action_q * 0.1, 0.1), 0.95)

        # Build reason
        reason = f"Q-Learning selected {agent} (L{level})"
        if len(self._decision_history) < 50:
            reason = f"Heuristic routing (cold start: {len(self._decision_history)}/50 decisions)"

        return {
            "agent": agent,
            "level": level,
            "confidence": round(confidence, 2),
            "reason": reason,
            "decisions_made": len(self._decision_history),
        }

    def _action_to_agent(self, action: ActionType) -> str:
        """Map ActionType to agent name."""
        mapping = {
            ActionType.EXPLORE: "explore",
            ActionType.DELEGATE: "hephaestus",
            ActionType.ORACLE: "oracle",
            ActionType.LIBRARIAN: "librarian",
            ActionType.HEPHAESTUS: "hephaestus",
            ActionType.MULTIMODAL: "multimodal-looker",
        }
        return mapping.get(action, "hephaestus")

    def search(self, query: str, **kwargs) -> SearchResults:
        """Search with learning — logs outcome and updates Q-values.

        This is the main entry point that wraps the underlying router's search.
        """
        start_time = time.time()

        # Build context for state representation
        context = self._build_context(query, kwargs)

        # Convert query to QState
        state = QState.from_context(query, context)

        # Determine available actions based on query characteristics
        available_actions = self._get_available_actions(query, context)

        # Select action using Q-Learning (epsilon-greedy)
        selected_action = self._q_learning.select_action(state, available_actions)

        # Execute search using the router (route to appropriate retriever)
        unified_query = self._build_unified_query(query, selected_action, kwargs)
        results = self._router.search(unified_query)

        # Compute latency
        latency_ms = (time.time() - start_time) * 1000

        # Build outcome and log it
        outcome = self._build_outcome(
            query=query,
            action=selected_action,
            results=results,
            latency_ms=latency_ms,
            context=context,
        )

        # Log outcome to database
        self._outcome_logger.log(outcome)

        # Compute reward signal
        reward = self._compute_reward(
            success=outcome.success,
            latency_ms=latency_ms,
            quality_score=outcome.quality_score,
        )

        # Update Q-Learning with actual reward
        self._q_learning.update(
            state=state,
            action=selected_action,
            reward=reward,
            task_id=outcome.task_id,
        )

        # Track decision for stats
        self._track_decision(
            state=state,
            action=selected_action,
            reward=reward,
            latency_ms=latency_ms,
        )

        return results

    def _build_context(self, query: str, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Build context dict for QState.from_context()."""
        return {
            "retriever_used": kwargs.get("retriever", "semantic"),
            "result_count": len(kwargs.get("results", [])),
            "query_length": len(query),
            "has_filters": bool(kwargs.get("filters")),
        }

    def _get_available_actions(
        self, query: str, context: dict[str, Any]
    ) -> list[ActionType]:
        """Determine available actions based on query characteristics."""
        # All actions available by default
        available = [
            ActionType.EXPLORE,
            ActionType.DELEGATE,
            ActionType.ORACLE,
            ActionType.LIBRARIAN,
            ActionType.HEPHAESTUS,
            ActionType.MULTIMODAL,
        ]

        # Narrow down based on query type hints
        query_lower = query.lower()
        if any(word in query_lower for word in ["find", "search", "locate"]):
            # Research-oriented query
            available = [ActionType.EXPLORE, ActionType.LIBRARIAN]
        elif any(word in query_lower for word in ["fix", "debug", "error"]):
            # Implementation/fix query
            available = [ActionType.HEPHAESTUS, ActionType.DELEGATE]
        elif any(word in query_lower for word in ["design", "architecture", "review"]):
            # Review/analysis query
            available = [ActionType.ORACLE, ActionType.LIBRARIAN]

        return available

    def _build_unified_query(
        self, query: str, action: ActionType, kwargs: dict[str, Any]
    ) -> UnifiedMemoryQuery:
        """Build UnifiedMemoryQuery based on selected action."""
        use_semantic = action in [ActionType.EXPLORE, ActionType.ORACLE]

        return UnifiedMemoryQuery(
            query=query,
            max_results_per_source=kwargs.get("max_results", 10),
            use_semantic=use_semantic,
            filters=kwargs.get("filters", {}),
        )

    def _build_outcome(
        self,
        query: str,
        action: ActionType,
        results: SearchResults,
        latency_ms: float,
        context: dict[str, Any],
    ) -> DelegationOutcome:
        """Build DelegationOutcome from routing decision."""
        # Determine success based on results
        has_results = len(results.results) > 0
        success = (
            has_results and latency_ms < 500
        )  # Consider slow queries as partial failure

        # Map action to task type
        task_type = self._action_to_task_type(action)

        return DelegationOutcome(
            task_id=str(uuid.uuid4()),
            task_description=query,
            task_type=task_type,
            agent=action.value,
            level=self._action_to_level(action),
            success=success,
            latency_ms=latency_ms,
            tokens_used=0,  # No token counting for router decisions
            quality_score=None,  # Will be set if user provides feedback
            context=context,
        )

    def _action_to_task_type(self, action: ActionType) -> str:
        """Map ActionType to task_type string."""
        mapping = {
            ActionType.EXPLORE: "research",
            ActionType.DELEGATE: "implementation",
            ActionType.ORACLE: "review",
            ActionType.LIBRARIAN: "research",
            ActionType.HEPHAESTUS: "implementation",
            ActionType.MULTIMODAL: "research",
        }
        return mapping.get(action, "research")

    def _action_to_level(self, action: ActionType) -> int:
        """Map ActionType to L1-L5 level."""
        mapping = {
            ActionType.EXPLORE: 3,  # L3: research
            ActionType.DELEGATE: 2,  # L2: simple delegation
            ActionType.ORACLE: 4,  # L4: complex review
            ActionType.LIBRARIAN: 3,  # L3: research
            ActionType.HEPHAESTUS: 3,  # L3: implementation
            ActionType.MULTIMODAL: 3,  # L3: research
        }
        return mapping.get(action, 3)

    def _compute_reward(
        self,
        success: bool,
        latency_ms: float,
        quality_score: Optional[float] = None,
    ) -> float:
        """Compute reward signal from outcome.

        Reward = base_reward + latency_penalty + quality_bonus

        - base_reward: +1 for success, -1 for failure
        - latency_penalty: -0.001 per ms over 100ms threshold
        - quality_bonus: +0.5 if quality_score > 0.8
        """
        # Base reward: +1 for success, -1 for failure
        base_reward = 1.0 if success else -1.0

        # Latency penalty: -0.001 per ms over threshold
        latency_penalty = 0.0
        if latency_ms > LATENCY_THRESHOLD_MS:
            latency_penalty = -LATENCY_PENALTY_PER_MS * (
                latency_ms - LATENCY_THRESHOLD_MS
            )

        # Quality bonus: +0.5 if quality is high
        quality_bonus = 0.0
        if quality_score is not None and quality_score > QUALITY_BONUS_THRESHOLD:
            quality_bonus = QUALITY_BONUS_VALUE

        return base_reward + latency_penalty + quality_bonus

    def _track_decision(
        self,
        state: QState,
        action: ActionType,
        reward: float,
        latency_ms: float,
    ) -> None:
        """Track decision for learning statistics."""
        # Determine if exploration or exploitation
        is_exploration = action not in [
            ActionType.HEPHAESTUS,
            ActionType.DELEGATE,
        ]

        self._decision_history.append(
            {
                "state": state.to_key(),
                "action": action.value,
                "reward": reward,
                "latency_ms": latency_ms,
                "timestamp": datetime.now().isoformat(),
                "is_exploration": is_exploration,
            }
        )

        # Keep only last 1000 decisions
        if len(self._decision_history) > 1000:
            self._decision_history = self._decision_history[-1000:]

    def get_learning_stats(self) -> LearningStats:
        """Get learning statistics showing improvement over time."""
        if not self._decision_history:
            return LearningStats()

        total = len(self._decision_history)
        successful = sum(1 for d in self._decision_history if d["reward"] > 0)
        exploration_count = sum(
            1 for d in self._decision_history if d.get("is_exploration")
        )
        exploitation_count = total - exploration_count

        # Get Q-values from all states
        all_q_values: list[float] = []
        for decision in self._decision_history:
            state = QState.from_context(decision["state"].split("|")[0], {})
            q_vals = self._q_learning.get_q_values(state)
            all_q_values.extend(q_vals.values())

        avg_q = sum(all_q_values) / len(all_q_values) if all_q_values else 0.0

        # Recent rewards (last 50)
        recent_rewards = [d["reward"] for d in self._decision_history[-50:]]

        # Compute improvement trend (positive = improving)
        improvement_trend = 0.0
        if len(recent_rewards) >= 20:
            first_half = sum(recent_rewards[:10]) / 10
            second_half = sum(recent_rewards[10:20]) / 10
            improvement_trend = second_half - first_half

        return LearningStats(
            total_decisions=total,
            successful_decisions=successful,
            success_rate=successful / total if total > 0 else 0.0,
            average_q_value=round(avg_q, 4),
            exploration_count=exploration_count,
            exploitation_count=exploitation_count,
            recent_rewards=recent_rewards[-20:],  # Last 20 for display
            improvement_trend=round(improvement_trend, 4),
        )

    def reset_learning(self) -> None:
        """Reset Q-table and decision history (for testing)."""
        self._decision_history = []
        # Re-initialize Q-table
        self._q_learning = QLearningEngine(
            db_path=getattr(self._q_learning, "_db_path", None)
        )


# Import path for UnifiedMemoryQuery and SearchResults
# These are imported at module level from memory_core.router
__all__ = [
    "AdaptiveRouter",
    "LearningStats",
]
