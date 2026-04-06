"""Routing Decision Caching

Caches frequently used routing decisions to improve performance.
Uses LRU cache with TTL for automatic expiration.
"""

import time
import logging
from typing import Dict, Any, Optional, Tuple
from collections import OrderedDict

logger = logging.getLogger("routing-cache")


class RoutingCache:
    """LRU cache for routing decisions with TTL."""

    def __init__(self, max_size: int = 1000, default_ttl: float = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Tuple[Any, float, float]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get cached routing decision."""
        if key not in self._cache:
            self._misses += 1
            return None

        value, created_at, ttl = self._cache[key]

        # Check if expired
        if time.time() - created_at > ttl:
            del self._cache[key]
            self._misses += 1
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        self._hits += 1
        return value

    def put(self, key: str, value: Any, ttl: Optional[float] = None):
        """Cache a routing decision."""
        if ttl is None:
            ttl = self.default_ttl

        # Evict oldest if cache is full
        if len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)

        self._cache[key] = (value, time.time(), ttl)

    def clear(self):
        """Clear the cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "default_ttl": self.default_ttl,
        }

    def generate_key(
        self, task_description: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate cache key from task description and context."""
        key = task_description.lower().strip()
        if context:
            # Add context factors to key
            for k, v in sorted(context.items()):
                key += f"|{k}={v}"
        return key


# Global cache instance
_routing_cache = None


def get_routing_cache() -> RoutingCache:
    """Get or create the global routing cache."""
    global _routing_cache
    if _routing_cache is None:
        _routing_cache = RoutingCache()
    return _routing_cache
