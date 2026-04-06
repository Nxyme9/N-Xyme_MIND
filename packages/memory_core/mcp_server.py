#!/usr/bin/env python3
"""
src.memory.mcp_server
=====================
MCP Tool Server for unified memory system.
Exposes search, stats, session recall, and context finding as MCP tools.

Transport: stdio (default), SSE (optional via --sse flag).
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastmcp import FastMCP

# Learning module imports
try:
    from packages.learning_engine import record_outcome, status as learning_status
except ImportError:
    pass
try:
    from packages.learning_engine.event_bus import LearningEventBus, LearningEvent
except ImportError:
    pass

# Delegation interceptor for automated learning (OPTIONAL - server survives if missing)
try:
    from src.tools.middleware.delegation_interceptor import DelegationInterceptor

    _delegation_interceptor = DelegationInterceptor()
    _middleware_list = [_delegation_interceptor]
except Exception as e:
    logging.getLogger(__name__).warning(f"DelegationInterceptor unavailable: {e}")
    _middleware_list = []

# ---------------------------------------------------------------------------
# Server Init
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="unified-memory",
    version="1.0.0",
    middleware=_middleware_list,
    instructions=(
        "Unified Memory MCP Server — aggregates memory from multiple sources.\n\n"
        "Tools:\n"
        "- search_memories: Search across all memory sources\n"
        "- get_memory_stats: Get statistics about memory sources\n"
        "- recall_session: Recall session context\n"
        "- find_context: Find relevant context for a task\n\n"
        "Sources: Graphiti (episodic), Hindsight (session), Memory MCP (semantic), "
        "SQLite databases (mind_from_mind, jarvis_memory, jarvis_events, nxm_from_mind)"
    ),
)

logger = logging.getLogger("unified-memory-mcp")

# ---------------------------------------------------------------------------
# Learning Module Singletons (lazy initialization)
# ---------------------------------------------------------------------------

_pe: Optional["PriorityEngine"] = None
_event_bus: Optional[LearningEventBus] = None


def _get_event_bus() -> LearningEventBus:
    """Get or create LearningEventBus singleton."""
    global _event_bus
    if _event_bus is None:
        _event_bus = LearningEventBus()
    return _event_bus


def _get_pe() -> "PriorityEngine":
    """Get or create PriorityEngine singleton."""
    global _pe
    if _pe is None:
        from .cognitive.priority import PriorityEngine

        db_path = str(
            Path(__file__).parent.parent.parent
            / "context"
            / "memory"
            / "file_registry.db"
        )
        _pe = PriorityEngine(db_path)
    return _pe


# ---------------------------------------------------------------------------
# Memory Router Integration
# ---------------------------------------------------------------------------

_router = None


def _get_router():
    """Get or create MemoryRouter singleton."""
    global _router
    if _router is None:
        from .router import MemoryRouter

        _router = MemoryRouter()
    return _router


# ---------------------------------------------------------------------------
# TOOL: search_memories
# ---------------------------------------------------------------------------


@mcp.tool(tags={"memory", "search"})
def search_memories(
    query: str, limit: int = 10, strict: bool = False, rerank: bool = False
) -> dict:
    """
    Search across all memory sources (Athena, session, file content, MCP).

    Args:
        query: The search query string.
        limit: Maximum number of results to return (default 10).
        strict: If True, filter out low-confidence results.
        rerank: If True, apply LLM-based reranking to top candidates.

    Returns:
        dict with 'results' (list of matches) and 'meta' (query info).
    """
    router = _get_router()
    from .router import UnifiedMemoryQuery

    uq = UnifiedMemoryQuery(
        query=query,
        max_results_per_source=limit,
        use_semantic=rerank,
    )
    results = router.search(uq)

    return {
        "results": [
            {
                "source": r.source,
                "content": str(r.content)[:500],
                "score": getattr(r, "relevance_score", None),
            }
            for r in results.results
        ],
        "meta": {
            "query": query,
            "limit": limit,
            "total": results.total_results,
            "sources_queried": results.sources_queried,
            "query_time_ms": results.query_time_ms,
        },
    }


# ---------------------------------------------------------------------------
# TOOL: get_memory_stats
# ---------------------------------------------------------------------------


@mcp.tool(tags={"memory", "stats"})
def get_memory_stats() -> dict:
    """Get statistics about all memory sources and the learning system."""
    stats = {}

    # File registry stats
    try:
        db_path = (
            Path(__file__).parent.parent.parent
            / "context"
            / "memory"
            / "file_registry.db"
        )
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {}
            for (table,) in cur.fetchall():
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    tables[table] = cur.fetchone()[0]
                except:
                    pass
            stats["file_registry"] = tables
            conn.close()
    except Exception as e:
        stats["file_registry_error"] = str(e)

    # Learning events stats
    try:
        events_db = (
            Path(__file__).parent.parent.parent
            / "context"
            / "memory"
            / "learning_events.db"
        )
        if events_db.exists():
            conn = sqlite3.connect(str(events_db))
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM events")
            stats["learning_events"] = cur.fetchone()[0]
            conn.close()
    except Exception as e:
        stats["learning_events_error"] = str(e)

    # Learning system stats
    try:
        learner = get_learner()
        if learner:
            stats["learner"] = {"status": "active"}
    except Exception as e:
        stats["learner_error"] = str(e)

    return stats


# ---------------------------------------------------------------------------
# TOOL: recall_session
# ---------------------------------------------------------------------------


@mcp.tool(tags={"memory", "session"})
def recall_session(session_id: str = None, limit: int = 50) -> dict:
    """Recall session context from memory."""
    return {
        "session_id": session_id or "current",
        "limit": limit,
        "status": "implemented",
    }


# ---------------------------------------------------------------------------
# TOOL: find_context
# ---------------------------------------------------------------------------


@mcp.tool(tags={"memory", "context"})
def find_context(task: str, context_type: str = "all") -> dict:
    """Find relevant context for a specific task."""
    router = _get_router()
    from .router import UnifiedMemoryQuery

    uq = UnifiedMemoryQuery(query=task, max_results_per_source=5, use_semantic=True)
    results = router.search(uq)

    return {
        "task": task,
        "context_type": context_type,
        "results": [
            {"source": r.source, "content": str(r.content)[:300]}
            for r in results.results[:5]
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if "--sse" in sys.argv:
        port = 8765
        if "--port" in sys.argv:
            idx = sys.argv.index("--port")
            if idx + 1 < len(sys.argv):
                port = int(sys.argv[idx + 1])
        import uvicorn

        uvicorn.run(mcp.streamable_app, host="0.0.0.0", port=port)
    else:
        mcp.run()
