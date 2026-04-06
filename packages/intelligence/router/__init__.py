"""Router package — Core routing components."""

from .unified import UnifiedDelegationRouter, RoutingDecision
from .trigger import get_trigger_router
from .memory import get_memory_router
from .ml import get_ml_router
from .local_model import get_local_analyzer

__all__ = [
    "UnifiedDelegationRouter",
    "RoutingDecision",
    "get_trigger_router",
    "get_memory_router",
    "get_ml_router",
    "get_local_analyzer",
]
