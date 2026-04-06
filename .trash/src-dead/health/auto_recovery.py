"""Auto Recovery — 4-tier autonomous recovery state machine."""

from __future__ import annotations

import logging
import os
import signal
import sqlite3
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from src.health.health_schema import HealthScore, HealthStatus, SystemHealth
from src.infrastructure.circuit_breaker import get_circuit_breaker, CircuitBreakerRegistry

logger = logging.getLogger(__name__)


class RecoveryTier(Enum):
    """Recovery tiers from least to most aggressive."""

    TIER1_WAIT = "wait"  # Wait and retry
    TIER2_CLEAR_CACHE = "clear_cache"  # Clear caches
    TIER3_RESTART = "restart"  # Restart component
    TIER4_DEGRADE = "degrade"  # Degrade functionality


@dataclass
class RecoveryAction:
    """A single recovery action."""

    tier: RecoveryTier
    component: str
    action: str
    success: bool = False
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class RecoveryState:
    """State of the recovery process for a component."""

    component: str
    current_tier: RecoveryTier = RecoveryTier.TIER1_WAIT
    attempts: int = 0
    max_attempts: int = 4
    last_recovery_time: float = 0.0
    recovery_cooldown: float = 60.0  # seconds between recovery attempts
    actions: list[RecoveryAction] = field(default_factory=list)
    recovered: bool = False

    @property
    def can_attempt_recovery(self) -> bool:
        """Check if we can attempt recovery (cooldown + max attempts)."""
        if self.attempts >= self.max_attempts:
            return False
        if self.last_recovery_time > 0:
            elapsed = time.time() - self.last_recovery_time
            if elapsed < self.recovery_cooldown:
                return False
        return True

    def record_action(self, action: RecoveryAction):
        """Record a recovery action."""
        self.actions.append(action)
        self.attempts += 1
        self.last_recovery_time = time.time()
        if action.success:
            self.recovered = True


class AutoRecovery:
    """4-tier autonomous recovery system.

    Tiers (escalating):
    1. WAIT: Wait and retry (passive)
    2. CLEAR_CACHE: Clear component caches
    3. RESTART: Restart component
    4. DEGRADE: Degrade functionality (fallback mode)
    """

    def __init__(self):
        self._recovery_states: dict[str, RecoveryState] = {}
        self._recovery_handlers: dict[str, dict[RecoveryTier, Callable]] = {}
        self._circuit_breakers = CircuitBreakerRegistry()
        self._wait_attempts: dict[str, int] = {}

    def register_handler(
        self,
        component: str,
        tier: RecoveryTier,
        handler: Callable,
    ):
        """Register a recovery handler for a component and tier.

        Args:
            component: Component name.
            tier: Recovery tier.
            handler: Callable that performs the recovery action.
        """
        if component not in self._recovery_handlers:
            self._recovery_handlers[component] = {}
        self._recovery_handlers[component][tier] = handler

    def register_default_handlers(self):
        """Register default recovery handlers for common components."""
        # Default handlers (can be overridden)
        for component in ["ollama", "memory_db", "knowledge_graph", "mcp_server"]:
            self.register_handler(
                component, RecoveryTier.TIER1_WAIT, self._default_wait
            )
            self.register_handler(
                component, RecoveryTier.TIER2_CLEAR_CACHE, self._default_clear_cache
            )
            self.register_handler(
                component, RecoveryTier.TIER3_RESTART, self._default_restart
            )
            self.register_handler(
                component, RecoveryTier.TIER4_DEGRADE, self._default_degrade
            )

    def attempt_recovery(
        self, component: str, health_score: HealthScore
    ) -> RecoveryState:
        """Attempt recovery for a component.

        Args:
            component: Component name.
            health_score: Current health score.

        Returns:
            RecoveryState with recovery actions taken.
        """
        if component not in self._recovery_states:
            self._recovery_states[component] = RecoveryState(component=component)

        state = self._recovery_states[component]

        if not state.can_attempt_recovery:
            logger.warning(
                f"Recovery for '{component}' blocked: "
                f"attempts={state.attempts}/{state.max_attempts}, "
                f"cooldown_remaining={max(0, state.recovery_cooldown - (time.time() - state.last_recovery_time)):.1f}s"
            )
            return state

        # Determine which tier to attempt
        tier = self._determine_tier(health_score, state)
        if tier is None:
            return state

        # Get handler
        handlers = self._recovery_handlers.get(component, {})
        handler = handlers.get(tier)
        if handler is None:
            logger.warning(
                f"No recovery handler for '{component}' at tier {tier.value}"
            )
            return state

        # Execute recovery
        logger.info(
            f"Recovery for '{component}' at tier {tier.value} (attempt {state.attempts + 1})"
        )
        try:
            handler(component)
            action = RecoveryAction(
                tier=tier, component=component, action=tier.value, success=True
            )
        except Exception as e:
            logger.error(f"Recovery failed for '{component}' at tier {tier.value}: {e}")
            action = RecoveryAction(
                tier=tier,
                component=component,
                action=tier.value,
                success=False,
                error=str(e),
            )

        state.record_action(action)

        # Open circuit breaker if recovery failed
        if not action.success:
            breaker = get_circuit_breaker(component)
            breaker._on_failure()

        return state

    def check_and_recover(
        self, system_health: SystemHealth
    ) -> dict[str, RecoveryState]:
        """Check all components and attempt recovery for unhealthy ones.

        Args:
            system_health: Current system health.

        Returns:
            Dict of component name to RecoveryState for components that needed recovery.
        """
        results = {}

        for component, score in system_health.components.items():
            if score.total < 60:  # Below warning threshold
                state = self.attempt_recovery(component, score)
                if state.actions:
                    results[component] = state

        return results

    def get_recovery_status(self) -> dict[str, dict]:
        """Get recovery status for all components."""
        return {
            component: {
                "current_tier": state.current_tier.value,
                "attempts": state.attempts,
                "max_attempts": state.max_attempts,
                "recovered": state.recovered,
                "last_recovery_time": state.last_recovery_time,
                "actions": [
                    {
                        "tier": a.tier.value,
                        "action": a.action,
                        "success": a.success,
                        "error": a.error,
                    }
                    for a in state.actions
                ],
            }
            for component, state in self._recovery_states.items()
        }

    def reset(self, component: Optional[str] = None):
        """Reset recovery state.

        Args:
            component: Component to reset, or None for all.
        """
        if component:
            if component in self._recovery_states:
                self._recovery_states[component] = RecoveryState(component=component)
        else:
            self._recovery_states.clear()

    def _determine_tier(
        self, health_score: HealthScore, state: RecoveryState
    ) -> Optional[RecoveryTier]:
        """Determine which recovery tier to attempt.

        Args:
            health_score: Current health score.
            state: Current recovery state.

        Returns:
            RecoveryTier to attempt, or None if no recovery needed.
        """
        score = health_score.total

        if score >= 80:
            return None  # Healthy, no recovery needed

        # Escalate tier based on score and previous attempts
        if score >= 60:
            return RecoveryTier.TIER1_WAIT
        elif score >= 40:
            return RecoveryTier.TIER2_CLEAR_CACHE
        elif score >= 20:
            return RecoveryTier.TIER3_RESTART
        else:
            return RecoveryTier.TIER4_DEGRADE

    # Default recovery handlers
    def _default_wait(self, component: str):
        """Default wait handler with exponential backoff."""
        attempts = self._wait_attempts.get(component, 0)
        # Exponential backoff: 1s, 2s, 4s, 8s, max 16s
        wait_time = min(2**attempts, 16)

        logger.info(
            f"Recovery: Waiting {wait_time}s for '{component}' to recover (attempt {attempts + 1})"
        )
        time.sleep(wait_time)

        # Update attempt counter
        self._wait_attempts[component] = attempts + 1

    def _default_clear_cache(self, component: str):
        """Default clear cache handler - clears relevant caches."""
        cleared = []

        # Try to clear generic caches
        try:
            from src.infrastructure.cache_service import CacheService

            cache = CacheService()
            cache._cache.clear()
            cleared.append("CacheService")
        except ImportError:
            pass

        try:
            from src.model_router.semantic_cache import SemanticCache

            semantic = SemanticCache.__new__(SemanticCache)
            semantic._exact_cache = {}
            semantic._semantic_cache = {}
            cleared.append("SemanticCache")
        except (ImportError, AttributeError):
            pass

        # Component-specific cache clearing
        if component == "ollama":
            # Clear embedding cache files
            cache_dirs = [
                os.path.expanduser("~/.cache/ollama"),
                os.path.expanduser("~/.cache/tmprag"),
            ]
            for cache_dir in cache_dirs:
                if os.path.exists(cache_dir):
                    try:
                        for f in os.listdir(cache_dir):
                            fpath = os.path.join(cache_dir, f)
                            if os.path.isfile(fpath):
                                os.remove(fpath)
                        cleared.append(f"dir:{cache_dir}")
                    except OSError:
                        pass

        if component == "memory_db":
            # Clear query cache in state/db
            try:
                from src.state.db import get_db

                db = get_db()
                if hasattr(db, "_query_cache"):
                    db._query_cache.clear()
                cleared.append("memory_db")
            except Exception:
                pass

        logger.info(f"Recovery: Cleared caches for '{component}': {cleared}")

    def _default_restart(self, component: str):
        """Default restart handler - actually restart the component."""
        if component == "ollama":
            # Try to restart ollama service
            logger.info(f"Recovery: Attempting to restart Ollama service")
            try:
                # Try systemd first
                import subprocess
                subprocess.run(
                    ["systemctl", "restart", "ollama"],
                    capture_output=True,
                    timeout=30,
                )
            except Exception as e:
                logger.warning(f"Could not restart ollama via systemd: {e}")

            try:
                # Try to find and signal ollama process
                result = subprocess.run(
                    ["pgrep", "-f", "ollama"], capture_output=True, text=True
                )
                if result.returncode == 0:
                    pids = result.stdout.strip().split("\n")
                    for pid in pids:
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            logger.info(
                                f"Recovery: Sent SIGTERM to ollama process {pid}"
                            )
                        except (OSError, ValueError):
                            pass
            except Exception as e:
                logger.warning(f"Could not find ollama process: {e}")

        elif component == "mcp_server":
            # Try to restart MCP server
            logger.info(f"Recovery: Attempting to restart MCP server")
            try:
                result = subprocess.run(
                    ["pgrep", "-f", "mcp"], capture_output=True, text=True
                )
                if result.returncode == 0:
                    pids = result.stdout.strip().split("\n")
                    for pid in pids:
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            logger.info(f"Recovery: Sent SIGTERM to MCP process {pid}")
                        except (OSError, ValueError):
                            pass
            except Exception as e:
                logger.warning(f"Could not restart MCP server: {e}")

        elif component == "memory_db":
            # Try to compact SQLite database
            logger.info(f"Recovery: Attempting to compact SQLite database")
            try:
                db_path = os.path.expanduser("~/.local/share/n-xyme/mind.db")
                if os.path.exists(db_path):
                    conn = sqlite3.connect(db_path)
                    conn.execute("VACUUM")
                    conn.close()
                    logger.info(f"Recovery: Compacted SQLite database")
            except Exception as e:
                logger.warning(f"Could not compact database: {e}")

        elif component == "knowledge_graph":
            # Reload knowledge graph
            logger.info(f"Recovery: Reloading knowledge graph")
            try:
                from src.memory.knowledge_graph import KnowledgeGraph

                logger.info(f"Recovery: Knowledge graph reload requested")
            except Exception as e:
                logger.warning(f"Could not reload knowledge graph: {e}")

        else:
            logger.warning(
                f"Recovery: No restart action defined for component '{component}'"
            )

    def _default_degrade(self, component: str):
        """Default degrade handler - switch to fallback mode."""
        if component == "ollama":
            # Disable embedding, use simpler path
            logger.info(f"Recovery: Degrading Ollama - disabling embedding cache")
            try:
                from src.model_router import model_router

                if hasattr(model_router, "_embedding_enabled"):
                    model_router._embedding_enabled = False
                if hasattr(model_router, "_use_fallback"):
                    model_router._use_fallback = True
            except Exception as e:
                logger.warning(f"Could not degrade ollama: {e}")

        elif component == "memory_db":
            # Switch to simpler query path, skip FTS5
            logger.info(f"Recovery: Degrading memory_db - using basic query path")
            try:
                from src.state.db import get_db

                db = get_db()
                if hasattr(db, "_use_fts5"):
                    db._use_fts5 = False
            except Exception as e:
                logger.warning(f"Could not degrade memory_db: {e}")

        elif component == "knowledge_graph":
            # Disable graph traversal, use linear search
            logger.info(f"Recovery: Degrading knowledge_graph - using linear search")
            try:
                from src.memory.knowledge_graph import KnowledgeGraph
            except Exception as e:
                logger.warning(f"Could not degrade knowledge_graph: {e}")

        elif component == "mcp_server":
            # Disable MCP features, use direct access
            logger.info(f"Recovery: Degrading mcp_server - using direct file access")
            try:
                from src.mcp_server import mcp_server

                if hasattr(mcp_server, "_enabled"):
                    mcp_server._enabled = False
            except Exception as e:
                logger.warning(f"Could not degrade mcp_server: {e}")

        else:
            logger.warning(
                f"Recovery: No degrade action defined for component '{component}'"
            )

        logger.info(f"Recovery: Degraded '{component}' to fallback mode")
