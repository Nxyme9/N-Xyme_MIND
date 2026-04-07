"""Session auto-inject hook — reads all context on session start.

Provides SessionInjector class that aggregates:
- Session state (.sisyphus/session-state.json)
- Active context (.context/activeContext.md)
- Memory router stats
- Learning engine stats

Thread-safe with caching (5-minute TTL).
"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Constants
CACHE_TTL_SECONDS = 300  # 5 minutes
SESSION_STATE_PATH = Path(".sisyphus/session-state.json")
ACTIVE_CONTEXT_PATH = Path(".context/activeContext.md")

# Optional imports - graceful fallback if unavailable
_MEMORY_CORE_AVAILABLE = False
_LEARNING_ENGINE_AVAILABLE = False

try:
    from packages.memory_core.router import get_default_router

    _MEMORY_CORE_AVAILABLE = True
except ImportError as e:
    logger.debug(f"memory_core not available: {e}")

try:
    from packages.learning_engine.routing.adaptive_router import (
        AdaptiveRouter,
        LearningStats,
    )

    _LEARNING_ENGINE_AVAILABLE = True
except ImportError as e:
    logger.debug(f"learning_engine not available: {e}")


class SessionInjector:
    """Injects aggregated context on session start.

    Thread-safe with 5-minute cache. Reads session state, active context,
    memory stats, and learning stats to provide comprehensive context.

    Usage:
        injector = SessionInjector()
        context = injector.inject_context()
        # Use context string to initialize agent
    """

    def __init__(self, cache_ttl: int = CACHE_TTL_SECONDS):
        """Initialize session injector.

        Args:
            cache_ttl: Cache time-to-live in seconds (default: 300 = 5 minutes)
        """
        self._cache_ttl = cache_ttl
        self._lock = threading.Lock()
        self._cached_context: Optional[str] = None
        self._cache_timestamp: Optional[float] = None

    def inject_context(self) -> str:
        """Get aggregated context string.

        Reads all context sources and returns a single string with
        session state, active context, memory stats, and learning stats.

        Returns:
            String containing all context for session injection
        """
        # Check cache first (thread-safe)
        with self._lock:
            if self._cached_context is not None and self._cache_timestamp is not None:
                elapsed = time.time() - self._cache_timestamp
                if elapsed < self._cache_ttl:
                    logger.debug(f"Returning cached context (age: {elapsed:.1f}s)")
                    return self._cached_context

            # Cache miss or expired - rebuild context
            logger.info("Rebuilding session context...")
            self._cached_context = self._build_context()
            self._cache_timestamp = time.time()
            return self._cached_context

    def _build_context(self) -> str:
        """Build aggregated context string from all sources.

        Returns:
            Formatted context string
        """
        parts: list[str] = []

        # 1. Session state
        session_state = self._read_session_state()
        if session_state:
            parts.append(self._format_session_state(session_state))

        # 2. Active context
        active_context = self._read_active_context()
        if active_context:
            parts.append(self._format_active_context(active_context))

        # 3. Memory stats
        memory_stats = self._get_memory_stats()
        if memory_stats:
            parts.append(self._format_memory_stats(memory_stats))

        # 4. Learning stats
        learning_stats = self._get_learning_stats()
        if learning_stats:
            parts.append(self._format_learning_stats(learning_stats))

        if not parts:
            return "# Session Context\n\nNo context available."

        return "\n\n".join(parts)

    def _read_session_state(self) -> Optional[dict]:
        """Read session state from JSON file.

        Returns:
            Dict with session state or None if unavailable
        """
        try:
            if SESSION_STATE_PATH.exists():
                with open(SESSION_STATE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read session state: {e}")
        return None

    def _read_active_context(self) -> Optional[str]:
        """Read active context markdown file.

        Returns:
            String with active context content or None if unavailable
        """
        try:
            if ACTIVE_CONTEXT_PATH.exists():
                with open(ACTIVE_CONTEXT_PATH, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception as e:
            logger.warning(f"Failed to read active context: {e}")
        return None

    def _get_memory_stats(self) -> Optional[dict]:
        """Get memory router statistics.

        Returns:
            Dict with memory stats or None if unavailable
        """
        if not _MEMORY_CORE_AVAILABLE:
            return None

        try:
            # Try to get stats from session-state (already loaded)
            session_state = self._read_session_state()
            if session_state and "memory_stats" in session_state:
                return session_state["memory_stats"]
        except Exception as e:
            logger.debug(f"Failed to get memory stats: {e}")
        return None

    def _get_learning_stats(self) -> Optional[dict]:
        """Get learning engine statistics.

        Returns:
            Dict with learning stats or None if unavailable
        """
        if not _LEARNING_ENGINE_AVAILABLE:
            return None

        try:
            router = AdaptiveRouter()
            stats = router.get_learning_stats()
            return {
                "total_decisions": stats.total_decisions,
                "successful_decisions": stats.successful_decisions,
                "success_rate": stats.success_rate,
                "average_q_value": stats.average_q_value,
                "exploration_count": stats.exploration_count,
                "exploitation_count": stats.exploitation_count,
                "improvement_trend": stats.improvement_trend,
            }
        except Exception as e:
            logger.debug(f"Failed to get learning stats: {e}")
        return None

    def _format_session_state(self, state: dict) -> str:
        """Format session state as markdown.

        Args:
            state: Session state dict

        Returns:
            Formatted markdown string
        """
        lines = [
            "# Session State",
            "",
            f"- **Last Agent**: {state.get('last_agent', 'unknown')}",
            f"- **Last Action**: {state.get('last_action', 'none')}",
            f"- **Session Started**: {state.get('session_started', 'unknown')}",
            f"- **Current Task**: {state.get('current_task', 'none')}",
            "",
        ]

        completed = state.get("completed_changes", [])
        if completed:
            lines.append("## Completed Changes")
            for change in completed[-10:]:  # Last 10
                lines.append(f"- {change}")
            lines.append("")

        pending = state.get("pending_changes", [])
        if pending:
            lines.append("## Pending Changes")
            for change in pending:
                lines.append(f"- {change}")
            lines.append("")

        return "\n".join(lines).strip()

    def _format_active_context(self, content: str) -> str:
        """Format active context content.

        Args:
            content: Raw active context content

        Returns:
            Formatted markdown string
        """
        return f"# Active Context\n\n{content.strip()}"

    def _format_memory_stats(self, stats: dict) -> str:
        """Format memory stats.

        Args:
            stats: Memory stats dict

        Returns:
            Formatted markdown string
        """
        return (
            "# Memory System Stats\n\n"
            f"- **Files Indexed**: {stats.get('files_indexed', 0):,}\n"
            f"- **Chunks Embedded**: {stats.get('chunks_embedded', 0):,}\n"
            f"- **Drives Scanned**: {stats.get('drives_scanned', 0)}\n"
            f"- **Tests Passing**: {stats.get('tests_passing', 0)}\n"
            f"- **MCP Tools**: {stats.get('mcp_tools', 0)}"
        )

    def _format_learning_stats(self, stats: dict) -> str:
        """Format learning stats.

        Args:
            stats: Learning stats dict

        Returns:
            Formatted markdown string
        """
        return (
            "# Learning Engine Stats\n\n"
            f"- **Total Decisions**: {stats.get('total_decisions', 0):,}\n"
            f"- **Success Rate**: {stats.get('success_rate', 0.0):.1%}\n"
            f"- **Average Q-Value**: {stats.get('average_q_value', 0.0):.4f}\n"
            f"- **Exploration Count**: {stats.get('exploration_count', 0):,}\n"
            f"- **Exploitation Count**: {stats.get('exploitation_count', 0):,}\n"
            f"- **Improvement Trend**: {stats.get('improvement_trend', 0.0):+.4f}"
        )

    def clear_cache(self) -> None:
        """Clear cached context to force rebuild on next call.

        Thread-safe.
        """
        with self._lock:
            self._cached_context = None
            self._cache_timestamp = None
            logger.info("Context cache cleared")


# Default instance for convenience
_default_injector: Optional[SessionInjector] = None


def get_default_injector() -> SessionInjector:
    """Get or create default SessionInjector instance."""
    global _default_injector
    if _default_injector is None:
        _default_injector = SessionInjector()
    return _default_injector


__all__ = [
    "SessionInjector",
    "get_default_injector",
]
