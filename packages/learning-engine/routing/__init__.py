"""Routing module for learning-engine.

Exports:
- optimizer: Routing weight optimizer
- ab_testing: A/B testing framework
- counterfactual: Counterfactual learning engine
"""

from .optimizer import (
    AgentWeights,
    RoutingRecommendation,
    RoutingWeightOptimizer,
    get_routing_optimizer,
)

from .ab_testing import (
    ABTest,
    ABTestingFramework,
    TestStatus,
    TestVariant,
    get_ab_testing,
)

from .counterfactual import (
    CounterfactualEngine,
    CounterfactualResult,
)

__all__ = [
    # optimizer
    "AgentWeights",
    "RoutingRecommendation",
    "RoutingWeightOptimizer",
    "get_routing_optimizer",
    # ab_testing
    "ABTest",
    "ABTestingFramework",
    "TestStatus",
    "TestVariant",
    "get_ab_testing",
    # counterfactual
    "CounterfactualEngine",
    "CounterfactualResult",
]