"""State database wrapper for delegation learning."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class DelegationRecord:
    """A delegation outcome record from the database."""
    id: int
    task_id: str
    agent: str
    level: str
    status: str  # "success" or "failure"
    tokens: int
    timestamp: str

    @property
    def success(self) -> bool:
        return self.status == "success"


class StateDB:
    """Wrapper for the .sisyphus/state.db SQLite database."""

    def __init__(self, db_path: Path | str):
        self._db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        """Lazy connection - connects on first use."""
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def get_delegations(self, limit: int = 1000) -> list[DelegationRecord]:
        """Get delegation records from the database."""
        conn = self._connect()
        cursor = conn.execute(
            "SELECT id, task_id, agent, level, status, tokens, timestamp "
            "FROM delegations ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        return [
            DelegationRecord(
                id=row["id"],
                task_id=row["task_id"],
                agent=row["agent"],
                level=row["level"],
                status=row["status"],
                tokens=row["tokens"],
                timestamp=row["timestamp"],
            )
            for row in cursor.fetchall()
        ]

    def get_all_agent_performance(self) -> dict[str, dict[str, Any]]:
        """Get aggregated performance data per agent."""
        # Placeholder - the learner.py uses this but it's not critical
        conn = self._connect()
        cursor = conn.execute(
            "SELECT agent, status, COUNT(*) as count FROM delegations GROUP BY agent, status"
        )
        result: dict[str, dict[str, Any]] = {}
        for row in cursor.fetchall():
            agent = row["agent"]
            if agent not in result:
                result[agent] = {}
            result[agent][row["status"]] = row["count"]
        return result

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


# Export for convenience
__all__ = ["StateDB", "DelegationRecord"]