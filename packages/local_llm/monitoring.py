#!/usr/bin/env python3
"""Monitoring — Track tool call success rate, latency per tool, request/response metrics."""

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
DEFAULT_DB_PATH = "~/.cache/n-xyme-mind/local_llm/monitoring.db"

# Batch write configuration
BATCH_SIZE = 10
BATCH_TIMEOUT_SECONDS = 5.0


@dataclass
class ToolMetrics:
    """Metrics for a single tool."""

    tool_name: str
    call_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0
    last_called: Optional[str] = None


@dataclass
class RequestMetrics:
    """Metrics for a single request."""

    request_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    model: str = ""
    prompt: str = ""
    response: str = ""
    tool_calls_made: int = 0
    tools_executed: int = 0
    tools_succeeded: int = 0
    total_latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None


class MonitoringDB:
    """SQLite-based monitoring database for LLM operations.

    Tracks:
    - Tool-level metrics (success rate, latency per tool)
    - Request-level metrics (request/response stats)
    - Aggregate statistics
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """Initialize MonitoringDB.

        Args:
            db_path: Path to SQLite database.
                   Defaults to ~/.cache/n-xyme-mind/local_llm/monitoring.db
        """
        self.db_path = str(Path(db_path).expanduser())
        self._lock = threading.Lock()
        self._write_queue: deque[RequestMetrics] = deque()
        self._flush_event = threading.Event()
        self._shutdown = threading.Event()
        self._flush_thread: Optional[threading.Thread] = None
        self._ensure_db()
        self._start_flush_thread()

    def _ensure_db(self) -> None:
        """Ensure database and tables exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")

        # Requests table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL UNIQUE,
                timestamp TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt TEXT,
                response TEXT,
                tool_calls_made INTEGER NOT NULL DEFAULT 0,
                tools_executed INTEGER NOT NULL DEFAULT 0,
                tools_succeeded INTEGER NOT NULL DEFAULT 0,
                total_latency_ms REAL NOT NULL,
                success INTEGER NOT NULL,
                error TEXT
            )
        """)

        # Tool metrics table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tool_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name TEXT NOT NULL UNIQUE,
                call_count INTEGER NOT NULL DEFAULT 0,
                success_count INTEGER NOT NULL DEFAULT 0,
                failure_count INTEGER NOT NULL DEFAULT 0,
                total_latency_ms REAL NOT NULL DEFAULT 0,
                min_latency_ms REAL NOT NULL DEFAULT 0,
                max_latency_ms REAL NOT NULL DEFAULT 0,
                last_called TEXT
            )
        """)

        # Indices
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_requests_timestamp ON requests(timestamp)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_model ON requests(model)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tool_metrics_name ON tool_metrics(tool_name)"
        )

        conn.commit()
        conn.close()

    def _start_flush_thread(self) -> None:
        """Start background thread for periodic flush."""
        self._flush_thread = threading.Thread(
            target=self._flush_loop,
            name="MonitoringDB-Flush",
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
                """INSERT OR REPLACE INTO requests 
                   (request_id, timestamp, model, prompt, response, tool_calls_made,
                    tools_executed, tools_succeeded, total_latency_ms, success, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        r.request_id,
                        r.timestamp,
                        r.model,
                        r.prompt,
                        r.response,
                        r.tool_calls_made,
                        r.tools_executed,
                        r.tools_succeeded,
                        r.total_latency_ms,
                        1 if r.success else 0,
                        r.error,
                    )
                    for r in records
                ],
            )
            conn.commit()
        except Exception:
            with self._lock:
                self._write_queue.extendleft(reversed(records))
        finally:
            conn.close()

    def record_request(self, metrics: RequestMetrics) -> None:
        """Record a request (queued for batch insert).

        Args:
            metrics: RequestMetrics to record
        """
        with self._lock:
            self._write_queue.append(metrics)
            should_flush = len(self._write_queue) >= BATCH_SIZE
        if should_flush:
            self._flush_queued()

    def record_tool_call(
        self,
        tool_name: str,
        latency_ms: float,
        success: bool,
    ) -> None:
        """Record a tool call execution.

        Args:
            tool_name: Name of the tool
            latency_ms: Time taken to execute
            success: Whether execution succeeded
        """
        conn = sqlite3.connect(self.db_path)
        try:
            # Get current metrics
            row = conn.execute(
                "SELECT * FROM tool_metrics WHERE tool_name = ?",
                (tool_name,),
            ).fetchone()

            if row:
                # Update existing
                conn.execute(
                    """UPDATE tool_metrics SET
                       call_count = call_count + 1,
                       success_count = success_count + ?,
                       failure_count = failure_count + ?,
                       total_latency_ms = total_latency_ms + ?,
                       min_latency_ms = MIN(min_latency_ms, ?),
                       max_latency_ms = MAX(max_latency_ms, ?),
                       last_called = ?
                       WHERE tool_name = ?""",
                    (
                        1 if success else 0,
                        0 if success else 1,
                        latency_ms,
                        latency_ms,
                        latency_ms,
                        datetime.now().isoformat(),
                        tool_name,
                    ),
                )
            else:
                # Insert new
                conn.execute(
                    """INSERT INTO tool_metrics 
                       (tool_name, call_count, success_count, failure_count,
                        total_latency_ms, min_latency_ms, max_latency_ms, last_called)
                       VALUES (?, 1, ?, ?, ?, ?, ?, ?)""",
                    (
                        tool_name,
                        1 if success else 0,
                        0 if success else 1,
                        latency_ms,
                        latency_ms,
                        latency_ms,
                        datetime.now().isoformat(),
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    def flush(self) -> None:
        """Force flush of pending writes."""
        self._flush_queued()
        self._flush_event.set()

    def get_tool_metrics(self, tool_name: Optional[str] = None) -> list[ToolMetrics]:
        """Get tool-level metrics.

        Args:
            tool_name: Optional filter by tool name

        Returns:
            List of ToolMetrics
        """
        self.flush()
        conn = sqlite3.connect(self.db_path)

        if tool_name:
            rows = conn.execute(
                "SELECT * FROM tool_metrics WHERE tool_name = ?",
                (tool_name,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM tool_metrics").fetchall()

        conn.close()

        return [
            ToolMetrics(
                tool_name=row[1],
                call_count=row[2],
                success_count=row[3],
                failure_count=row[4],
                total_latency_ms=row[5],
                min_latency_ms=row[6],
                max_latency_ms=row[7],
                last_called=row[8],
            )
            for row in rows
        ]

    def get_request_metrics(
        self,
        limit: int = 100,
        model: Optional[str] = None,
        success: Optional[bool] = None,
    ) -> list[RequestMetrics]:
        """Get request-level metrics.

        Args:
            limit: Maximum number of requests to return
            model: Optional model filter
            success: Optional success filter

        Returns:
            List of RequestMetrics, most recent first
        """
        self.flush()
        conn = sqlite3.connect(self.db_path)

        query = "SELECT * FROM requests WHERE 1=1"
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
            RequestMetrics(
                request_id=row[1],
                timestamp=row[2],
                model=row[3],
                prompt=row[4] or "",
                response=row[5] or "",
                tool_calls_made=row[6],
                tools_executed=row[7],
                tools_succeeded=row[8],
                total_latency_ms=row[9],
                success=bool(row[10]),
                error=row[11],
            )
            for row in rows
        ]

    def get_aggregate_stats(self) -> dict[str, Any]:
        """Get aggregate statistics.

        Returns:
            Dictionary with aggregate stats
        """
        self.flush()
        conn = sqlite3.connect(self.db_path)

        # Overall request stats
        overall = conn.execute(
            """SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                AVG(total_latency_ms) as avg_latency,
                MIN(total_latency_ms) as min_latency,
                MAX(total_latency_ms) as max_latency,
                SUM(tool_calls_made) as total_tool_calls,
                SUM(tools_succeeded) as total_tool_successes
               FROM requests"""
        ).fetchone()

        # By model
        by_model = conn.execute(
            """SELECT model,
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                    AVG(total_latency_ms) as avg_latency
               FROM requests GROUP BY model"""
        ).fetchall()

        # Tool-level stats
        tool_stats = conn.execute(
            """SELECT 
                    tool_name,
                    call_count,
                    success_count,
                    failure_count,
                    total_latency_ms,
                    min_latency_ms,
                    max_latency_ms
               FROM tool_metrics"""
        ).fetchall()

        conn.close()

        return {
            "total_requests": overall[0] if overall else 0,
            "successful_requests": overall[1] if overall else 0,
            "success_rate": (
                overall[1] / overall[0] if overall and overall[0] > 0 else 0
            ),
            "avg_request_latency_ms": round(overall[3], 2)
            if overall and overall[3]
            else 0,
            "min_request_latency_ms": round(overall[4], 2)
            if overall and overall[4]
            else 0,
            "max_request_latency_ms": round(overall[5], 2)
            if overall and overall[5]
            else 0,
            "total_tool_calls": overall[6] if overall else 0,
            "total_tool_successes": overall[7] if overall else 0,
            "tool_success_rate": (
                overall[7] / overall[6] if overall and overall[6] > 0 else 0
            ),
            "by_model": {
                row[0]: {
                    "total": row[1],
                    "successes": row[2],
                    "success_rate": row[2] / row[1] if row[1] > 0 else 0,
                    "avg_latency_ms": round(row[3], 2) if row[3] else 0,
                }
                for row in by_model
            },
            "by_tool": {
                row[0]: {
                    "call_count": row[1],
                    "success_count": row[2],
                    "failure_count": row[3],
                    "success_rate": row[2] / row[1] if row[1] > 0 else 0,
                    "total_latency_ms": round(row[4], 2),
                    "min_latency_ms": round(row[5], 2),
                    "max_latency_ms": round(row[6], 2),
                    "avg_latency_ms": round(row[4] / row[1], 2) if row[1] > 0 else 0,
                }
                for row in tool_stats
            },
        }

    def close(self) -> None:
        """Shutdown the tracker and flush pending writes."""
        self._shutdown.set()
        self._flush_event.set()
        if self._flush_thread:
            self._flush_thread.join(timeout=5.0)
        self.flush()

    def __enter__(self) -> "MonitoringDB":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


# Global singleton
_monitor: Optional[MonitoringDB] = None
_monitor_lock = threading.Lock()


def get_monitor() -> MonitoringDB:
    """Get or create the global MonitoringDB instance."""
    global _monitor
    with _monitor_lock:
        if _monitor is None:
            _monitor = MonitoringDB()
        return _monitor


def record_request(
    request_id: str,
    model: str,
    prompt: str = "",
    response: str = "",
    tool_calls_made: int = 0,
    tools_executed: int = 0,
    tools_succeeded: int = 0,
    total_latency_ms: float = 0.0,
    success: bool = True,
    error: Optional[str] = None,
) -> None:
    """Convenience function to record a request."""
    metrics = RequestMetrics(
        request_id=request_id,
        model=model,
        prompt=prompt,
        response=response,
        tool_calls_made=tool_calls_made,
        tools_executed=tools_executed,
        tools_succeeded=tools_succeeded,
        total_latency_ms=total_latency_ms,
        success=success,
        error=error,
    )
    get_monitor().record_request(metrics)


def record_tool_call(
    tool_name: str,
    latency_ms: float,
    success: bool,
) -> None:
    """Convenience function to record a tool call."""
    get_monitor().record_tool_call(tool_name, latency_ms, success)


def get_tool_metrics(tool_name: Optional[str] = None) -> list[ToolMetrics]:
    """Convenience function to get tool metrics."""
    return get_monitor().get_tool_metrics(tool_name)


def get_request_metrics(
    limit: int = 100,
    model: Optional[str] = None,
) -> list[RequestMetrics]:
    """Convenience function to get request metrics."""
    return get_monitor().get_request_metrics(limit=limit, model=model)


def get_stats() -> dict[str, Any]:
    """Convenience function to get aggregate stats."""
    return get_monitor().get_aggregate_stats()
