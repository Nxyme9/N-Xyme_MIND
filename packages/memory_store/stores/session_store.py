"""SessionStore — Session state migration from .sisyphus to memory_store.

This module provides:
- Migration of session state from .sisyphus/state.db
- Migration of context from .sisyphus/context.db
- Migration of messages from .sisyphus/messages.db
- Dual-write pattern during transition period
"""

import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Project root detection
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_DB_PATH = _PROJECT_ROOT / "packages" / "memory_store" / "memory.db"

# Source .sisyphus databases
_STATE_DB = _PROJECT_ROOT / ".sisyphus" / "state.db"
_CONTEXT_DB = _PROJECT_ROOT / ".sisyphus" / "context.db"
_MESSAGES_DB = _PROJECT_ROOT / ".sisyphus" / "messages.db"


class SessionStore:
    """Session store that migrates from .sisyphus to memory_store.

    Implements dual-write pattern: writes to BOTH legacy .sisyphus
    AND memory_store during transition period.
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(_DEFAULT_DB_PATH)
        self.db_path = Path(self.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Thread-local storage for connection pooling
        self._local = threading.local()

        # Initialize schema
        conn = self._create_connection()
        self._ensure_schema(conn)
        conn.close()

        logger.info(f"SessionStore initialized at {self.db_path}")

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection."""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    @property
    def _conn(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = self._create_connection()
        return self._local.conn

    def _ensure_schema(self, conn: sqlite3.Connection):
        """Create migration tables if they don't exist."""
        # Sessions table (from state.db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                last_agent TEXT NOT NULL DEFAULT '',
                last_action TEXT NOT NULL DEFAULT '',
                session_started TEXT NOT NULL DEFAULT '',
                last_updated TEXT NOT NULL DEFAULT '',
                current_task TEXT NOT NULL DEFAULT '',
                pending_changes TEXT NOT NULL DEFAULT '[]',
                completed_changes TEXT NOT NULL DEFAULT '[]',
                context TEXT NOT NULL DEFAULT '{}',
                migrated_at TEXT
            )
        """)

        # Delegations table (from state.db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS delegations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                agent TEXT NOT NULL,
                level TEXT NOT NULL,
                status TEXT NOT NULL,
                tokens INTEGER NOT NULL DEFAULT 0,
                timestamp TEXT NOT NULL,
                migrated_at TEXT
            )
        """)

        # Agent performance table (from state.db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                task_type TEXT NOT NULL,
                success INTEGER NOT NULL DEFAULT 0,
                failure INTEGER NOT NULL DEFAULT 0,
                last_failure_reason TEXT NOT NULL DEFAULT '',
                last_updated TEXT NOT NULL DEFAULT '',
                migrated_at TEXT,
                UNIQUE(agent_name, task_type)
            )
        """)

        # Results table (from state.db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS results (
                task_id TEXT PRIMARY KEY,
                task_description TEXT NOT NULL,
                agent TEXT NOT NULL,
                level TEXT NOT NULL,
                success INTEGER NOT NULL DEFAULT 0,
                result_path TEXT NOT NULL DEFAULT '',
                timestamp TEXT NOT NULL,
                migrated_at TEXT
            )
        """)

        # Session context (from context.db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                context_type TEXT NOT NULL,
                context_key TEXT NOT NULL,
                context_value TEXT,
                priority INTEGER DEFAULT 0,
                created_at REAL,
                expires_at REAL,
                metadata TEXT,
                migrated_at TEXT
            )
        """)

        # Session summary (from context.db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_summary (
                session_id TEXT PRIMARY KEY,
                summary TEXT,
                key_decisions TEXT,
                active_tasks TEXT,
                created_at REAL,
                updated_at REAL,
                migrated_at TEXT
            )
        """)

        # Messages (from messages.db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                from_agent TEXT NOT NULL,
                to_agent TEXT,
                type TEXT NOT NULL,
                subject TEXT,
                content TEXT,
                priority INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at REAL,
                updated_at REAL,
                response_to TEXT,
                metadata TEXT,
                migrated_at TEXT
            )
        """)

        # Migration metadata
        conn.execute("""
            CREATE TABLE IF NOT EXISTS migration_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_db TEXT NOT NULL,
                source_table TEXT NOT NULL,
                records_migrated INTEGER NOT NULL DEFAULT 0,
                migrated_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'success'
            )
        """)

        conn.commit()

    # ===== Session Operations =====

    def store_session(
        self, session_data: Dict[str, Any], dual_write: bool = True
    ) -> str:
        """Store a session with dual-write support.

        Args:
            session_data: Session data dict
            dual_write: If True, write to both legacy and memory_store

        Returns:
            Session ID
        """
        session_id = session_data.get("session_id")
        migrated_at = datetime.now(timezone.utc).isoformat()

        conn = self._conn
        conn.execute(
            """
            INSERT OR REPLACE INTO sessions 
            (session_id, last_agent, last_action, session_started, last_updated, 
             current_task, pending_changes, completed_changes, context, migrated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                session_id,
                session_data.get("last_agent", ""),
                session_data.get("last_action", ""),
                session_data.get("session_started", ""),
                session_data.get("last_updated", ""),
                session_data.get("current_task", ""),
                session_data.get("pending_changes", "[]"),
                session_data.get("completed_changes", "[]"),
                session_data.get("context", "{}"),
                migrated_at,
            ),
        )
        conn.commit()

        # Dual-write to memory_store if enabled
        if dual_write:
            self._write_session_to_memory(session_data)

        return session_id

    def _write_session_to_memory(self, session_data: Dict[str, Any]):
        """Write session to memory_store as episodic memory."""
        try:
            from packages.memory_store import memory_write

            content = f"Session: {session_data.get('session_id')}\n"
            content += f"Task: {session_data.get('current_task', 'N/A')}\n"
            content += f"Agent: {session_data.get('last_agent', 'N/A')}\n"
            content += f"Started: {session_data.get('session_started', 'N/A')}\n"

            memory_write(
                content=content,
                kind="episodic",
                scope="session",
                tags=["session", "migrated", session_data.get("session_id", "")],
            )
            logger.debug(
                f"Dual-write session to memory_store: {session_data.get('session_id')}"
            )
        except Exception as e:
            logger.warning(f"Failed to dual-write session to memory_store: {e}")

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID."""
        conn = self._conn
        cursor = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def list_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List all sessions."""
        conn = self._conn
        cursor = conn.execute(
            "SELECT * FROM sessions ORDER BY last_updated DESC LIMIT ?", (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    # ===== Delegation Operations =====

    def store_delegation(
        self, delegation_data: Dict[str, Any], dual_write: bool = True
    ) -> int:
        """Store a delegation record."""
        migrated_at = datetime.now(timezone.utc).isoformat()

        conn = self._conn
        cursor = conn.execute(
            """
            INSERT INTO delegations 
            (task_id, agent, level, status, tokens, timestamp, migrated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                delegation_data.get("task_id"),
                delegation_data.get("agent"),
                delegation_data.get("level"),
                delegation_data.get("status"),
                delegation_data.get("tokens", 0),
                delegation_data.get("timestamp"),
                migrated_at,
            ),
        )
        conn.commit()

        # Dual-write to learning_engine if enabled
        if dual_write:
            self._write_delegation_to_learning(delegation_data)

        return cursor.lastrowid

    def _write_delegation_to_learning(self, delegation_data: Dict[str, Any]):
        """Write delegation to learning_engine."""
        try:
            from packages.learning_engine import record_outcome

            record_outcome(
                task=delegation_data.get("task_id", ""),
                agent=delegation_data.get("agent", ""),
                success=delegation_data.get("status") == "completed",
                latency_ms=0,
                tokens_used=delegation_data.get("tokens", 0),
            )
        except Exception as e:
            logger.warning(f"Failed to dual-write delegation to learning: {e}")

    def list_delegations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all delegations."""
        conn = self._conn
        cursor = conn.execute(
            "SELECT * FROM delegations ORDER BY timestamp DESC LIMIT ?", (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    # ===== Agent Performance Operations =====

    def store_agent_performance(self, perf_data: Dict[str, Any]) -> int:
        """Store agent performance record."""
        migrated_at = datetime.now(timezone.utc).isoformat()

        conn = self._conn
        cursor = conn.execute(
            """
            INSERT OR REPLACE INTO agent_performance
            (agent_name, task_type, success, failure, last_failure_reason, last_updated, migrated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                perf_data.get("agent_name"),
                perf_data.get("task_type"),
                perf_data.get("success", 0),
                perf_data.get("failure", 0),
                perf_data.get("last_failure_reason", ""),
                perf_data.get("last_updated", ""),
                migrated_at,
            ),
        )
        conn.commit()
        return cursor.lastrowid

    def list_agent_performance(self) -> List[Dict[str, Any]]:
        """List all agent performance records."""
        conn = self._conn
        cursor = conn.execute("SELECT * FROM agent_performance")
        return [dict(row) for row in cursor.fetchall()]

    # ===== Results Operations =====

    def store_result(self, result_data: Dict[str, Any]) -> str:
        """Store a result record."""
        migrated_at = datetime.now(timezone.utc).isoformat()

        conn = self._conn
        conn.execute(
            """
            INSERT OR REPLACE INTO results
            (task_id, task_description, agent, level, success, result_path, timestamp, migrated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                result_data.get("task_id"),
                result_data.get("task_description"),
                result_data.get("agent"),
                result_data.get("level"),
                result_data.get("success", 0),
                result_data.get("result_path", ""),
                result_data.get("timestamp"),
                migrated_at,
            ),
        )
        conn.commit()
        return result_data.get("task_id", "")

    def list_results(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all results."""
        conn = self._conn
        cursor = conn.execute(
            "SELECT * FROM results ORDER BY timestamp DESC LIMIT ?", (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    # ===== Session Context Operations =====

    def store_session_context(self, ctx_data: Dict[str, Any]) -> int:
        """Store session context."""
        migrated_at = datetime.now(timezone.utc).isoformat()

        conn = self._conn
        cursor = conn.execute(
            """
            INSERT INTO session_context 
            (session_id, context_type, context_key, context_value, priority, 
             created_at, expires_at, metadata, migrated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                ctx_data.get("session_id"),
                ctx_data.get("context_type"),
                ctx_data.get("context_key"),
                ctx_data.get("context_value"),
                ctx_data.get("priority", 0),
                ctx_data.get("created_at"),
                ctx_data.get("expires_at"),
                ctx_data.get("metadata"),
                migrated_at,
            ),
        )
        conn.commit()
        return cursor.lastrowid

    def get_session_context(self, session_id: str) -> List[Dict[str, Any]]:
        """Get context for a session."""
        conn = self._conn
        cursor = conn.execute(
            "SELECT * FROM session_context WHERE session_id = ?", (session_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    # ===== Session Summary Operations =====

    def store_session_summary(self, summary_data: Dict[str, Any]) -> str:
        """Store session summary."""
        migrated_at = datetime.now(timezone.utc).isoformat()

        conn = self._conn
        conn.execute(
            """
            INSERT OR REPLACE INTO session_summary
            (session_id, summary, key_decisions, active_tasks, 
             created_at, updated_at, migrated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                summary_data.get("session_id"),
                summary_data.get("summary"),
                summary_data.get("key_decisions"),
                summary_data.get("active_tasks"),
                summary_data.get("created_at"),
                summary_data.get("updated_at"),
                migrated_at,
            ),
        )
        conn.commit()
        return summary_data.get("session_id", "")

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get summary for a session."""
        conn = self._conn
        cursor = conn.execute(
            "SELECT * FROM session_summary WHERE session_id = ?", (session_id,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    # ===== Message Operations =====

    def store_message(self, msg_data: Dict[str, Any]) -> str:
        """Store a message."""
        migrated_at = datetime.now(timezone.utc).isoformat()

        conn = self._conn
        conn.execute(
            """
            INSERT OR REPLACE INTO messages
            (id, from_agent, to_agent, type, subject, content, priority, status,
             created_at, updated_at, response_to, metadata, migrated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                msg_data.get("id"),
                msg_data.get("from_agent"),
                msg_data.get("to_agent"),
                msg_data.get("type"),
                msg_data.get("subject"),
                msg_data.get("content"),
                msg_data.get("priority", 0),
                msg_data.get("status", "pending"),
                msg_data.get("created_at"),
                msg_data.get("updated_at"),
                msg_data.get("response_to"),
                msg_data.get("metadata"),
                migrated_at,
            ),
        )
        conn.commit()
        return msg_data.get("id", "")

    def list_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all messages."""
        conn = self._conn
        cursor = conn.execute(
            "SELECT * FROM messages ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_messages_for_agent(
        self, agent: str, status: str = None
    ) -> List[Dict[str, Any]]:
        """Get messages for a specific agent."""
        conn = self._conn
        if status:
            cursor = conn.execute(
                "SELECT * FROM messages WHERE to_agent = ? AND status = ? ORDER BY created_at DESC",
                (agent, status),
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM messages WHERE to_agent = ? ORDER BY created_at DESC",
                (agent,),
            )
        return [dict(row) for row in cursor.fetchall()]

    # ===== Statistics =====

    def stats(self) -> Dict[str, Any]:
        """Get migration statistics."""
        conn = self._conn

        stats = {}

        for table in [
            "sessions",
            "delegations",
            "agent_performance",
            "results",
            "session_context",
            "session_summary",
            "messages",
        ]:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
            stats[f"{table}_count"] = cursor.fetchone()[0]

        return stats

    def migration_log(self) -> List[Dict[str, Any]]:
        """Get migration log."""
        conn = self._conn
        cursor = conn.execute("SELECT * FROM migration_log ORDER BY migrated_at DESC")
        return [dict(row) for row in cursor.fetchall()]


# Singleton instance
_session_store: Optional[SessionStore] = None
_lock = threading.Lock()


def get_session_store() -> SessionStore:
    """Get or create SessionStore singleton."""
    global _session_store
    if _session_store is None:
        with _lock:
            if _session_store is None:
                _session_store = SessionStore()
    return _session_store


__all__ = ["SessionStore", "get_session_store"]
