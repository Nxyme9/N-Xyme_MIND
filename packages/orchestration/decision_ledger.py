#!/usr/bin/env python3
"""Decision Ledger — SQLite-based decision tracking for N-Xyme MIND.

Records architecture, policy, tooling, workflow, and recovery decisions.
Thread-safe with locking for concurrent access.
"""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional

# Default database path
DEFAULT_DB_PATH = "~/.cache/n-xyme-mind/decisions.db"


class DecisionStatus(Enum):
    """Status of a decision."""

    LOCKED = "LOCKED"
    PROVISIONAL = "PROVISIONAL"
    DEPRECATED = "DEPRECATED"


DECISION_TYPES = {"ARCH", "POLICY", "TOOLING", "WORKFLOW", "RECOVERY"}


@dataclass
class DecisionRecord:
    """Record of a single decision."""

    id: str
    title: str
    context: str
    decision: str
    alternatives: str
    tags: List[str] = field(default_factory=list)
    status: DecisionStatus = DecisionStatus.PROVISIONAL
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_decision_seq(conn: sqlite3.Connection) -> int:
    """Get next sequence number for decision ID."""
    row = conn.execute(
        "SELECT MAX(CAST(SUBSTR(id, 5) AS INTEGER)) FROM decisions WHERE id LIKE 'DEC_%'"
    ).fetchone()
    current_max = row[0] if row and row[0] is not None else 0
    return current_max + 1


def make_decision_id(seq: int) -> str:
    return f"DEC_{seq:05d}"


class DecisionLedger:
    """SQLite-based decision ledger with thread-safe access."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """Initialize DecisionLedger.

        Args:
            db_path: Path to SQLite database.
                     Defaults to ~/.cache/n-xyme-mind/decisions.db
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
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                title TEXT NOT NULL,
                context TEXT NOT NULL,
                decision TEXT NOT NULL,
                alternatives TEXT,
                tags TEXT,
                status TEXT NOT NULL DEFAULT 'PROVISIONAL'
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON decisions(timestamp)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_decisions_status ON decisions(status)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_tags ON decisions(tags)")
        conn.commit()
        conn.close()

    def record_decision(
        self,
        title: str,
        context: str,
        decision: str,
        alternatives: str = "",
        tags: Optional[List[str]] = None,
        status: DecisionStatus = DecisionStatus.PROVISIONAL,
    ) -> DecisionRecord:
        """Record a new decision.

        Args:
            title: Title of the decision
            context: Context/background for the decision
            decision: The decision that was made
            alternatives: Alternative options considered
            tags: List of tags for categorization
            status: Decision status (default: PROVISIONAL)

        Returns:
            DecisionRecord with generated ID and timestamp
        """
        if not title or not context or not decision:
            raise ValueError("title, context, and decision are required")

        tags = tags or []
        tags_str = ",".join(tags) if tags else ""

        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                seq = _next_decision_seq(conn)
                decision_id = make_decision_id(seq)
                timestamp = _now_iso()

                conn.execute(
                    """INSERT INTO decisions 
                       (id, timestamp, title, context, decision, alternatives, tags, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        decision_id,
                        timestamp,
                        title,
                        context,
                        decision,
                        alternatives,
                        tags_str,
                        status.value,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        return DecisionRecord(
            id=decision_id,
            title=title,
            context=context,
            decision=decision,
            alternatives=alternatives,
            tags=tags,
            status=status,
            timestamp=timestamp,
        )

    def get_decisions(
        self,
        tag: Optional[str] = None,
        status: Optional[DecisionStatus] = None,
        limit: int = 100,
    ) -> List[DecisionRecord]:
        """Retrieve decisions with optional filters.

        Args:
            tag: Optional tag filter
            status: Optional status filter
            limit: Maximum number of decisions to return (default 100)

        Returns:
            List of DecisionRecord objects, most recent first
        """
        conn = sqlite3.connect(self.db_path)
        query = "SELECT * FROM decisions WHERE 1=1"
        params: List[Any] = []

        if tag:
            query += " AND tags LIKE ?"
            params.append(f"%{tag}%")
        if status:
            query += " AND status = ?"
            params.append(status.value)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()

        return [
            DecisionRecord(
                id=row[0],
                timestamp=row[1],
                title=row[2],
                context=row[3],
                decision=row[4],
                alternatives=row[5] or "",
                tags=row[6].split(",") if row[6] else [],
                status=DecisionStatus(row[7]),
            )
            for row in rows
        ]

    def get_decision(self, id: str) -> Optional[DecisionRecord]:
        """Retrieve a single decision by ID.

        Args:
            id: Decision ID (e.g., "DEC_00001")

        Returns:
            DecisionRecord or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT * FROM decisions WHERE id = ?", (id,)).fetchone()
        conn.close()

        if row is None:
            return None

        return DecisionRecord(
            id=row[0],
            timestamp=row[1],
            title=row[2],
            context=row[3],
            decision=row[4],
            alternatives=row[5] or "",
            tags=row[6].split(",") if row[6] else [],
            status=DecisionStatus(row[7]),
        )

    def update_status(self, id: str, status: DecisionStatus) -> bool:
        """Update the status of a decision.

        Args:
            id: Decision ID
            status: New status

        Returns:
            True if updated, False if decision not found
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                "UPDATE decisions SET status = ? WHERE id = ?",
                (status.value, id),
            )
            conn.commit()
            updated = cursor.rowcount > 0
            conn.close()

        return updated


# Global singleton
_ledger: Optional[DecisionLedger] = None
_ledger_lock = threading.Lock()


def get_ledger() -> DecisionLedger:
    """Get or create the global DecisionLedger instance."""
    global _ledger
    with _ledger_lock:
        if _ledger is None:
            _ledger = DecisionLedger()
        return _ledger


def record_decision(
    title: str,
    context: str,
    decision: str,
    alternatives: str = "",
    tags: Optional[List[str]] = None,
    status: DecisionStatus = DecisionStatus.PROVISIONAL,
) -> DecisionRecord:
    """Convenience function to record a decision."""
    return get_ledger().record_decision(
        title=title,
        context=context,
        decision=decision,
        alternatives=alternatives,
        tags=tags,
        status=status,
    )


def get_decisions(
    tag: Optional[str] = None,
    status: Optional[DecisionStatus] = None,
    limit: int = 100,
) -> List[DecisionRecord]:
    """Convenience function to get decisions."""
    return get_ledger().get_decisions(tag=tag, status=status, limit=limit)


def get_decision(id: str) -> Optional[DecisionRecord]:
    """Convenience function to get a single decision."""
    return get_ledger().get_decision(id)
