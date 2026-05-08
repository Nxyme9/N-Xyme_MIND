"""
Learning namespace tools for nx-brain-mcp.

This module contains all learning-related MCP tools.
"""

from __future__ import annotations

from typing import Optional


def learning_route_task(task_description: str) -> dict[str, any]:
    """Get routing recommendation for a task using AdaptiveRouter with Q-Learning."""
    try:
        from packages.learning_engine.mcp_server import route_task

        return route_task(task_description)
    except Exception as e:
        return {"error": str(e)}


def learning_record_outcome(
    task: str, agent: str, success: bool, latency_ms: int = 0, tokens_used: int = 0
) -> dict[str, any]:
    """Record a delegation outcome for learning."""
    try:
        from packages.learning_engine.mcp_server import record_outcome

        return record_outcome(task, agent, success, latency_ms, tokens_used)
    except Exception as e:
        return {"error": str(e)}


def learning_status() -> dict[str, any]:
    """Get current learning system status (routing weights, A/B tests)."""
    try:
        from packages.learning_engine.mcp_server import status

        return status()
    except Exception as e:
        return {"error": str(e)}


def learning_get_recommendations(task_description: str) -> dict[str, any]:
    """Get agent recommendations for a task."""
    try:
        from packages.learning_engine.delegation import get_routing_recommendations

        result = get_routing_recommendations()
        if isinstance(result, dict) and result.get("error") == "no delegations found":
            return {
                "recommendations": [],
                "task_description": task_description,
                "status": "no_data_yet",
                "message": "No delegation history yet. The system learns from usage.",
            }
        return result
    except Exception as e:
        return {"error": str(e)}


def learning_get_outcomes(
    agent: Optional[str] = None, task_type: Optional[str] = None, limit: int = 100
) -> dict[str, any]:
    """Retrieve delegation outcomes with optional filters."""
    try:
        from packages.learning_engine.mcp_server import get_outcomes

        return get_outcomes(agent, task_type, limit)
    except Exception as e:
        return {"error": str(e)}
