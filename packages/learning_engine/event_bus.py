"""
Learning Event Bus - Simple pub/sub for learning signals.

Provides cross-module communication for learning events like skill outcomes,
search results, and preference updates. Uses in-memory queue with SQLite
persistence via LearningDB.
"""

import ast
import json

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from .db import get_db, LearningDB


@dataclass
class LearningEvent:
    """Represents a learning event across modules."""

    source: str
    task_id: str
    action: str
    success: bool
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for database storage."""
        return {
            "source": self.source,
            "task_id": self.task_id,
            "action": self.action,
            "success": 1 if self.success else 0,
            "context": str(self.context),
            "timestamp": self.timestamp.isoformat(),
        }


class LearningEventBus:
    """
    Simple pub/sub event bus for learning signals.

    Thread-safe in-memory queue with batch SQLite persistence.
    Auto-flushes every 100 events or 30 seconds.
    """

    _instance: "LearningEventBus | None" = None
    _instance_lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "LearningEventBus":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._initialized: bool = True
        self._db: LearningDB = get_db()
        self._queue: list[LearningEvent] = []
        self._lock: threading.Lock = threading.Lock()
        self._subscribers: dict[str, list[Callable[[LearningEvent], None]]] = (
            defaultdict(list)
        )
        self._flush_threshold: int = 100
        self._flush_interval: float = 30.0  # seconds
        self._last_flush: float = time.time()

        self._init_db()

    def _init_db(self) -> None:
        """Initialize the events table if it doesn't exist."""
        conn = self._db.get_connection("learning_events.db")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                task_id TEXT NOT NULL,
                action TEXT NOT NULL,
                success INTEGER NOT NULL,
                context TEXT,
                timestamp TEXT NOT NULL
            )
        """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_id ON events(task_id)
        """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_source ON events(source)
        """
        )
        conn.commit()

    def publish(self, event: LearningEvent) -> None:
        """
        Publish an event to the bus.

        Adds to in-memory queue and triggers handlers immediately.
        Auto-flushes when threshold is reached.
        """
        with self._lock:
            self._queue.append(event)

            # Notify subscribers immediately
            if event.source in self._subscribers:
                for handler in self._subscribers[event.source]:
                    try:
                        handler(event)
                    except Exception:
                        pass  # Don't let handler errors break the bus

            # Check auto-flush
            if (
                len(self._queue) >= self._flush_threshold
                or (time.time() - self._last_flush) >= self._flush_interval
            ):
                self.flush()

    def subscribe(self, source: str, handler: Callable[[LearningEvent], None]) -> None:
        """
        Subscribe to events from a specific source.

        Args:
            source: The event source to subscribe to (e.g., 'skill', 'search')
            handler: Callback function that receives LearningEvent
        """
        with self._lock:
            self._subscribers[source].append(handler)

    def flush(self) -> None:
        """Batch-write pending events to SQLite."""
        with self._lock:
            if not self._queue:
                return

            conn = self._db.get_connection("learning_events.db")
            events_to_write = self._queue.copy()
            self._queue.clear()
            self._last_flush = time.time()

        # Write outside the lock to avoid blocking publishes
        for event in events_to_write:
            conn.execute(
                """INSERT INTO events (source, task_id, action, success, context, timestamp)
                   VALUES (:source, :task_id, :action, :success, :context, :timestamp)""",
                event.to_dict(),
            )
        conn.commit()

    def get_events(self, task_id: str, limit: int = 100) -> list[LearningEvent]:
        """
        Query events for a specific task_id.

        Args:
            task_id: The task ID to filter events by
            limit: Maximum number of events to return (default: 100)

        Returns:
            List of LearningEvent objects
        """
        # First flush pending events
        self.flush()

        conn = self._db.get_connection("learning_events.db")
        cursor = conn.execute(
            """SELECT source, task_id, action, success, context, timestamp
               FROM events WHERE task_id = :task_id
               ORDER BY timestamp DESC LIMIT :limit""",
            {"task_id": task_id, "limit": limit},
        )

        events: list[LearningEvent] = []
        for row in cursor.fetchall():
            events.append(
                LearningEvent(
                    source=row["source"],
                    task_id=row["task_id"],
                    action=row["action"],
                    success=bool(row["success"]),
                    context=json.loads(row["context"]) if row["context"] else {},
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                )
            )

        return events


# Singleton instance for convenience
_event_bus_instance: "LearningEventBus | None" = None
_event_bus_lock: threading.Lock = threading.Lock()


def get_event_bus() -> LearningEventBus:
    """Get the singleton LearningEventBus instance."""
    global _event_bus_instance
    if _event_bus_instance is None:
        with _event_bus_lock:
            if _event_bus_instance is None:
                _event_bus_instance = LearningEventBus()
    return _event_bus_instance
