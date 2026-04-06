"""SQLite database manager with WAL mode and thread-safe operations."""

from __future__ import annotations

import json
import sqlite3
import threading
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

try:
    from src.observability.metrics import get_metrics_collector
except ImportError:
    get_metrics_collector = None

from .models import Session, Delegation, AgentPerformance, Result

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent.parent.parent / ".sisyphus" / "state.db"


class StateDB:
    """SQLite database manager with WAL mode, proper locking, and migration support."""

    def __init__(self, db_path: Path | None = None):
        self._db_path = db_path or DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._lock = threading.Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(str(self._db_path), timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return self._local.conn

    def _init_db(self):
        """Create tables if they don't exist."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                last_agent TEXT NOT NULL DEFAULT '',
                last_action TEXT NOT NULL DEFAULT '',
                session_started TEXT NOT NULL DEFAULT '',
                last_updated TEXT NOT NULL DEFAULT '',
                current_task TEXT NOT NULL DEFAULT '',
                pending_changes TEXT NOT NULL DEFAULT '[]',
                completed_changes TEXT NOT NULL DEFAULT '[]',
                context TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS delegations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                agent TEXT NOT NULL,
                level TEXT NOT NULL,
                status TEXT NOT NULL,
                tokens INTEGER NOT NULL DEFAULT 0,
                timestamp TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_delegations_task_id ON delegations(task_id);
            CREATE INDEX IF NOT EXISTS idx_delegations_timestamp ON delegations(timestamp);

            CREATE TABLE IF NOT EXISTS agent_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                task_type TEXT NOT NULL,
                success INTEGER NOT NULL DEFAULT 0,
                failure INTEGER NOT NULL DEFAULT 0,
                last_failure_reason TEXT NOT NULL DEFAULT '',
                last_updated TEXT NOT NULL DEFAULT '',
                UNIQUE(agent_name, task_type)
            );

            CREATE TABLE IF NOT EXISTS results (
                task_id TEXT PRIMARY KEY,
                task_description TEXT NOT NULL,
                agent TEXT NOT NULL,
                level TEXT NOT NULL,
                success INTEGER NOT NULL DEFAULT 0,
                result_path TEXT NOT NULL DEFAULT '',
                timestamp TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_results_timestamp ON results(timestamp);
            CREATE INDEX IF NOT EXISTS idx_results_description ON results(task_description);
        """)
        conn.commit()

    # ── Session Operations ──────────────────────────────────────────

    def upsert_session(self, session: Session) -> None:
        """Insert or update a session."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO sessions (
                session_id, last_agent, last_action, session_started,
                last_updated, current_task, pending_changes,
                completed_changes, context
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                last_agent=excluded.last_agent,
                last_action=excluded.last_action,
                session_started=excluded.session_started,
                last_updated=excluded.last_updated,
                current_task=excluded.current_task,
                pending_changes=excluded.pending_changes,
                completed_changes=excluded.completed_changes,
                context=excluded.context
            """,
            (
                session.session_id,
                session.last_agent,
                session.last_action,
                session.session_started,
                session.last_updated,
                session.current_task,
                json.dumps(session.pending_changes),
                json.dumps(session.completed_changes),
                json.dumps(session.context),
            ),
        )
        conn.commit()

    def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return None
        return Session(
            session_id=row["session_id"],
            last_agent=row["last_agent"],
            last_action=row["last_action"],
            session_started=row["session_started"],
            last_updated=row["last_updated"],
            current_task=row["current_task"],
            pending_changes=json.loads(row["pending_changes"]),
            completed_changes=json.loads(row["completed_changes"]),
            context=json.loads(row["context"]),
        )

    def get_active_session(self) -> Session | None:
        """Get the most recently updated session."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM sessions ORDER BY last_updated DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return Session(
            session_id=row["session_id"],
            last_agent=row["last_agent"],
            last_action=row["last_action"],
            session_started=row["session_started"],
            last_updated=row["last_updated"],
            current_task=row["current_task"],
            pending_changes=json.loads(row["pending_changes"]),
            completed_changes=json.loads(row["completed_changes"]),
            context=json.loads(row["context"]),
        )

    # ── Delegation Operations ───────────────────────────────────────

    def add_delegation(self, delegation: Delegation) -> None:
        """Add a delegation log entry."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO delegations (task_id, agent, level, status, tokens, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                delegation.task_id,
                delegation.agent,
                delegation.level,
                delegation.status,
                delegation.tokens,
                delegation.timestamp,
            ),
        )
        conn.commit()
        logger.info(
            "Delegation recorded",
            extra={"context": {"task_id": delegation.task_id, "agent": delegation.agent, "level": delegation.level, "status": delegation.status, "tokens": delegation.tokens}},
        )
        if get_metrics_collector is not None:
            metrics = get_metrics_collector()
            success = delegation.status == "success"
            metrics.record_delegation(
                agent=delegation.agent,
                level=delegation.level,
                success=success,
                tokens=delegation.tokens,
            )

    def get_delegations(self, limit: int = 50) -> list[Delegation]:
        """Get recent delegations."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM delegations ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [
            Delegation(
                task_id=row["task_id"],
                agent=row["agent"],
                level=row["level"],
                status=row["status"],
                tokens=row["tokens"],
                timestamp=row["timestamp"],
            )
            for row in rows
        ]

    def get_delegation_stats(self) -> dict[str, Any]:
        """Get delegation statistics."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) as cnt FROM delegations").fetchone()[
            "cnt"
        ]
        success = conn.execute(
            "SELECT COUNT(*) as cnt FROM delegations WHERE status = 'success'"
        ).fetchone()["cnt"]
        rate = (success * 100 // total) if total > 0 else 0
        return {
            "total": total,
            "success": success,
            "failures": total - success,
            "success_rate": rate,
        }

    # ── Agent Performance Operations ────────────────────────────────

    def upsert_agent_performance(self, perf: AgentPerformance) -> None:
        """Insert or update agent performance."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO agent_performance (
                agent_name, task_type, success, failure,
                last_failure_reason, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_name, task_type) DO UPDATE SET
                success=excluded.success,
                failure=excluded.failure,
                last_failure_reason=excluded.last_failure_reason,
                last_updated=excluded.last_updated
            """,
            (
                perf.agent_name,
                perf.task_type,
                perf.success,
                perf.failure,
                perf.last_failure_reason,
                perf.last_updated,
            ),
        )
        conn.commit()

    def get_agent_performance(self, agent_name: str) -> list[AgentPerformance]:
        """Get all performance entries for an agent."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM agent_performance WHERE agent_name = ?", (agent_name,)
        ).fetchall()
        return [
            AgentPerformance(
                agent_name=row["agent_name"],
                task_type=row["task_type"],
                success=row["success"],
                failure=row["failure"],
                last_failure_reason=row["last_failure_reason"],
                last_updated=row["last_updated"],
            )
            for row in rows
        ]

    def get_all_agent_performance(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Get all agent performance data in the original nested format."""
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM agent_performance").fetchall()
        result: dict[str, dict[str, dict[str, Any]]] = {}
        for row in rows:
            agent = row["agent_name"]
            task_type = row["task_type"]
            if agent not in result:
                result[agent] = {}
            result[agent][task_type] = {
                "success": row["success"],
                "failure": row["failure"],
                "last_failure_reason": row["last_failure_reason"],
            }
        return result

    # ── Result Operations ───────────────────────────────────────────

    def upsert_result(self, result: Result) -> None:
        """Insert or update a cached result."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO results (
                task_id, task_description, agent, level, success,
                result_path, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                task_description=excluded.task_description,
                agent=excluded.agent,
                level=excluded.level,
                success=excluded.success,
                result_path=excluded.result_path,
                timestamp=excluded.timestamp
            """,
            (
                result.task_id,
                result.task_description,
                result.agent,
                result.level,
                1 if result.success else 0,
                result.result_path,
                result.timestamp,
            ),
        )
        conn.commit()
        logger.info(
            "Result recorded",
            extra={"context": {"task_id": result.task_id, "agent": result.agent, "success": result.success}},
        )

    def find_result(
        self, task_description: str, ttl_hours: int = 24
    ) -> dict[str, Any] | None:
        """Find a cached result matching a task description within TTL."""
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()
        rows = conn.execute(
            "SELECT * FROM results ORDER BY timestamp DESC",
        ).fetchall()

        task_lower = task_description.lower()
        task_words = set(task_lower.split())

        for row in rows:
            try:
                result_time = datetime.fromisoformat(
                    row["timestamp"].replace("Z", "+00:00")
                )
                age_hours = (
                    datetime.now(timezone.utc) - result_time
                ).total_seconds() / 3600
                if age_hours > ttl_hours:
                    continue
            except (ValueError, TypeError):
                continue

            desc_lower = row["task_description"].lower()
            desc_words = set(desc_lower.split())
            overlap = len(task_words & desc_words)

            if overlap >= 3 or desc_lower in task_lower or task_lower in desc_lower:
                return {
                    "found": True,
                    "result_path": row["result_path"],
                    "task_id": row["task_id"],
                    "agent": row["agent"],
                    "age_hours": round(age_hours, 1),
                    "ttl_hours": ttl_hours,
                    "success": bool(row["success"]),
                }

        return None

    def get_all_results(self) -> list[Result]:
        """Get all cached results."""
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM results ORDER BY timestamp DESC").fetchall()
        return [
            Result(
                task_id=row["task_id"],
                task_description=row["task_description"],
                agent=row["agent"],
                level=row["level"],
                success=bool(row["success"]),
                result_path=row["result_path"],
                timestamp=row["timestamp"],
            )
            for row in rows
        ]

    # ── Migration ───────────────────────────────────────────────────

    def migrate_from_files(self, root_dir: Path | None = None) -> dict[str, int]:
        """Migrate existing JSON/JSONL files to SQLite. Returns counts."""
        root = root_dir or Path(__file__).parent.parent.parent
        sisyphus = root / ".sisyphus"
        counts: dict[str, int] = {
            "sessions": 0,
            "delegations": 0,
            "agent_performance": 0,
            "results": 0,
        }

        # Migrate session-state.json
        session_file = sisyphus / "session-state.json"
        if session_file.exists():
            try:
                data = json.loads(session_file.read_text())
                session = Session(
                    session_id="default",
                    last_agent=data.get("last_agent", ""),
                    last_action=data.get("last_action", ""),
                    session_started=data.get("session_started", ""),
                    last_updated=data.get("last_updated", ""),
                    current_task=data.get("current_task", ""),
                    pending_changes=data.get("pending_changes", []),
                    completed_changes=data.get("completed_changes", []),
                    context=data.get("context", {}),
                )
                self.upsert_session(session)
                counts["sessions"] = 1
                logger.info("Migrated session-state.json")
            except Exception as e:
                logger.error(f"Failed to migrate session-state.json: {e}")

        # Migrate delegations.jsonl
        delegations_file = sisyphus / "delegation-logs" / "delegations.jsonl"
        if delegations_file.exists():
            try:
                conn = self._get_conn()
                with open(delegations_file) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            delegation = Delegation(
                                task_id=data.get("task_id", ""),
                                agent=data.get("agent", ""),
                                level=data.get("level", ""),
                                status=data.get("status", ""),
                                tokens=data.get("tokens", 0),
                                timestamp=data.get("timestamp", ""),
                            )
                            conn.execute(
                                """
                                INSERT INTO delegations (task_id, agent, level, status, tokens, timestamp)
                                VALUES (?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    delegation.task_id,
                                    delegation.agent,
                                    delegation.level,
                                    delegation.status,
                                    delegation.tokens,
                                    delegation.timestamp,
                                ),
                            )
                            counts["delegations"] += 1
                        except json.JSONDecodeError:
                            continue
                conn.commit()
                logger.info(f"Migrated {counts['delegations']} delegations")
            except Exception as e:
                logger.error(f"Failed to migrate delegations.jsonl: {e}")

        # Migrate agent-performance.json
        perf_file = sisyphus / "agent-performance.json"
        if perf_file.exists():
            try:
                data = json.loads(perf_file.read_text())
                now = datetime.now(timezone.utc).isoformat()
                for agent_name, task_types in data.items():
                    if agent_name == "last_updated":
                        continue
                    if isinstance(task_types, dict):
                        for task_type, metrics in task_types.items():
                            perf = AgentPerformance(
                                agent_name=agent_name,
                                task_type=task_type,
                                success=metrics.get("success", 0),
                                failure=metrics.get("failure", 0),
                                last_failure_reason=metrics.get(
                                    "last_failure_reason", ""
                                ),
                                last_updated=now,
                            )
                            self.upsert_agent_performance(perf)
                            counts["agent_performance"] += 1
                logger.info(
                    f"Migrated {counts['agent_performance']} agent performance entries"
                )
            except Exception as e:
                logger.error(f"Failed to migrate agent-performance.json: {e}")

        # Migrate results/index.json
        results_file = sisyphus / "results" / "index.json"
        if results_file.exists():
            try:
                data = json.loads(results_file.read_text())
                results = data.get("results", [])
                for r in results:
                    result = Result(
                        task_id=r.get("task_id", ""),
                        task_description=r.get("task_description", ""),
                        agent=r.get("agent", ""),
                        level=r.get("level", ""),
                        success=r.get("success", False),
                        result_path=r.get("result_path", ""),
                        timestamp=r.get("timestamp", ""),
                    )
                    self.upsert_result(result)
                    counts["results"] += 1
                logger.info(f"Migrated {counts['results']} results")
            except Exception as e:
                logger.error(f"Failed to migrate results/index.json: {e}")

        return counts

    # ── Maintenance ─────────────────────────────────────────────────

    def vacuum(self) -> None:
        """Vacuum the database."""
        conn = self._get_conn()
        conn.execute("VACUUM")
        logger.info("Database vacuumed")

    def close(self) -> None:
        """Close the thread-local connection."""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
