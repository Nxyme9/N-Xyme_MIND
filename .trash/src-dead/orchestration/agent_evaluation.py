"""
Agent Evaluation — Evaluate agent performance (ported from MIND)

Tracks agent response quality, speed, and accuracy.

Usage:
    evaluator = AgentEvaluator()
    evaluator.record("explore", success=True, duration=1.5)
    evaluator.record("explore", success=False, duration=3.0)
    stats = evaluator.get_stats("explore")
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentMetric:
    """Agent performance metric."""

    agent: str
    success: bool
    duration: float  # seconds
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentEvaluator:
    """Evaluate and track agent performance."""

    def __init__(self):
        self._metrics: Dict[str, List[AgentMetric]] = defaultdict(list)
        logger.info("AgentEvaluator: Initialized")

    def record(
        self,
        agent: str,
        success: bool,
        duration: float,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Record agent execution."""
        metric = AgentMetric(
            agent=agent,
            success=success,
            duration=duration,
            metadata=metadata or {},
        )
        self._metrics[agent].append(metric)

        # Keep only last 1000 per agent
        if len(self._metrics[agent]) > 1000:
            self._metrics[agent] = self._metrics[agent][-1000:]

    def get_stats(self, agent: Optional[str] = None) -> Dict[str, Any]:
        """Get agent statistics."""
        if agent:
            return self._get_agent_stats(agent)

        # All agents
        return {
            "agents": {name: self._get_agent_stats(name) for name in self._metrics.keys()},
            "total_agents": len(self._metrics),
        }

    def _get_agent_stats(self, agent: str) -> Dict[str, Any]:
        """Get stats for a single agent."""
        metrics = self._metrics.get(agent, [])
        if not metrics:
            return {"agent": agent, "total": 0}

        total = len(metrics)
        successes = sum(1 for m in metrics if m.success)
        failures = total - successes
        durations = [m.duration for m in metrics]

        return {
            "agent": agent,
            "total": total,
            "successes": successes,
            "failures": failures,
            "success_rate": round(successes / total * 100, 1) if total > 0 else 0,
            "avg_duration": round(sum(durations) / len(durations), 2) if durations else 0,
            "min_duration": round(min(durations), 2) if durations else 0,
            "max_duration": round(max(durations), 2) if durations else 0,
            "p95_duration": round(sorted(durations)[int(len(durations) * 0.95)], 2)
            if len(durations) > 1
            else 0,
        }

    def get_top_performers(self, limit: int = 5) -> List[Dict]:
        """Get top performing agents."""
        all_stats = []
        for agent in self._metrics.keys():
            stats = self._get_agent_stats(agent)
            if stats["total"] > 0:
                all_stats.append(stats)

        return sorted(
            all_stats,
            key=lambda x: (x["success_rate"], -x["avg_duration"]),
            reverse=True,
        )[:limit]

    def get_underperformers(self, min_success_rate: float = 80.0) -> List[Dict]:
        """Get agents with low success rate."""
        underperformers = []
        for agent in self._metrics.keys():
            stats = self._get_agent_stats(agent)
            if stats["total"] >= 5 and stats["success_rate"] < min_success_rate:
                underperformers.append(stats)

        return sorted(underperformers, key=lambda x: x["success_rate"])
