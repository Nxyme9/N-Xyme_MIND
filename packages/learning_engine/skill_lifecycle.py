"""Skill Lifecycle Manager — State machine for skill evolution.

Manages skills through five lifecycle states:
  Proposed → Experimental → Active → Deprecated → Archived

Each transition is tracked with evaluation metrics:
  success_rate, latency, cost, invocation_count, last_evaluated
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SkillState(str, Enum):
    """Lifecycle states for a skill."""

    PROPOSED = "proposed"
    EXPERIMENTAL = "experimental"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


# Valid state transitions — a skill may only move along these edges.
_VALID_TRANSITIONS: dict[SkillState, list[SkillState]] = {
    SkillState.PROPOSED: [SkillState.EXPERIMENTAL, SkillState.ARCHIVED],
    SkillState.EXPERIMENTAL: [
        SkillState.ACTIVE,
        SkillState.DEPRECATED,
        SkillState.ARCHIVED,
    ],
    SkillState.ACTIVE: [SkillState.DEPRECATED, SkillState.EXPERIMENTAL],
    SkillState.DEPRECATED: [SkillState.ARCHIVED, SkillState.ACTIVE],
    SkillState.ARCHIVED: [SkillState.PROPOSED],
}


@dataclass
class SkillMetrics:
    """Evaluation metrics attached to a skill."""

    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    total_cost: float = 0.0
    invocation_count: int = 0
    last_evaluated: float = 0.0

    def update(
        self,
        success: bool,
        latency_ms: float,
        cost: float,
    ) -> None:
        """Update metrics with a single invocation result."""
        self.invocation_count += 1
        n = self.invocation_count
        self.success_rate = (
            (self.success_rate * (n - 1)) + (1.0 if success else 0.0)
        ) / n
        self.avg_latency_ms = ((self.avg_latency_ms * (n - 1)) + latency_ms) / n
        self.total_cost += cost
        self.last_evaluated = time.time()


@dataclass
class Skill:
    """A single skill tracked by the lifecycle manager."""

    name: str
    state: SkillState = SkillState.PROPOSED
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    metrics: SkillMetrics = field(default_factory=SkillMetrics)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    transition_history: list[dict[str, Any]] = field(default_factory=list)


class SkillLifecycleManager:
    """Manages skill lifecycle states with SQLite persistence.

    Usage::

        mgr = SkillLifecycleManager(db_path="skills.db")
        mgr.register("code_review", "Automated code review skill")
        mgr.transition("code_review", SkillState.EXPERIMENTAL)
        mgr.record_outcome("code_review", success=True, latency_ms=120.0, cost=0.01)
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or ":memory:"
        self._local = threading.local()
        self._shared_conn: sqlite3.Connection | None = None  # For :memory: databases
        self._skills: dict[str, Skill] = {}
        self._lock = threading.Lock()
        self._init_db()
        self._load_from_db()
        self._db_path = db_path or ":memory:"
        self._local = threading.local()
        self._skills: dict[str, Skill] = {}
        self._lock = threading.Lock()
        self._init_db()
        self._load_from_db()

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Create tables if they do not exist."""
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS skills (
                    name TEXT PRIMARY KEY,
                    state TEXT NOT NULL DEFAULT 'proposed',
                    description TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    success_rate REAL NOT NULL DEFAULT 0.0,
                    avg_latency_ms REAL NOT NULL DEFAULT 0.0,
                    total_cost REAL NOT NULL DEFAULT 0.0,
                    invocation_count INTEGER NOT NULL DEFAULT 0,
                    last_evaluated REAL NOT NULL DEFAULT 0.0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_name TEXT NOT NULL,
                    from_state TEXT NOT NULL,
                    to_state TEXT NOT NULL,
                    reason TEXT NOT NULL DEFAULT '',
                    timestamp REAL NOT NULL,
                    FOREIGN KEY (skill_name) REFERENCES skills(name)
                );
            """)

    def _connect(self) -> sqlite3.Connection:
        """Get thread-local connection, except for :memory: which uses shared connection."""
        # For in-memory databases, use a shared connection with check_same_thread=False
        if self._db_path == ":memory:":
            if self._shared_conn is None:
                self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._shared_conn.row_factory = sqlite3.Row
            return self._shared_conn
        # For file-based databases, use thread-local connections
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self._db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
        return self._local.conn
        """Get thread-local connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self._db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            if self._db_path != ":memory:":
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
        return self._local.conn

    def _load_from_db(self) -> None:
        """Hydrate in-memory skill objects from the database."""
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute("SELECT * FROM skills").fetchall()
                for row in rows:
                    metrics = SkillMetrics(
                        success_rate=row["success_rate"],
                        avg_latency_ms=row["avg_latency_ms"],
                        total_cost=row["total_cost"],
                        invocation_count=row["invocation_count"],
                        last_evaluated=row["last_evaluated"],
                    )
                    skill = Skill(
                        name=row["name"],
                        state=SkillState(row["state"]),
                        description=row["description"],
                        metadata=json.loads(row["metadata_json"]),
                        metrics=metrics,
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                    self._skills[skill.name] = skill

    def _persist_skill(self, skill: Skill) -> None:
        """Upsert a single skill row."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO skills (
                    name, state, description, metadata_json,
                    success_rate, avg_latency_ms, total_cost,
                    invocation_count, last_evaluated,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    state=excluded.state,
                    description=excluded.description,
                    metadata_json=excluded.metadata_json,
                    success_rate=excluded.success_rate,
                    avg_latency_ms=excluded.avg_latency_ms,
                    total_cost=excluded.total_cost,
                    invocation_count=excluded.invocation_count,
                    last_evaluated=excluded.last_evaluated,
                    updated_at=excluded.updated_at
                """,
                (
                    skill.name,
                    skill.state.value,
                    skill.description,
                    json.dumps(skill.metadata),
                    skill.metrics.success_rate,
                    skill.metrics.avg_latency_ms,
                    skill.metrics.total_cost,
                    skill.metrics.invocation_count,
                    skill.metrics.last_evaluated,
                    skill.created_at,
                    skill.updated_at,
                ),
            )

    def _record_transition(
        self, skill_name: str, from_state: SkillState, to_state: SkillState, reason: str
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO transitions (skill_name, from_state, to_state, reason, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (skill_name, from_state.value, to_state.value, reason, time.time()),
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Skill:
        """Register a new skill in the PROPOSED state."""
        with self._lock:
            if name in self._skills:
                raise ValueError(f"Skill '{name}' already exists")
            skill = Skill(
                name=name,
                description=description,
                metadata=metadata or {},
            )
            self._skills[name] = skill
        self._persist_skill(skill)
        logger.info("Registered skill '%s' in state '%s'", name, skill.state.value)
        return skill

    def transition(
        self,
        name: str,
        target_state: SkillState,
        reason: str = "",
    ) -> Skill:
        """Move a skill to *target_state* if the transition is valid."""
        with self._lock:
            skill = self._get_locked(name)
            allowed = _VALID_TRANSITIONS.get(skill.state, [])
            if target_state not in allowed:
                raise ValueError(
                    f"Cannot transition '{name}' from '{skill.state.value}' "
                    f"to '{target_state.value}'. Allowed: {[s.value for s in allowed]}"
                )
            from_state = skill.state
            skill.state = target_state
            skill.updated_at = time.time()
            skill.transition_history.append(
                {
                    "from": from_state.value,
                    "to": target_state.value,
                    "reason": reason,
                    "timestamp": skill.updated_at,
                }
            )
        self._persist_skill(skill)
        self._record_transition(name, from_state, target_state, reason)
        logger.info("Skill '%s': %s → %s", name, from_state.value, target_state.value)
        return skill

    def record_outcome(
        self,
        name: str,
        success: bool,
        latency_ms: float,
        cost: float = 0.0,
    ) -> SkillMetrics:
        """Record a single invocation outcome and update metrics."""
        with self._lock:
            skill = self._get_locked(name)
            skill.metrics.update(success=success, latency_ms=latency_ms, cost=cost)
            skill.updated_at = time.time()
        self._persist_skill(skill)
        return skill.metrics

    def get(self, name: str) -> Skill | None:
        """Return a skill by name, or None."""
        with self._lock:
            return self._skills.get(name)

    def list_skills(self, state: SkillState | None = None) -> list[Skill]:
        """Return all skills, optionally filtered by state."""
        with self._lock:
            skills = list(self._skills.values())
        if state is None:
            return skills
        return [s for s in skills if s.state == state]

    def evaluate_promotion(self, name: str) -> bool:
        """Evaluate whether a skill should move to the next state."""
        with self._lock:
            skill = self._get_locked(name)
            m = skill.metrics
            if skill.state == SkillState.EXPERIMENTAL:
                if m.success_rate >= 0.80 and m.invocation_count >= 10:
                    self.transition(
                        name,
                        SkillState.ACTIVE,
                        reason=f"Auto-promoted: success_rate={m.success_rate:.2f}, invocations={m.invocation_count}",
                    )
                    return True
            elif (
                str(skill.state) == str(SkillState.ACTIVE)
                or str(skill.state) == "active"
            ):
                if m.success_rate < 0.50 and m.invocation_count >= 20:
                    self.transition(
                        name,
                        SkillState.DEPRECATED,
                        reason=f"Auto-deprecated: success_rate={m.success_rate:.2f}, invocations={m.invocation_count}",
                    )
                    return True
        return False

    def get_transition_history(self, name: str) -> list[dict[str, Any]]:
        """Return the full transition history for a skill."""
        with self._lock:
            skill = self._get_locked(name)
            return list(skill.transition_history)

    def delete(self, name: str) -> None:
        """Remove a skill from the manager and database."""
        with self._lock:
            skill = self._get_locked(name)
            del self._skills[name]
        with self._connect() as conn:
            conn.execute("DELETE FROM skills WHERE name = ?", (name,))
            conn.execute("DELETE FROM transitions WHERE skill_name = ?", (name,))
        logger.info("Deleted skill '%s'", name)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get(self, name: str) -> Skill:
        if name not in self._skills:
            raise KeyError(f"Skill '{name}' not found")
        return self._skills[name]

    def _get_locked(self, name: str) -> Skill:
        if name not in self._skills:
            raise KeyError(f"Skill '{name}' not found")
        return self._skills[name]
