#!/usr/bin/env python3
"""RunTracker — SQLite-based run tracking for Golden Spine.

Records every inference request/response for debugging and analytics.
Thread-safe with batched writes for high-throughput scenarios.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Default database path
DEFAULT_DB_PATH = "~/.cache/n-xyme-mind/spine/runs.db"

# Batch write configuration
BATCH_SIZE = 10
BATCH_TIMEOUT_SECONDS = 5.0


@dataclass
class RunRecord:
    """Record of a single model inference run."""

    run_id: str
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    model: str = ""
    prompt: str = ""
    response: str = ""
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    fallback_used: bool = False
    circuit_state: str = "closed"  # "closed", "open", "half_open"
    retry_count: int = 0


class RunTracker:
    """SQLite-based run tracker with thread-safe batched writes."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """Initialize RunTracker.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.cache/n-xyme-mind/spine/runs.db
        """
        self.db_path = str(Path(db_path).expanduser())
        self._lock = threading.Lock()
        self._write_queue: deque[RunRecord] = deque()
        self._flush_event = threading.Event()
        self._shutdown = threading.Event()
        self._flush_thread: Optional[threading.Thread] = None
        self._ensure_db()
        self._start_flush_thread()

    def _ensure_db(self) -> None:
        """Ensure database and tables exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        # Enable WAL mode for concurrent reads
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL UNIQUE,
                timestamp TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt TEXT,
                response TEXT,
                latency_ms REAL NOT NULL,
                success INTEGER NOT NULL,
                error TEXT,
                fallback_used INTEGER NOT NULL DEFAULT 0,
                circuit_state TEXT NOT NULL DEFAULT 'closed',
                retry_count INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_timestamp ON runs(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_model ON runs(model)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_success ON runs(success)")
        conn.commit()
        conn.close()

    def _start_flush_thread(self) -> None:
        """Start background thread for periodic flush."""
        self._flush_thread = threading.Thread(
            target=self._flush_loop,
            name="RunTracker-Flush",
            daemon=True,
        )
        self._flush_thread.start()

    def _flush_loop(self) -> None:
        """Background loop that flushes queue periodically."""
        while not self._shutdown.is_set():
            self._flush_event.wait(BATCH_TIMEOUT_SECONDS)
            if not self._shutdown.is_set():
                self._flush_queued()

    def _flush_queued(self) -> None:
        """Flush queued records to database."""
        with self._lock:
            if not self._write_queue:
                return
            records = list(self._write_queue)
            self._write_queue.clear()

        if not records:
            return

        conn = sqlite3.connect(self.db_path)
        try:
            conn.executemany(
                """INSERT OR REPLACE INTO runs 
                   (run_id, timestamp, model, prompt, response, latency_ms, 
                    success, error, fallback_used, circuit_state, retry_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        r.run_id,
                        r.timestamp,
                        r.model,
                        r.prompt,
                        r.response,
                        r.latency_ms,
                        1 if r.success else 0,
                        r.error,
                        1 if r.fallback_used else 0,
                        r.circuit_state,
                        r.retry_count,
                    )
                    for r in records
                ],
            )
            conn.commit()
        except Exception:
            # Re-queue on failure (best effort)
            with self._lock:
                self._write_queue.extendleft(reversed(records))
        finally:
            conn.close()

    def record_run(self, record: RunRecord) -> None:
        """Record a run (queued for batch insert).

        Args:
            record: RunRecord to record
        """
        with self._lock:
            self._write_queue.append(record)
            should_flush = len(self._write_queue) >= BATCH_SIZE
        if should_flush:
            self._flush_queued()

    def flush(self) -> None:
        """Force flush of pending writes."""
        self._flush_queued()
        self._flush_event.set()

    def get_runs(
        self,
        limit: int = 100,
        model: Optional[str] = None,
        success: Optional[bool] = None,
    ) -> list[RunRecord]:
        """Retrieve runs with optional filters.

        Args:
            limit: Maximum number of runs to return (default 100)
            model: Optional model filter
            success: Optional success filter

        Returns:
            List of RunRecord objects, most recent first
        """
        # Flush before reading to ensure latest data
        self.flush()

        conn = sqlite3.connect(self.db_path)
        query = "SELECT * FROM runs WHERE 1=1"
        params: list[Any] = []

        if model:
            query += " AND model = ?"
            params.append(model)
        if success is not None:
            query += " AND success = ?"
            params.append(1 if success else 0)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()

        return [
            RunRecord(
                run_id=row[1],
                timestamp=row[2],
                model=row[3],
                prompt=row[4] or "",
                response=row[5] or "",
                latency_ms=row[6],
                success=bool(row[7]),
                error=row[8],
                fallback_used=bool(row[9]),
                circuit_state=row[10],
                retry_count=row[11],
            )
            for row in rows
        ]

    def get_last_run(self) -> Optional[RunRecord]:
        """Get the most recent run.

        Returns:
            RunRecord or None if no runs exist
        """
        runs = self.get_runs(limit=1)
        return runs[0] if runs else None

    def get_stats(self) -> dict[str, Any]:
        """Get aggregate statistics across all runs.

        Returns:
            Dictionary with aggregate stats
        """
        self.flush()

        conn = sqlite3.connect(self.db_path)

        # Overall stats
        overall = conn.execute(
            """SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                AVG(latency_ms) as avg_latency,
                MIN(latency_ms) as min_latency,
                MAX(latency_ms) as max_latency
               FROM runs"""
        ).fetchone()

        # By model
        by_model = conn.execute(
            """SELECT model,
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                    AVG(latency_ms) as avg_latency
               FROM runs GROUP BY model"""
        ).fetchall()

        # By circuit state
        by_circuit = conn.execute(
            """SELECT circuit_state,
                    COUNT(*) as total
               FROM runs GROUP BY circuit_state"""
        ).fetchall()

        # Fallback usage
        fallback_stats = conn.execute(
            """SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN fallback_used = 1 THEN 1 ELSE 0 END) as fallbacks
               FROM runs"""
        ).fetchone()

        conn.close()

        return {
            "total_runs": overall[0] if overall else 0,
            "successful_runs": overall[1] if overall else 0,
            "success_rate": (
                overall[1] / overall[0] if overall and overall[0] > 0 else 0
            ),
            "avg_latency_ms": round(overall[2], 2) if overall and overall[2] else 0,
            "min_latency_ms": round(overall[3], 2) if overall and overall[3] else 0,
            "max_latency_ms": round(overall[4], 2) if overall and overall[4] else 0,
            "by_model": {
                row[0]: {
                    "total": row[1],
                    "successes": row[2],
                    "success_rate": row[2] / row[1] if row[1] > 0 else 0,
                    "avg_latency_ms": round(row[3], 2) if row[3] else 0,
                }
                for row in by_model
            },
            "by_circuit_state": {row[0]: row[1] for row in by_circuit},
            "fallback_count": fallback_stats[1] if fallback_stats else 0,
        }

    def close(self) -> None:
        """Shutdown the tracker and flush pending writes."""
        self._shutdown.set()
        self._flush_event.set()
        if self._flush_thread:
            self._flush_thread.join(timeout=5.0)
        self.flush()

    def __enter__(self) -> "RunTracker":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


# Global singleton
_tracker: Optional[RunTracker] = None
_tracker_lock = threading.Lock()


def get_tracker() -> RunTracker:
    """Get or create the global RunTracker instance."""
    global _tracker
    with _tracker_lock:
        if _tracker is None:
            _tracker = RunTracker()
        return _tracker


def record_run(
    run_id: str,
    model: str,
    prompt: str = "",
    response: str = "",
    latency_ms: float = 0.0,
    success: bool = True,
    error: Optional[str] = None,
    fallback_used: bool = False,
    circuit_state: str = "closed",
    retry_count: int = 0,
) -> None:
    """Convenience function to record a run."""
    record = RunRecord(
        run_id=run_id,
        model=model,
        prompt=prompt,
        response=response,
        latency_ms=latency_ms,
        success=success,
        error=error,
        fallback_used=fallback_used,
        circuit_state=circuit_state,
        retry_count=retry_count,
    )
    get_tracker().record_run(record)


def get_runs(limit: int = 100) -> list[RunRecord]:
    """Convenience function to get recent runs."""
    return get_tracker().get_runs(limit=limit)


def get_stats() -> dict[str, Any]:
    """Convenience function to get run statistics."""
    return get_tracker().get_stats()


def get_last_run() -> Optional[RunRecord]:
    """Convenience function to get the last run."""
    return get_tracker().get_last_run()