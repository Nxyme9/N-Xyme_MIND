"""Context awareness module - understands what user is working on."""

import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class ContextAwareness:
    """Analyzes file activity to understand current user context."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Ensure activity table exists."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    action TEXT NOT NULL DEFAULT 'read',
                    timestamp TEXT NOT NULL,
                    project_dir TEXT
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_activity_path ON file_activity(file_path)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON file_activity(timestamp)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_activity_project ON file_activity(project_dir)"
            )
            conn.commit()
        finally:
            conn.close()

    def _detect_project_dir(self, file_path: str) -> str:
        """Detect project directory from file path."""
        markers = [
            ".git",
            "package.json",
            "pyproject.toml",
            "Cargo.toml",
            "go.mod",
            "setup.py",
            "requirements.txt",
            "Makefile",
            "CMakeLists.txt",
        ]
        p = Path(file_path)
        for parent in p.parents:
            for marker in markers:
                if (parent / marker).exists():
                    return str(parent)
        return str(p.parent)

    def update_context(self, file_path: str, action: str = "read"):
        """Update context based on file access."""
        project_dir = self._detect_project_dir(file_path)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO file_activity (file_path, action, timestamp, project_dir) VALUES (?, ?, ?, ?)",
                (
                    file_path,
                    action,
                    datetime.now(timezone.utc).isoformat(),
                    project_dir,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_current_context(self) -> dict:
        """Get current working context."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            # Recent files (last 24h)
            cursor.execute("""
                SELECT file_path, action, COUNT(*) as count, MAX(timestamp) as last_access
                FROM file_activity
                WHERE timestamp > datetime('now', '-24 hours')
                GROUP BY file_path
                ORDER BY count DESC, last_access DESC
                LIMIT 20
            """)
            recent_files = [
                {"file": r[0], "action": r[1], "count": r[2], "last": r[3]}
                for r in cursor.fetchall()
            ]

            # Active projects
            cursor.execute("""
                SELECT project_dir, COUNT(*) as accesses, COUNT(DISTINCT file_path) as unique_files
                FROM file_activity
                WHERE timestamp > datetime('now', '-24 hours') AND project_dir IS NOT NULL
                GROUP BY project_dir
                ORDER BY accesses DESC
                LIMIT 5
            """)
            active_projects = [
                {"dir": r[0], "accesses": r[1], "files": r[2]}
                for r in cursor.fetchall()
            ]

            # Most common actions
            cursor.execute("""
                SELECT action, COUNT(*) FROM file_activity
                WHERE timestamp > datetime('now', '-24 hours')
                GROUP BY action ORDER BY COUNT(*) DESC
            """)
            actions = {r[0]: r[1] for r in cursor.fetchall()}

            return {
                "recent_files": recent_files,
                "active_projects": active_projects,
                "actions": actions,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        finally:
            conn.close()

    def detect_active_task(self) -> Optional[dict]:
        """Detect what task user is working on based on file patterns."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            # Find most active project in last hour
            cursor.execute("""
                SELECT project_dir, COUNT(*) as accesses, COUNT(DISTINCT file_path) as files
                FROM file_activity
                WHERE timestamp > datetime('now', '-1 hour') AND project_dir IS NOT NULL
                GROUP BY project_dir
                ORDER BY accesses DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if not row:
                return None

            project_dir, accesses, file_count = row

            # Get file types in this project
            cursor.execute(
                """
                SELECT file_path FROM file_activity
                WHERE project_dir = ? AND timestamp > datetime('now', '-1 hour')
                ORDER BY timestamp DESC LIMIT 10
            """,
                (project_dir,),
            )
            files = [r[0] for r in cursor.fetchall()]

            # Detect task type from file patterns
            extensions = [Path(f).suffix for f in files]
            ext_counts: Dict[str, int] = {}
            for ext in extensions:
                ext_counts[ext] = ext_counts.get(ext, 0) + 1

            dominant_ext: str = ""
            if ext_counts:
                dominant_ext = max(ext_counts.keys(), key=lambda k: ext_counts[k])  # type: ignore[arg-type, assignment]
            task_type = "unknown"
            if dominant_ext in (".py", ".js", ".ts", ".rs", ".go"):
                task_type = "coding"
            elif dominant_ext in (".md", ".rst", ".txt"):
                task_type = "writing"
            elif dominant_ext in (".json", ".yaml", ".yml", ".toml"):
                task_type = "configuring"
            elif dominant_ext == ".pdf":
                task_type = "reading"

            return {
                "project": project_dir,
                "task_type": task_type,
                "accesses": accesses,
                "files_touched": file_count,
                "recent_files": files[:5],
                "confidence": min(1.0, accesses / 10.0),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        finally:
            conn.close()

    def predict_next_files(self, limit: int = 10) -> list[dict]:
        """Predict files user might need next based on current context."""
        context = self.get_current_context()
        if not context["active_projects"]:
            return []

        # Get files from active projects that haven't been accessed recently
        active_dirs = [p["dir"] for p in context["active_projects"]]
        predictions = []

        for project_dir in active_dirs[:2]:
            # Find related files in same directory
            for root, dirs, files in os.walk(project_dir):
                # Skip hidden dirs and common exclusions
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d not in ("node_modules", "__pycache__", "venv", ".venv")
                ]
                for f in files:
                    if f.startswith("."):
                        continue
                    ext = os.path.splitext(f)[1]
                    if ext in (
                        ".py",
                        ".js",
                        ".ts",
                        ".md",
                        ".json",
                        ".yaml",
                        ".yml",
                        ".toml",
                        ".txt",
                    ):
                        file_path = os.path.join(root, f)
                        # Score based on recency of directory activity
                        score = 0.5  # base score
                        if any(
                            file_path in rf.get("file", "")
                            for rf in context["recent_files"]
                        ):
                            score += 0.3  # already accessed recently
                        predictions.append(
                            {
                                "file": file_path,
                                "score": score,
                                "reason": "active_project",
                            }
                        )
                        if len(predictions) >= limit:
                            break
                if len(predictions) >= limit:
                    break
            if len(predictions) >= limit:
                break

        return sorted(predictions, key=lambda x: x["score"], reverse=True)[:limit]

    def get_context_summary(self) -> str:
        """Human-readable context summary."""
        context = self.get_current_context()
        task = self.detect_active_task()

        lines = ["=== Current Context ==="]

        if task:
            lines.append(f"Active task: {task['task_type']} in {task['project']}")
            lines.append(f"Confidence: {task['confidence']:.0%}")
            lines.append(f"Files touched: {task['files_touched']}")
            lines.append("")

        if context["active_projects"]:
            lines.append("Active projects:")
            for p in context["active_projects"][:3]:
                lines.append(
                    f"  - {p['dir']} ({p['accesses']} accesses, {p['files']} files)"
                )
            lines.append("")

        if context["recent_files"]:
            lines.append("Recent files:")
            for f in context["recent_files"][:5]:
                lines.append(f"  - {f['file']} ({f['count']}x {f['action']})")

        return "\n".join(lines)
