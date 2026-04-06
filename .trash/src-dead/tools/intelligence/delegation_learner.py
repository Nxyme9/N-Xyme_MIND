"""Delegation Learning Enhancement — Advanced routing optimization.

Implements:
- Track which agents perform best on which task types
- Auto-adjust routing weights based on outcomes
- A/B testing for routing strategies
- Performance-based agent recommendations
"""

from __future__ import annotations

import json
import logging
import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentPerformance:
    """Performance metrics for an agent on a task type."""

    agent_name: str
    task_type: str
    total_tasks: int = 0
    successful_tasks: int = 0
    avg_latency_ms: float = 0.0
    avg_quality_score: float = 0.0
    last_used: str = ""
    streak_success: int = 0
    streak_failure: int = 0

    @property
    def success_rate(self) -> float:
        return self.successful_tasks / max(1, self.total_tasks)

    @property
    def composite_score(self) -> float:
        """Combined score: 50% success rate, 30% quality, 20% speed."""
        speed_score = min(1.0, 5000 / max(1, self.avg_latency_ms))
        return (
            self.success_rate * 0.5 + self.avg_quality_score * 0.3 + speed_score * 0.2
        )


@dataclass
class ABTest:
    """A/B test for routing strategies."""

    id: str
    name: str
    strategy_a: str
    strategy_b: str
    tasks_a: int = 0
    tasks_b: int = 0
    success_a: int = 0
    success_b: int = 0
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    is_active: bool = True


class DelegationLearner:
    """Advanced delegation learning with A/B testing."""

    def __init__(self, storage_path: Path | None = None):
        """Initialize delegation learner.

        Args:
            storage_path: Path to store learning data.
        """
        self.storage_path = storage_path or Path(".sisyphus/delegation_learning")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.performances: dict[str, AgentPerformance] = {}
        self.ab_tests: list[ABTest] = []
        self._load_data()

    def record_outcome(
        self,
        agent_name: str,
        task_type: str,
        success: bool,
        latency_ms: float,
        quality_score: float = 0.5,
    ) -> None:
        """Record a delegation outcome.

        Args:
            agent_name: Agent that handled the task.
            task_type: Type of task.
            success: Whether the task was successful.
            latency_ms: Task latency.
            quality_score: Quality score (0-1).
        """
        key = f"{agent_name}:{task_type}"
        if key not in self.performances:
            self.performances[key] = AgentPerformance(
                agent_name=agent_name,
                task_type=task_type,
            )

        perf = self.performances[key]
        perf.total_tasks += 1
        if success:
            perf.successful_tasks += 1
            perf.streak_success += 1
            perf.streak_failure = 0
        else:
            perf.streak_failure += 1
            perf.streak_success = 0

        # Exponential moving average
        alpha = 0.3
        perf.avg_latency_ms = alpha * latency_ms + (1 - alpha) * perf.avg_latency_ms
        perf.avg_quality_score = (
            alpha * quality_score + (1 - alpha) * perf.avg_quality_score
        )
        perf.last_used = datetime.now(timezone.utc).isoformat()

        self._save_data()

    def recommend_agent(
        self,
        task_type: str,
        available_agents: list[str],
        use_ab_test: bool = True,
    ) -> str:
        """Recommend the best agent for a task type.

        Args:
            task_type: Type of task.
            available_agents: List of available agents.
            use_ab_test: Whether to use A/B testing.

        Returns:
            Recommended agent name.
        """
        # Check active A/B tests
        if use_ab_test:
            active_test = next(
                (
                    t
                    for t in self.ab_tests
                    if t.is_active and task_type in t.name.lower()
                ),
                None,
            )
            if active_test:
                # Randomly assign to strategy
                if random.random() < 0.5:
                    active_test.tasks_a += 1
                    return active_test.strategy_a
                else:
                    active_test.tasks_b += 1
                    return active_test.strategy_b

        # Find best performing agent
        best_agent = None
        best_score = -1.0

        for agent_name in available_agents:
            key = f"{agent_name}:{task_type}"
            perf = self.performances.get(key)
            if perf:
                score = perf.composite_score
            else:
                score = 0.5  # Default for unknown agents

            if score > best_score:
                best_score = score
                best_agent = agent_name

        return best_agent or (available_agents[0] if available_agents else "sisyphus")

    def start_ab_test(
        self,
        name: str,
        strategy_a: str,
        strategy_b: str,
    ) -> ABTest:
        """Start an A/B test for routing strategies.

        Args:
            name: Test name.
            strategy_a: Strategy A (agent name).
            strategy_b: Strategy B (agent name).

        Returns:
            Created ABTest.
        """
        import uuid

        test = ABTest(
            id=str(uuid.uuid4())[:8],
            name=name,
            strategy_a=strategy_a,
            strategy_b=strategy_b,
        )
        self.ab_tests.append(test)
        return test

    def get_ab_test_results(self, test_id: str) -> dict[str, Any] | None:
        """Get results of an A/B test.

        Args:
            test_id: Test ID.

        Returns:
            Test results or None.
        """
        test = next((t for t in self.ab_tests if t.id == test_id), None)
        if not test:
            return None

        return {
            "name": test.name,
            "strategy_a": {
                "name": test.strategy_a,
                "tasks": test.tasks_a,
                "success_rate": test.success_a / max(1, test.tasks_a),
            },
            "strategy_b": {
                "name": test.strategy_b,
                "tasks": test.tasks_b,
                "success_rate": test.success_b / max(1, test.tasks_b),
            },
            "is_active": test.is_active,
        }

    def get_agent_rankings(self, task_type: str) -> list[dict[str, Any]]:
        """Get agent rankings for a task type.

        Args:
            task_type: Task type.

        Returns:
            List of agent rankings.
        """
        rankings = []
        for key, perf in self.performances.items():
            if perf.task_type == task_type:
                rankings.append(
                    {
                        "agent": perf.agent_name,
                        "success_rate": round(perf.success_rate, 4),
                        "avg_latency_ms": round(perf.avg_latency_ms, 2),
                        "avg_quality": round(perf.avg_quality_score, 4),
                        "composite_score": round(perf.composite_score, 4),
                        "total_tasks": perf.total_tasks,
                        "streak_success": perf.streak_success,
                    }
                )

        rankings.sort(key=lambda x: x["composite_score"], reverse=True)
        return rankings

    def _save_data(self) -> None:
        """Save learning data."""
        data = {
            "performances": {
                key: {
                    "agent_name": p.agent_name,
                    "task_type": p.task_type,
                    "total_tasks": p.total_tasks,
                    "successful_tasks": p.successful_tasks,
                    "avg_latency_ms": p.avg_latency_ms,
                    "avg_quality_score": p.avg_quality_score,
                    "last_used": p.last_used,
                    "streak_success": p.streak_success,
                    "streak_failure": p.streak_failure,
                }
                for key, p in self.performances.items()
            },
            "ab_tests": [
                {
                    "id": t.id,
                    "name": t.name,
                    "strategy_a": t.strategy_a,
                    "strategy_b": t.strategy_b,
                    "tasks_a": t.tasks_a,
                    "tasks_b": t.tasks_b,
                    "success_a": t.success_a,
                    "success_b": t.success_b,
                    "started_at": t.started_at,
                    "is_active": t.is_active,
                }
                for t in self.ab_tests
            ],
        }
        (self.storage_path / "learning_data.json").write_text(
            json.dumps(data, indent=2)
        )

    def _load_data(self) -> None:
        """Load learning data."""
        data_file = self.storage_path / "learning_data.json"
        if not data_file.exists():
            return

        try:
            data = json.loads(data_file.read_text())
            for key, d in data.get("performances", {}).items():
                self.performances[key] = AgentPerformance(
                    agent_name=d["agent_name"],
                    task_type=d["task_type"],
                    total_tasks=d["total_tasks"],
                    successful_tasks=d["successful_tasks"],
                    avg_latency_ms=d["avg_latency_ms"],
                    avg_quality_score=d["avg_quality_score"],
                    last_used=d.get("last_used", ""),
                    streak_success=d.get("streak_success", 0),
                    streak_failure=d.get("streak_failure", 0),
                )
            for d in data.get("ab_tests", []):
                self.ab_tests.append(ABTest(**d))
        except Exception as e:
            logger.warning(f"Failed to load delegation learning data: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get delegation learning statistics."""
        return {
            "total_performances_tracked": len(self.performances),
            "active_ab_tests": sum(1 for t in self.ab_tests if t.is_active),
            "total_ab_tests": len(self.ab_tests),
        }


# Global singleton
_delegation_learner = DelegationLearner()


def record_outcome(
    agent_name: str,
    task_type: str,
    success: bool,
    latency_ms: float,
    quality_score: float = 0.5,
) -> None:
    """Convenience function to record outcome."""
    _delegation_learner.record_outcome(
        agent_name, task_type, success, latency_ms, quality_score
    )


def recommend_agent(
    task_type: str,
    available_agents: list[str],
    use_ab_test: bool = True,
) -> str:
    """Convenience function to recommend agent."""
    return _delegation_learner.recommend_agent(task_type, available_agents, use_ab_test)
