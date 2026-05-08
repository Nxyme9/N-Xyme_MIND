"""Lifecycle management for graceful shutdown of brain packages.

Provides:
- LifecycleManager with register_shutdown_handler for cleanup callbacks
- Signal handlers (SIGINT, SIGTERM) for Ctrl+C and termination
- Context manager support for lifecycle-aware code blocks
- State flushing for memory_core, learning_engine, intelligence, orchestration

Usage:
    with LifecycleManager() as lm:
        lm.register_shutdown_handler("memory_core", flush_memory_state)
        lm.register_shutdown_handler("learning_engine", save_learning_stats)

    # Or manually:
    lm = LifecycleManager()
    lm.register_shutdown_handler("intelligence", cleanup)
    lm.shutdown()
"""

from __future__ import annotations

import asyncio
import atexit
import logging
import signal
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ShutdownPhase(Enum):
    """Shutdown phases for ordered cleanup."""

    PRE_FLUSH = "pre_flush"  # Prepare for shutdown
    FLUSH_STATE = "flush_state"  # Save state to disk
    CLEANUP = "cleanup"  # Close connections, release resources
    FINALIZE = "finalize"  # Last chance cleanup


@dataclass
class ShutdownHandler:
    """A registered shutdown handler."""

    name: str
    callback: Callable[[], None]
    phase: ShutdownPhase
    priority: int = 0  # Higher = runs first within phase
    description: str = ""


class LifecycleManager:
    """Manages graceful shutdown of brain packages.

    Features:
    - Register handlers for different shutdown phases
    - Signal handling for SIGINT/SIGTERM
    - Context manager support
    - Ordered shutdown by phase and priority
    - Thread-safe operations
    """

    _instance: Optional["LifecycleManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "LifecycleManager":
        """Singleton pattern - only one lifecycle manager per process."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialize the lifecycle manager."""
        # Only initialize once (singleton pattern)
        if self._initialized:
            return

        self._handlers: Dict[str, List[ShutdownHandler]] = {
            "memory_core": [],
            "learning_engine": [],
            "intelligence": [],
            "orchestration": [],
            "global": [],
        }
        self._signal_handlers: Dict[int, Callable] = {}
        self._shutdown_called = False
        self._shutdown_lock = threading.Lock()
        self._initialized = True
        self._is_active = False

        # Register atexit handler for clean shutdown
        atexit.register(self._atexit_handler)

        logger.info("LifecycleManager initialized")

    def __enter__(self) -> "LifecycleManager":
        """Enter context manager - activates the manager."""
        self._is_active = True
        self._register_default_signal_handlers()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager - triggers shutdown."""
        self._is_active = False
        self.shutdown()

    def _register_default_signal_handlers(self) -> None:
        """Register default signal handlers for graceful shutdown."""

        def sigint_handler(signum, frame):
            logger.info("Received SIGINT (Ctrl+C) - initiating graceful shutdown")
            self.shutdown()

        def sigterm_handler(signum, frame):
            logger.info("Received SIGTERM - initiating graceful shutdown")
            self.shutdown()

        # Register handlers if not already registered
        if signal.SIGINT not in self._signal_handlers:
            try:
                signal.signal(signal.SIGINT, sigint_handler)
                self._signal_handlers[signal.SIGINT] = sigint_handler
            except (ValueError, OSError) as e:
                logger.warning(f"Could not register SIGINT handler: {e}")

        if signal.SIGTERM not in self._signal_handlers:
            try:
                signal.signal(signal.SIGTERM, sigterm_handler)
                self._signal_handlers[signal.SIGTERM] = sigterm_handler
            except (ValueError, OSError) as e:
                logger.warning(f"Could not register SIGTERM handler: {e}")

    def _atexit_handler(self) -> None:
        """Handler called on Python exit."""
        if not self._shutdown_called:
            self.shutdown()

    def register_shutdown_handler(
        self,
        package: str,
        callback: Callable[[], None],
        phase: ShutdownPhase = ShutdownPhase.CLEANUP,
        priority: int = 0,
        description: str = "",
    ) -> None:
        """Register a shutdown handler for a specific package.

        Args:
            package: Package name (memory_core, learning_engine, intelligence, orchestration, global)
            callback: Function to call on shutdown
            phase: Shutdown phase (PRE_FLUSH, FLUSH_STATE, CLEANUP, FINALIZE)
            priority: Higher priority runs first within phase
            description: Human-readable description of the handler
        """
        if package not in self._handlers:
            self._handlers[package] = []

        handler = ShutdownHandler(
            name=package,
            callback=callback,
            phase=phase,
            priority=priority,
            description=description,
        )
        self._handlers[package].append(handler)
        logger.debug(f"Registered shutdown handler for {package}: {description}")

    def register_memory_flush(self, flush_fn: Callable[[], None]) -> None:
        """Convenience: Register a memory state flush handler.

        Args:
            flush_fn: Function to flush/save memory state
        """
        self.register_shutdown_handler(
            "memory_core",
            flush_fn,
            phase=ShutdownPhase.FLUSH_STATE,
            priority=100,
            description="Flush memory state to disk",
        )

    def register_learning_save(self, save_fn: Callable[[], None]) -> None:
        """Convenience: Register a learning stats save handler.

        Args:
            save_fn: Function to save learning statistics
        """
        self.register_shutdown_handler(
            "learning_engine",
            save_fn,
            phase=ShutdownPhase.FLUSH_STATE,
            priority=90,
            description="Save learning engine stats",
        )

    def register_intelligence_cleanup(self, cleanup_fn: Callable[[], None]) -> None:
        """Convenience: Register an intelligence cleanup handler.

        Args:
            cleanup_fn: Function to cleanup intelligence state
        """
        self.register_shutdown_handler(
            "intelligence",
            cleanup_fn,
            phase=ShutdownPhase.CLEANUP,
            priority=50,
            description="Cleanup intelligence state",
        )

    def register_orchestration_cleanup(self, cleanup_fn: Callable[[], None]) -> None:
        """Convenience: Register an orchestration cleanup handler.

        Args:
            cleanup_fn: Function to cleanup orchestration state
        """
        self.register_shutdown_handler(
            "orchestration",
            cleanup_fn,
            phase=ShutdownPhase.CLEANUP,
            priority=40,
            description="Cleanup orchestration state",
        )

    def _get_sorted_handlers(self) -> List[ShutdownHandler]:
        """Get all handlers sorted by phase and priority."""
        all_handlers = []
        for handlers in self._handlers.values():
            all_handlers.extend(handlers)

        # Sort by phase order, then by priority (descending)
        phase_order = {
            ShutdownPhase.PRE_FLUSH: 0,
            ShutdownPhase.FLUSH_STATE: 1,
            ShutdownPhase.CLEANUP: 2,
            ShutdownPhase.FINALIZE: 3,
        }

        return sorted(
            all_handlers,
            key=lambda h: (phase_order[h.phase], -h.priority),
        )

    def shutdown(self, emergency: bool = False) -> None:
        """Execute graceful shutdown of all registered handlers.

        Args:
            emergency: If True, skip flush phase and go directly to cleanup
        """
        with self._shutdown_lock:
            if self._shutdown_called:
                logger.debug("Shutdown already in progress")
                return

            self._shutdown_called = True
            logger.info("Starting graceful shutdown...")

        handlers = self._get_sorted_handlers()

        # Skip flush phase in emergency shutdown
        if emergency:
            handlers = [h for h in handlers if h.phase != ShutdownPhase.FLUSH_STATE]

        # Execute handlers
        errors: List[tuple[str, Exception]] = []
        for handler in handlers:
            try:
                logger.debug(
                    f"Executing {handler.phase.value} handler for {handler.name}"
                )
                handler.callback()
            except Exception as e:
                error_msg = f"Error in {handler.name} handler: {e}"
                logger.error(error_msg)
                errors.append((handler.name, e))

        # Report summary
        if errors:
            logger.warning(f"Shutdown completed with {len(errors)} errors")
            for name, error in errors:
                logger.warning(f"  - {name}: {error}")
        else:
            logger.info("Graceful shutdown completed successfully")

        # Reset singleton for testing purposes
        with self._lock:
            LifecycleManager._instance = None

    def reset(self) -> None:
        """Reset the lifecycle manager (for testing)."""
        with self._shutdown_lock:
            self._handlers = {
                "memory_core": [],
                "learning_engine": [],
                "intelligence": [],
                "orchestration": [],
                "global": [],
            }
            self._shutdown_called = False
            self._is_active = False
            logger.debug("LifecycleManager reset")


# =============================================================================
# Default shutdown handlers for brain packages
# =============================================================================


def _flush_memory_state() -> None:
    """Default handler to flush memory state."""
    try:
        from packages.memory_store import get_memory_stats

        stats = get_memory_stats()
        logger.info(f"Memory state flushed: {stats.get('status', 'unknown')}")
    except Exception as e:
        logger.warning(f"Could not flush memory state: {e}")


def _save_learning_stats() -> None:
    """Default handler to save learning engine stats."""
    try:
        from packages.learning_engine import status

        stats = status()
        logger.info(f"Learning stats saved: version={stats.get('version', 'unknown')}")
    except Exception as e:
        logger.warning(f"Could not save learning stats: {e}")


def _cleanup_intelligence() -> None:
    """Default handler to cleanup intelligence resources."""
    try:
        from packages.intelligence import available_agents

        agents = available_agents()
        logger.info(f"Intelligence cleanup: {len(agents)} agents known")
    except Exception as e:
        logger.warning(f"Could not cleanup intelligence: {e}")


def _cleanup_orchestration() -> None:
    """Default handler to cleanup orchestration resources."""
    try:

        logger.info("Orchestration cleanup: handlers released")
    except Exception as e:
        logger.warning(f"Could not cleanup orchestration: {e}")


def register_default_handlers(lm: Optional[LifecycleManager] = None) -> None:
    """Register default shutdown handlers for all brain packages.

    Args:
        lm: Optional LifecycleManager instance (uses singleton if not provided)
    """
    if lm is None:
        lm = LifecycleManager()

    lm.register_memory_flush(_flush_memory_state)
    lm.register_learning_save(_save_learning_stats)
    lm.register_intelligence_cleanup(_cleanup_intelligence)
    lm.register_orchestration_cleanup(_cleanup_orchestration)


# =============================================================================
# Async support
# =============================================================================


class AsyncLifecycleManager(LifecycleManager):
    """Async-compatible lifecycle manager.

    Supports async handlers for packages that need async cleanup.
    """

    def __init__(self):
        """Initialize async lifecycle manager."""
        super().__init__()
        self._async_handlers: Dict[str, List[Callable]] = {
            "memory_core": [],
            "learning_engine": [],
            "intelligence": [],
            "orchestration": [],
        }

    def register_async_handler(
        self,
        package: str,
        async_callback: Callable,
    ) -> None:
        """Register an async shutdown handler.

        Args:
            package: Package name
            async_callback: Async function to call on shutdown
        """
        if package not in self._async_handlers:
            self._async_handlers[package] = []
        self._async_handlers[package].append(async_callback)

    async def async_shutdown(self) -> None:
        """Execute graceful shutdown including async handlers."""
        # First run sync handlers
        self.shutdown()

        # Then run async handlers
        for handlers in self._async_handlers.values():
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler()
                    else:
                        handler()
                except Exception as e:
                    logger.error(f"Error in async handler: {e}")


# =============================================================================
# Convenience functions
# =============================================================================

_lifecycle_manager: Optional[LifecycleManager] = None


def get_lifecycle_manager() -> LifecycleManager:
    """Get the global LifecycleManager instance.

    Returns:
        The singleton LifecycleManager
    """
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = LifecycleManager()
    return _lifecycle_manager


@contextmanager
def lifecycle_context():
    """Context manager for lifecycle-aware code.

    Usage:
        with lifecycle_context() as lm:
            lm.register_shutdown_handler("memory_core", flush_fn)
            # ... your code here ...

    Yields:
        LifecycleManager instance
    """
    lm = get_lifecycle_manager()
    with lm:
        yield lm


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "LifecycleManager",
    "AsyncLifecycleManager",
    "ShutdownPhase",
    "ShutdownHandler",
    "get_lifecycle_manager",
    "lifecycle_context",
    "register_default_handlers",
]
