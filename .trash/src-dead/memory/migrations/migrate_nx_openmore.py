#!/usr/bin/env python3
"""
Migrate nx_openmore memory databases.

Source: NX_OPENMORE_ROOT env var or /mnt/Library/nx_openmore/context/memory/
- mind_from_mind.db (2.1 MB) - Primary mind state
- jarvis_memory.db (28 KB) - JARVIS agent memory  
- jarvis_events.db (20 KB) - Event logs
- nxm_from_mind.db (68 KB) - NXM state
- semantic_memory.json (322 B) - Semantic memory
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
NX_OPENMORE_ROOT = os.environ.get("NX_OPENMORE_ROOT", "/mnt/Library/nx_openmore")
MEMORY_PATH = f"{NX_OPENMORE_ROOT}/context/memory"

# Source DB paths
SOURCES = {
    "mind_from_mind": f"{MEMORY_PATH}/mind_from_mind.db",
    "jarvis_memory": f"{MEMORY_PATH}/jarvis_memory.db",
    "jarvis_events": f"{MEMORY_PATH}/jarvis_events.db",
    "nxm_from_mind": f"{MEMORY_PATH}/nxm_from_mind.db",
    "semantic_memory": f"{MEMORY_PATH}/semantic_memory.json",
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
    
    # nx_openmore specific table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nx_openmore_migrations (
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

def migrate_mind_from_mind() -> Tuple[int, Optional[str]]:
    """Migrate mind_from_mind.db (2.1 MB)."""
    db_path = SOURCES["mind_from_mind"]
    
    if not os.path.exists(db_path):
        return 0, "Source DB not found"
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Get all tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall()]
        
        migrated = 0
        for table in tables:
            try:
                cur.execute(f"SELECT * FROM {table} LIMIT 100")
                rows = cur.fetchall()
                
                for row_idx, row in enumerate(rows):
                    record_id = f"mind_from_mind_{table}_{row_idx}"
                    content = str(row)
                    
                    insert_migration(
                        source="nx_openmore",
                        source_type=f"mind_{table}",
                        content=content,
                        metadata={"table": table, "row": row_idx},
                        record_id=record_id,
                    )
                    migrated += 1
                    
            except Exception as e:
                logger.warning(f"Error migrating table {table}: {e}")
        
        conn.close()
        return migrated, None
        
    except Exception as e:
        return 0, str(e)


def migrate_jarvis_memory() -> Tuple[int, Optional[str]]:
    """Migrate jarvis_memory.db (28 KB)."""
    db_path = SOURCES["jarvis_memory"]
    
    if not os.path.exists(db_path):
        return 0, "Source DB not found"
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Try different table names
        table_names = ["memories", "memory", "jarvis_memory"]
        migrated = 0
        
        for table in table_names:
            try:
                cur.execute(f"SELECT * FROM {table}")
                rows = cur.fetchall()
                
                for row_idx, row in enumerate(rows):
                    record_id = f"jarvis_memory_{row_idx}"
                    content = str(row)
                    
                    insert_migration(
                        source="nx_openmore",
                        source_type="jarvis_memory",
                        content=content,
                        metadata={"table": table, "row": row_idx},
                        record_id=record_id,
                    )
                    migrated += 1
                    
                break  # Found valid table
            except Exception:
                continue
        
        conn.close()
        return migrated, None
        
    except Exception as e:
        return 0, str(e)


def migrate_jarvis_events() -> Tuple[int, Optional[str]]:
    """Migrate jarvis_events.db (20 KB)."""
    db_path = SOURCES["jarvis_events"]
    
    if not os.path.exists(db_path):
        return 0, "Source DB not found"
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        table_names = ["events", "event_log", "jarvis_events"]
        migrated = 0
        
        for table in table_names:
            try:
                cur.execute(f"SELECT * FROM {table}")
                rows = cur.fetchall()
                
                for row_idx, row in enumerate(rows):
                    record_id = f"jarvis_events_{row_idx}"
                    content = str(row)
                    
                    insert_migration(
                        source="nx_openmore",
                        source_type="jarvis_event",
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


def migrate_nxm_from_mind() -> Tuple[int, Optional[str]]:
    """Migrate nxm_from_mind.db (68 KB)."""
    db_path = SOURCES["nxm_from_mind"]
    
    if not os.path.exists(db_path):
        return 0, "Source DB not found"
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        table_names = ["nxm_state", "state", "nxm_from_mind"]
        migrated = 0
        
        for table in table_names:
            try:
                cur.execute(f"SELECT * FROM {table}")
                rows = cur.fetchall()
                
                for row_idx, row in enumerate(rows):
                    record_id = f"nxm_from_mind_{row_idx}"
                    content = str(row)
                    
                    insert_migration(
                        source="nx_openmore",
                        source_type="nxm_state",
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


def migrate_semantic_memory() -> Tuple[int, Optional[str]]:
    """Migrate semantic_memory.json (322 B)."""
    json_path = SOURCES["semantic_memory"]
    
    if not os.path.exists(json_path):
        return 0, "Source JSON not found"
    
    try:
        with open(json_path) as f:
            data = json.load(f)
        
        migrated = 0
        for concept_id, concept_data in data.items():
            record_id = f"semantic_{concept_id}"
            
            if isinstance(concept_data, dict):
                content = concept_data.get("description", str(concept_data))
            else:
                content = str(concept_data)
            
            insert_migration(
                source="nx_openmore",
                source_type="semantic_concept",
                content=content,
                metadata=concept_data if isinstance(concept_data, dict) else {},
                record_id=record_id,
            )
            migrated += 1
        
        return migrated, None
        
    except Exception as e:
        return 0, str(e)


# ============================================================================
# Main Migration Functions
# ============================================================================

def migrate_all() -> Dict[str, Tuple[int, Optional[str]]]:
    """Run all nx_openmore migrations."""
    init_migration_db()
    
    results = {
        "mind_from_mind": migrate_mind_from_mind(),
        "jarvis_memory": migrate_jarvis_memory(),
        "jarvis_events": migrate_jarvis_events(),
        "nxm_from_mind": migrate_nxm_from_mind(),
        "semantic_memory": migrate_semantic_memory(),
    }
    
    return results


def check_sources() -> Dict[str, bool]:
    """Check which sources are accessible."""
    return {
        name: os.path.exists(path) 
        for name, path in SOURCES.items()
    }


def get_record_counts() -> Dict[str, int]:
    """Get estimated record counts for each source."""
    counts = {}
    
    for name, path in SOURCES.items():
        if not os.path.exists(path):
            counts[name] = 0
            continue
        
        if path.endswith(".json"):
            try:
                with open(path) as f:
                    data = json.load(f)
                counts[name] = len(data) if isinstance(data, dict) else 0
            except Exception:
                counts[name] = 0
        else:
            try:
                conn = sqlite3.connect(path)
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                tables = cur.fetchone()[0]
                conn.close()
                counts[name] = tables * 100  # Estimate
            except Exception:
                counts[name] = 0
    
    return counts


if __name__ == "__main__":
    # Test imports
    print("nx_openmore migration module ready")
    print(f"Sources: {list(SOURCES.keys())}")
