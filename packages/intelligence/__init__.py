"""Intelligence bundle — Task routing and delegation intelligence.

Public API:
- route(task_description) -> RoutingDecision
- score_complexity(task_description) -> ComplexityScore
- available_agents() -> list
"""

__interface_version__ = "1.0.0"
__version__ = "0.1.0"

# Re-export from submodules
from .router.unified import UnifiedDelegationRouter, RoutingDecision
from .circuit_breaker import get_circuit_breaker_registry
from .fallback import get_fallback_chain, FallbackChain


async def route(task_description: str) -> RoutingDecision:
    """Route a task to the optimal agent.

    Args:
        task_description: The task to route

    Returns:
        RoutingDecision with level, agent, confidence, and strategy
    """
    router = UnifiedDelegationRouter()
    return await router.route_task(task_description)


def score_complexity(task_description: str):
    """Score the complexity of a task.

    Args:
        task_description: The task to score

    Returns:
        ScoreResult with level, tokens, and complexity factors
    """
    from .router.keyword import score_complexity as _score

    return _score(task_description)


def available_agents() -> list:
    """Get list of available agents.

    Returns:
        list of agent names
    """
    return [
        "sisyphus",
        "hephaestus",
        "oracle",
        "explore",
        "librarian",
        "metis",
        "momus",
        "plan",
        "atlas",
        "sisyphus-junior",
        "multimodal-looker",
    ]


__all__ = [
    "route",
    "score_complexity",
    "available_agents",
    "RoutingDecision",
    "UnifiedDelegationRouter",
    "__interface_version__",
    "__version__",
]
