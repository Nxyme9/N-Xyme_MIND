"""Memory tools for core-mcp - delegates to memory_core implementations."""

from core_mcp import mcp

# Import original tool implementations from memory_core
from packages.memory_core.mcp_server import (
    search_memories as _search_memories,
    get_memory_stats as _get_memory_stats,
    recall_session as _recall_session,
    find_context as _find_context,
    memory_search as _memory_search,
    memory_write as _memory_write,
    memory_stats as _memory_stats,
)


# ---------------------------------------------------------------------------
# Tool Wrappers - Register with memory_ prefix
# ---------------------------------------------------------------------------


@mcp.tool(name="memory_search_memories", tags={"memory", "search"})
def memory_search_memories(
    query: str,
    limit: int = 10,
    strict: bool = False,
    rerank: bool = False,
    trust_weight: float = 0.0,
) -> dict:
    """Search across all memory sources (Athena, session, file content, MCP).

    Args:
        query: The search query string.
        limit: Maximum number of results to return (default 10).
        strict: If True, filter out low-confidence results.
        rerank: If True, apply LLM-based reranking to top candidates.
        trust_weight: Weight for trust scoring (0.0 = no trust, 0.3 = 30% trust). Default 0.0.

    Returns:
        dict with 'results' (list of matches) and 'meta' (query info).
    """
    return _search_memories(
        query=query,
        limit=limit,
        strict=strict,
        rerank=rerank,
        trust_weight=trust_weight,
    )


@mcp.tool(name="memory_get_stats", tags={"memory", "stats"})
def memory_get_stats() -> dict:
    """Get statistics about all memory sources and the learning system."""
    return _get_memory_stats()


@mcp.tool(name="memory_recall_session", tags={"memory", "session"})
def memory_recall_session(session_id: str = None, limit: int = 50) -> dict:
    """Recall session context from memory.

    Args:
        session_id: Optional session ID to recall.
        limit: Maximum number of messages to return (default 50).

    Returns:
        dict with session_id, limit, and status.
    """
    return _recall_session(session_id=session_id, limit=limit)


@mcp.tool(name="memory_find_context", tags={"memory", "context"})
def memory_find_context(task: str, context_type: str = "all", trust_weight: float = 0.0) -> dict:
    """Find relevant context for a specific task.

    Args:
        task: The task to find context for.
        context_type: Type of context (all, semantic, episodic). Default: all.
        trust_weight: Weight for trust scoring (0.0 = no trust, 0.3 = 30% trust). Default: 0.0.

    Returns:
        dict with task, context_type, and results.
    """
    return _find_context(task=task, context_type=context_type, trust_weight=trust_weight)


@mcp.tool(name="memory_router_search", tags={"memory", "search"})
def memory_router_search(query: str, top_k: int = 10, trust_weight: float = 0.0) -> dict:
    """Search memory using the MemoryRouter.

    Args:
        query: The search query string.
        top_k: Maximum number of results to return (default 10).
        trust_weight: Weight for trust scoring (0.0 = no trust, 0.3 = 30% trust). Default 0.0.

    Returns:
        dict with 'results' (list of matches) and 'meta' (query info).
    """
    return _memory_search(query=query, top_k=top_k, trust_weight=trust_weight)


@mcp.tool(name="memory_write", tags={"memory", "write"})
def memory_write(content: str, kind: str = "episodic", scope: str = "global") -> dict:
    """Write memory using MemoryManager.

    Args:
        content: The memory content to store.
        kind: Type of memory (episodic, semantic, etc.). Default: episodic.
        scope: Scope of memory (global, session, etc.). Default: global.

    Returns:
        dict with success status and memory_id.
    """
    return _memory_write(content=content, kind=kind, scope=scope)


@mcp.tool(name="memory_comprehensive_stats", tags={"memory", "stats"})
def memory_comprehensive_stats() -> dict:
    """Get comprehensive memory statistics.

    Returns:
        dict with store stats, forgetting stats, trust stats, priority stats.
    """
    return _memory_stats()
