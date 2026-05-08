"""
Tunnel Package - Multi-provider API key management and routing
==============================================================

Provides:
- KeyPool: Thread-safe key pool with weighted selection
- TunnelOrchestrator: Multi-provider orchestration with fallback
- Provider interface: Pluggable provider abstraction

Quick Start:
    from packages.tunnel import get_orchestrator

    tunnel = get_orchestrator()
    stats = tunnel.get_stats()
"""

from .key_pool import KeyPool, PooledKey, create_pool_from_config
from .orchestrator import (
    TunnelOrchestrator,
    get_orchestrator,
    reset_orchestrator,
    TunnelConfig,
    ProviderHealth,
    FallbackRouter,
)
from .providers import (
    ProviderInterface,
    ProviderConfig,
    OpenCodeProvider,
    OpenRouterProvider,
    get_provider,
    PROVIDERS,
)

__all__ = [
    # Key pool
    "KeyPool",
    "PooledKey",
    "create_pool_from_config",
    # Orchestrator
    "TunnelOrchestrator",
    "get_orchestrator",
    "reset_orchestrator",
    "TunnelConfig",
    "ProviderHealth",
    "FallbackRouter",
    # Providers
    "ProviderInterface",
    "ProviderConfig",
    "OpenCodeProvider",
    "OpenRouterProvider",
    "get_provider",
    "PROVIDERS",
]
