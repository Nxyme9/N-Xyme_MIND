#!/usr/bin/env python3
"""Strategy Snapshots — SQLite-based project state preservation.

Preserves project strategy state across sessions (SSNAP markdown format).
Thread-safe with threading.Lock for concurrent access.
"""

from __future__ import annotations

import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

# Default database path
DEFAULT_DB_PATH = "~/.cache/n-xyme-mind/strategy.db"


def _now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _make_snapshot_id(name: str) -> str:
    """Generate a unique SSNAP ID for a snapshot.

    Args:
        name: Project name

    Returns:
        SSNAP_{date}_{safe_name}_{uuid_short} format
    """
    ymd = datetime.now(timezone.utc).strftime("%Y%m%d")
    safe = (
        "".join(c if c.isalnum() or c in "_-" else "_" for c in name.strip().lower())[
            :32
        ]
        or "strategy"
    )
    uuid_short = uuid.uuid4().hex[:8]
    return f"SSNAP_{ymd}_{safe}_{uuid_short}"


@dataclass
class SnapshotRecord:
    """Record of a single strategy snapshot."""

    id: str
    project_name: str
    posture: str
    locked_decisions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    sprint_targets: str = ""
    timestamp: str = field(default_factory=_now_iso)


class StrategySnapshot:
    """SQLite-based strategy snapshot manager with thread-safe writes."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """Initialize StrategySnapshot.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.cache/n-xyme-mind/strategy.db
        """
        self.db_path = str(Path(db_path).expanduser())
        self._lock = threading.Lock()
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Ensure database and tables exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        # Enable WAL mode for concurrent reads
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id TEXT PRIMARY KEY,
                project_name TEXT NOT NULL,
                posture TEXT NOT NULL,
                locked_decisions TEXT NOT NULL,
                risks TEXT NOT NULL,
                sprint_targets TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_snapshots_project ON snapshots(project_name)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON snapshots(timestamp DESC)"
        )
        conn.commit()
        conn.close()

    def create_snapshot(
        self,
        project_name: str,
        posture: str,
        locked_decisions: List[str],
        risks: List[str],
        sprint_targets: str,
    ) -> SnapshotRecord:
        """Create a new strategy snapshot.

        Args:
            project_name: Name of the project
            posture: Current project posture/description
            locked_decisions: List of locked decision IDs
            risks: List of current risk descriptions
            sprint_targets: Next sprint target description

        Returns:
            SnapshotRecord with generated ID and timestamp
        """
        snapshot_id = _make_snapshot_id(project_name)
        timestamp = _now_iso()

        # Serialize lists as JSON strings
        locked_json = ",".join(locked_decisions) if locked_decisions else ""
        risks_json = ",".join(risks) if risks else ""

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """INSERT INTO snapshots 
                   (id, project_name, posture, locked_decisions, risks, sprint_targets, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    snapshot_id,
                    project_name,
                    posture,
                    locked_json,
                    risks_json,
                    sprint_targets,
                    timestamp,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        return SnapshotRecord(
            id=snapshot_id,
            project_name=project_name,
            posture=posture,
            locked_decisions=locked_decisions,
            risks=risks,
            sprint_targets=sprint_targets,
            timestamp=timestamp,
        )

    def get_snapshots(
        self, project: Optional[str] = None, limit: int = 100
    ) -> List[SnapshotRecord]:
        """Retrieve snapshots with optional project filter.

        Args:
            project: Optional project name filter
            limit: Maximum number of snapshots to return (default 100)

        Returns:
            List of SnapshotRecord objects, most recent first
        """
        conn = sqlite3.connect(self.db_path)
        query = "SELECT * FROM snapshots WHERE 1=1"
        params: List[Any] = []

        if project:
            query += " AND project_name = ?"
            params.append(project)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()

        return [
            SnapshotRecord(
                id=row[0],
                project_name=row[1],
                posture=row[2],
                locked_decisions=row[3].split(",") if row[3] else [],
                risks=row[4].split(",") if row[4] else [],
                sprint_targets=row[5],
                timestamp=row[6],
            )
            for row in rows
        ]

    def get_latest_snapshot(self, project: str) -> Optional[SnapshotRecord]:
        """Get the most recent snapshot for a project.

        Args:
            project: Project name

        Returns:
            SnapshotRecord or None if no snapshots exist
        """
        snapshots = self.get_snapshots(project=project, limit=1)
        return snapshots[0] if snapshots else None


# Global singleton
_snapshots: Optional[StrategySnapshot] = None
_snapshots_lock = threading.Lock()


def get_snapshot_manager() -> StrategySnapshot:
    """Get or create the global StrategySnapshot instance."""
    global _snapshots
    with _snapshots_lock:
        if _snapshots is None:
            _snapshots = StrategySnapshot()
        return _snapshots


def create_snapshot(
    project_name: str,
    posture: str,
    locked_decisions: List[str],
    risks: List[str],
    sprint_targets: str,
) -> SnapshotRecord:
    """Convenience function to create a snapshot."""
    return get_snapshot_manager().create_snapshot(
        project_name=project_name,
        posture=posture,
        locked_decisions=locked_decisions,
        risks=risks,
        sprint_targets=sprint_targets,
    )


def get_snapshots(
    project: Optional[str] = None, limit: int = 100
) -> List[SnapshotRecord]:
    """Convenience function to get snapshots."""
    return get_snapshot_manager().get_snapshots(project=project, limit=limit)


def get_latest_snapshot(project: str) -> Optional[SnapshotRecord]:
    """Convenience function to get the latest snapshot for a project."""
    return get_snapshot_manager().get_latest_snapshot(project)
