"""
Memory Integration for Model Router.

Records routing outcomes and learns from historical data to improve future routing decisions.
Integrates with the unified-memory system for persistent storage and retrieval.
"""

import logging
import time
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Memory database path
MEMORY_DB_PATH = "context/memory/mind_from_mind.db"


class RoutingMemory:
    """Stores and retrieves routing outcomes for learning."""

    def __init__(self, db_path: str = MEMORY_DB_PATH):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        """Ensure memory database exists."""
        try:
            import sqlite3
            from pathlib import Path

            db = Path(self.db_path)
            db.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(db))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS routing_outcomes (
                    id TEXT PRIMARY KEY,
                    timestamp REAL,
                    task_type TEXT,
                    model_used TEXT,
                    provider TEXT,
                    success BOOLEAN,
                    latency_ms REAL,
                    error_message TEXT,
                    user_feedback TEXT
                )
            """)
            conn.commit()
            conn.close()
            logger.info(f"Routing memory database initialized at {self.db_path}")
        except Exception as e:
            logger.warning(f"Failed to initialize routing memory: {e}")

    def record_outcome(
        self,
        task_type: str,
        model_used: str,
        provider: str,
        success: bool,
        latency_ms: float,
        error_message: str = None,
        user_feedback: str = None,
    ) -> str:
        """Record a routing outcome."""
        try:
            import sqlite3

            outcome_id = str(uuid.uuid4())
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "INSERT INTO routing_outcomes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    outcome_id,
                    time.time(),
                    task_type,
                    model_used,
                    provider,
                    success,
                    latency_ms,
                    error_message,
                    user_feedback,
                ),
            )
            conn.commit()
            conn.close()
            logger.info(f"Recorded routing outcome: {outcome_id}")
            return outcome_id
        except Exception as e:
            logger.error(f"Failed to record routing outcome: {e}")
            return None

    def get_best_model(self, task_type: str, limit: int = 5) -> list:
        """Get best performing models for a task type."""
        try:
            import sqlite3

            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                """
                SELECT model_used, provider, 
                       AVG(CASE WHEN success THEN 1 ELSE 0 END) as success_rate,
                       AVG(latency_ms) as avg_latency,
                       COUNT(*) as usage_count
                FROM routing_outcomes 
                WHERE task_type = ?
                GROUP BY model_used, provider
                ORDER BY success_rate DESC, avg_latency ASC
                LIMIT ?
            """,
                (task_type, limit),
            )
            results = cursor.fetchall()
            conn.close()
            return [
                {
                    "model": row[0],
                    "provider": row[1],
                    "success_rate": row[2],
                    "avg_latency": row[3],
                    "usage_count": row[4],
                }
                for row in results
            ]
        except Exception as e:
            logger.error(f"Failed to get best model: {e}")
            return []

    def get_routing_stats(self) -> dict:
        """Get overall routing statistics."""
        try:
            import sqlite3

            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_requests,
                    AVG(CASE WHEN success THEN 1 ELSE 0 END) as overall_success_rate,
                    AVG(latency_ms) as avg_latency,
                    COUNT(DISTINCT model_used) as unique_models,
                    COUNT(DISTINCT provider) as unique_providers
                FROM routing_outcomes
            """)
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    "total_requests": row[0],
                    "overall_success_rate": row[1],
                    "avg_latency": row[2],
                    "unique_models": row[3],
                    "unique_providers": row[4],
                }
            return {}
        except Exception as e:
            logger.error(f"Failed to get routing stats: {e}")
            return {}


# Global instance
routing_memory = RoutingMemory()
