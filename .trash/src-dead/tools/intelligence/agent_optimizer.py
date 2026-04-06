"""Agent selection optimization — track performance, auto-select best agent, detect decay."""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from src.state.db import StateDB
    from src.state.models import AgentPerformance
    HAS_STATE_DB = True
except ImportError:
    HAS_STATE_DB = False
    StateDB = None

logger = logging.getLogger(__name__)

DEFAULT_AGENTS = [
    "hephaestus", "explore", "oracle", "sisyphus", "prometheus",
    "metis", "momus", "librarian", "atlas", "sisyphus-junior",
]

DEFAULT_TASK_TYPES = [
    "implementation", "research", "review", "planning", "trivial_fix",
    "bug_fix", "refactoring", "testing", "documentation", "architecture",
]

PERFORMANCE_DECAY_THRESHOLD = 0.15
PERFORMANCE_MIN_SAMPLES = 3
PERFORMANCE_WEIGHT = 0.7
RECENCY_WEIGHT = 0.3
DECAY_WINDOW_HOURS = 168


@dataclass
class AgentScore:
    """Score for an agent on a specific task type."""

    agent_name: str
    task_type: str
    score: float
    success_rate: float
    total_tasks: int
    success_count: int
    failure_count: int
    last_updated: str
    decay_detected: bool
    decay_amount: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "task_type": self.task_type,
            "score": round(self.score, 3),
            "success_rate": round(self.success_rate, 3),
            "total_tasks": self.total_tasks,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_updated": self.last_updated,
            "decay_detected": self.decay_detected,
            "decay_amount": round(self.decay_amount, 3),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class SelectionResult:
    """Result of agent selection for a task."""

    selected_agent: str
    confidence: float
    alternatives: list[dict[str, Any]]
    reason: str
    scores: list[AgentScore]

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_agent": self.selected_agent,
            "confidence": round(self.confidence, 3),
            "alternatives": self.alternatives,
            "reason": self.reason,
            "scores": [s.to_dict() for s in self.scores],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class AgentOptimizer:
    """Tracks agent performance per task type and auto-selects the best agent."""

    def __init__(self, db: StateDB | None = None, root_dir: Path | None = None):
        if db is not None:
            self._db = db
        elif HAS_STATE_DB:
            db_path = (root_dir or Path(__file__).parent.parent.parent) / ".sisyphus" / "state.db"
            self._db = StateDB(db_path)
        else:
            self._db = None

        self._lock = threading.Lock()
        self._performance_cache: dict[str, dict[str, dict[str, Any]]] = {}
        self._decay_history: dict[str, list[dict[str, Any]]] = {}
        self._last_load_time: float = 0
        self._cache_ttl = 60

    def select_agent(self, task_type: str, exclude: list[str] | None = None) -> SelectionResult:
        """Select the best agent for a given task type."""
        exclude = exclude or []
        scores = self._compute_scores(task_type, exclude)

        if not scores:
            return SelectionResult(
                selected_agent="hephaestus" if task_type == "implementation" else "explore",
                confidence=0.5,
                alternatives=[],
                reason="no historical data, using default",
                scores=[],
            )

        best = max(scores, key=lambda s: s.score)
        alternatives = [
            {"agent": s.agent_name, "score": round(s.score, 3), "success_rate": round(s.success_rate, 3)}
            for s in sorted(scores, key=lambda s: s.score, reverse=True)[1:5]
        ]

        confidence = best.score if best.total_tasks >= PERFORMANCE_MIN_SAMPLES else 0.5
        reason = (
            f"Best performer for '{task_type}' with {best.success_rate:.0%} success rate"
            f" over {best.total_tasks} tasks"
        )
        if best.decay_detected:
            reason += f" (WARNING: decay detected, -{best.decay_amount:.0%})"

        return SelectionResult(
            selected_agent=best.agent_name,
            confidence=confidence,
            alternatives=alternatives,
            reason=reason,
            scores=scores,
        )

    def record_result(self, agent_name: str, task_type: str, success: bool) -> None:
        """Record a task result for an agent."""
        if self._db is None:
            return

        with self._lock:
            try:
                perf_data = self._db.get_all_agent_performance()
                agent_data = perf_data.get(agent_name, {})
                task_data = agent_data.get(task_type, {"success": 0, "failure": 0})

                if success:
                    task_data["success"] = task_data.get("success", 0) + 1
                else:
                    task_data["failure"] = task_data.get("failure", 0) + 1
                    task_data["last_failure_reason"] = "task failed"

                perf = AgentPerformance(
                    agent_name=agent_name,
                    task_type=task_type,
                    success=task_data["success"],
                    failure=task_data["failure"],
                    last_failure_reason=task_data.get("last_failure_reason", ""),
                    last_updated=datetime.now(timezone.utc).isoformat(),
                )
                self._db.upsert_agent_performance(perf)
                self._invalidate_cache()
            except Exception as e:
                logger.error(f"Failed to record agent result: {e}")

    def get_performance(self, agent_name: str) -> dict[str, dict[str, Any]]:
        """Get all performance data for an agent."""
        if self._db is None:
            return {}

        self._load_cache_if_needed()
        return self._performance_cache.get(agent_name, {})

    def get_all_performance(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Get performance data for all agents."""
        if self._db is None:
            return {}

        self._load_cache_if_needed()
        return dict(self._performance_cache)

    def detect_decay(self, agent_name: str, task_type: str | None = None) -> list[dict[str, Any]]:
        """Detect performance decay for an agent."""
        if self._db is None:
            return []

        perf_data = self._db.get_all_agent_performance()
        agent_data = perf_data.get(agent_name, {})
        decays: list[dict[str, Any]] = []

        task_types_to_check = (
            [task_type] if task_type else list(agent_data.keys())
        )

        for tt in task_types_to_check:
            task_data = agent_data.get(tt, {})
            total = task_data.get("success", 0) + task_data.get("failure", 0)
            if total < PERFORMANCE_MIN_SAMPLES:
                continue

            success_rate = task_data.get("success", 0) / total
            if success_rate < 0.5:
                decay_amount = 0.5 - success_rate
                decay_info = {
                    "agent": agent_name,
                    "task_type": tt,
                    "current_rate": round(success_rate, 3),
                    "threshold": 0.5,
                    "decay_amount": round(decay_amount, 3),
                    "total_tasks": total,
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                }
                decays.append(decay_info)

                if agent_name not in self._decay_history:
                    self._decay_history[agent_name] = []
                self._decay_history[agent_name].append(decay_info)

        return decays

    def get_rankings(self, task_type: str) -> list[dict[str, Any]]:
        """Get agent rankings for a specific task type."""
        scores = self._compute_scores(task_type)
        return [
            {
                "rank": i + 1,
                "agent": s.agent_name,
                "score": round(s.score, 3),
                "success_rate": round(s.success_rate, 3),
                "total_tasks": s.total_tasks,
                "decay_detected": s.decay_detected,
            }
            for i, s in enumerate(sorted(scores, key=lambda s: s.score, reverse=True))
        ]

    def get_recommendations(self) -> list[str]:
        """Get optimization recommendations based on current performance data."""
        recommendations: list[str] = []
        all_perf = self.get_all_performance()

        for agent_name, task_types in all_perf.items():
            for task_type, data in task_types.items():
                total = data.get("success", 0) + data.get("failure", 0)
                if total < PERFORMANCE_MIN_SAMPLES:
                    continue

                success_rate = data.get("success", 0) / total
                if success_rate < 0.5:
                    recommendations.append(
                        f"Agent '{agent_name}' has low success rate ({success_rate:.0%}) "
                        f"for '{task_type}' tasks ({total} attempts). Consider retraining or reassignment."
                    )

            decays = self.detect_decay(agent_name)
            for decay in decays:
                recommendations.append(
                    f"Performance decay detected for '{agent_name}' on "
                    f"'{decay['task_type']}': {decay['decay_amount']:.0%} below threshold"
                )

        if not recommendations:
            recommendations.append("All agents performing within acceptable parameters.")

        return recommendations

    def _compute_scores(
        self, task_type: str, exclude: list[str] | None = None
    ) -> list[AgentScore]:
        """Compute weighted scores for all agents on a task type."""
        exclude = exclude or []
        perf_data = self.get_all_performance()
        scores: list[AgentScore] = []
        now = time.time()

        for agent_name, task_types in perf_data.items():
            if agent_name in exclude:
                continue

            task_data = task_types.get(task_type)
            if task_data is None:
                continue

            success = task_data.get("success", 0)
            failure = task_data.get("failure", 0)
            total = success + failure

            if total == 0:
                continue

            success_rate = success / total
            last_updated_str = task_data.get("last_updated", "")
            recency_score = self._compute_recency_score(last_updated_str, now)
            weighted_score = (success_rate * PERFORMANCE_WEIGHT) + (recency_score * RECENCY_WEIGHT)

            decay_detected = False
            decay_amount = 0.0
            if success_rate < 0.5 and total >= PERFORMANCE_MIN_SAMPLES:
                decay_detected = True
                decay_amount = 0.5 - success_rate

            scores.append(AgentScore(
                agent_name=agent_name,
                task_type=task_type,
                score=weighted_score,
                success_rate=success_rate,
                total_tasks=total,
                success_count=success,
                failure_count=failure,
                last_updated=last_updated_str,
                decay_detected=decay_detected,
                decay_amount=decay_amount,
            ))

        return scores

    def _compute_recency_score(self, last_updated_str: str, now: float) -> float:
        """Compute recency score (1.0 = very recent, 0.0 = stale)."""
        if not last_updated_str:
            return 0.5

        try:
            last_updated = datetime.fromisoformat(last_updated_str.replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - last_updated).total_seconds() / 3600
            if age_hours <= 1:
                return 1.0
            elif age_hours >= DECAY_WINDOW_HOURS:
                return 0.0
            else:
                return 1.0 - (age_hours / DECAY_WINDOW_HOURS)
        except (ValueError, TypeError):
            return 0.5

    def _load_cache_if_needed(self) -> None:
        """Reload cache if TTL expired."""
        if time.time() - self._last_load_time < self._cache_ttl:
            return

        try:
            self._performance_cache = self._db.get_all_agent_performance()
            self._last_load_time = time.time()
        except Exception as e:
            logger.error(f"Failed to load performance cache: {e}")

    def _invalidate_cache(self) -> None:
        """Invalidate the performance cache."""
        self._last_load_time = 0

    def reset(self) -> None:
        """Reset all optimizer state."""
        with self._lock:
            self._performance_cache.clear()
            self._decay_history.clear()
            self._last_load_time = 0


def optimize_agent_selection(
    task_type: str, db: StateDB | None = None, exclude: list[str] | None = None
) -> SelectionResult:
    """Convenience function to select the best agent for a task type."""
    optimizer = AgentOptimizer(db=db)
    return optimizer.select_agent(task_type, exclude)


def create_optimizer(db: StateDB | None = None) -> AgentOptimizer:
    """Create a new agent optimizer."""
    return AgentOptimizer(db=db)
