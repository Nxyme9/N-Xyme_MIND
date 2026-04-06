#!/usr/bin/env python3
"""
Migrate transcripts from nx_openmore context/claude/transcripts/.

Source: TRANSCRIPTS_ROOT env var or /mnt/Library/nx_openmore/context/claude/transcripts/
- 400+ transcript files (JSON/TXT) to embed and index
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Source path
TRANSCRIPTS_ROOT = os.environ.get("TRANSCRIPTS_ROOT", "/mnt/Library/nx_openmore/context/claude")
TRANSCRIPTS_PATH = f"{TRANSCRIPTS_ROOT}/transcripts"


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
    
    import sqlite3
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
    
    # Transcript index table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transcript_index (
            file_name TEXT PRIMARY KEY,
            file_path TEXT NOT NULL,
            content TEXT,
            embedding BLOB,
            indexed_at TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()


def insert_transcript(file_name: str, file_path: str, content: str,
                     embedding: Optional[List[float]] = None):
    """Insert a transcript record."""
    db_path = get_db_path()
    
    import sqlite3
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        INSERT OR REPLACE INTO transcript_index 
        (file_name, file_path, content, embedding, indexed_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        file_name,
        file_path,
        content[:10000],  # Limit content size
        json.dumps(embedding) if embedding else None,
        datetime.now().isoformat(),
    ))
    
    conn.commit()
    conn.close()


def insert_migration(source: str, source_type: str, content: str, 
                    metadata: Optional[Dict[str, Any]] = None,
                    record_id: Optional[str] = None):
    """Insert a migration record."""
    db_path = get_db_path()
    
    if record_id is None:
        record_id = f"{source}_{datetime.now().timestamp()}"
    
    import sqlite3
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


def get_embedding_engine():
    """Try to get embedding engine."""
    try:
        from ...embeddings import get_engine
        return get_engine()
    except Exception:
        return None


# ============================================================================
# Transcript Migration
# ============================================================================

def list_transcripts() -> List[str]:
    """List all transcript files."""
    if not os.path.isdir(TRANSCRIPTS_PATH):
        return []
    
    transcripts = []
    for fname in os.listdir(TRANSCRIPTS_PATH):
        if fname.endswith('.json') or fname.endswith('.txt'):
            transcripts.append(fname)
    
    return sorted(transcripts)


def migrate_transcript(fname: str, max_content_size: int = 5000) -> Tuple[int, Optional[str]]:
    """Migrate a single transcript file."""
    fpath = os.path.join(TRANSCRIPTS_PATH, fname)
    
    if not os.path.exists(fpath):
        return 0, "File not found"
    
    try:
        content = ""
        
        if fname.endswith('.json'):
            with open(fpath) as f:
                data = json.load(f)
            
            # Extract text content from transcript JSON
            if isinstance(data, dict):
                # Try common transcript structures
                content = data.get("text", "") or data.get("content", "")
                if not content:
                    content = json.dumps(data)[:max_content_size]
            elif isinstance(data, list):
                # List of messages
                texts = []
                for item in data:
                    if isinstance(item, dict):
                        texts.append(item.get("text", str(item)))
                    else:
                        texts.append(str(item))
                content = "\n".join(texts)[:max_content_size]
            else:
                content = str(data)[:max_content_size]
        else:
            # Plain text
            with open(fpath) as f:
                content = f.read()[:max_content_size]
        
        if not content:
            return 0, "No content extracted"
        
        # Try to generate embedding
        embedding = None
        try:
            engine = get_embedding_engine()
            if engine:
                embedding = engine.embed_text(content[:max_content_size])
        except Exception as e:
            logger.debug(f"Embedding failed for {fname}: {e}")
        
        # Insert into both tables
        insert_transcript(fname, fpath, content, embedding)
        
        record_id = f"transcript_{fname}"
        insert_migration(
            source="transcripts",
            source_type="transcript",
            content=content,
            metadata={"file": fname, "path": fpath},
            record_id=record_id,
        )
        
        return 1, None
        
    except Exception as e:
        return 0, str(e)


def migrate_all(batch_size: int = 50, limit: int = 200) -> Dict[str, Tuple[int, Optional[str]]]:
    """Migrate all transcripts."""
    init_migration_db()
    
    transcripts = list_transcripts()
    results = {}
    
    for idx, fname in enumerate(transcripts[:limit]):
        logger.info(f"Migrating transcript {idx+1}/{min(len(transcripts), limit)}: {fname}")
        
        count, error = migrate_transcript(fname)
        results[fname] = (count, error)
        
        if (idx + 1) % batch_size == 0:
            logger.info(f"Batch complete: {idx+1} transcripts processed")
    
    return results


def count_transcripts() -> int:
    """Count available transcripts."""
    return len(list_transcripts())


def check_transcripts_accessible() -> bool:
    """Check if transcripts directory is accessible."""
    return os.path.isdir(TRANSCRIPTS_PATH)


if __name__ == "__main__":
    print("Transcript migration module ready")
    print(f"Transcripts path: {TRANSCRIPTS_PATH}")
    print(f"Accessible: {check_transcripts_accessible()}")
    print(f"Found: {count_transcripts()} transcripts")
