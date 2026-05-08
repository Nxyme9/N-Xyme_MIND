"""
Mind namespace tools for nx-brain-mcp.

This module contains all mind-related MCP tools.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def session_pool_stats() -> dict[str, Any]:
    """Get session pool statistics."""
    try:
        from packages.session_pool_mcp.mcp_server import pool_stats

        return pool_stats()
    except Exception as e:
        logger.error(f"session_pool_stats failed: {e}")
        return {"error": str(e)}


def mind_log_task_completion(
    task_id: str, description: str, success: bool, agent: str, duration_ms: int
) -> dict[str, Any]:
    """Log task completion to session state."""
    try:
        from packages.nx_mind_mcp import log_task_completion

        return log_task_completion(task_id, description, success, agent, duration_ms)
    except Exception as e:
        logger.error(f"mind_log_task_completion failed: {e}")
        return {"error": str(e)}


def mind_get_mind_state() -> dict[str, Any]:
    """Get current MIND state (project, phase, active tasks)."""
    try:
        from packages.nx_mind_mcp import get_mind_state

        return get_mind_state()
    except Exception as e:
        logger.error(f"mind_get_mind_state failed: {e}")
        return {"error": str(e)}


def mind_update_mind_state(
    project: Optional[str] = None,
    phase: Optional[str] = None,
    active_tasks: Optional[list] = None,
    context: Optional[dict] = None,
    clear_context: bool = False,
) -> dict[str, Any]:
    """Update MIND state with new information."""
    try:
        from packages.nx_mind_mcp import update_mind_state

        return update_mind_state(project, phase, active_tasks, context, clear_context)
    except Exception as e:
        logger.error(f"mind_update_mind_state failed: {e}")
        return {"error": str(e)}


def mind_get_session_history(limit: int = 10) -> dict[str, Any]:
    """Get history of past sessions with summaries."""
    try:
        from packages.nx_mind_mcp import get_session_history

        result = get_session_history(limit)
        if isinstance(result, dict) and "unified_memory" in result.get("error", ""):
            return {
                "sessions": [],
                "limit": limit,
                "status": "unified_memory_unavailable",
                "message": "unified_memory module not installed. Using local session storage instead.",
            }
        return result
    except ImportError as e:
        if "unified_memory" in str(e):
            return {
                "sessions": [],
                "limit": limit,
                "status": "unified_memory_unavailable",
                "message": "unified_memory module not installed. Using local session storage instead.",
            }
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"mind_get_session_history failed: {e}")
        return {"error": str(e)}


def mind_get_active_workflow() -> dict[str, Any]:
    """Get currently active BMAD workflow and step."""
    try:
        from packages.nx_mind_mcp import get_active_workflow

        return get_active_workflow()
    except Exception as e:
        logger.error(f"mind_get_active_workflow failed: {e}")
        return {"error": str(e)}


def mind_set_context(key: str, value: str) -> dict[str, Any]:
    """Set project context for current session."""
    try:
        from packages.nx_mind_mcp import set_context

        return set_context(key, value)
    except Exception as e:
        logger.error(f"mind_set_context failed: {e}")
        return {"error": str(e)}


def mind_get_project_manifest() -> dict[str, Any]:
    """Get project metadata and progress."""
    try:
        from packages.nx_mind_mcp import get_project_manifest

        return get_project_manifest()
    except Exception as e:
        logger.error(f"mind_get_project_manifest failed: {e}")
        return {"error": str(e)}
