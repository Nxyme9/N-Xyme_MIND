#!/usr/bin/env python3
"""OutcomeLogger — Records delegation outcomes for learning system."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class DelegationOutcome:
    task_id: str
    task_description: str
    task_type: str  # "implementation", "research", "review", "fix"
    agent: str
    level: int  # L1-L5
    success: bool
    latency_ms: float
    tokens_used: int = 0
    quality_score: Optional[float] = None  # 0-1, from user feedback
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class OutcomeLogger:
    """Records and retrieves delegation outcomes for learning."""

    def __init__(self, db_path: str = ".sisyphus/outcomes.db"):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                task_description TEXT,
                task_type TEXT NOT NULL,
                agent TEXT NOT NULL,
                level INTEGER NOT NULL,
                success INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                quality_score REAL,
                context_json TEXT DEFAULT '{}',
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_agent ON outcomes(agent)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_outcomes_task_type ON outcomes(task_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_outcomes_success ON outcomes(success)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_outcomes_timestamp ON outcomes(timestamp)"
        )
        conn.commit()
        conn.close()

    def log(self, outcome: DelegationOutcome) -> int:
        """Log a delegation outcome. Returns the outcome ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """INSERT INTO outcomes 
               (task_id, task_description, task_type, agent, level, success, latency_ms, tokens_used, quality_score, context_json, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                outcome.task_id,
                outcome.task_description,
                outcome.task_type,
                outcome.agent,
                outcome.level,
                1 if outcome.success else 0,
                outcome.latency_ms,
                outcome.tokens_used,
                outcome.quality_score,
                json.dumps(outcome.context),
                outcome.timestamp,
            ),
        )
        conn.commit()
        outcome_id = cursor.lastrowid
        conn.close()
        return outcome_id if outcome_id is not None else 0

    def get_outcomes(
        self,
        agent: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[DelegationOutcome]:
        """Retrieve outcomes with optional filters."""
        conn = sqlite3.connect(self.db_path)
        query = "SELECT * FROM outcomes WHERE 1=1"
        params = []

        if agent:
            query += " AND agent = ?"
            params.append(agent)
        if task_type:
            query += " AND task_type = ?"
            params.append(task_type)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()

        return [
            DelegationOutcome(
                task_id=row[1],
                task_description=row[2],
                task_type=row[3],
                agent=row[4],
                level=row[5],
                success=bool(row[6]),
                latency_ms=row[7],
                tokens_used=row[8],
                quality_score=row[9],
                context=json.loads(row[10]),
                timestamp=row[11],
            )
            for row in rows
        ]

    def get_agent_stats(self, agent: str) -> dict[str, Any]:
        """Get performance stats for a specific agent."""
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            """SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                AVG(latency_ms) as avg_latency,
                AVG(tokens_used) as avg_tokens,
                AVG(quality_score) as avg_quality
               FROM outcomes WHERE agent = ?""",
            (agent,),
        ).fetchone()
        conn.close()

        if not row or row[0] == 0:
            return {"total": 0}

        return {
            "total": row[0],
            "successes": row[1],
            "success_rate": row[1] / row[0] if row[0] > 0 else 0,
            "avg_latency_ms": round(row[2], 2),
            "avg_tokens": round(row[3], 0) if row[3] else 0,
            "avg_quality": round(row[4], 2) if row[4] else None,
        }

    def get_all_agent_stats(self) -> dict[str, dict[str, Any]]:
        """Get stats for all agents."""
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            """SELECT agent,
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                    AVG(latency_ms) as avg_latency
               FROM outcomes GROUP BY agent"""
        ).fetchall()
        conn.close()

        return {
            row[0]: {
                "total": row[1],
                "success_rate": row[2] / row[1] if row[1] > 0 else 0,
                "avg_latency_ms": round(row[3], 2),
            }
            for row in rows
        }
