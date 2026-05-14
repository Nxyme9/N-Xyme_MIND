#!/usr/bin/env python3
"""
Memory Store MCP Server
=================
MCP Tool Server for unified memory system.
Exposes search, stats, session recall, and context finding as MCP tools.

Transport: stdio (default), SSE (optional via --sse flag).
"""

from __future__ import annotations

import contextlib
import logging
import os
import sqlite3
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from fastmcp import FastMCP

# Learning module imports
with contextlib.suppress(ImportError):
    from packages.learning_engine import record_outcome, status as learning_status  # noqa: F401
with contextlib.suppress(ImportError):
    from packages.learning_engine.event_bus import LearningEventBus, LearningEvent  # noqa: F401

# Try to get learner from various sources
_learner = None
try:
    from packages.intelligence.realtime_learner import get_learner as _get_learner

    _learner = _get_learner()
except Exception:
    pass

# Delegation interceptor for automated learning (OPTIONAL - server survives if missing)
try:
    from src.tools.middleware.delegation_interceptor import DelegationInterceptor

    _delegation_interceptor = DelegationInterceptor()
    _middleware_list = [_delegation_interceptor]
except Exception as e:
    logging.getLogger(__name__).debug(
        f"DelegationInterceptor not available (optional): {e}"
    )
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

if TYPE_CHECKING:
    from .cognitive.priority import PriorityEngine

_pe: PriorityEngine | None = None
_event_bus: LearningEventBus | None = None


def _get_event_bus() -> LearningEventBus:
    """Get or create LearningEventBus singleton."""
    global _event_bus
    if _event_bus is None:
        _event_bus = LearningEventBus()
    return _event_bus


def _get_pe() -> PriorityEngine:
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
        use_semantic=True,
        rerank=rerank,  # Wire rerank parameter to router
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
                if not table or not isinstance(table, str) or not table.isidentifier():
                    continue
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    tables[table] = cur.fetchone()[0]
                except sqlite3.Error:
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
        if _learner:
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
    import logging
    import sqlite3

    logger = logging.getLogger(__name__)
    # Find project root (parent of packages/) - 3 levels up
    import packages.memory_store.mcp_server as self_module

    project_root = Path(self_module.__file__).parent.parent.parent
    db_path = project_root / ".sisyphus" / "messages.db"

    if not os.path.exists(db_path):
        logger.warning(f"messages.db not found at {db_path}")
        return {
            "session_id": session_id or "current",
            "limit": limit,
            "messages": [],
            "status": "db_not_found",
        }

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if session_id:
            # Query messages for specific session (session_id prefix or from_agent)
            cursor.execute(
                """
                SELECT id, from_agent, to_agent, type, subject, content, created_at
                FROM messages
                WHERE id LIKE ? OR from_agent = ?
                ORDER BY created_at DESC
                LIMIT ?
            """,
                (f"{session_id}%", session_id, limit),
            )
        else:
            # Query recent messages regardless of session
            cursor.execute(
                """
                SELECT id, from_agent, to_agent, type, subject, content, created_at
                FROM messages
                ORDER BY created_at DESC
                LIMIT ?
            """,
                (limit,),
            )

        rows = cursor.fetchall()
        conn.close()

        messages = []
        for row in rows:
            messages.append(
                {
                    "id": row["id"],
                    "from_agent": row["from_agent"],
                    "to_agent": row["to_agent"],
                    "type": row["type"],
                    "subject": row["subject"],
                    "content": row["content"][:500]
                    if row["content"]
                    else None,  # Truncate long content
                    "created_at": row["created_at"],
                }
            )

        logger.info(f"recall_session: retrieved {len(messages)} messages")
        return {
            "session_id": session_id or "current",
            "limit": limit,
            "messages": messages,
            "status": "ok",
        }

    except Exception as e:
        logger.error(f"recall_session error: {e}")
        return {
            "session_id": session_id or "current",
            "limit": limit,
            "messages": [],
            "status": "error",
            "error": str(e),
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
# TOOL: memory_search
# ---------------------------------------------------------------------------


@mcp.tool(tags={"memory", "search"})
def memory_search(query: str, top_k: int = 10) -> dict:
    """Search memory using the MemoryRouter.

    Args:
        query: The search query string.
        top_k: Maximum number of results to return (default 10).

    Returns:
        dict with 'results' (list of matches) and 'meta' (query info).
    """
    try:
        router = _get_router()
        from .router import UnifiedMemoryQuery

        uq = UnifiedMemoryQuery(
            query=query,
            max_results_per_source=top_k,
            use_semantic=True,
        )
        results = router.search(uq)

        return {
            "results": [
                {
                    "source": r.source,
                    "content": str(r.content)[:500],
                    "score": r.relevance_score,
                }
                for r in results.results
            ],
            "meta": {
                "query": query,
                "top_k": top_k,
                "total": results.total_results,
                "sources_queried": results.sources_queried,
                "query_time_ms": results.query_time_ms,
            },
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# TOOL: memory_write
# ---------------------------------------------------------------------------


@mcp.tool(tags={"memory", "write"})
def memory_write(
    content: str,
    kind: str = "episodic",
    scope: str = "global",
    tags: list[str] | None = None,
) -> dict:
    """Write memory using MemoryManager.

    Args:
        content: The memory content to store.
        kind: Type of memory (episodic, semantic, procedural, declarative).
            Default: episodic.
        scope: Scope of memory (global, session, project). Default: global.
        tags: Optional list of tags for the memory.

    Returns:
        dict with success status and memory_id.
    """
    try:
        import hashlib

        from .memory_manager import get_memory_manager

        # Generate memory ID from content hash
        memory_id = hashlib.sha256(content.encode()).hexdigest()[:16]

        mm = get_memory_manager()
        result = mm.on_memory_write(
            memory_id=memory_id,
            content=content,
            kind=kind,
            scope=scope,
            tags=tags,
        )

        return {
            "success": result.success,
            "memory_id": result.memory_id,
            "action": result.action,
            "metadata": result.metadata,
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# TOOL: memory_stats
# ---------------------------------------------------------------------------


@mcp.tool(tags={"memory", "stats"})
def memory_stats() -> dict:
    """Get comprehensive memory statistics.

    Returns:
        dict with store stats, forgetting stats, trust stats, priority stats.
    """
    try:
        from .memory_manager import get_memory_manager

        mm = get_memory_manager()
        stats = mm.get_stats()

        return {
            "store": stats.get("store", {}),
            "forgetting": stats.get("forgetting", {}),
            "reconsolidation": stats.get("reconsolidation", {}),
            "trust": stats.get("trust", {}),
            "priority": stats.get("priority", {}),
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# TOOL: get_capabilities (Dynamic Discovery)
# ---------------------------------------------------------------------------


@mcp.tool(tags={"mcp", "discovery"})
def get_capabilities() -> dict:
    """
    Dynamic MCP capability discovery - shows what this MCP can do.
    Use this to understand available tools without memorizing them.

    Returns:
        dict with available tools, health status, and sources.
    """
    # Lazy import to keep startup fast
    try:
        from .router import MemoryRouter

        router = MemoryRouter()
        sources = router.list_sources() if hasattr(router, "list_sources") else []
    except Exception:
        sources = []

    return {
        "server": "unified-memory",
        "version": "1.0.0",
        "tools": [
            {"name": "search_memories", "desc": "Search across all memory sources"},
            {"name": "get_memory_stats", "desc": "Get statistics about memory sources"},
            {"name": "recall_session", "desc": "Recall session context from memory"},
            {
                "name": "find_context",
                "desc": "Find relevant context for a specific task",
            },
            {"name": "memory_search", "desc": "Search via MemoryRouter (alias)"},
            {"name": "memory_write", "desc": "Write to memory store"},
            {"name": "memory_stats", "desc": "Stats via MemoryManager (alias)"},
            {"name": "health_check", "desc": "Lightweight health check"},
            {"name": "get_capabilities", "desc": "This dynamic discovery tool"},
        ],
        "sources": sources,
        "health": {
            "router": "ready" if sources else "degraded",
            "db": "ok",
        },
    }


# ---------------------------------------------------------------------------
# TOOL: health_check (Lightweight Health)
# ---------------------------------------------------------------------------


@mcp.tool(tags={"mcp", "health"})
def health_check() -> dict:
    """
    Lightweight health check - fast response for monitoring.
    Returns status without loading heavy dependencies.
    """
    # Quick check - don't load full router
    import sqlite3
    from pathlib import Path

    root = Path(__file__).parent.parent.parent
    checks = {}

    # Check file registry
    db = root / "context" / "memory" / "file_registry.db"
    if db.exists():
        try:
            conn = sqlite3.connect(str(db), timeout=1)
            conn.execute("SELECT 1").fetchone()
            conn.close()
            checks["file_registry"] = "ok"
        except sqlite3.Error:
            checks["file_registry"] = "error"
    else:
        checks["file_registry"] = "missing"

    # Check learning events
    db = root / "context" / "memory" / "learning_events.db"
    if db.exists():
        checks["learning_events"] = "ok"
    else:
        checks["learning_events"] = "not_initialized"

    return {
        "status": "healthy"
        if all(v != "error" for v in checks.values())
        else "degraded",
        "checks": checks,
        "mcp": "unified-memory",
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
