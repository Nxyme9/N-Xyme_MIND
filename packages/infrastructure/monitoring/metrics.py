"""
Metrics Store — SQLite backend for nervous system metrics, actions, and alerts.

Usage:
    store = MetricsStore()
    store.record_metric("sisyphus", "tokens_used", 1500)
    store.record_action("trigger_001", "execute", True, "Success")
    store.publish_alert("sisyphus", "healer", "health_warning", '{"threshold": 0.8}')
    alerts = store.read_alerts("healer")
    store.mark_read(alerts[0]["id"])
    metrics = store.query_metrics(source="sisyphus", hours=24)
    store.prune_old(days=7)
    stats = store.get_stats()
"""

import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MetricsStore:
    """SQLite-backed metrics, actions, and alerts store for the nervous system."""

    def __init__(self, db_path: str = "data/nervous_system.db"):
        """
        Initialize the metrics store.

        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = db_path
        self._ensure_data_dir()
        self._init_db()
        logger.info(f"MetricsStore: Initialized at {db_path}")

    def _ensure_data_dir(self) -> None:
        """Create data directory if it doesn't exist."""
        data_dir = Path(self.db_path).parent
        data_dir.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with PRAGMAs and row factory."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-20000")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA temp_store=MEMORY")
        return conn

    def _init_db(self) -> None:
        """Create tables and indexes if they don't exist."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    value REAL NOT NULL,
                    session_id TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    trigger_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    message TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS agent_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    from_agent TEXT NOT NULL,
                    to_agent TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    payload TEXT DEFAULT '',
                    read INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS metrics_hourly (
                    series_id TEXT NOT NULL,
                    hour_ts INTEGER NOT NULL,
                    avg_value REAL,
                    min_value REAL,
                    max_value REAL,
                    count INTEGER,
                    PRIMARY KEY (series_id, hour_ts)
                );

                CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metrics(timestamp);
                CREATE INDEX IF NOT EXISTS idx_actions_ts ON actions(timestamp);
                CREATE INDEX IF NOT EXISTS idx_alerts_agent ON agent_alerts(to_agent, read);
            """)
            conn.commit()

    def record_metric(self, source: str, metric: str, value: float, session_id: str = "") -> int:
        """
        Record a metric value.

        Args:
            source: Source of the metric (e.g., agent name).
            metric: Metric name (e.g., 'tokens_used', 'latency').
            value: Numeric value of the metric.
            session_id: Optional session identifier.

        Returns:
            ID of the inserted record.
        """
        timestamp = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO metrics (timestamp, source, metric, value, session_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (timestamp, source, metric, value, session_id),
            )
            conn.commit()
            return cursor.lastrowid or 0

    def record_action(self, trigger_id: str, action: str, success: bool, message: str = "") -> int:
        """
        Record an action execution.

        Args:
            trigger_id: ID of the trigger that caused the action.
            action: Action name or type.
            success: Whether the action succeeded.
            message: Optional message/details about the action.

        Returns:
            ID of the inserted record.
        """
        timestamp = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO actions (timestamp, trigger_id, action, success, message)
                   VALUES (?, ?, ?, ?, ?)""",
                (timestamp, trigger_id, action, 1 if success else 0, message),
            )
            conn.commit()
            return cursor.lastrowid or 0

    def publish_alert(
        self, from_agent: str, to_agent: str, alert_type: str, payload: str = ""
    ) -> int:
        """
        Publish an alert from one agent to another.

        Args:
            from_agent: Source agent sending the alert.
            to_agent: Target agent receiving the alert.
            alert_type: Type of alert (e.g., 'health_warning', 'task_complete').
            payload: Optional JSON payload as string.

        Returns:
            ID of the inserted record.
        """
        timestamp = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO agent_alerts (timestamp, from_agent, to_agent, alert_type, payload)
                   VALUES (?, ?, ?, ?, ?)""",
                (timestamp, from_agent, to_agent, alert_type, payload),
            )
            conn.commit()
            return cursor.lastrowid or 0

    def read_alerts(self, agent_name: str) -> List[Dict[str, Any]]:
        """
        Read unread alerts for a specific agent.

        Args:
            agent_name: Name of the agent to read alerts for.

        Returns:
            List of alert records as dictionaries.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT id, timestamp, from_agent, to_agent, alert_type, payload, read
                   FROM agent_alerts
                   WHERE to_agent = ? AND read = 0
                   ORDER BY timestamp DESC""",
                (agent_name,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def mark_read(self, alert_id: int) -> None:
        """
        Mark an alert as read.

        Args:
            alert_id: ID of the alert to mark as read.
        """
        with self._get_connection() as conn:
            conn.execute("UPDATE agent_alerts SET read = 1 WHERE id = ?", (alert_id,))
            conn.commit()

    def query_metrics(
        self, source: Optional[str] = None, metric: Optional[str] = None, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Query metrics with optional filters.

        Args:
            source: Filter by source (optional).
            metric: Filter by metric name (optional).
            hours: Number of hours to look back (default 24).

        Returns:
            List of metric records as dictionaries.
        """
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        query = "SELECT id, timestamp, source, metric, value, session_id FROM metrics WHERE timestamp >= ?"
        params: List[Any] = [cutoff]

        if source:
            query += " AND source = ?"
            params.append(source)

        if metric:
            query += " AND metric = ?"
            params.append(metric)

        query += " ORDER BY timestamp DESC"

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]


    def downsample(self, older_than_hours=24):
        """Roll up raw metrics into hourly aggregates."""
        cutoff_ts = int(time.time()) - (older_than_hours * 3600)
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO metrics_hourly (series_id, hour_ts, avg_value, min_value, max_value, count) SELECT source || '.' || metric, (CAST(strftime('%s', timestamp) AS INTEGER) / 3600) * 3600, AVG(value), MIN(value), MAX(value), COUNT(*) FROM metrics WHERE CAST(strftime('%s', timestamp) AS INTEGER) < ? GROUP BY source, metric, (CAST(strftime('%s', timestamp) AS INTEGER) / 3600)",
                (cutoff_ts,)
            )
            conn.commit()


    def get_baseline(self, source, metric, hours=168):
        """Get adaptive baseline (mean + 2*stddev) from historical data."""
        with self._get_connection() as conn:
            sql = "SELECT AVG(value), COUNT(*), CASE WHEN COUNT(*) > 1 THEN SQRT(AVG(value*value) - AVG(value)*AVG(value)) ELSE 0 END FROM metrics WHERE source = ? AND metric = ? AND timestamp > datetime('now', ?)"
            rows = conn.execute(sql, (source, metric, f'-{hours} hours')).fetchone()
        if rows and rows[1] >= 5:
            mean, cnt, stddev = rows
            return {"mean": mean, "stddev": stddev, "upper": mean + 2 * (stddev or 0), "lower": mean - 2 * (stddev or 0), "count": cnt}
        return None

    def is_anomaly(self, source, metric, value, hours=168):
        """Check if value is anomalous (outside mean +/- 2*stddev)."""
        baseline = self.get_baseline(source, metric, hours)
        if not baseline:
            return False
        return value > baseline["upper"] or value < baseline["lower"]


    def is_anomaly(self, source, metric, value, hours=168):
        """Check if value is anomalous (outside mean +/- 2*stddev)."""
        baseline = self.get_baseline(source, metric, hours)
        if not baseline:
            return False
        return value > baseline["upper"] or value < baseline["lower"]


    def record_task_start(self, task_id, task_name, plan_name='', estimated_minutes=0, category='general'):
        """Record task start time."""
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO task_velocity (task_id, task_name, plan_name, estimated_minutes, status, started_at, category) VALUES (?, ?, ?, ?, 'in_progress', datetime('now'), ?)",
                (task_id, task_name, plan_name, estimated_minutes, category)
            )
            conn.commit()

    def record_task_complete(self, task_id):
        """Record task completion and calculate actual time."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE task_velocity SET status='completed', completed_at=datetime('now'), actual_minutes=ROUND((julianday(datetime('now')) - julianday(started_at)) * 1440.0, 1) WHERE task_id=? AND status='in_progress'",
                (task_id,)
            )
            conn.commit()

    def get_velocity(self, days=7):
        """Get velocity metrics for the last N days."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT 
                    COUNT(*) as tasks,
                    AVG(actual_minutes) as avg_minutes,
                    60.0 / AVG(actual_minutes) as tasks_per_hour,
                    AVG(estimated_minutes * 1.0 / NULLIF(actual_minutes, 0)) as estimate_ratio,
                    SUM(actual_minutes) as total_minutes
                FROM task_velocity 
                WHERE status='completed' AND completed_at > datetime('now', ?)
            """, (f'-{days} days',)).fetchone()
            if rows and rows[0]:
                return {
                    'tasks': rows[0],
                    'avg_minutes': round(rows[1], 1),
                    'tasks_per_hour': round(rows[2], 1),
                    'estimate_ratio': round(rows[3], 1) if rows[3] else 1.0,
                    'total_hours': round(rows[4] / 60, 1) if rows[4] else 0
                }
            return None

    def get_velocity_by_category(self, days=7):
        """Get velocity broken down by category."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT category, COUNT(*), AVG(actual_minutes), 60.0/AVG(actual_minutes)
                FROM task_velocity 
                WHERE status='completed' AND completed_at > datetime('now', ?)
                GROUP BY category ORDER BY COUNT(*) DESC
            """, (f'-{days} days',)).fetchall()
            return [{'category': r[0], 'tasks': r[1], 'avg_minutes': round(r[2],1), 'per_hour': round(r[3],1)} for r in rows]

    def estimate_task(self, category='general'):
        """Estimate task time based on historical velocity."""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT AVG(actual_minutes) FROM task_velocity 
                WHERE status='completed' AND category=? AND actual_minutes > 0
            """, (category,)).fetchone()
            if row and row[0]:
                return round(row[0], 0)
            # Fallback to overall average
            row = conn.execute("SELECT AVG(actual_minutes) FROM task_velocity WHERE status='completed' AND actual_minutes > 0").fetchone()
            return round(row[0], 15) if row and row[0] else 15

    def store_velocity_snapshot(self):
        """Store velocity snapshot in Graphiti for cross-session memory."""
        import requests
        v = self.get_velocity(30)
        if not v:
            return
        text = f"Velocity snapshot: {v['tasks']} tasks in {v['total_hours']}h. Avg {v['avg_minutes']}min/task ({v['tasks_per_hour']}/hour). Estimates are {v['estimate_ratio']}x too high."
        try:
            requests.post('http://localhost:8001/json-rpc', json={
                'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                'params': {'name': 'graphiti_add_episode', 'arguments': {'text': text, 'name': f'velocity-{datetime.now().strftime("%Y-%m-%d")}', 'source': 'velocity-tracker'}}
            }, timeout=10)
        except Exception: pass

    def prune_old(self, days: int = 7) -> Dict[str, int]:
        """
        Delete records older than N days from all tables.

        Args:
            days: Number of days to keep (default 7).

        Returns:
            Dictionary with counts of deleted records per table.
        """
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        deleted = {}

        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff,))
            deleted["metrics"] = cursor.rowcount

            cursor = conn.execute("DELETE FROM actions WHERE timestamp < ?", (cutoff,))
            deleted["actions"] = cursor.rowcount

            cursor = conn.execute("DELETE FROM agent_alerts WHERE timestamp < ?", (cutoff,))
            deleted["agent_alerts"] = cursor.rowcount

            conn.commit()

        logger.info(f"MetricsStore: Pruned {deleted}")
        return deleted

    def get_stats(self) -> Dict[str, int]:
        """
        Get record counts for all tables.

        Returns:
            Dictionary with record counts per table.
        """
        with self._get_connection() as conn:
            stats = {}

            cursor = conn.execute("SELECT COUNT(*) as count FROM metrics")
            stats["metrics"] = cursor.fetchone()["count"]

            cursor = conn.execute("SELECT COUNT(*) as count FROM actions")
            stats["actions"] = cursor.fetchone()["count"]

            cursor = conn.execute("SELECT COUNT(*) as count FROM agent_alerts")
            stats["agent_alerts"] = cursor.fetchone()["count"]

            return stats


# Module-level convenience instance
_default_store: Optional[MetricsStore] = None


def get_store(db_path: str = "data/nervous_system.db") -> MetricsStore:
    """Get or create the default metrics store instance."""
    global _default_store
    if _default_store is None:
        _default_store = MetricsStore(db_path)
    return _default_store
