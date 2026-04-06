"""Compatibility: src.intelligence.learning → src.tools.intelligence.learning"""
from src.tools.intelligence.learning import (  # noqa: F401
    DelegationLearner, PatternInsight, LearningReport, learn_from_delegations,
    get_routing_recommendations, generate_learning_report, HAS_STATE_DB
)
