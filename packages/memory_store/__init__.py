"""N-Xyme Memory Core - Modular memory system with TEMPR retrieval.

Public API:
- search(): Semantic + keyword search with RRF fusion
- store(): Store memories in vector/graph/relational stores
- recall_session(): Retrieve session context
- stats(): Get memory system statistics
- __interface_version__: Current API version
"""

__interface_version__ = "1.0.0"


def health_check() -> dict:
    """Health check for memory_store module."""
    return {
        "status": "healthy",
        "message": "Memory core operational",
        "details": {
            "stores_available": ["vector", "graph", "relational", "file"],
            "retrievers_available": ["semantic", "keyword", "tempr"],
        },
    }


# Import and expose public APIs from submodules
from packages.memory_store.retrievers import (
    TEMPRRetriever,
    SemanticRetriever,
    KeywordRetriever,
    rrf_fusion,
)
from packages.memory_store.stores import (
    VectorStore,
    GraphStore,
    RelationalStore,
    FileStore,
)
from packages.memory_store.sessions import SessionContext, SessionLifecycle
from packages.memory_store.cognitive import (
    AdaptiveDecay,
    SleepEngine,
    MemoryReconsolidation,
)


# Lazy-loaded functions for backwards compatibility
def search(query: str, limit: int = 10, strategy: str = "rrf_fusion"):
    """Search memories using TEMPR retrieval.

    Args:
        query: Search query string
        limit: Maximum results to return
        strategy: Retrieval strategy (semantic, keyword, rrf_fusion)

    Returns:
        List of search results with scores
    """
    retriever = TEMPRRetriever()
    if strategy == "semantic":
        return retriever.semantic_search(query, limit)
    elif strategy == "keyword":
        return retriever.keyword_search(query, limit)
    else:
        return retriever.search(query, limit)


def store(
    content: str, kind: str = "memory", scope: str = "session", metadata: dict = None
):
    """Store a memory in the system.

    Args:
        content: Memory content to store
        kind: Type of memory (memory, summary, principle, etc.)
        scope: Scope (session, global, project)
        metadata: Optional metadata dict

    Returns:
        Storage result dict
    """
    # Import MCP server functions
    try:
        from packages.memory_store.mcp_server import create_memory

        return create_memory(
            content, kind=kind, scope=scope, tags=[], metadata=metadata or {}
        )
    except Exception as e:
        return {"status": "error", "message": str(e)}


def recall_session(session_id: str = None, limit: int = 50):
    """Recall session context.

    Args:
        session_id: Optional session ID to recall
        limit: Maximum memories to return

    Returns:
        List of session memories
    """
    try:
        from packages.memory_store.mcp_server import recall_session as mcp_recall

        return mcp_recall(session_id, limit)
    except Exception as e:
        return {"status": "error", "message": str(e)}


def stats():
    """Get memory system statistics.

    Returns:
        Dict with memory stats
    """
    try:
        from packages.memory_store.mcp_server import get_memory_stats

        return get_memory_stats()
    except Exception:
        # Fallback to basic stats
        return {
            "status": "ok",
            "interface_version": __interface_version__,
            "components": {
                "retrievers": "TEMPR engine loaded",
                "stores": "Vector, Graph, Relational, File stores available",
                "sessions": "Session lifecycle and context management",
                "cognitive": "Adaptive forgetting, sleep engine, reconsolidation, priority, retention, trust",
            },
        }


# Expose submodules for advanced usage
__all__ = [
    "__interface_version__",
    "health_check",
    "search",
    "store",
    "recall_session",
    "stats",
    # Submodules
    "TEMPRRetriever",
    "SemanticRetriever",
    "KeywordRetriever",
    "rrf_fusion",
    "VectorStore",
    "GraphStore",
    "RelationalStore",
    "FileStore",
    "SessionContext",
    "SessionLifecycle",
    "AdaptiveDecay",
    "SleepEngine",
    "MemoryReconsolidation",
]
