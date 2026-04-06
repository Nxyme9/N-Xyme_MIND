"""SQLite MCP Server - stdio-based SQLite database interaction."""

from mcp.server.fastmcp import FastMCP
import sqlite3
import os
from typing import Optional

mcp = FastMCP("sqlite")

DEFAULT_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".sisyphus",
    "routing.db",
)


def _get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    db = db_path or DEFAULT_DB
    if not os.path.exists(db):
        raise FileNotFoundError(f"Database not found: {db}")
    return sqlite3.connect(db)


@mcp.tool()
def query(sql: str, db_path: Optional[str] = None) -> dict:
    """Execute a SELECT query and return results. READ-ONLY — only SELECT allowed."""
    if not sql.strip().upper().startswith("SELECT"):
        return {"error": "Only SELECT statements are allowed"}
    try:
        conn = _get_connection(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return {"rows": rows, "count": len(rows)}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def list_tables(db_path: Optional[str] = None) -> dict:
    """List all tables in the database."""
    try:
        conn = _get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [r[0] for r in cursor.fetchall()]
        conn.close()
        return {"tables": tables}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def describe_table(table: str, db_path: Optional[str] = None) -> dict:
    """Show schema/columns for a table."""
    try:
        conn = _get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [
            {
                "cid": r[0],
                "name": r[1],
                "type": r[2],
                "notnull": bool(r[3]),
                "default": r[4],
                "pk": bool(r[5]),
            }
            for r in cursor.fetchall()
        ]
        conn.close()
        return {"table": table, "columns": columns}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def sample_table(table: str, limit: int = 10, db_path: Optional[str] = None) -> dict:
    """Get sample rows from a table."""
    try:
        conn = _get_connection(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table} LIMIT ?", (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return {"table": table, "rows": rows, "count": len(rows)}
    except Exception as e:
        return {"error": str(e)}


def main():
    mcp.run()


if __name__ == "__main__":
    main()
