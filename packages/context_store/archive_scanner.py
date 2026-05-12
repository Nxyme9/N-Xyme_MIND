"""
Archive Scanner — Scans and retrieves relevant information from session history archives.

Provides:
- scan_archives(): scan all past sessions for relevant content
- find_related_sessions(query): find sessions related to current task
- extract_context_from_session(session_id): extract key context from a session
- build_context_summary(queries): build a summary of relevant past sessions

Uses existing SQLite databases in .sisyphus/ directory.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Default DB path (reuse existing routing.db in project root)
DEFAULT_DB_PATH = ".sisyphus/routing.db"


def _get_project_root() -> Path:
    """Get project root directory."""
    # This file is in packages/nx-context-mcp/nx_context_mcp/
    return Path(__file__).resolve().parent.parent.parent.parent


def _get_db_path(db_path: Optional[str] = None) -> str:
    """Get absolute path to database."""
    if db_path is None:
        project_root = _get_project_root()
        db_path = str(project_root / DEFAULT_DB_PATH)
    elif not Path(db_path).is_absolute():
        # Relative path - make relative to project root
        project_root = _get_project_root()
        db_path = str(project_root / db_path)
    return db_path


def _get_sisyphus_dir() -> Path:
    """Get .sisyphus directory."""
    return _get_project_root() / ".sisyphus"


@dataclass
class SessionSummary:
    """Summary of a session."""

    session_id: str
    message_count: int
    timestamp: str = ""  # ISO format timestamp
    first_date: Optional[str] = None
    last_date: Optional[str] = None
    agents: List[str] = field(default_factory=list)
    tasks: List[str] = field(default_factory=list)
    success: bool = True


@dataclass
class SessionContext:
    """Extracted context from a session."""

    session_id: str
    timestamp: str
    agents: List[str]
    task_summary: str
    key_operations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class ArchiveScanner:
    """Scans and retrieves information from session history archives."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        sisyphus_dir: Optional[Path] = None,
    ):
        self.db_path = _get_db_path(db_path)
        self.sisyphus_dir = sisyphus_dir or _get_sisyphus_dir()

        # Cache for session data
        self._session_cache: Dict[str, SessionSummary] = {}
        self._jsonl_entries: List[Dict[str, Any]] = []

        logger.info(
            f"ArchiveScanner: Initialized (db={self.db_path}, sisyphus={self.sisyphus_dir})"
        )

    def _get_connection(self) -> sqlite3.Connection:
        """Get SQLite connection with proper settings."""
        db_path = Path(self.db_path)
        if not db_path.parent.exists():
            db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(db_path), timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def scan_archives(
        self,
        limit: int = 100,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Scan all past sessions for relevant content.

        Args:
            limit: Maximum number of sessions to return (default 100)
            date_from: Filter sessions from this date (ISO 8601 format)
            date_to: Filter sessions until this date (ISO 8601 format)

        Returns:
            Dict with session summaries and metadata
        """
        sessions: List[SessionSummary] = []

        # Scan from session-log.jsonl
        session_log = self.sisyphus_dir / "session-log.jsonl"
        max_lines = 10000
        line_count = 0
        file_size_mb = 0
        if session_log.exists():
            file_size_mb = session_log.stat().st_size / (1024 * 1024)
            try:
                with open(session_log, "r", encoding="utf-8") as f:
                    for line in f:
                        if line_count >= max_lines:
                            logger.warning(f"JSONL scan bounded at {max_lines} lines")
                            break
                        if line.strip():
                            entry = json.loads(line)
                            session = SessionSummary(
                                session_id=entry.get("task_id", "unknown"),
                                message_count=1,
                                timestamp=entry.get("timestamp", ""),
                                agents=[entry.get("agent", "unknown")],
                                tasks=[entry.get("description", "")],
                                success=entry.get("success", True),
                            )

                            # Apply date filters
                            if date_from and session.timestamp < date_from:
                                continue
                            if date_to and session.timestamp > date_to:
                                continue

                            sessions.append(session)
                        line_count += 1
            except Exception as e:
                logger.error(f"Failed to read session-log.jsonl: {e}")

        # Also scan routing.db for session data
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                """
                SELECT task_id, COUNT(*), MIN(timestamp), MAX(timestamp)
                FROM outcomes
                GROUP BY task_id
                ORDER BY MAX(timestamp) DESC
                LIMIT ?
            """,
                (limit,),
            )

            for row in cursor.fetchall():
                task_id, count, first_ts, last_ts = row
                # Skip if already in sessions
                if not any(s.session_id == task_id for s in sessions):
                    sessions.append(
                        SessionSummary(
                            session_id=task_id or "unknown",
                            message_count=count or 0,
                            timestamp=str(last_ts) if last_ts else "",
                            first_date=str(first_ts) if first_ts else None,
                            last_date=str(last_ts) if last_ts else None,
                        )
                    )

            conn.close()
        except Exception as e:
            logger.warning(f"Could not query routing.db: {e}")

        # Sort by most recent
        sessions.sort(key=lambda s: s.timestamp or "", reverse=True)

        return {
            "status": "ok",
            "tool": "scan_archives",
            "sessions": [
                {
                    "session_id": s.session_id,
                    "message_count": s.message_count,
                    "timestamp": s.timestamp,
                    "agents": s.agents,
                    "tasks": s.tasks,
                    "success": s.success,
                }
                for s in sessions[:limit]
            ],
            "total_found": len(sessions),
            "filters": {
                "date_from": date_from,
                "date_to": date_to,
                "limit": limit,
            },
            "timestamp": datetime.now().isoformat(),
        }

    def find_related_sessions(
        self,
        query: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Find sessions related to current task.

        Args:
            query: Search query string
            limit: Maximum number of results to return (default 10)

        Returns:
            Dict with matching sessions and relevance scores
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())

        matches: List[Dict[str, Any]] = []

        max_lines = 10000
        line_count = 0
        # Search in session-log.jsonl with bounded scan
        session_log = self.sisyphus_dir / "session-log.jsonl"
        if session_log.exists():
            try:
                with open(session_log, "r", encoding="utf-8") as f:
                    for line in f:
                        if line_count >= max_lines:
                            break
                        if line.strip():
                            entry = json.loads(line)
                            description = entry.get("description", "").lower()
                            task_id = entry.get("task_id", "")

                            # Calculate word overlap score
                            desc_words = set(description.split())
                            overlap = query_words & desc_words
                            score = len(overlap) / max(len(query_words), 1)

                            # Also check for substring match
                            if query_lower in description:
                                score = max(score, 0.5)

                            if score > 0:
                                matches.append(
                                    {
                                        "session_id": task_id,
                                        "description": entry.get("description", ""),
                                        "agent": entry.get("agent", ""),
                                        "timestamp": entry.get("timestamp", ""),
                                        "success": entry.get("success", True),
                                        "score": round(score, 3),
                                        "match_type": "description",
                                    }
                                )
                        line_count += 1
            except Exception as e:
                logger.error(f"Failed to search session-log.jsonl: {e}")

        # Search in outcomes.db
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                """
                SELECT task_id, task_description, agent, success, timestamp
                FROM outcomes
                WHERE task_description LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (f"%{query}%", limit * 2),
            )

            for row in cursor.fetchall():
                session_id, desc, agent, success, ts = row
                # Check if not already in matches
                if not any(m["session_id"] == session_id for m in matches):
                    matches.append(
                        {
                            "session_id": session_id or "",
                            "description": desc or "",
                            "agent": agent or "",
                            "success": bool(success) if success is not None else True,
                            "timestamp": str(ts) if ts else "",
                            "score": 0.6,  # Database match gets moderate score
                            "match_type": "database",
                        }
                    )

            conn.close()
        except Exception as e:
            logger.warning(f"Could not search outcomes.db: {e}")

        # Sort by score and limit
        matches.sort(key=lambda m: m["score"], reverse=True)

        return {
            "status": "ok",
            "tool": "find_related_sessions",
            "query": query,
            "matches": matches[:limit],
            "total_found": len(matches),
            "timestamp": datetime.now().isoformat(),
        }

    def extract_context_from_session(
        self,
        session_id: str,
        include_messages: bool = False,
    ) -> Dict[str, Any]:
        """
        Extract key context from a session.

        Args:
            session_id: Session ID to extract context from
            include_messages: Whether to include full message content

        Returns:
            Dict with session context and key information
        """
        context: Dict[str, Any] = {
            "session_id": session_id,
            "found": False,
            "timestamp": "",
            "agents": [],
            "tasks": [],
            "operations": [],
            "success": True,
        }

        # Extract from session-log.jsonl
        session_log = self.sisyphus_dir / "session-log.jsonl"
        if session_log.exists():
            try:
                with open(session_log, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            entry = json.loads(line)
                            if entry.get("task_id") == session_id:
                                context["found"] = True
                                context["timestamp"] = entry.get("timestamp", "")
                                context["agents"].append(entry.get("agent", ""))
                                if entry.get("description"):
                                    context["tasks"].append(
                                        entry.get("description", "")
                                    )
                                context["success"] = entry.get("success", True)

                                # Extract operations from metadata
                                metadata = entry.get("metadata", {})
                                if isinstance(metadata, dict):
                                    context["operations"].extend(
                                        metadata.get("operations", [])
                                    )
            except Exception as e:
                logger.error(f"Failed to read session-log.jsonl: {e}")

        # Get additional context from outcomes.db
        if context["found"]:
            try:
                conn = self._get_connection()
                cursor = conn.execute(
                    """
                    SELECT task_description, agent, success, level, latency_ms
                    FROM outcomes
                    WHERE task_id = ?
                    ORDER BY timestamp ASC
                """,
                    (session_id,),
                )

                rows = cursor.fetchall()
                if rows:
                    # Add more detailed operations
                    for row in rows:
                        desc, agent, success, level, latency = row
                        if desc and desc not in context["tasks"]:
                            context["tasks"].append(desc)
                        if agent and agent not in context["agents"]:
                            context["agents"].append(agent)

                    context["operation_count"] = len(rows)
                    context["success_rate"] = (
                        sum(1 for r in rows if r[2]) / len(rows) if rows else 0
                    )

                conn.close()
            except Exception as e:
                logger.warning(f"Could not query outcomes.db: {e}")

        context["timestamp"] = datetime.now().isoformat()

        return {
            "status": "ok" if context["found"] else "not_found",
            "tool": "extract_context_from_session",
            "context": context,
            "timestamp": context["timestamp"],
        }

    def build_context_summary(
        self,
        queries: List[str],
        max_sessions_per_query: int = 5,
    ) -> Dict[str, Any]:
        """
        Build a summary of relevant past sessions.

        Args:
            queries: List of search queries
            max_sessions_per_query: Maximum sessions to include per query

        Returns:
            Dict with combined context summary from all queries
        """
        all_sessions: Dict[str, Dict[str, Any]] = {}
        all_tasks: List[str] = []
        all_agents: Set[str] = set()

        for query in queries:
            # Find related sessions for each query
            result = self.find_related_sessions(
                query=query,
                limit=max_sessions_per_query,
            )

            for match in result.get("matches", []):
                session_id = match.get("session_id", "")
                if not session_id:
                    continue

                # Avoid duplicates - prefer higher score
                if session_id in all_sessions:
                    if match.get("score", 0) > all_sessions[session_id].get("score", 0):
                        all_sessions[session_id] = match
                else:
                    all_sessions[session_id] = match

                # Collect tasks and agents
                if match.get("description"):
                    all_tasks.append(match["description"])
                if match.get("agent"):
                    all_agents.add(match["agent"])

        # Get full context for each unique session
        session_contexts: List[Dict[str, Any]] = []
        for session_id in all_sessions.keys():
            ctx_result = self.extract_context_from_session(session_id)
            if ctx_result.get("context", {}).get("found"):
                session_contexts.append(ctx_result["context"])

        # Build summary
        summary = {
            "queries": queries,
            "unique_sessions": len(all_sessions),
            "total_tasks": len(all_tasks),
            "agents": sorted(list(all_agents)),
            "session_contexts": session_contexts[:10],  # Limit to 10 for context size
            "task_overview": list(set(all_tasks))[:20],  # Unique tasks, limit to 20
        }

        return {
            "status": "ok",
            "tool": "build_context_summary",
            "summary": summary,
            "timestamp": datetime.now().isoformat(),
        }


# Convenience function for quick access
_scanner_instance: Optional[ArchiveScanner] = None


def get_scanner(db_path: Optional[str] = None) -> ArchiveScanner:
    """Get singleton ArchiveScanner instance.

    Args:
        db_path: Optional path to SQLite database

    Returns:
        ArchiveScanner instance
    """
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = ArchiveScanner(db_path=db_path)
    return _scanner_instance
