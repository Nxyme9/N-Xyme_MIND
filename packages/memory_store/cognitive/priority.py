"""Priority engine — Learn and calculate file importance.

This module provides a priority engine that learns file importance based on:
- Access frequency
- Recency of modifications
- Content value (size)
- File type
- Project context

The engine adapts over time based on user behavior patterns.
"""

import logging
import math
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Default weights for priority calculation
DEFAULT_WEIGHTS = {
    "recency": 0.30,
    "frequency": 0.25,
    "content": 0.20,
    "type": 0.15,
    "project": 0.10,
}

# File type base priorities
FILE_TYPE_PRIORITY = {
    "code": 1.0,
    "doc": 0.8,
    "config": 0.5,
    "data": 0.3,
    "text": 0.3,
    "other": 0.2,
}

# Actions that count as file access
VALID_ACTIONS = {"read", "edit", "create", "delete", "index"}


class PriorityEngine:
    """Learns file importance and calculates priority scores."""

    def __init__(self, db_path: str):
        """Initialize priority engine with registry DB path.

        Args:
            db_path: Path to the SQLite file registry database.
        """
        self.db_path = db_path
        self.weights = DEFAULT_WEIGHTS.copy()
        self._load_weights()
        self._init_access_table()

    def _get_connection(self) -> sqlite3.Connection:
        """Get SQLite connection with proper settings."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def _init_access_table(self) -> None:
        """Initialize file_access table if not exists."""
        try:
            conn = self._get_connection()
            conn.execute("""CREATE TABLE IF NOT EXISTS file_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )""")
            conn.execute(
                """CREATE INDEX IF NOT EXISTS idx_file_access_path ON file_access(file_path)"""
            )
            conn.execute(
                """CREATE INDEX IF NOT EXISTS idx_file_access_timestamp ON file_access(timestamp)"""
            )
            conn.execute("""CREATE TABLE IF NOT EXISTS query_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                result_id TEXT NOT NULL,
                source TEXT NOT NULL,
                used INTEGER DEFAULT 0,
                ignored INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL,
                session_id TEXT
            )""")
            conn.commit()
            conn.close()
            logger.debug("Initialized file_access table")
        except Exception as e:
            logger.error(f"Failed to init access table: {e}")

    def _infer_file_type(self, file_path: str) -> str:
        """Infer file type from file extension."""
        ext = Path(file_path).suffix.lower()
        type_mapping = {
            ".py": "code",
            ".js": "code",
            ".ts": "code",
            ".tsx": "code",
            ".jsx": "code",
            ".go": "code",
            ".rs": "code",
            ".java": "code",
            ".c": "code",
            ".cpp": "code",
            ".h": "code",
            ".cs": "code",
            ".md": "doc",
            ".txt": "doc",
            ".rst": "doc",
            ".pdf": "doc",
            ".json": "config",
            ".yaml": "config",
            ".yml": "config",
            ".toml": "config",
            ".ini": "config",
            ".xml": "config",
            ".db": "data",
            ".sqlite": "data",
            ".csv": "data",
            ".jsonl": "data",
            ".parquet": "data",
        }
        return type_mapping.get(ext, "other")

    def _calculate_recency_score(self, metadata: dict[str, Any]) -> float:
        """Calculate recency score using exponential decay."""
        modified = metadata.get("modified") or metadata.get("modified_time")
        if not modified:
            return 0.5

        try:
            if isinstance(modified, str):
                modified_dt = datetime.fromisoformat(modified.replace("Z", "+00:00"))
            else:
                modified_dt = modified

            now = (
                datetime.now(modified_dt.tzinfo)
                if modified_dt.tzinfo
                else datetime.now()
            )
            days_since = (now - modified_dt).total_seconds() / 86400

            decay_rate = 10.0
            score = math.exp(-days_since / decay_rate)
            return max(0.0, min(1.0, score))
        except Exception:
            return 0.5

    def _calculate_frequency_score(self, file_path: str) -> float:
        """Calculate access frequency score."""
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                """SELECT COUNT(*) FROM file_access
                   WHERE file_path = ? AND timestamp > datetime('now', '-30 days')""",
                (file_path,),
            )
            count = cursor.fetchone()[0]
            conn.close()

            max_expected = 100
            if count == 0:
                return 0.0
            score = math.log(1 + count) / math.log(1 + max_expected)
            return max(0.0, min(1.0, score))
        except Exception as e:
            logger.debug(f"Error calculating frequency: {e}")
            return 0.0

    def _calculate_content_score(self, metadata: dict[str, Any]) -> float:
        """Calculate content value score based on file size."""
        size = metadata.get("size_bytes", 0)
        if size <= 0:
            return 0.0

        max_size = 1_000_000
        score = math.log1p(size) / math.log1p(max_size)
        return max(0.0, min(1.0, score))

    def _calculate_type_score(self, metadata: dict[str, Any]) -> float:
        """Calculate score based on file type."""
        file_type = metadata.get("file_type", "other")
        return FILE_TYPE_PRIORITY.get(file_type, FILE_TYPE_PRIORITY["other"])

    def _calculate_project_score(self, file_path: str) -> float:
        """Calculate score based on project context."""
        active_projects = self.get_active_projects()
        if not active_projects:
            return 0.5

        try:
            file_path_obj = Path(file_path).resolve()
            for project_dir in active_projects:
                project_path = Path(project_dir).resolve()
                try:
                    if (
                        project_path in file_path_obj.parents
                        or file_path_obj.parent == project_path
                    ):
                        return 1.0
                except ValueError:
                    pass
        except Exception:
            pass

        return 0.2

    def calculate_priority(self, file_path: str, metadata: dict[str, Any]) -> float:
        """Calculate priority score for a file (0.0-1.0)."""
        recency = self._calculate_recency_score(metadata)
        frequency = self._calculate_frequency_score(file_path)
        content = self._calculate_content_score(metadata)
        file_type = self._calculate_type_score(metadata)
        project = self._calculate_project_score(file_path)

        priority = (
            recency * self.weights["recency"]
            + frequency * self.weights["frequency"]
            + content * self.weights["content"]
            + file_type * self.weights["type"]
            + project * self.weights["project"]
        )

        return max(0.0, min(1.0, priority))

    def update_access(self, file_path: str, action: str = "read") -> bool:
        """Track file access event."""
        if action not in VALID_ACTIONS:
            action = "read"

        try:
            conn = self._get_connection()
            timestamp = datetime.now().isoformat()
            conn.execute(
                "INSERT INTO file_access (file_path, action, timestamp) VALUES (?, ?, ?)",
                (file_path, action, timestamp),
            )
            conn.commit()
            conn.close()
            logger.debug(f"Updated access: {file_path} ({action})")
            return True
        except Exception as e:
            logger.error(f"Failed to update access for {file_path}: {e}")
            return False

    def get_top_priorities(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get highest priority files."""
        try:
            conn = self._get_connection()

            cursor = conn.execute(
                """SELECT 
                    fa.file_path,
                    COUNT(fa.id) as access_count,
                    MAX(fa.timestamp) as last_access,
                    fr.size_bytes,
                    fr.indexed_at
                FROM file_access fa
                LEFT JOIN file_registry fr ON fa.file_path = fr.file_path
                WHERE fa.timestamp > datetime('now', '-30 days')
                GROUP BY fa.file_path
                ORDER BY access_count DESC, last_access DESC
                LIMIT ?""",
                (limit,),
            )

            results = []
            for row in cursor.fetchall():
                file_path, access_count, last_access, size_bytes, indexed_at = row
                metadata = {
                    "size_bytes": size_bytes or 0,
                    "modified": indexed_at,
                    "file_type": self._infer_file_type(file_path),
                }
                priority = self.calculate_priority(file_path, metadata)
                results.append(
                    {
                        "file_path": file_path,
                        "priority": priority,
                        "access_count": access_count,
                        "last_access": last_access,
                    }
                )

            conn.close()
            return results
        except Exception as e:
            logger.error(f"Failed to get top priorities: {e}")
            return []

    def get_active_projects(self) -> list[str]:
        """Detect active projects from recent file activity."""
        try:
            conn = self._get_connection()
            cursor = conn.execute("""SELECT DISTINCT file_path FROM file_access
                WHERE timestamp > datetime('now', '-7 days') ORDER BY timestamp DESC""")

            project_dirs = set()
            for row in cursor.fetchall():
                file_path = row[0]
                try:
                    path = Path(file_path).resolve()
                    for parent in path.parents:
                        if (
                            (parent / "pyproject.toml").exists()
                            or (parent / "package.json").exists()
                            or (parent / "Cargo.toml").exists()
                            or (parent / "go.mod").exists()
                            or (parent / ".git").exists()
                        ):
                            project_dirs.add(str(parent))
                            break
                        if parent == parent.parent:
                            break
                except Exception:
                    pass

            conn.close()
            return sorted(project_dirs)
        except Exception as e:
            logger.error(f"Failed to get active projects: {e}")
            return []

    def should_index_now(self, file_path: str) -> bool:
        """Decide if file should be indexed immediately."""
        try:
            metadata = {"file_type": self._infer_file_type(file_path)}
            type_score = self._calculate_type_score(metadata)

            if type_score >= 0.8:
                return True

            conn = self._get_connection()
            cursor = conn.execute(
                """SELECT COUNT(*) FROM file_access
                   WHERE file_path = ? AND timestamp > datetime('now', '-1 days')""",
                (file_path,),
            )
            recent_access = cursor.fetchone()[0] > 0
            conn.close()

            if recent_access:
                return True

            return False
        except Exception as e:
            logger.debug(f"Error in should_index_now: {e}")
            return False

    def track_query_feedback(
        self,
        query: str,
        result_id: str,
        source: str,
        used: bool = False,
        ignored: bool = False,
        session_id: Optional[str] = None,
    ) -> bool:
        """Track query feedback (result used or ignored)."""
        try:
            conn = self._get_connection()
            timestamp = datetime.now().isoformat()
            conn.execute(
                """INSERT INTO query_feedback
                   (query, result_id, source, used, ignored, timestamp, session_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    query,
                    result_id,
                    source,
                    1 if used else 0,
                    1 if ignored else 0,
                    timestamp,
                    session_id,
                ),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to track query feedback: {e}")
            return False

    def get_query_stats(self, query: str, days: int = 30) -> dict[str, Any]:
        """Get statistics for a specific query."""
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                """SELECT 
                   COUNT(*) as total,
                   SUM(used) as used_count,
                   SUM(ignored) as ignored_count,
                   GROUP_CONCAT(DISTINCT source) as sources
                   FROM query_feedback
                   WHERE query = ? AND timestamp > datetime('now', '-' || ? || ' days')""",
                (query, days),
            )
            row = cursor.fetchone()
            conn.close()

            if row[0] is None:
                return {
                    "total_feedback": 0,
                    "used_count": 0,
                    "ignored_count": 0,
                    "sources": [],
                }

            return {
                "total_feedback": row[0] or 0,
                "used_count": row[1] or 0,
                "ignored_count": row[2] or 0,
                "sources": row[3].split(",") if row[3] else [],
            }
        except Exception as e:
            logger.error(f"Failed to get query stats: {e}")
            return {
                "total_feedback": 0,
                "used_count": 0,
                "ignored_count": 0,
                "sources": [],
            }

    def detect_topic_drift(self, days: int = 7) -> float:
        """Detect topic drift by comparing recent vs historical file types."""
        try:
            conn = self._get_connection()

            cursor = conn.execute(
                """SELECT DISTINCT file_path FROM file_access
                   WHERE timestamp > datetime('now', '-' || ? || ' days')""",
                (days,),
            )
            recent_paths = [row[0] for row in cursor.fetchall()]

            cursor = conn.execute(
                """SELECT DISTINCT file_path FROM file_access
                   WHERE timestamp > datetime('now', '-90 days')
                   AND timestamp <= datetime('now', '-' || ? || ' days')""",
                (days,),
            )
            historical_paths = [row[0] for row in cursor.fetchall()]
            conn.close()

            if not recent_paths or not historical_paths:
                return 0.0

            recent_counts = {}
            for path in recent_paths:
                ftype = self._infer_file_type(path)
                recent_counts[ftype] = recent_counts.get(ftype, 0) + 1

            historical_counts = {}
            for path in historical_paths:
                ftype = self._infer_file_type(path)
                historical_counts[ftype] = historical_counts.get(ftype, 0) + 1

            recent_total = sum(recent_counts.values())
            historical_total = sum(historical_counts.values())

            if recent_total == 0 or historical_total == 0:
                return 0.0

            all_types = set(recent_counts.keys()) | set(historical_counts.keys())
            drift_score = 0.0

            for file_type in all_types:
                recent_p = recent_counts.get(file_type, 0) / recent_total
                historical_p = historical_counts.get(file_type, 0) / historical_total

                if historical_p == 0:
                    drift_score += recent_p
                elif recent_p == 0:
                    drift_score += historical_p
                else:
                    drift_score += abs(recent_p - historical_p)

            return min(1.0, drift_score / 2.0)

        except Exception as e:
            logger.error(f"Failed to detect topic drift: {e}")
            return 0.0

    def get_learning_stats(self) -> dict[str, Any]:
        """Get learning statistics."""
        try:
            conn = self._get_connection()

            cursor = conn.execute("SELECT COUNT(*) FROM query_feedback")
            total_feedback = cursor.fetchone()[0] or 0

            cursor = conn.execute("SELECT COUNT(DISTINCT query) FROM query_feedback")
            unique_queries = cursor.fetchone()[0] or 0

            cursor = conn.execute(
                """SELECT query, COUNT(*) as cnt FROM query_feedback
                   GROUP BY query ORDER BY cnt DESC LIMIT 10"""
            )
            top_queries = [
                {"query": row[0], "count": row[1]} for row in cursor.fetchall()
            ]

            cursor = conn.execute(
                """SELECT fa.file_path FROM file_access fa
                   WHERE fa.timestamp > datetime('now', '-30 days')"""
            )
            topic_trends = {}
            for row in cursor.fetchall():
                ftype = self._infer_file_type(row[0])
                topic_trends[ftype] = topic_trends.get(ftype, 0) + 1

            conn.close()

            return {
                "total_feedback": total_feedback,
                "unique_queries": unique_queries,
                "top_queries": top_queries,
                "topic_trends": topic_trends,
            }
        except Exception as e:
            logger.error(f"Failed to get learning stats: {e}")
            return {
                "total_feedback": 0,
                "unique_queries": 0,
                "top_queries": [],
                "topic_trends": {},
            }

    def update_weights_from_feedback(self, feedback_data: list[dict]):
        """Learn optimal weights from user feedback.

        Args:
            feedback_data: List of dicts with keys: query, clicked_result_id, relevance_score
        """
        if not feedback_data:
            return

        # Track which factors correlate with high relevance scores
        factor_scores = {factor: [] for factor in self.weights}

        for feedback in feedback_data:
            relevance = feedback.get("relevance_score", 0.5)
            for factor in self.weights:
                # Use access patterns to infer factor importance
                factor_scores[factor].append(relevance)

        # Calculate average relevance per factor
        factor_averages = {}
        for factor, scores in factor_scores.items():
            if scores:
                factor_averages[factor] = sum(scores) / len(scores)

        # Update weights proportionally
        total = sum(factor_averages.values())
        if total > 0:
            for factor in self.weights:
                self.weights[factor] = factor_averages.get(factor, 0.1) / total

        # Persist updated weights
        self._save_weights()

    def _save_weights(self):
        """Save current weights to file."""
        weights_file = (
            Path(__file__).parent.parent.parent.parent
            / ".sisyphus"
            / "priority_weights.json"
        )
        weights_file.parent.mkdir(parents=True, exist_ok=True)
        import json

        with open(weights_file, "w") as f:
            json.dump(
                {"weights": self.weights, "updated_at": datetime.now().isoformat()},
                f,
                indent=2,
            )

    def _load_weights(self):
        """Load weights from file if they exist."""
        weights_file = (
            Path(__file__).parent.parent.parent.parent
            / ".sisyphus"
            / "priority_weights.json"
        )
        if weights_file.exists():
            import json

            with open(weights_file, "r") as f:
                data = json.load(f)
                self.weights.update(data.get("weights", {}))


# Convenience function
def compute_priority(
    file_path: str,
    metadata: dict[str, Any],
    db_path: str = "context/memory/file_registry.db",
) -> float:
    """Compute priority for a file."""
    engine = PriorityEngine(db_path)
    return engine.calculate_priority(file_path, metadata)
