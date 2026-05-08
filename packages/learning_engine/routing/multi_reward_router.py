"""Multi-Agent Reward Routing — Thompson Sampling for agent selection."""

from __future__ import annotations

import logging
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from packages.intelligence.delegation.logger import DelegationOutcomeLogger
from packages.learning_engine.rl.bandits import MultiArmedBandit

logger = logging.getLogger(__name__)


class RewardSignal(Enum):
    """Reward signal types tracked per agent."""

    SUCCESS_RATE = "success_rate"
    LATENCY = "latency"
    TOKEN_EFFICIENCY = "token_efficiency"
    COMPOSITE = "composite"


@dataclass
class AgentRewards:
    """Accumulated rewards for a single agent."""

    agent: str
    pulls: int = 0
    success_count: int = 0
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    last_updated: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        return self.success_count / self.pulls if self.pulls > 0 else 0.5

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.pulls if self.pulls > 0 else 0.0

    @property
    def avg_tokens(self) -> float:
        return self.total_tokens / self.pulls if self.pulls > 0 else 0.0

    def compute_composite_reward(
        self,
        latency_weight: float = 0.2,
        token_weight: float = 0.1,
        success_weight: float = 0.7,
        reference_latency: float = 5000.0,
        reference_tokens: int = 15000,
    ) -> float:
        """Compute composite reward combining multiple signals."""
        success_component = self.success_rate * success_weight

        latency_component = 1.0
        if self.avg_latency_ms > 0:
            latency_component = min(1.0, reference_latency / self.avg_latency_ms)
        latency_component *= latency_weight

        token_component = 1.0
        if self.avg_tokens > 0:
            token_component = min(1.0, reference_tokens / self.avg_tokens)
        token_component *= token_weight

        return success_component + latency_component + token_component


@dataclass
class RoutingDecision:
    """Result of a routing decision."""

    task_id: str
    task_description: str
    selected_agent: str
    confidence: float
    strategy: str
    all_scores: dict[str, float]
    timestamp: datetime = field(default_factory=datetime.now)


class MultiRewardRouter:
    """Multi-agent routing using Thompson Sampling with multiple reward signals.

    Features:
    - Thompson Sampling for exploration/exploitation balance
    - Per-agent reward tracking: success rate, latency, token efficiency
    - Composite reward computation for agent selection
    - Outcome logging for continuous learning
    """

    def __init__(
        self,
        outcome_logger: Optional[DelegationOutcomeLogger] = None,
        strategy: str = "thompson",
        exploration_weight: float = 1.0,
        min_pulls_for_selection: int = 3,
    ):
        self._bandit = MultiArmedBandit(strategy=strategy)
        self._agents: dict[str, AgentRewards] = {}
        self._outcome_logger = outcome_logger or DelegationOutcomeLogger()
        self._exploration_weight = exploration_weight
        self._min_pulls = min_pulls_for_selection
        self._default_agents = [
            "hephaestus",
            "explore",
            "oracle",
            "librarian",
            "atlas",
            "sisyphus-junior",
            "multimodal-looker",
        ]

        for agent in self._default_agents:
            self._agents[agent] = AgentRewards(agent=agent)

    def route(
        self,
        task_description: str,
        level: int = 3,
        context: Optional[dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> RoutingDecision:
        """Route a task to the best-performing agent based on accumulated rewards."""
        if task_id is None:
            task_id = str(uuid.uuid4())[:8]

        all_scores = {}
        for agent, rewards in self._agents.items():
            score = rewards.compute_composite_reward()
            all_scores[agent] = score
            self._bandit.update(agent, score)

        selected_agent = self._select_with_thompson()

        confidence = self._compute_confidence(selected_agent)

        logger.info(
            f"[{task_id}] Routed to {selected_agent} (confidence: {confidence:.2f}) for: {task_description[:50]}..."
        )

        return RoutingDecision(
            task_id=task_id,
            task_description=task_description,
            selected_agent=selected_agent,
            confidence=confidence,
            strategy=self._bandit.strategy,
            all_scores=all_scores,
        )

    def _select_with_thompson(self) -> str:
        """Select agent using Thompson Sampling."""
        samples = {}
        for agent, rewards in self._agents.items():
            if rewards.pulls < self._min_pulls:
                return agent

            mean = rewards.compute_composite_reward()
            std = max(0.1, 1.0 / (rewards.pulls**0.5))
            sample = random.gauss(mean, std * self._exploration_weight)
            samples[agent] = sample

        if not samples:
            return random.choice(self._default_agents)

        return max(samples.keys(), key=lambda a: samples[a])

    def _compute_confidence(self, agent: str) -> float:
        """Compute confidence in the selection based on pull count."""
        rewards = self._agents.get(agent)
        if not rewards or rewards.pulls == 0:
            return 0.1
        if rewards.pulls < self._min_pulls:
            return 0.3
        return min(0.95, 0.5 + (rewards.pulls / 100.0))

    async def record_outcome(
        self,
        task_id: str,
        task_description: str,
        agent: str,
        success: bool,
        latency_ms: float = 0,
        tokens_used: int = 0,
        level: int = 3,
    ) -> None:
        """Record outcome and update agent rewards."""
        rewards = self._agents.get(agent)
        if rewards:
            rewards.pulls += 1
            if success:
                rewards.success_count += 1
            rewards.total_latency_ms += latency_ms
            rewards.total_tokens += tokens_used
            rewards.last_updated = datetime.now()

        reward = 1.0 if success else 0.0
        self._bandit.update(agent, reward)

        await self._outcome_logger.log_outcome(
            task_id=task_id,
            task_description=task_description,
            level=level,
            agent=agent,
            success=success,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
        )

        logger.debug(
            f"Recorded outcome: {agent} → {'success' if success else 'failed'} "
            f"(latency: {latency_ms:.0f}ms, tokens: {tokens_used})"
        )

    def get_agent_stats(self, agent: Optional[str] = None) -> dict[str, Any]:
        """Get statistics for one or all agents."""
        if agent:
            rewards = self._agents.get(agent)
            if not rewards:
                return {"agent": agent, "message": "No data"}
            return {
                "agent": agent,
                "pulls": rewards.pulls,
                "success_count": rewards.success_count,
                "success_rate": rewards.success_rate,
                "avg_latency_ms": rewards.avg_latency_ms,
                "avg_tokens": rewards.avg_tokens,
                "composite_reward": rewards.compute_composite_reward(),
                "last_updated": rewards.last_updated.isoformat()
                if rewards.last_updated
                else None,
            }

        return {
            agent: {
                "pulls": r.pulls,
                "success_rate": r.success_rate,
                "avg_latency_ms": r.avg_latency_ms,
                "composite_reward": r.compute_composite_reward(),
            }
            for agent, r in self._agents.items()
        }

    def get_bandit_stats(self) -> dict[str, dict[str, float]]:
        """Get bandit arm statistics."""
        return self._bandit.get_statistics()

    def get_learning_progress(self) -> dict[str, Any]:
        """Get overall learning progress metrics."""
        total_pulls = sum(r.pulls for r in self._agents.values())
        total_successes = sum(r.success_count for r in self._agents.values())

        return {
            "total_outcomes": total_pulls,
            "total_successes": total_successes,
            "overall_success_rate": total_successes / total_pulls
            if total_pulls > 0
            else 0.0,
            "exploration_strategy": self._bandit.strategy,
            "agents_tracked": len([r for r in self._agents.values() if r.pulls > 0]),
            "bandit_stats": self.get_bandit_stats(),
        }


_router: Optional[MultiRewardRouter] = None


def get_multi_reward_router() -> MultiRewardRouter:
    """Get or create the global multi-reward router."""
    global _router
    if _router is None:
        _router = MultiRewardRouter()
    return _router


__all__ = [
    "MultiRewardRouter",
    "RoutingDecision",
    "AgentRewards",
    "RewardSignal",
    "get_multi_reward_router",
]
