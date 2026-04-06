"""Forgetting Curve — Ebbinghaus decay R=e^(-t/S).

Implements the Ebbinghaus forgetting curve model for memory decay:
    R(t) = e^(-t / S)

Where:
    R = retrievability (0.0 to 1.0)
    t = time since last review (in seconds)
    S = stability factor (determined by repetitions and difficulty)

Supports spaced repetition scheduling: when retrievability drops
below a threshold, the memory should be reviewed.
"""

from __future__ import annotations

import math
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class MemoryTrace:
    """A trace of memory reviews for spaced repetition.

    Attributes:
        trace_id: Unique identifier.
        memory_id: Associated memory identifier.
        reviews: List of review timestamps.
        difficulty: Difficulty factor 0.0-1.0 (higher = harder to remember).
        stability: Current stability factor in seconds.
        retrievability: Current retrievability 0.0-1.0.
        created_at: Unix timestamp of first review.
    """

    trace_id: str
    memory_id: str
    reviews: list[float] = field(default_factory=list)
    difficulty: float = 0.5
    stability: float = 86400.0
    retrievability: float = 1.0
    created_at: float = field(default_factory=time.time)

    def add_review(self, timestamp: Optional[float] = None,
                   quality: float = 0.5) -> None:
        """Record a review and update stability/retrievability.

        Args:
            timestamp: Review time (default: now).
            quality: Review quality 0.0 (failed) to 1.0 (perfect).
        """
        ts = timestamp or time.time()
        self.reviews.append(ts)

        if len(self.reviews) == 1:
            self.stability = self._initial_stability(quality)
        else:
            self.stability = self._update_stability(quality)

        self.retrievability = 1.0
        self.difficulty = self._update_difficulty(quality)

    def current_retrievability(self, now: Optional[float] = None) -> float:
        """Calculate current retrievability using Ebbinghaus formula.

        Args:
            now: Current time (default: time.time()).

        Returns:
            Retrievability score 0.0-1.0.
        """
        if not self.reviews:
            return 0.0

        t = (now or time.time()) - self.reviews[-1]
        return ebbinghaus_retrievability(t, self.stability)

    def next_review_time(self, threshold: float = 0.3,
                         now: Optional[float] = None) -> float:
        """Calculate when retrievability will drop below threshold.

        Args:
            threshold: Retrievability threshold for review.
            now: Current time (default: time.time()).

        Returns:
            Unix timestamp when review should occur.
        """
        if self.stability <= 0:
            return now or time.time()

        t = -self.stability * math.log(threshold)
        last_review = self.reviews[-1] if self.reviews else (now or time.time())
        return last_review + t

    def _initial_stability(self, quality: float) -> float:
        """Compute initial stability from first review quality."""
        base = 86400.0
        return base * (0.5 + quality)

    def _update_stability(self, quality: float) -> float:
        """Update stability based on review quality and current stability."""
        factor = 1.0 + (0.5 * quality) + (0.3 * (1.0 - self.difficulty))
        return self.stability * factor

    def _update_difficulty(self, quality: float) -> float:
        """Update difficulty based on review quality."""
        target = 1.0 - quality
        return self.difficulty * 0.7 + target * 0.3


class ForgettingCurve:
    """Manages forgetting curves for multiple memory traces.

    Provides spaced repetition scheduling and retrievability tracking
    for a collection of memories.

    Args:
        db_path: Path to SQLite database. Uses in-memory if None.
        default_threshold: Retrievability threshold for review (default: 0.3).
    """

    def __init__(self, db_path: Optional[str] = None,
                 default_threshold: float = 0.3) -> None:
        self._db_path = db_path or ":memory:"
        self._threshold = default_threshold
        self._conn: Optional[sqlite3.Connection] = None
        self._traces: dict[str, MemoryTrace] = {}
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
            CREATE TABLE IF NOT EXISTS memory_traces (
                trace_id TEXT PRIMARY KEY,
                memory_id TEXT NOT NULL,
                reviews TEXT NOT NULL DEFAULT '[]',
                difficulty REAL NOT NULL DEFAULT 0.5,
                stability REAL NOT NULL DEFAULT 86400.0,
                retrievability REAL NOT NULL DEFAULT 1.0,
                created_at REAL NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_traces_memory ON memory_traces(memory_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_traces_retrievability ON memory_traces(retrievability)"
        )
        conn.commit()

    def create_trace(self, memory_id: str,
                     difficulty: float = 0.5) -> MemoryTrace:
        """Create a new memory trace.

        Args:
            memory_id: Associated memory identifier.
            difficulty: Initial difficulty 0.0-1.0.

        Returns:
            The created MemoryTrace.

        Raises:
            ValueError: If difficulty is out of range.
        """
        if not 0.0 <= difficulty <= 1.0:
            raise ValueError("Difficulty must be between 0.0 and 1.0")

        trace = MemoryTrace(
            trace_id=f"trace-{memory_id}",
            memory_id=memory_id,
            difficulty=difficulty,
        )
        self._traces[trace.trace_id] = trace
        self._persist_trace(trace)
        return trace

    def record_review(self, memory_id: str,
                      quality: float = 0.5,
                      timestamp: Optional[float] = None) -> Optional[MemoryTrace]:
        """Record a review for an existing memory trace.

        Args:
            memory_id: Memory to review.
            quality: Review quality 0.0-1.0.
            timestamp: Review time (default: now).

        Returns:
            Updated MemoryTrace, or None if trace doesn't exist.
        """
        if not 0.0 <= quality <= 1.0:
            raise ValueError("Quality must be between 0.0 and 1.0")

        trace_id = f"trace-{memory_id}"
        trace = self._traces.get(trace_id)

        if trace is None:
            row = self._get_conn().execute(
                "SELECT * FROM memory_traces WHERE trace_id = ?",
                (trace_id,),
            ).fetchone()
            if row is None:
                return None
            trace = _row_to_trace(row)
            self._traces[trace_id] = trace

        trace.add_review(timestamp, quality)
        trace.retrievability = trace.current_retrievability()
        self._persist_trace(trace)
        return trace

    def get_trace(self, memory_id: str) -> Optional[MemoryTrace]:
        """Get a memory trace by memory ID.

        Args:
            memory_id: Memory identifier.

        Returns:
            MemoryTrace if found, None otherwise.
        """
        trace_id = f"trace-{memory_id}"
        trace = self._traces.get(trace_id)
        if trace is not None:
            trace.retrievability = trace.current_retrievability()
            return trace

        row = self._get_conn().execute(
            "SELECT * FROM memory_traces WHERE trace_id = ?",
            (trace_id,),
        ).fetchone()

        if row is None:
            return None

        trace = _row_to_trace(row)
        self._traces[trace_id] = trace
        trace.retrievability = trace.current_retrievability()
        return trace

    def needs_review(self, threshold: Optional[float] = None,
                     now: Optional[float] = None) -> list[MemoryTrace]:
        """Find all memories that need review.

        Args:
            threshold: Retrievability threshold (default: instance threshold).
            now: Current time (default: time.time()).

        Returns:
            List of MemoryTraces below the threshold.
        """
        thresh = threshold if threshold is not None else self._threshold
        due: list[MemoryTrace] = []

        for trace in self._traces.values():
            r = trace.current_retrievability(now)
            if r < thresh:
                due.append(trace)

        return sorted(due, key=lambda t: t.current_retrievability(now))

    def get_review_schedule(self, now: Optional[float] = None) -> list[dict[str, Any]]:
        """Get upcoming review schedule for all traces.

        Args:
            now: Current time (default: time.time()).

        Returns:
            List of dicts with memory_id, next_review, retrievability.
        """
        schedule = []
        for trace in self._traces.values():
            next_review = trace.next_review_time(self._threshold, now)
            schedule.append({
                "memory_id": trace.memory_id,
                "next_review": next_review,
                "retrievability": trace.current_retrievability(now),
                "stability": trace.stability,
            })
        return sorted(schedule, key=lambda x: x["next_review"])

    def delete_trace(self, memory_id: str) -> bool:
        """Delete a memory trace.

        Args:
            memory_id: Memory to delete trace for.

        Returns:
            True if deleted, False if not found.
        """
        trace_id = f"trace-{memory_id}"
        self._traces.pop(trace_id, None)
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM memory_traces WHERE trace_id = ?", (trace_id,)
        )
        conn.commit()
        return cursor.rowcount > 0

    def get_stats(self) -> dict[str, Any]:
        """Get forgetting curve statistics."""
        now = time.time()
        traces = list(self._traces.values())

        if not traces:
            return {
                "total_traces": 0,
                "avg_retrievability": 0.0,
                "avg_stability": 0.0,
                "needs_review": 0,
            }

        retrievabilities = [t.current_retrievability(now) for t in traces]
        stabilities = [t.stability for t in traces]
        needs_review = sum(
            1 for r in retrievabilities if r < self._threshold
        )

        return {
            "total_traces": len(traces),
            "avg_retrievability": round(
                sum(retrievabilities) / len(retrievabilities), 4
            ),
            "avg_stability": round(
                sum(stabilities) / len(stabilities), 2
            ),
            "needs_review": needs_review,
        }
    def _persist_trace(self, trace: MemoryTrace) -> None:
        import json
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO memory_traces
               (trace_id, memory_id, reviews, difficulty, stability, retrievability, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                trace.trace_id,
                trace.memory_id,
                json.dumps(trace.reviews),
                trace.difficulty,
                trace.stability,
                trace.retrievability,
                trace.created_at,
            ),
        )
        conn.commit()

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "ForgettingCurve":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


def ebbinghaus_retrievability(t: float, s: float) -> float:
    """Calculate retrievability using the Ebbinghaus forgetting curve.

    Formula: R = e^(-t / S)

    Args:
        t: Time since last review (seconds).
        s: Stability factor (seconds).

    Returns:
        Retrievability score 0.0-1.0.
    """
    if s <= 0:
        return 0.0
    if t <= 0:
        return 1.0
    return math.exp(-t / s)


def _row_to_trace(row: sqlite3.Row) -> MemoryTrace:
    import json
    return MemoryTrace(
        trace_id=row["trace_id"],
        memory_id=row["memory_id"],
        reviews=json.loads(row["reviews"]),
        difficulty=row["difficulty"],
        stability=row["stability"],
        retrievability=row["retrievability"],
        created_at=row["created_at"],
    )
