"""Session manager for querying sessions from SQLite database."""

import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Find project root (parent of web_frontend)
_PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_PATH = _PROJECT_ROOT / ".sisyphus" / "state.db"


def session_list(limit: int = 10) -> list[dict[str, Any]]:
    """Get list of sessions from state.db.

    Args:
        limit: Maximum number of sessions to return

    Returns:
        List of session dicts with: session_id, created_at, last_active, message_count
    """
    if not DB_PATH.exists():
        logger.warning("Session database not found at %s", DB_PATH)
        return []

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT session_id, session_started, last_updated
            FROM sessions
            ORDER BY last_updated DESC
            LIMIT ?
            """,
            (limit,),
        )

        rows = cursor.fetchall()
        conn.close()

        sessions: list[dict[str, Any]] = []
        for row in rows:
            sessions.append(
                {
                    "session_id": row["session_id"],
                    "created_at": row["session_started"],
                    "last_active": row["last_updated"],
                    "message_count": 0,
                }
            )

        logger.debug("Retrieved %d sessions from database", len(sessions))
        return sessions

    except sqlite3.Error as e:
        logger.error("Failed to query sessions: %s", e)
        return []
