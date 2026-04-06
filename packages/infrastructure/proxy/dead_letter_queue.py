"""Dead Letter Queue — Stores failed requests for retry."""

import json
import os
import sqlite3
import threading
import time
from typing import Dict, List, Optional


class DeadLetterQueue:
    def __init__(self, db_path: str = "data/proxy/dead_letter.db", max_retries: int = 3):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.max_retries = max_retries
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""CREATE TABLE IF NOT EXISTS dead_letters (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, prompt TEXT,
            system_prompt TEXT, agent_type TEXT, error_type TEXT, error_message TEXT,
            retry_count INTEGER DEFAULT 0, max_retries INTEGER, status TEXT DEFAULT 'pending')""")
        conn.commit()
        conn.close()

    def add(self, prompt: str, system_prompt: str, agent_type: str,
            error_type: str, error_message: str) -> int:
        """Add a failed request to the dead letter queue."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "INSERT INTO dead_letters (timestamp, prompt, system_prompt, agent_type, error_type, error_message, max_retries) VALUES (?,?,?,?,?,?,?)",
                (time.time(), prompt, system_prompt, agent_type, error_type, error_message, self.max_retries))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_pending(self, limit: int = 10) -> List[dict]:
        """Get pending items for retry."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT id, prompt, system_prompt, agent_type, error_type, error_message, retry_count FROM dead_letters WHERE status='pending' AND retry_count < max_retries ORDER BY timestamp ASC LIMIT ?",
                (limit,))
            return [{"id": r[0], "prompt": r[1], "system_prompt": r[2], "agent_type": r[3],
                     "error_type": r[4], "error_message": r[5], "retry_count": r[6]} for r in cursor.fetchall()]
        finally:
            conn.close()

    def mark_retrying(self, item_id: int) -> None:
        """Mark an item as being retried."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("UPDATE dead_letters SET status='retrying', retry_count=retry_count+1 WHERE id=?", (item_id,))
            conn.commit()
        finally:
            conn.close()

    def mark_completed(self, item_id: int, success: bool) -> None:
        """Mark an item as completed (success or failed)."""
        conn = sqlite3.connect(self.db_path)
        try:
            status = "completed" if success else "failed"
            conn.execute("UPDATE dead_letters SET status=? WHERE id=?", (status, item_id))
            conn.commit()
        finally:
            conn.close()

    def get_stats(self) -> dict:
        """Get queue statistics."""
        conn = sqlite3.connect(self.db_path)
        try:
            pending = conn.execute("SELECT COUNT(*) FROM dead_letters WHERE status='pending'").fetchone()[0]
            retrying = conn.execute("SELECT COUNT(*) FROM dead_letters WHERE status='retrying'").fetchone()[0]
            completed = conn.execute("SELECT COUNT(*) FROM dead_letters WHERE status='completed'").fetchone()[0]
            failed = conn.execute("SELECT COUNT(*) FROM dead_letters WHERE status='failed'").fetchone()[0]
            return {"pending": pending, "retrying": retrying, "completed": completed, "failed": failed}
        finally:
            conn.close()


# Global instance
dead_letter_queue = DeadLetterQueue()
