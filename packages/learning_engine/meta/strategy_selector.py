"""Strategy Selector — Contextual Bandit with Neural Thompson Sampling.

Phase 3.1 of Bleeding Edge Masterplan - implements contextual bandits for strategy selection.

Context = task embedding (384-dim) from model_cache
Actions = [embedding_routing, graph_routing, bandit_routing, heuristic_routing]
Reward = composite(success, latency, cost, quality)
Algorithm = Neural Thompson Sampling
Success criteria: Strategy selection accuracy > 75%; adaptation within 5 tasks
"""

from __future__ import annotations

import json
import math
import random
import sqlite3
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import numpy as np


# ============================================================================
# Configuration
# ============================================================================

# Strategy types as defined in masterplan
class StrategyType(Enum):
    """Available routing strategies."""

    EMBEDDING_ROUTING = "embedding_routing"
    GRAPH_ROUTING = "graph_routing"
    BANDIT_ROUTING = "bandit_routing"
    HEURISTIC_ROUTING = "heuristic_routing"

    @classmethod
    def all(cls) -> list["StrategyType"]:
        return list(cls)


# Thompson Sampling configuration
DEFAULT_PRIOR_MEAN = 0.5  # Prior mean reward
DEFAULT_PRIOR_VARIANCE = 1.0  # Prior variance (high = uncertain)
THOMPSON_SAMPLES = 100  # Number of posterior samples per selection

# Reward component weights (from masterplan)
REWARD_SUCCESS_WEIGHT = 1.0
REWARD_LATENCY_WEIGHT = 0.01  # per 100ms saved
REWARD_COST_WEIGHT = 0.5  # normalized
REWARD_QUALITY_WEIGHT = 0.5  # quality score bonus

# Adaptation targets
TARGET_ACCURACY = 0.75  # 75% accuracy target
ADAPTATION_TASKS = 5  # Adapt within 5 tasks

# Context dimension (matches EmbeddingCache.DIMENSION)
CONTEXT_DIM = 384


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class StrategyOutcome:
    """Outcome of a strategy selection."""

    task_id: str
    task_embedding: np.ndarray  # 384-dim context
    strategy: StrategyType
    success: bool
    latency_ms: float
    cost: float
    quality_score: Optional[float]
    reward: float


@dataclass
class StrategyStatistics:
    """Statistics for a strategy arm."""

    strategy: StrategyType
    pulls: int = 0
    total_reward: float = 0.0
    sum_squared: float = 0.0
    successes: int = 0

    @property
    def mean_reward(self) -> float:
        return self.total_reward / self.pulls if self.pulls > 0 else DEFAULT_PRIOR_MEAN

    @property
    def variance(self) -> float:
        if self.pulls < 2:
            return DEFAULT_PRIOR_VARIANCE
        mean = self.mean_reward
        return (self.sum_squared / self.pulls) - (mean**2)

    @property
    def success_rate(self) -> float:
        return self.successes / self.pulls if self.pulls > 0 else 0.0

    @property
    def confidence_radius(self) -> float:
        if self.pulls < 2:
            return float("inf")
        return 1.96 * math.sqrt(self.variance / self.pulls)


@dataclass
class SelectorStats:
    """Statistics showing strategy selection learning."""

    total_decisions: int = 0
    successful_selections: int = 0
    accuracy: float = 0.0
    adaptation_count: int = 0
    is_adapted: bool = False
    strategy_counts: dict[str, int] = field(default_factory=dict)
    recent_accuracy: list[float] = field(default_factory=list)


# ============================================================================
# Neural Network for Thompson Sampling
# ============================================================================


class StrategyPredictor:
    """Simple neural network to predict strategy rewards from context.

    Uses a lightweight 2-layer network for fast inference:
    - Input: 384-dim task embedding
    - Hidden: 64 units, ReLU
    - Output: |StrategyType| units (mean + variance per strategy)
    """

    def __init__(
        self,
        input_dim: int = CONTEXT_DIM,
        hidden_dim: int = 64,
        output_dim: int = len(StrategyType),
        learning_rate: float = 0.01,
    ):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.lr = learning_rate

        # Initialize weights with Xavier
        scale = math.sqrt(2.0 / (input_dim + hidden_dim))
        self.W1 = np.random.randn(input_dim, hidden_dim) * scale
        self.b1 = np.zeros(hidden_dim)
        scale = math.sqrt(2.0 / (hidden_dim + output_dim))
        self.W2 = np.random.randn(hidden_dim, output_dim) * scale
        self.b2 = np.zeros(output_dim)

        # Prior parameters (for Bayesian interpretation)
        self._prior_mean = DEFAULT_PRIOR_MEAN
        self._prior_var = DEFAULT_PRIOR_VARIANCE

        self._lock = threading.Lock()

    def forward(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Forward pass returning mean and log_variance predictions.

        Args:
            x: Input embedding (batch_size, input_dim)

        Returns:
            (mean, log_variance) predictions (batch_size, output_dim)
        """
        # Hidden layer
        h = np.maximum(0, x @ self.W1 + self.b1)  # ReLU

        # Output layer - mean
        mean = h @ self.W2 + self.b2

        # Output layer - log variance (ensure positive)
        log_var = h @ self.W2 + self.b2  # Shared weights for simplicity
        log_var = np.clip(log_var, -5, 2)  # Clamp for numerical stability

        return mean, log_var

    def predict(self, context: np.ndarray) -> np.ndarray:
        """Predict rewards for each strategy given context.

        Args:
            context: Task embedding (input_dim,)

        Returns:
            Predicted rewards for each strategy (output_dim,)
        """
        with self._lock:
            x = context.reshape(1, -1)
            mean, _ = self.forward(x)
            return mean[0]

    def sample_posterior(
        self, context: np.ndarray
    ) -> dict[StrategyType, float]:
        """Sample from posterior distribution for each strategy.

        Args:
            context: Task embedding (input_dim,)

        Returns:
            Dict of strategy -> sampled reward
        """
        with self._lock:
            x = context.reshape(1, -1)
            mean, log_var = self.forward(x)

            samples = {}
            for i, strategy in enumerate(StrategyType):
                mu = mean[0, i]
                sigma = math.exp(0.5 * log_var[0, i])
                # Sample from posterior
                samples[strategy] = random.gauss(mu, sigma)

            return samples

    def update(
        self,
        context: np.ndarray,
        strategy: StrategyType,
        actual_reward: float,
    ) -> None:
        """Update network weights using gradient descent.

        Simplified update: move weights toward maximizing reward.

        Args:
            context: Task embedding (input_dim,)
            strategy: The strategy that was selected
            actual_reward: The reward received
        """
        with self._lock:
            x = context.reshape(1, -1)
            mean, log_var = self.forward(x)

            strategy_idx = list(StrategyType).index(strategy)

            # Compute error
            predicted = mean[0, strategy_idx]
            error = actual_reward - predicted

            # Simple gradient update (single step toward target)
            # This is a simplified update - proper implementation would use
            # proper backpropagation through the network

            # Update output layer (simplified)
            gradient = error * self.lr

            # Apply gradient to relevant outputs
            h = np.maximum(0, x @ self.W1 + self.b1)
            if h[0, strategy_idx] != 0:  # Only update if activated
                self.W2[:, strategy_idx] += gradient * h[0] / (np.linalg.norm(h) + 1e-8)
                self.b2[strategy_idx] += gradient * 0.1

    def to_json(self) -> str:
        """Serialize network weights to JSON."""
        return json.dumps(
            {
                "W1": self.W1.tolist(),
                "b1": self.b1.tolist(),
                "W2": self.W2.tolist(),
                "b2": self.b2.tolist(),
            }
        )

    @classmethod
    def from_json(cls, data: str) -> "StrategyPredictor":
        """Deserialize network weights from JSON."""
        obj = json.loads(data)
        predictor = cls()
        predictor.W1 = np.array(obj["W1"])
        predictor.b1 = np.array(obj["b1"])
        predictor.W2 = np.array(obj["W2"])
        predictor.b2 = np.array(obj["b2"])
        return predictor


# ============================================================================
# Strategy Selector (Core)
# ============================================================================


class StrategySelector:
    """Contextual Bandit with Neural Thompson Sampling.

    Learns which routing strategy works best for each task type by:
    1. Using task embeddings as context (384-dim)
    2. Maintaining Bayesian posterior over strategy rewards
    3. Using Thompson Sampling for exploration-exploitation balance
    4. Adapting within 5 tasks to achieve >75% accuracy
    """

    def __init__(
        self,
        db_path: str = ".sisyphus/strategy_selector.db",
        embedding_cache=None,
        use_neural: bool = True,
    ):
        self._db_path = db_path
        self._embedding_cache = embedding_cache
        self._use_neural = use_neural

        # Strategy statistics (for Thompson Sampling)
        self._strategy_stats: dict[StrategyType, StrategyStatistics] = {
            s: StrategyStatistics(strategy=s) for s in StrategyType
        }

        # Neural predictor (for context-aware selection)
        self._predictor = StrategyPredictor() if use_neural else None

        # Outcome history for adaptation tracking
        self._outcome_history: list[StrategyOutcome] = []
        self._recent_outcomes: int = 20  # Track last 20 for adaptation

        # Decision tracking
        self._decision_history: list[dict[str, Any]] = []
        self._lock = threading.Lock()

        # Load from database
        self._load_from_db()

    def _get_embedding(self, task_description: str) -> np.ndarray:
        """Get 384-dim embedding for task description."""
        if self._embedding_cache:
            try:
                return self._embedding_cache.encode(task_description)
            except Exception:
                pass

        # Fallback: random embedding (will be updated quickly)
        return np.random.randn(CONTEXT_DIM).astype(np.float32)

    def select_strategy(
        self, task_description: str, context: Optional[dict[str, Any]] = None
    ) -> tuple[StrategyType, dict[str, Any]]:
        """Select optimal routing strategy for the task.

        Uses Neural Thompson Sampling to balance exploration/exploitation.

        Args:
            task_description: The task to route
            context: Optional additional context

        Returns:
            (selected_strategy, decision_metadata)
        """
        with self._lock:
            # Get task embedding
            embedding = self._get_embedding(task_description)

            # Thompson Sampling: sample from posterior
            if self._use_neural and self._predictor:
                # Neural Thompson Sampling
                posterior_samples = self._predictor.sample_posterior(embedding)

                # Add Bayesian prior (combine with empirical statistics)
                samples = {}
                for strategy in StrategyType:
                    stats = self._strategy_stats[strategy]
                    if stats.pulls > 0:
                        # Combine neural prediction with empirical estimate
                        neural_pred = posterior_samples.get(strategy, DEFAULT_PRIOR_MEAN)
                        empirical = stats.mean_reward
                        # Weight by number of pulls (more pulls = more trust in empirical)
                        weight = min(stats.pulls / 10.0, 0.8)
                        samples[strategy] = (1 - weight) * neural_pred + weight * empirical
                    else:
                        samples[strategy] = posterior_samples.get(
                            strategy, DEFAULT_PRIOR_MEAN
                        )

                # Select strategy with highest sampled reward
                selected = max(samples.keys(), key=lambda s: samples[s])
                strategy_source = "neural_thompson"
            else:
                # Pure Thompson Sampling (based on empirical statistics)
                samples = {}
                for strategy in StrategyType:
                    stats = self._strategy_stats[strategy]
                    if stats.pulls == 0:
                        samples[strategy] = DEFAULT_PRIOR_MEAN
                    elif stats.confidence_radius == float("inf"):
                        samples[strategy] = float("inf")  # Prioritize unexplored
                    else:
                        samples[strategy] = random.gauss(
                            stats.mean_reward, stats.confidence_radius
                        )

                selected = max(samples.keys(), key=lambda s: samples[s])
                strategy_source = "thompson"

            # Get decision metadata
            stats = self._strategy_stats[selected]
            q_values = self._get_q_values(embedding)

            metadata = {
                "strategy": selected.value,
                "source": strategy_source,
                "expected_reward": stats.mean_reward,
                "confidence": stats.confidence_radius,
                "success_rate": stats.success_rate,
                "pulls": stats.pulls,
                "q_values": q_values,
                "total_decisions": len(self._decision_history),
            }

            # Track decision
            self._track_decision(
                task_description=task_description,
                embedding=embedding,
                selected=selected,
                metadata=metadata,
            )

            return selected, metadata

    def _get_q_values(self, embedding: np.ndarray) -> dict[str, float]:
        """Get Q-values (expected rewards) for each strategy."""
        if self._predictor:
            try:
                predictions = self._predictor.predict(embedding)
                return {
                    strategy.value: float(predictions[i])
                    for i, strategy in enumerate(StrategyType)
                }
            except Exception:
                pass

        # Fallback to empirical
        return {
            strategy.value: stats.mean_reward
            for strategy, stats in self._strategy_stats.items()
        }

    def _track_decision(
        self,
        task_description: str,
        embedding: np.ndarray,
        selected: StrategyType,
        metadata: dict[str, Any],
    ) -> None:
        """Track decision for learning statistics."""
        self._decision_history.append(
            {
                "task": task_description,
                "embedding": embedding.tolist(),
                "strategy": selected.value,
                "metadata": metadata,
            }
        )

    def record_outcome(
        self,
        task_id: str,
        task_description: str,
        strategy: StrategyType,
        success: bool,
        latency_ms: float,
        cost: float,
        quality_score: Optional[float] = None,
    ) -> dict[str, Any]:
        """Record outcome and update strategy statistics.

        This is the core learning loop - updates both the neural network
        and empirical statistics.

        Args:
            task_id: Unique task identifier
            task_description: The task description
            strategy: The strategy that was selected
            success: Whether the task succeeded
            latency_ms: Task latency in milliseconds
            cost: Normalized cost (0-1)
            quality_score: Optional quality score (0-1)

        Returns:
            Analysis of what was learned
        """
        # Compute composite reward
        reward = self._compute_reward(
            success=success,
            latency_ms=latency_ms,
            cost=cost,
            quality_score=quality_score,
        )

        # Get task embedding
        embedding = self._get_embedding(task_description)

        # Create outcome
        outcome = StrategyOutcome(
            task_id=task_id,
            task_embedding=embedding,
            strategy=strategy,
            success=success,
            latency_ms=latency_ms,
            cost=cost,
            quality_score=quality_score,
            reward=reward,
        )

        with self._lock:
            self._outcome_history.append(outcome)

            # Keep only recent outcomes
            if len(self._outcome_history) > 1000:
                self._outcome_history = self._outcome_history[-500:]

            # Update strategy statistics
            stats = self._strategy_stats[strategy]
            stats.pulls += 1
            stats.total_reward += reward
            stats.sum_squared += reward**2
            if success:
                stats.successes += 1

            # Update neural predictor
            if self._predictor:
                self._predictor.update(embedding, strategy, reward)

            # Save to database
            self._save_to_db()

        # Return analysis
        return {
            "strategy": strategy.value,
            "reward": reward,
            "success": success,
            "stats": {
                "pulls": stats.pulls,
                "mean_reward": stats.mean_reward,
                "success_rate": stats.success_rate,
            },
            "adaptation_status": self._check_adaptation(),
        }

    def _compute_reward(
        self,
        success: bool,
        latency_ms: float,
        cost: float,
        quality_score: Optional[float],
    ) -> float:
        """Compute composite reward from outcome components.

        Reward = w_success * success + w_latency * latency_bonus
               + w_cost * cost_bonus + w_quality * quality_bonus
        """
        # Base reward: success = +1, failure = -1
        base = 1.0 if success else -1.0

        # Latency bonus: faster is better (normalize to 0-1)
        latency_bonus = max(0, (500 - latency_ms) / 500) * REWARD_LATENCY_WEIGHT

        # Cost bonus: cheaper is better
        cost_bonus = (1 - cost) * REWARD_COST_WEIGHT

        # Quality bonus: higher quality = bonus
        quality_bonus = 0.0
        if quality_score is not None:
            quality_bonus = (quality_score - 0.5) * REWARD_QUALITY_WEIGHT

        return base + latency_bonus + cost_bonus + quality_bonus

    def _check_adaptation(self) -> dict[str, Any]:
        """Check if selector has adapted within target task count."""
        recent = self._outcome_history[-ADAPTATION_TASKS:]

        if len(recent) < ADAPTATION_TASKS:
            return {
                "adapted": False,
                "progress": f"{len(recent)}/{ADAPTATION_TASKS} tasks",
                "accuracy": 0.0,
            }

        # Compute accuracy on recent outcomes
        successes = sum(1 for o in recent if o.success)
        accuracy = successes / len(recent)

        return {
            "adapted": accuracy >= TARGET_ACCURACY,
            "progress": f"{len(recent)}/{ADAPTATION_TASKS} tasks",
            "accuracy": accuracy,
            "target": TARGET_ACCURACY,
        }

    def get_stats(self) -> SelectorStats:
        """Get comprehensive strategy selection statistics."""
        with self._lock:
            total = len(self._outcome_history)
            successful = sum(1 for o in self._outcome_history if o.success)

            # Recent accuracy (last 20)
            recent = self._outcome_history[-20:]
            recent_accuracy = []
            if recent:
                for i in range(len(recent)):
                    window = recent[max(0, i - 4) : i + 1]
                    if window:
                        acc = sum(1 for o in window if o.success) / len(window)
                        recent_accuracy.append(acc)

            # Strategy counts
            strategy_counts = defaultdict(int)
            for outcome in self._outcome_history:
                strategy_counts[outcome.strategy.value] += 1

            # Check adaptation
            adaptation = self._check_adaptation()

            return SelectorStats(
                total_decisions=total,
                successful_selections=successful,
                accuracy=successful / total if total > 0 else 0.0,
                adaptation_count=len(self._outcome_history),
                is_adapted=adaptation.get("adapted", False),
                strategy_counts=dict(strategy_counts),
                recent_accuracy=recent_accuracy,
            )

    def reset(self) -> None:
        """Reset all learned state (for testing)."""
        with self._lock:
            self._strategy_stats = {
                s: StrategyStatistics(strategy=s) for s in StrategyType
            }
            self._predictor = StrategyPredictor() if self._use_neural else None
            self._outcome_history = []
            self._decision_history = []

    # ============================================================================
    # Database Persistence
    # ============================================================================

    def _load_from_db(self) -> None:
        """Load state from database."""
        if not self._db_path:
            return
        try:
            conn = sqlite3.connect(self._db_path)
            cur = conn.execute(
                "SELECT strategy_stats_json, predictor_json FROM strategy_selector WHERE id=1"
            )
            row = cur.fetchone()
            if row:
                # Load strategy statistics
                stats_dict = json.loads(row[0])
                for strategy_str, stats_data in stats_dict.items():
                    try:
                        strategy = StrategyType(strategy_str)
                        stats = self._strategy_stats[strategy]
                        stats.pulls = stats_data.get("pulls", 0)
                        stats.total_reward = stats_data.get("total_reward", 0.0)
                        stats.sum_squared = stats_data.get("sum_squared", 0.0)
                        stats.successes = stats_data.get("successes", 0)
                    except ValueError:
                        continue

                # Load predictor weights
                if row[1] and self._predictor:
                    self._predictor = StrategyPredictor.from_json(row[1])

            conn.close()
        except Exception:
            pass  # Table doesn't exist yet

    def _save_to_db(self) -> None:
        """Save state to database."""
        if not self._db_path:
            return
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute(
                """CREATE TABLE IF NOT EXISTS strategy_selector (
                    id INTEGER PRIMARY KEY,
                    strategy_stats_json TEXT,
                    predictor_json TEXT
                )"""
            )

            # Serialize strategy statistics
            stats_dict = {}
            for strategy, stats in self._strategy_stats.items():
                stats_dict[strategy.value] = {
                    "pulls": stats.pulls,
                    "total_reward": stats.total_reward,
                    "sum_squared": stats.sum_squared,
                    "successes": stats.successes,
                }

            # Serialize predictor
            predictor_json = self._predictor.to_json() if self._predictor else None

            conn.execute(
                "INSERT OR REPLACE INTO strategy_selector (id, strategy_stats_json, predictor_json) VALUES (1, ?, ?)",
                (json.dumps(stats_dict), predictor_json),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass


# ============================================================================
# Integration with Unified Router
# ============================================================================


class StrategyRouter:
    """Wrapper that integrates StrategySelector with the unified router.

    Provides a clean interface for routing tasks to strategies while
    maintaining backward compatibility with existing Q-Learning.
    """

    def __init__(
        self,
        strategy_selector: Optional[StrategySelector] = None,
        adaptive_router=None,  # Existing AdaptiveRouter
    ):
        self._selector = strategy_selector or StrategySelector()
        self._adaptive_router = adaptive_router

    def select_strategy(
        self, task_description: str, context: Optional[dict[str, Any]] = None
    ) -> tuple[StrategyType, dict[str, Any]]:
        """Select routing strategy for task."""
        return self._selector.select_strategy(task_description, context)

    def record_outcome(
        self,
        task_id: str,
        task_description: str,
        strategy: StrategyType,
        success: bool,
        latency_ms: float,
        cost: float = 0.0,
        quality_score: Optional[float] = None,
    ) -> dict[str, Any]:
        """Record outcome and update selector."""
        return self._selector.record_outcome(
            task_id=task_id,
            task_description=task_description,
            strategy=strategy,
            success=success,
            latency_ms=latency_ms,
            cost=cost,
            quality_score=quality_score,
        )

    def get_stats(self) -> SelectorStats:
        """Get selector statistics."""
        return self._selector.get_stats()

    def reset(self) -> None:
        """Reset selector state."""
        self._selector.reset()


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "StrategyType",
    "StrategySelector",
    "StrategyRouter",
    "SelectorStats",
    "StrategyStatistics",
    "TARGET_ACCURACY",
    "ADAPTATION_TASKS",
    "CONTEXT_DIM",
]
