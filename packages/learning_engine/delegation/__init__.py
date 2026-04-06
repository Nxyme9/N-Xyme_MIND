"""Delegation module for learning-engine.

Exports:
- learner: Delegation learning and pattern analysis
"""

from .learner import (
    DelegationLearner,
    LearningReport,
    PatternInsight,
    learn_from_delegations,
    get_routing_recommendations,
    generate_learning_report,
)

__all__ = [
    "DelegationLearner",
    "LearningReport",
    "PatternInsight",
    "learn_from_delegations",
    "get_routing_recommendations",
    "generate_learning_report",
]