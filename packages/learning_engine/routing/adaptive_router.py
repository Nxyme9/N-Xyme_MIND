"""Adaptive router — wraps MemoryRouter with Q-Learning feedback loop."""

from __future__ import annotations

import logging
import random
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

from ..outcome_logger import DelegationOutcome, OutcomeLogger
from ..rl.q_learning import ActionType, QLearningEngine, QState
from ...memory_core.router import MemoryRouter, SearchResults, UnifiedMemoryQuery

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Constants for reward computation
LATENCY_THRESHOLD_MS = 100.0
LATENCY_PENALTY_PER_MS = 0.001
QUALITY_BONUS_THRESHOLD = 0.8
QUALITY_BONUS_VALUE = 0.5

# Circuit breaker configuration
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 10
CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS = 15
CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS = 3


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


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests allowed
    OPEN = "open"  # Failure threshold exceeded, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker with open/half-open/closed states.

    Prevents cascading failures by stopping requests to failing services
    and allowing them to recover after a timeout.
    """

    def __init__(
        self,
        failure_threshold: int = CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        recovery_timeout: int = CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS,
        half_open_max_calls: int = CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, auto-transitioning if needed."""
        if self._state == CircuitState.OPEN and self._last_failure_time:
            # Check if recovery timeout has passed
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                logger.info("Circuit breaker transitioning OPEN -> HALF_OPEN")
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    def record_success(self) -> None:
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                logger.info("Circuit breaker transitioning HALF_OPEN -> CLOSED")
                self._state = CircuitState.CLOSED
                self._failure_count = 0
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            logger.warning(
                "Circuit breaker transitioning HALF_OPEN -> OPEN (test failed)"
            )
            self._state = CircuitState.OPEN
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                logger.warning(
                    f"Circuit breaker transitioning CLOSED -> OPEN "
                    f"(failures: {self._failure_count}/{self.failure_threshold})"
                )
                self._state = CircuitState.OPEN

    def is_available(self) -> bool:
        """Check if a request can be made."""
        return self.state != CircuitState.OPEN


def retry_with_backoff(
    func: Callable[[], T],
    max_attempts: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 2.0,
    backoff_factor: float = 2.0,
) -> T:
    """Retry a function with exponential backoff for SQLite operations.

    Args:
        func: Function to execute
        max_attempts: Maximum number of attempts (default 3)
        base_delay: Initial delay in seconds (default 0.1)
        max_delay: Maximum delay in seconds (default 2.0)
        backoff_factor: Multiplier for each retry (default 2.0)

    Returns:
        Result of the function

    Raises:
        Last exception if all attempts fail
    """
    last_exception: Optional[Exception] = None
    delay = base_delay

    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_attempts - 1:
                logger.warning(
                    f"SQLite operation failed (attempt {attempt + 1}/{max_attempts}): {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                time.sleep(delay)
                delay = min(delay * backoff_factor, max_delay)
            else:
                logger.error(
                    f"SQLite operation failed after {max_attempts} attempts: {e}"
                )

    # All attempts failed, raise the last exception
    raise last_exception  # type: ignore


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

        # Circuit breaker for Q-Learning database
        self._circuit_breaker = CircuitBreaker()

        # Track if using fallback mode
        self._using_fallback = False

    def route(self, task_description: str) -> dict[str, Any]:
        """Route a task to optimal agent using Q-Learning.

        Uses learned routing decisions from past outcomes. Falls back to
        heuristic routing during cold start (first 50 decisions) or if
        Q-Learning database is unavailable (circuit breaker open).

        Args:
            task_description: The task to route

        Returns:
            Dict with agent, level, confidence, reason, and learning info
        """
        # Check if Q-Learning is available (circuit breaker not open)
        if not self._circuit_breaker.is_available():
            logger.warning("Q-Learning circuit breaker OPEN, using heuristic fallback")
            return self._heuristic_route(task_description)

        # Try Q-Learning route with circuit breaker protection
        try:
            return self._route_with_q_learning(task_description)
        except Exception as e:
            logger.error(f"Q-Learning routing failed: {e}, falling back to heuristic")
            self._circuit_breaker.record_failure()
            return self._heuristic_route(task_description)

    def _route_with_q_learning(self, task_description: str) -> dict[str, Any]:
        """Route using Q-Learning with circuit breaker protection."""
        # Determine available agents for this task
        available_actions = self._get_available_actions(task_description, {})

        # Build state from task description
        state = QState.from_context(task_description, {"task_type": "delegation"})

        # Select action using Q-Learning (epsilon-greedy)
        try:
            selected_action = self._q_learning.select_action(state, available_actions)
            self._circuit_breaker.record_success()
        except Exception as e:
            raise RuntimeError(f"Q-Learning select_action failed: {e}") from e

        # Map action to agent and level
        agent = self._action_to_agent(selected_action)
        level = self._action_to_level(selected_action)

        # Determine confidence based on Q-values
        try:
            q_values = self._q_learning.get_q_values(state)
            action_q = q_values.get(selected_action.value, 0.0)
            confidence = min(max(0.5 + action_q * 0.1, 0.1), 0.95)
        except Exception:
            confidence = 0.5  # Default confidence if Q-value lookup fails

        # Build reason
        reason = f"Q-Learning selected {agent} (L{level})"
        if len(self._decision_history) < 50:
            reason = f"Heuristic routing (cold start: {len(self._decision_history)}/50 decisions)"

        result = {
            "agent": agent,
            "level": level,
            "confidence": round(confidence, 2),
            "reason": reason,
            "decisions_made": len(self._decision_history),
        }

        # Log the routing decision and update Q-Learning
        # This is the CRITICAL FIX: route() now learns from every decision
        self._log_and_learn_routing(
            task_description, agent, level, selected_action, state
        )

        return result

    def _log_and_learn_routing(
        self,
        task_description: str,
        agent: str,
        level: int,
        action: ActionType,
        state: QState,
    ) -> None:
        """Log routing decision and update Q-Learning for route() calls.

        This method ensures that every routing decision made via route() is
        logged to the outcome database and used to update Q-values, creating
        a real learning loop for delegation routing.
        """
        # Create outcome for this routing decision
        outcome = DelegationOutcome(
            task_id=str(uuid.uuid4()),
            task_description=task_description,
            task_type="delegation",
            agent=agent,
            level=level,
            success=True,  # Routing itself succeeded
            latency_ms=0.0,  # No execution latency for routing decision
            tokens_used=0,
            quality_score=None,
            context={"routing_decision": True},
        )

        # Log outcome to database
        try:
            retry_with_backoff(
                lambda: self._outcome_logger.log(outcome),
                max_attempts=3,
            )
        except Exception as e:
            logger.warning(f"Failed to log routing outcome: {e}")

        # Compute reward (routing success = base +1)
        reward = self._compute_reward(success=True, latency_ms=0.0, quality_score=None)

        # Update Q-Learning
        try:
            retry_with_backoff(
                lambda: self._q_learning.update(
                    state=state,
                    action=action,
                    reward=reward,
                    task_id=outcome.task_id,
                ),
                max_attempts=3,
            )
        except Exception as e:
            logger.warning(f"Failed to update Q-Learning for routing: {e}")

        # Track decision for stats
        self._track_decision(
            state=state,
            action=action,
            reward=reward,
            latency_ms=0.0,
        )

    def _heuristic_route(self, task_description: str) -> dict[str, Any]:
        """Fallback heuristic routing when Q-Learning is unavailable."""
        task_lower = task_description.lower()

        # Simple heuristic based on keywords
        if any(w in task_lower for w in ["find", "search", "locate", "explore"]):
            agent, level = "explore", 3
        elif any(w in task_lower for w in ["fix", "debug", "error", "bug"]):
            agent, level = "hephaestus", 2
        elif any(
            w in task_lower for w in ["design", "architecture", "review", "analyze"]
        ):
            agent, level = "oracle", 4
        elif any(w in task_lower for w in ["implement", "create", "add", "build"]):
            agent, level = "hephaestus", 3
        elif any(w in task_lower for w in ["doc", "explain", "what", "how"]):
            agent, level = "librarian", 3
        else:
            agent, level = "hephaestus", 3  # Default

        return {
            "agent": agent,
            "level": level,
            "confidence": 0.3,  # Lower confidence for fallback
            "reason": f"Heuristic fallback (circuit breaker: {self._circuit_breaker.state.value})",
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
        Uses circuit breaker and retry logic for database operations.
        """
        start_time = time.time()

        # Build context for state representation
        context = self._build_context(query, kwargs)

        # Convert query to QState
        state = QState.from_context(query, context)

        # Determine available actions based on query characteristics
        available_actions = self._get_available_actions(query, context)

        # Check if Q-Learning is available
        if not self._circuit_breaker.is_available():
            # Fall back to heuristic routing - just search without learning
            logger.warning("Q-Learning circuit breaker OPEN, skipping learning updates")
            return self._search_without_learning(query, kwargs, available_actions)

        # Select action using Q-Learning (epsilon-greedy) with retry
        try:
            selected_action = retry_with_backoff(
                lambda: self._q_learning.select_action(state, available_actions),
                max_attempts=3,
            )
            self._circuit_breaker.record_success()
        except Exception as e:
            logger.error(f"Q-Learning select_action failed: {e}")
            self._circuit_breaker.record_failure()
            return self._search_without_learning(query, kwargs, available_actions)

        # Execute search using the router (route to appropriate retriever)
        unified_query = self._build_unified_query(query, selected_action, kwargs)
        results = self._router.search(unified_query)

        # Compute latency
        latency_ms = (time.time() - start_time) * 1000

        # Build outcome and log it with retry logic
        outcome = self._build_outcome(
            query=query,
            action=selected_action,
            results=results,
            latency_ms=latency_ms,
            context=context,
        )

        # Log outcome to database with retry
        try:
            retry_with_backoff(
                lambda: self._outcome_logger.log(outcome),
                max_attempts=3,
            )
        except Exception as e:
            logger.warning(f"Failed to log outcome after retries: {e}")

        # Compute reward signal
        reward = self._compute_reward(
            success=outcome.success,
            latency_ms=latency_ms,
            quality_score=outcome.quality_score,
        )

        # Update Q-Learning with actual reward with retry
        try:
            retry_with_backoff(
                lambda: self._q_learning.update(
                    state=state,
                    action=selected_action,
                    reward=reward,
                    task_id=outcome.task_id,
                ),
                max_attempts=3,
            )
        except Exception as e:
            logger.warning(f"Failed to update Q-Learning after retries: {e}")

        # Track decision for stats
        self._track_decision(
            state=state,
            action=selected_action,
            reward=reward,
            latency_ms=latency_ms,
        )

        return results

    def _search_without_learning(
        self,
        query: str,
        kwargs: dict[str, Any],
        available_actions: list[ActionType],
    ) -> SearchResults:
        """Search without Q-Learning updates (circuit breaker open or error)."""
        # Pick first available action as heuristic
        selected_action = (
            available_actions[0] if available_actions else ActionType.EXPLORE
        )

        # Execute search
        unified_query = self._build_unified_query(query, selected_action, kwargs)
        return self._router.search(unified_query)

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
        # Reset circuit breaker
        self._circuit_breaker = CircuitBreaker()

    def recover_from_outcomes(self) -> dict[str, Any]:
        """Recover Q-table from outcome history when database is corrupted.

        Reads all outcomes from the OutcomeLogger database and rebuilds the
        Q-table by computing rewards from historical data. This allows the
        learning system to recover from a corrupted Q-Learning database.

        Returns:
            Dict with recovery stats: outcomes_processed, q_entries_updated, success
        """
        logger.info("Starting Q-table recovery from outcome history")

        try:
            # Get all outcomes with retry logic
            outcomes = retry_with_backoff(
                lambda: self._outcome_logger.get_outcomes(limit=10000),
                max_attempts=3,
            )
        except Exception as e:
            logger.error(f"Failed to retrieve outcomes for recovery: {e}")
            return {
                "success": False,
                "outcomes_processed": 0,
                "q_entries_updated": 0,
                "error": str(e),
            }

        if not outcomes:
            logger.warning("No outcomes found for recovery")
            return {
                "success": True,
                "outcomes_processed": 0,
                "q_entries_updated": 0,
                "error": None,
            }

        # Rebuild Q-table from outcomes
        q_updates: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        outcomes_processed = 0

        for outcome in outcomes:
            outcomes_processed += 1

            # Build state from outcome
            state = QState.from_context(
                outcome.task_description,
                {"task_type": outcome.task_type, "level": outcome.level},
            )
            state_key = state.to_key()

            # Compute reward from historical outcome
            reward = self._compute_reward(
                success=outcome.success,
                latency_ms=outcome.latency_ms,
                quality_score=outcome.quality_score,
            )

            # Map agent to action
            action = self._agent_to_action(outcome.agent)

            # Accumulate reward for this (state, action) pair
            q_updates[state_key][action.value] += reward

        # Apply accumulated Q-value updates
        q_entries_updated = 0
        for state_key, action_values in q_updates.items():
            state = QState.from_context(state_key.split("|")[0], {})
            for action_str, reward_sum in action_values.items():
                try:
                    action = ActionType(action_str)
                    # Apply average reward (divided by number of occurrences)
                    count = len([o for o in outcomes if o.agent == action_str])
                    avg_reward = reward_sum / max(count, 1)
                    self._q_learning.update(
                        state=state,
                        action=action,
                        reward=avg_reward,
                    )
                    q_entries_updated += 1
                except ValueError:
                    continue

        # Reset circuit breaker after successful recovery
        self._circuit_breaker = CircuitBreaker()

        logger.info(
            f"Q-table recovery complete: {outcomes_processed} outcomes, "
            f"{q_entries_updated} Q-entries updated"
        )

        return {
            "success": True,
            "outcomes_processed": outcomes_processed,
            "q_entries_updated": q_entries_updated,
            "error": None,
        }

    def _agent_to_action(self, agent: str) -> ActionType:
        """Map agent name to ActionType."""
        mapping = {
            "explore": ActionType.EXPLORE,
            "hephaestus": ActionType.HEPHAESTUS,
            "oracle": ActionType.ORACLE,
            "librarian": ActionType.LIBRARIAN,
            "delegate": ActionType.DELEGATE,
            "multimodal-looker": ActionType.MULTIMODAL,
        }
        return mapping.get(agent, ActionType.HEPHAESTUS)


# Import path for UnifiedMemoryQuery and SearchResults
# These are imported at module level from memory_core.router
__all__ = [
    "AdaptiveRouter",
    "LearningStats",
    "CircuitBreaker",
    "CircuitState",
    "retry_with_backoff",
]
