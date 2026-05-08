"""
SQLite namespace tools for nx-brain-mcp.

This module contains all sqlite-related MCP tools.
Functions are registered manually in __init__.py after MCP is available.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def _get_project_root() -> Path:
    """Get the project root directory."""
    _module_file = Path(__file__).resolve()
    return _module_file.parent.parent.parent


# ============================================================================
# SQLITE TOOLS (sqlite.*) - Personal Brain Data Query
# ============================================================================


def sqlite_query(sql: str, db_path: Optional[str] = None) -> dict[str, any]:
    """Execute a SQL query against the routing database."""
    try:
        from sqlite_mcp import query as sqlite_query_fn

        return sqlite_query_fn(sql, db_path)
    except Exception as e:
        return {"error": str(e)}


def sqlite_list_tables(db_path: Optional[str] = None) -> dict[str, any]:
    """List all tables in the database."""
    try:
        from sqlite_mcp import list_tables as sqlite_list_tables_fn

        return sqlite_list_tables_fn(db_path)
    except Exception as e:
        return {"error": str(e)}


def sqlite_describe_table(table: str, db_path: Optional[str] = None) -> dict[str, any]:
    """Show schema/columns for a table."""
    try:
        from sqlite_mcp import describe_table as sqlite_describe_fn

        # Fix default path - routing.db is in project root .sisyphus/
        _project_root = _get_project_root()
        actual_db = db_path or str(_project_root / ".sisyphus" / "routing.db")
        return sqlite_describe_fn(table, actual_db)
    except Exception as e:
        return {"error": str(e)}
