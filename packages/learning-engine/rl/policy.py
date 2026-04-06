"""Policy management for reinforcement learning."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any

from .q_learning import ActionType, QState


@dataclass
class Policy:
    """Represents a learned policy for action selection."""

    name: str
    description: str = ""
    created_at: float = field(default_factory=lambda: __import__("time").time())
    q_table_data: dict[str, Any] = field(default_factory=dict)


class PolicyManager:
    """Manages multiple policies for different contexts."""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path
        self._policies: dict[str, Policy] = {}
        if db_path:
            self._load_policies()

    def _load_policies(self) -> None:
        if not self._db_path:
            return
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS policies (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE,
                    description TEXT,
                    created_at REAL,
                    q_table_json TEXT
                )
            """)
            rows = conn.execute(
                "SELECT name, description, created_at, q_table_json FROM policies"
            ).fetchall()
            for row in rows:
                self._policies[row[0]] = Policy(
                    name=row[0],
                    description=row[1] or "",
                    created_at=row[2],
                    q_table_data=json.loads(row[3]) if row[3] else {},
                )
            conn.close()
        except Exception:
            pass

    def save_policy(self, name: str, description: str, q_table_data: dict) -> None:
        """Save a policy to the database."""
        if not self._db_path:
            return
        self._policies[name] = Policy(
            name=name, description=description, q_table_data=q_table_data
        )
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute(
                """
                INSERT INTO policies (name, description, created_at, q_table_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    description=excluded.description,
                    q_table_json=excluded.q_table_json
            """,
                (
                    name,
                    description,
                    __import__("time").time(),
                    json.dumps(q_table_data),
                ),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def get_policy(self, name: str) -> Policy | None:
        """Get a policy by name."""
        return self._policies.get(name)

    def list_policies(self) -> list[str]:
        """List all policy names."""
        return list(self._policies.keys())


__all__ = [
    "Policy",
    "PolicyManager",
]
