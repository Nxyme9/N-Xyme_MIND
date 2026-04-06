"""
Infrastructure Bundle — Platform services: proxy, network, resilience, monitoring, cost, config

Public API:
- proxy: MCP proxy server for intelligent routing
- CircuitBreaker: Fault tolerance pattern
- HealthCheck: System health monitoring
- CostTracker: AI usage cost tracking

Version: 1.0.0
"""

__interface_version__ = "1.0.0"

# Re-export core public API
from .resilience.circuit_breaker import CircuitBreaker, CircuitBreakerOpen, CircuitState
from .cost.tracker import CostTracker, ModelProvider, MODEL_PRICING, UsageRecord
from .monitoring.metrics import MetricsStore

# Proxy module - exposes intelligent routing
from . import proxy
from . import network
from . import monitoring
from . import cost
from . import config
from . import resilience
from . import utils

__all__ = [
    "__interface_version__",
    # Core classes
    "CircuitBreaker",
    "CircuitBreakerOpen", 
    "CircuitState",
    "CostTracker",
    "ModelProvider",
    "MODEL_PRICING",
    "UsageRecord",
    "MetricsStore",
    # Modules
    "proxy",
    "network", 
    "monitoring",
    "cost",
    "config",
    "resilience",
    "utils",
]