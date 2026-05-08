"""
Tunnel Orchestrator - Unified multi-provider API tunnel management
================================================================

Manages KeyPools for multiple providers with fallback routing,
health tracking, and learning integration.

Usage:
    from packages.tunnel.orchestrator import TunnelOrchestrator

    tunnel = TunnelOrchestrator()
    result = await tunnel.chat("openrouter", "qwen/qwen3.6-plus:free", messages)

    # Or use fallback chain
    result = await tunnel.route_with_fallback(model, messages, chain)
"""

import json
import logging
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Try to import existing NxRotator components
try:
    from nx_rotator.core.aggregator import NxRotator, RequestResult
    from nx_rotator.integration import get_rotator, is_enabled as nx_rotator_enabled

    NX_ROTATOR_AVAILABLE = True
except ImportError:
    NX_ROTATOR_AVAILABLE = False
    NxRotator = None
    RequestResult = None
    nx_rotator_enabled = lambda: False

from .key_pool import KeyPool

# Default config path
DEFAULT_CONFIG = Path("configs/tunnel_config.json")


@dataclass
class TunnelConfig:
    """Tunnel system configuration."""

    enabled: bool = True
    default_mode: str = "race"  # race, funnel, parallel, turbo, single

    # Provider settings
    providers: Dict[str, Dict] = field(default_factory=dict)

    # Fallback chain
    fallback_chain: List[str] = field(
        default_factory=lambda: ["openrouter", "google", "opencode"]
    )

    # Learning
    learning_enabled: bool = True
    learning_db_path: str = "configs/api-keys/nx_rotator_learning.db"


class ProviderHealth:
    """Track health scores for each provider."""

    def __init__(self):
        self._scores: Dict[str, float] = {}
        self._lock = threading.RLock()

    def record_success(self, provider: str, weight: float = 0.1):
        with self._lock:
            current = self._scores.get(provider, 0.5)
            self._scores[provider] = min(1.0, current + weight)

    def record_failure(self, provider: str, weight: float = 0.2):
        with self._lock:
            current = self._scores.get(provider, 0.5)
            self._scores[provider] = max(0.0, current - weight)

    def get_score(self, provider: str) -> float:
        with self._lock:
            return self._scores.get(provider, 0.5)

    def get_healthiest(self, providers: List[str]) -> Optional[str]:
        with self._lock:
            if not providers:
                return None
            return max(providers, key=lambda p: self._scores.get(p, 0.5))

    def get_all_scores(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._scores)


class FallbackRouter:
    """Routes through providers with automatic fallback."""

    def __init__(self, chain: List[str], providers: Dict[str, KeyPool]):
        self.chain = chain
        self._providers = providers
        self._health = ProviderHealth()
        self._lock = threading.RLock()

    def add_provider(self, name: str, pool: KeyPool):
        with self._lock:
            self._providers[name] = pool

    def remove_provider(self, name: str):
        with self._lock:
            self._providers.pop(name, None)
            if name in self.chain:
                self.chain.remove(name)

    def get_pool(self, provider: str) -> Optional[KeyPool]:
        return self._providers.get(provider)

    def get_health(self) -> ProviderHealth:
        return self._health

    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        with self._lock:
            return {
                "chain": self.chain,
                "providers": {
                    name: pool.get_stats() for name, pool in self._providers.items()
                },
                "health": self._health.get_all_scores(),
            }


class TunnelOrchestrator:
    def __init__(
        self,
        config_path: Optional[Path] = None,
        container: Optional[Any] = None,
    ):
        self._config_path = config_path or DEFAULT_CONFIG
        self._config = self._load_config()

        self._pools: Dict[str, KeyPool] = {}
        self._nx_rotator: Any = None

        self._fallback_router: Optional[FallbackRouter] = None
        self._health = ProviderHealth()

        self._learning_db_path = self._config.learning_db_path
        self._learning_enabled = self._config.learning_enabled

        self._initialized = False

    @classmethod
    def create_with_container(
        cls, config_path: Optional[Path] = None, container: Optional[Any] = None
    ) -> "TunnelOrchestrator":
        try:
            from packages.core.di_container import get_container as get_di_container

            c = container or get_di_container()
        except ImportError:
            c = None

        instance = cls(config_path=config_path)
        instance._init_pools()
        instance._init_nx_rotator()
        instance._initialized = True

        if c is not None:
            try:
                c.register("tunnel_orchestrator", instance=instance, singleton=True)
            except Exception:
                pass

        return instance

    def _load_config(self) -> TunnelConfig:
        """Load configuration from JSON."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                data = json.load(f)
            return TunnelConfig(**data)
        return TunnelConfig()

    def _init_pools(self):
        """Initialize provider pools from config."""
        providers = self._config.providers

        if not providers:
            # Try to load from keys.json
            keys_path = Path("configs/api-keys/keys.json")
            if keys_path.exists():
                with open(keys_path) as f:
                    keys_data = json.load(f)

                # Extract OpenRouter keys
                or_keys = keys_data.get("openrouter", [])
                if or_keys:
                    pool = KeyPool("openrouter", max_keys=10)
                    for key_info in or_keys[:10]:  # Max 10 keys
                        if isinstance(key_info, dict):
                            pool.add_key(
                                key=key_info.get("key", ""),
                                key_id=key_info.get("id"),
                                metadata=key_info,
                                weight=key_info.get("weight", 1.0),
                            )
                    self._pools["openrouter"] = pool

        # Initialize fallback router
        self._fallback_router = FallbackRouter(
            chain=self._config.fallback_chain,
            providers=self._pools,
        )

    def _init_nx_rotator(self):
        """Initialize NxRotator if available."""
        if NX_ROTATOR_AVAILABLE and nx_rotator_enabled():
            self._nx_rotator = get_rotator()
            if self._nx_rotator:
                logger.info(
                    f"[TunnelOrchestrator] NxRotator enabled with "
                    f"{len(self._nx_rotator.keys)} keys"
                )

    def get_pool(self, provider: str) -> Optional[KeyPool]:
        """Get KeyPool for provider."""
        return self._pools.get(provider)

    def get_nx_rotator(self):
        """Get NxRotator instance."""
        return self._nx_rotator

    def add_provider_pool(self, provider: str, pool: KeyPool):
        """Add a provider pool."""
        self._pools[provider] = pool
        if self._fallback_router:
            self._fallback_router.add_provider(provider, pool)
        logger.info(f"[TunnelOrchestrator] Added pool for: {provider}")

    def add_key(
        self,
        provider: str,
        key: str,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Dynamically add key to provider pool."""
        pool = self._pools.get(provider)

        if not pool:
            # Create new pool
            pool = KeyPool(provider)
            self.add_provider_pool(provider, pool)

        return pool.add_key(key, metadata)

    def remove_key(self, provider: str, key_id: str) -> bool:
        """Remove key from provider pool."""
        pool = self._pools.get(provider)
        if pool:
            return pool.remove_key(key_id)
        return False

    def get_available_providers(self) -> List[str]:
        """Get list of providers with available keys."""
        return [name for name, pool in self._pools.items() if pool.get_available_keys()]

    def get_stats(self) -> Dict[str, Any]:
        """Get tunnel statistics."""
        return {
            "enabled": self._config.enabled,
            "default_mode": self._config.default_mode,
            "nx_rotator_available": self._nx_rotator is not None,
            "providers": {name: pool.get_stats() for name, pool in self._pools.items()},
            "health": self._health.get_all_scores(),
            "fallback_chain": self._config.fallback_chain,
        }

    def is_enabled(self) -> bool:
        """Check if tunnel is enabled."""
        return self._config.enabled

    def get_mode(self) -> str:
        """Get default tunnel mode."""
        return self._config.default_mode

    def set_mode(self, mode: str):
        """Set default tunnel mode."""
        if mode in ("race", "funnel", "parallel", "turbo", "single"):
            self._config.default_mode = mode
        else:
            logger.warning(f"[TunnelOrchestrator] Unknown mode: {mode}")

    def record_success(self, provider: str, latency_ms: float = 0.0):
        """Record successful request."""
        self._health.record_success(provider)

    def record_failure(self, provider: str):
        """Record failed request."""
        self._health.record_failure(provider)


# Singleton accessor
_orchestrator: Optional[TunnelOrchestrator] = None


def get_orchestrator() -> TunnelOrchestrator:
    """Get singleton TunnelOrchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = TunnelOrchestrator()
    return _orchestrator


def reset_orchestrator():
    """Reset singleton (for testing)."""
    global _orchestrator
    _orchestrator = None
