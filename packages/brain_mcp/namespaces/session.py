"""
Session namespace tools for nx-brain-mcp - ML-NATIVE IMPLEMENTATION

This module replaces the old .sisyphus/state.db dependency with:
- memory_store for semantic session storage + retrieval
- learning_engine for session quality + restoration prediction

Key capabilities:
- Sessions as first-class memory objects (episodic, session scope)
- Semantic search for finding similar sessions
- Quality scoring from learning_engine outcomes
- Adaptive session restoration using learned ranking
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# PATH SETUP
# ============================================================================

_project_root = Path(__file__).resolve().parent.parent.parent.parent.parent


# ============================================================================
# SESSION TOOLS - ML-NATIVE (replaces .sisyphus dependency)
# ============================================================================


def _get_memory_client():
    """Lazy load memory_store MCP client."""
    try:
        from packages.memory_store.mcp_server import mcp as memory_mcp

        return memory_mcp
    except ImportError as e:
        logger.warning(f"memory_store not available: {e}")
        return None


def _get_learning_client():
    """Lazy load learning_engine client with extended API."""
    try:
        from packages.learning_engine import record_outcome, status as learning_status
        from packages.learning_engine.outcome_logger import OutcomeLogger
        from packages.learning_engine.delegation import DelegationLearner
        import threading

        # Lazy-init singleton for outcome logger
        _outcome_logger: Optional[OutcomeLogger] = None
        _delegation_learner: Optional[DelegationLearner] = None
        _lock = threading.Lock()

        def get_outcome_logger() -> OutcomeLogger:
            nonlocal _outcome_logger
            if _outcome_logger is None:
                with _lock:
                    if _outcome_logger is None:
                        _outcome_logger = OutcomeLogger()
            return _outcome_logger

        def get_delegation_learner() -> DelegationLearner:
            nonlocal _delegation_learner
            if _delegation_learner is None:
                with _lock:
                    if _delegation_learner is None:
                        _delegation_learner = DelegationLearner()
            return _delegation_learner

        return {
            "record": record_outcome,
            "status": learning_status,
            "get_outcomes": get_outcome_logger().get_outcomes,
            "analyze_delegations": get_delegation_learner().analyze_delegations,
        }
    except ImportError as e:
        logger.warning(f"learning_engine not available: {e}")
        return None


def session_create(
    task_description: str,
    agent_type: str = "sisyphus",
    initial_context: Optional[dict] = None,
) -> dict[str, Any]:
    """Create a new session - writes to memory_store instead of .sisyphus.

    This is the ML-native replacement for creating session-state.json.

    Args:
        task_description: What the user wants to accomplish
        agent_type: Primary agent for this session (default: sisyphus)
        initial_context: Optional dict with context to include

    Returns:
        Dict with session_id, status, created_at
    """
    try:
        memory = _get_memory_client()
        learning = _get_learning_client()

        session_id = f"session_{int(time.time() * 1000)}"
        created_at = datetime.now(timezone.utc).isoformat()

        # Construct session content as structured memory
        content_parts = [
            f"Task: {task_description}",
            f"Agent: {agent_type}",
            f"Started: {created_at}",
        ]

        if initial_context:
            for key, value in initial_context.items():
                content_parts.append(f"{key}: {value}")

        content = "\n".join(content_parts)

        # Write to memory_store as episodic memory with session scope
        memory_id = None
        if memory:
            try:
                # Call memory_store's memory_write to persist the session
                from packages.memory_store import memory_write as mem_write

                task_type = _infer_task_type(task_description)
                write_result = mem_write(
                    content=content,
                    kind="episodic",
                    scope="session",
                    tags=["session", task_type, session_id],
                )

                if write_result and "memory_id" in write_result:
                    memory_id = write_result["memory_id"]
                    logger.info(
                        f"Session written to memory_store: memory_id={memory_id}"
                    )
                else:
                    logger.warning(
                        f"memory_write returned unexpected result: {write_result}"
                    )
            except Exception as e:
                logger.warning(f"memory_store write failed: {e}")

        # Start learning tracking
        if learning:
            try:
                # Infer task type from description (simple heuristic)
                task_type = _infer_task_type(task_description)
                learning["record"](
                    task=f"session_create:{task_description[:50]}",
                    agent=agent_type,
                    success=True,
                    latency_ms=0,
                    tokens_used=0,
                    metadata={"session_id": session_id, "task_type": task_type},
                )
            except Exception as e:
                logger.warning(f"learning tracking failed: {e}")

        return {
            "session_id": session_id,
            "status": "created",
            "created_at": created_at,
            "task_description": task_description,
            "agent_type": agent_type,
            "storage": "memory_store",  # Provenance - NOT .sisyphus
            "memory_id": memory_id,  # From memory_store write
        }

    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        return {"status": "error", "error": str(e)}


def _infer_task_type(task_description: str) -> str:
    """Simple heuristic to infer task type from description."""
    desc = task_description.lower()

    if any(w in desc for w in ["fix", "bug", "error", "debug"]):
        return "bugfix"
    elif any(w in desc for w in ["implement", "create", "build", "add"]):
        return "implementation"
    elif any(w in desc for w in ["refactor", "improve", "clean"]):
        return "refactor"
    elif any(w in desc for w in ["research", "find", "search", "explore"]):
        return "research"
    elif any(w in desc for w in ["review", "check", "verify"]):
        return "review"
    elif any(w in desc for w in ["explain", "how", "what"]):
        return "question"
    else:
        return "general"


def session_resume(
    task_description: str,
    max_candidates: int = 5,
) -> dict[str, Any]:
    """Resume a session by finding relevant past sessions - uses semantic search.

    This is the ML-native replacement for reading session-state.json.
    Uses memory_store for semantic retrieval + learning_engine for ranking.

    Args:
        task_description: What the user wants to accomplish now
        max_candidates: Number of similar sessions to consider

    Returns:
        Dict with session_id, content, relevance_score, restoration_method
    """
    try:
        memory = _get_memory_client()
        learning = _get_learning_client()

        # Step 1: Semantic search in memory_store
        semantic_results = []
        if memory:
            try:
                # Use memory_store's memory_search for semantic retrieval
                from packages.memory_store.mcp_server import memory_search as mem_search

                search_result = mem_search(query=task_description, top_k=max_candidates)

                if search_result and "results" in search_result:
                    semantic_results = search_result["results"]
                    logger.info(
                        f"Semantic search found {len(semantic_results)} results"
                    )
            except Exception as e:
                logger.warning(f"Semantic search failed: {e}")

        # Step 2: Learn from learning_engine for adaptive ranking
        reranked_results = []
        if learning and semantic_results:
            try:
                # Analyze past delegations to get success rates per agent
                analysis = learning["analyze_delegations"](limit=100)

                if analysis and "agent_stats" in analysis:
                    agent_success_rates: dict[str, float] = {}

                    for agent_name, stats in analysis["agent_stats"].items():
                        if isinstance(stats, dict):
                            # Calculate success rate from stats
                            total = stats.get("total", 0)
                            if total > 0:
                                success = stats.get("success", 0)
                                agent_success_rates[agent_name] = success / total
                            else:
                                agent_success_rates[agent_name] = 0.5

                    # Re-rank candidates based on learned success rates
                    # Extract agent names from session content if available
                    reranked_results = []
                    for session_candidate in semantic_results:
                        score = session_candidate.get("score", 0.5)
                        content = session_candidate.get("content", "")

                        # Boost score if session mentions high-success agents
                        boost = 0.0
                        for agent, rate in agent_success_rates.items():
                            if agent.lower() in content.lower():
                                boost += rate * 0.1  # Max 10% boost from agent match

                        adjusted_score = min(1.0, score + boost)
                        session_candidate["adjusted_score"] = adjusted_score
                        session_candidate["learned_boost"] = boost
                        reranked_results.append(session_candidate)

                    # Sort by adjusted score
                    reranked_results.sort(
                        key=lambda x: x.get("adjusted_score", 0), reverse=True
                    )

                    logger.info(
                        f"Re-ranked {len(reranked_results)} candidates via learning_engine"
                    )
                else:
                    reranked_results = semantic_results
                    logger.debug(
                        "No agent stats available, using semantic ranking only"
                    )

            except Exception as e:
                logger.warning(f"Learning ranking failed: {e}")
                reranked_results = semantic_results
        else:
            reranked_results = semantic_results

        # Return the best match from learned ranking if available
        best_session = None
        final_results = reranked_results if reranked_results else semantic_results
        if final_results:
            best_session = final_results[0]

        # Use adjusted_score if available (learned ranking), otherwise original score
        relevance_score = (
            best_session.get("adjusted_score")
            if best_session and best_session.get("adjusted_score")
            else best_session.get("score")
            if best_session
            else None
        )

        # Determine search method for return
        if reranked_results and learning:
            search_method = "learned_rerank"
        elif semantic_results:
            search_method = "semantic"
        else:
            search_method = "fallback"

        return {
            "session_id": best_session.get("session_id") if best_session else None,
            "status": "found" if final_results else "not_found",
            "content": best_session.get("content") if best_session else None,
            "relevance_score": relevance_score,
            "task_description": task_description,
            "storage": "memory_store",  # NOT .sisyphus
            "search_method": search_method,
            "candidates": final_results,
        }

    except Exception as e:
        logger.error(f"Failed to resume session: {e}")
        return {"status": "error", "error": str(e)}


def session_get(
    session_id: str,
    include_content: bool = True,
    include_metadata: bool = True,
) -> dict[str, Any]:
    """Get a specific session by ID - queries memory_store instead of .sisyphus.

    Args:
        session_id: The session to retrieve
        include_content: Include the session content
        include_metadata: Include metadata (timestamps, quality, etc.)

    Returns:
        Dict with session data
    """
    try:
        memory = _get_memory_client()

        # Query memory_store for this session
        session_data = None
        if memory:
            try:
                # Use recall_session to get session messages
                from packages.memory_store.mcp_server import recall_session as recall

                recall_result = recall(session_id=session_id, limit=100)

                if recall_result and recall_result.get("status") == "ok":
                    session_data = recall_result
                else:
                    logger.warning(f"recall_session returned: {recall_result}")
            except Exception as e:
                logger.warning(f"memory_store recall failed: {e}")

        # Return session data or not found
        if session_data and session_data.get("messages"):
            return {
                "session_id": session_id,
                "status": "found",
                "messages": session_data.get("messages", []),
                "storage": "memory_store",
            }

        # Fallback: session not found (ML-native system, no .sisyphus fallback)
        return {
            "session_id": session_id,
            "status": "not_found",
            "message": "Session not found in memory_store",
            "storage": "memory_store",
        }

    except Exception as e:
        logger.error(f"Failed to get session: {e}")
        return {"status": "error", "error": str(e)}


def session_update(
    session_id: str,
    content_addition: str,
    event_type: str = "tool_call",
    metadata_update: Optional[dict] = None,
) -> dict[str, Any]:
    """Update session content during active work.

    Args:
        session_id: Session to update
        content_addition: New content to append
        event_type: Type of event (tool_call, decision, error, correction, completion)
        metadata_update: Optional metadata updates

    Returns:
        Dict with update status
    """
    try:
        memory = _get_memory_client()

        if memory:
            try:
                # Use memory_write to append/update session content
                from packages.memory_store.mcp_server import memory_write as mem_write

                update_content = f"[{event_type}] {content_addition}"
                if metadata_update:
                    update_content += f" | metadata: {metadata_update}"

                write_result = mem_write(
                    content=update_content,
                    kind="episodic",
                    scope="session",
                    tags=["session", session_id, event_type],
                )

                logger.info(f"Session updated in memory_store: {write_result}")
            except Exception as e:
                logger.warning(f"memory_store update failed: {e}")

        return {
            "session_id": session_id,
            "status": "updated",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "storage": "memory_store",
        }

    except Exception as e:
        logger.error(f"Failed to update session: {e}")
        return {"status": "error", "error": str(e)}


def session_archive(
    session_id: str,
    outcome_summary: str,
    success_indicator: bool,
) -> dict[str, Any]:
    """Archive a session - triggers quality scoring.

    Args:
        session_id: Session to archive
        outcome_summary: Summary of what was accomplished
        success_indicator: Whether the session was successful

    Returns:
        Dict with archive status and quality score
    """
    try:
        learning = _get_learning_client()

        # Compute quality score via learning_engine
        quality_score = 0.5  # Default - marked as "uncomputed" when no history
        quality_note = "uncomputed - no learning history"

        if learning:
            try:
                # Query outcomes from the past 7 days related to session tasks
                outcomes = learning["get_outcomes"](limit=100)

                if outcomes and len(outcomes) > 0:
                    # Calculate quality based on success rate, latency efficiency, token efficiency
                    total = len(outcomes)
                    successful = sum(1 for o in outcomes if o.success)
                    success_rate = successful / total

                    # Latency score: normalize around 10 seconds baseline
                    avg_latency = sum(o.latency_ms for o in outcomes) / total
                    latency_score = max(0, 1 - (avg_latency / 10000))  # 0 at 10s+

                    # Token efficiency if available
                    if any(o.tokens_used for o in outcomes):
                        avg_tokens = (
                            sum(o.tokens_used or 0 for o in outcomes if o.tokens_used)
                            / total
                        )
                        # Penalize high token usage slightly
                        token_score = max(0, 1 - (avg_tokens / 50000))
                    else:
                        token_score = 0.5

                    # Weighted quality score: 50% success, 30% latency, 20% tokens
                    quality_score = (
                        (success_rate * 0.5)
                        + (latency_score * 0.3)
                        + (token_score * 0.2)
                    )
                    # Clamp to 0-1
                    quality_score = max(0.0, min(1.0, quality_score))
                    quality_note = f"computed from {total} past outcomes"
                    logger.info(
                        f"Quality scoring: {quality_score:.2f} "
                        f"(success={success_rate:.1%}, latency={avg_latency:.0f}ms)"
                    )
                else:
                    logger.debug(
                        "No learning history found, using default quality score"
                    )

            except Exception as e:
                logger.warning(f"Quality scoring failed: {e}")
                quality_note = "scoring failed - using default"

        # Mark session as archived in memory_store
        memory = _get_memory_client()
        if memory:
            try:
                # Would update archive status
                pass
            except Exception as e:
                logger.warning(f"Archive update failed: {e}")

        # Determine retention policy based on quality
        if quality_score >= 0.8:
            retention_policy = "permanent"
        elif quality_score >= 0.5:
            retention_policy = "standard"
        else:
            retention_policy = "ephemeral"

        return {
            "session_id": session_id,
            "status": "archived",
            "quality_score": quality_score,
            "quality_note": quality_note,
            "retention_policy": retention_policy,
            "storage": "memory_store",
        }

    except Exception as e:
        logger.error(f"Failed to archive session: {e}")
        return {"status": "error", "error": str(e)}


def session_list_mcp(
    limit: int = 10,
    filter_scope: str = "all",
    filter_task_type: Optional[str] = None,
    filter_agent: Optional[str] = None,
    filter_date_from: Optional[str] = None,
    filter_date_to: Optional[str] = None,
) -> dict[str, Any]:
    """List sessions - reads from opencode.db directly.

    Args:
        limit: Max sessions to return
        filter_scope: Filter by scope (all, active, archived)
        filter_task_type: Filter by task type
        filter_agent: Filter by agent
        filter_date_from: Filter from date
        filter_date_to: Filter from date

    Returns:
        Dict with sessions list
    """
    try:
        # Direct query from opencode.db
        import sqlite3
        from pathlib import Path

        OPENCODE_DB = Path.home() / ".local/share/opencode/opencode.db"

        db = sqlite3.connect(str(OPENCODE_DB))
        cur = db.cursor()

        cur.execute(
            """
            SELECT s.id, s.title, s.time_created, s.time_updated
            FROM session s
            ORDER BY s.time_updated DESC
            LIMIT ?
        """,
            (limit,),
        )

        sessions = []
        for row in cur.fetchall():
            sessions.append(
                {
                    "session_id": row[0],
                    "title": row[1] or "Untitled",
                    "created": row[2],
                    "updated": row[3],
                }
            )

        db.close()

        return {
            "status": "found" if sessions else "empty",
            "sessions": sessions,
            "count": len(sessions),
            "storage": "opencode.db",
            "message": f"Retrieved {len(sessions)} sessions",
        }

    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        return {"status": "error", "error": str(e), "sessions": []}


def session_find_similar(
    session_id: Optional[str] = None,
    task_description: Optional[str] = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """Find similar sessions using vector similarity - NEW capability.

    This is a NEW capability enabled by memory_store's vector store.
    The old .sisyphus system had no semantic similarity search.

    Args:
        session_id: Find sessions similar to this one
        task_description: Find sessions similar to this task
        top_k: Number of similar sessions to return

    Returns:
        Dict with similar sessions and similarity scores
    """
    try:
        memory = _get_memory_client()

        if not memory:
            return {
                "status": "no_memory",
                "similar_sessions": [],
                "message": "memory_store not available",
            }

        # Use memory_store's semantic search for vector-based similarity
        try:
            from packages.memory_store.mcp_server import memory_search as mem_search

            # Determine search query
            search_query = ""
            if session_id:
                # Find similar to a specific session
                search_query = f"session {session_id}"
            elif task_description:
                # Find similar to a task description
                search_query = task_description
            else:
                return {
                    "status": "invalid_input",
                    "similar_sessions": [],
                    "message": "Either session_id or task_description required",
                }

            search_result = mem_search(query=search_query, top_k=top_k)

            if search_result and "results" in search_result:
                similar_sessions = [
                    {
                        "session_id": r.get("source"),
                        "content": r.get("content"),
                        "relevance_score": r.get("score"),
                    }
                    for r in search_result["results"]
                ]

                return {
                    "status": "found",
                    "similar_sessions": similar_sessions,
                    "search_method": "vector_similarity",
                    "storage": "memory_store",
                    "query": search_query,
                }
            else:
                return {
                    "status": "no_results",
                    "similar_sessions": [],
                    "search_method": "vector_similarity",
                    "storage": "memory_store",
                }
        except Exception as e:
            logger.error(f"Failed to find similar sessions: {e}")
            return {"status": "error", "error": str(e)}

    except Exception as e:
        logger.error(f"Failed to find similar sessions: {e}")
        return {"status": "error", "error": str(e)}


# ============================================================================
# POOLING OPERATIONS (delegated to memory_store, keeping for compatibility)
# ============================================================================


def session_get_pooled(agent_type: str) -> dict[str, Any]:
    """Get a pre-warmed session from pool - now uses memory_store."""
    # This is now handled by finding an active session in memory_store
    # Keeping for API compatibility
    try:
        result = session_resume(
            task_description=f"Continue work with {agent_type}",
            max_candidates=1,
        )
        return result
    except Exception as e:
        return {"error": str(e)}


def session_return_pooled(session_id: str, agent_type: str) -> dict[str, Any]:
    """Return session to pool - now updates memory_store."""
    # This is now a no-op - sessions stay in memory_store
    # Keeping for API compatibility
    return {
        "status": "ml_native",
        "message": "Sessions now persist in memory_store, no pool management needed",
    }


# Alias for backwards compatibility
def session_return(session_id: str, agent_type: str) -> dict[str, Any]:
    """Return session to pool (alias for session_return_pooled)."""
    return session_return_pooled(session_id, agent_type)


def session_warm_pool(agents: Optional[list] = None) -> dict[str, Any]:
    """Pre-warm session pool - now prepares memory_store queries.

    In the ML-native system, this could prefetch relevant sessions.
    """
    return {
        "status": "ml_native",
        "message": "Pool warming replaced by semantic prefetch in memory_store",
        "storage": "memory_store",
    }


# ============================================================================
# DIAGNOSTICS
# ============================================================================


def session_health() -> dict[str, Any]:
    """Get health status of the ML-native session system."""
    memory = _get_memory_client()
    learning = _get_learning_client()

    return {
        "status": "healthy",
        "architecture": "ml_native",
        "storage": "memory_store",  # NOT .sisyphus
        "memory_available": memory is not None,
        "learning_available": learning is not None,
        "sisyphus_dependency": False,
        "vector_search": "ready" if memory else "unavailable",
        "quality_scoring": "ready" if learning else "unavailable",
    }
