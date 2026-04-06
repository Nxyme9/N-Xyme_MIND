"""
trigger-guardian-mcp
====================
MCP Tool Server for trigger phrase monitoring and routing.
Enables workflow initiation and agent handoff detection.

Transport: stdio (default), SSE (optional via --sse flag).
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Server Init
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="trigger-guardian",
    version="1.0.0",
    instructions=(
        "Trigger Guardian MCP Server — monitor and route trigger phrases.\n\n"
        "Tools:\n"
        "- register_trigger: Register a trigger phrase with callback action\n"
        "- list_triggers: List all registered triggers\n"
        "- check_trigger: Check if input matches any registered trigger\n"
        "- get_trigger_handlers: Return handlers for a matched trigger\n"
        "- log_trigger_event: Log trigger activation for analytics\n"
        "- clear_triggers: Clear all registered triggers\n"
    ),
)

logger = logging.getLogger("trigger-guardian-mcp")

# ---------------------------------------------------------------------------
# In-Memory Trigger Registry
# ---------------------------------------------------------------------------

class TriggerRegistry:
    """In-memory registry for trigger phrases and their handlers."""
    
    def __init__(self):
        self._triggers: Dict[str, dict] = {}
        self._event_log: List[dict] = []
        # Load default triggers
        self._load_defaults()
    
    def _load_defaults(self):
        """Load default triggers from built-in patterns."""
        defaults = [
            {
                "phrase": "/start-work",
                "description": "Start a new work session",
                "handler": "skill",
                "handler_target": "start-work",
                "pattern_type": "exact"
            },
            {
                "phrase": "/handoff",
                "description": "Hand off to another agent/session",
                "handler": "skill",
                "handler_target": "handoff",
                "pattern_type": "exact"
            },
            {
                "phrase": "/git-master",
                "description": "Git operations with master workflow",
                "handler": "skill",
                "handler_target": "git-master",
                "pattern_type": "exact"
            },
            {
                "phrase": "/refactor",
                "description": "Intelligent refactoring command",
                "handler": "skill",
                "handler_target": "refactor",
                "pattern_type": "exact"
            },
            {
                "phrase": "/playwright",
                "description": "Browser automation with Playwright",
                "handler": "skill",
                "handler_target": "playwright",
                "pattern_type": "exact"
            },
            {
                "phrase": "/dev-browser",
                "description": "Persistent browser automation",
                "handler": "skill",
                "handler_target": "dev-browser",
                "pattern_type": "exact"
            },
        ]
        
        for trigger in defaults:
            self.register(
                phrase=trigger["phrase"],
                description=trigger["description"],
                handler=trigger["handler"],
                handler_target=trigger["handler_target"],
                pattern_type=trigger["pattern_type"]
            )
    
    def register(
        self,
        phrase: str,
        description: str = "",
        handler: str = "callback",
        handler_target: str = "",
        pattern_type: str = "exact"
    ) -> dict:
        """Register a new trigger phrase."""
        if phrase in self._triggers:
            return {
                "success": False,
                "error": f"Trigger '{phrase}' already registered",
                "phrase": phrase
            }
        
        self._triggers[phrase] = {
            "phrase": phrase,
            "description": description,
            "handler": handler,
            "handler_target": handler_target,
            "pattern_type": pattern_type,
            "registered_at": datetime.now().isoformat(),
            "trigger_count": 0,
            "last_triggered": None
        }
        
        return {
            "success": True,
            "phrase": phrase,
            "registered": True
        }
    
    def list_all(self) -> dict:
        """List all registered triggers."""
        return {
            "triggers": list(self._triggers.values()),
            "count": len(self._triggers),
            "timestamp": datetime.now().isoformat()
        }
    
    def check(self, input_text: str) -> dict:
        """Check if input matches any registered trigger."""
        matched = None
        
        for phrase, trigger in self._triggers.items():
            pattern_type = trigger.get("pattern_type", "exact")
            
            if pattern_type == "exact":
                if input_text.strip() == phrase:
                    matched = trigger
                    break
            elif pattern_type == "prefix":
                if input_text.strip().startswith(phrase):
                    matched = trigger
                    break
            elif pattern_type == "regex":
                try:
                    if re.search(phrase, input_text):
                        matched = trigger
                        break
                except re.error:
                    pass
        
        result = {
            "input": input_text,
            "matched": matched is not None,
            "trigger": None,
            "timestamp": datetime.now().isoformat()
        }
        
        if matched:
            result["trigger"] = matched
            # Update trigger stats
            matched["trigger_count"] += 1
            matched["last_triggered"] = datetime.now().isoformat()
        
        return result
    
    def get_handlers(self, phrase: str) -> dict:
        """Get handlers for a specific trigger phrase."""
        trigger = self._triggers.get(phrase)
        
        if not trigger:
            return {
                "found": False,
                "phrase": phrase,
                "error": f"Trigger '{phrase}' not found"
            }
        
        return {
            "found": True,
            "phrase": phrase,
            "handler": trigger.get("handler"),
            "handler_target": trigger.get("handler_target"),
            "description": trigger.get("description")
        }
    
    def log_event(
        self,
        phrase: str,
        input_text: str,
        metadata: dict = None
    ) -> dict:
        """Log a trigger activation event."""
        event = {
            "phrase": phrase,
            "input": input_text,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self._event_log.append(event)
        
        return {
            "success": True,
            "event_id": len(self._event_log) - 1,
            "logged": True
        }
    
    def clear(self) -> dict:
        """Clear all registered triggers (keeps event log)."""
        count = len(self._triggers)
        self._triggers.clear()
        
        return {
            "success": True,
            "cleared_count": count,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_events(self, limit: int = 50) -> dict:
        """Get recent trigger events."""
        return {
            "events": self._event_log[-limit:],
            "total_events": len(self._event_log),
            "timestamp": datetime.now().isoformat()
        }


# Global registry instance
_registry = TriggerRegistry()

# ---------------------------------------------------------------------------
# TOOL: register_trigger
# ---------------------------------------------------------------------------

@mcp.tool(tags={"trigger", "register"})
def register_trigger(
    phrase: str,
    description: str = "",
    handler: str = "callback",
    handler_target: str = "",
    pattern_type: str = "exact"
) -> dict:
    """
    Registers a trigger phrase with callback action.
    
    Args:
        phrase: The trigger phrase to register (e.g., "/my-command")
        description: Human-readable description of the trigger
        handler: Handler type ("callback", "skill", "function", "workflow")
        handler_target: Target identifier for the handler
        pattern_type: Matching pattern ("exact", "prefix", "regex")
    
    Returns:
        dict with registration status
    """
    if not phrase:
        return {
            "success": False,
            "error": "Phrase cannot be empty"
        }
    
    valid_patterns = ["exact", "prefix", "regex"]
    if pattern_type not in valid_patterns:
        return {
            "success": False,
            "error": f"Invalid pattern_type. Must be one of: {valid_patterns}"
        }
    
    return _registry.register(
        phrase=phrase,
        description=description,
        handler=handler,
        handler_target=handler_target,
        pattern_type=pattern_type
    )


# ---------------------------------------------------------------------------
# TOOL: list_triggers
# ---------------------------------------------------------------------------

@mcp.tool(tags={"trigger", "list"})
def list_triggers() -> dict:
    """
    Lists all registered triggers.
    
    Returns:
        dict with list of all triggers and count
    """
    return _registry.list_all()


# ---------------------------------------------------------------------------
# TOOL: check_trigger
# ---------------------------------------------------------------------------

@mcp.tool(tags={"trigger", "check"})
def check_trigger(input_text: str) -> dict:
    """
    Checks if input matches any registered trigger.
    
    Args:
        input_text: The input string to check
    
    Returns:
        dict with match result and trigger info if matched
    """
    if not input_text:
        return {
            "input": input_text,
            "matched": False,
            "error": "Input cannot be empty"
        }
    
    return _registry.check(input_text)


# ---------------------------------------------------------------------------
# TOOL: get_trigger_handlers
# ---------------------------------------------------------------------------

@mcp.tool(tags={"trigger", "handlers"})
def get_trigger_handlers(phrase: str) -> dict:
    """
    Returns handlers for a matched trigger.
    
    Args:
        phrase: The trigger phrase to get handlers for
    
    Returns:
        dict with handler information
    """
    if not phrase:
        return {
            "found": False,
            "error": "Phrase cannot be empty"
        }
    
    return _registry.get_handlers(phrase)


# ---------------------------------------------------------------------------
# TOOL: log_trigger_event
# ---------------------------------------------------------------------------

@mcp.tool(tags={"trigger", "log", "analytics"})
def log_trigger_event(
    phrase: str,
    input_text: str,
    metadata: dict = None
) -> dict:
    """
    Logs trigger activation for analytics.
    
    Args:
        phrase: The matched trigger phrase
        input_text: The original input that triggered it
        metadata: Additional metadata to log
    
    Returns:
        dict with logging status
    """
    if not phrase:
        return {
            "success": False,
            "error": "Phrase cannot be empty"
        }
    
    if not input_text:
        return {
            "success": False,
            "error": "Input text cannot be empty"
        }
    
    return _registry.log_event(phrase, input_text, metadata)


# ---------------------------------------------------------------------------
# TOOL: clear_triggers
# ---------------------------------------------------------------------------

@mcp.tool(tags={"trigger", "clear"})
def clear_triggers() -> dict:
    """
    Clears all registered triggers.
    
    Note: This does not clear the event log, only the trigger registry.
    
    Returns:
        dict with clear operation status
    """
    return _registry.clear()


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Trigger Guardian MCP Server")
    parser.add_argument("--sse", action="store_true", help="Use SSE transport")
    parser.add_argument("--port", type=int, default=8767, help="SSE port")
    args = parser.parse_args()
    
    if args.sse:
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run(transport="stdio")