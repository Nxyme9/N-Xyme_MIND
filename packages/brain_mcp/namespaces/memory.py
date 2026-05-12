"""
Memory namespace tools for nx-brain-mcp.

This module contains all memory-related MCP tools.
Functions are defined here and registered in brain_mcp/__init__.py
after the real MCP server is available.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _sanitize_search_input(value: str, max_length: int = 500) -> str:
    """Sanitize search input to prevent injection attacks."""
    if not isinstance(value, str):
        return ""
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)
    sanitized = sanitized[:max_length]
    return sanitized.strip()


def memory_search_memories(
    query: str, limit: int = 10, strict: bool = False, rerank: bool = False
) -> dict[str, Any]:
    """Search across all memory sources."""
    query = _sanitize_search_input(query)
    try:
        from packages.memory_store import mcp_server as mem_mcp

        return mem_mcp.search_memories(query, limit, strict, rerank)
    except Exception as e:
        logger.error(f"memory_search_memories failed: {e}")
        return {"error": str(e), "results": []}


def memory_get_memory_stats() -> dict[str, Any]:
    """Get statistics about all memory sources and learning system."""
    try:
        from packages.memory_store import mcp_server as mem_mcp

        return mem_mcp.get_memory_stats()
    except Exception as e:
        logger.error(f"memory_get_memory_stats failed: {e}")
        return {"status": "error", "message": str(e)}


def memory_recall_session(
    session_id: Optional[str] = None, limit: int = 50
) -> dict[str, Any]:
    """Recall session context from memory."""
    try:
        from packages.memory_store import mcp_server as mem_mcp

        return mem_mcp.recall_session(session_id, limit)
    except Exception as e:
        logger.error(f"memory_recall_session failed: {e}")
        return {"status": "error", "message": str(e)}


def memory_find_context(task: str, context_type: str = "all") -> dict[str, Any]:
    """Find relevant context for a specific task."""
    task = _sanitize_search_input(task)
    try:
        from packages.memory_store.mcp_server import find_context

        return find_context(task, context_type)
    except Exception as e:
        logger.error(f"memory_find_context failed: {e}")
        return {"status": "error", "message": str(e)}


def memory_memory_write(
    content: str,
    kind: str = "memory",
    scope: str = "session",
    tags: Optional[list] = None,
) -> dict[str, Any]:
    """Write a memory to the memory store."""
    try:
        from packages.memory_store import mcp_server as mem_mcp

        return mem_mcp.memory_write(content, kind, scope, tags or [])
    except Exception as e:
        logger.error(f"memory_memory_write failed: {e}")
        return {"status": "error", "message": str(e)}


def memory_auto_write(content: str) -> dict[str, Any]:
    """Automatically categorize and write memory (falls back to direct write)."""
    try:
        from packages.memory_store import mcp_server as mem_mcp

        return mem_mcp.memory_write(content, kind="episodic", scope="global")
    except Exception as e:
        logger.error(f"memory_auto_write failed: {e}")
        return {"status": "error", "message": str(e)}


def memory_rank_memories(query: str, limit: int = 10) -> dict[str, Any]:
    """Rank memories by relevance to query."""
    query = _sanitize_search_input(query)
    try:
        from packages.memory_store import mcp_server as mem_mcp

        return mem_mcp.search_memories(query, limit)
    except Exception as e:
        logger.error(f"memory_rank_memories failed: {e}")
        return {"status": "error", "message": str(e)}
