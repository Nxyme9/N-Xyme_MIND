"""
Tunnel Key Pool - Pluggable key pool for multi-provider API key management
==========================================================================

Key features:
- Thread-safe key management
- Weighted key selection
- Dynamic key add/remove at runtime
- Per-key health tracking
- Circuit breaker integration

Usage:
    from packages.tunnel.key_pool import KeyPool

    pool = KeyPool("openrouter", max_keys=10)
    pool.add_key("sk-or-xxx", {"id": "or-001", "weight": 1.0})

    key = pool.rotate()  # Get next key based on weight
    pool.remove_key("or-001")
"""

import threading
import time
import uuid
import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PooledKey:
    """A single API key in the pool with health tracking."""

    id: str
    key: str
    provider: str
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Runtime state
    is_available: bool = True
    cooldown_until: float = 0.0
    consecutive_errors: int = 0
    health_score: float = 1.0

    # Stats
    request_count: int = 0
    error_count: int = 0
    total_tokens: int = 0
    latency_history: List[float] = field(default_factory=list)

    def is_ready(self) -> bool:
        """Check if key is ready for use."""
        if not self.is_available:
            return False
        if time.time() < self.cooldown_until:
            return False
        if self.consecutive_errors >= 5:
            return False
        return True

    def record_success(self, tokens: int = 0, latency_ms: float = 0.0):
        """Record successful request."""
        self.consecutive_errors = 0
        self.health_score = min(1.0, self.health_score + 0.1)
        self.cooldown_until = 0.0
        self.request_count += 1
        self.total_tokens += tokens

        if latency_ms > 0:
            self.latency_history.append(latency_ms)
            if len(self.latency_history) > 100:
                self.latency_history = self.latency_history[-100:]

    def record_failure(
        self, error_type: str = "unknown", cooldown_seconds: float = 0.0
    ):
        """Record failed request."""
        self.consecutive_errors += 1
        self.error_count += 1
        self.health_score = max(0.0, self.health_score - 0.15)

        if cooldown_seconds > 0:
            self.cooldown_until = time.time() + cooldown_seconds
        elif self.consecutive_errors >= 3:
            # Auto-cooldown on repeated errors
            cooldown = min(10 * (2 ** (self.consecutive_errors - 3)), 300)
            self.cooldown_until = time.time() + cooldown

    def get_avg_latency(self) -> float:
        """Get average latency."""
        if not self.latency_history:
            return 0.0
        return sum(self.latency_history) / len(self.latency_history)

    def get_stats(self) -> Dict[str, Any]:
        """Get key statistics."""
        return {
            "id": self.id,
            "provider": self.provider,
            "weight": self.weight,
            "health_score": self.health_score,
            "is_available": self.is_available,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "total_tokens": self.total_tokens,
            "avg_latency_ms": self.get_avg_latency(),
            "success_rate": (
                (self.request_count - self.error_count) / self.request_count * 100
                if self.request_count > 0
                else 100.0
            ),
        }


class KeyPool:
    """
    Pluggable key pool for any LLM provider.

    Thread-safe with weighted key selection and health tracking.
    """

    def __init__(self, provider: str, max_keys: int = 10):
        self.provider = provider
        self.max_keys = max_keys
        self._keys: Dict[str, PooledKey] = {}
        self._lock = threading.RLock()
        self._weight_calculator: Optional[Callable] = None

        logger.info(f"[KeyPool] Created for provider: {provider}")

    def add_key(
        self,
        key: str,
        metadata: Optional[Dict[str, Any]] = None,
        key_id: Optional[str] = None,
        weight: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Add a new key to the pool.

        Returns:
            {"success": bool, "key_id": str, "error": str or None}
        """
        with self._lock:
            if len(self._keys) >= self.max_keys:
                return {
                    "success": False,
                    "error": f"Pool full (max {self.max_keys} keys)",
                }

            # Generate key ID if not provided
            if not key_id:
                key_id = f"{self.provider}-{uuid.uuid4().hex[:8]}"

            # Check for duplicate
            if key_id in self._keys:
                return {
                    "success": False,
                    "error": f"Key ID already exists: {key_id}",
                }

            pooled_key = PooledKey(
                id=key_id,
                key=key,
                provider=self.provider,
                weight=weight,
                metadata=metadata or {},
            )

            self._keys[key_id] = pooled_key
            logger.info(f"[KeyPool] Added key: {key_id} to {self.provider} pool")

            return {"success": True, "key_id": key_id}

    def remove_key(self, key_id: str) -> bool:
        """Remove a key from the pool."""
        with self._lock:
            if key_id in self._keys:
                del self._keys[key_id]
                logger.info(f"[KeyPool] Removed key: {key_id}")
                return True
            return False

    def get_key(self, key_id: str) -> Optional[PooledKey]:
        """Get a specific key by ID."""
        return self._keys.get(key_id)

    def get_available_keys(self) -> List[PooledKey]:
        """Get all healthy, available keys."""
        with self._lock:
            return [k for k in self._keys.values() if k.is_ready()]

    def get_all_keys(self) -> List[PooledKey]:
        """Get all keys in pool."""
        with self._lock:
            return list(self._keys.values())

    def rotate(self) -> Optional[PooledKey]:
        """
        Get next key based on weight and health.

        Uses weighted random selection favoring healthier keys.
        """
        available = self.get_available_keys()

        if not available:
            logger.warning(f"[KeyPool] No available keys for {self.provider}")
            return None

        # Calculate weights (health score * key weight)
        weights = []
        for k in available:
            effective_weight = k.weight * k.health_score
            weights.append(effective_weight)

        # Weighted selection
        total = sum(weights)
        if total <= 0:
            return available[0]

        import random

        r = random.uniform(0, total)
        cumulative = 0

        for i, k in enumerate(available):
            cumulative += weights[i]
            if r <= cumulative:
                return k

        return available[0]

    def update_key_weight(self, key_id: str, weight: float) -> bool:
        """Update key weight."""
        with self._lock:
            if key_id in self._keys:
                self._keys[key_id].weight = weight
                return True
            return False

    def set_key_unavailable(self, key_id: str, available: bool = False) -> bool:
        """Set key availability."""
        with self._lock:
            if key_id in self._keys:
                self._keys[key_id].is_available = available
                return True
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            all_keys = list(self._keys.values())
            available = [k for k in all_keys if k.is_ready()]

            return {
                "provider": self.provider,
                "total_keys": len(all_keys),
                "available_keys": len(available),
                "max_keys": self.max_keys,
                "keys": [k.get_stats() for k in all_keys],
            }

    def reset(self):
        """Reset all keys in pool."""
        with self._lock:
            self._keys.clear()
            logger.info(f"[KeyPool] Reset pool for {self.provider}")


# Convenience functions
def create_pool_from_config(provider: str, config: Dict[str, Any]) -> KeyPool:
    """Create a KeyPool from configuration dict."""
    pool = KeyPool(
        provider=provider,
        max_keys=config.get("max_concurrent", 10),
    )

    for key_data in config.get("keys", []):
        pool.add_key(
            key=key_data["key"],
            key_id=key_data.get("id"),
            metadata=key_data.get("metadata", {}),
            weight=key_data.get("weight", 1.0),
        )

    return pool
