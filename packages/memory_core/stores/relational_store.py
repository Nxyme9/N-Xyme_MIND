"""Relational Store — SQLite-based structured memory storage."""

import json
import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from packages.memory_core.stores.base import (
    MemoryRecord,
    RelationalStore as RelationalStoreABC,
)

logger = logging.getLogger(__name__)


# Project root detection - resolve relative to module location
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_DB_PATH = _PROJECT_ROOT / "context" / "memory" / "mind_from_mind.db"


# Migration definitions
MIGRATIONS = [
    {
        "version": 1,
        "description": "Initial schema: memories table",
        "sql": """
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'episodic',
                scope TEXT NOT NULL DEFAULT 'session',
                tier TEXT NOT NULL DEFAULT 'short_term',
                meta_json TEXT DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                archived INTEGER DEFAULT 0
            )
        """,
    },
    {
        "version": 2,
        "description": "Add memory_embeddings table",
        "sql": """
            CREATE TABLE IF NOT EXISTS memory_embeddings (
                memory_id TEXT PRIMARY KEY,
                embedding BLOB NOT NULL,
                FOREIGN KEY (memory_id) REFERENCES memories(id)
            )
        """,
    },
    {
        "version": 3,
        "description": "Add indexes for performance",
        "sql": """
            CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind);
            CREATE INDEX IF NOT EXISTS idx_memories_scope ON memories(scope);
            CREATE INDEX IF NOT EXISTS idx_memories_tier ON memories(tier);
            CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at);
            CREATE INDEX IF NOT EXISTS idx_memories_archived ON memories(archived);
        """,
    },
    {
        "version": 4,
        "description": "Add updated_at column for record tracking",
        "sql": """
            ALTER TABLE memories ADD COLUMN updated_at TEXT DEFAULT (datetime('now'));
        """,
    },
    {
        "version": 5,
        "description": "Fix duplicate column on migration 4 (ignore if exists)",
        "sql": """
            -- Migration 4 may fail if column already exists - this handles that case
            SELECT 1;  -- No-op, handled by Python logic
        """,
    },
]


class RelationalStore(RelationalStoreABC):
    """SQLite-based relational memory store with connection pooling."""

    def __init__(self, db_path: str = None):
        # Default to the correct absolute path if no path provided
        if db_path is None:
            db_path = str(_DEFAULT_DB_PATH)

        # Resolve relative paths against project root
        path = Path(db_path)
        if not path.is_absolute():
            path = _PROJECT_ROOT / path

        self.db_path = path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Thread-local storage for connection pooling
        self._local = threading.local()

        # Run initialization with a temporary connection
        conn = self._create_connection()
        self._ensure_migrations_table(conn)
        self._set_wal_mode(conn)
        self._run_pending_migrations(conn)
        self._run_integrity_check(conn)
        conn.close()

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with optimized settings."""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    @property
    def _conn(self) -> sqlite3.Connection:
        """Get thread-local connection (lazy creation, connection pooling)."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = self._create_connection()
        return self._local.conn

    def _set_wal_mode(self, conn: sqlite3.Connection) -> None:
        """Enable WAL journal mode for better concurrency."""
        conn.execute("PRAGMA journal_mode=WAL")
        conn.commit()

    def _run_integrity_check(self, conn: sqlite3.Connection) -> None:
        """Run integrity check on database, log warning if fails."""
        try:
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            if result and result[0] != "ok":
                logger.warning(f"SQLite integrity check failed: {result[0]}")
            else:
                logger.debug("SQLite integrity check passed")
        except Exception as e:
            logger.warning(f"Failed to run integrity check: {e}")

    def _ensure_migrations_table(self, conn: sqlite3.Connection):
        """Create the migrations tracking table if it doesn't exist."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL,
                description TEXT
            )
        """)

    def _get_applied_migrations(self, conn) -> set[int]:
        """Get the set of already applied migration versions."""
        cursor = conn.execute("SELECT version FROM schema_migrations")
        return {row[0] for row in cursor.fetchall()}

    def _record_migration(self, conn, version: int, description: str):
        """Record a migration as applied."""
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at, description) VALUES (?, ?, ?)",
            (version, datetime.now().isoformat(), description),
        )

    def _run_pending_migrations(self, conn: sqlite3.Connection):
        """Run any pending migrations that haven't been applied yet."""
        applied = self._get_applied_migrations(conn)
        for migration in MIGRATIONS:
            if migration["version"] not in applied:
                try:
                    conn.executescript(migration["sql"])
                    conn.execute(
                        "INSERT INTO schema_migrations (version, applied_at, description) VALUES (?, ?, ?)",
                        (
                            migration["version"],
                            datetime.now().isoformat(),
                            migration["description"],
                        ),
                    )
                    conn.commit()
                    logger.info(
                        f"Applied migration v{migration['version']}: {migration['description']}"
                    )
                except sqlite3.OperationalError as e:
                    # Handle case where column already exists (migration 4)
                    if "duplicate column name" in str(e).lower():
                        logger.warning(
                            f"Migration v{migration['version']} failed - column may already exist: {e}"
                        )
                        conn.execute(
                            "INSERT INTO schema_migrations (version, applied_at, description) VALUES (?, ?, ?)",
                            (
                                migration["version"],
                                datetime.now().isoformat(),
                                migration["description"] + " (column existed)",
                            ),
                        )
                        conn.commit()
                    else:
                        raise

    def _ensure_tables(self):
        """Legacy method - tables are now created via migrations."""
        pass

    def store(self, record: MemoryRecord) -> str:
        """Store a memory record and return its ID."""
        conn = self._conn
        conn.execute(
            "INSERT OR REPLACE INTO memories (id, content, kind, scope, tier, meta_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
            (
                record.id,
                record.content,
                record.kind,
                record.scope,
                record.tier,
                json.dumps(record.metadata),
            ),
        )
        conn.commit()
        return record.id

    def get(self, id: str) -> MemoryRecord | None:
        """Get a memory record by ID."""
        conn = self._conn
        cursor = conn.execute(
            "SELECT id, content, kind, scope, tier, meta_json FROM memories WHERE id = ?",
            (id,),
        )
        row = cursor.fetchone()
        if row:
            return MemoryRecord(
                id=row["id"],
                content=row["content"],
                kind=row["kind"],
                scope=row["scope"],
                tier=row["tier"],
                metadata=json.loads(row["meta_json"]) if row["meta_json"] else {},
            )
        return None

    def search(self, query: str, limit: int = 10) -> List[MemoryRecord]:
        """Search for memory records."""
        conn = self._conn
        cursor = conn.execute(
            "SELECT id, content, kind, scope, tier, meta_json FROM memories WHERE content LIKE ? AND archived = 0 LIMIT ?",
            (f"%{query}%", limit),
        )
        return [
            MemoryRecord(
                id=row["id"],
                content=row["content"],
                kind=row["kind"],
                scope=row["scope"],
                tier=row["tier"],
                metadata=json.loads(row["meta_json"]) if row["meta_json"] else {},
            )
            for row in cursor.fetchall()
        ]

    def delete(self, id: str) -> bool:
        """Delete a memory record by ID."""
        conn = self._conn
        cursor = conn.execute("UPDATE memories SET archived = 1 WHERE id = ?", (id,))
        conn.commit()
        return cursor.rowcount > 0

    def stats(self) -> Dict[str, Any]:
        """Get statistics about the store."""
        conn = self._conn
        cursor = conn.execute(
            "SELECT COUNT(*), COUNT(DISTINCT kind) FROM memories WHERE archived = 0"
        )
        row = cursor.fetchone()
        return {"total_memories": row[0] or 0, "memory_types": row[1] or 0}

    def checkpoint(self) -> bool:
        """Run WAL checkpoint to flush WAL to database.

        Returns:
            True if checkpoint succeeded.
        """
        try:
            conn = self._conn
            conn.commit()  # Ensure any pending changes are flushed first
            cursor = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            result = cursor.fetchone()
            # Result is (busy, log, checkpointed)
            return result is not None and result[0] == 0
        except Exception as e:
            logger.error(f"WAL checkpoint failed: {e}")
            return False

    def backup(self, backup_path: str) -> bool:
        """Create a backup of the database.

        Args:
            backup_path: Path to the backup file.

        Returns:
            True if backup succeeded.
        """
        backup_db = Path(backup_path)
        backup_db.parent.mkdir(parents=True, exist_ok=True)

        # Use pooled connection for source, new connection for target
        source = self._conn
        target = self._create_connection()
        try:
            source.backup(target)
            logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return False
        finally:
            target.close()

    def integrity_check(self) -> tuple[bool, str]:
        """Run integrity check on the database.

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            conn = self._conn
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            if result and result[0] == "ok":
                return (True, "Database integrity OK")
            else:
                return (False, result[0] if result else "Unknown error")
        except Exception as e:
            return (False, str(e))


__all__ = ["RelationalStore"]
