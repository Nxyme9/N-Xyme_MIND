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
# LAZY IMPORTS — Prevent eager cascade that crashes MCP startup
# FAISS/numpy imported inside rl/__init__.py at module level caused
# brain_mcp/__init__.py → _register_nxyme_modules() → learning_engine/__init__
# → rl/__init__.py → q_learning.py (faiss import) → cascade failure.
# Solution: TYPE_CHECKING + __getattr__ pattern. Imports defer until first access.
# =============================================================================
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .rl import (
        QLearningEngine,
        MultiArmedBandit,
        PolicyManager,
        CompositeReward,
    )
    from .meta import (
        MetaLearningEngine,
        EWCEngine,
        ActiveLearningEngine,
    )
    from .routing import (
        RoutingWeightOptimizer,
        RoutingRecommendation,
        AgentWeights,
        ABTestingFramework,
        ABTest,
        TestStatus,
        TestVariant,
        CounterfactualEngine,
        CounterfactualResult,
    )
    from .delegation import (
        DelegationLearner,
        LearningReport,
        PatternInsight,
    )
    from .session_hooks import SessionLifecycleHook
    from .routing.outcome_hook import TaskOutcomeHook, TaskContext, TaskState

# Lazy module __getattr__ — resolve only when accessed
_LAZY_MAPPINGS = {
    "QLearningEngine": ".rl.q_learning",
    "MultiArmedBandit": ".rl.bandit",
    "PolicyManager": ".rl.policy",
    "CompositeReward": ".rl.reward",
    "MetaLearningEngine": ".meta.meta_learning",
    "EWCEngine": ".meta.ewc",
    "ActiveLearningEngine": ".meta.active_learning",
    "RoutingWeightOptimizer": ".routing.optimizer",
    "RoutingRecommendation": ".routing.optimizer",
    "AgentWeights": ".routing.optimizer",
    "get_routing_optimizer": ".routing.optimizer",
    "ABTestingFramework": ".routing.ab_testing",
    "ABTest": ".routing.ab_testing",
    "TestStatus": ".routing.ab_testing",
    "TestVariant": ".routing.ab_testing",
    "get_ab_testing": ".routing.ab_testing",
    "CounterfactualEngine": ".routing.counterfactual",
    "CounterfactualResult": ".routing.counterfactual",
    "DelegationLearner": ".delegation.learner",
    "LearningReport": ".delegation.learner",
    "PatternInsight": ".delegation.learner",
    "SessionLifecycleHook": ".session_hooks",
    "TaskOutcomeHook": ".routing.outcome_hook",
    "TaskContext": ".routing.outcome_hook",
    "TaskState": ".routing.outcome_hook",
    "get_hook": ".routing.outcome_hook",
    "learn_from_delegations": ".delegation.learner",
    "get_routing_recommendations": ".delegation.learner",
    "generate_learning_report": ".delegation.learner",
}


def __getattr__(name: str):
    if name in _LAZY_MAPPINGS:
        import importlib
        mod_path = _LAZY_MAPPINGS[name]
        module = importlib.import_module(mod_path, package=__package__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return list(__all__) + list(_LAZY_MAPPINGS.keys())

# =============================================================================
# Module-level singletons (lazy initialization, thread-safe)
# =============================================================================

import threading
from pathlib import Path
from typing import Optional

_learner: Optional[DelegationLearner] = None
_routing_optimizer: Optional[RoutingWeightOptimizer] = None
_ab_testing: Optional[ABTestingFramework] = None
_session_hook: Optional[SessionLifecycleHook] = None
_task_hook: Optional[TaskOutcomeHook] = None
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
    from .routing.optimizer import get_routing_optimizer
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
    from .routing.optimizer import get_routing_optimizer
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
    from .routing.optimizer import get_routing_optimizer
    from .delegation.learner import DelegationLearner
    global _routing_optimizer, _ab_testing, _learner
    
    result = {"version": __interface_version__}
    
    if _routing_optimizer is None:
        with _lock:
            if _routing_optimizer is None:
                _routing_optimizer = get_routing_optimizer()
    result["routing_weights"] = _routing_optimizer.get_routing_weights()
    
    if _ab_testing is None:
        with _lock:
            if _ab_testing is None:
                from .routing.ab_testing import get_ab_testing
                _ab_testing = get_ab_testing()
    result["ab_tests"] = _ab_testing.get_all_tests()
    
    if _learner is None:
        with _lock:
            if _learner is None:
                _learner = DelegationLearner()
    result["delegation_stats"] = _learner.analyze_delegations()
    
    return result


def get_session_hook() -> SessionLifecycleHook:
    """Get or create the global SessionLifecycleHook instance."""
    global _session_hook
    if _session_hook is None:
        with _lock:
            if _session_hook is None:
                _session_hook = SessionLifecycleHook()
    return _session_hook


def get_task_hook() -> TaskOutcomeHook:
    """Get or create the global TaskOutcomeHook instance."""
    global _task_hook
    if _task_hook is None:
        with _lock:
            if _task_hook is None:
                _task_hook = TaskOutcomeHook()
    return _task_hook


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
    # hooks
    "SessionLifecycleHook",
    "TaskOutcomeHook",
    "TaskContext",
    "TaskState",
    "get_hook",
    "get_session_hook",
    "get_task_hook",
    # Public API
    "record_outcome",
    "route_task",
    "status",
    "retrain",
]