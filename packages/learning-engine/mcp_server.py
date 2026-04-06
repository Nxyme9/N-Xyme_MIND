"""Learning Engine MCP Server — exposes learning system as MCP tools."""

from __future__ import annotations

import traceback
from typing import Any, Dict, Optional

from fastmcp import FastMCP

mcp = FastMCP("N-Xyme Learning Engine")


@mcp.tool()
def record_outcome(
    task: str,
    agent: str,
    success: bool,
    latency_ms: float = 0,
    tokens_used: int = 0
) -> Dict[str, Any]:
    """Record a delegation outcome for learning.
    
    Args:
        task: Task description
        agent: The agent that handled the task
        success: Whether the task succeeded
        latency_ms: Execution latency in milliseconds
        tokens_used: Number of tokens used
    
    Returns:
        Dict with status and result
    """
    try:
        # Import from package - use package-relative import
        from packages.learning_engine import record_outcome as _record
        
        # Extract level from task if possible (default to 3)
        level = 3  # Default complexity
        _record(agent=agent, level=level, success=success, latency_ms=latency_ms)
        
        return {"status": "success", "recorded": {"task": task, "agent": agent, "success": success}}
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def route_task(task_description: str) -> Dict[str, Any]:
    """Get routing recommendation for a task.
    
    Args:
        task_description: The task to route
    
    Returns:
        Dict with level, agent, confidence, and strategy
    """
    try:
        from packages.learning_engine import route_task as _route
        
        # Default level for now
        level = 3
        result = _route(task_description=task_description, level=level)
        
        return {
            "status": "success",
            "level": result.level,
            "agent": result.agent,
            "confidence": result.confidence,
            "strategy": result.strategy
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def status() -> Dict[str, Any]:
    """Get current learning system status.
    
    Returns:
        Dict with routing weights, A/B tests, and learning stats
    """
    try:
        from packages.learning_engine import status as _status
        
        result = _status()
        return {"status": "success", **result}
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def retrain() -> Dict[str, Any]:
    """Trigger retraining of learning models.
    
    Returns:
        Dict with retrain status
    """
    try:
        from packages.learning_engine import retrain as _retrain
        
        _retrain()
        return {"status": "success", "message": "Retraining triggered"}
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def get_recommendations(task_description: str) -> Dict[str, Any]:
    """Get agent recommendations for a task.
    
    Args:
        task_description: The task to get recommendations for
    
    Returns:
        Dict with recommendations list
    """
    try:
        from packages.learning_engine.delegation import get_routing_recommendations
        
        recommendations = get_routing_recommendations(task_description)
        
        return {
            "status": "success",
            "recommendations": [
                {"agent": r.agent, "score": r.score, "reason": r.reason}
                for r in recommendations
            ]
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


if __name__ == "__main__":
    mcp.run()