"""SQLite-based message queue with priority, consumer groups, and dead letter queue."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
import logging
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any

try:
    from packages.infrastructure.monitoring.metrics_collector import get_metrics_collector
except ImportError:
    get_metrics_collector = None

try:
    from packages.infrastructure.monitoring.telemetry import get_logger
except ImportError:
    get_logger = None

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / ".sisyphus" / "queue.db"

PRIORITY_MAP = {"high": 3, "normal": 2, "low": 1}
PRIORITY_REVERSE = {3: "high", 2: "normal", 1: "low"}

DEFAULT_TTL_SECONDS = 3600
DEFAULT_MAX_RETRIES = 3
DEFAULT_VISIBILITY_TIMEOUT_SECONDS = 300


class MessagePriority(IntEnum):
    HIGH = 3
    NORMAL = 2
    LOW = 1


@dataclass
class Message:
    id: str
    body: str
    priority: MessagePriority
    consumer_id: str | None = None
    status: str = "pending"
    retries: int = 0
    max_retries: int = DEFAULT_MAX_RETRIES
    ttl_seconds: int = DEFAULT_TTL_SECONDS
    created_at: float = field(default_factory=time.time)
    visible_at: float = 0.0
    updated_at: float = field(default_factory=time.time)
    error: str = ""

    def is_expired(self) -> bool:
        return time.time() > (self.created_at + self.ttl_seconds)

    def is_visible(self) -> bool:
        return time.time() >= self.visible_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "body": self.body,
            "priority": self.priority.name.lower(),
            "consumer_id": self.consumer_id,
            "status": self.status,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "ttl_seconds": self.ttl_seconds,
            "created_at": self.created_at,
            "visible_at": self.visible_at,
            "updated_at": self.updated_at,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        return cls(
            id=data["id"],
            body=data["body"],
            priority=MessagePriority(data["priority_value"]),
            consumer_id=data.get("consumer_id"),
            status=data.get("status", "pending"),
            retries=data.get("retries", 0),
            max_retries=data.get("max_retries", DEFAULT_MAX_RETRIES),
            ttl_seconds=data.get("ttl_seconds", DEFAULT_TTL_SECONDS),
            created_at=data.get("created_at", time.time()),
            visible_at=data.get("visible_at", 0.0),
            updated_at=data.get("updated_at", time.time()),
            error=data.get("error", ""),
        )

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Message:
        return cls(
            id=row["id"],
            body=row["body"],
            priority=MessagePriority(row["priority"]),
            consumer_id=row["consumer_id"],
            status=row["status"],
            retries=row["retries"],
            max_retries=row["max_retries"],
            ttl_seconds=row["ttl_seconds"],
            created_at=row["created_at"],
            visible_at=row["visible_at"],
            updated_at=row["updated_at"],
            error=row["error"] if "error" in row.keys() else "",
        )


class MessageQueue:
    """SQLite-based message queue with priority, consumer groups, and dead letter queue."""

    def __init__(
        self,
        db_path: Path | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        visibility_timeout: int = DEFAULT_VISIBILITY_TIMEOUT_SECONDS,
        default_ttl: int = DEFAULT_TTL_SECONDS,
    ):
        self._db_path = db_path or DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._lock = threading.Lock()
        self._max_retries = max_retries
        self._visibility_timeout = visibility_timeout
        self._default_ttl = default_ttl
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(str(self._db_path), timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                body TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 2,
                consumer_id TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                retries INTEGER NOT NULL DEFAULT 0,
                max_retries INTEGER NOT NULL DEFAULT 3,
                ttl_seconds INTEGER NOT NULL DEFAULT 3600,
                created_at REAL NOT NULL,
                visible_at REAL NOT NULL DEFAULT 0,
                updated_at REAL NOT NULL,
                error TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_messages_status_priority
                ON messages(status, priority DESC, visible_at, created_at);
            CREATE INDEX IF NOT EXISTS idx_messages_created_at
                ON messages(created_at);
            CREATE INDEX IF NOT EXISTS idx_messages_consumer
                ON messages(consumer_id);

            CREATE TABLE IF NOT EXISTS dead_letters (
                id TEXT PRIMARY KEY,
                body TEXT NOT NULL,
                priority INTEGER NOT NULL,
                consumer_id TEXT,
                original_status TEXT NOT NULL,
                retries INTEGER NOT NULL,
                max_retries INTEGER NOT NULL,
                ttl_seconds INTEGER NOT NULL,
                created_at REAL NOT NULL,
                moved_at REAL NOT NULL,
                error TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_dead_letters_moved_at
                ON dead_letters(moved_at);
        """)
        conn.commit()

    def enqueue(
        self,
        body: str | dict[str, Any],
        priority: MessagePriority | str = MessagePriority.NORMAL,
        ttl_seconds: int | None = None,
        message_id: str | None = None,
        max_retries: int | None = None,
    ) -> str:
        if isinstance(body, dict):
            body = json.dumps(body)
        if isinstance(priority, str):
            priority = MessagePriority(PRIORITY_MAP.get(priority.lower(), 2))
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        retries = max_retries if max_retries is not None else self._max_retries
        msg_id = message_id or str(uuid.uuid4())
        now = time.time()

        msg = Message(
            id=msg_id,
            body=body,
            priority=priority,
            status="pending",
            retries=0,
            max_retries=retries,
            ttl_seconds=ttl,
            created_at=now,
            visible_at=now,
            updated_at=now,
        )

        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO messages (
                id, body, priority, consumer_id, status, retries,
                max_retries, ttl_seconds, created_at, visible_at, updated_at, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                msg.id,
                msg.body,
                msg.priority,
                msg.consumer_id,
                msg.status,
                msg.retries,
                msg.max_retries,
                msg.ttl_seconds,
                msg.created_at,
                msg.visible_at,
                msg.updated_at,
                msg.error,
            ),
        )
        conn.commit()

        self._emit_metric("queue_messages_enqueued_total", 1)
        self._emit_metric("queue_depth", self.get_queue_depth())
        self._log_event(
            "enqueue",
            {"message_id": msg.id, "priority": msg.priority.name.lower(), "ttl": ttl},
        )

        return msg.id

    def dequeue(self, consumer_id: str) -> Message | None:
        now = time.time()
        visibility_until = now + self._visibility_timeout

        conn = self._get_conn()
        with self._lock:
            row = conn.execute(
                """
                SELECT * FROM messages
                WHERE status = 'pending'
                  AND visible_at <= ?
                  AND (created_at + ttl_seconds) > ?
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
                """,
                (now, now),
            ).fetchone()

            if row is None:
                return None

            msg = Message.from_row(row)
            msg.status = "processing"
            msg.consumer_id = consumer_id
            msg.visible_at = visibility_until
            msg.updated_at = now
            conn.execute(
                """
                UPDATE messages
                SET status = 'processing',
                    consumer_id = ?,
                    visible_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (consumer_id, visibility_until, now, msg.id),
            )
            conn.commit()

        self._emit_metric("queue_messages_dequeued_total", 1)
        self._emit_metric("queue_depth", self.get_queue_depth())
        self._log_event("dequeue", {"message_id": msg.id, "consumer_id": consumer_id})

        return msg

    def ack(self, message_id: str) -> bool:
        now = time.time()
        conn = self._get_conn()
        with self._lock:
            cursor = conn.execute(
                "SELECT * FROM messages WHERE id = ? AND status = 'processing'",
                (message_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return False

            conn.execute(
                "DELETE FROM messages WHERE id = ?",
                (message_id,),
            )
            conn.commit()

        self._emit_metric("queue_messages_acked_total", 1)
        self._emit_metric("queue_depth", self.get_queue_depth())
        self._log_event("ack", {"message_id": message_id})

        return True

    def nack(self, message_id: str, requeue: bool = True) -> bool:
        now = time.time()
        conn = self._get_conn()

        with self._lock:
            row = conn.execute(
                "SELECT * FROM messages WHERE id = ? AND status = 'processing'",
                (message_id,),
            ).fetchone()

            if row is None:
                return False

            msg = Message.from_row(row)
            msg.retries += 1
            msg.updated_at = now

            if requeue and msg.retries < msg.max_retries:
                msg.status = "pending"
                msg.consumer_id = None
                msg.visible_at = now
                conn.execute(
                    """
                    UPDATE messages
                    SET status = ?, consumer_id = ?, retries = ?,
                        visible_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        msg.status,
                        msg.consumer_id,
                        msg.retries,
                        msg.visible_at,
                        msg.updated_at,
                        msg.id,
                    ),
                )
                self._log_event(
                    "nack_requeue", {"message_id": message_id, "retry": msg.retries}
                )
            else:
                self._move_to_dead_letter(msg, now)
                conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))
                self._emit_metric("queue_dead_letters_total", 1)
                self._log_event(
                    "nack_dead_letter",
                    {"message_id": message_id, "retries": msg.retries},
                )

            conn.commit()

        self._emit_metric("queue_messages_nacked_total", 1)
        self._emit_metric("queue_depth", self.get_queue_depth())
        return True

    def get_queue_depth(self) -> int:
        now = time.time()
        conn = self._get_conn()
        row = conn.execute(
            """
            SELECT COUNT(*) as cnt FROM messages
            WHERE status = 'pending'
              AND visible_at <= ?
              AND (created_at + ttl_seconds) > ?
            """,
            (now, now),
        ).fetchone()
        return row["cnt"]

    def get_queue_depth_by_priority(self) -> dict[str, int]:
        now = time.time()
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT priority, COUNT(*) as cnt FROM messages
            WHERE status = 'pending'
              AND visible_at <= ?
              AND (created_at + ttl_seconds) > ?
            GROUP BY priority
            """,
            (now, now),
        ).fetchall()

        result = {"high": 0, "normal": 0, "low": 0}
        for row in rows:
            prio = PRIORITY_REVERSE.get(row["priority"], "normal")
            result[prio] = row["cnt"]
        return result

    def get_dead_letters(self) -> list[Message]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM dead_letters ORDER BY moved_at DESC"
        ).fetchall()
        return [self._row_to_dead_letter_msg(row) for row in rows]

    def purge_expired(self) -> int:
        now = time.time()
        conn = self._get_conn()
        with self._lock:
            cursor = conn.execute(
                """
                DELETE FROM messages
                WHERE status = 'pending'
                  AND (created_at + ttl_seconds) <= ?
                """,
                (now,),
            )
            deleted = cursor.rowcount
            conn.commit()

        if deleted > 0:
            self._emit_metric("queue_messages_expired_total", deleted)
            self._emit_metric("queue_depth", self.get_queue_depth())
            self._log_event("purge_expired", {"deleted": deleted})

        return deleted

    def get_message(self, message_id: str) -> Message | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM messages WHERE id = ?", (message_id,)
        ).fetchone()
        if row is None:
            return None
        return Message.from_row(row)

    def requeue_dead_letter(self, message_id: str) -> bool:
        conn = self._get_conn()
        with self._lock:
            row = conn.execute(
                "SELECT * FROM dead_letters WHERE id = ?", (message_id,)
            ).fetchone()
            if row is None:
                return False

            now = time.time()
            conn.execute(
                """
                INSERT OR REPLACE INTO messages (
                    id, body, priority, consumer_id, status, retries,
                    max_retries, ttl_seconds, created_at, visible_at, updated_at, error
                ) VALUES (?, ?, ?, NULL, 'pending', 0, ?, ?, ?, ?, ?, '')
                """,
                (
                    row["id"],
                    row["body"],
                    row["priority"],
                    row["max_retries"],
                    row["ttl_seconds"],
                    row["created_at"],
                    now,
                    now,
                ),
            )
            conn.execute("DELETE FROM dead_letters WHERE id = ?", (message_id,))
            conn.commit()

        self._log_event("dead_letter_requeue", {"message_id": message_id})
        return True

    def delete_dead_letter(self, message_id: str) -> bool:
        conn = self._get_conn()
        with self._lock:
            cursor = conn.execute(
                "DELETE FROM dead_letters WHERE id = ?", (message_id,)
            )
            conn.commit()
        return cursor.rowcount > 0

    def get_stats(self) -> dict[str, Any]:
        now = time.time()
        conn = self._get_conn()

        pending = conn.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE status = 'pending' AND visible_at <= ? AND (created_at + ttl_seconds) > ?",
            (now, now),
        ).fetchone()["cnt"]

        processing = conn.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE status = 'processing'"
        ).fetchone()["cnt"]

        dead_letters = conn.execute(
            "SELECT COUNT(*) as cnt FROM dead_letters"
        ).fetchone()["cnt"]

        expired = conn.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE status = 'pending' AND (created_at + ttl_seconds) <= ?",
            (now,),
        ).fetchone()["cnt"]

        return {
            "pending": pending,
            "processing": processing,
            "dead_letters": dead_letters,
            "expired": expired,
            "total_messages": pending + processing,
        }

    def vacuum(self) -> None:
        conn = self._get_conn()
        conn.execute("VACUUM")
        self._log_event("vacuum", {})

    def close(self) -> None:
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def _move_to_dead_letter(self, msg: Message, now: float) -> None:
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO dead_letters (
                id, body, priority, consumer_id, original_status,
                retries, max_retries, ttl_seconds, created_at, moved_at, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                msg.id,
                msg.body,
                msg.priority,
                msg.consumer_id,
                msg.status,
                msg.retries,
                msg.max_retries,
                msg.ttl_seconds,
                msg.created_at,
                now,
                msg.error,
            ),
        )
        self._log_event("dead_letter", {"message_id": msg.id, "retries": msg.retries})

    def _row_to_dead_letter_msg(self, row: sqlite3.Row) -> Message:
        return Message(
            id=row["id"],
            body=row["body"],
            priority=MessagePriority(row["priority"]),
            consumer_id=row["consumer_id"],
            status="dead_letter",
            retries=row["retries"],
            max_retries=row["max_retries"],
            ttl_seconds=row["ttl_seconds"],
            created_at=row["created_at"],
            visible_at=0.0,
            updated_at=row["moved_at"],
            error=row["error"] if "error" in row.keys() else "",
        )

    def _emit_metric(self, name: str, value: float) -> None:
        if get_metrics_collector is not None:
            try:
                collector = get_metrics_collector()
                if "total" in name or "depth" in name:
                    if "depth" in name:
                        collector.gauge_set(name, value)
                    else:
                        collector.counter_inc(name, value)
            except Exception:
                pass

    def _log_event(self, event: str, context: dict[str, Any]) -> None:
        try:
            log = logger or (get_logger("message_queue") if get_logger else None)
            if log:
                log.info(f"queue:{event}", extra={"context": context})
        except Exception:
            pass
