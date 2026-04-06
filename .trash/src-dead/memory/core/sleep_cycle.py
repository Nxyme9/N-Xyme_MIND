"""Sleep Cycle — JOURNAL → CONSOLIDATE → RECALL (smysle/agent-memory).

Implements a cyclic memory processing system inspired by biological
sleep phases. Each cycle processes memories through three phases:

    JOURNAL: Write recent session events to episodic storage
    CONSOLIDATE: Transfer important memories to long-term storage
    RECALL: Retrieve and strengthen relevant memories

The cycle runs periodically, with each phase performing distinct
operations on the memory hierarchy.
"""

from __future__ import annotations

import sqlite3
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional


class SleepPhase(Enum):
    """Sleep cycle phases."""

    IDLE = "idle"
    JOURNAL = "journal"
    CONSOLIDATE = "consolidate"
    RECALL = "recall"


@dataclass
class SleepEvent:
    """An event recorded during a sleep cycle.

    Attributes:
        event_id: Unique identifier.
        phase: Phase during which event occurred.
        content: Event description/data.
        timestamp: Unix timestamp.
        metadata: Optional key-value data.
    """

    event_id: str
    phase: SleepPhase
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CycleResult:
    """Result of a complete sleep cycle.

    Attributes:
        cycle_id: Unique cycle identifier.
        started_at: Cycle start timestamp.
        completed_at: Cycle end timestamp.
        phases_completed: List of phases that ran.
        events: Events generated during cycle.
        stats: Phase-specific statistics.
    """

    cycle_id: str
    started_at: float
    completed_at: float
    phases_completed: list[SleepPhase]
    events: list[SleepEvent]
    stats: dict[str, Any] = field(default_factory=dict)


class SleepCycle:
    """Cyclic memory processing system.

    Manages the JOURNAL → CONSOLIDATE → RECALL cycle for memory
    maintenance. Each phase can have custom handlers registered.

    Args:
        db_path: Path to SQLite database. Uses in-memory if None.
        journal_handler: Callback for journal phase (optional).
        consolidate_handler: Callback for consolidate phase (optional).
        recall_handler: Callback for recall phase (optional).
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        journal_handler: Optional[Callable[[dict[str, Any]], list[SleepEvent]]] = None,
        consolidate_handler: Optional[Callable[[dict[str, Any]], list[SleepEvent]]] = None,
        recall_handler: Optional[Callable[[dict[str, Any]], list[SleepEvent]]] = None,
    ) -> None:
        self._db_path = db_path or ":memory:"
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.RLock()
        self._current_phase = SleepPhase.IDLE
        self._cycle_count = 0

        self._journal_handler = journal_handler
        self._consolidate_handler = consolidate_handler
        self._recall_handler = recall_handler

        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            db_path = self._db_path
            if db_path != ":memory:":
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sleep_events (
                event_id TEXT PRIMARY KEY,
                phase TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp REAL NOT NULL,
                cycle_id TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sleep_cycles (
                cycle_id TEXT PRIMARY KEY,
                started_at REAL NOT NULL,
                completed_at REAL,
                phases_completed TEXT NOT NULL DEFAULT '[]',
                stats TEXT NOT NULL DEFAULT '{}'
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_cycle ON sleep_events(cycle_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_phase ON sleep_events(phase)"
        )
        conn.commit()

    def run_cycle(self, cycle_id: Optional[str] = None,
                  context: Optional[dict[str, Any]] = None) -> CycleResult:
        """Execute a full JOURNAL → CONSOLIDATE → RECALL cycle.

        Args:
            cycle_id: Unique cycle ID (auto-generated if None).
            context: Context dict passed to phase handlers.

        Returns:
            CycleResult with all events and stats.
        """
        import uuid
        cid = cycle_id or f"cycle-{uuid.uuid4().hex[:8]}"
        ctx = context or {}
        started_at = time.time()
        phases_completed: list[SleepPhase] = []
        all_events: list[SleepEvent] = []
        stats: dict[str, Any] = {}

        with self._lock:
            self._current_phase = SleepPhase.JOURNAL
            journal_events = self._run_phase(
                SleepPhase.JOURNAL, cid, ctx, self._journal_handler
            )
            all_events.extend(journal_events)
            phases_completed.append(SleepPhase.JOURNAL)
            stats["journal_count"] = len(journal_events)

            self._current_phase = SleepPhase.CONSOLIDATE
            consolidate_events = self._run_phase(
                SleepPhase.CONSOLIDATE, cid, ctx, self._consolidate_handler
            )
            all_events.extend(consolidate_events)
            phases_completed.append(SleepPhase.CONSOLIDATE)
            stats["consolidate_count"] = len(consolidate_events)

            self._current_phase = SleepPhase.RECALL
            recall_events = self._run_phase(
                SleepPhase.RECALL, cid, ctx, self._recall_handler
            )
            all_events.extend(recall_events)
            phases_completed.append(SleepPhase.RECALL)
            stats["recall_count"] = len(recall_events)

            self._current_phase = SleepPhase.IDLE
            self._cycle_count += 1

        completed_at = time.time()
        result = CycleResult(
            cycle_id=cid,
            started_at=started_at,
            completed_at=completed_at,
            phases_completed=phases_completed,
            events=all_events,
            stats=stats,
        )
        self._persist_cycle(result)
        return result

    def _run_phase(
        self,
        phase: SleepPhase,
        cycle_id: str,
        context: dict[str, Any],
        handler: Optional[Callable[[dict[str, Any]], list[SleepEvent]]],
    ) -> list[SleepEvent]:
        """Run a single sleep phase.

        Args:
            phase: Phase to run.
            cycle_id: Current cycle ID.
            context: Context for handler.
            handler: Optional phase handler callback.

        Returns:
            List of events generated by this phase.
        """
        events: list[SleepEvent] = []

        if handler is not None:
            try:
                handler_events = handler(context)
                events.extend(handler_events)
            except Exception:
                events.append(SleepEvent(
                    event_id=f"{cycle_id}-{phase.value}-error",
                    phase=phase,
                    content=f"Handler error in {phase.value} phase",
                    metadata={"error": True},
                ))
        else:
            events.append(SleepEvent(
                event_id=f"{cycle_id}-{phase.value}-default",
                phase=phase,
                content=f"Default {phase.value} phase completed",
            ))

        self._persist_events(events, cycle_id)
        return events

    def get_cycle(self, cycle_id: str) -> Optional[CycleResult]:
        """Retrieve a completed cycle by ID.

        Args:
            cycle_id: Cycle identifier.

        Returns:
            CycleResult if found, None otherwise.
        """
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM sleep_cycles WHERE cycle_id = ?", (cycle_id,)
        ).fetchone()

        if row is None:
            return None

        import json
        events = self.get_events_for_cycle(cycle_id)
        return CycleResult(
            cycle_id=row["cycle_id"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            phases_completed=json.loads(row["phases_completed"]),
            events=events,
            stats=json.loads(row["stats"]),
        )

    def get_events_for_cycle(self, cycle_id: str) -> list[SleepEvent]:
        """Get all events for a specific cycle.

        Args:
            cycle_id: Cycle identifier.

        Returns:
            List of SleepEvents.
        """
        conn = self._get_conn()
        import json
        rows = conn.execute(
            "SELECT * FROM sleep_events WHERE cycle_id = ? ORDER BY timestamp",
            (cycle_id,),
        ).fetchall()

        return [
            SleepEvent(
                event_id=r["event_id"],
                phase=SleepPhase(r["phase"]),
                content=r["content"],
                timestamp=r["timestamp"],
                metadata=json.loads(r["metadata"]),
            )
            for r in rows
        ]

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent cycle history.

        Args:
            limit: Maximum cycles to return.

        Returns:
            List of cycle summary dicts.
        """
        conn = self._get_conn()
        import json
        rows = conn.execute(
            "SELECT * FROM sleep_cycles ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

        return [
            {
                "cycle_id": r["cycle_id"],
                "started_at": r["started_at"],
                "completed_at": r["completed_at"],
                "phases_completed": json.loads(r["phases_completed"]),
                "stats": json.loads(r["stats"]),
            }
            for r in rows
        ]

    @property
    def current_phase(self) -> SleepPhase:
        """Get the current sleep phase."""
        return self._current_phase

    @property
    def cycle_count(self) -> int:
        """Get total number of completed cycles."""
        return self._cycle_count

    def _persist_cycle(self, result: CycleResult) -> None:
        """Persist cycle result to database."""
        conn = self._get_conn()
        import json
        conn.execute(
            """INSERT OR REPLACE INTO sleep_cycles
               (cycle_id, started_at, completed_at, phases_completed, stats)
               VALUES (?, ?, ?, ?, ?)""",
            (
                result.cycle_id,
                result.started_at,
                result.completed_at,
                json.dumps([p.value for p in result.phases_completed]),
                json.dumps(result.stats),
            ),
        )
        conn.commit()

    def _persist_events(self, events: list[SleepEvent], cycle_id: str) -> None:
        """Persist events to database."""
        conn = self._get_conn()
        import json
        for event in events:
            conn.execute(
                """INSERT OR REPLACE INTO sleep_events
                   (event_id, phase, content, timestamp, cycle_id, metadata)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    event.event_id,
                    event.phase.value,
                    event.content,
                    event.timestamp,
                    cycle_id,
                    json.dumps(event.metadata),
                ),
            )
        conn.commit()

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "SleepCycle":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
