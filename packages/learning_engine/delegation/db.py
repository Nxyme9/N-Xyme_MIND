"""State database wrapper for delegation learning."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class DelegationRecord:
    """A delegation outcome record from the database.
    
    Schema matches DelegationOutcome from outcome_logger.py:
    level is INTEGER (L1-L5), success is bool (computed from success INTEGER).
    """
    id: int
    task_id: str
    agent: str
    level: int  # L1-L5 as integer (was str)
    success: bool  # computed from success INTEGER (was status str)
    tokens: int
    latency_ms: float
    timestamp: str

    @property
    def failure_reason(self) -> str | None:
        return getattr(self, "_failure_reason", None)


class StateDB:
    """Wrapper for .sisyphus/outcomes.db — reads delegation outcomes for learner.
    
    Points to outcomes.db (correct DB with 26 records) instead of state.db (empty).
    Schema matches DelegationOutcome: level=INTEGER, success=INTEGER(0/1).
    """

    def __init__(self, db_path: Path | str | None = None):
        if db_path is None:
            project_root = Path(__file__).resolve().parents[3]
            db_path = project_root / ".sisyphus" / "outcomes.db"
        self._db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        """Lazy connection - connects on first use."""
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def get_delegations(self, limit: int = 1000) -> list[DelegationRecord]:
        """Get delegation records from outcomes.db."""
        conn = self._connect()
        cursor = conn.execute(
            "SELECT id, task_id, agent, level, success, tokens_used, latency_ms, timestamp "
            "FROM outcomes ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        return [
            DelegationRecord(
                id=row["id"],
                task_id=row["task_id"],
                agent=row["agent"],
                level=row["level"],
                success=bool(row["success"]),
                tokens=row["tokens_used"],
                latency_ms=row["latency_ms"],
                timestamp=row["timestamp"],
            )
            for row in cursor.fetchall()
        ]

    def get_all_agent_performance(self) -> dict[str, dict[str, Any]]:
        """Get aggregated performance data per agent."""
        conn = self._connect()
        cursor = conn.execute(
            "SELECT agent, success, COUNT(*) as count FROM outcomes GROUP BY agent, success"
        )
        result: dict[str, dict[str, Any]] = {}
        for row in cursor.fetchall():
            agent = row["agent"]
            if agent not in result:
                result[agent] = {}
            label = "success" if row["success"] == 1 else "failure"
            result[agent][label] = row["count"]
        return result

    def update_feedback(self, task_id: str, agent: str, success: bool, failure_reason: str = "") -> None:
        """Write feedback for a delegation (for future learning)."""
        conn = self._connect()
        conn.execute(
            "UPDATE outcomes SET success = ? WHERE task_id = ? AND agent = ?",
            (1 if success else 0, task_id, agent)
        )
        conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


# Export for convenience
__all__ = ["StateDB", "DelegationRecord"]