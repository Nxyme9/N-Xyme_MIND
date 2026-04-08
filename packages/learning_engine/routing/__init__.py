"""Learning engine routing package."""

# Existing routing modules
from .optimizer import (
    RoutingWeightOptimizer,
    RoutingRecommendation,
    AgentWeights,
    get_routing_optimizer,
)

from .ab_testing import (
    ABTestingFramework,
    ABTest,
    TestStatus,
    TestVariant,
    get_ab_testing,
)

from .counterfactual import (
    CounterfactualEngine,
    CounterfactualResult,
)

# New adaptive router with Q-Learning feedback loop
from .adaptive_router import AdaptiveRouter, LearningStats

# Strategy selector (Phase 3.1 - Contextual Bandits)
from ..meta.strategy_selector import (
    StrategySelector,
    StrategyRouter,
    StrategyType,
    SelectorStats,
)

__all__ = [
    # optimizer
    "RoutingWeightOptimizer",
    "RoutingRecommendation",
    "AgentWeights",
    "get_routing_optimizer",
    # ab_testing
    "ABTestingFramework",
    "ABTest",
    "TestStatus",
    "TestVariant",
    "get_ab_testing",
    # counterfactual
    "CounterfactualEngine",
    "CounterfactualResult",
    # adaptive_router
    "AdaptiveRouter",
    "LearningStats",
    # strategy_selector
    "StrategySelector",
    "StrategyRouter",
    "StrategyType",
    "SelectorStats",
]