"""Learning tools for core-mcp - delegates to learning_engine implementation."""

from __future__ import annotations

import traceback
from typing import Any, Dict, Optional

from core_mcp import mcp


# Import implementations from learning_engine package
def _import_learning_engine():
    """Import the learning engine MCP server module."""
    import packages.learning_engine.mcp_server as le

    return le


# =============================================================================
# Tool Wrappers - delegate to learning_engine.mcp_server
# =============================================================================


@mcp.tool()
def learning_record_outcome(
    task: str, agent: str, success: bool, latency_ms: float = 0, tokens_used: int = 0
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
        le = _import_learning_engine()
        return le.record_outcome(task, agent, success, latency_ms, tokens_used)
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def learning_route_task(task_description: str) -> Dict[str, Any]:
    """Get routing recommendation for a task using AdaptiveRouter with Q-Learning.

    Args:
        task_description: The task to route

    Returns:
        Dict with level, agent, confidence, strategy, and learning info
    """
    try:
        le = _import_learning_engine()
        return le.route_task(task_description)
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def learning_status() -> Dict[str, Any]:
    """Get current learning system status.

    Returns:
        Dict with routing weights, A/B tests, and learning stats
    """
    try:
        le = _import_learning_engine()
        return le.status()
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def learning_retrain() -> Dict[str, Any]:
    """Trigger retraining of learning models.

    Returns:
        Dict with retrain status
    """
    try:
        le = _import_learning_engine()
        return le.retrain()
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def learning_get_recommendations(task_description: str) -> Dict[str, Any]:
    """Get agent recommendations for a task.

    Args:
        task_description: The task to get recommendations for

    Returns:
        Dict with recommendations list
    """
    try:
        le = _import_learning_engine()
        return le.get_recommendations(task_description)
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def learning_q_stats() -> Dict[str, Any]:
    """Get Q-Learning statistics, agent performance, and routing weights.

    Returns:
        Dict with learning stats, agent performance, and routing weights
    """
    try:
        le = _import_learning_engine()
        return le.learning_stats()
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def learning_log_outcome(
    task_id: str,
    task_description: str,
    task_type: str,
    agent: str,
    level: int,
    success: bool,
    latency_ms: float,
    tokens_used: int = 0,
) -> Dict[str, Any]:
    """Log a delegation outcome using OutcomeLogger.

    Args:
        task_id: Unique identifier for the task
        task_description: Description of the task
        task_type: Type of task (implementation, research, review, fix)
        agent: Agent that handled the task
        level: Complexity level (L1-L5)
        success: Whether the task succeeded
        latency_ms: Execution latency in milliseconds
        tokens_used: Number of tokens used (default 0)

    Returns:
        Dict with status and logged outcome
    """
    try:
        le = _import_learning_engine()
        return le.log_outcome(
            task_id,
            task_description,
            task_type,
            agent,
            level,
            success,
            latency_ms,
            tokens_used,
        )
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def learning_get_outcomes(
    agent: Optional[str] = None,
    task_type: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """Retrieve delegation outcomes with optional filters.

    Args:
        agent: Filter by agent name (optional)
        task_type: Filter by task type (optional)
        limit: Maximum number of outcomes to return (default 100)

    Returns:
        Dict with list of outcomes
    """
    try:
        le = _import_learning_engine()
        return le.get_outcomes(agent, task_type, limit)
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def learning_get_progress() -> Dict[str, Any]:
    """Get real-time learning progress statistics for dashboard.

    Returns:
        Dict with:
        - total_decisions: Total decisions made
        - success_rate_over_time: Success rate trend
        - top_performers: Top agent per task type
        - q_learning_convergence: Convergence status
        - exploration_exploitation_ratio: Exploration vs exploitation
        - recent_reward_trend: Recent reward trend
    """
    try:
        le = _import_learning_engine()
        return le.get_learning_progress()
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}
