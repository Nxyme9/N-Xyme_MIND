"""Intelligence MCP Server — exposes task routing and delegation intelligence as MCP tools."""

from __future__ import annotations

import traceback
import asyncio
from typing import Any, Dict, List

from fastmcp import FastMCP

mcp = FastMCP("N-Xyme Intelligence")


# In-memory routing history for get_routing_history
_routing_history: List[Dict[str, Any]] = []


@mcp.tool()
async def route(task_description: str) -> Dict[str, Any]:
    """Route a task to the optimal agent.
    
    Args:
        task_description: The task to route
    
    Returns:
        Dict with level, agent, confidence, and strategy
    """
    try:
        from packages.intelligence import route as _route
        
        result = await _route(task_description)
        
        # Add to history
        _routing_history.append({
            "task": task_description,
            "level": result.level,
            "agent": result.agent,
            "confidence": result.confidence,
            "strategy": result.strategy_used
        })
        # Keep only last 100 entries
        if len(_routing_history) > 100:
            _routing_history.pop(0)
        
        return {
            "status": "success",
            "level": result.level,
            "agent": result.agent,
            "confidence": result.confidence,
            "strategy": result.strategy_used
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def score_complexity(task_description: str) -> Dict[str, Any]:
    """Score the complexity of a task (L1-L5).
    
    Args:
        task_description: The task to score
    
    Returns:
        Dict with level, tokens, and complexity factors
    """
    try:
        from packages.intelligence import score_complexity as _score
        
        result = _score(task_description)
        
        return {
            "status": "success",
            "level": result.level,
            "confidence": result.confidence,
            "reason": result.reason
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def available_agents() -> Dict[str, Any]:
    """List available agents.
    
    Returns:
        Dict with agent list
    """
    try:
        from packages.intelligence import available_agents as _agents
        
        agents = _agents()
        
        return {
            "status": "success",
            "agents": agents,
            "count": len(agents)
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def get_routing_history(limit: int = 10) -> Dict[str, Any]:
    """Get recent routing decisions.
    
    Args:
        limit: Maximum number of entries to return (default 10)
    
    Returns:
        Dict with routing history list
    """
    try:
        history = _routing_history[-limit:] if limit > 0 else _routing_history
        
        return {
            "status": "success",
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


if __name__ == "__main__":
    mcp.run()