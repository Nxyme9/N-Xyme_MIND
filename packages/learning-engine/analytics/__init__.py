"""Analytics module for learning-engine.

Exports:
- metrics: Learning metrics collection
"""

from .metrics import LearningMetrics, MetricsCollector, get_dashboard_data, generate_report

__all__ = [
    "LearningMetrics",
    "MetricsCollector",
    "get_dashboard_data",
    "generate_report",
]