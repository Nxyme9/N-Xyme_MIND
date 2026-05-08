"""
Catalyst namespace tools for nx-brain-mcp.

This module contains all catalyst-related MCP tools.
Functions are registered manually in __init__.py after MCP is available.
"""

from __future__ import annotations

from typing import Optional


# ============================================================================
# CATALYST TOOLS (catalyst.*)
# ============================================================================


def catalyst_orchestrate(
    user_input: str, context: Optional[dict] = None
) -> dict[str, any]:
    """Orchestrate BMAD workflow based on user input."""
    try:
        from packages.catalyst_orchestrator.mcp_server import orchestrate

        return orchestrate(user_input, context)
    except Exception as e:
        return {"error": str(e)}


def catalyst_detect_state(user_input: str) -> dict[str, any]:
    """Detect user state (FLOW, FRICTION, or ADAPT) from input."""
    try:
        from packages.catalyst_orchestrator.mcp_server import detect_state

        return detect_state(user_input)
    except Exception as e:
        return {"error": str(e)}


def catalyst_list_workflows() -> dict[str, any]:
    """List all available BMAD workflows."""
    try:
        from packages.catalyst_orchestrator.mcp_server import list_workflows

        return list_workflows()
    except Exception as e:
        return {"error": str(e)}


def catalyst_get_orchestrator_status() -> dict[str, any]:
    """Get current orchestrator status."""
    try:
        from packages.catalyst_orchestrator.mcp_server import get_orchestrator_status

        return get_orchestrator_status()
    except Exception as e:
        return {"error": str(e)}
