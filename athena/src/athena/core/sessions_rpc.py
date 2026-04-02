"""
athena.core.sessions_rpc
========================

Agent-to-Agent RPC layer for Protocol 416 (Parallel Agent Swarms).
Extracted from OpenClaw's sessions_* tools pattern ("The Great Steal 2.0").

Architecture:
  [Swarm Agent A] --(HTTP POST)--> [athenad /sessions/send] --(SQLite)--> [Master Agent polls /sessions/{id}/history]

Uses the existing athena.db SQLite database. Zero external dependencies.
"""

import sqlite3
import time
import uuid
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from pydantic import BaseModel

from athena.core.config import get_project_root

logger = logging.getLogger("athenad")

PROJECT_ROOT = get_project_root()
DB_PATH = PROJECT_ROOT / ".agent" / "inputs" / "athena.db"


# --- Pydantic Models ---


class SessionRegister(BaseModel):
    session_id: Optional[str] = None  # Auto-generated if not provided
    role: str  # e.g., "master", "A", "B", "C", "D"
    goal: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SessionMessage(BaseModel):
    from_session: str
    to_session: str
    content: str
    msg_type: str = "text"  # text, synthesis, error, heartbeat


class SessionStatus(BaseModel):
    session_id: str
    status: str  # active, completed, error


# --- Core RPC Logic ---


class SessionsRPC:
    """SQLite-backed message bus for inter-agent communication."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def init_tables(self):
        """Create swarm tables if they don't exist."""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS swarm_sessions (
                    session_id TEXT PRIMARY KEY,
                    role TEXT NOT NULL,
                    goal TEXT,
                    status TEXT DEFAULT 'active',
                    metadata TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS swarm_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_session TEXT NOT NULL,
                    to_session TEXT NOT NULL,
                    content TEXT NOT NULL,
                    msg_type TEXT DEFAULT 'text',
                    timestamp REAL NOT NULL,
                    read INTEGER DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_messages_to
                    ON swarm_messages(to_session, timestamp);
                CREATE INDEX IF NOT EXISTS idx_messages_from
                    ON swarm_messages(from_session, timestamp);
            """)
            conn.commit()
            logger.info("✅ Swarm RPC tables initialized.")
        finally:
            conn.close()

    def register_session(self, reg: SessionRegister) -> Dict[str, Any]:
        """Register a new swarm session. Returns the session record."""
        session_id = reg.session_id or f"swarm-{reg.role}-{uuid.uuid4().hex[:8]}"
        now = time.time()
        metadata_str = str(reg.metadata) if reg.metadata else None

        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO swarm_sessions
                   (session_id, role, goal, status, metadata, created_at, updated_at)
                   VALUES (?, ?, ?, 'active', ?, ?, ?)""",
                (session_id, reg.role, reg.goal, metadata_str, now, now),
            )
            conn.commit()
            logger.info(f"📡 Session registered: {session_id} (role={reg.role})")
            return {
                "session_id": session_id,
                "role": reg.role,
                "status": "active",
                "created_at": now,
            }
        finally:
            conn.close()

    def send_message(self, msg: SessionMessage) -> Dict[str, Any]:
        """Send a message from one session to another."""
        now = time.time()
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO swarm_messages
                   (from_session, to_session, content, msg_type, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (msg.from_session, msg.to_session, msg.content, msg.msg_type, now),
            )
            conn.commit()
            msg_id = cursor.lastrowid
            logger.info(
                f"💬 Message #{msg_id}: {msg.from_session} → {msg.to_session} ({msg.msg_type})"
            )
            return {
                "id": msg_id,
                "from": msg.from_session,
                "to": msg.to_session,
                "timestamp": now,
                "status": "delivered",
            }
        finally:
            conn.close()

    def get_history(
        self, session_id: str, limit: int = 50, unread_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get message history for a session (messages sent TO this session)."""
        conn = self._get_conn()
        try:
            query = """SELECT id, from_session, to_session, content, msg_type, timestamp, read
                       FROM swarm_messages
                       WHERE to_session = ?"""
            params: list = [session_id]

            if unread_only:
                query += " AND read = 0"

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()

            # Mark as read
            if rows:
                ids = [r["id"] for r in rows]
                placeholders = ",".join(["?"] * len(ids))
                conn.execute(
                    f"UPDATE swarm_messages SET read = 1 WHERE id IN ({placeholders})",
                    ids,
                )
                conn.commit()

            return [dict(r) for r in rows]
        finally:
            conn.close()

    def list_sessions(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all swarm sessions, optionally filtered by status."""
        conn = self._get_conn()
        try:
            if status:
                rows = conn.execute(
                    "SELECT * FROM swarm_sessions WHERE status = ? ORDER BY created_at DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM swarm_sessions ORDER BY created_at DESC"
                ).fetchall()

            result = []
            for r in rows:
                session = dict(r)
                # Count unread messages
                unread = conn.execute(
                    "SELECT COUNT(*) FROM swarm_messages WHERE to_session = ? AND read = 0",
                    (r["session_id"],),
                ).fetchone()[0]
                session["unread_messages"] = unread
                result.append(session)

            return result
        finally:
            conn.close()

    def update_status(self, update: SessionStatus) -> Dict[str, Any]:
        """Update a session's status (active, completed, error)."""
        now = time.time()
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE swarm_sessions SET status = ?, updated_at = ? WHERE session_id = ?",
                (update.status, now, update.session_id),
            )
            conn.commit()
            logger.info(f"📡 Session {update.session_id} → {update.status}")
            return {"session_id": update.session_id, "status": update.status}
        finally:
            conn.close()
