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
        "- spine_probe: Run GoldenSpine health check\n"
        "- spine_run: Execute inference via GoldenSpine\n"
        "- spine_status: Get GoldenSpine status\n"
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
            from .session_hooks import SessionInjector

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
                PROJECT_ROOT.parent / "nx_mind_mcp" / "session_writer.py",
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
    """Get history of past sessions with summaries.

    Queries unified-memory for session data and returns
    aggregated session history with summaries.
    Falls back to local session storage if unified_memory is not available.
    """
    try:
        # Try to import unified-memory MCP client
        unified_memory_available = False
        try:
            from unified_memory import search_memories

            unified_memory_available = True
        except ImportError:
            try:
                from packages.unified_memory.client import UnifiedMemoryClient

                unified_memory_available = True
                client = UnifiedMemoryClient()
                results = client.search("session history", limit=limit * 2)
                return _build_session_history_response(results, limit)
            except ImportError:
                pass

        if unified_memory_available:
            # Search for session-related memories
            results = search_memories(
                query="session_summary session_complete session_end",
                limit=limit * 2,
                strict=False,
            )
            return _build_session_history_response(results, limit)

        # Fallback: Read from local session storage
        return _get_local_session_history(limit)

    except Exception as e:
        logger.warning(f"get_session_history failed: {e}")
        return {"sessions": [], "count": 0, "error": str(e)}


def _get_local_session_history(limit: int) -> dict[str, Any]:
    """Get session history from local storage (fallback when unified_memory unavailable)."""
    import json
    from pathlib import Path

    session_file = (
        Path(__file__).parent.parent.parent / ".context" / "session-history.json"
    )
    if session_file.exists():
        try:
            with open(session_file) as f:
                data = json.load(f)
                sessions = data.get("sessions", [])[:limit]
                return {"sessions": sessions, "count": len(sessions), "source": "local"}
        except Exception:
            pass

    return {"sessions": [], "count": 0, "source": "local", "status": "no_sessions"}


def _build_session_history_response(results: dict, limit: int) -> dict[str, Any]:
    """Build session history response from unified-memory results."""
    if not results or not results.get("results"):
        return {"sessions": [], "count": 0}

    # Group by session_id (extract from content)
    sessions = {}
    for r in results.get("results", []):
        content = r.get("content", "")
        # Extract session_id if present
        import re

        session_match = re.search(
            r'session[_-]?id["\s:]+([a-f0-9]+)', content, re.IGNORECASE
        )
        if session_match:
            sid = session_match.group(1)
            if sid not in sessions:
                sessions[sid] = {
                    "session_id": sid,
                    "summary": content[:200],
                    "messages": [],
                }
            sessions[sid]["messages"].append(content)

    # Convert to list and apply limit
    session_list = list(sessions.values())[:limit]

    return {"sessions": session_list, "count": len(session_list)}


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
    # Golden Spine tools
    "spine_probe",
    "spine_run",
    "spine_status",
]


# =============================================================================
# Golden Spine Integration
# =============================================================================

_spine_instance: Optional[Any] = None


def _get_spine():
    """Get or create GoldenSpine instance."""
    global _spine_instance
    if _spine_instance is None:
        try:
            from packages.infrastructure.spine.spine import GoldenSpine

            _spine_instance = GoldenSpine()
        except ImportError as e:
            logger.warning(f"GoldenSpine not available: {e}")
            return None
    return _spine_instance


@mcp.tool()
def spine_probe() -> dict[str, Any]:
    """Run GoldenSpine health check across all 3 layers.

    Returns:
        Dict with process, model, and responsive layer health results.
    """
    try:
        spine = _get_spine()
        if spine is None:
            return {"error": "GoldenSpine not available", "healthy": False}

        report = spine.probe()
        return {
            "healthy": report.overall_healthy,
            "process": {
                "healthy": report.process.healthy,
                "message": report.process.message,
            },
            "model": {"healthy": report.model.healthy, "message": report.model.message},
            "responsive": {
                "healthy": report.responsive.healthy,
                "message": report.responsive.message,
            },
        }
    except Exception as e:
        logger.error(f"Error running spine probe: {e}")
        return {"error": str(e), "healthy": False}


@mcp.tool()
def spine_run(prompt: str, model: Optional[str] = None) -> dict[str, Any]:
    """Execute inference via GoldenSpine with resilience pipeline.

    Args:
        prompt: The prompt to send to the model
        model: Optional model override (uses config default if not set)

    Returns:
        Dict with run_id, model, success, latency_ms, and error if any.
    """
    try:
        spine = _get_spine()
        if spine is None:
            return {"error": "GoldenSpine not available", "success": False}

        result = spine.run(prompt=prompt, model=model)
        return {
            "run_id": result.run_id,
            "model": result.model,
            "success": result.success,
            "latency_ms": result.latency_ms,
            "error": result.error,
        }
    except Exception as e:
        logger.error(f"Error running spine inference: {e}")
        return {"error": str(e), "success": False}


@mcp.tool()
def spine_status() -> dict[str, Any]:
    """Get current GoldenSpine status.

    Returns:
        Dict with running state, run count, health, fallback status, and run stats.
    """
    try:
        spine = _get_spine()
        if spine is None:
            return {"error": "GoldenSpine not available", "running": False}

        return spine.status()
    except Exception as e:
        logger.error(f"Error getting spine status: {e}")
        return {"error": str(e), "running": False}
