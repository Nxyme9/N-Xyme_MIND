#!/usr/bin/env python3
"""
DataProvider - Unified Data Layer for N-Xyme MIND Dashboard

Implements T1.1 from dashboard-v2-plan.md:
- T1.1.1: Sync fetchers (no async - too risky)
- T1.1.2: TTL cache (30s default, thread-safe)
- T1.1.3: Error handling with fallback values
- T1.1.4: PID lock to prevent duplicate dashboard
- T1.1.5: Backward compatible wrapper for get_system_stats()
"""

import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional
import logging

logger = logging.getLogger(__name__)

# ─── PID Lock ───────────────────────────────────────────────────────────────────


class PIDLock:
    """Prevent duplicate dashboard instances."""

    LOCK_FILE = "/tmp/nxyme-dashboard.pid"

    @classmethod
    def acquire(cls) -> bool:
        """Acquire lock. Returns True if acquired, False if already running."""
        try:
            # Check if lock file exists and process is alive
            lock_path = Path(cls.LOCK_FILE)
            if lock_path.exists():
                try:
                    pid = int(lock_path.read_text().strip())
                    # Check if process exists
                    os.kill(pid, 0)
                    logger.warning(f"Dashboard already running with PID {pid}")
                    return False
                except (ValueError, ProcessLookupError):
                    # Stale lock file, remove it
                    lock_path.unlink()

            # Write our PID
            lock_path.write_text(str(os.getpid()))
            return True
        except Exception as e:
            logger.warning(f"Failed to acquire PID lock: {e}")
            return True  # Allow running if lock fails

    @classmethod
    def release(cls) -> None:
        """Release lock on exit."""
        try:
            Path(cls.LOCK_FILE).unlink(missing_ok=True)
        except Exception:
            pass


# ─── TTL Cache ─────────────────────────────────────────────────────────────────-


class TTLCache:
    """Thread-safe TTL cache with configurable expiration."""

    def __init__(self, default_ttl: float = 30.0):
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Get value if exists and not expired."""
        with self._lock:
            if key in self._cache:
                value, expires_at = self._cache[key]
                if time.time() < expires_at:
                    return value
                # Expired - remove
                del self._cache[key]
            return None

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value with TTL."""
        with self._lock:
            ttl = ttl or self._default_ttl
            self._cache[key] = (value, time.time() + ttl)

    def invalidate(self, key: str) -> None:
        """Remove specific key."""
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cache."""
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            now = time.time()
            valid = sum(1 for _, exp in self._cache.values() if now < exp)
            return {"total": len(self._cache), "valid": valid}


# ─── Fallback Values ───────────────────────────────────────────────────────────


# Default fallback values for all data sources
FALLBACK_VALUES = {
    "daemon_running": False,
    "daemon_pid": None,
    "ollama_running": False,
    "memory_sources": 0,
    "memory_enabled": 0,
    "indexed_files": 0,
    "indexed_chunks": 0,
    "router_backends": 0,
    "orchestration_agents": 0,
    "learning_feedback": 0,
    "learning_queries": 0,
    "learning_top_queries": [],
    "preferences": 0,
    "outcomes": 0,
}


# ─── Data Provider ──────────────────────────────────────────────────────────────


class DataProvider:
    """
    Unified data layer for dashboard - wraps all data sources with:
    - Sync fetchers (no async - per T1.1.1 decision)
    - TTL cache (30s default)
    - Error handling with fallbacks
    - Thread-safe operations
    """

    def __init__(self, cache_ttl: float = 30.0):
        self._cache = TTLCache(default_ttl=cache_ttl)
        self._fetchers: dict[str, Callable[[], Any]] = {}
        self._register_default_fetchers()

    def _register_default_fetchers(self) -> None:
        """Register all default data fetchers."""

        # Daemon status - using subprocess
        self._fetchers["daemon"] = self._fetch_daemon_status

        # Ollama status - HTTP check
        self._fetchers["ollama"] = self._fetch_ollama_status

        # Memory stats - from mcp_server
        self._fetchers["memory"] = self._fetch_memory_stats

        # Indexed files - from drive_embedder
        self._fetchers["indexed"] = self._fetch_indexed_count

        # Router backends - from memory_router
        self._fetchers["router"] = self._fetch_router_status

        # Orchestration agents - from agent_card_registry
        self._fetchers["orchestration"] = self._fetch_orchestration_status

        # Learning stats - from mcp_server
        self._fetchers["learning"] = self._fetch_learning_stats

        # Preferences - from memory stats
        self._fetchers["preferences"] = self._fetch_preferences

        # Outcomes - from outcomes.jsonl
        self._fetchers["outcomes"] = self._fetch_outcomes

    def _fetch_daemon_status(self) -> dict:
        """Fetch daemon running status."""
        try:
            r = subprocess.run(
                ["pgrep", "-f", "src.memory.daemon"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            running = r.returncode == 0 and r.stdout.strip()
            pid_str = r.stdout.strip().split("\n")[0] if running else "N/A"
            try:
                pid_val = int(pid_str) if pid_str != "N/A" else None
            except (ValueError, TypeError):
                pid_val = None
            return {
                "daemon_running": bool(running),
                "daemon_pid": pid_val,
            }
        except Exception as e:
            logger.debug(f"Daemon status fetch failed: {e}")
            return {"daemon_running": False, "daemon_pid": None}

    def _fetch_ollama_status(self) -> dict:
        """Fetch Ollama running status."""
        try:
            import urllib.request

            urllib.request.urlopen("http://localhost:11434", timeout=2)
            return {"ollama_running": True}
        except Exception:
            return {"ollama_running": False}

    def _fetch_memory_stats(self) -> dict:
        """Fetch memory system stats."""
        try:
            from src.memory.mcp_server import get_memory_stats as _gs

            m = _gs()
            file_reg = m.get("file_registry", {})
            return {
                "memory_sources": len(file_reg),
                "memory_enabled": m.get("learning_events", 0),
            }
        except Exception as e:
            logger.debug(f"Memory stats fetch failed: {e}")
            return {"memory_sources": 0, "memory_enabled": 0}

    def _fetch_indexed_count(self) -> dict:
        """Fetch indexed files/chunks count."""
        try:
            from src.memory.drive_embedder import get_indexed_count as _gc

            i = _gc()
            return {
                "indexed_files": i.get("total_files", 0),
                "indexed_chunks": i.get("total_chunks", 0),
            }
        except Exception as e:
            logger.debug(f"Indexed count fetch failed: {e}")
            return {"indexed_files": 0, "indexed_chunks": 0}

    def _fetch_router_status(self) -> dict:
        """Fetch router backends count."""
        try:
            from src.memory.memory_router import get_router

            return {"router_backends": len(get_router().backends)}
        except Exception as e:
            logger.debug(f"Router status fetch failed: {e}")
            return {"router_backends": 0}

    def _fetch_orchestration_status(self) -> dict:
        """Fetch orchestration agent count."""
        try:
            from src.orchestration.agent_card_registry import get_agent_registry

            return {"orchestration_agents": len(get_agent_registry().get_all_agents())}
        except Exception as e:
            logger.debug(f"Orchestration status fetch failed: {e}")
            return {"orchestration_agents": 0}

    def _fetch_learning_stats(self) -> dict:
        """Fetch learning system stats."""
        try:
            from src.memory.mcp_server import get_learning_stats as _gs

            l = _gs()
            return {
                "learning_feedback": l.get("total_feedback", 0),
                "learning_queries": l.get("unique_queries", 0),
                "learning_top_queries": l.get("top_queries", []),
            }
        except Exception as e:
            logger.debug(f"Learning stats fetch failed: {e}")
            return {
                "learning_feedback": 0,
                "learning_queries": 0,
                "learning_top_queries": [],
            }

    def _fetch_preferences(self) -> dict:
        """Fetch user preferences count."""
        try:
            from src.memory.mcp_server import get_memory_stats as _ms

            m = _ms()
            return {
                "preferences": m.get("file_registry", {}).get("user_preferences", 0)
            }
        except Exception as e:
            logger.debug(f"Preferences fetch failed: {e}")
            return {"preferences": 0}

    def _fetch_outcomes(self) -> dict:
        """Fetch delegation outcomes count."""
        try:
            p = Path(".sisyphus/outcomes.jsonl")
            return {"outcomes": len(p.read_text().splitlines()) if p.exists() else 0}
        except Exception as e:
            logger.debug(f"Outcomes fetch failed: {e}")
            return {"outcomes": 0}

    # ─── Public API ───────────────────────────────────────────────────────────

    def get(
        self, category: str, use_cache: bool = True, ttl: Optional[float] = None
    ) -> dict:
        """
        Get data for a specific category.

        Args:
            category: Data category (daemon, ollama, memory, indexed, router,
                     orchestration, learning, preferences, outcomes)
            use_cache: Whether to use cache (default True)
            ttl: Optional TTL override for this call

        Returns:
            Dictionary with ONLY the keys belonging to that category (no fallbacks here)
        """
        cache_key = f"data_{category}"

        # Try cache first
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        # Fetch fresh data - just return what the fetcher provides
        if category in self._fetchers:
            try:
                data = self._fetchers[category]()
            except Exception as e:
                logger.warning(f"Fetcher for {category} raised: {e}")
                data = {}
        else:
            data = {}

        # Cache result (store ONLY the category data, not fallbacks)
        if use_cache:
            self._cache.set(cache_key, data, ttl)

        return data  # Return just the category data, no fallbacks

    def get_all(self, use_cache: bool = True) -> dict:
        """Get all data sources at once (batch fetch)."""
        result = {}
        for category in self._fetchers.keys():
            cat_data = self.get(category, use_cache=use_cache)
            result.update(cat_data)

        # Apply fallbacks for any keys that are still missing
        for key, fallback in FALLBACK_VALUES.items():
            if key not in result:
                result[key] = fallback

        return result

    def invalidate(self, category: Optional[str] = None) -> None:
        """Invalidate cache for specific category or all."""
        if category:
            self._cache.invalidate(f"data_{category}")
        else:
            self._cache.clear()

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return self._cache.get_stats()


# ─── Singleton Instance ───────────────────────────────────────────────────────


# Global DataProvider instance
_data_provider: Optional[DataProvider] = None


def get_data_provider() -> DataProvider:
    """Get or create global DataProvider instance."""
    global _data_provider
    if _data_provider is None:
        _data_provider = DataProvider()
    return _data_provider


# ─── Backward Compatibility Wrapper ───────────────────────────────────────────


def get_system_stats() -> dict:
    """
    Backward compatible wrapper for get_system_stats().

    Uses DataProvider with caching for efficiency while maintaining
    the same interface as the original function.
    """
    # Check PID lock first
    if not PIDLock.acquire():
        logger.warning("Another dashboard instance is running")
        # Still return data but log warning

    try:
        provider = get_data_provider()
        # Use cache for backward compat calls (30s TTL)
        return provider.get_all(use_cache=True)
    finally:
        # Note: We don't release the PID lock here because we want it
        # to persist for the lifetime of the dashboard process
        pass


def refresh_stats() -> dict:
    """Force refresh stats (bypass cache)."""
    provider = get_data_provider()
    provider.invalidate()  # Clear all cache
    return provider.get_all(use_cache=False)
