#!/usr/bin/env python3
"""
nx_routing - Unified Routing System
===================================
Single source of truth for all routing decisions.

CONSOLIDATED FROM:
- packages/learning_engine/mcp_server.py (route_task, record_outcome)
- packages/intelligence/mcp_server.py (score_complexity)
- packages/session-pool-mcp/mcp_server.py (route_task)

This module provides:
- route_task(): Route to optimal agent using Q-Learning
- score_complexity(): L1-L5 complexity scoring
- record_outcome(): Log delegation outcomes for learning
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger("nx_routing")

_OUTCOME_SIGNING_KEY = os.environ.get("NXYME_OUTCOME_SIGNING_KEY", "")

ALLOWED_AGENTS = frozenset(
    {
        "hephaestus",
        "explore",
        "oracle",
        "librarian",
        "metis",
        "momus",
        "sisyphus",
        "sisyphus-junior",
        "atlas",
        "catalyst",
        "hybrid",
    }
)


def _generate_outcome_signature(
    task_id: str, agent: str, level: int, success: bool
) -> str:
    """Generate HMAC signature for outcome to prevent forgery."""
    if not _OUTCOME_SIGNING_KEY:
        return ""
    message = f"{task_id}:{agent}:{level}:{success}"
    return hmac.new(
        _OUTCOME_SIGNING_KEY.encode(), message.encode(), hashlib.sha256
    ).hexdigest()[:16]


def _verify_outcome_signature(
    task_id: str, agent: str, level: int, success: bool, signature: str
) -> bool:
    """Verify HMAC signature matches expected value."""
    if not signature:
        return _OUTCOME_SIGNING_KEY == ""
    expected = _generate_outcome_signature(task_id, agent, level, success)
    return hmac.compare_digest(signature, expected)


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass
class RoutingResult:
    """Result from route_task"""

    agent: str
    level: int
    confidence: float
    reason: str
    strategy: str = "adaptive"
    decisions_made: int = 0


@dataclass
class ComplexityResult:
    """Result from score_complexity"""

    level: int
    tokens: int
    factors: Dict[str, Any]


@dataclass
class OutcomeResult:
    """Result from record_outcome"""

    success: bool
    task_id: str


# ============================================================================
# COMPLEXITY SCORING (from intelligence)
# ============================================================================


def _compute_complexity(task_description: str) -> ComplexityResult:
    """Compute task complexity L1-L5 using keyword analysis."""
    task_lower = task_description.lower()

    # Complexity factors
    factors = {
        "length": len(task_description),
        "keywords": [],
        "multi_step": False,
        "unknown_domain": False,
    }

    # High complexity keywords
    high_complexity = [
        "architect",
        "redesign",
        "refactor",
        "create system",
        "design system",
        "multiple",
        "complex",
        "integrate",
        "pipeline",
        "security",
    ]
    # Medium complexity
    mid_complexity = ["add feature", "implement", "fix bug", "improve", "optimize"]
    # Low complexity
    low_complexity = ["typo", "fix error", "simple", "small"]

    for kw in high_complexity:
        if kw in task_lower:
            factors["keywords"].append(kw)
    for kw in mid_complexity:
        if kw in task_lower:
            factors["keywords"].append(kw)
    for kw in low_complexity:
        if kw in task_lower:
            factors["keywords"].append(kw)

    # Multi-step detection
    if any(x in task_lower for x in ["then", "and then", "after that", "finally"]):
        factors["multi_step"] = True

    # Compute level
    level = 1
    if factors["keywords"] or factors["multi_step"]:
        level = 2
    if any(kw in task_lower for kw in high_complexity):
        level = 4
    if len(task_description) > 500:
        level = min(5, level + 1)

    # Estimate tokens
    tokens = len(task_description) * 4 // 3

    return ComplexityResult(level=level, tokens=tokens, factors=factors)


def score_complexity(task_description: str) -> ComplexityResult:
    """Score the complexity of a task (L1-L5).

    Args:
        task_description: The task to score

    Returns:
        ComplexityResult with level, tokens, and factors
    """
    return _compute_complexity(task_description)


# ============================================================================
# Q-LEARNING ROUTING (from learning_engine)
# ============================================================================

import random

# FIX: Q-table with complexity levels (replaces static _Q_WEIGHTS)
# Q[agent][complexity_level] = q_value
_Q_TABLE = {
    "hephaestus": {"L1": 0.6, "L2": 0.7, "L3": 0.8, "L4": 0.5, "L5": 0.4},
    "explore": {"L1": 0.8, "L2": 0.7, "L3": 0.5, "L4": 0.4, "L5": 0.3},
    "librarian": {"L1": 0.7, "L2": 0.6, "L3": 0.5, "L4": 0.5, "L5": 0.4},
    "oracle": {"L1": 0.3, "L2": 0.4, "L3": 0.6, "L4": 0.8, "L5": 0.9},
    "metis": {"L1": 0.2, "L2": 0.3, "L3": 0.5, "L4": 0.7, "L5": 0.9},
    "sisyphus-junior": {"L1": 0.9, "L2": 0.5, "L3": 0.3, "L4": 0.2, "L5": 0.1},
    "momus": {"L1": 0.4, "L2": 0.5, "L3": 0.6, "L4": 0.7, "L5": 0.8},
    "hybrid": {"L1": 0.9, "L2": 0.95, "L3": 0.85, "L4": 0.6, "L5": 0.3},
}

# Decision tracking - actual counter instead of static calculation
_decision_count = 0
_decision_history = []  # Last 1000 decisions

# Session pinning cache - pins agent for session duration
# Format: {session_id: {"agent": str, "task_hash": str}}
_SESSION_PIN_CACHE: Dict[str, Dict[str, str]] = {}


def _select_agent_qlearning(level: int, task: str) -> tuple[str, float]:
    """Select agent using Q-table with epsilon-greedy exploration.

    Returns: (agent_name, q_value)
    """
    global _decision_count

    level_key = f"L{level}"
    agents = list(_Q_TABLE.keys())

    # 10% epsilon-greedy exploration - use random for true exploration
    if random.random() < 0.1:  # 10% random exploration
        agent = random.choice(agents)
        return agent, _Q_TABLE[agent].get(level_key, 0.5)

    # Exploitation: select agent with highest Q-value for this level
    best_agent = max(agents, key=lambda a: _Q_TABLE[a].get(level_key, 0.5))
    best_q = _Q_TABLE[best_agent][level_key]
    return best_agent, best_q


def _update_q_value(agent: str, level: int, success: bool):
    """Update Q-value based on outcome (simple reinforcement)."""
    global _Q_TABLE
    level_key = f"L{level}"
    current = _Q_TABLE[agent].get(level_key, 0.5)
    # Learning rate 0.1: success increases, failure decreases
    delta = 0.1 if success else -0.1
    _Q_TABLE[agent][level_key] = min(1.0, max(0.1, current + delta))


def _route_with_qlearning(
    task_description: str, complexity: ComplexityResult
) -> RoutingResult:
    """Route using Q-learning based on complexity."""

    global _decision_count, _decision_history

    level = complexity.level

    # FIX: Use Q-table based selection instead of hardcoded mapping
    agent, confidence = _select_agent_qlearning(level, task_description)

    # Track decision
    _decision_count += 1
    _decision_history.append(
        {
            "agent": agent,
            "level": level,
            "timestamp": time.time(),
        }
    )
    # Keep last 1000
    _decision_history[:] = _decision_history[-1000:]

    return RoutingResult(
        agent=agent,
        level=level,
        confidence=confidence,
        reason=f"Q-Learning routed to {agent} (complexity: {level}, q={confidence:.2f})",
        strategy="qlearning",
        decisions_made=_decision_count,  # FIX: Actual counter instead of static calc
    )


def route_task(task_description: str, session_id: str = None) -> RoutingResult:
    """Route a task to the optimal agent using Q-Learning.

    Args:
        task_description: The task to route
        session_id: Optional session ID for session pinning

    Returns:
        RoutingResult with agent, level, confidence
    """
    # Check if session has pinned agent
    if session_id:
        pinned = get_pinned_agent(session_id)
        if pinned:
            return RoutingResult(
                agent=pinned,
                level=1,
                confidence=1.0,
                reason=f"Session pinned to {pinned}",
                strategy="session_pin",
                decisions_made=1,
            )

    complexity = score_complexity(task_description)
    return _route_with_qlearning(task_description, complexity)


def pin_routing(session_id: str, agent: str, task_hash: str = None) -> dict:
    """Pin routing for a session for consistent model selection.

    Once pinned, all routing within this session will return the same agent
    until unpinned.

    Args:
        session_id: The session ID to pin
        agent: The agent to pin
        task_hash: Optional task hash for specific pinning

    Returns:
        dict with status and details
    """
    _SESSION_PIN_CACHE[session_id] = {
        "agent": agent,
        "task_hash": task_hash or "",
    }
    return {"status": "pinned", "session_id": session_id, "agent": agent}


def get_pinned_agent(session_id: str) -> Optional[str]:
    """Get the pinned agent for a session.

    Args:
        session_id: The session ID to check

    Returns:
        Pinned agent name or None if not pinned
    """
    entry = _SESSION_PIN_CACHE.get(session_id)
    return entry.get("agent") if entry else None


def unpin_routing(session_id: str) -> dict:
    """Unpin routing for a session.

    Args:
        session_id: The session ID to unpin

    Returns:
        dict with status
    """
    if session_id in _SESSION_PIN_CACHE:
        del _SESSION_PIN_CACHE[session_id]
        return {"status": "unpinned", "session_id": session_id}
    return {"status": "not_pinned", "session_id": session_id}


# ============================================================================
# OUTCOME RECORDING (from learning_engine)
# ============================================================================


def _get_db_path() -> Path:
    """Get path to routing database."""
    db_path = Path.home() / ".opencode" / "routing.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def _init_db():
    """Initialize routing database."""
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS outcomes (
            id INTEGER PRIMARY KEY,
            task_description TEXT,
            agent TEXT,
            level INTEGER,
            success INTEGER,
            latency_ms INTEGER,
            tokens_used INTEGER,
            trace_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def record_outcome(
    task_description: str,
    agent: str,
    level: int,
    success: bool,
    latency_ms: float = 0,
    tokens_used: int = 0,
    signature: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> OutcomeResult:
    """Record delegation outcome for learning with signature verification."""
    task_id = f"outcome_{int(time.time())}"

    if _OUTCOME_SIGNING_KEY:
        if not _verify_outcome_signature(
            task_id, agent, level, success, signature or ""
        ):
            logger.warning(f"OUTCOME_REJECTED: Invalid signature for {agent} L{level}")
            return OutcomeResult(success=False, task_id=task_id)

    if not isinstance(level, int) or not (1 <= level <= 5):
        logger.warning(f"OUTCOME_REJECTED: Invalid level {level}")
        return OutcomeResult(success=False, task_id=task_id)

    if not isinstance(success, bool):
        logger.warning(f"OUTCOME_REJECTED: Invalid success type {type(success)}")
        return OutcomeResult(success=False, task_id=task_id)

    if agent not in ALLOWED_AGENTS:
        logger.warning(f"OUTCOME_REJECTED: Unknown agent {agent}")
        return OutcomeResult(success=False, task_id=task_id)

    _init_db()

    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO outcomes (task_description, agent, level, success, latency_ms, tokens_used, trace_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            task_description,
            agent,
            level,
            int(success),
            latency_ms,
            tokens_used,
            trace_id,
        ),
    )
    conn.commit()
    conn.close()

    _update_q_value(agent, level, success)

    try:
        from packages.learning_engine.bridges.outcome_to_memory_bridge import (
            bridge_outcome_to_memory,
        )

        outcome_dict = {
            "task_description": task_description,
            "agent": agent,
            "level": level,
            "success": success,
            "latency_ms": latency_ms,
            "tokens_used": tokens_used,
        }
        bridge_outcome_to_memory(outcome_dict)
    except Exception as e:
        logger.debug(f"Memory bridge failed: {e}")

    return OutcomeResult(success=True, task_id=task_id)


# ============================================================================
# HYBRID AGENT EXECUTION
# ============================================================================


async def execute_hybrid(
    task_description: str, cloud_model: str = "anthropic/claude-3-haiku"
) -> dict:
    """Execute a task using the hybrid cloud+GGUF agent loop.

    Args:
        task_description: The task to execute
        cloud_model: Model to use for cloud reasoning (default: claude-3-haiku)

    Returns:
        dict with answer, tool_calls, iterations, latency_ms, model_used
    """
    try:
        from packages.orchestration.hybrid_agent_loop import (
            HybridAgentLoop,
            HybridConfig,
        )

        config = HybridConfig.from_env()
        config.cloud_model = cloud_model  # Override default
        hybrid = HybridAgentLoop(config)
        result = await hybrid.run(task_description)
        return result.to_dict()
    except Exception as e:
        logger.error(f"Hybrid execution failed: {e}")
        return {
            "success": False,
            "answer": f"Hybrid execution error: {e}",
            "tool_calls": [],
            "iterations": 0,
            "latency_ms": 0,
            "model_used": "error",
        }


# ============================================================================
# COMPATIBILITY EXPORTS
# ============================================================================

# For backward compatibility
__all__ = [
    "route_task",
    "score_complexity",
    "record_outcome",
    "pin_routing",
    "get_pinned_agent",
    "unpin_routing",
    "execute_hybrid",
    "RoutingResult",
    "ComplexityResult",
    "OutcomeResult",
    "_generate_outcome_signature",
]
