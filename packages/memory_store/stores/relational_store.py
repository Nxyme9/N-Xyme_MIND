"""Relational Store — SQLite-based structured memory storage."""

import json
import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from packages.memory_store.stores.base import (
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
    {
        "version": 6,
        "description": "Add tags support via meta_json",
        "sql": """
            -- Tags are stored in meta_json column - no schema change needed
            -- This migration just confirms the capability
            SELECT 1;
        """,
    },
    {
        "version": 7,
        "description": "Add memory versioning (version_hash, parent_version, branch_id, is_latest)",
        "sql": """
            -- Add versioning columns to memories table
            ALTER TABLE memories ADD COLUMN version_hash TEXT;
            ALTER TABLE memories ADD COLUMN parent_version TEXT;
            ALTER TABLE memories ADD COLUMN branch_id TEXT DEFAULT 'main';
            ALTER TABLE memories ADD COLUMN is_latest INTEGER DEFAULT 1;
            
            -- Create memory_versions table for full version history
            CREATE TABLE IF NOT EXISTS memory_versions (
                id TEXT PRIMARY KEY,
                memory_id TEXT NOT NULL,
                version_hash TEXT NOT NULL,
                parent_version TEXT,
                branch_id TEXT DEFAULT 'main',
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                created_by TEXT DEFAULT 'system'
            );
            
            -- Create branches table for branch management
            CREATE TABLE IF NOT EXISTS branches (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                parent_branch_id TEXT,
                is_active INTEGER DEFAULT 1
            );
            
            -- Create indexes for version queries
            CREATE INDEX IF NOT EXISTS idx_memory_versions_memory_id ON memory_versions(memory_id);
            CREATE INDEX IF NOT EXISTS idx_memory_versions_hash ON memory_versions(version_hash);
            CREATE INDEX IF NOT EXISTS idx_memory_versions_branch ON memory_versions(branch_id);
            CREATE INDEX IF NOT EXISTS idx_memories_branch ON memories(branch_id);
            
            -- Insert default main branch
            INSERT OR IGNORE INTO branches (id, name, is_active) VALUES ('main', 'main', 1);
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

    # ===== Version Control Methods =====

    def store_version(
        self,
        memory_id: str,
        version_hash: str,
        content: str,
        parent_version: Optional[str] = None,
        branch_id: str = "main",
        created_by: str = "system",
    ) -> str:
        """Store a memory version in the versions table.

        Args:
            memory_id: The memory ID
            version_hash: SHA256 hash of the content
            content: The memory content
            parent_version: Parent version hash
            branch_id: Branch ID (default 'main')
            created_by: Creator identifier

        Returns:
            Version ID
        """
        import uuid

        conn = self._conn
        version_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO memory_versions 
               (id, memory_id, version_hash, parent_version, branch_id, content, created_at, created_by) 
               VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?)""",
            (
                version_id,
                memory_id,
                version_hash,
                parent_version,
                branch_id,
                content,
                created_by,
            ),
        )
        conn.commit()
        return version_id

    def get_version_history(self, memory_id: str) -> List[Dict[str, Any]]:
        """Get version history for a memory.

        Args:
            memory_id: The memory ID

        Returns:
            List of version records
        """
        conn = self._conn
        cursor = conn.execute(
            """SELECT id, memory_id, version_hash, parent_version, branch_id, content, created_at, created_by
               FROM memory_versions WHERE memory_id = ? ORDER BY created_at DESC""",
            (memory_id,),
        )
        return [
            {
                "id": row["id"],
                "memory_id": row["memory_id"],
                "version_hash": row["version_hash"],
                "parent_version": row["parent_version"],
                "branch_id": row["branch_id"],
                "content": row["content"],
                "created_at": row["created_at"],
                "created_by": row["created_by"],
            }
            for row in cursor.fetchall()
        ]

    def get_version_by_hash(
        self, memory_id: str, version_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific version by hash.

        Args:
            memory_id: The memory ID
            version_hash: The version hash

        Returns:
            Version record or None
        """
        conn = self._conn
        cursor = conn.execute(
            """SELECT id, memory_id, version_hash, parent_version, branch_id, content, created_at, created_by
               FROM memory_versions WHERE memory_id = ? AND version_hash = ?""",
            (memory_id, version_hash),
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "memory_id": row["memory_id"],
                "version_hash": row["version_hash"],
                "parent_version": row["parent_version"],
                "branch_id": row["branch_id"],
                "content": row["content"],
                "created_at": row["created_at"],
                "created_by": row["created_by"],
            }
        return None

    def get_latest_version(
        self, memory_id: str, branch_id: str = "main"
    ) -> Optional[Dict[str, Any]]:
        """Get the latest version for a memory on a branch.

        Args:
            memory_id: The memory ID
            branch_id: Branch ID

        Returns:
            Version record or None
        """
        conn = self._conn
        cursor = conn.execute(
            """SELECT id, memory_id, version_hash, parent_version, branch_id, content, created_at, created_by
               FROM memory_versions WHERE memory_id = ? AND branch_id = ? ORDER BY created_at DESC LIMIT 1""",
            (memory_id, branch_id),
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "memory_id": row["memory_id"],
                "version_hash": row["version_hash"],
                "parent_version": row["parent_version"],
                "branch_id": row["branch_id"],
                "content": row["content"],
                "created_at": row["created_at"],
                "created_by": row["created_by"],
            }
        return None

    # ===== Branch Management Methods =====

    def create_branch(self, name: str, parent_branch_id: Optional[str] = None) -> str:
        """Create a new branch.

        Args:
            name: Branch name
            parent_branch_id: Parent branch ID (for branching)

        Returns:
            Branch ID
        """
        import uuid

        conn = self._conn
        branch_id = str(uuid.uuid4())[:8]  # Short ID
        conn.execute(
            """INSERT INTO branches (id, name, parent_branch_id, is_active) VALUES (?, ?, ?, 1)""",
            (branch_id, name, parent_branch_id),
        )
        conn.commit()
        return branch_id

    def get_branch(self, branch_id: str) -> Optional[Dict[str, Any]]:
        """Get branch by ID.

        Args:
            branch_id: Branch ID

        Returns:
            Branch record or None
        """
        conn = self._conn
        cursor = conn.execute(
            "SELECT id, name, created_at, parent_branch_id, is_active FROM branches WHERE id = ?",
            (branch_id,),
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "name": row["name"],
                "created_at": row["created_at"],
                "parent_branch_id": row["parent_branch_id"],
                "is_active": row["is_active"],
            }
        return None

    def get_branch_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get branch by name.

        Args:
            name: Branch name

        Returns:
            Branch record or None
        """
        conn = self._conn
        cursor = conn.execute(
            "SELECT id, name, created_at, parent_branch_id, is_active FROM branches WHERE name = ?",
            (name,),
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "name": row["name"],
                "created_at": row["created_at"],
                "parent_branch_id": row["parent_branch_id"],
                "is_active": row["is_active"],
            }
        return None

    def list_branches(self) -> List[Dict[str, Any]]:
        """List all branches.

        Returns:
            List of branch records
        """
        conn = self._conn
        cursor = conn.execute(
            "SELECT id, name, created_at, parent_branch_id, is_active FROM branches ORDER BY created_at"
        )
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "created_at": row["created_at"],
                "parent_branch_id": row["parent_branch_id"],
                "is_active": row["is_active"],
            }
            for row in cursor.fetchall()
        ]

    def set_active_branch(self, branch_id: str) -> bool:
        """Set active branch.

        Args:
            branch_id: Branch ID to activate

        Returns:
            True if successful
        """
        conn = self._conn
        conn.execute("UPDATE branches SET is_active = 0")
        cursor = conn.execute(
            "UPDATE branches SET is_active = 1 WHERE id = ?", (branch_id,)
        )
        conn.commit()
        return cursor.rowcount > 0

    def get_active_branch(self) -> Optional[Dict[str, Any]]:
        """Get the currently active branch.

        Returns:
            Active branch record or None
        """
        conn = self._conn
        cursor = conn.execute(
            "SELECT id, name, created_at, parent_branch_id, is_active FROM branches WHERE is_active = 1"
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "name": row["name"],
                "created_at": row["created_at"],
                "parent_branch_id": row["parent_branch_id"],
                "is_active": row["is_active"],
            }
        return None


__all__ = ["RelationalStore"]
