"""Session archiver — Archive and restore old sessions."""

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional


class SessionArchiver:
    """Archive and restore session data."""

    DB_PATH = "context/memory/file_registry.db"

    def __init__(self, archive_path: str = "data/session_archive"):
        self.archive_path = Path(archive_path)
        self.archive_path.mkdir(parents=True, exist_ok=True)

    def archive_session(self, session_id: str, session_data: dict) -> bool:
        """Archive a session.

        Args:
            session_id: Unique session identifier
            session_data: Session data to archive

        Returns:
            True if archived successfully
        """
        try:
            archive_file = self.archive_path / f"{session_id}.json"
            archive_file.write_text(json.dumps(session_data, indent=2))

            # Also store in SQLite for querying
            conn = sqlite3.connect(self.DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO session_archive
                (session_id, archived_at, summary, files_changed, tasks_completed)
                VALUES (?, ?, ?, ?, ?)""",
                (
                    session_id,
                    datetime.now(timezone.utc).isoformat(),
                    session_data.get("summary", ""),
                    session_data.get("files_changed", 0),
                    session_data.get("tasks_completed", 0),
                ),
            )
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def restore_session(self, session_id: str) -> Optional[dict]:
        """Restore a session from archive.

        Args:
            session_id: Session ID to restore

        Returns:
            Session data or None if not found
        """
        archive_file = self.archive_path / f"{session_id}.json"
        if archive_file.exists():
            return json.loads(archive_file.read_text())
        return None

    def list_archived(self, limit: int = 10) -> list:
        """List archived sessions.

        Args:
            limit: Maximum number to return

        Returns:
            List of archived session info
        """
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT session_id, archived_at, summary, files_changed, tasks_completed
                FROM session_archive
                ORDER BY archived_at DESC
                LIMIT ?""",
                (limit,),
            )
            rows = cursor.fetchall()
            conn.close()
            return [
                {
                    "session_id": row[0],
                    "archived_at": row[1],
                    "summary": row[2],
                    "files_changed": row[3],
                    "tasks_completed": row[4],
                }
                for row in rows
            ]
        except Exception:
            conn.close()
            return []

    def cleanup_old_archives(self, days: int = 30) -> int:
        """Clean up archives older than specified days.

        Args:
            days: Number of days to keep

        Returns:
            Number of archives removed
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        removed = 0

        # Clean up JSON files
        for archive_file in self.archive_path.glob("*.json"):
            mtime = datetime.fromtimestamp(archive_file.stat().st_mtime, timezone.utc)
            if mtime < cutoff:
                archive_file.unlink()
                removed += 1

        # Clean up SQLite records
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM session_archive WHERE archived_at < ?",
            (cutoff.isoformat(),),
        )
        removed += cursor.rowcount
        conn.commit()
        conn.close()

        return removed


# Initialize archive table
def _init_archive_db():
    """Initialize the session_archive table."""
    conn = sqlite3.connect(SessionArchiver.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS session_archive (
            session_id TEXT PRIMARY KEY,
            archived_at TEXT NOT NULL,
            summary TEXT,
            files_changed INTEGER DEFAULT 0,
            tasks_completed INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


_init_archive_db()