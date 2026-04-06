"""
Cache Service — Ported from N-Xyme MIND

In-memory caching with TTL for high-traffic operations.
Falls back to no-op if Redis available later.

Usage:
    cache = CacheService()
    cache.set("key", "value", ttl=300)
    value = cache.get("key")  # Returns "value"
"""

import hashlib
import logging
import time
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class CacheEntry:
    """A cached value with TTL."""

    def __init__(self, value: Any, ttl: int = 300):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
        self.hits = 0

    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl


class CacheService:
    """In-memory cache with TTL support."""

    def __init__(self, max_size: int = 10000, default_ttl: int = 300):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
        logger.info(f"CacheService: Initialized (max={max_size}, ttl={default_ttl}s)")

    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and arguments."""
        parts = [prefix]
        parts.extend(str(a) for a in args)
        parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key = ":".join(parts)
        if len(key) > 200:
            return f"{prefix}:{hashlib.md5(key.encode()).hexdigest()[:16]}"
        return key

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        entry = self._cache.get(key)
        if entry is None:
            self._misses += 1
            return None
        if entry.is_expired:
            del self._cache[key]
            self._misses += 1
            return None
        entry.hits += 1
        self._hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        ttl = ttl or self.default_ttl

        # Evict oldest if at capacity (OrderedDict.popitem is O(1))
        if len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)

        self._cache[key] = CacheEntry(value, ttl)

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        expired = [k for k, v in self._cache.items() if v.is_expired]
        for k in expired:
            del self._cache[k]
        return len(expired)

    def cached(self, prefix: str, ttl: Optional[int] = None):
        """Decorator for caching function results."""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                key = self._make_key(prefix, *args, **kwargs)
                result = self.get(key)
                if result is not None:
                    return result
                result = func(*args, **kwargs)
                self.set(key, result, ttl)
                return result

            return wrapper

        return decorator

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "expired": sum(1 for e in self._cache.values() if e.is_expired),
        }


# Global cache instance
_global_cache = CacheService()


def get_cache() -> CacheService:
    """Get global cache instance."""
    return _global_cache
