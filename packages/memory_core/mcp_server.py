#!/usr/bin/env python3
"""
Memory Core MCP Server
======================
MCP Tool Server for unified memory system.
Exposes search, stats, session recall, and context finding as MCP tools.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import sys
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

try:
    from packages.learning_engine import record_outcome, status as learning_status
except ImportError:
    pass
try:
    from packages.learning_engine.event_bus import LearningEventBus, LearningEvent
except ImportError:
    pass

_learner = None
try:
    from packages.intelligence.realtime_learner import get_learner as _get_learner
    _learner = _get_learner()
except Exception:
    pass

try:
    from src.tools.middleware.delegation_interceptor import DelegationInterceptor
    _delegation_interceptor = DelegationInterceptor()
    _middleware_list = [_delegation_interceptor]
except Exception as e:
    logging.getLogger(__name__).debug(f"DelegationInterceptor not available: {e}")
    _middleware_list = []

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

_pe: Optional["PriorityEngine"] = None
_event_bus: Optional[LearningEventBus] = None
_router = None


def _get_event_bus() -> LearningEventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = LearningEventBus()
    return _event_bus


def _get_pe() -> "PriorityEngine":
    global _pe
    if _pe is None:
        from .cognitive.priority import PriorityEngine
        db_path = str(Path(__file__).parent.parent.parent / "context" / "memory" / "file_registry.db")
        _pe = PriorityEngine(db_path)
    return _pe


def _get_router():
    global _router
    if _router is None:
        from .router import MemoryRouter
        _router = MemoryRouter()
    return _router


@mcp.tool(tags={"memory", "search"})
def search_memories(query: str, limit: int = 10, strict: bool = False, rerank: bool = False) -> dict:
    router = _get_router()
    from .router import UnifiedMemoryQuery
    uq = UnifiedMemoryQuery(query=query, max_results_per_source=limit, use_semantic=True)
    results = router.search(uq)
    return {
        "results": [{"source": r.source, "content": str(r.content)[:500], "score": getattr(r, "relevance_score", None)} for r in results.results],
        "meta": {"query": query, "limit": limit, "total": results.total_results, "sources_queried": results.sources_queried, "query_time_ms": results.query_time_ms},
    }


@mcp.tool(tags={"memory", "stats"})
def get_memory_stats() -> dict:
    stats = {}
    try:
        db_path = Path(__file__).parent.parent.parent / "context" / "memory" / "file_registry.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {}
            for (table,) in cur.fetchall():
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    tables[table] = cur.fetchone()[0]
                except sqlite3.Error:
                    pass
            stats["file_registry"] = tables
            conn.close()
    except Exception as e:
        stats["file_registry_error"] = str(e)
    try:
        events_db = Path(__file__).parent.parent.parent / "context" / "memory" / "learning_events.db"
        if events_db.exists():
            conn = sqlite3.connect(str(events_db))
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM events")
            stats["learning_events"] = cur.fetchone()[0]
            conn.close()
    except Exception as e:
        stats["learning_events_error"] = str(e)
    if _learner:
        stats["learner"] = {"status": "active"}
    return stats


@mcp.tool(tags={"memory", "session"})
def recall_session(session_id: str = None, limit: int = 50) -> dict:
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / ".sisyphus" / "messages.db"
    if not os.path.exists(db_path):
        logger.warning(f"messages.db not found at {db_path}")
        return {"session_id": session_id or "current", "limit": limit, "messages": [], "status": "db_not_found"}
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if session_id:
            cursor.execute(
                "SELECT id, from_agent, to_agent, type, subject, content, created_at FROM messages WHERE id LIKE ? OR from_agent = ? ORDER BY created_at DESC LIMIT ?",
                (f"{session_id}%", session_id, limit),
            )
        else:
            cursor.execute(
                "SELECT id, from_agent, to_agent, type, subject, content, created_at FROM messages ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        rows = cursor.fetchall()
        conn.close()
        messages = [{"id": r["id"], "from_agent": r["from_agent"], "to_agent": r["to_agent"], "type": r["type"], "subject": r["subject"], "content": r["content"][:500] if r["content"] else None, "created_at": r["created_at"]} for r in rows]
        logger.info(f"recall_session: retrieved {len(messages)} messages")
        return {"session_id": session_id or "current", "limit": limit, "messages": messages, "status": "ok"}
    except Exception as e:
        logger.error(f"recall_session error: {e}")
        return {"session_id": session_id or "current", "limit": limit, "messages": [], "status": "error", "error": str(e)}


@mcp.tool(tags={"memory", "context"})
def find_context(task: str, context_type: str = "all") -> dict:
    router = _get_router()
    from .router import UnifiedMemoryQuery
    uq = UnifiedMemoryQuery(query=task, max_results_per_source=5, use_semantic=True)
    results = router.search(uq)
    return {"task": task, "context_type": context_type, "results": [{"source": r.source, "content": str(r.content)[:300]} for r in results.results[:5]]}


@mcp.tool(tags={"memory", "search"})
def memory_search(query: str, top_k: int = 10) -> dict:
    try:
        router = _get_router()
        from .router import UnifiedMemoryQuery
        uq = UnifiedMemoryQuery(query=query, max_results_per_source=top_k, use_semantic=True)
        results = router.search(uq)
        return {
            "results": [{"source": r.source, "content": str(r.content)[:500], "score": r.relevance_score} for r in results.results],
            "meta": {"query": query, "top_k": top_k, "total": results.total_results, "sources_queried": results.sources_queried, "query_time_ms": results.query_time_ms},
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool(tags={"memory", "write"})
def memory_write(content: str, kind: str = "episodic", scope: str = "global") -> dict:
    try:
        import hashlib
        from .memory_manager import get_memory_manager
        memory_id = hashlib.sha256(content.encode()).hexdigest()[:16]
        mm = get_memory_manager()
        result = mm.on_memory_write(memory_id=memory_id, content=content, kind=kind)
        return {"success": result.success, "memory_id": result.memory_id, "action": result.action, "metadata": result.metadata}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool(tags={"memory", "stats"})
def memory_stats() -> dict:
    try:
        from .memory_manager import get_memory_manager
        mm = get_memory_manager()
        stats = mm.get_stats()
        return {"store": stats.get("store", {}), "forgetting": stats.get("forgetting", {}), "reconsolidation": stats.get("reconsolidation", {}), "trust": stats.get("trust", {}), "priority": stats.get("priority", {})}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool(tags={"mcp", "discovery"})
def get_capabilities() -> dict:
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
            {"name": "find_context", "desc": "Find relevant context for a specific task"},
            {"name": "memory_search", "desc": "Search memory using MemoryRouter"},
            {"name": "memory_write", "desc": "Write memory using MemoryManager"},
            {"name": "memory_stats", "desc": "Get comprehensive memory statistics"},
            {"name": "get_capabilities", "desc": "Dynamic discovery of MCP capabilities"},
        ],
        "sources": sources,
        "health": {"router": "ready" if sources else "degraded", "db": "ok"},
    }


@mcp.tool(tags={"mcp", "health"})
def health_check() -> dict:
    root = Path(__file__).parent.parent.parent
    checks = {}
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
    db = root / "context" / "memory" / "learning_events.db"
    checks["learning_events"] = "ok" if db.exists() else "not_initialized"
    return {"status": "healthy" if all(v != "error" for v in checks.values()) else "degraded", "checks": checks, "mcp": "unified-memory"}


if __name__ == "__main__":
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