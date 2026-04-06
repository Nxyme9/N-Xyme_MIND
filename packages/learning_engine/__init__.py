"""N-Xyme Learning Engine v0.1 — Self-Learning System.

Consolidates all learning code from 3 locations into a clean modular bundle:
- src/tools/learning/
- src/tools/intelligence/learning.py, routing_optimizer.py, ab_testing.py
- src/infrastructure/proxy/learning_engine.py

Provides: record_outcome(), route_task(), status(), retrain()
"""

from __future__ import annotations

__interface_version__ = "1.0.0"

# =============================================================================
# Core Imports - rl module
# =============================================================================

from .rl import (
    QLearningEngine,
    MultiArmedBandit,
    PolicyManager,
    CompositeReward,
)

# =============================================================================
# Core Imports - meta module
# =============================================================================

from .meta import (
    MetaLearningEngine,
    EWCEngine,
    ActiveLearningEngine,
)

# =============================================================================
# Core Imports - routing module
# =============================================================================

from .routing import (
    RoutingWeightOptimizer,
    RoutingRecommendation,
    AgentWeights,
    get_routing_optimizer,
    ABTestingFramework,
    ABTest,
    TestStatus,
    TestVariant,
    get_ab_testing,
    CounterfactualEngine,
    CounterfactualResult,
)

# =============================================================================
# Core Imports - delegation module
# =============================================================================

from .delegation import (
    DelegationLearner,
    LearningReport,
    PatternInsight,
    learn_from_delegations,
    get_routing_recommendations,
    generate_learning_report,
)

# =============================================================================
# Module-level singletons (lazy initialization, thread-safe)
# =============================================================================

import threading
from pathlib import Path
from typing import Optional

_learner: Optional[DelegationLearner] = None
_routing_optimizer: Optional[RoutingWeightOptimizer] = None
_ab_testing: Optional[ABTestingFramework] = None
_lock = threading.Lock()


def record_outcome(
    agent: str,
    level: int,
    success: bool,
    latency_ms: float = 0
) -> None:
    """Record a delegation outcome for learning.
    
    Args:
        agent: The agent that handled the task
        level: Complexity level (1-5)
        success: Whether the task succeeded
        latency_ms: Execution latency in milliseconds
    """
    global _routing_optimizer
    if _routing_optimizer is None:
        with _lock:
            if _routing_optimizer is None:
                _routing_optimizer = get_routing_optimizer()
    _routing_optimizer.update_weights(agent, level, success, latency_ms)


def route_task(task_description: str, level: int) -> RoutingRecommendation:
    """Route a task to the optimal agent based on learned weights.
    
    Args:
        task_description: Description of the task
        level: Complexity level (1-5)
    
    Returns:
        RoutingRecommendation with optimal agent and confidence
    """
    global _routing_optimizer
    if _routing_optimizer is None:
        with _lock:
            if _routing_optimizer is None:
                _routing_optimizer = get_routing_optimizer()
    return _routing_optimizer.get_optimal_agent(task_description, level)


def status() -> dict:
    """Get current learning system status.
    
    Returns:
        Dict with routing weights, A/B tests, and learning stats
    """
    global _routing_optimizer, _ab_testing, _learner
    
    result = {"version": __interface_version__}
    
    # Routing weights
    if _routing_optimizer is None:
        with _lock:
            if _routing_optimizer is None:
                _routing_optimizer = get_routing_optimizer()
    result["routing_weights"] = _routing_optimizer.get_routing_weights()
    
    # A/B tests
    if _ab_testing is None:
        with _lock:
            if _ab_testing is None:
                _ab_testing = get_ab_testing()
    result["ab_tests"] = _ab_testing.get_all_tests()
    
    # Delegation learning stats
    if _learner is None:
        with _lock:
            if _learner is None:
                _learner = DelegationLearner()
    result["delegation_stats"] = _learner.analyze_delegations()
    
    return result


def retrain() -> None:
    """Trigger retraining of learning models.
    
    Currently a placeholder - full retraining would involve:
    - Re-training Q-learning tables
    - Updating bandit arm probabilities
    - Recomputing meta-learning parameters
    - Re-evaluating EWC重要性 weights
    """
    global _routing_optimizer
    if _routing_optimizer is None:
        with _lock:
            if _routing_optimizer is None:
                _routing_optimizer = get_routing_optimizer()
    _routing_optimizer.reset_weights()


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Version
    "__interface_version__",
    # rl
    "QLearningEngine",
    "MultiArmedBandit",
    "PolicyManager",
    "CompositeReward",
    # meta
    "MetaLearningEngine",
    "EWCEngine",
    "ActiveLearningEngine",
    # routing
    "RoutingWeightOptimizer",
    "RoutingRecommendation",
    "AgentWeights",
    "get_routing_optimizer",
    "ABTestingFramework",
    "ABTest",
    "TestStatus",
    "TestVariant",
    "get_ab_testing",
    "CounterfactualEngine",
    "CounterfactualResult",
    # delegation
    "DelegationLearner",
    "LearningReport",
    "PatternInsight",
    "learn_from_delegations",
    "get_routing_recommendations",
    "generate_learning_report",
    # Public API
    "record_outcome",
    "route_task",
    "status",
    "retrain",
]