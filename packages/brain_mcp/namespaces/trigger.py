"""
Trigger namespace tools for nx-brain-mcp.

This module contains all trigger-related MCP tools.
Functions are registered manually in __init__.py after MCP is available.
"""

from __future__ import annotations

from typing import Optional


# ============================================================================
# TRIGGER TOOLS (trigger.*)
# ============================================================================


def trigger_register(
    phrase: str,
    description: str = "",
    handler: str = "callback",
    handler_target: str = "",
    pattern_type: str = "exact",
) -> dict[str, any]:
    """Register a trigger phrase with callback action."""
    try:
        from trigger_guardian_mcp import register_trigger

        return register_trigger(
            phrase, description, handler, handler_target, pattern_type
        )
    except Exception as e:
        return {"error": str(e)}


def trigger_list() -> dict[str, any]:
    """List all registered triggers."""
    try:
        from trigger_guardian_mcp import list_triggers

        return list_triggers()
    except Exception as e:
        return {"error": str(e)}


def trigger_check(input_text: str) -> dict[str, any]:
    """Check if input matches any registered trigger."""
    try:
        from trigger_guardian_mcp import check_trigger

        return check_trigger(input_text)
    except Exception as e:
        return {"error": str(e)}


def trigger_clear() -> dict[str, any]:
    """Clear all registered triggers."""
    try:
        from trigger_guardian_mcp import clear_triggers

        return clear_triggers()
    except Exception as e:
        return {"error": str(e)}


def trigger_execute(phrase: str, args: Optional[dict] = None) -> dict[str, any]:
    """Execute a trigger's callback handler."""
    try:
        from trigger_guardian_mcp import execute_trigger

        return execute_trigger(phrase, args)
    except Exception as e:
        return {"error": str(e)}
