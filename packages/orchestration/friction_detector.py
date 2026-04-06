"""FrictionDetector — measures operation duration and flags slow operations."""

import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class FrictionDetector:
    """SQLite-backed friction detector for measuring operation latency."""

    def __init__(self, db_path: str = "data/nervous_system.db"):
        self.db_path = db_path
        self.timers: Dict[str, Dict] = {}
        self._ensure_data_dir()
        self._init_table()

    def _ensure_data_dir(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_table(self) -> None:
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS friction_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    flagged INTEGER DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_friction_op ON friction_log(operation);
            """)
            conn.commit()

    def start_timer(self, operation: str) -> str:
        """Start timing an operation. Returns timer_id."""
        timer_id = f"{operation}-{time.time()}"
        self.timers[timer_id] = {"operation": operation, "start": time.time()}
        return timer_id

    def stop_timer(self, timer_id: str) -> float:
        """Stop timing and return duration in ms. Flags if >2000ms."""
        timer = self.timers.pop(timer_id)
        duration_ms = (time.time() - timer["start"]) * 1000
        flagged = 1 if duration_ms > 2000 else 0

        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO friction_log (operation, duration_ms, timestamp, flagged) VALUES (?, ?, ?, ?)",
                (timer["operation"], duration_ms, datetime.utcnow().isoformat(), flagged),
            )
            conn.commit()
        return duration_ms

    def get_report(self, hours: int = 24) -> Dict:
        """Return friction summary with averages and suggestions."""
        with self._get_connection() as conn:
            cutoff = datetime.utcnow().isoformat()
            conn.execute(
                "DELETE FROM friction_log WHERE timestamp < datetime('now', ?)",
                (f"-{hours} hours",),
            )
            conn.commit()

            avg_rows = conn.execute("""
                SELECT operation, AVG(duration_ms) as avg_ms, COUNT(*) as cnt
                FROM friction_log GROUP BY operation ORDER BY avg_ms DESC
            """).fetchall()

            high_rows = conn.execute("""
                SELECT operation, duration_ms, timestamp FROM friction_log
                WHERE flagged = 1 ORDER BY duration_ms DESC LIMIT 10
            """).fetchall()

        highest = [{"op": r[0], "ms": r[1], "ts": r[2]} for r in high_rows]
        suggestions = [
            f"Optimize {r[0]} ({r[2]} calls, avg {r[1]:.0f}ms)" for r in avg_rows if r[1] > 500
        ][:5]

        return {
            "average_ms": {r[0]: round(r[1], 1) for r in avg_rows},
            "highest": highest,
            "suggestions": suggestions or ["No significant friction detected"],
        }
