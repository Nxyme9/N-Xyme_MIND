#!/usr/bin/env python3
"""ContributionAnalyzer — DAG-Shapley Attribution for Multi-Agent Tasks.

Phase 5.3 of Masterplan: Attribution & Learning.

Computes Shapley-value-based attribution for multi-agent tasks to determine
which agent contributed most to a task outcome. Uses Monte Carlo
sampling approximation for computational efficiency.

Usage:
    from packages.orchestration.contribution_analyzer import ContributionAnalyzer

    analyzer = ContributionAnalyzer()

    # Record agents that worked on a task
    analyzer.record_agent_task("task_001", "hephaestus")
    analyzer.record_agent_task("task_001", "oracle")
    analyzer.record_agent_task("task_001", "explore")

    # Compute DAG-Shapley attribution
    contributions = analyzer.compute_shapley("task_001", ["hephaestus", "oracle", "explore"])
    # Returns: {"hephaestus": 0.45, "oracle": 0.35, "explore": 0.20}

    # Record contribution
    analyzer.record_contribution("task_001", "hephaestus", 0.45)

Algorithm:
    - Sample random orderings of agents
    - For each agent, compute marginal contribution in each ordering
    - Marginal contribution = value(coalition ∪ {agent}) - value(coalition)
    - Average across all samples for final Shapley values
    - Normalize to sum to 1.0
"""

from __future__ import annotations

import json
import logging
import random
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Configure module logger
logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = "~/.cache/n-xyme-mind/contributions.db"


@dataclass
class ContributionRecord:
    """Record of contribution for a single agent."""

    task_id: str
    agent_id: str
    contribution: float
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    sample_count: int = 0


@dataclass
class ShapleyResult:
    """Result of Shapley value computation."""

    task_id: str
    contributions: dict[str, float]
    sample_count: int
    computed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ContributionAnalyzer:
    """Computes DAG-Shapley attribution for multi-agent tasks.

    Uses Monte Carlo sampling to approximate the Shapley value for each
    agent in a task. This is computationally efficient while providing
    mathematically grounded attribution.
    """

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        n_samples: int = 100,
        seed: Optional[int] = None,
    ):
        """Initialize ContributionAnalyzer.

        Args:
            db_path: Path to SQLite database for contribution history.
                    Defaults to ~/.cache/n-xyme-mind/contributions.db
            n_samples: Number of orderings to sample for approximation.
                      Defaults to 100.
            seed: Random seed for reproducibility. Defaults to None.
        """
        self.db_path = str(Path(db_path).expanduser())
        self.n_samples = n_samples
        self.seed = seed
        self._lock = threading.Lock()

        # In-memory cache for task data
        self._task_data: dict[str, dict[str, Any]] = defaultdict(dict)
        self._agent_tasks: dict[str, list[str]] = defaultdict(list)

        # Ensure DB directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._ensure_db()
        logger.info(
            f"ContributionAnalyzer initialized with db={self.db_path}, samples={n_samples}"
        )

    def _ensure_db(self) -> None:
        """Ensure database and tables exist."""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contributions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                contribution REAL NOT NULL,
                timestamp TEXT NOT NULL,
                sample_count INTEGER DEFAULT 0,
                UNIQUE(task_id, agent_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS task_agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                UNIQUE(task_id, agent_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_contributions_task
            ON contributions(task_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_agents_task
            ON task_agents(task_id)
        """)
        conn.commit()
        conn.close()
        logger.debug("Database tables initialized")

    def _generate_task_value(
        self,
        task_id: str,
        coalition: list[str],
    ) -> float:
        """Compute value function for a coalition of agents.

        This is a simplified value function that returns 1.0 if
        all agents in coalition participated in the task, 0.0 otherwise.

        In a full implementation, this would use actual task outcome
        data (success/failure, quality scores, etc.).

        Args:
            task_id: The task being evaluated
            coalition: List of agent IDs in coalition

        Returns:
            Value proxy (0.0 - 1.0)
        """
        if not coalition:
            return 0.0

        # Get actual agents for this task
        actual_agents = set(self._agent_tasks.get(task_id, []))
        coalition_set = set(coalition)

        # Value is fraction of coalition that actually worked on task
        # with bonus for having more agents (collaboration value)
        if not actual_agents:
            return 0.0

        # Check overlap
        overlap = len(coalition_set & actual_agents)

        # Value increases with more actual agents in coalition
        # Normalized by total actual agents
        base_value = overlap / len(actual_agents) if actual_agents else 0.0

        # Bonus for having the full team (collaboration matters)
        if coalition_set >= actual_agents:
            base_value = min(1.0, base_value * 1.1)

        return base_value

    def compute_shapley(
        self,
        task_id: str,
        agent_ids: list[str],
    ) -> dict[str, float]:
        """Compute DAG-Shapley attribution for multi-agent task.

        Uses Monte Carlo sampling to approximate Shapley values.
        For each sampled ordering, computes marginal contribution
        of each agent when added to the coalition.

        Args:
            task_id: The task to analyze
            agent_ids: List of agents that worked on the task

        Returns:
            Dict mapping agent_id -> contribution_score (0-1).
            Values sum to 1.0.
        """
        if not agent_ids:
            logger.warning(f"Empty agent list for task {task_id}")
            return {}

        if len(agent_ids) == 1:
            # Single agent gets all credit
            return {agent_ids[0]: 1.0}

        # Set seed for reproducibility
        if self.seed is not None:
            random.seed(self.seed)

        # Track cumulative contributions
        marginals: dict[str, list[float]] = defaultdict(list)

        # Sample orderings
        for _ in range(self.n_samples):
            # Random permutation of agents
            ordering = agent_ids.copy()
            random.shuffle(ordering)

            # Compute marginal contributions
            coalition: list[str] = []
            for agent in ordering:
                # Value before adding agent
                value_before = self._generate_task_value(task_id, coalition)

                # Value after adding agent
                coalition.append(agent)
                value_after = self._generate_task_value(task_id, coalition)

                # Marginal contribution
                marginal = value_after - value_before
                marginals[agent].append(marginal)

        # Average marginal contributions
        raw_scores = {}
        for agent, values in marginals.items():
            raw_scores[agent] = sum(values) / len(values) if values else 0.0

        # Normalize to sum to 1.0
        total = sum(raw_scores.values())
        if total > 0:
            normalized = {a: v / total for a, v in raw_scores.items()}
        else:
            # Equal split if all zeros
            normalized = {a: 1.0 / len(agent_ids) for a in agent_ids}

        logger.info(
            f"Computed Shapley for task {task_id}: "
            f"{len(agent_ids)} agents, {self.n_samples} samples"
        )

        return normalized

    def record_agent_task(self, task_id: str, agent_id: str) -> None:
        """Record that an agent worked on a task.

        Args:
            task_id: The task ID
            agent_id: The agent ID
        """
        import sqlite3

        with self._lock:
            # Update in-memory cache
            if agent_id not in self._agent_tasks[task_id]:
                self._agent_tasks[task_id].append(agent_id)

                # Persist to DB
                conn = sqlite3.connect(self.db_path)
                conn.execute(
                    """INSERT OR IGNORE INTO task_agents
                       (task_id, agent_id, timestamp)
                       VALUES (?, ?, ?)""",
                    (
                        task_id,
                        agent_id,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()
                conn.close()
                logger.debug(f"Recorded agent {agent_id} for task {task_id}")

    def record_contribution(
        self,
        task_id: str,
        agent_id: str,
        contribution: float,
    ) -> None:
        """Record a contribution for future analysis.

        Args:
            task_id: The task ID
            agent_id: The agent ID
            contribution: Contribution score (0-1)
        """
        import sqlite3

        with self._lock:
            # Persist to DB
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """INSERT OR REPLACE INTO contributions
                   (task_id, agent_id, contribution, timestamp, sample_count)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    task_id,
                    agent_id,
                    contribution,
                    datetime.now(timezone.utc).isoformat(),
                    self.n_samples,
                ),
            )
            conn.commit()
            conn.close()
            logger.info(
                f"Recorded contribution: {agent_id}={contribution:.3f} for task {task_id}"
            )

    def get_contribution_history(
        self,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[ContributionRecord]:
        """Get contribution history from database.

        Args:
            task_id: Filter by task ID (optional)
            agent_id: Filter by agent ID (optional)
            limit: Maximum records to return

        Returns:
            List of ContributionRecord
        """
        import sqlite3

        conn = sqlite3.connect(self.db_path)

        query = "SELECT task_id, agent_id, contribution, timestamp FROM contributions"
        params = []

        if task_id and agent_id:
            query += " WHERE task_id = ? AND agent_id = ?"
            params = [task_id, agent_id]
        elif task_id:
            query += " WHERE task_id = ?"
            params = [task_id]
        elif agent_id:
            query += " WHERE agent_id = ?"
            params = [agent_id]

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        records = [
            ContributionRecord(
                task_id=row[0],
                agent_id=row[1],
                contribution=row[2],
                timestamp=row[3],
            )
            for row in cursor.fetchall()
        ]
        conn.close()

        return records

    def get_agent_stats(self, agent_id: str) -> dict[str, Any]:
        """Get aggregate statistics for an agent.

        Args:
            agent_id: The agent ID

        Returns:
            Dict with aggregate stats
        """
        import sqlite3

        conn = sqlite3.connect(self.db_path)

        # Average contribution
        row = conn.execute(
            """SELECT AVG(contribution), COUNT(*), MAX(timestamp)
               FROM contributions WHERE agent_id = ?""",
            (agent_id,),
        ).fetchone()

        avg_contrib = row[0] if row and row[0] is not None else 0.0
        task_count = row[1] if row and row[1] else 0
        last_contrib = row[2] if row and row[2] else None

        # Tasks completed
        tasks_row = conn.execute(
            "SELECT COUNT(DISTINCT task_id) FROM task_agents WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
        tasks_completed = tasks_row[0] if tasks_row and tasks_row[0] else 0

        conn.close()

        return {
            "agent_id": agent_id,
            "avg_contribution": avg_contrib,
            "contribution_count": task_count,
            "tasks_completed": tasks_completed,
            "last_contribution": last_contrib,
        }

    def export_json(self, path: Optional[str] = None) -> str:
        """Export all contributions to JSON.

        Args:
            path: Path to write to. If None, returns JSON string.

        Returns:
            JSON string if path is None, otherwise empty string
        """
        import sqlite3

        conn = sqlite3.connect(self.db_path)

        cursor = conn.execute(
            """SELECT c.task_id, c.agent_id, c.contribution, c.timestamp,
                      GROUP_CONCAT(a.agent_id) as agents
               FROM contributions c
               LEFT JOIN task_agents a ON c.task_id = a.task_id
               GROUP BY c.task_id, c.agent_id
               ORDER BY c.timestamp DESC"""
        )

        data = []
        for row in cursor.fetchall():
            data.append(
                {
                    "task_id": row[0],
                    "agent_id": row[1],
                    "contribution": row[2],
                    "timestamp": row[3],
                    "task_agents": row[4].split(",") if row[4] else [],
                }
            )

        conn.close()

        json_str = json.dumps(data, indent=2)

        if path:
            Path(path).write_text(json_str)
            logger.info(f"Exported contributions to {path}")
            return ""

        return json_str


def get_analyzer(
    db_path: str = DEFAULT_DB_PATH,
    n_samples: int = 100,
) -> ContributionAnalyzer:
    """Get a ContributionAnalyzer instance.

    Convenience function for quick access.

    Args:
        db_path: Database path
        n_samples: Number of samples

    Returns:
        ContributionAnalyzer instance
    """
    return ContributionAnalyzer(db_path=db_path, n_samples=n_samples)
