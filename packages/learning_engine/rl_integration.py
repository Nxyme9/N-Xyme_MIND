"""RL Integration — Connect reward signals to training pipeline.

Features:
- Policy gradient (REINFORCE) for agent selection optimization
- Q-value updates from delegation outcomes
- Action space: agent selection (hephaestus, explore, oracle, etc.)
- State: task complexity, domain, history
- Episodic training: accumulate outcomes, compute gradients, update policy
- Integration with packages/training/ pipeline
"""

from __future__ import annotations

import math
import random
import sqlite3
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from .rl.q_learning import ActionType, QLearningEngine, QState
from .rl.policy import PolicyManager


class AgentType(Enum):
    """Available agents for action space."""

    HEPHAESTUS = "hephaestus"
    EXPLORE = "explore"
    ORACLE = "oracle"
    LIBRARIAN = "librarian"
    MULTIMODAL = "multimodal"
    METIS = "metis"
    MOMUS = "momus"
    ATLAS = "atlas"
    SISYPHUS_JUNIOR = "sisyphus-junior"


@dataclass
class TaskState:
    """State representation for RL agent selection."""

    task_description: str
    complexity: int  # L1-L5
    domain: str  # "implementation", "research", "review", "architecture"
    history: list[str] = field(default_factory=list)

    def to_key(self) -> str:
        history_hash = "_".join(self.history[-3:]) if self.history else "none"
        return f"{self.domain}|{self.complexity}|{hash(history_hash) % 1000}"

    @staticmethod
    def from_task(
        task: str, complexity: int = 3, domain: str = "general"
    ) -> "TaskState":
        return TaskState(
            task_description=task,
            complexity=min(max(complexity, 1), 5),
            domain=domain,
        )


@dataclass
class DelegationOutcome:
    """Records outcome of a delegation for RL training."""

    task_id: str
    agent: AgentType
    state: TaskState
    success: bool
    latency_ms: int
    tokens_used: int
    timestamp: float = field(default_factory=time.time)
    reward: float = 0.0


class PolicyGradientAgent:
    """REINFORCE policy gradient agent for agent selection."""

    def __init__(
        self,
        learning_rate: float = 0.01,
        gamma: float = 0.99,
        entropy_coef: float = 0.01,
    ):
        self.lr = learning_rate
        self.gamma = gamma
        self.entropy_coef = entropy_coef

        self._policy: dict[str, dict[AgentType, float]] = defaultdict(
            lambda: {agent: 1.0 / len(AgentType) for agent in AgentType}
        )
        self._returns: dict[str, list[float]] = defaultdict(list)
        self._log_probs: dict[str, list[tuple[AgentType, float]]] = defaultdict(list)

    def get_policy(self, state: TaskState) -> dict[AgentType, float]:
        key = state.to_key()
        return self._policy[key]

    def select_action(self, state: TaskState) -> AgentType:
        """Sample action from policy."""
        key = state.to_key()
        policy = self._policy[key]

        probs = list(policy.values())
        agents = list(policy.keys())

        if random.random() < 0.1:
            return random.choice(agents)

        return random.choices(agents, weights=probs, k=1)[0]

    def store_outcome(self, state: TaskState, action: AgentType, reward: float) -> None:
        """Store trajectory for gradient computation."""
        key = state.to_key()

        log_prob = math.log(max(self._policy[key][action], 1e-10))
        self._log_probs[key].append((action, log_prob))
        self._returns[key].append(reward)

    def compute_returns(self, key: str) -> list[float]:
        """Compute discounted returns for episode."""
        returns = []
        running = 0.0
        for r in reversed(self._returns[key]):
            running = r + self.gamma * running
            returns.insert(0, running)
        return returns

    def update_policy(self) -> dict[str, float]:
        """Update policy using REINFORCE gradient."""
        updates = {}
        entropy_sum = 0.0

        for key in self._log_probs:
            if not self._log_probs[key]:
                continue

            returns = self.compute_returns(key)
            baseline = sum(returns) / len(returns) if returns else 0.0

            advantages = [r - baseline for r in returns]

            for (action, log_prob), advantage in zip(self._log_probs[key], advantages):
                gradient = self.lr * advantage * log_prob
                self._policy[key][action] += gradient

            probs = list(self._policy[key].values())
            probs = [max(p, 0.01) for p in probs]
            total = sum(probs)
            for agent in self._policy[key]:
                self._policy[key][agent] = (
                    probs[agents.index(agent)] / total
                    if (agents := list(self._policy[key].keys())) and total > 0
                    else 1 / len(AgentType)
                )

            entropy = -sum(
                p * math.log(max(p, 1e-10)) for p in self._policy[key].values()
            )
            entropy_sum += entropy
            updates[key] = sum(abs(a) for a in advantages)

        self._returns.clear()
        self._log_probs.clear()

        return {
            "updates": len(updates),
            "avg_entropy": entropy_sum / max(len(updates), 1),
        }


@dataclass
class RLIntegration:
    """Main RL integration connecting rewards to training pipeline."""

    def __init__(
        self,
        db_path: str | None = None,
        training_pipeline_path: str | None = None,
    ):
        self._db_path = db_path or ".sisyphus/rl_integration.db"
        self._training_pipeline_path = training_pipeline_path
        self._setup_db()

        self._q_learning = QLearningEngine(db_path=self._db_path)
        self._policy_gradient = PolicyGradientAgent()
        self._policy_manager = PolicyManager(db_path=self._db_path)

        self._episodes: list[DelegationOutcome] = []
        self._current_episode: list[DelegationOutcome] = []

    def _setup_db(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY,
                task_id TEXT,
                agent TEXT,
                complexity INTEGER,
                domain TEXT,
                success INTEGER,
                latency_ms INTEGER,
                tokens_used INTEGER,
                reward REAL,
                timestamp REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rl_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()
        conn.close()

    def compute_reward(
        self,
        success: bool,
        latency_ms: int,
        tokens_used: int,
        complexity: int,
    ) -> float:
        """Compute reward from delegation outcome."""
        success_reward = 1.0 if success else -0.5

        latency_penalty = min(latency_ms / 10000.0, 0.5)

        tokens_reward = min(tokens_used / 10000.0, 0.3)

        complexity_bonus = complexity * 0.1

        return success_reward - latency_penalty + tokens_reward + complexity_bonus

    def record_delegation(
        self,
        task_id: str,
        agent: AgentType,
        state: TaskState,
        success: bool,
        latency_ms: int,
        tokens_used: int,
    ) -> float:
        """Record delegation outcome and compute reward."""
        reward = self.compute_reward(success, latency_ms, tokens_used, state.complexity)

        outcome = DelegationOutcome(
            task_id=task_id,
            agent=agent,
            state=state,
            success=success,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            reward=reward,
        )

        self._current_episode.append(outcome)

        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.execute(
            """
            INSERT INTO episodes (task_id, agent, complexity, domain, success, latency_ms, tokens_used, reward, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                task_id,
                agent.value,
                state.complexity,
                state.domain,
                1 if success else 0,
                latency_ms,
                tokens_used,
                reward,
                time.time(),
            ),
        )
        conn.commit()
        conn.close()

        self._q_learning.update(
            QState(task=state.task_description, context_hash=state.to_key()),
            ActionType[agent.name],
            reward,
        )

        self._policy_gradient.store_outcome(state, agent, reward)

        return reward

    def end_episode(self) -> dict[str, Any]:
        """End current episode, compute gradients, update policy."""
        if not self._current_episode:
            return {"status": "no_data"}

        self._episodes.extend(self._current_episode)
        self._current_episode = []

        pg_result = self._policy_gradient.update_policy()

        total_reward = sum(e.reward for e in self._episodes[-10:])
        success_rate = sum(1 for e in self._episodes[-10:] if e.success) / min(
            len(self._episodes[-10:]), 1
        )

        return {
            "status": "updated",
            "episode_length": len(self._episodes[-10:]),
            "avg_reward": total_reward / min(len(self._episodes[-10:]), 1),
            "success_rate": success_rate,
            "policy_updates": pg_result.get("updates", 0),
            "avg_entropy": pg_result.get("avg_entropy", 0.0),
        }

    def select_agent(
        self,
        state: TaskState,
        available_agents: list[AgentType] | None = None,
    ) -> AgentType:
        """Select optimal agent using learned policy."""
        if available_agents is None:
            available_agents = list(AgentType)

        state_key = state.to_key()

        q_values = self._q_learning.get_q_values(state_key)

        agent_scores: dict[AgentType, float] = {}
        for agent in available_agents:
            q_val = q_values.get(agent.value, 0.0)
            pg_prob = self._policy_gradient.get_policy(state).get(agent, 0.25)
            agent_scores[agent] = 0.5 * q_val + 0.5 * pg_prob

        if random.random() < 0.1:
            return random.choice(available_agents)

        return max(agent_scores, key=agent_scores.get)

    def trigger_training(
        self,
        min_episodes: int = 20,
        success_threshold: float = 0.7,
    ) -> dict[str, Any]:
        """Trigger training pipeline if conditions met."""
        recent = (
            self._episodes[-min_episodes:]
            if len(self._episodes) >= min_episodes
            else self._episodes
        )

        if not recent:
            return {"status": "insufficient_data", "episodes": len(self._episodes)}

        success_rate = sum(1 for e in recent if e.success) / len(recent)

        if success_rate >= success_threshold:
            return {"status": "training_not_needed", "success_rate": success_rate}

        if self._training_pipeline_path:
            return {
                "status": "pipeline_triggered",
                "success_rate": success_rate,
                "pipeline_path": self._training_pipeline_path,
            }

        return {
            "status": "policy_updated",
            "success_rate": success_rate,
            "episodes": len(self._episodes),
        }

    def save_policy(self, name: str, description: str = "") -> None:
        """Save current policy to database."""
        q_table = self._q_learning._q_table.values
        self._policy_manager.save_policy(name, description, q_table)

    def load_policy(self, name: str) -> bool:
        """Load policy from database."""
        policy = self._policy_manager.get_policy(name)
        if policy:
            self._q_learning._q_table.values = policy.q_table_data
            return True
        return False

    def get_stats(self) -> dict[str, Any]:
        """Get RL integration statistics."""
        recent = self._episodes[-100:] if len(self._episodes) >= 100 else self._episodes

        if not recent:
            return {"status": "no_data", "total_episodes": len(self._episodes)}

        return {
            "total_episodes": len(self._episodes),
            "recent_success_rate": sum(1 for e in recent if e.success) / len(recent),
            "recent_avg_reward": sum(e.reward for e in recent) / len(recent),
            "avg_latency_ms": sum(e.latency_ms for e in recent) / len(recent),
            "avg_tokens": sum(e.tokens_used for e in recent) / len(recent),
            "q_table_size": len(self._q_learning._q_table.values),
            "policy_states": len(self._policy_gradient._policy),
        }


def get_rl_integration(db_path: str | None = None) -> RLIntegration:
    """Get or create RL integration instance."""
    if db_path is None:
        db_path = ".sisyphus/rl_integration.db"
    return RLIntegration(db_path=db_path)


__all__ = [
    "AgentType",
    "TaskState",
    "DelegationOutcome",
    "PolicyGradientAgent",
    "RLIntegration",
    "get_rl_integration",
]
