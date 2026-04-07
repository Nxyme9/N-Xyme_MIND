#!/usr/bin/env python3
"""Session auto-inject hook - reads ALL context on session start and injects into agent awareness.

This module provides SessionInjector class that reads context from:
- .sisyphus/session-state.json
- .context/activeContext.md
- .context/memory_bank/*.md
- MemoryRouter stats
- LearningEngine stats
- HealthCheck status

Usage:
    from nx_mind_mcp.session_hooks import SessionInjector
    
    injector = SessionInjector()
    context = injector.inject_context()
    # context now contains all relevant session context
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Constants
CACHE_TTL_SECONDS = 300  # 5 minutes
PROJECT_ROOT = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")


@dataclass
class SessionContext:
    """Container for session context data."""

    session_state: dict[str, Any] = field(default_factory=dict)
    active_context: str = ""
    memory_bank: dict[str, str] = field(default_factory=dict)
    memory_stats: dict[str, Any] = field(default_factory=dict)
    learning_stats: dict[str, Any] = field(default_factory=dict)
    health_status: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""


class SessionInjector:
    """Reads all context files on first call and returns a single context string.

    Caches context after first read with TTL of 5 minutes.
    Thread-safe with threading.Lock.
    """

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize SessionInjector.

        Args:
            project_root: Optional project root path. Defaults to PROJECT_ROOT.
        """
        self._project_root = project_root or PROJECT_ROOT
        self._cache: Optional[SessionContext] = None
        self._cache_time: float = 0.0
        self._lock = Lock()

    def inject_context(self) -> str:
        """Get session context, using cache if available.

        Returns:
            Single string containing all relevant context for agent injection.
        """
        # Check if cache is valid
        if self._is_cache_valid():
            return self._format_context(self._cache)

        # Acquire lock and refresh cache
        with self._lock:
            # Double-check after acquiring lock
            if self._is_cache_valid():
                return self._format_context(self._cache)

            # Read all context sources
            context = self._read_all_context()
            self._cache = context
            self._cache_time = time.time()

            return self._format_context(context)

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid (within TTL)."""
        if self._cache is None:
            return False
        elapsed = time.time() - self._cache_time
        return elapsed < CACHE_TTL_SECONDS

    def _read_all_context(self) -> SessionContext:
        """Read all context sources and return as SessionContext."""
        context = SessionContext(timestamp=datetime.now(timezone.utc).isoformat())

        # Read session state
        context.session_state = self._read_session_state()

        # Read active context
        context.active_context = self._read_active_context()

        # Read memory bank files
        context.memory_bank = self._read_memory_bank()

        # Get memory stats
        context.memory_stats = self._get_memory_stats()

        # Get learning stats
        context.learning_stats = self._get_learning_stats()

        # Get health status
        context.health_status = self._get_health_status()

        return context

    def _read_session_state(self) -> dict[str, Any]:
        """Read .sisyphus/session-state.json."""
        session_file = self._project_root / ".sisyphus" / "session-state.json"
        if not session_file.exists():
            logger.warning(f"Session state file not found: {session_file}")
            return {}

        try:
            with open(session_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading session state: {e}")
            return {}

    def _read_active_context(self) -> str:
        """Read .context/activeContext.md."""
        active_file = self._project_root / ".context" / "activeContext.md"
        if not active_file.exists():
            logger.warning(f"Active context file not found: {active_file}")
            return ""

        try:
            with open(active_file, "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading active context: {e}")
            return ""

    def _read_memory_bank(self) -> dict[str, str]:
        """Read all .md files from .context/memory_bank/."""
        memory_bank_dir = self._project_root / ".context" / "memory_bank"
        result = {}

        if not memory_bank_dir.exists():
            logger.warning(f"Memory bank directory not found: {memory_bank_dir}")
            return result

        try:
            for md_file in memory_bank_dir.glob("*.md"):
                try:
                    with open(md_file, "r") as f:
                        result[md_file.name] = f.read()
                except Exception as e:
                    logger.error(f"Error reading {md_file.name}: {e}")
        except Exception as e:
            logger.error(f"Error listing memory bank: {e}")

        return result

    def _get_memory_stats(self) -> dict[str, Any]:
        """Get memory stats from MemoryRouter and related modules."""
        stats = {
            "status": "unavailable",
            "error": None,
        }

        try:
            # Try to get stats from memory_core modules
            from memory_core.router import MemoryRouter
            from memory_core.health import HealthCheck

            # Get health check for memory
            health = HealthCheck()
            mem_health = health.check_memory_stores()

            stats = {
                "status": "available",
                "memory_health": {
                    "component": mem_health.component,
                    "status": mem_health.status.value if hasattr(mem_health.status, 'value') else str(mem_health.status),
                    "latency_ms": mem_health.latency_ms,
                }
            }
        except ImportError as e:
            stats["error"] = f"Import error: {e}"
        except Exception as e:
            stats["error"] = str(e)

        return stats

    def _get_learning_stats(self) -> dict[str, Any]:
        """Get learning stats from AdaptiveRouter."""
        stats = {
            "status": "unavailable",
            "error": None,
        }

        try:
            from learning_engine.routing.adaptive_router import AdaptiveRouter
            from learning_engine.outcome_logger import OutcomeLogger

            # Get outcome logger stats
            logger_outcome = OutcomeLogger()
            outcomes = logger_outcome.get_outcomes(limit=1000) or []

            # Get routing stats
            stats = {
                "status": "available",
                "total_outcomes": len(outcomes),
                "successful_outcomes": sum(1 for o in outcomes if o.success),
                "failed_outcomes": sum(1 for o in outcomes if not o.success),
            }

            # Try to get AdaptiveRouter stats if available
            try:
                router = AdaptiveRouter()
                learning_stats = router.get_learning_stats()
                stats["learning_stats"] = {
                    "total_decisions": learning_stats.total_decisions,
                    "success_rate": learning_stats.success_rate,
                    "improvement_trend": learning_stats.improvement_trend,
                }
            except Exception:
                pass  # AdaptiveRouter stats are optional

        except ImportError as e:
            stats["error"] = f"Import error: {e}"
        except Exception as e:
            stats["error"] = str(e)

        return stats

    def _get_health_status(self) -> dict[str, Any]:
        """Get health status from HealthCheck."""
        status = {
            "status": "unavailable",
            "error": None,
        }

        try:
            from memory_core.health import HealthCheck

            health = HealthCheck()
            overall = health.get_overall_health()

            status = {
                "status": overall.get("status", "unknown"),
                "overall_status": overall.get("overall_status", "unknown"),
                "components_checked": overall.get("components_checked", 0),
                "total_latency_ms": overall.get("total_latency_ms", 0),
            }
        except ImportError as e:
            status["error"] = f"Import error: {e}"
        except Exception as e:
            status["error"] = str(e)

        return status

    def _format_context(self, context: SessionContext) -> str:
        """Format SessionContext as a single string for agent injection."""
        lines = []
        lines.append("=" * 60)
        lines.append("SESSION CONTEXT - Auto-injected at session start")
        lines.append("=" * 60)
        lines.append(f"Timestamp: {context.timestamp}")
        lines.append("")

        # Session State
        lines.append("## Session State")
        if context.session_state:
            lines.append(f"  Last Agent: {context.session_state.get('last_agent', 'unknown')}")
            lines.append(f"  Current Task: {context.session_state.get('current_task', 'none')}")
            lines.append(f"  Last Action: {context.session_state.get('last_action', 'none')}")
            
            pending = context.session_state.get('pending_changes', [])
            if pending:
                lines.append(f"  Pending Changes: {len(pending)}")
                for p in pending[:3]:
                    lines.append(f"    - {p}")
            
            completed = context.session_state.get('completed_changes', [])
            if completed:
                lines.append(f"  Completed Changes: {len(completed)}")
                for c in completed[-3:]:
                    lines.append(f"    - {c}")
        else:
            lines.append("  (no session state)")
        lines.append("")

        # Active Context
        lines.append("## Active Context")
        if context.active_context:
            # Show first 20 lines of active context
            active_lines = context.active_context.split("\n")[:20]
            for line in active_lines:
                lines.append(f"  {line}")
        else:
            lines.append("  (no active context)")
        lines.append("")

        # Memory Bank
        lines.append("## Memory Bank")
        if context.memory_bank:
            for name, content in context.memory_bank.items():
                lines.append(f"  ### {name}")
                # Show first 10 lines of each memory bank file
                content_lines = content.split("\n")[:10]
                for line in content_lines:
                    if line.strip():
                        lines.append(f"    {line}")
                lines.append("    ...")
        else:
            lines.append("  (no memory bank files)")
        lines.append("")

        # Memory Stats
        lines.append("## Memory System Stats")
        if context.memory_stats.get("status") == "available":
            mem_health = context.memory_stats.get("memory_health", {})
            lines.append(f"  Status: {context.memory_stats.get('status')}")
            lines.append(f"  Component: {mem_health.get('component')}")
            lines.append(f"  Health: {mem_health.get('status')}")
            lines.append(f"  Latency: {mem_health.get('latency_ms', 0):.2f}ms")
        else:
            lines.append(f"  Status: {context.memory_stats.get('status')}")
            if context.memory_stats.get("error"):
                lines.append(f"  Error: {context.memory_stats.get('error')}")
        lines.append("")

        # Learning Stats
        lines.append("## Learning Engine Stats")
        if context.learning_stats.get("status") == "available":
            lines.append(f"  Total Outcomes: {context.learning_stats.get('total_outcomes', 0)}")
            lines.append(f"  Successful: {context.learning_stats.get('successful_outcomes', 0)}")
            lines.append(f"  Failed: {context.learning_stats.get('failed_outcomes', 0)}")
            
            learning = context.learning_stats.get("learning_stats", {})
            if learning:
                lines.append(f"  Decisions: {learning.get('total_decisions', 0)}")
                lines.append(f"  Success Rate: {learning.get('success_rate', 0):.2%}")
                lines.append(f"  Trend: {learning.get('improvement_trend', 0):.4f}")
        else:
            lines.append(f"  Status: {context.learning_stats.get('status')}")
            if context.learning_stats.get("error"):
                lines.append(f"  Error: {context.learning_stats.get('error')}")
        lines.append("")

        # Health Status
        lines.append("## System Health")
        if context.health_status.get("status") == "available":
            lines.append(f"  Overall: {context.health_status.get('overall_status')}")
            lines.append(f"  Components: {context.health_status.get('components_checked')}")
            lines.append(f"  Latency: {context.health_status.get('total_latency_ms', 0):.2f}ms")
        else:
            lines.append(f"  Status: {context.health_status.get('status')}")
            if context.health_status.get("error"):
                lines.append(f"  Error: {context.health_status.get('error')}")

        lines.append("")
        lines.append("=" * 60)
        lines.append("END SESSION CONTEXT")
        lines.append("=" * 60)

        return "\n".join(lines)

    def invalidate_cache(self) -> None:
        """Invalidate the cached context, forcing refresh on next call."""
        with self._lock:
            self._cache = None
            self._cache_time = 0.0


# Default instance for convenience
_default_injector: Optional[SessionInjector] = None


def get_session_injector() -> SessionInjector:
    """Get or create default SessionInjector instance."""
    global _default_injector
    if _default_injector is None:
        _default_injector = SessionInjector()
    return _default_injector
