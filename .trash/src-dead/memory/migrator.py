#!/usr/bin/env python3
"""
Memory Migrator — Migrate old memory from nx_openmore and N-Xyme_CATALYST into unified system.

Source locations:
1. nx_openmore: $NX_OPENMORE_ROOT/context/memory/
   - mind_from_mind.db (2.1 MB) - Primary mind state
   - jarvis_memory.db (28 KB) - JARVIS agent memory
   - jarvis_events.db (20 KB) - Event logs
   - nxm_from_mind.db (68 KB) - NXM state
   - semantic_memory.json (322 B) - Semantic memory

2. N-Xyme_CATALYST: /mnt/NXYME_CORE/01_CODING/00_N-Xyme_CATALYST/data/
   - opencode.db (3.6 GB) - OpenCode sessions
   - nervous_system.db (303 KB) - System state
   - block_registry.db (106 KB) - Trigger blocks

3. Transcripts: $NX_OPENMORE_ROOT/context/claude/transcripts/
   - 400+ transcript files to embed and index
"""

import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

# Mount paths (may not be accessible in current environment)
NX_OPENMORE_PATH = os.environ.get("NX_OPENMORE_ROOT", "/mnt/Library/nx_openmore")
N_XYME_CATALYST_PATH = "/mnt/NXYME_CORE/01_CODING/00_N-Xyme_CATALYST"

# Source DB paths
NX_OPENMORE_SOURCES = {
    "mind_from_mind": f"{NX_OPENMORE_PATH}/context/memory/mind_from_mind.db",
    "jarvis_memory": f"{NX_OPENMORE_PATH}/context/memory/jarvis_memory.db",
    "jarvis_events": f"{NX_OPENMORE_PATH}/context/memory/jarvis_events.db",
    "nxm_from_mind": f"{NX_OPENMORE_PATH}/context/memory/nxm_from_mind.db",
    "semantic_memory": f"{NX_OPENMORE_PATH}/context/memory/semantic_memory.json",
}

N_XYME_CATALYST_SOURCES = {
    "opencode": f"{N_XYME_CATALYST_PATH}/data/opencode/opencode.db",
    "nervous_system": f"{N_XYME_CATALYST_PATH}/data/nervous_system.db",
    "block_registry": f"{N_XYME_CATALYST_PATH}/data/block_registry.db",
    "mind_data": f"{N_XYME_CATALYST_PATH}/data/mind-data",
    "neo4j": f"{N_XYME_CATALYST_PATH}/data/neo4j",
}

TRANSCRIPTS_PATH = f"{NX_OPENMORE_PATH}/context/claude/transcripts"

# Unified memory DB path
MEMORY_DB_PATH = os.environ.get("MEMORY_DB_PATH", "./data/memory_migration.db")

# ============================================================================
# Data Models
# ============================================================================


@dataclass
class MigrationRecord:
    """A single migrated memory record."""

    id: str
    source: str
    source_type: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedded: bool = False
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=datetime.now)
    migrated_at: datetime = field(default_factory=datetime.now)


@dataclass
class MigrationStatus:
    """Migration status for a source."""

    source_name: str
    exists: bool
    record_count: int = 0
    migrated_count: int = 0
    error: Optional[str] = None
    last_attempt: Optional[datetime] = None


# ============================================================================
# Migration Database
# ============================================================================


class MigrationDB:
    """Unified migration database for storing migrated records."""

    def __init__(self, db_path: str = MEMORY_DB_PATH):
        self.db_path = db_path
        self._ensure_dir()
        self._init_db()

    def _ensure_dir(self):
        """Ensure database directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _init_db(self):
        """Initialize migration database schema."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Main migration table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                source_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                embedded INTEGER DEFAULT 0,
                embedding BLOB,
                created_at TEXT,
                migrated_at TEXT NOT NULL
            )
        """)

        # Migration status tracking
        cur.execute("""
            CREATE TABLE IF NOT EXISTS migration_status (
                source_name TEXT PRIMARY KEY,
                source_exists INTEGER DEFAULT 0,
                record_count INTEGER DEFAULT 0,
                migrated_count INTEGER DEFAULT 0,
                error TEXT,
                last_attempt TEXT
            )
        """)

        # Transcript index
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transcript_index (
                file_name TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                content TEXT,
                embedding BLOB,
                indexed_at TEXT NOT NULL
            )
        """)

        # Create indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_source ON migrations(source)")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_source_type ON migrations(source_type)"
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_embedded ON migrations(embedded)")

        conn.commit()
        conn.close()

    def insert_migration(self, record: MigrationRecord):
        """Insert a migration record."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute(
            """
            INSERT OR REPLACE INTO migrations 
            (id, source, source_type, content, metadata, embedded, embedding, created_at, migrated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                record.id,
                record.source,
                record.source_type,
                record.content,
                json.dumps(record.metadata),
                1 if record.embedded else 0,
                json.dumps(record.embedding) if record.embedding else None,
                record.created_at.isoformat(),
                record.migrated_at.isoformat(),
            ),
        )

        conn.commit()
        conn.close()

    def update_status(self, status: MigrationStatus):
        """Update migration status for a source."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute(
            """
            INSERT OR REPLACE INTO migration_status 
            (source_name, source_exists, record_count, migrated_count, error, last_attempt)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                status.source_name,
                1 if status.exists else 0,
                status.record_count,
                status.migrated_count,
                status.error,
                status.last_attempt.isoformat() if status.last_attempt else None,
            ),
        )

        conn.commit()
        conn.close()

    def get_status(self, source_name: str) -> Optional[MigrationStatus]:
        """Get migration status for a source."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM migration_status WHERE source_name = ?", (source_name,)
        )
        row = cur.fetchone()
        conn.close()

        if row:
            return MigrationStatus(
                source_name=row[0],
                exists=bool(row[1]),
                record_count=row[2],
                migrated_count=row[3],
                error=row[4],
                last_attempt=datetime.fromisoformat(row[5]) if row[5] else None,
            )
        return None

    def get_all_status(self) -> List[MigrationStatus]:
        """Get migration status for all sources."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT * FROM migration_status")
        rows = cur.fetchall()
        conn.close()

        return [
            MigrationStatus(
                source_name=row[0],
                exists=bool(row[1]),
                record_count=row[2],
                migrated_count=row[3],
                error=row[4],
                last_attempt=datetime.fromisoformat(row[5]) if row[5] else None,
            )
            for row in rows
        ]

    def count_migrations(self, source: Optional[str] = None) -> int:
        """Count migration records."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        if source:
            cur.execute("SELECT COUNT(*) FROM migrations WHERE source = ?", (source,))
        else:
            cur.execute("SELECT COUNT(*) FROM migrations")

        count = cur.fetchone()[0]
        conn.close()
        return count

    def list_tables(self) -> List[str]:
        """List all tables in migration DB."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall()]
        conn.close()

        return tables


# ============================================================================
# Source Migration Base
# ============================================================================


class BaseMigrator:
    """Base class for source migrators."""

    def __init__(self, name: str, source_path: str):
        self.name = name
        self.source_path = source_path
        self.db = MigrationDB()

    def exists(self) -> bool:
        """Check if source exists."""
        return os.path.exists(self.source_path)

    def migrate(self) -> Tuple[int, Optional[str]]:
        """Migrate source. Returns (count, error)."""
        raise NotImplementedError

    def count_records(self) -> int:
        """Count records in source."""
        raise NotImplementedError


# ============================================================================
# nx_openmore Migrators
# ============================================================================


class MindFromMindMigrator(BaseMigrator):
    """Migrate mind_from_mind.db (2.1 MB)."""

    def __init__(self):
        super().__init__("mind_from_mind", NX_OPENMORE_SOURCES["mind_from_mind"])

    def exists(self) -> bool:
        return os.path.exists(self.source_path)

    def count_records(self) -> int:
        if not self.exists():
            return 0
        try:
            conn = sqlite3.connect(self.source_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cur.fetchone()[0]
            conn.close()
            return table_count * 1000 if table_count > 0 else 0
        except Exception:
            return 0

    def migrate(self) -> Tuple[int, Optional[str]]:
        if not self.exists():
            return 0, "Source file not found"

        try:
            conn = sqlite3.connect(self.source_path)
            cur = conn.cursor()

            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cur.fetchall()]

            migrated = 0
            for table in tables:
                try:
                    cur.execute(f"SELECT * FROM {table} LIMIT 100")
                    rows = cur.fetchall()
                    columns = [desc[0] for desc in cur.description]

                    for row_idx, row in enumerate(rows):
                        record_id = f"{self.name}_{table}_{row_idx}"

                        content_parts = []
                        metadata = {"table": table, "columns": columns}
                        for col_idx, col in enumerate(columns):
                            if col_idx < len(row):
                                val = row[col_idx]
                                if val:
                                    content_parts.append(f"{col}: {val}")
                                    metadata[col] = str(val)

                        content = "; ".join(content_parts)
                        if content:
                            record = MigrationRecord(
                                id=record_id,
                                source=self.name,
                                source_type=table,
                                content=content,
                                metadata=metadata,
                            )
                            self.db.insert_migration(record)
                            migrated += 1

                except Exception as e:
                    logger.warning(f"Error migrating table {table}: {e}")

            conn.close()
            return migrated, None

        except Exception as e:
            return 0, str(e)


class JarvisMemoryMigrator(BaseMigrator):
    """Migrate jarvis_memory.db (28 KB)."""

    def __init__(self):
        super().__init__("jarvis_memory", NX_OPENMORE_SOURCES["jarvis_memory"])

    def exists(self) -> bool:
        return os.path.exists(self.source_path)

    def count_records(self) -> int:
        if not self.exists():
            return 0
        try:
            conn = sqlite3.connect(self.source_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM facts")
            count = cur.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0

    def migrate(self) -> Tuple[int, Optional[str]]:
        if not self.exists():
            return 0, "Source file not found"

        try:
            conn = sqlite3.connect(self.source_path)
            cur = conn.cursor()

            migrated = 0
            # Migrate facts table
            try:
                cur.execute("SELECT * FROM facts")
                rows = cur.fetchall()
                for row_idx, row in enumerate(rows):
                    record_id = f"{self.name}_facts_{row_idx}"
                    content = str(row) if row else ""

                    record = MigrationRecord(
                        id=record_id,
                        source=self.name,
                        source_type="fact",
                        content=content,
                        metadata={"table": "facts", "row": row_idx},
                    )
                    self.db.insert_migration(record)
                    migrated += 1
            except Exception:
                pass

            # Migrate episodes table
            try:
                cur.execute("SELECT * FROM episodes")
                rows = cur.fetchall()
                for row_idx, row in enumerate(rows):
                    record_id = f"{self.name}_episodes_{row_idx}"
                    content = str(row) if row else ""

                    record = MigrationRecord(
                        id=record_id,
                        source=self.name,
                        source_type="episode",
                        content=content,
                        metadata={"table": "episodes", "row": row_idx},
                    )
                    self.db.insert_migration(record)
                    migrated += 1
            except Exception:
                pass

            # Migrate conversation_history table
            try:
                cur.execute("SELECT * FROM conversation_history")
                rows = cur.fetchall()
                for row_idx, row in enumerate(rows):
                    record_id = f"{self.name}_conv_{row_idx}"
                    content = str(row) if row else ""

                    record = MigrationRecord(
                        id=record_id,
                        source=self.name,
                        source_type="conversation",
                        content=content,
                        metadata={"table": "conversation_history", "row": row_idx},
                    )
                    self.db.insert_migration(record)
                    migrated += 1
            except Exception:
                pass

            conn.close()
            return migrated, None

        except Exception as e:
            return 0, str(e)


class JarvisEventsMigrator(BaseMigrator):
    """Migrate jarvis_events.db (20 KB)."""

    def __init__(self):
        super().__init__("jarvis_events", NX_OPENMORE_SOURCES["jarvis_events"])

    def exists(self) -> bool:
        return os.path.exists(self.source_path)

    def count_records(self) -> int:
        if not self.exists():
            return 0
        try:
            conn = sqlite3.connect(self.source_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM event_log")
            count = cur.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0

    def migrate(self) -> Tuple[int, Optional[str]]:
        if not self.exists():
            return 0, "Source file not found"

        try:
            conn = sqlite3.connect(self.source_path)
            cur = conn.cursor()

            cur.execute("SELECT * FROM event_log")
            rows = cur.fetchall()

            migrated = 0
            for row_idx, row in enumerate(rows):
                record_id = f"{self.name}_{row_idx}"
                content = str(row) if row else ""

                record = MigrationRecord(
                    id=record_id,
                    source=self.name,
                    source_type="event",
                    content=content,
                    metadata={"row": row_idx},
                )
                self.db.insert_migration(record)
                migrated += 1

            conn.close()
            return migrated, None

        except Exception as e:
            return 0, str(e)


class NXMFromMindMigrator(BaseMigrator):
    """Migrate nxm_from_mind.db (68 KB)."""

    def __init__(self):
        super().__init__("nxm_from_mind", NX_OPENMORE_SOURCES["nxm_from_mind"])

    def exists(self) -> bool:
        return os.path.exists(self.source_path)

    def count_records(self) -> int:
        if not self.exists():
            return 0
        try:
            conn = sqlite3.connect(self.source_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM threads")
            count = cur.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0

    def migrate(self) -> Tuple[int, Optional[str]]:
        if not self.exists():
            return 0, "Source file not found"

        try:
            conn = sqlite3.connect(self.source_path)
            cur = conn.cursor()

            migrated = 0
            tables = [
                "threads",
                "messages",
                "memory_facts",
                "tasks",
                "projects",
                "clients",
                "settings",
                "providers",
            ]

            for table in tables:
                try:
                    cur.execute(f"SELECT * FROM {table}")
                    rows = cur.fetchall()
                    for row_idx, row in enumerate(rows):
                        record_id = f"{self.name}_{table}_{row_idx}"
                        content = str(row) if row else ""

                        record = MigrationRecord(
                            id=record_id,
                            source=self.name,
                            source_type=table,
                            content=content,
                            metadata={"table": table, "row": row_idx},
                        )
                        self.db.insert_migration(record)
                        migrated += 1
                except Exception:
                    pass

            conn.close()
            return migrated, None

        except Exception as e:
            return 0, str(e)


class SemanticMemoryMigrator(BaseMigrator):
    """Migrate semantic_memory.json (322 B)."""

    def __init__(self):
        super().__init__("semantic_memory", NX_OPENMORE_SOURCES["semantic_memory"])

    def exists(self) -> bool:
        return os.path.exists(self.source_path)

    def count_records(self) -> int:
        if not self.exists():
            return 0
        try:
            with open(self.source_path) as f:
                data = json.load(f)
            return len(data) if isinstance(data, dict) else 0
        except Exception:
            return 0

    def migrate(self) -> Tuple[int, Optional[str]]:
        if not self.exists():
            return 0, "Source file not found"

        try:
            with open(self.source_path) as f:
                data = json.load(f)

            migrated = 0
            for concept_id, concept_data in data.items():
                record_id = f"{self.name}_{concept_id}"

                if isinstance(concept_data, dict):
                    content = concept_data.get("description", str(concept_data))
                else:
                    content = str(concept_data)

                record = MigrationRecord(
                    id=record_id,
                    source=self.name,
                    source_type="concept",
                    content=content,
                    metadata=concept_data if isinstance(concept_data, dict) else {},
                )
                self.db.insert_migration(record)
                migrated += 1

            return migrated, None

        except Exception as e:
            return 0, str(e)


# ============================================================================
# N-Xyme_CATALYST Migrators
# ============================================================================


class OpenCodeDBMigrator(BaseMigrator):
    """Migrate opencode.db (3.6 GB - large, chunked processing)."""

    def __init__(self):
        super().__init__("opencode", N_XYME_CATALYST_SOURCES["opencode"])

    def exists(self) -> bool:
        return os.path.exists(self.source_path)

    def count_records(self) -> int:
        if not self.exists():
            return 0
        try:
            conn = sqlite3.connect(self.source_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM message")
            count = cur.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0

    def migrate(
        self, batch_size: int = 1000, limit: int = 10000
    ) -> Tuple[int, Optional[str]]:
        """Migrate opencode.db sessions (chunked)."""
        if not self.exists():
            return 0, "Source file not found"

        try:
            conn = sqlite3.connect(self.source_path)
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) FROM message")
            total = cur.fetchone()[0]
            logger.info(f"Total messages in opencode.db: {total}")

            migrated = 0
            offset = 0

            while offset < min(total, limit):
                cur.execute(
                    """
                    SELECT m.id, m.session_id, m.time_created, p.data
                    FROM message m
                    JOIN part p ON m.id = p.message_id
                    ORDER BY m.id
                    LIMIT ? OFFSET ?
                """,
                    (batch_size, offset),
                )

                rows = cur.fetchall()
                if not rows:
                    break

                for row_idx, row in enumerate(rows):
                    msg_id, session_id, timestamp, data = row
                    record_id = f"opencode_{msg_id}"

                    # Parse data - part table has no type column
                    content = ""
                    try:
                        parsed = json.loads(data)
                        content = parsed.get("text", str(data))
                    except Exception:
                        content = str(data)[:500]

                    # Handle timestamp - may be milliseconds or seconds, or invalid
                    created_at = datetime.now()
                    if (
                        timestamp
                        and isinstance(timestamp, (int, float))
                        and timestamp > 0
                    ):
                        try:
                            if timestamp > 1e12:  # milliseconds
                                created_at = datetime.fromtimestamp(timestamp / 1000)
                            else:
                                created_at = datetime.fromtimestamp(timestamp)
                        except (ValueError, OSError):
                            pass

                    if content and len(content) > 10:
                        record = MigrationRecord(
                            id=record_id,
                            source=self.name,
                            source_type="message",
                            content=content[:2000],
                            metadata={
                                "session_id": str(session_id),
                                "message_id": str(msg_id),
                            },
                            created_at=created_at,
                        )
                        self.db.insert_migration(record)
                        migrated += 1

                offset += batch_size
                logger.info(f"Migrated {migrated} records from opencode.db")

            conn.close()
            return migrated, None

        except Exception as e:
            return 0, str(e)


class NervousSystemMigrator(BaseMigrator):
    """Migrate nervous_system.db (303 KB)."""

    def __init__(self):
        super().__init__("nervous_system", N_XYME_CATALYST_SOURCES["nervous_system"])

    def exists(self) -> bool:
        return os.path.exists(self.source_path)

    def count_records(self) -> int:
        if not self.exists():
            return 0
        try:
            conn = sqlite3.connect(self.source_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM metrics")
            count = cur.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0

    def migrate(self) -> Tuple[int, Optional[str]]:
        if not self.exists():
            return 0, "Source file not found"

        try:
            conn = sqlite3.connect(self.source_path)
            cur = conn.cursor()

            migrated = 0
            tables = [
                "metrics",
                "actions",
                "agent_alerts",
                "metrics_hourly",
                "task_velocity",
                "friction_log",
            ]

            for table in tables:
                try:
                    cur.execute(f"SELECT * FROM {table}")
                    rows = cur.fetchall()
                    for row_idx, row in enumerate(rows):
                        record_id = f"{self.name}_{table}_{row_idx}"
                        content = str(row) if row else ""

                        record = MigrationRecord(
                            id=record_id,
                            source=self.name,
                            source_type=table,
                            content=content,
                            metadata={"table": table, "row": row_idx},
                        )
                        self.db.insert_migration(record)
                        migrated += 1
                except Exception:
                    pass

            conn.close()
            return migrated, None

        except Exception as e:
            return 0, str(e)


class BlockRegistryMigrator(BaseMigrator):
    """Migrate block_registry.db (106 KB)."""

    def __init__(self):
        super().__init__("block_registry", N_XYME_CATALYST_SOURCES["block_registry"])

    def exists(self) -> bool:
        return os.path.exists(self.source_path)

    def count_records(self) -> int:
        if not self.exists():
            return 0
        try:
            conn = sqlite3.connect(self.source_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM blocks")
            count = cur.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0

    def migrate(self) -> Tuple[int, Optional[str]]:
        if not self.exists():
            return 0, "Source file not found"

        try:
            conn = sqlite3.connect(self.source_path)
            cur = conn.cursor()

            cur.execute("SELECT * FROM blocks")
            rows = cur.fetchall()

            migrated = 0
            for row_idx, row in enumerate(rows):
                record_id = f"{self.name}_{row_idx}"
                content = str(row) if row else ""

                record = MigrationRecord(
                    id=record_id,
                    source=self.name,
                    source_type="block",
                    content=content,
                    metadata={"row": row_idx},
                )
                self.db.insert_migration(record)
                migrated += 1

            conn.close()
            return migrated, None

        except Exception as e:
            return 0, str(e)


# ============================================================================
# Transcript Migrator
# ============================================================================


class TranscriptMigrator:
    """Migrate transcripts from nx_openmore context/claude/transcripts/."""

    def __init__(self):
        self.transcripts_path = TRANSCRIPTS_PATH
        self.db = MigrationDB()
        self._engine = None

    def exists(self) -> bool:
        return os.path.isdir(self.transcripts_path)

    def count_transcripts(self) -> int:
        if not self.exists():
            return 0
        try:
            files = [
                f
                for f in os.listdir(self.transcripts_path)
                if f.endswith(".json") or f.endswith(".txt")
            ]
            return len(files)
        except Exception:
            return 0

    def _get_engine(self):
        """Lazy load embedding engine."""
        if self._engine is None:
            try:
                from ..embeddings import get_engine

                self._engine = get_engine()
            except Exception:
                self._engine = None
        return self._engine

    def migrate(self, batch_size: int = 50) -> Tuple[int, Optional[str]]:
        """Migrate transcript files."""
        if not self.exists():
            return 0, "Transcripts directory not found"

        try:
            files = [
                f
                for f in os.listdir(self.transcripts_path)
                if f.endswith(".json") or f.endswith(".txt")
            ]

            migrated = 0
            for file_idx, fname in enumerate(files[:200]):  # Limit for safety
                fpath = os.path.join(self.transcripts_path, fname)

                try:
                    with open(fpath) as f:
                        content = f.read()

                    # Generate embedding if engine available
                    embedding = None
                    engine = self._get_engine()
                    if engine:
                        try:
                            embedding = engine.embed_text(content[:5000])
                        except Exception:
                            pass

                    # Store in DB
                    record_id = f"transcript_{file_idx}"
                    record = MigrationRecord(
                        id=record_id,
                        source="transcripts",
                        source_type="transcript",
                        content=content[:5000],
                        metadata={"file": fname},
                        embedded=embedding is not None,
                        embedding=embedding,
                    )
                    self.db.insert_migration(record)
                    migrated += 1

                except Exception as e:
                    logger.warning(f"Error migrating transcript {fname}: {e}")

                if (file_idx + 1) % batch_size == 0:
                    logger.info(f"Migrated {migrated} transcripts...")

            return migrated, None

        except Exception as e:
            return 0, str(e)


# ============================================================================
# Migration Orchestrator
# ============================================================================


class MigrationOrchestrator:
    """Orchestrates all memory migrations."""

    def __init__(self):
        self.db = MigrationDB()
        self.migrators: List[BaseMigrator] = []
        self._register_migrators()

    def _register_migrators(self):
        """Register all source migrators."""
        # nx_openmore migrators
        self.migrators.append(MindFromMindMigrator())
        self.migrators.append(JarvisMemoryMigrator())
        self.migrators.append(JarvisEventsMigrator())
        self.migrators.append(NXMFromMindMigrator())
        self.migrators.append(SemanticMemoryMigrator())

        # N-Xyme_CATALYST migrators
        self.migrators.append(OpenCodeDBMigrator())
        self.migrators.append(NervousSystemMigrator())
        self.migrators.append(BlockRegistryMigrator())

    def get_status(self) -> Dict[str, MigrationStatus]:
        """Get migration status for all sources."""
        status_dict = {}

        # Check each migrator
        for migrator in self.migrators:
            exists = migrator.exists()
            count = migrator.count_records() if exists else 0

            db_status = self.db.get_status(migrator.name)
            if db_status:
                status_dict[migrator.name] = db_status
            else:
                status_dict[migrator.name] = MigrationStatus(
                    source_name=migrator.name,
                    exists=exists,
                    record_count=count,
                )

        # Check transcript migrator
        transcript_migrator = TranscriptMigrator()
        exists = transcript_migrator.exists()
        count = transcript_migrator.count_transcripts() if exists else 0

        status_dict["transcripts"] = MigrationStatus(
            source_name="transcripts",
            exists=exists,
            record_count=count,
        )

        return status_dict

    def migrate_all(self) -> Dict[str, Tuple[int, Optional[str]]]:
        """Run all migrations."""
        results = {}

        for migrator in self.migrators:
            logger.info(f"Migrating {migrator.name}...")

            exists = migrator.exists()
            count = migrator.count_records() if exists else 0

            status = MigrationStatus(
                source_name=migrator.name,
                exists=exists,
                record_count=count,
                last_attempt=datetime.now(),
            )

            if not exists:
                status.error = "Source not accessible (mount may not be available)"
                results[migrator.name] = (0, status.error)
            else:
                migrated, error = migrator.migrate()
                status.migrated_count = migrated
                status.error = error
                results[migrator.name] = (migrated, error)

            self.db.update_status(status)

        # Migrate transcripts
        logger.info("Migrating transcripts...")
        transcript_migrator = TranscriptMigrator()
        exists = transcript_migrator.exists()

        if not exists:
            results["transcripts"] = (0, "Transcripts directory not accessible")
        else:
            migrated, error = transcript_migrator.migrate()
            results["transcripts"] = (migrated, error)

        return results

    def migrate_source(self, source_name: str) -> Tuple[int, Optional[str]]:
        """Migrate a specific source."""
        for migrator in self.migrators:
            if migrator.name == source_name:
                count, error = migrator.migrate()

                status = MigrationStatus(
                    source_name=source_name,
                    exists=migrator.exists(),
                    record_count=migrator.count_records() if migrator.exists() else 0,
                    migrated_count=count,
                    error=error,
                    last_attempt=datetime.now(),
                )
                self.db.update_status(status)

                return count, error

        return 0, f"Unknown source: {source_name}"


# ============================================================================
# Convenience Functions
# ============================================================================

_orchestrator: Optional[MigrationOrchestrator] = None


def get_orchestrator() -> MigrationOrchestrator:
    """Get the global migration orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MigrationOrchestrator()
    return _orchestrator


def migrate_all() -> Dict[str, Tuple[int, Optional[str]]]:
    """Migrate all sources."""
    return get_orchestrator().migrate_all()


def migrate_source(source_name: str) -> Tuple[int, Optional[str]]:
    """Migrate a specific source."""
    return get_orchestrator().migrate_source(source_name)


def get_migration_status() -> Dict[str, dict]:
    """Get migration status for all sources."""
    status_dict = get_orchestrator().get_status()
    return {
        name: {
            "exists": s.exists,
            "record_count": s.record_count,
            "migrated_count": s.migrated_count,
            "error": s.error,
            "last_attempt": s.last_attempt.isoformat() if s.last_attempt else None,
        }
        for name, s in status_dict.items()
    }


def get_migration_db() -> MigrationDB:
    """Get the migration database."""
    return MigrationDB()


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    # Quick import test
    print("Migration module ready")
