"""Orchestration MCP Server — exposes agent coordination as MCP tools."""

from __future__ import annotations

import traceback
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

mcp = FastMCP("N-Xyme Orchestration")


@mcp.tool()
def spawn(agent: str, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Spawn an agent task.
    
    Args:
        agent: Agent name (e.g., "hephaestus", "explore", "oracle")
        task: Task description
        context: Optional context dict with additional parameters
    
    Returns:
        Dict with task_id and status
    """
    try:
        from packages.orchestration import spawn as _spawn
        
        task_id = _spawn(agent=agent, task=task, context=context)
        
        return {
            "status": "success",
            "task_id": task_id,
            "agent": agent,
            "task": task
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def task_status(task_id: str) -> Dict[str, Any]:
    """Get status of a task.
    
    Args:
        task_id: Task ID returned by spawn()
    
    Returns:
        Dict with task status information
    """
    try:
        from packages.orchestration import task_status as _status
        
        result = _status(task_id=task_id)
        
        return {"status": "success", **result}
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def tools_list() -> Dict[str, Any]:
    """List all available tools.
    
    Returns:
        Dict with tool list
    """
    try:
        from packages.orchestration import tools_list as _tools
        
        tools = _tools()
        
        return {
            "status": "success",
            "tools": tools,
            "count": len(tools)
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def get_session_state() -> Dict[str, Any]:
    """Get current session state.
    
    Returns:
        Dict with session state information
    """
    try:
        from packages.orchestration.sessions.manager import SessionManager
        
        # Create a session manager to get current state
        # Note: This returns basic info - in production would use singleton
        session_mgr = SessionManager()
        active_sessions = session_mgr.list_active(max_age_seconds=3600)
        
        return {
            "status": "success",
            "active_sessions": len(active_sessions),
            "sessions": [
                {
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "created": s.get("created"),
                    "last_active": s.get("last_active")
                }
                for s in active_sessions
            ]
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


if __name__ == "__main__":
    mcp.run()