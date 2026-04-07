"""nx-mind-mcp - Session context injection for agent awareness.

MCP server providing:
- get_session_context(): Auto-injects session context on first call
- log_task_completion(): Logs task completion to session state
- Plus existing MIND state management tools
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Optional

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Path Setup
# ---------------------------------------------------------------------------


def _setup_paths():
    """Add project root to path for imports."""
    project_root = Path(__file__).resolve().parent.parent.parent
    packages_root = project_root / "packages"

    # Add packages to path for session_hooks and session_writer
    if str(packages_root) not in sys.path:
        sys.path.insert(0, str(packages_root))

    return project_root


PROJECT_ROOT = _setup_paths()

logger = logging.getLogger("nx-mind-mcp")

# ---------------------------------------------------------------------------
# Server Init
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="nx-mind",
    version="1.0.0",
    instructions=(
        "N-Xyme MIND MCP Server — session context injection and state management.\n\n"
        "Tools:\n"
        "- get_session_context: Auto-inject session context on first call\n"
        "- log_task_completion: Log task completion to session state\n"
        "- get_mind_state: Get current MIND state\n"
        "- update_mind_state: Update MIND state\n"
        "- get_session_history: Get session history\n"
        "- get_active_workflow: Get active workflow\n"
        "- set_context: Set project context\n"
        "- sync_to_memory: Sync state to memory MCP\n"
        "- get_project_manifest: Get project metadata\n"
    ),
)

# ---------------------------------------------------------------------------
# Session Hooks Integration
# ---------------------------------------------------------------------------

# Lazy-loaded instances
_session_injector: Optional[Any] = None
_session_writer: Optional[Any] = None


def _get_session_injector():
    """Get or create SessionInjector instance."""
    global _session_injector
    if _session_injector is None:
        try:
            from nx_mind_mcp.session_hooks import SessionInjector

            _session_injector = SessionInjector(project_root=PROJECT_ROOT)
        except ImportError as e:
            logger.warning(f"SessionInjector not available: {e}")
            return None
    return _session_injector


def _get_session_writer():
    """Get or create SessionWriter instance."""
    global _session_writer
    if _session_writer is None:
        try:
            # Import from package root level (packages/nx-mind-mcp/session_writer.py)
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "session_writer",
                PROJECT_ROOT.parent / "nx-mind-mcp" / "session_writer.py",
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                SessionWriter = module.SessionWriter

                _session_writer = SessionWriter(
                    state_path=str(PROJECT_ROOT / ".sisyphus" / "session-state.json"),
                    context_path=str(PROJECT_ROOT / ".context" / "activeContext.md"),
                    log_path=str(PROJECT_ROOT / ".sisyphus" / "session-log.jsonl"),
                )
        except (ImportError, AttributeError) as e:
            logger.warning(f"SessionWriter not available: {e}")
            return None
    return _session_writer


# ---------------------------------------------------------------------------
# MCP Tools - Session Context Injection
# ---------------------------------------------------------------------------


@mcp.tool()
def get_session_context() -> str:
    """Get aggregated session context for agent awareness.

    Reads from:
    - .sisyphus/session-state.json
    - .context/activeContext.md
    - Memory bank files
    - Memory system stats
    - Learning engine stats
    - Health status

    Auto-injects on first call (lazy loading). Caches for 5 minutes.

    Returns:
        String containing all session context for agent injection.
    """
    try:
        injector = _get_session_injector()
        if injector is None:
            return "Error: SessionInjector not available"
        return injector.inject_context()
    except Exception as e:
        logger.error(f"Error getting session context: {e}")
        return f"Error: {e}"


@mcp.tool()
def log_task_completion(
    task_id: str,
    description: str,
    success: bool,
    agent: str,
    duration_ms: float,
) -> dict[str, Any]:
    """Log task completion to session state.

    Writes to:
    - .sisyphus/session-state.json
    - .context/activeContext.md
    - .sisyphus/session-log.jsonl

    Non-blocking (spawns background thread).

    Args:
        task_id: Unique identifier for the task
        description: What was accomplished
        success: Whether task succeeded
        agent: Agent that handled the task
        duration_ms: How long the task took

    Returns:
        Dict with status and message.
    """
    try:
        writer = _get_session_writer()
        if writer is None:
            return {"status": "error", "message": "SessionWriter not available"}

        writer.write_completion(
            task_id=task_id,
            description=description,
            success=success,
            agent=agent,
            duration_ms=duration_ms,
        )

        return {
            "status": "ok",
            "message": f"Task {task_id} logged successfully",
            "task_id": task_id,
            "success": success,
        }
    except Exception as e:
        logger.error(f"Error logging task completion: {e}")
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------------------------
# MCP Tools - Existing MIND State Management
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# MCP Tools - Existing MIND State Management (stub implementations)
# ---------------------------------------------------------------------------


@mcp.tool()
def get_mind_state() -> dict[str, Any]:
    """Get current MIND state.

    Returns:
        Dict with project, phase, active_tasks, context, and timestamps.
    """
    return {
        "project": None,
        "phase": None,
        "active_tasks": [],
        "context": {},
        "timestamp": "",
    }


@mcp.tool()
def update_mind_state(
    project: Optional[str] = None,
    phase: Optional[str] = None,
    active_tasks: Optional[list[str]] = None,
    context: Optional[dict[str, str]] = None,
    clear_context: bool = False,
) -> dict[str, Any]:
    """Update MIND state with new information."""
    return {"status": "ok", "message": "State update placeholder"}


@mcp.tool()
def get_session_history(limit: int = 10) -> dict[str, Any]:
    """Get history of past sessions with summaries."""
    return {"sessions": [], "count": 0}


@mcp.tool()
def get_active_workflow() -> dict[str, Any]:
    """Get currently active BMAD workflow and step."""
    return {"workflow": None, "phase": None, "step": None}


@mcp.tool()
def set_context(key: str, value: str) -> dict[str, Any]:
    """Set project context for current session."""
    return {"status": "ok", "key": key, "value": value}


@mcp.tool()
def sync_to_memory(target: str = "memory") -> dict[str, Any]:
    """Sync MIND state to memory MCP."""
    return {"status": "ok", "target": target}


@mcp.tool()
def get_project_manifest() -> dict[str, Any]:
    """Get project metadata and progress."""
    return {
        "name": "N-Xyme_MIND",
        "description": "",
        "version": "1.0.0",
        "progress": 0,
        "milestones": [],
    }


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "mcp",
    "get_session_context",
    "log_task_completion",
    "get_mind_state",
    "update_mind_state",
    "get_session_history",
    "get_active_workflow",
    "set_context",
    "sync_to_memory",
    "get_project_manifest",
]
