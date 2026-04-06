# KB|"""Advanced Learning Engine — Cutting-edge ML for routing optimization.

# ZM|Adds:
# ZV|- Q-Learning: Tabular RL for optimal action selection
# KM|- Multi-Armed Bandit: Epsilon-Greedy + UCB exploration
# KM|- Meta-Learning: MAML-style fast adaptation
# QT|- Reward Shaping: Composite reward functions
# KM|- Counterfactual Learning: What-if scenario analysis
# ZM|- Continual Learning: Elastic weight consolidation
# KM|- Active Learning: Confidence intervals for uncertainty
# """

from __future__ import annotations

import json
import math
import sqlite3
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_ALPHA = 0.1  # Learning rate for Q-learning
DEFAULT_GAMMA = 0.9  # Discount factor
DEFAULT_EPSILON = 0.1  # Exploration rate (epsilon-greedy)
DEFAULT_LAMBDA = 0.01  # EWC regularization strength
CONTEXT_DIM = 64  # Embedding dimension for context
META_LR = 0.01  # Meta-learning inner loop LR
META_TASKs = 5  # Tasks per meta-update

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


class ActionType(Enum):
    """Available actions for routing decisions."""

    EXPLORE = "explore"
    DELEGATE = "delegate"
    ORACLE = "oracle"
    LIBRARIAN = "librarian"
    HEPHAESTUS = "hephaestus"
    MULTIMODAL = "multimodal"


@dataclass
class QState:
    """A state representation for Q-learning (task + context hash)."""

    task: str
    context_hash: str

    def to_key(self) -> str:
        return f"{self.task}|{self.context_hash}"

    @staticmethod
    def from_context(task: str, context: dict[str, Any]) -> "QState":
        ctx_hash = _hash_context(context)
        return QState(task=task, context_hash=ctx_hash[:16])


@dataclass
class QTable:
    """Q-value table with (state, action) -> value mapping."""

    values: dict[str, dict[str, float]] = field(
        default_factory=lambda: defaultdict(dict)
    )

    def get(self, state: QState, action: ActionType) -> float:
        key = state.to_key()
        return self.values.get(key, {}).get(action.value, 0.0)

    def set(self, state: QState, action: ActionType, value: float) -> None:
        self.values[state.to_key()][action.value] = value

    def update(self, state: QState, action: ActionType, delta: float) -> None:
        key = state.to_key()
        if key not in self.values:
            self.values[key] = {}
        if action.value not in self.values[key]:
            self.values[key][action.value] = 0.0
        self.values[key][action.value] += delta

    def to_json(self) -> str:
        # Compact JSON for storage
        return json.dumps(self.values, separators=(",", ":"))


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


@dataclass
class MetaParameters:
    """MAML-style meta-parameters for fast adaptation."""

    inner_lr: float = META_LR
    outer_lr: float = 0.001
    task_gradients: dict[str, list[float]] = field(default_factory=dict)


@dataclass
class EWCParams:
    """Elastic Weight Consolidation parameters."""

    fisher_diagonal: dict[str, float] = field(default_factory=dict)
    optimal_params: dict[str, float] = field(default_factory=dict)
    lambda_reg: float = DEFAULT_LAMBDA


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


@dataclass
class CounterfactualResult:
    """Result of counterfactual 'what-if' analysis."""

    hypothetical_action: str
    estimated_reward: float
    confidence: float
    based_on: int  # How many similar contexts this is based on


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash_context(context: dict[str, Any]) -> str:
    """Create a deterministic hash from context dict."""
    if not context:
        return "empty"
    # Simple hash based on sorted key-value pairs
    s = "|".join(f"{k}:{v}" for k, v in sorted(context.items()))
    return str(abs(hash(s)) % 1000000)


def _softmax(values: list[float], temperature: float = 1.0) -> list[float]:
    """Compute softmax probabilities."""
    if not values:
        return []
    max_v = max(values)
    exp = [math.exp((v - max_v) / temperature) for v in values]
    total = sum(exp)
    return [e / total for e in exp]


# ---------------------------------------------------------------------------
# Core Learning Engines
# ---------------------------------------------------------------------------


class QLearningEngine:
    """Tabular Q-Learning for optimal action selection.

    Q(s, a) = Q(s, a) + α * (r + γ * max_a' Q(s', a') - Q(s, a))
    """

    def __init__(
        self,
        alpha: float = DEFAULT_ALPHA,
        gamma: float = DEFAULT_GAMMA,
        db_path: str | None = None,
    ):
        self.alpha = alpha
        self.gamma = gamma
        self._q_table = QTable()
        self._db_path = db_path
        self._load_from_db()

    def _load_from_db(self) -> None:
        if not self._db_path:
            return
        try:
            conn = sqlite3.connect(self._db_path)
            cur = conn.execute("SELECT state_action_json FROM q_learning WHERE id=1")
            row = cur.fetchone()
            if row:
                self._q_table.values = json.loads(row[0])
            conn.close()
        except Exception:
            pass  # Table doesn't exist yet

    def _save_to_db(self) -> None:
        if not self._db_path:
            return
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS q_learning (
                    id INTEGER PRIMARY KEY,
                    state_action_json TEXT
                )
            """)
            conn.execute(
                "INSERT OR REPLACE INTO q_learning (id, state_action_json) VALUES (1, ?)",
                (self._q_table.to_json(),),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def select_action(
        self,
        state: QState,
        available_actions: list[ActionType],
        epsilon: float = DEFAULT_EPSILON,
    ) -> ActionType:
        """Epsilon-greedy action selection."""
        import random

        if random.random() < epsilon:
            return random.choice(available_actions)

        # Greedy: select action with highest Q-value
        best = available_actions[0]
        best_value = self._q_table.get(state, best)
        for action in available_actions:
            val = self._q_table.get(state, action)
            if val > best_value:
                best_value = val
                best = action
        return best

    def update(
        self,
        state: QState,
        action: ActionType,
        reward: float,
        next_state: QState | None = None,
    ) -> None:
        """Update Q-value using TD learning."""
        current_q = self._q_table.get(state, action)

        if next_state:
            # Compute max Q-value for next state
            max_next_q = max(self._q_table.get(next_state, a) for a in ActionType)
            target = reward + self.gamma * max_next_q
        else:
            target = reward

        td_error = target - current_q
        self._q_table.update(state, action, self.alpha * td_error)
        self._save_to_db()

    def get_q_values(self, state: QState) -> dict[str, float]:
        """Get all Q-values for a state."""
        return {action.value: self._q_table.get(state, action) for action in ActionType}


class MultiArmedBandit:
    """Multi-Armed Bandit with Epsilon-Greedy and UCB strategies.

    Supports:
    - Epsilon-Greedy: Explore with probability ε, exploit otherwise
    - UCB (Upper Confidence Bound): Balance exploration/exploitation
    - Thompson Sampling: Bayesian approach
    """

    def __init__(
        self,
        epsilon: float = DEFAULT_EPSILON,
        ucb_c: float = 2.0,  # Exploration constant for UCB
        strategy: str = "ucb",  # "epsilon", "ucb", or "thompson"
    ):
        self.epsilon = epsilon
        self.ucb_c = ucb_c
        self.strategy = strategy
        self._arms: dict[str, BanditArm] = {}
        self._total_pulls = 0

    def select_arm(self, context: str) -> str:
        """Select an arm based on the chosen strategy."""
        if not self._arms:
            return "delegate"  # Default fallback

        import random

        if self.strategy == "epsilon":
            if random.random() < self.epsilon:
                return random.choice(list(self._arms.keys()))
            # Exploit: choose best
            return max(self._arms.keys(), key=lambda a: self._arms[a].mean_reward)

        elif self.strategy == "ucb":
            # UCB: maximize mean + confidence bound
            best_arm = None
            best_value = float("-inf")
            for arm_name, arm in self._arms.items():
                if arm.pulls == 0:
                    return arm_name  # Unexplored arm
                ucb_value = arm.mean_reward + self.ucb_c * math.sqrt(
                    math.log(self._total_pulls) / arm.pulls
                )
                if ucb_value > best_value:
                    best_value = ucb_value
                    best_arm = arm_name
            return best_arm or "delegate"

        elif self.strategy == "thompson":
            # Thompson Sampling: sample from posterior
            samples = {}
            for arm_name, arm in self._arms.items():
                if arm.pulls == 0:
                    samples[arm_name] = float("inf")
                else:
                    # Sample from posterior (simplified: normal approximation)
                    import random

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
        # Initialize from meta-parameters
        adapted = dict(self._meta_parameters)

        if not support_outcomes:
            return adapted

        # Compute gradient-like update (simplified)
        for outcome in support_outcomes:
            reward = outcome.get("reward", 0)
            # Simple gradient: adjust based on reward
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

        # Simplified meta-update
        avg_reward = sum(o.get("reward", 0) for o in query_outcomes) / len(
            query_outcomes
        )

        # Update meta-parameters
        if not self._meta_parameters:
            # Initialize with default values
            self._meta_parameters = {
                "q_learning_rate": 0.1,
                "epsilon": 0.1,
                "gamma": 0.9,
            }

        # Adjust based on query performance
        for key in self._meta_parameters:
            self._meta_parameters[key] += self.outer_lr * (avg_reward - 0.5)

    def get_parameters(self) -> dict[str, float]:
        return self._meta_parameters


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

        # Update optimal parameters
        self._optimal_params = dict(task_params)

        # Compute Fisher diagonal (simplified: based on outcome variance)
        if outcomes:
            rewards = [o.get("reward", 0) for o in outcomes]
            variance = sum(
                (r - sum(rewards) / len(rewards)) ** 2 for r in rewards
            ) / len(rewards)

            for key in task_params:
                self._fisher_diagonal[key] = variance + 0.01  # Add small constant


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
            return 1.0  # No data = max uncertainty

        stats = self._context_statistics[key]
        if stats.get("count", 0) < 2:
            return 0.8  # Low data = high uncertainty

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

        # Update variance
        if stats["count"] >= 2:
            mean = stats["sum"] / stats["count"]
            stats["variance"] = (stats["sum_sq"] / stats["count"]) - (mean**2)


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


# ---------------------------------------------------------------------------
# Advanced Learning Orchestrator
# ---------------------------------------------------------------------------


class AdvancedLearningEngine:
    """Orchestrates all advanced learning components.

    Combines:
    - Q-Learning for optimal action selection
    - Multi-Armed Bandit for exploration
    - Meta-Learning for fast adaptation
    - EWC for continual learning
    - Active Learning for uncertainty
    - Counterfactual for what-if analysis
    """

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path
        self._q_learning = QLearningEngine(db_path=db_path)
        self._bandit = MultiArmedBandit(strategy="ucb")
        self._meta = MetaLearningEngine()
        self._ewc = EWCEngine()
        self._active = ActiveLearningEngine()
        self._counterfactual = CounterfactualEngine()

        self._baseline_latency = 500.0  # ms
        self._baseline_cost = 0.01  # normalized

    def select_action(
        self, task: str, context: dict[str, Any], available_actions: list[ActionType]
    ) -> tuple[ActionType, dict[str, Any]]:
        """Select optimal action using all learning components.

        Returns:
            (selected_action, decision_metadata)
        """
        state = QState.from_context(task, context)

        # 1. Check if we need more data (Active Learning)
        action_names = [a.value for a in available_actions]
        needs_data = [
            self._active.should_collect_more_data(context, a.value)
            for a in available_actions
        ]

        # 2. Use Q-Learning with epsilon-greedy
        selected = self._q_learning.select_action(state, available_actions)

        # 3. Possibly override with Bandit if high uncertainty
        if any(needs_data):
            bandit_selection = self._bandit.select_arm(task)
            # Convert to ActionType if available
            for action in available_actions:
                if action.value == bandit_selection:
                    selected = action
                    break

        # 4. Get Q-values for decision metadata
        q_values = self._q_learning.get_q_values(state)

        # 5. Check confidence
        uncertainty = self._active.compute_uncertainty(context, selected.value)

        metadata = {
            "q_values": q_values,
            "uncertainty": uncertainty,
            "needs_more_data": uncertainty > 0.3,
            "strategy": "q_learning" if uncertainty < 0.3 else "bandit",
            "task": task,
        }

        return selected, metadata

    def record_outcome(
        self,
        task: str,
        action: ActionType,
        success: bool,
        latency_ms: float,
        cost: float,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Record outcome and update all learning components.

        Returns:
            analysis of what was learned
        """
        state = QState.from_context(task, context)

        # 1. Compute composite reward
        q_values = self._q_learning.get_q_values(state)
        max_q = max(q_values.values()) if q_values else 0.5
        confidence = (max_q + 1) / 2  # Normalize to 0.5-1.0

        is_novel = action.value not in self._bandit._arms

        composite = CompositeReward.compute(
            success=success,
            latency_ms=latency_ms,
            cost=cost,
            confidence=confidence,
            is_novel=is_novel,
            baseline_latency=self._baseline_latency,
            baseline_cost=self._baseline_cost,
        )

        total_reward = composite.total

        # 2. Update Q-Learning
        self._q_learning.update(state, action, total_reward)

        # 3. Update Bandit
        self._bandit.update(action.value, total_reward)

        # 4. Update Active Learning
        self._active.update_statistics(context, action.value, total_reward)

        # 5. Store for Counterfactual
        self._counterfactual.store_outcome(context, action.value, total_reward)

        # 6. Update EWC (periodically)
        if getattr(self._ewc, "_task_count", 0) % 10 == 0:
            self._ewc.update_after_task(
                self._meta.get_parameters(), [{"reward": total_reward}]
            )

        return {
            "composite_reward": composite.to_dict()
            if hasattr(composite, "to_dict")
            else {
                "total": total_reward,
                "components": {
                    "base": composite.base,
                    "latency": composite.latency_bonus,
                    "cost": composite.cost_penalty,
                    "confidence": composite.confidence_bonus,
                    "exploration": composite.exploration_bonus,
                },
            },
            "q_value": self._q_learning.get_q_values(state).get(action.value, 0),
            "bandit_stats": self._bandit.get_statistics(),
        }

    def analyze_counterfactual(
        self, context: dict[str, Any], current_action: str
    ) -> list[CounterfactualResult]:
        """Run counterfactual analysis for all actions."""
        actions = ["explore", "delegate", "oracle", "librarian", "hephaestus"]
        return [
            self._counterfactual.estimate(context, a, actions)
            for a in actions
            if a != current_action
        ]

    def get_learning_status(self) -> dict[str, Any]:
        """Get comprehensive learning status."""
        return {
            "q_learning": {
                "states_learned": len(self._q_learning._q_table.values),
                "alpha": self._q_learning.alpha,
                "gamma": self._q_learning.gamma,
            },
            "bandit": {
                "arms": len(self._bandit._arms),
                "total_pulls": self._bandit._total_pulls,
                "strategy": self._bandit.strategy,
            },
            "meta": {
                "parameters": self._meta.get_parameters(),
                "task_count": getattr(self._meta, "_task_count", 0),
            },
            "ewc": {
                "task_count": getattr(self._ewc, "_task_count", 0),
                "lambda_reg": self._ewc.lambda_reg,
            },
            "active_learning": {
                "contexts_tracked": len(self._active._context_statistics),
                "uncertainty_threshold": self._active.uncertainty_threshold,
            },
            "counterfactual": {
                "contexts_stored": len(self._counterfactual._similar_contexts)
            },
        }
