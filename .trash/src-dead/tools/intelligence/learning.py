"""Learning from past delegations — analyze outcomes, identify patterns, recommend routing improvements."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from src.state.db import StateDB
    from src.state.models import Delegation, Result
    HAS_STATE_DB = True
except ImportError:
    HAS_STATE_DB = False
    StateDB = None  # type: ignore[misc]

logger = logging.getLogger(__name__)


@dataclass
class PatternInsight:
    """A discovered pattern from historical delegation data."""

    pattern_type: str
    description: str
    confidence: float
    recommendation: str
    evidence_count: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_type": self.pattern_type,
            "description": self.description,
            "confidence": self.confidence,
            "recommendation": self.recommendation,
            "evidence_count": self.evidence_count,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class LearningReport:
    """Comprehensive learning report from delegation analysis."""

    total_delegations: int
    success_rate: float
    agent_performance: dict[str, dict[str, Any]]
    level_accuracy: dict[str, dict[str, Any]]
    patterns: list[PatternInsight]
    recommendations: list[str]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_delegations": self.total_delegations,
            "success_rate": self.success_rate,
            "agent_performance": self.agent_performance,
            "level_accuracy": self.level_accuracy,
            "patterns": [p.to_dict() for p in self.patterns],
            "recommendations": self.recommendations,
            "generated_at": self.generated_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class DelegationLearner:
    """Analyzes historical delegation outcomes to improve future routing."""

    def __init__(self, db: StateDB | None = None, root_dir: Path | None = None):
        if db is not None:
            self._db = db
        elif HAS_STATE_DB:
            db_path = (root_dir or Path(__file__).parent.parent.parent) / ".sisyphus" / "state.db"
            self._db = StateDB(db_path)
        else:
            self._db = None
        self._lock = threading.Lock()
        self._cache: dict[str, Any] = {}
        self._cache_time: float = 0
        self._cache_ttl = 300

    def analyze_delegations(self, limit: int = 1000) -> dict[str, Any]:
        """Analyze historical delegation outcomes."""
        if self._db is None:
            return {"error": "no database available", "delegations": []}

        delegations = self._db.get_delegations(limit=limit)
        if not delegations:
            return {"error": "no delegations found", "delegations": []}

        total = len(delegations)
        success_count = sum(1 for d in delegations if d.status == "success")
        failure_count = total - success_count
        success_rate = (success_count / total * 100) if total > 0 else 0

        agent_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"success": 0, "failure": 0, "total": 0})
        level_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"success": 0, "failure": 0, "total": 0})

        for d in delegations:
            is_success = d.status == "success"
            agent_stats[d.agent]["total"] += 1
            agent_stats[d.agent]["success" if is_success else "failure"] += 1
            level_stats[d.level]["total"] += 1
            level_stats[d.level]["success" if is_success else "failure"] += 1

        agent_performance = {}
        for agent, stats in agent_stats.items():
            agent_success = stats["success"]
            agent_total = stats["total"]
            agent_performance[agent] = {
                "success_rate": (agent_success / agent_total * 100) if agent_total > 0 else 0,
                "total": agent_total,
                "success": agent_success,
                "failure": stats["failure"],
            }

        level_performance = {}
        for level, stats in level_stats.items():
            level_success = stats["success"]
            level_total = stats["total"]
            level_performance[level] = {
                "success_rate": (level_success / level_total * 100) if level_total > 0 else 0,
                "total": level_total,
                "success": level_success,
                "failure": stats["failure"],
            }

        return {
            "total_delegations": total,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": round(success_rate, 2),
            "agent_performance": agent_performance,
            "level_performance": level_performance,
        }

    def identify_patterns(self, limit: int = 1000) -> list[PatternInsight]:
        """Identify success/failure patterns from historical data."""
        if self._db is None:
            return []

        analysis = self.analyze_delegations(limit)
        if "error" in analysis:
            return []

        patterns: list[PatternInsight] = []

        agent_perf = analysis.get("agent_performance", {})
        for agent, stats in agent_perf.items():
            if stats["total"] >= 5:
                if stats["success_rate"] >= 90:
                    patterns.append(PatternInsight(
                        pattern_type="agent_success",
                        description=f"Agent '{agent}' has {stats['success_rate']}% success rate",
                        confidence=0.85,
                        recommendation=f"Prioritize '{agent}' for similar tasks",
                        evidence_count=stats["total"],
                        metadata={"agent": agent, "success_rate": stats["success_rate"]},
                    ))
                elif stats["success_rate"] <= 50:
                    patterns.append(PatternInsight(
                        pattern_type="agent_struggle",
                        description=f"Agent '{agent}' has low success rate: {stats['success_rate']}%",
                        confidence=0.80,
                        recommendation=f"Review task assignment for '{agent}' or consider alternative agents",
                        evidence_count=stats["total"],
                        metadata={"agent": agent, "success_rate": stats["success_rate"]},
                    ))

        level_perf = analysis.get("level_performance", {})
        for level, stats in level_perf.items():
            if stats["total"] >= 3:
                if stats["success_rate"] <= 60:
                    patterns.append(PatternInsight(
                        pattern_type="level_struggle",
                        description=f"Level {level} tasks have low success rate: {stats['success_rate']}%",
                        confidence=0.75,
                        recommendation=f"Review complexity scoring for level {level} tasks",
                        evidence_count=stats["total"],
                        metadata={"level": level, "success_rate": stats["success_rate"]},
                    ))

        if len(patterns) == 0:
            patterns.append(PatternInsight(
                pattern_type="insufficient_data",
                description="Not enough data to identify patterns",
                confidence=0.0,
                recommendation="Collect more delegation data before pattern analysis",
                evidence_count=analysis.get("total_delegations", 0),
            ))

        return patterns

    def recommend_routing(self, task_type: str | None = None, limit: int = 1000) -> dict[str, Any]:
        """Recommend optimal routing based on historical patterns."""
        if self._db is None:
            return {"error": "no database available", "recommendations": []}

        analysis = self.analyze_delegations(limit)
        if "error" in analysis:
            return analysis

        recommendations: list[str] = []
        agent_perf = analysis.get("agent_performance", {})

        best_agent = None
        best_rate = 0
        for agent, stats in agent_perf.items():
            if stats["total"] >= 3 and stats["success_rate"] > best_rate:
                best_rate = stats["success_rate"]
                best_agent = agent

        if best_agent:
            recommendations.append(f"Best performing agent: '{best_agent}' ({best_rate}% success rate)")

        level_perf = analysis.get("level_performance", {})
        for level, stats in sorted(level_perf.items()):
            if stats["total"] >= 3 and stats["success_rate"] < 70:
                recommendations.append(f"Level {level} needs review ({stats['success_rate']}% success rate)")

        overall_rate = analysis.get("success_rate", 0)
        if overall_rate < 80:
            recommendations.append(f"Overall success rate is low ({overall_rate}%). Review delegation strategy.")
        elif overall_rate >= 95:
            recommendations.append(f"Excellent overall success rate ({overall_rate}%). Current strategy is effective.")

        return {
            "recommendations": recommendations,
            "best_agent": best_agent,
            "best_agent_rate": best_rate,
            "overall_success_rate": overall_rate,
            "total_delegations": analysis.get("total_delegations", 0),
        }

    def get_agent_success_patterns(self) -> dict[str, float]:
        """Get success rates per agent for quick lookup."""
        if self._db is None:
            return {}

        analysis = self.analyze_delegations()
        agent_perf = analysis.get("agent_performance", {})
        return {
            agent: stats["success_rate"]
            for agent, stats in agent_perf.items()
        }

    def get_level_accuracy(self) -> dict[str, dict[str, Any]]:
        """Get accuracy metrics per complexity level."""
        if self._db is None:
            return {}

        analysis = self.analyze_delegations()
        return analysis.get("level_performance", {})

    def generate_report(self, limit: int = 1000) -> LearningReport:
        """Generate a comprehensive learning report."""
        analysis = self.analyze_delegations(limit)
        patterns = self.identify_patterns(limit)
        routing = self.recommend_routing(limit=limit)

        recommendations = routing.get("recommendations", [])
        for pattern in patterns:
            if pattern.recommendation not in recommendations:
                recommendations.append(pattern.recommendation)

        return LearningReport(
            total_delegations=analysis.get("total_delegations", 0),
            success_rate=analysis.get("success_rate", 0),
            agent_performance=analysis.get("agent_performance", {}),
            level_accuracy=analysis.get("level_performance", {}),
            patterns=patterns,
            recommendations=recommendations,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def record_feedback(self, task_id: str, expected_agent: str, actual_agent: str, success: bool) -> None:
        """Record feedback for a delegation to improve future routing."""
        if self._db is None:
            return

        with self._lock:
            try:
                perf_data = self._db.get_all_agent_performance()
                agent_data = perf_data.get(actual_agent, {})
                task_type_data = agent_data.get(task_id, {"success": 0, "failure": 0})

                if success:
                    task_type_data["success"] = task_type_data.get("success", 0) + 1
                else:
                    task_type_data["failure"] = task_type_data.get("failure", 0) + 1
                    task_type_data["last_failure_reason"] = f"expected={expected_agent}, actual={actual_agent}"

                from src.state.models import AgentPerformance
                perf = AgentPerformance(
                    agent_name=actual_agent,
                    task_type=task_id,
                    success=task_type_data["success"],
                    failure=task_type_data["failure"],
                    last_failure_reason=task_type_data.get("last_failure_reason", ""),
                    last_updated=datetime.now(timezone.utc).isoformat(),
                )
                self._db.upsert_agent_performance(perf)
            except Exception as e:
                logger.error(f"Failed to record feedback: {e}")

    def clear_cache(self) -> None:
        """Clear the internal cache."""
        with self._lock:
            self._cache.clear()
            self._cache_time = 0


def learn_from_delegations(db: StateDB | None = None, limit: int = 1000) -> dict[str, Any]:
    """Convenience function to analyze delegations and return insights."""
    learner = DelegationLearner(db=db)
    return learner.analyze_delegations(limit)


def get_routing_recommendations(db: StateDB | None = None) -> dict[str, Any]:
    """Convenience function to get routing recommendations."""
    learner = DelegationLearner(db=db)
    return learner.recommend_routing()


def generate_learning_report(db: StateDB | None = None) -> LearningReport:
    """Convenience function to generate a full learning report."""
    learner = DelegationLearner(db=db)
    return learner.generate_report()
