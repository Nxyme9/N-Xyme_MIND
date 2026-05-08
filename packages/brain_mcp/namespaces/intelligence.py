"""
Intelligence namespace tools for nx-brain-mcp.

This module contains all intelligence-related MCP tools.
"""

from __future__ import annotations

import asyncio


def intelligence_route(task_description: str) -> dict[str, any]:
    """Route a task to the optimal agent."""
    try:
        from packages.intelligence import route

        return asyncio.run(route(task_description))
    except Exception as e:
        return {"error": str(e)}


def intelligence_score_complexity(task_description: str) -> dict[str, any]:
    """Score the complexity of a task (L1-L5)."""
    try:
        from packages.intelligence import score_complexity

        return score_complexity(task_description)
    except Exception as e:
        return {"error": str(e)}


def intelligence_available_agents() -> dict[str, any]:
    """List available agents."""
    try:
        from packages.intelligence.mcp_server import available_agents

        return available_agents()
    except Exception as e:
        return {"error": str(e)}


def intelligence_get_routing_history(limit: int = 10) -> dict[str, any]:
    """Get recent routing decisions."""
    try:
        from packages.intelligence.mcp_server import get_routing_history

        return get_routing_history(limit)
    except Exception as e:
        return {"error": str(e)}
