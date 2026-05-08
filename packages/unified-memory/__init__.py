"""
unified_memory - Re-exports from memory_store for convenient imports.

This package provides a unified API to access memory_store functionality
from the packages/ directory.

Usage:
    from unified_memory import search_memories, memory_write, get_memory_stats
    from unified_memory import UnifiedMemoryClient
"""

# Re-export functions from memory_store.mcp_server
from packages.memory_store.mcp_server import (
    search_memories,
    memory_write,
    get_memory_stats,
    find_context,
    recall_session,
    memory_search,
    memory_stats,
)

# Re-export from memory_store for convenience
from packages.memory_store import (
    search as core_search,
    store as core_store,
    recall_session as core_recall_session,
    stats as core_stats,
)


# UnifiedMemoryClient class for programmatic access
class UnifiedMemoryClient:
    """Client wrapper for unified memory operations.

    Provides a convenient interface for memory operations that mirrors
    the MCP server functionality but with a class-based API.
    """

    def __init__(self, default_limit: int = 10):
        """Initialize the client.

        Args:
            default_limit: Default maximum number of results for searches.
        """
        self.default_limit = default_limit

    def search(
        self, query: str, limit: int = None, strict: bool = False, rerank: bool = False
    ):
        """Search memories.

        Args:
            query: The search query.
            limit: Maximum results (uses default if None).
            strict: Filter low-confidence results.
            rerank: Apply LLM reranking.

        Returns:
            Search results dict.
        """
        limit = limit or self.default_limit
        return search_memories(query, limit, strict, rerank)

    def write(
        self,
        content: str,
        kind: str = "episodic",
        scope: str = "global",
        tags: list = None,
    ):
        """Write a memory.

        Args:
            content: The memory content.
            kind: Type of memory (episodic, semantic, procedural, declarative).
            scope: Scope (global, session, project).
            tags: Optional list of tags.

        Returns:
            Write result dict with success status and memory_id.
        """
        return memory_write(content, kind, scope, tags)

    def stats(self):
        """Get memory statistics.

        Returns:
            Memory stats dict.
        """
        return get_memory_stats()

    def find_context(self, task: str, context_type: str = "all"):
        """Find relevant context for a task.

        Args:
            task: The task description.
            context_type: Type of context to find.

        Returns:
            Context results dict.
        """
        return find_context(task, context_type)

    def recall_session(self, session_id: str = None, limit: int = 50):
        """Recall session context.

        Args:
            session_id: Optional session ID.
            limit: Maximum messages to return.

        Returns:
            Session recall dict.
        """
        return recall_session(session_id, limit)


# Convenience functions for direct imports
def create_memory(
    content: str,
    kind: str = "episodic",
    scope: str = "global",
    tags: list = None,
    metadata: dict = None,
):
    """Create a memory - wrapper for memory_write.

    Args:
        content: Memory content.
        kind: Type of memory.
        scope: Scope.
        tags: Optional tags.
        metadata: Optional metadata dict.

    Returns:
        Write result dict.
    """
    # Convert metadata to tags format if provided
    if metadata and not tags:
        tags = list(metadata.keys()) if metadata else None
    return memory_write(content, kind, scope, tags)


# Public API exports
__all__ = [
    # Functions from mcp_server
    "search_memories",
    "memory_write",
    "get_memory_stats",
    "find_context",
    "recall_session",
    "memory_search",
    "memory_stats",
    # Core functions
    "core_search",
    "core_store",
    "core_recall_session",
    "core_stats",
    # Client class
    "UnifiedMemoryClient",
    # Convenience
    "create_memory",
]

__version__ = "1.0.0"
