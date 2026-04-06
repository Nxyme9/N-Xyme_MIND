"""Analytics and metrics for learning-engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LearningMetrics:
    """Metrics for learning system performance."""
    total_delegations: int = 0
    successful_delegations: int = 0
    failed_delegations: int = 0
    avg_latency_ms: float = 0.0
    agent_usage: dict[str, int] = field(default_factory=dict)
    level_distribution: dict[int, int] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        if self.total_delegations == 0:
            return 0.0
        return self.successful_delegations / self.total_delegations


class MetricsCollector:
    """Collects and aggregates learning metrics."""
    
    def __init__(self):
        self._metrics = LearningMetrics()
    
    def record_delegation(self, agent: str, level: int, success: bool, latency_ms: float) -> None:
        """Record a delegation for metrics."""
        self._metrics.total_delegations += 1
        if success:
            self._metrics.successful_delegations += 1
        else:
            self._metrics.failed_delegations += 1
        
        # Update agent usage
        if agent not in self._metrics.agent_usage:
            self._metrics.agent_usage[agent] = 0
        self._metrics.agent_usage[agent] += 1
        
        # Update level distribution
        if level not in self._metrics.level_distribution:
            self._metrics.level_distribution[level] = 0
        self._metrics.level_distribution[level] += 1
        
        # Update average latency
        total = self._metrics.total_delegations
        current_avg = self._metrics.avg_latency_ms
        self._metrics.avg_latency_ms = ((total - 1) * current_avg + latency_ms) / total
    
    def get_metrics(self) -> LearningMetrics:
        """Get current metrics."""
        return self._metrics
    
    def reset(self) -> None:
        """Reset metrics."""
        self._metrics = LearningMetrics()


# Stub for dashboard integration
def get_dashboard_data() -> dict[str, Any]:
    """Get data for dashboard display."""
    return {
        "success_rate": 0.0,
        "total_delegations": 0,
        "agent_usage": {},
        "level_distribution": {},
    }


# Stub for report generation
def generate_report(metrics: LearningMetrics) -> str:
    """Generate a text report from metrics."""
    return f"""
Learning Metrics Report
========================
Total Delegations: {metrics.total_delegations}
Success Rate: {metrics.success_rate:.1%}
Avg Latency: {metrics.avg_latency_ms:.0f}ms
Agent Usage: {metrics.agent_usage}
Level Distribution: {metrics.level_distribution}
"""