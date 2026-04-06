"""Learning Engine MCP Server — exposes learning system as MCP tools."""

from __future__ import annotations

import sqlite3
import traceback
from typing import Any, Dict, Optional

from fastmcp import FastMCP

mcp = FastMCP("N-Xyme Learning Engine")

# ============================================================================
# MODEL CAPABILITIES (merged from intelligent_router_mcp)
# ============================================================================

MODEL_CAPABILITIES = {
    "qwen3.6-plus-free": {
        "reasoning": 0.95,
        "coding": 0.92,
        "creative": 0.88,
        "math": 0.90,
        "analysis": 0.93,
        "summarization": 0.90,
        "context_window": 1000000,
    },
    "qwen3.6-plus": {
        "reasoning": 0.95,
        "coding": 0.92,
        "creative": 0.88,
        "math": 0.90,
        "analysis": 0.93,
        "summarization": 0.90,
        "context_window": 131072,
    },
    "qwen3-coder": {
        "reasoning": 0.85,
        "coding": 0.97,
        "creative": 0.75,
        "math": 0.80,
        "analysis": 0.82,
        "summarization": 0.78,
        "context_window": 131072,
    },
    "deepseek-r1": {
        "reasoning": 0.93,
        "coding": 0.88,
        "creative": 0.82,
        "math": 0.91,
        "analysis": 0.90,
        "summarization": 0.85,
        "context_window": 131072,
    },
    "minimax-m2.5": {
        "reasoning": 0.72,
        "coding": 0.70,
        "creative": 0.78,
        "math": 0.70,
        "analysis": 0.75,
        "summarization": 0.80,
        "context_window": 32768,
    },
    "gemini-2.5-flash": {
        "reasoning": 0.82,
        "coding": 0.78,
        "creative": 0.85,
        "math": 0.80,
        "analysis": 0.85,
        "summarization": 0.88,
        "context_window": 1048576,
    },
}


@mcp.tool()
def record_outcome(
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
        # Import from package - use package-relative import
        from packages.learning_engine import record_outcome as _record

        # Extract level from task if possible (default to 3)
        level = 3  # Default complexity
        _record(agent=agent, level=level, success=success, latency_ms=latency_ms)

        return {
            "status": "success",
            "recorded": {"task": task, "agent": agent, "success": success},
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def route_task(task_description: str) -> Dict[str, Any]:
    """Get routing recommendation for a task using AdaptiveRouter with Q-Learning.

    Uses learned routing decisions from past outcomes. Falls back to
    heuristic routing during cold start (first 50 decisions).

    Args:
        task_description: The task to route

    Returns:
        Dict with level, agent, confidence, strategy, and learning info
    """
    try:
        from packages.learning_engine.routing.adaptive_router import AdaptiveRouter

        router = AdaptiveRouter()
        result = router.route(task_description)

        return {
            "status": "success",
            "agent": result.get("agent", "hephaestus"),
            "level": result.get("level", 3),
            "confidence": result.get("confidence", 0.5),
            "reason": result.get("reason", "AdaptiveRouter recommendation"),
            "learning": {
                "decisions_made": result.get("decisions_made", 0),
                "cold_start": result.get("decisions_made", 0) < 50,
            },
        }
    except Exception as e:
        # Fallback to old routing if AdaptiveRouter fails
        try:
            from packages.learning_engine import route_task as _route

            level = 3
            result = _route(task_description=task_description, level=level)

            return {
                "status": "success",
                "agent": result.recommended_agent,
                "confidence": result.confidence,
                "reason": result.reason,
                "learning": {"cold_start": True, "decisions_made": 0},
            }
        except Exception as e2:
            return {
                "status": "error",
                "error": str(e2),
                "traceback": traceback.format_exc(),
            }


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
            ],
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def learning_stats() -> Dict[str, Any]:
    """Get Q-Learning statistics, agent performance, and routing weights.

    Returns:
        Dict with learning stats, agent performance, and routing weights
    """
    try:
        from packages.learning_engine.outcome_logger import OutcomeLogger

        logger = OutcomeLogger()
        agent_stats = logger.get_all_agent_stats()

        # Get Q-Learning stats if available
        q_learning_stats = {}
        try:
            from packages.learning_engine.routing.adaptive_router import (
                AdaptiveRouter,
            )

            # Create temporary router to get stats
            temp_router = AdaptiveRouter()
            q_learning_stats = temp_router.get_learning_stats()
        except Exception:
            pass

        return {
            "status": "success",
            "agent_performance": agent_stats,
            "q_learning": q_learning_stats,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def log_outcome(
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
        from packages.learning_engine.outcome_logger import (
            DelegationOutcome,
            OutcomeLogger,
        )

        outcome = DelegationOutcome(
            task_id=task_id,
            task_description=task_description,
            task_type=task_type,
            agent=agent,
            level=level,
            success=success,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
        )

        logger = OutcomeLogger()
        outcome_id = logger.log(outcome)

        return {
            "status": "success",
            "outcome_id": outcome_id,
            "logged": {
                "task_id": task_id,
                "task_type": task_type,
                "agent": agent,
                "level": level,
                "success": success,
            },
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def get_outcomes(
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
        from packages.learning_engine.outcome_logger import OutcomeLogger

        logger = OutcomeLogger()
        outcomes = logger.get_outcomes(agent=agent, task_type=task_type, limit=limit)

        return {
            "status": "success",
            "count": len(outcomes),
            "outcomes": [
                {
                    "task_id": o.task_id,
                    "task_description": o.task_description,
                    "task_type": o.task_type,
                    "agent": o.agent,
                    "level": o.level,
                    "success": o.success,
                    "latency_ms": o.latency_ms,
                    "tokens_used": o.tokens_used,
                    "timestamp": o.timestamp,
                }
                for o in outcomes
            ],
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


if __name__ == "__main__":
    mcp.run()


@mcp.tool()
def get_learning_progress() -> Dict[str, Any]:
    """Get real-time learning progress statistics for dashboard (T8.3).

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
        from packages.learning_engine.routing.adaptive_router import AdaptiveRouter
        from packages.learning_engine.outcome_logger import OutcomeLogger

        # Get Q-Learning stats from AdaptiveRouter
        router = AdaptiveRouter()
        learning_stats = router.get_learning_stats()

        # Get agent stats from OutcomeLogger
        logger = OutcomeLogger()
        agent_stats = logger.get_all_agent_stats()

        # Get top performer per task type
        conn = sqlite3.connect(logger.db_path)
        rows = conn.execute(
            """SELECT task_type, agent,
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes
               FROM outcomes GROUP BY task_type, agent"""
        ).fetchall()
        conn.close()

        # Find top agent per task type
        task_type_best: dict[str, dict[str, Any]] = {}
        for row in rows:
            task_type, agent, total, successes = row
            success_rate = successes / total if total > 0 else 0
            if (
                task_type not in task_type_best
                or success_rate > task_type_best[task_type]["success_rate"]
            ):
                task_type_best[task_type] = {
                    "agent": agent,
                    "success_rate": success_rate,
                    "total": total,
                }

        # Determine Q-Learning convergence status
        convergence_status = "warming_up"
        if learning_stats.total_decisions >= 100:
            if abs(learning_stats.improvement_trend) < 0.05:
                convergence_status = "converged"
            elif learning_stats.improvement_trend > 0.1:
                convergence_status = "improving"
            elif learning_stats.improvement_trend < -0.1:
                convergence_status = "degrading"
            else:
                convergence_status = "stable"
        elif learning_stats.total_decisions >= 50:
            convergence_status = "learning"

        # Compute exploration vs exploitation ratio
        total_actions = (
            learning_stats.exploration_count + learning_stats.exploitation_count
        )
        if total_actions > 0:
            exploration_ratio = learning_stats.exploration_count / total_actions
            exploitation_ratio = learning_stats.exploitation_count / total_actions
        else:
            exploration_ratio = 0.5
            exploitation_ratio = 0.5

        # Recent reward trend (last 20)
        recent_rewards = (
            learning_stats.recent_rewards[-20:] if learning_stats.recent_rewards else []
        )
        reward_trend = "neutral"
        if len(recent_rewards) >= 10:
            first_half = sum(recent_rewards[:5]) / 5
            second_half = sum(recent_rewards[5:10]) / 5
            if second_half > first_half + 0.1:
                reward_trend = "improving"
            elif second_half < first_half - 0.1:
                reward_trend = "declining"
            else:
                reward_trend = "stable"

        return {
            "status": "success",
            "total_decisions": learning_stats.total_decisions,
            "success_rate_over_time": {
                "current": round(learning_stats.success_rate, 3),
                "trend": learning_stats.improvement_trend,
            },
            "top_performers": task_type_best,
            "q_learning_convergence": {
                "status": convergence_status,
                "average_q_value": learning_stats.average_q_value,
                "total_decisions": learning_stats.total_decisions,
            },
            "exploration_exploitation_ratio": {
                "exploration": round(exploration_ratio, 3),
                "exploitation": round(exploitation_ratio, 3),
                "exploration_count": learning_stats.exploration_count,
                "exploitation_count": learning_stats.exploitation_count,
            },
            "recent_reward_trend": {
                "status": reward_trend,
                "recent_rewards": recent_rewards,
            },
            "agent_overall_performance": agent_stats,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}
