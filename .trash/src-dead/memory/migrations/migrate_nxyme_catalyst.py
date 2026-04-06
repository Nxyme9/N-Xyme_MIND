#!/usr/bin/env python3
"""
Migrate N-Xyme_CATALYST memory databases.

Source: /mnt/NXYME_CORE/01_CODING/00_N-Xyme_CATALYST/data/
- opencode.db (3.6 GB) - OpenCode sessions
- nervous_system.db (303 KB) - System state
- block_registry.db (106 KB) - Trigger blocks
- mind-data/ (2.9 GB) - MIND system data
"""

import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Source paths
CATALYST_ROOT = "/mnt/NXYME_CORE/01_CODING/00_N-Xyme_CATALYST"
DATA_PATH = f"{CATALYST_ROOT}/data"

# Source paths
SOURCES = {
    "opencode": f"{DATA_PATH}/opencode/opencode.db",
    "nervous_system": f"{DATA_PATH}/nervous_system.db",
    "block_registry": f"{DATA_PATH}/block_registry.db",
    "mind_data": f"{DATA_PATH}/mind-data",
}


def get_db_path() -> str:
    """Get unified migration DB path."""
    return os.environ.get("MEMORY_DB_PATH", "./data/memory_migration.db")


def ensure_db_dir():
    """Ensure database directory exists."""
    db_path = get_db_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)


def init_migration_db():
    """Initialize migration database."""
    db_path = get_db_path()
    ensure_db_dir()
    
    conn = sqlite3.connect(db_path)
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
    
    # Catalyst specific table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS catalyst_migrations (
            id TEXT PRIMARY KEY,
            source_db TEXT NOT NULL,
            table_name TEXT,
            content TEXT NOT NULL,
            metadata TEXT,
            migrated_at TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()


def insert_migration(source: str, source_type: str, content: str, 
                    metadata: Optional[Dict[str, Any]] = None,
                    record_id: Optional[str] = None):
    """Insert a migration record."""
    db_path = get_db_path()
    
    if record_id is None:
        record_id = f"{source}_{datetime.now().timestamp()}"
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        INSERT OR REPLACE INTO migrations 
        (id, source, source_type, content, metadata, embedded, migrated_at)
        VALUES (?, ?, ?, ?, ?, 0, ?)
    """, (
        record_id,
        source,
        source_type,
        content,
        json.dumps(metadata or {}),
        datetime.now().isoformat(),
    ))
    
    conn.commit()
    conn.close()


# ============================================================================
# Individual Source Migrators
# ============================================================================

def migrate_opencode() -> Tuple[int, Optional[str]]:
    """Migrate opencode.db (3.6 GB - large, chunked processing)."""
    db_path = SOURCES["opencode"]
    
    if not os.path.exists(db_path):
        return 0, "Source DB not found"
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Get message count
        cur.execute("SELECT COUNT(*) FROM message")
        total = cur.fetchone()[0]
        logger.info(f"Total messages in opencode.db: {total}")
        
        # Chunk through messages
        migrated = 0
        batch_size = 1000
        limit = 10000  # Safety limit
        offset = 0
        
        while offset < min(total, limit):
            cur.execute("""
                SELECT m.id, m.session_id, m.time_created, p.data, p.type
                FROM message m
                JOIN part p ON m.id = p.message_id
                ORDER BY m.id
                LIMIT ? OFFSET ?
            """, (batch_size, offset))
            
            rows = cur.fetchall()
            if not rows:
                break
            
            for row_idx, row in enumerate(rows):
                msg_id, session_id, timestamp, data, ptype = row
                record_id = f"opencode_{msg_id}"
                
                # Parse data based on type
                content = ""
                try:
                    if ptype == "text":
                        parsed = json.loads(data)
                        content = parsed.get("text", str(data))
                    else:
                        content = str(data)[:500]
                except Exception:
                    content = str(data)[:500]
                
                if content and len(content) > 10:
                    insert_migration(
                        source="catalyst",
                        source_type="message",
                        content=content[:2000],
                        metadata={
                            "session_id": str(session_id),
                            "message_id": str(msg_id),
                            "part_type": str(ptype),
                        },
                        record_id=record_id,
                    )
                    migrated += 1
            
            offset += batch_size
            logger.info(f"Migrated {migrated} records from opencode.db")
        
        conn.close()
        return migrated, None
        
    except Exception as e:
        return 0, str(e)


def migrate_nervous_system() -> Tuple[int, Optional[str]]:
    """Migrate nervous_system.db (303 KB)."""
    db_path = SOURCES["nervous_system"]
    
    if not os.path.exists(db_path):
        return 0, "Source DB not found"
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Try different table names
        table_names = ["system_state", "state", "nervous_system"]
        migrated = 0
        
        for table in table_names:
            try:
                cur.execute(f"SELECT * FROM {table}")
                rows = cur.fetchall()
                
                for row_idx, row in enumerate(rows):
                    record_id = f"nervous_system_{row_idx}"
                    content = str(row)
                    
                    insert_migration(
                        source="catalyst",
                        source_type="system_state",
                        content=content,
                        metadata={"table": table, "row": row_idx},
                        record_id=record_id,
                    )
                    migrated += 1
                    
                break
            except Exception:
                continue
        
        conn.close()
        return migrated, None
        
    except Exception as e:
        return 0, str(e)


def migrate_block_registry() -> Tuple[int, Optional[str]]:
    """Migrate block_registry.db (106 KB)."""
    db_path = SOURCES["block_registry"]
    
    if not os.path.exists(db_path):
        return 0, "Source DB not found"
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        table_names = ["blocks", "block_registry", "blocks_registry"]
        migrated = 0
        
        for table in table_names:
            try:
                cur.execute(f"SELECT * FROM {table}")
                rows = cur.fetchall()
                
                for row_idx, row in enumerate(rows):
                    record_id = f"block_registry_{row_idx}"
                    content = str(row)
                    
                    insert_migration(
                        source="catalyst",
                        source_type="block",
                        content=content,
                        metadata={"table": table, "row": row_idx},
                        record_id=record_id,
                    )
                    migrated += 1
                    
                break
            except Exception:
                continue
        
        conn.close()
        return migrated, None
        
    except Exception as e:
        return 0, str(e)


def migrate_mind_data() -> Tuple[int, Optional[str]]:
    """Migrate mind-data/ directory (2.9 GB)."""
    data_path = SOURCES["mind_data"]
    
    if not os.path.isdir(data_path):
        return 0, "Source directory not found"
    
    migrated = 0
    
    try:
        # Walk through mind-data directory
        for root, dirs, files in os.walk(data_path):
            for fname in files:
                fpath = os.path.join(root, fname)
                
                try:
                    # Try to read as JSON
                    with open(fpath) as f:
                        data = json.load(f)
                    
                    content = json.dumps(data)[:2000]
                    
                    record_id = f"mind_data_{fname}"
                    insert_migration(
                        source="catalyst",
                        source_type="mind_data",
                        content=content,
                        metadata={"file": fname, "path": fpath},
                        record_id=record_id,
                    )
                    migrated += 1
                    
                except Exception:
                    # Try as text
                    try:
                        with open(fpath) as f:
                            content = f.read()[:2000]
                        
                        record_id = f"mind_data_{fname}"
                        insert_migration(
                            source="catalyst",
                            source_type="mind_data",
                            content=content,
                            metadata={"file": fname, "path": fpath},
                            record_id=record_id,
                        )
                        migrated += 1
                    except Exception:
                        pass
                
                # Safety limit
                if migrated >= 5000:
                    break
            
            if migrated >= 5000:
                break
    
    except Exception as e:
        return migrated, str(e)
    
    return migrated, None


# ============================================================================
# Main Migration Functions
# ============================================================================

def migrate_all() -> Dict[str, Tuple[int, Optional[str]]]:
    """Run all N-Xyme_CATALYST migrations."""
    init_migration_db()
    
    results = {
        "opencode": migrate_opencode(),
        "nervous_system": migrate_nervous_system(),
        "block_registry": migrate_block_registry(),
        "mind_data": migrate_mind_data(),
    }
    
    return results


def check_sources() -> Dict[str, bool]:
    """Check which sources are accessible."""
    result = {}
    for name, path in SOURCES.items():
        if name == "mind_data":
            result[name] = os.path.isdir(path)
        else:
            result[name] = os.path.exists(path)
    return result


def get_record_counts() -> Dict[str, int]:
    """Get estimated record counts for each source."""
    counts = {}
    
    for name, path in SOURCES.items():
        if not os.path.exists(path):
            if name == "mind_data":
                counts[name] = 0 if not os.path.isdir(path) else 1000
            else:
                counts[name] = 0
            continue
        
        if name == "mind_data" and os.path.isdir(path):
            try:
                counts[name] = sum(1 for _ in os.walk(path))
            except Exception:
                counts[name] = 0
        else:
            try:
                conn = sqlite3.connect(path)
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM message")
                counts[name] = cur.fetchone()[0]
                conn.close()
            except Exception:
                counts[name] = 0
    
    return counts


if __name__ == "__main__":
    print("N-Xyme_CATALYST migration module ready")
    print(f"Sources: {list(SOURCES.keys())}")
