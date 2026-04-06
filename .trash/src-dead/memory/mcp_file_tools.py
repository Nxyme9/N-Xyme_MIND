#!/usr/bin/env python3
"""
src.memory.mcp_file_tools
=========================
MCP tools for file search functionality.

Tools:
- search_files: Search indexed files using vector similarity
- get_file_context: Get full content for a specific file chunk
- list_indexed_files: List all indexed files from the database

Uses FileConnector from src.memory.file_connector for all operations.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

logger = logging.getLogger("mcp-file-tools")


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _get_file_connector():
    """Import and return FileConnector instance."""
    import sys
    from pathlib import Path as P

    # Add src to path if not already there
    project_root = P(__file__).parent.parent.parent.resolve()
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    from memory.file_connector import FileConnector

    return FileConnector()


def _get_sqlite_path(db_path: str = "context/memory/file_chroma") -> Path:
    """Get SQLite database path for file chunks."""
    project_root = Path(__file__).parent.parent.parent.resolve()
    return project_root / db_path / "file_chunks.db"


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


def register_file_tools(mcp: FastMCP) -> None:
    """
    Register all file-related MCP tools with the FastMCP server.

    Args:
        mcp: FastMCP server instance to register tools with.
    """
    mcp.tool(tags={"read", "file", "search"})(search_files)
    mcp.tool(tags={"read", "file", "context"})(get_file_context)
    mcp.tool(tags={"read", "file", "list"})(list_indexed_files)


def search_files(query: str, limit: int = 10) -> dict:
    """
    Search indexed files using vector similarity.

    Args:
        query: The search query string.
        limit: Maximum number of results to return (default: 10).

    Returns:
        dict with status, results, query, and metadata.
    """
    try:
        connector = _get_file_connector()
        results = connector.search(query, max_results=limit)

        # Format response
        formatted_results = []
        for r in results:
            formatted_results.append(
                {
                    "id": r.id,
                    "content": r.content[:500],  # Truncate long content
                    "score": r.score,
                    "metadata": r.metadata or {},
                }
            )

        return {
            "status": "ok",
            "query": query,
            "results": formatted_results,
            "count": len(formatted_results),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"search_files failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "query": query,
            "timestamp": datetime.now().isoformat(),
        }


def get_file_context(file_path: str, chunk_index: int = 0) -> dict:
    """
    Get full file context for a specific chunk.

    Args:
        file_path: Path to the file.
        chunk_index: Index of the chunk (default: 0).

    Returns:
        dict with content, metadata, or error.
    """
    try:
        connector = _get_file_connector()
        result = connector.get_file_context(file_path, chunk_index)

        if result is None:
            return {
                "status": "not_found",
                "file_path": file_path,
                "chunk_index": chunk_index,
                "message": "File chunk not found",
                "timestamp": datetime.now().isoformat(),
            }

        return {
            "status": "ok",
            "content": result.get("content", ""),
            "metadata": result.get("metadata", {}),
            "file_path": file_path,
            "chunk_index": chunk_index,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"get_file_context failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "file_path": file_path,
            "chunk_index": chunk_index,
            "timestamp": datetime.now().isoformat(),
        }


def list_indexed_files(drive: Optional[str] = None, limit: int = 100) -> dict:
    """
    List all indexed files from the database.

    Args:
        drive: Optional drive filter (e.g., "C:", "D:").
        limit: Maximum number of files to return (default: 100).

    Returns:
        dict with list of indexed files and metadata.
    """
    try:
        sqlite_path = _get_sqlite_path()

        if not sqlite_path.exists():
            return {
                "status": "no_index",
                "message": "No file index found. Index files first.",
                "files": [],
                "timestamp": datetime.now().isoformat(),
            }

        conn = sqlite3.connect(str(sqlite_path))
        cur = conn.cursor()

        # Query distinct files
        query = """
            SELECT file_path, COUNT(*) as chunk_count, MIN(chunk_index) as min_chunk
            FROM file_chunks
        """

        if drive:
            query += f" WHERE file_path LIKE '{drive}%'"

        query += f" GROUP BY file_path ORDER BY file_path LIMIT {limit}"

        cur.execute(query)
        rows = cur.fetchall()
        conn.close()

        files = []
        for row in rows:
            files.append(
                {
                    "file_path": row[0],
                    "chunk_count": row[1],
                    "min_chunk": row[2],
                }
            )

        return {
            "status": "ok",
            "files": files,
            "count": len(files),
            "drive_filter": drive,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"list_indexed_files failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "files": [],
            "timestamp": datetime.now().isoformat(),
        }


# ---------------------------------------------------------------------------
# Package Exports
# ---------------------------------------------------------------------------

__all__ = [
    "register_file_tools",
    "search_files",
    "get_file_context",
    "list_indexed_files",
]
