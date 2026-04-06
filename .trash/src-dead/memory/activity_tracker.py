"""Activity tracker for monitoring file access patterns and active projects.

This module tracks which files are accessed, when, and how often.
It identifies "active projects" based on recent file activity using
exponential decay scoring.
"""

import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Project markers used to identify project directories
PROJECT_MARKERS = [
    ".git",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "composer.json",
    "Gemfile",
    ".vscode",
    ".idea",
    "Makefile",
    "CMakeLists.txt",
]


def _get_db_connection(db_path: str) -> sqlite3.Connection:
    """Get SQLite connection with WAL mode and proper settings."""
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def _detect_project_dir(file_path: str) -> Optional[str]:
    """Detect project directory from file path by searching for markers.

    Args:
        file_path: Full path to the file

    Returns:
        Project directory path if found, None otherwise
    """
    try:
        path = Path(file_path).resolve()

        # Walk up the directory tree looking for project markers
        for parent in path.parents:
            for marker in PROJECT_MARKERS:
                if (parent / marker).exists():
                    return str(parent)

        # Also check the file's immediate parent as fallback
        return str(path.parent)

    except Exception as e:
        logger.debug(f"Failed to detect project for {file_path}: {e}")
        return None


class ActivityTracker:
    """Track file access patterns and identify active projects."""

    def __init__(self, db_path: str):
        """Initialize activity tracker with registry DB path.

        Args:
            db_path: Path to the SQLite database (same as file_registry)
        """
        self.db_path = db_path
        self._init_activity_table()

    def _init_activity_table(self) -> None:
        """Initialize file_activity table if it doesn't exist."""
        try:
            conn = _get_db_connection(self.db_path)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    action TEXT NOT NULL DEFAULT 'read',
                    timestamp TEXT NOT NULL,
                    project_dir TEXT
                )
            """)

            # Indexes for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_activity_timestamp 
                ON file_activity(timestamp)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_activity_project 
                ON file_activity(project_dir)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_activity_file 
                ON file_activity(file_path)
            """)

            conn.commit()
            conn.close()

            logger.debug(f"Initialized file_activity table at {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize activity table: {e}")

    def track_access(self, file_path: str, action: str = "read") -> bool:
        """Record a file access event.

        Args:
            file_path: Full path to the accessed file
            action: Type of action ('read', 'write', 'edit', 'create', 'delete')

        Returns:
            True if successful, False otherwise
        """
        try:
            # Skip if file doesn't exist (optional - remove if you want to track non-existent too)
            if not os.path.exists(file_path) and not file_path.startswith("/tmp"):
                logger.debug(f"Skipping tracking for non-existent file: {file_path}")
                # Still track it - user might be working with it

            project_dir = _detect_project_dir(file_path)
            timestamp = datetime.now(timezone.utc).isoformat()

            conn = _get_db_connection(self.db_path)

            conn.execute(
                """INSERT INTO file_activity 
                   (file_path, action, timestamp, project_dir)
                   VALUES (?, ?, ?, ?)""",
                (file_path, action, timestamp, project_dir),
            )

            conn.commit()
            conn.close()

            logger.debug(f"Tracked access: {file_path} ({action})")
            return True

        except Exception as e:
            logger.error(f"Failed to track access for {file_path}: {e}")
            return False

    def get_active_projects(self, days: int = 7) -> list[dict]:
        """Get projects that were active in the last N days.

        Args:
            days: Number of days to look back (default: 7)

        Returns:
            List of project dictionaries with stats
        """
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            conn = _get_db_connection(self.db_path)

            # Get unique projects with activity in the time window
            cursor = conn.execute(
                """
                SELECT 
                    project_dir,
                    COUNT(*) as access_count,
                    MAX(timestamp) as last_access,
                    COUNT(DISTINCT file_path) as unique_files
                FROM file_activity
                WHERE timestamp > ?
                AND project_dir IS NOT NULL
                GROUP BY project_dir
                ORDER BY access_count DESC
            """,
                (cutoff,),
            )

            projects = []
            for row in cursor.fetchall():
                project_dir, access_count, last_access, unique_files = row

                # Calculate activity score (frequency * recency)
                if last_access:
                    last_time = datetime.fromisoformat(last_access)
                    hours_ago = (
                        datetime.now(timezone.utc) - last_time
                    ).total_seconds() / 3600
                    # Exponential decay: score = count * e^(-hours/24)
                    # More recent = higher score
                    recency_factor = max(0.1, 2.0 ** (-hours_ago / 24))
                    score = access_count * recency_factor
                else:
                    score = 0

                projects.append(
                    {
                        "project_dir": project_dir,
                        "access_count": access_count,
                        "unique_files": unique_files,
                        "last_access": last_access,
                        "score": round(score, 2),
                    }
                )

            conn.close()
            return projects

        except Exception as e:
            logger.error(f"Failed to get active projects: {e}")
            return []

    def get_recent_files(self, limit: int = 50, days: int = 7) -> list[dict]:
        """Get recently accessed files.

        Args:
            limit: Maximum number of files to return (default: 50)
            days: Number of days to look back (default: 7)

        Returns:
            List of file access records
        """
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            conn = _get_db_connection(self.db_path)

            cursor = conn.execute(
                """
                SELECT 
                    file_path,
                    action,
                    timestamp,
                    project_dir
                FROM file_activity
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (cutoff, limit),
            )

            files = [
                {
                    "file_path": row[0],
                    "action": row[1],
                    "timestamp": row[2],
                    "project_dir": row[3],
                }
                for row in cursor.fetchall()
            ]

            conn.close()
            return files

        except Exception as e:
            logger.error(f"Failed to get recent files: {e}")
            return []

    def get_project_activity(self, project_dir: str) -> dict:
        """Get activity statistics for a specific project.

        Args:
            project_dir: Path to the project directory

        Returns:
            Dictionary with project activity stats
        """
        try:
            conn = _get_db_connection(self.db_path)

            # Total accesses
            total_cursor = conn.execute(
                """
                SELECT COUNT(*) FROM file_activity WHERE project_dir = ?
            """,
                (project_dir,),
            )
            total_accesses = total_cursor.fetchone()[0] or 0

            # By action type
            action_cursor = conn.execute(
                """
                SELECT action, COUNT(*) 
                FROM file_activity 
                WHERE project_dir = ?
                GROUP BY action
            """,
                (project_dir,),
            )
            by_action = {row[0]: row[1] for row in action_cursor.fetchall()}

            # Unique files
            unique_cursor = conn.execute(
                """
                SELECT COUNT(DISTINCT file_path) 
                FROM file_activity 
                WHERE project_dir = ?
            """,
                (project_dir,),
            )
            unique_files = unique_cursor.fetchone()[0] or 0

            # Time range
            range_cursor = conn.execute(
                """
                SELECT MIN(timestamp), MAX(timestamp)
                FROM file_activity
                WHERE project_dir = ?
            """,
                (project_dir,),
            )
            time_range = range_cursor.fetchone()

            # Most accessed files
            top_cursor = conn.execute(
                """
                SELECT file_path, COUNT(*) as cnt
                FROM file_activity
                WHERE project_dir = ?
                GROUP BY file_path
                ORDER BY cnt DESC
                LIMIT 10
            """,
                (project_dir,),
            )
            top_files = [
                {"file": row[0], "count": row[1]} for row in top_cursor.fetchall()
            ]

            conn.close()

            return {
                "project_dir": project_dir,
                "total_accesses": total_accesses,
                "unique_files": unique_files,
                "by_action": by_action,
                "first_access": time_range[0],
                "last_access": time_range[1],
                "top_files": top_files,
            }

        except Exception as e:
            logger.error(f"Failed to get project activity for {project_dir}: {e}")
            return {
                "project_dir": project_dir,
                "total_accesses": 0,
                "unique_files": 0,
                "by_action": {},
                "first_access": None,
                "last_access": None,
                "top_files": [],
            }

    def get_file_activity(self, file_path: str) -> dict:
        """Get access history for a specific file.

        Args:
            file_path: Full path to the file

        Returns:
            Dictionary with file activity stats
        """
        try:
            conn = _get_db_connection(self.db_path)

            # Total accesses
            total_cursor = conn.execute(
                """
                SELECT COUNT(*) FROM file_activity WHERE file_path = ?
            """,
                (file_path,),
            )
            total_accesses = total_cursor.fetchone()[0] or 0

            # By action type
            action_cursor = conn.execute(
                """
                SELECT action, COUNT(*) 
                FROM file_activity 
                WHERE file_path = ?
                GROUP BY action
            """,
                (file_path,),
            )
            by_action = {row[0]: row[1] for row in action_cursor.fetchall()}

            # Recent accesses
            recent_cursor = conn.execute(
                """
                SELECT timestamp, action
                FROM file_activity
                WHERE file_path = ?
                ORDER BY timestamp DESC
                LIMIT 10
            """,
                (file_path,),
            )
            recent = [
                {"timestamp": row[0], "action": row[1]}
                for row in recent_cursor.fetchall()
            ]

            # Project info
            project_cursor = conn.execute(
                """
                SELECT DISTINCT project_dir 
                FROM file_activity 
                WHERE file_path = ?
            """,
                (file_path,),
            )
            project_row = project_cursor.fetchone()
            project_dir = project_row[0] if project_row else None

            conn.close()

            return {
                "file_path": file_path,
                "project_dir": project_dir,
                "total_accesses": total_accesses,
                "by_action": by_action,
                "recent_accesses": recent,
            }

        except Exception as e:
            logger.error(f"Failed to get file activity for {file_path}: {e}")
            return {
                "file_path": file_path,
                "project_dir": None,
                "total_accesses": 0,
                "by_action": {},
                "recent_accesses": [],
            }

    def get_stats(self) -> dict:
        """Get overall activity statistics.

        Returns:
            Dictionary with activity statistics
        """
        try:
            conn = _get_db_connection(self.db_path)

            # Total records
            total_cursor = conn.execute("SELECT COUNT(*) FROM file_activity")
            total_records = total_cursor.fetchone()[0] or 0

            # By action
            action_cursor = conn.execute("""
                SELECT action, COUNT(*) FROM file_activity GROUP BY action
            """)
            by_action = {row[0]: row[1] for row in action_cursor.fetchall()}

            # Unique files
            files_cursor = conn.execute("""
                SELECT COUNT(DISTINCT file_path) FROM file_activity
            """)
            unique_files = files_cursor.fetchone()[0] or 0

            # Unique projects
            projects_cursor = conn.execute("""
                SELECT COUNT(DISTINCT project_dir) 
                FROM file_activity 
                WHERE project_dir IS NOT NULL
            """)
            unique_projects = projects_cursor.fetchone()[0] or 0

            # Date range
            range_cursor = conn.execute("""
                SELECT MIN(timestamp), MAX(timestamp) FROM file_activity
            """)
            time_range = range_cursor.fetchone()

            conn.close()

            return {
                "total_records": total_records,
                "unique_files": unique_files,
                "unique_projects": unique_projects,
                "by_action": by_action,
                "first_activity": time_range[0],
                "last_activity": time_range[1],
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "total_records": 0,
                "unique_files": 0,
                "unique_projects": 0,
                "by_action": {},
                "first_activity": None,
                "last_activity": None,
            }
