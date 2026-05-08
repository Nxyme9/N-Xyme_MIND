#!/usr/bin/env python3
"""Tool Cache - Prefix caching for tool definitions to reduce latency.

This module provides LRU caching for tool definitions, category manifests,
and tool descriptions to reduce computation overhead across requests.

Research: Prefix caching can reduce latency 20-40% for static content.
"""

from __future__ import annotations

import re
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, Optional, Pattern


class ToolCache:
    """Thread-safe LRU cache with TTL support for tool definitions.

    Caches tool schemas, category manifests, and tool descriptions
    to reduce latency for repeated tool definition requests.

    Attributes:
        max_size: Maximum number of entries in cache.
        ttl: Time-to-live in seconds (None for no expiration).
        hit_rate: Cache hit ratio (0-1).
        miss_rate: Cache miss ratio (0-1).
        cache_size: Current number of entries.
    """

    def __init__(self, max_size: int = 100, ttl: Optional[float] = None):
        """Initialize the cache.

        Args:
            max_size: Maximum number of entries (default 100).
            ttl: Time-to-live in seconds (default None = no expiration).
        """
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl
        self._lock = threading.RLock()

        # Statistics
        self._hits = 0
        self._misses = 0

    @property
    def hit_rate(self) -> float:
        """Return cache hit rate (0-1)."""
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    @property
    def miss_rate(self) -> float:
        """Return cache miss rate (0-1)."""
        return 1.0 - self.hit_rate

    @property
    def cache_size(self) -> int:
        """Return current cache size."""
        with self._lock:
            return len(self._cache)

    def get_or_compute(self, key: str, compute_fn: Callable[[], Any]) -> Any:
        """Get cached value or compute and cache it.

        Args:
            key: Cache key.
            compute_fn: Function to compute value if not cached.

        Returns:
            Cached or computed value.
        """
        with self._lock:
            # Check if key exists and is valid
            if key in self._cache:
                entry = self._cache[key]

                # Check TTL expiration
                if self._ttl is not None:
                    age = time.time() - entry.get("timestamp", 0)
                    if age > self._ttl:
                        # Entry expired - remove it
                        del self._cache[key]
                        self._misses += 1
                        entry = None
                    else:
                        # Move to end (most recently used)
                        self._cache.move_to_end(key)
                        self._hits += 1
                        return entry.get("value")
                else:
                    # No TTL - return cached value
                    self._cache.move_to_end(key)
                    self._hits += 1
                    return entry.get("value")

            # Cache miss - compute value
            self._misses += 1
            value = compute_fn()

            # Add to cache
            self._cache[key] = {
                "value": value,
                "timestamp": time.time(),
            }

            # Evict oldest if over capacity
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

            return value

    def invalidate(self, pattern: str) -> int:
        """Invalidate all entries matching a regex pattern.

        Args:
            pattern: Regex pattern to match keys against.

        Returns:
            Number of entries invalidated.
        """
        compiled: Pattern[str] = re.compile(pattern)
        invalidated = 0

        with self._lock:
            keys_to_remove = [key for key in self._cache.keys() if compiled.search(key)]
            for key in keys_to_remove:
                del self._cache[key]
                invalidated += 1

        return invalidated

    def clear(self) -> None:
        """Clear all cache entries and reset statistics."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with hit_rate, miss_rate, cache_size, hits, misses.
        """
        with self._lock:
            return {
                "hit_rate": self.hit_rate,
                "miss_rate": self.miss_rate,
                "cache_size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "max_size": self._max_size,
                "ttl": self._ttl,
            }


# =============================================================================
# CACHE KEYS - Standard key formats for tool caching
# =============================================================================


class CacheKeys:
    """Standard cache key generators for tool definitions."""

    @staticmethod
    def manifest_key(categories: tuple) -> str:
        """Generate cache key for category manifest.

        Args:
            categories: Sorted tuple of category names.

        Returns:
            Cache key string.
        """
        return f"manifest:{','.join(sorted(categories))}"

    @staticmethod
    def tools_key(category: str) -> str:
        """Generate cache key for category tools.

        Args:
            category: Category name.

        Returns:
            Cache key string.
        """
        return f"tools:{category}"

    @staticmethod
    def description_key(category: str, tool: str) -> str:
        """Generate cache key for tool description.

        Args:
            category: Category name.
            tool: Tool name.

        Returns:
            Cache key string.
        """
        return f"description:{category}:{tool}"

    @staticmethod
    def schema_key(tool_name: str, version: Optional[str] = None) -> str:
        """Generate cache key for tool schema.

        Args:
            tool_name: Name of the tool.
            version: Optional version string for schema versioning.

        Returns:
            Cache key string.
        """
        if version:
            return f"schema:{tool_name}:{version}"
        return f"schema:{tool_name}"


# =============================================================================
# CACHED WRAPPERS - Wrap tool_categories functions with caching
# =============================================================================

# Global cache instance (1 hour TTL by default)
tool_cache = ToolCache(max_size=100, ttl=3600.0)


def cached_build_category_manifest(
    categories: list,
    cache: Optional[ToolCache] = None,
) -> str:
    """Cached version of build_category_manifest.

    Args:
        categories: List of category names.
        cache: Optional cache instance (defaults to global).

    Returns:
        Category manifest string.
    """
    from packages.orchestration.tool_categories import build_category_manifest

    if cache is None:
        cache = tool_cache

    # Use tuple for hashable key
    categories_tuple = tuple(sorted(categories))
    key = CacheKeys.manifest_key(categories_tuple)

    return cache.get_or_compute(key, lambda: build_category_manifest(categories))


def cached_get_tools_for_category(
    category: str,
    cache: Optional[ToolCache] = None,
) -> list:
    """Cached version of get_tools_for_category.

    Args:
        category: Category name.
        cache: Optional cache instance (defaults to global).

    Returns:
        List of tool names in the category.
    """
    from packages.orchestration.tool_categories import get_tools_for_category

    if cache is None:
        cache = tool_cache

    key = CacheKeys.tools_key(category)

    return cache.get_or_compute(key, lambda: get_tools_for_category(category))


def cached_get_tool_description(
    category: str,
    tool: str,
    cache: Optional[ToolCache] = None,
) -> Optional[str]:
    """Cached version of get_tool_description.

    Args:
        category: Category name.
        tool: Tool name.
        cache: Optional cache instance (defaults to global).

    Returns:
        Tool description or None.
    """
    from packages.orchestration.tool_categories import get_tool_description

    if cache is None:
        cache = tool_cache

    key = CacheKeys.description_key(category, tool)

    return cache.get_or_compute(key, lambda: get_tool_description(category, tool))


def cached_get_tool_schema(
    tool_name: str,
    version: Optional[str] = None,
    cache: Optional[ToolCache] = None,
) -> Optional[Dict[str, Any]]:
    """Cached version of get_tool_schema from tool_registry.

    Args:
        tool_name: Name of the tool.
        version: Optional version string for schema versioning.
        cache: Optional cache instance (defaults to global).

    Returns:
        Tool schema dict or None if not found.
    """
    # Import lazily to avoid circular imports
    try:
        from packages.orchestration.agent_framework.src.tool_registry import (
            ToolRegistry,
        )

        # Get global registry instance
        registry = ToolRegistry.get_global_instance()

        if cache is None:
            cache = tool_cache

        key = CacheKeys.schema_key(tool_name, version)

        # Compute function that retrieves schema from registry
        def compute_schema() -> Optional[Dict[str, Any]]:
            return registry.get_tool_schema(tool_name) if registry else None

        return cache.get_or_compute(key, compute_schema)
    except ImportError:
        # Fallback if tool_registry not available
        return None


# =============================================================================
# CACHE MANAGEMENT - Invalidation and clearing
# =============================================================================


def invalidate_category(category: str, cache: Optional[ToolCache] = None) -> int:
    """Invalidate all cache entries for a category.

    Args:
        category: Category name to invalidate.
        cache: Optional cache instance (defaults to global).

    Returns:
        Number of entries invalidated.
    """
    if cache is None:
        cache = tool_cache

    # Invalidate tools and descriptions for this category
    pattern = f"(^|;)tools:{category}(;|$)|(^|;)description:{category}:"
    return cache.invalidate(pattern)


def invalidate_manifests(cache: Optional[ToolCache] = None) -> int:
    """Invalidate all category manifest cache entries.

    Args:
        cache: Optional cache instance (defaults to global).

    Returns:
        Number of entries invalidated.
    """
    if cache is None:
        cache = tool_cache

    return cache.invalidate("^manifest:")


def invalidate_schema(
    tool_name: Optional[str] = None,
    version: Optional[str] = None,
    cache: Optional[ToolCache] = None,
) -> int:
    """Invalidate schema cache entries.

    Args:
        tool_name: Specific tool name to invalidate (optional).
        version: Version to invalidate (requires tool_name).
        cache: Optional cache instance (defaults to global).

    Returns:
        Number of entries invalidated.
    """
    if cache is None:
        cache = tool_cache

    if tool_name:
        # Invalidate specific tool schema
        key = CacheKeys.schema_key(tool_name, version)
        if key in cache._cache:
            del cache._cache[key]
            return 1
        return 0
    else:
        # Invalidate all schema entries
        return cache.invalidate("^schema:")


def clear_tool_cache(cache: Optional[ToolCache] = None) -> Dict[str, Any]:
    """Clear the tool cache and return stats.

    Args:
        cache: Optional cache instance (defaults to global).

    Returns:
        Statistics before clearing.
    """
    if cache is None:
        cache = tool_cache

    stats = cache.get_stats()
    cache.clear()
    return stats


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    import unittest

    class TestToolCache(unittest.TestCase):
        """Unit tests for ToolCache."""

        def test_basic_get_set(self):
            """Test basic get/set operations."""
            cache = ToolCache(max_size=3)

            # First call should miss and compute
            result = cache.get_or_compute("key1", lambda: "value1")
            self.assertEqual(result, "value1")
            self.assertEqual(cache.cache_size, 1)
            self.assertEqual(cache.hit_rate, 0.0)  # First call is always a miss

            # Second call should hit
            result = cache.get_or_compute("key1", lambda: "value1")
            self.assertEqual(result, "value1")
            self.assertEqual(cache._hits, 1)
            self.assertEqual(cache.hit_rate, 0.5)

        def test_lru_eviction(self):
            """Test LRU eviction when max_size exceeded."""
            cache = ToolCache(max_size=2)

            cache.get_or_compute("key1", lambda: "value1")
            cache.get_or_compute("key2", lambda: "value2")

            # Access key1 to make it most recently used
            cache.get_or_compute("key1", lambda: "value1")

            # Add third key - key2 should be evicted
            cache.get_or_compute("key3", lambda: "value3")

            # key1 and key3 should exist, key2 should be gone
            self.assertEqual(cache.cache_size, 2)

            # key2 should now be a miss
            result = cache.get_or_compute("key2", lambda: "new_value2")
            self.assertEqual(result, "new_value2")

        def test_ttl_expiration(self):
            """Test TTL expiration of cache entries."""
            cache = ToolCache(max_size=10, ttl=0.1)  # 100ms TTL

            # First call - always a miss (computes value)
            result = cache.get_or_compute("key1", lambda: "value1")
            self.assertEqual(result, "value1")
            self.assertEqual(cache._hits, 0)  # First call is always a miss

            # Wait for expiration
            time.sleep(0.15)

            # Should be a miss now (entry expired)
            result = cache.get_or_compute("key1", lambda: "new_value")
            self.assertEqual(result, "new_value")
            self.assertEqual(cache._hits, 0)  # Still no hits
            self.assertEqual(
                cache._misses, 3
            )  # Three misses: initial + expired + compute

        def test_thread_safety(self):
            """Test thread-safe operations."""
            cache = ToolCache(max_size=100)
            results = []

            def worker(thread_id: int):
                for i in range(50):
                    key = f"key_{i % 10}"  # Some keys repeated
                    result = cache.get_or_compute(key, lambda k=key: f"value_{k}")
                    results.append((thread_id, key, result))

            # Run 4 threads
            threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # No exceptions means thread safety passed
            self.assertEqual(len(results), 200)

        def test_invalidate_pattern(self):
            """Test pattern-based invalidation."""
            cache = ToolCache(max_size=10)

            cache.get_or_compute("manifest:exec", lambda: "m1")
            cache.get_or_compute("tools:exec", lambda: "t1")
            cache.get_or_compute("tools:search", lambda: "t2")
            cache.get_or_compute("description:exec:read", lambda: "d1")

            self.assertEqual(cache.cache_size, 4)

            # Invalidate all tools entries
            count = cache.invalidate("^tools:")
            self.assertEqual(count, 2)
            self.assertEqual(cache.cache_size, 2)

            # Invalidate using regex with alternatives
            count = cache.invalidate("manifest:|description:")
            self.assertEqual(count, 2)
            self.assertEqual(cache.cache_size, 0)

        def test_clear(self):
            """Test clear operation."""
            cache = ToolCache(max_size=10)

            cache.get_or_compute("key1", lambda: "value1")
            cache.get_or_compute("key1", lambda: "value1")  # Second call hits
            cache.get_or_compute("key2", lambda: "value2")

            self.assertEqual(cache._hits, 1)  # One hit after second get

            cache.clear()

            self.assertEqual(cache.cache_size, 0)
            self.assertEqual(cache._hits, 0)
            self.assertEqual(cache._misses, 0)

        def test_cache_keys(self):
            """Test cache key generation."""
            # Test manifest key
            key = CacheKeys.manifest_key(("EXECUTION", "SEARCH"))
            self.assertEqual(key, "manifest:EXECUTION,SEARCH")

            # Test tools key
            key = CacheKeys.tools_key("EXECUTION")
            self.assertEqual(key, "tools:EXECUTION")

            # Test description key
            key = CacheKeys.description_key("EXECUTION", "read_file")
            self.assertEqual(key, "description:EXECUTION:read_file")

            # Test schema key without version
            key = CacheKeys.schema_key("read_file")
            self.assertEqual(key, "schema:read_file")

            # Test schema key with version
            key = CacheKeys.schema_key("read_file", version="v2")
            self.assertEqual(key, "schema:read_file:v2")

        def test_get_stats(self):
            """Test statistics retrieval."""
            cache = ToolCache(max_size=10)

            cache.get_or_compute("key1", lambda: "value1")
            cache.get_or_compute("key1", lambda: "value1")
            cache.get_or_compute("key2", lambda: "value2")

            stats = cache.get_stats()

            self.assertEqual(stats["cache_size"], 2)
            self.assertEqual(stats["hits"], 1)
            self.assertEqual(stats["misses"], 2)
            self.assertAlmostEqual(stats["hit_rate"], 1 / 3)
            self.assertAlmostEqual(stats["miss_rate"], 2 / 3)
            self.assertEqual(stats["max_size"], 10)
            self.assertIsNone(stats["ttl"])

    # Run tests
    unittest.main(verbosity=2)
