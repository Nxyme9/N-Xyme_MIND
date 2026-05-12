"""Routing Weight Optimizer — Bayesian routing with Thompson Sampling, UCB, and adaptive learning."""

from __future__ import annotations

import json
import logging
import math
import random
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

logger = logging.getLogger("routing-optimizer")


def _beta_sample(alpha: float, beta: float) -> float:
    """Sample from Beta(alpha, beta) via accept-reject."""
    for _ in range(100):
        u1, u2 = random.random(), random.random()
        x = u1 ** (1.0 / alpha)
        y = u2 ** (1.0 / beta)
        if x + y <= 1:
            z = x / (x + y)
            if u2 < beta * (1 - z) ** (beta - 1) / (alpha * z ** (alpha - 1) + beta * (1 - z) ** (beta - 1)):
                return z
    return alpha / (alpha + beta)


@dataclass
class AgentWeights:
    success_rate: float = 0.5
    avg_latency_ms: float = 0.0
    total_tasks: int = 0
    success_count: int = 0
    failure_count: int = 0
    by_level: Dict[int, Dict[str, float]] = field(default_factory=dict)
    beta_alpha: float = 1.0
    beta_beta: float = 1.0
    current_alpha: float = 0.1

    def bayesian_mean(self) -> float:
        return self.beta_alpha / (self.beta_alpha + self.beta_beta) if (self.beta_alpha + self.beta_beta) > 0 else 0.5


@dataclass
class RoutingRecommendation:
    recommended_agent: str
    confidence: float
    reason: str
    weights: Dict[str, AgentWeights]
    exploration_bonus: float = 0.0
    bayesian_lower: float = 0.0
    bayesian_upper: float = 1.0


class RoutingWeightOptimizer:
    def __init__(
        self,
        alpha: float = 0.1,
        persist_path: Optional[str] = None,
        cold_start_prior: float = 0.5,
        ucb_c: float = 2.0,
        adaptive_alpha: bool = True,
    ):
        self._base_alpha = alpha
        self._cold_start_prior = cold_start_prior
        self._ucb_c = ucb_c
        self._adaptive_alpha = adaptive_alpha
        self._weights: Dict[str, AgentWeights] = {}
        self._initialized = False
        self._total_updates = 0

        if persist_path is None:
            project_root = Path(__file__).parent.parent.parent
            persist_path = str(project_root / ".sisyphus" / "routing-weights.json")
        self._persist_path = persist_path

        self._load_weights()
        self._warm_start_from_db()

    def _warm_start_from_db(self) -> None:
        try:
            db_path = Path(".sisyphus/outcomes.db")
            if db_path.exists():
                import sqlite3
                conn = sqlite3.connect(str(db_path))
                cursor = conn.execute(
                    "SELECT agent, COUNT(*), SUM(success) FROM delegation_records GROUP BY agent"
                )
                for agent, count, successes in cursor.fetchall():
                    if agent in self._weights:
                        w = self._weights[agent]
                        w.beta_alpha = 1.0 + (successes or 0)
                        w.beta_beta = 1.0 + (count - (successes or 0))
                        w.total_tasks = count
                        w.success_count = successes or 0
                        w.failure_count = count - (successes or 0)
                        w.success_rate = w.bayesian_mean()
                conn.close()
                logger.info("Warm-started from outcomes.db")
        except Exception as e:
            logger.debug(f"Could not warm-start from db: {e}")

    def _compute_adaptive_alpha(self, weights: AgentWeights) -> float:
        if not self._adaptive_alpha:
            return self._base_alpha
        if weights.total_tasks < 5:
            return min(self._base_alpha * 2.0, 0.3)
        confidence_width = min(1.0, weights.bayesian_mean() + 0.5 - max(0.0, weights.bayesian_mean() - 0.5))
        return min(max(self._base_alpha * (1.2 - confidence_width * 0.4), self._base_alpha * 0.3), self._base_alpha * 3.0)

    def _load_weights(self) -> None:
        try:
            path = Path(self._persist_path)
            if path.exists():
                with open(path, 'r') as f:
                    data = json.load(f)
                for agent_name, agent_data in data.items():
                    weights = AgentWeights(
                        success_rate=agent_data.get('success_rate', self._cold_start_prior),
                        avg_latency_ms=agent_data.get('avg_latency_ms', 0.0),
                        total_tasks=agent_data.get('total_tasks', 0),
                        success_count=agent_data.get('success_count', 0),
                        failure_count=agent_data.get('failure_count', 0),
                        by_level=agent_data.get('by_level', {}),
                        beta_alpha=agent_data.get('beta_alpha', 1.0),
                        beta_beta=agent_data.get('beta_beta', 1.0),
                        current_alpha=agent_data.get('current_alpha', self._base_alpha),
                    )
                    self._weights[agent_name] = weights
                self._initialized = True
                logger.info(f"Loaded weights for {len(self._weights)} agents from {self._persist_path}")
        except Exception as e:
            logger.warning(f"Failed to load weights: {e}")

    def _persist_weights(self) -> None:
        try:
            path = Path(self._persist_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            for agent_name, weights in self._weights.items():
                data[agent_name] = {
                    'success_rate': weights.success_rate,
                    'avg_latency_ms': weights.avg_latency_ms,
                    'total_tasks': weights.total_tasks,
                    'success_count': weights.success_count,
                    'failure_count': weights.failure_count,
                    'by_level': weights.by_level,
                    'beta_alpha': weights.beta_alpha,
                    'beta_beta': weights.beta_beta,
                    'current_alpha': weights.current_alpha,
                }
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist weights: {e}")

    def _initialize_default_weights(self) -> None:
        default_agents = [
            "hephaestus", "sisyphus-junior", "explore", "librarian",
            "oracle", "momus", "prometheus", "metis", "atlas"
        ]
        for agent in default_agents:
            if agent not in self._weights:
                self._weights[agent] = AgentWeights(success_rate=self._cold_start_prior)
        self._initialized = True

    def update_weights(self, agent: str, level: int, success: bool, latency_ms: float = 0) -> None:
        if not self._initialized:
            self._initialize_default_weights()

        if agent not in self._weights:
            self._weights[agent] = AgentWeights(success_rate=self._cold_start_prior)

        weights = self._weights[agent]
        self._total_updates += 1

        effective_alpha = self._compute_adaptive_alpha(weights)
        weights.current_alpha = effective_alpha

        if success:
            weights.beta_alpha += 1.0
        else:
            weights.beta_beta += 1.0

        weights.total_tasks += 1

        if success:
            weights.success_count += 1
        else:
            weights.failure_count += 1

        weights.success_rate = (
            effective_alpha * (1.0 if success else 0.0) +
            (1 - effective_alpha) * weights.success_rate
        )

        if latency_ms > 0:
            if weights.avg_latency_ms == 0:
                weights.avg_latency_ms = latency_ms
            else:
                weights.avg_latency_ms = (
                    effective_alpha * latency_ms +
                    (1 - effective_alpha) * weights.avg_latency_ms
                )

        if level not in weights.by_level:
            weights.by_level[level] = {"success_rate": self._cold_start_prior, "avg_latency_ms": 0.0, "beta_alpha": 1.0, "beta_beta": 1.0}

        level_weights = weights.by_level[level]
        level_weights["success_rate"] = (
            effective_alpha * (1.0 if success else 0.0) +
            (1 - effective_alpha) * level_weights["success_rate"]
        )

        if success:
            level_weights["beta_alpha"] = level_weights.get("beta_alpha", 1.0) + 1.0
        else:
            level_weights["beta_beta"] = level_weights.get("beta_beta", 1.0) + 1.0

        if latency_ms > 0:
            if level_weights["avg_latency_ms"] == 0:
                level_weights["avg_latency_ms"] = latency_ms
            else:
                level_weights["avg_latency_ms"] = (
                    effective_alpha * latency_ms +
                    (1 - effective_alpha) * level_weights["avg_latency_ms"]
                )

        logger.debug(f"Updated {agent} (L{level}): α={effective_alpha:.3f}, β=({weights.beta_alpha:.1f},{weights.beta_beta:.1f}), mean={weights.bayesian_mean():.3f}")
        self._persist_weights()

    def _score_agents_thompson(self, level: int) -> List[Tuple[str, float, str]]:
        agent_scores = []
        total_pulls = max(self._total_updates, 1)

        for agent, weights in self._weights.items():
            if level in weights.by_level:
                lw = weights.by_level[level]
                level_alpha = lw.get("beta_alpha", 1.0)
                level_beta = lw.get("beta_beta", 1.0)
                level_success_rate = lw["success_rate"]
                level_latency = lw["avg_latency_ms"]
            else:
                level_alpha = weights.beta_alpha
                level_beta = weights.beta_beta
                level_success_rate = weights.success_rate
                level_latency = weights.avg_latency_ms

            if level == 0 and weights.total_tasks == 0:
                thompson_sample = self._cold_start_prior
                ucb_bonus = self._ucb_c * math.sqrt(math.log(total_pulls + 1))
            else:
                thompson_sample = _beta_sample(level_alpha, level_beta)
                ucb_bonus = self._ucb_c * math.sqrt(math.log(total_pulls) / max(weights.total_tasks, 1))

            normalized_latency = min(level_latency / 10000.0, 1.0)
            raw_score = thompson_sample * (1 - normalized_latency * 0.3) + ucb_bonus * 0.1
            agent_scores.append((agent, raw_score, f"TS={thompson_sample:.3f}, UCB={ucb_bonus:.3f}, lat={level_latency:.0f}ms"))

        agent_scores.sort(key=lambda x: x[1], reverse=True)
        return agent_scores

    def get_optimal_agent(self, task_description: str, level: int) -> RoutingRecommendation:
        if not self._initialized:
            self._initialize_default_weights()

        if not self._weights:
            return RoutingRecommendation(recommended_agent="hephaestus", confidence=0.5, reason="No weights", weights=self._weights)

        agent_scores = self._score_agents_thompson(level)
        if not agent_scores:
            return RoutingRecommendation(recommended_agent="hephaestus", confidence=0.5, reason="No data", weights=self._weights)

        best_agent, best_score, best_reason = agent_scores[0]
        weights = self._weights.get(best_agent)

        if weights:
            bay_mean = weights.bayesian_mean()
            bayesian_std = math.sqrt(bay_mean * (1 - bay_mean) / max(weights.total_tasks, 1))
            bayesian_lower = max(0.0, bay_mean - bayesian_std)
            bayesian_upper = min(1.0, bay_mean + bayesian_std)
            data_confidence = min(weights.total_tasks / 50.0, 1.0)
            bayesian_confidence = 1.0 - (bayesian_upper - bayesian_lower)
            confidence = min(bayesian_confidence * 0.5 + data_confidence * 0.3 + best_score * 0.2, 0.95)
        else:
            bayesian_lower, bayesian_upper = 0.0, 1.0
            confidence = 0.5

        return RoutingRecommendation(
            recommended_agent=best_agent,
            confidence=confidence,
            reason=best_reason,
            weights=self._weights,
            exploration_bonus=self._ucb_c,
            bayesian_lower=bayesian_lower,
            bayesian_upper=bayesian_upper,
        )

    def get_routing_weights(self) -> Dict[str, Dict[str, Any]]:
        if not self._initialized:
            self._initialize_default_weights()

        result = {}
        for agent, weights in self._weights.items():
            result[agent] = {
                "success_rate": weights.success_rate,
                "bayesian_mean": weights.bayesian_mean(),
                "beta_params": f"Beta({weights.beta_alpha:.1f},{weights.beta_beta:.1f})",
                "avg_latency_ms": weights.avg_latency_ms,
                "total_tasks": weights.total_tasks,
                "success_count": weights.success_count,
                "failure_count": weights.failure_count,
                "current_alpha": weights.current_alpha,
                "by_level": weights.by_level,
            }
        return result

    def reset_weights(self) -> None:
        self._weights.clear()
        self._initialized = False
        self._total_updates = 0
        self._initialize_default_weights()


_routing_optimizer: Optional[RoutingWeightOptimizer] = None


def get_routing_optimizer(alpha: float = 0.1, cold_start_prior: float = 0.5, ucb_c: float = 2.0) -> RoutingWeightOptimizer:
    global _routing_optimizer
    if _routing_optimizer is None:
        _routing_optimizer = RoutingWeightOptimizer(alpha=alpha, cold_start_prior=cold_start_prior, ucb_c=ucb_c)
    return _routing_optimizer