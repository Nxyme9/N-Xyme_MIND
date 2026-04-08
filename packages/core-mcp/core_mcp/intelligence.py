"""Intelligence tools for core-mcp - delegates to intelligence implementation."""

from __future__ import annotations

import traceback
from typing import Any, Dict

from core_mcp import mcp


# Import original tool implementations from intelligence package
def _import_intelligence():
    """Import the intelligence MCP server module."""
    import packages.intelligence.mcp_server as intelligence

    return intelligence


# ---------------------------------------------------------------------------
# Tool Wrappers - Register with intelligence_ prefix
# ---------------------------------------------------------------------------


@mcp.tool()
async def intelligence_route(task_description: str) -> Dict[str, Any]:
    """Route a task to the optimal agent.

    Args:
        task_description: The task to route

    Returns:
        Dict with level, agent, confidence, and strategy
    """
    try:
        intelligence = _import_intelligence()
        return await intelligence.route(task_description)
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def intelligence_score_complexity(task_description: str) -> Dict[str, Any]:
    """Score the complexity of a task (L1-L5).

    Args:
        task_description: The task to score

    Returns:
        Dict with level, tokens, and complexity factors
    """
    try:
        intelligence = _import_intelligence()
        return intelligence.score_complexity(task_description)
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def intelligence_available_agents() -> Dict[str, Any]:
    """List available agents.

    Returns:
        Dict with agent list
    """
    try:
        intelligence = _import_intelligence()
        return intelligence.available_agents()
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def intelligence_routing_history(limit: int = 10) -> Dict[str, Any]:
    """Get recent routing decisions.

    Args:
        limit: Maximum number of entries to return (default 10)

    Returns:
        Dict with routing history list
    """
    try:
        intelligence = _import_intelligence()
        return intelligence.get_routing_history(limit)
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}
