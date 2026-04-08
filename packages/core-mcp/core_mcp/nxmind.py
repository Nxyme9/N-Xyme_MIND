"""nxmind - N-Xyme MIND tools for core-mcp.

Imports all 12 tool functions from nx_mind_mcp and re-registers them with nxmind_ prefix.
Each tool delegates to the original implementation in nx_mind_mcp.
"""

from __future__ import annotations

from typing import Any, Optional

# Import shared mcp instance from core_mcp
from core_mcp import mcp

# Import all tool functions from nx_mind_mcp
from nx_mind_mcp import (
    get_active_workflow,
    get_mind_state,
    get_project_manifest,
    get_session_context,
    get_session_history,
    log_task_completion,
    set_context,
    spine_probe,
    spine_run,
    spine_status,
    sync_to_memory,
    update_mind_state,
)

# ---------------------------------------------------------------------------
# Wrapper Functions with nxmind_ prefix
# ---------------------------------------------------------------------------
# Each function wraps the original implementation, forwarding all parameters
# ---------------------------------------------------------------------------


@mcp.tool()
def nxmind_get_session_context() -> str:
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
    return get_session_context()


@mcp.tool()
def nxmind_log_task_completion(
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
    return log_task_completion(
        task_id=task_id,
        description=description,
        success=success,
        agent=agent,
        duration_ms=duration_ms,
    )


@mcp.tool()
def nxmind_get_mind_state() -> dict[str, Any]:
    """Get current MIND state.

    Returns:
        Dict with project, phase, active_tasks, context, and timestamps.
    """
    return get_mind_state()


@mcp.tool()
def nxmind_update_mind_state(
    project: Optional[str] = None,
    phase: Optional[str] = None,
    active_tasks: Optional[list[str]] = None,
    context: Optional[dict[str, str]] = None,
    clear_context: bool = False,
) -> dict[str, Any]:
    """Update MIND state with new information.

    Args:
        project: Project name
        phase: Current phase
        active_tasks: List of active tasks
        context: Key-value pairs for context
        clear_context: Whether to clear existing context

    Returns:
        Dict with status and message.
    """
    return update_mind_state(
        project=project,
        phase=phase,
        active_tasks=active_tasks,
        context=context,
        clear_context=clear_context,
    )


@mcp.tool()
def nxmind_get_session_history(limit: int = 10) -> dict[str, Any]:
    """Get history of past sessions with summaries.

    Args:
        limit: Maximum number of sessions to return

    Returns:
        Dict with sessions list and count.
    """
    return get_session_history(limit=limit)


@mcp.tool()
def nxmind_get_active_workflow() -> dict[str, Any]:
    """Get currently active BMAD workflow and step.

    Returns:
        Dict with workflow, phase, and step.
    """
    return get_active_workflow()


@mcp.tool()
def nxmind_set_context(key: str, value: str) -> dict[str, Any]:
    """Set project context for current session.

    Args:
        key: Context key
        value: Context value

    Returns:
        Dict with status, key, and value.
    """
    return set_context(key=key, value=value)


@mcp.tool()
def nxmind_sync_to_memory(target: str = "memory") -> dict[str, Any]:
    """Sync MIND state to memory MCP.

    Args:
        target: Target MCP (memory or unified-memory)

    Returns:
        Dict with status and target.
    """
    return sync_to_memory(target=target)


@mcp.tool()
def nxmind_get_project_manifest() -> dict[str, Any]:
    """Get project metadata and progress.

    Returns:
        Dict with name, description, version, progress, and milestones.
    """
    return get_project_manifest()


@mcp.tool()
def nxmind_spine_probe() -> dict[str, Any]:
    """Run GoldenSpine health check across all 3 layers.

    Returns:
        Dict with process, model, and responsive layer health results.
    """
    return spine_probe()


@mcp.tool()
def nxmind_spine_run(prompt: str, model: Optional[str] = None) -> dict[str, Any]:
    """Execute inference via GoldenSpine with resilience pipeline.

    Args:
        prompt: The prompt to send to the model
        model: Optional model override (uses config default if not set)

    Returns:
        Dict with run_id, model, success, latency_ms, and error if any.
    """
    return spine_run(prompt=prompt, model=model)


@mcp.tool()
def nxmind_spine_status() -> dict[str, Any]:
    """Get current GoldenSpine status.

    Returns:
        Dict with running state, run count, health, fallback status, and run stats.
    """
    return spine_status()


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "nxmind_get_session_context",
    "nxmind_log_task_completion",
    "nxmind_get_mind_state",
    "nxmind_update_mind_state",
    "nxmind_get_session_history",
    "nxmind_get_active_workflow",
    "nxmind_set_context",
    "nxmind_sync_to_memory",
    "nxmind_get_project_manifest",
    "nxmind_spine_probe",
    "nxmind_spine_run",
    "nxmind_spine_status",
]
