"""
Caching Layer for N-Xyme_MIND
=============================
TTL/LRU caching utilities based on leaked Anthropic source code patterns.

Reference: /home/nxyme/Documentos/CODE/source_code/ant-source-code-main/utils/memoize.ts

Features:
- memoizeWithTTL: Time-to-live with background refresh
- memoizeWithLRU: LRU eviction policy
- FileReadCache: File contents with mtime invalidation
- cache_decorator: Decorator utilities
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    Callable,
    Generic,
    TypeVar,
    Protocol,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")
TResult = TypeVar("TResult")
TArgs = TypeVar("TArgs")
TKey = TypeVar("TKey")


class CacheProtocol(Protocol):
    """Protocol for cache objects."""

    def clear(self) -> None: ...
    def size(self) -> int: ...

    def delete(self, key: str) -> bool: ...
    def get(self, key: str) -> Any | None: ...
    def has(self, key: str) -> bool: ...

    def peek(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any) -> None: ...

    def __contains__(self, key: object) -> bool: ...
    def __len__(self) -> int: ...


# =============================================================================
# TTL Cache Implementation
# =============================================================================


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with timestamp and refresh state."""

    value: T
    timestamp: float
    refreshing: bool = False


class TTLmemoize(Generic[TArgs, TResult]):
    """
    Memoization decorator with TTL and optional background refresh.

    Implements write-through cache pattern:
    - If cache is fresh → return immediately
    - If cache is stale → return stale value but refresh in background
    - If no cache exists → block and compute the value

    Args:
        func: Function to memoize
        ttl_ms: Time-to-live in milliseconds (default: 5 minutes)
        background_refresh: Enable background refresh on stale (default: True)
        thread_safe: Enable thread safety (default: True)
    """

    def __init__(
        self,
        func: Callable[[*TArgs], TResult],
        ttl_ms: float = 5 * 60 * 1000,
        background_refresh: bool = True,
        thread_safe: bool = True,
    ):
        self._func = func
        self._ttl_ms = ttl_ms / 1000.0  # Convert to seconds
        self._background_refresh = background_refresh
        self._thread_safe = thread_safe
        self._cache: dict[str, CacheEntry[TResult]] = {}
        self._lock = threading.RLock() if thread_safe else None
        self._in_flight: dict[str, asyncio.Future[TResult]] = {}

        # Support both sync and async invocation
        self._is_async = asyncio.iscoroutinefunction(func)

    def _get_lock(self) -> threading.Lock | None:
        return self._lock

    def _acquire(self) -> None:
        if self._lock:
            self._lock.acquire()

    def _release(self) -> None:
        if self._lock:
            self._lock.release()

    def _make_key(self, args: tuple[Any, ...]) -> str:
        """Generate cache key from arguments."""
        try:
            arg_str = str(args)
            return hashlib.md5(arg_str.encode()).hexdigest()
        except (TypeError, ValueError):
            # Unhashable args - use id
            return str(id(args))

    def _now(self) -> float:
        """Current timestamp."""
        return time.time()

    def _is_stale(self, entry: CacheEntry[TResult]) -> bool:
        """Check if cache entry is stale."""
        return (self._now() - entry.timestamp) > self._ttl_ms

    def __call__(self, *args: TArgs, **kwargs: Any) -> TResult:
        """Execute memoized function."""
        key = self._make_key(args)
        cached = self._cache.get(key)
        now = self._now()

        if self._thread_safe:
            self._acquire()
            try:
                cached = self._cache.get(key)
            finally:
                self._release()

        # Cold miss - compute immediately
        if cached is None:
            value = self._func(*args, **kwargs)
            entry = CacheEntry(value=value, timestamp=now, refreshing=False)

            if self._thread_safe:
                self._acquire()
                try:
                    # Identity guard: check if clear() was called during computation
                    if key in self._cache:
                        return cached.value if cached else value
                    self._cache[key] = entry
                finally:
                    self._release()
            else:
                self._cache[key] = entry

            return value

        # Stale entry - background refresh
        if self._is_stale(cached) and not cached.refreshing:
            if self._background_refresh:
                # Mark as refreshing to prevent duplicate refreshes
                cached.refreshing = True

                # Schedule background refresh (non-blocking)
                stale_entry = cached

                def _refresh():
                    try:
                        new_value = self._func(*args, **kwargs)
                        if self._thread_safe:
                            self._acquire()
                            try:
                                if self._cache.get(key) is stale_entry:
                                    self._cache[key] = CacheEntry(
                                        new_value, self._now(), False
                                    )
                            finally:
                                self._release()
                        else:
                            current = self._cache.get(key)
                            if current is stale_entry:
                                self._cache[key] = CacheEntry(
                                    new_value, self._now(), False
                                )
                    except Exception as e:
                        logger.error(f"Background refresh failed: {e}")
                        if self._thread_safe:
                            self._acquire()
                            try:
                                if self._cache.get(key) is stale_entry:
                                    self._cache.pop(key, None)
                            finally:
                                self._release()
                        else:
                            current = self._cache.get(key)
                            if current is stale_entry:
                                self._cache.pop(key, None)

                # Non-blocking execution
                if threading.current_thread().name == "MainThread":
                    thread = threading.Thread(target=_refresh, daemon=True)
                    thread.start()
                else:
                    # Already in background - execute directly
                    _refresh()

            # Return stale value immediately
            return cached.value

        # Fresh or already refreshing - return cached value
        return cached.value

    def clear(self) -> None:
        """Clear all cache entries."""
        if self._thread_safe:
            self._acquire()
            try:
                self._cache.clear()
                self._in_flight.clear()
            finally:
                self._release()
        else:
            self._cache.clear()
            self._in_flight.clear()

    @property
    def cache(self) -> CacheProtocol:
        """Cache interface for external management."""
        return _TTLCacheAdapter(self)


class _TTLCacheAdapter:
    """Adapter to expose TTLmemoize as cache protocol."""

    def __init__(self, memo: TTLmemoize):
        self._memo = memo

    def clear(self) -> None:
        self._memo.clear()

    def size(self) -> int:
        return len(self._memo._cache)

    def delete(self, key: str) -> bool:
        return self._memo._cache.pop(key, None) is not None

    def get(self, key: str) -> Any | None:
        return self._memo._cache.get(key, None) if key in self._memo._cache else None

    def has(self, key: str) -> bool:
        return key in self._memo._cache

    def peek(self, key: str) -> Any | None:
        entry = self._memo._cache.get(key)
        return entry.value if entry else None

    def set(self, key: str, value: Any) -> None:
        self._memo._cache[key] = CacheEntry(value, self._memo._now(), False)

    def __contains__(self, key: object) -> bool:
        return str(key) in self._memo._cache

    def __len__(self) -> int:
        return len(self._memo._cache)


# =============================================================================
# LRU Cache Implementation
# =============================================================================


class LRUCache(Generic[TKey, TResult]):
    """
    LRU (Least Recently Used) cache with eviction.

    Prevents unbounded memory growth by evicting least recently used
    entries when cache reaches max size.

    Args:
        maxsize: Maximum number of entries (default: 100)
    """

    def __init__(self, maxsize: int = 100):
        self._maxsize = maxsize
        self._cache: OrderedDict[TKey, TResult] = OrderedDict()
        self._lock = threading.RLock()

    def _move_to_end(self, key: TKey) -> None:
        """Move key to end (most recently used)."""
        if key in self._cache:
            self._cache.move_to_end(key)

    def get(self, key: TKey, default: TResult | None = None) -> TResult | None:
        """Get value, updating recency."""
        with self._lock:
            if key in self._cache:
                self._move_to_end(key)
                return self._cache[key]
            return default

    def peek(self, key: TKey, default: TResult | None = None) -> TResult | None:
        """Get value without updating recency."""
        with self._lock:
            return self._cache.get(key, default)

    def set(self, key: TKey, value: TResult) -> None:
        """Set value, evicting if necessary."""
        with self._lock:
            if key in self._cache:
                self._move_to_end(key)
                self._cache[key] = value
                return

            # Evict oldest if at capacity
            if len(self._cache) >= self._maxsize:
                oldest = next(iter(self._cache))
                del self._cache[oldest]

            self._cache[key] = value

    def delete(self, key: TKey) -> bool:
        """Delete key, return True if existed."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def has(self, key: TKey) -> bool:
        """Check if key exists."""
        with self._lock:
            return key in self._cache

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._cache.clear()

    @property
    def size(self) -> int:
        """Current cache size."""
        with self._lock:
            return len(self._cache)

    @property
    def maxsize(self) -> int:
        """Maximum cache size."""
        return self._maxsize

    def __contains__(self, key: TKey) -> bool:
        return key in self._cache

    def __len__(self) -> int:
        return len(self._cache)

    def __getitem__(self, key: TKey) -> TResult:
        with self._lock:
            return self._cache[key]

    def __setitem__(self, key: TKey, value: TResult) -> None:
        self.set(key, value)

    @property
    def cache(self) -> CacheProtocol:
        """Cache interface for compatibility."""
        return _LRUCacheAdapter(self)


class _LRUCacheAdapter:
    """Adapter to expose LRUCache as cache protocol."""

    def __init__(self, cache: LRUCache):
        self._cache = cache

    def clear(self) -> None:
        self._cache.clear()

    def size(self) -> int:
        return self._cache.size

    def delete(self, key: str) -> bool:
        return self._cache.delete(key)

    def get(self, key: str) -> Any | None:
        return self._cache.get(key)

    def has(self, key: str) -> bool:
        return self._cache.has(key)

    def peek(self, key: str) -> Any | None:
        return self._cache.peek(key)

    def set(self, key: str, value: Any) -> None:
        self._cache.set(key, value)

    def __contains__(self, key: object) -> bool:
        return key in self._cache

    def __len__(self) -> int:
        return len(self._cache)


# =============================================================================
# File Read Cache
# =============================================================================


@dataclass
class FileCacheEntry:
    """File cache entry with metadata."""

    content: str
    mtime: float
    size: int


class FileReadCache:
    """
    Cache for file contents with mtime-based invalidation.

    Caches file contents and automatically invalidates
    when file's modification time changes.

    Args:
        max_size_bytes: Maximum total cache size in bytes (default: 50MB)
    """

    def __init__(self, max_size_bytes: int = 50 * 1024 * 1024):
        self._max_size = max_size_bytes
        self._cache: dict[str, FileCacheEntry] = {}
        self._lock = threading.RLock()

    def _get_mtime(self, path: Path) -> float:
        """Get file modification time."""
        try:
            return path.stat().st_mtime
        except OSError:
            return 0.0

    def _get_size(self, path: Path) -> int:
        """Get file size."""
        try:
            return path.stat().st_size
        except OSError:
            return 0

    def read(self, path: Path | str, encoding: str = "utf-8") -> str:
        """Read file with caching."""
        path = Path(path)
        key = str(path.resolve())

        with self._lock:
            entry = self._cache.get(key)

            # Cache miss or invalid mtime
            if entry is None or entry.mtime != self._get_mtime(path):
                content = path.read_text(encoding=encoding)
                mtime = self._get_mtime(path)
                size = self._get_size(path)

                # Evict if necessary
                self._evict_if_needed(size)

                self._cache[key] = FileCacheEntry(content, mtime, size)
                return content

            return entry.content

    def _evict_if_needed(self, needed_size: int) -> None:
        """Evict oldest entries if over size limit."""
        current_size = sum(e.size for e in self._cache.values())

        while current_size + needed_size > self._max_size and self._cache:
            oldest_key = next(iter(self._cache))
            removed = self._cache.pop(oldest_key, None)
            if removed:
                current_size -= removed.size

    def invalidate(self, path: Path | str) -> None:
        """Invalidate specific file."""
        path = Path(path)
        key = str(path.resolve())

        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear cache."""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Current cache size in bytes."""
        with self._lock:
            return sum(e.size for e in self._cache.values())

    def count(self) -> int:
        """Number of cached files."""
        with self._lock:
            return len(self._cache)


# =============================================================================
# Decorator Utilities
# =============================================================================


def memoize(
    ttl_ms: float = 5 * 60 * 1000,
    background_refresh: bool = True,
) -> Callable[[Callable[..., Any]], TTLmemoize[Any, Any]]:
    """
    Decorator to memoize a function with TTL.

    Args:
        ttl_ms: Time-to-live in milliseconds
        background_refresh: Enable background refresh

    Example:
        @memoize(ttl_ms=60000)
        def expensive_operation(x: int) -> int:
            return x * 2
    """

    def decorator(func: Callable[[*TArgs], TResult]) -> TTLmemoize[TArgs, TResult]:
        return TTLmemoize(func, ttl_ms, background_refresh)

    return decorator


def lru_cache(
    maxsize: int = 100,
) -> Callable[[Callable], Callable]:
    """
    Decorator to memoize with LRU eviction.

    Example:
        @lru_cache(maxsize=50)
        def expensive_operation(x: int) -> int:
            return x * 2
    """
    cache = LRUCache(maxsize=maxsize)

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            if cache.has(key):
                return cache.get(key)
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result

        wrapper.cache = cache  # type: ignore
        return wrapper

    return decorator


def cache_key(*args: Any, **kwargs: Any) -> str:
    """
    Generate cache key from arguments.

    Uses MD5 hash for consistent key generation.
    """
    data = f"{args}:{sorted(kwargs.items())}"
    return hashlib.md5(data.encode()).hexdigest()


# =============================================================================
# Async Variants
# =============================================================================


class TTLmemoizeAsync(Generic[TArgs, TResult]):
    """
    Async version of TTLmemoize with background refresh.

    Supports async functions with proper concurrency handling
    via in-flight request deduplication.
    """

    def __init__(
        self,
        func: Callable[[*TArgs], TResult],
        ttl_ms: float = 5 * 60 * 1000,
        background_refresh: bool = True,
    ):
        self._func = func
        self._ttl_ms = ttl_ms / 1000.0
        self._background_refresh = background_refresh
        self._cache: dict[str, CacheEntry[TResult]] = {}
        self._in_flight: dict[str, asyncio.Future[TResult]] = {}
        self._lock = asyncio.Lock()

    def _make_key(self, args: tuple[Any, ...]) -> str:
        try:
            arg_str = str(args)
            return hashlib.md5(arg_str.encode()).hexdigest()
        except (TypeError, ValueError):
            return str(id(args))

    def _now(self) -> float:
        return time.time()

    async def __call__(self, *args: TArgs, **kwargs: Any) -> TResult:
        key = self._make_key(args)
        cached = self._cache.get(key)
        now = self._now()

        # Cold miss
        if cached is None:
            # Check in-flight
            if key in self._in_flight:
                return await self._in_flight[key]

            # Create promise
            promise = asyncio.create_task(self._func(*args, **kwargs))
            self._in_flight[key] = promise

            try:
                result = await promise
                # Identity guard
                if key in self._in_flight:
                    self._cache[key] = CacheEntry(result, now, False)
                return result
            finally:
                self._in_flight.pop(key, None)

        # Stale - background refresh
        is_stale = (now - cached.timestamp) > self._ttl_ms
        if is_stale and not cached.refreshing and self._background_refresh:
            cached.refreshing = True
            stale_entry = cached

            async def _refresh():
                try:
                    new_value = await self._func(*args, **kwargs)
                    if self._cache.get(key) is stale_entry:
                        self._cache[key] = CacheEntry(new_value, self._now(), False)
                except Exception as e:
                    logger.error(f"Background refresh failed: {e}")
                    if self._cache.get(key) is stale_entry:
                        self._cache.pop(key, None)

            asyncio.create_task(_refresh())
            return cached.value

        return cached.value

    async def clear(self) -> None:
        self._cache.clear()
        self._in_flight.clear()


# =============================================================================
# Export
# =============================================================================

__all__ = [
    "TTLmemoize",
    "TTLmemoizeAsync",
    "LRUCache",
    "FileReadCache",
    "memoize",
    "lru_cache",
    "cache_key",
    "CacheEntry",
    "FileCacheEntry",
]
