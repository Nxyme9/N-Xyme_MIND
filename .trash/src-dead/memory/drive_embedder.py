"""Drive file embedding pipeline — indexes files from drives into memory system."""

import logging
import json
import sqlite3
import struct
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "context/memory/mind_from_mind.db"
EMBED_DIM = 768
OLLAMA_MODEL = "nomic-embed-text"


def init_file_tables(db_path: Optional[Path] = None):
    """Create file indexing tables if they don't exist."""
    db = db_path or DB_PATH
    conn = sqlite3.connect(str(db))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_index (
            filepath TEXT PRIMARY KEY,
            file_hash TEXT NOT NULL,
            file_type TEXT,
            drive TEXT,
            size INTEGER,
            mtime REAL,
            indexed_at TEXT,
            chunk_count INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_chunks (
            chunk_id TEXT PRIMARY KEY,
            filepath TEXT REFERENCES file_index(filepath),
            chunk_index INTEGER,
            content TEXT,
            embedding_id TEXT
        )
    """)

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_file_index_hash ON file_index(file_hash)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_file_index_drive ON file_index(drive)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_file_chunks_filepath ON file_chunks(filepath)"
    )

    conn.commit()
    conn.close()


def needs_reindex(
    filepath: str, file_hash: str, db_path: Optional[Path] = None
) -> bool:
    """Check if a file needs re-indexing based on hash."""
    db = db_path or DB_PATH
    conn = sqlite3.connect(str(db))
    cursor = conn.cursor()
    cursor.execute("SELECT file_hash FROM file_index WHERE filepath = ?", (filepath,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return True
    return row[0] != file_hash


def embed_file_content(
    filepath: str,
    content: str,
    file_hash: str,
    file_type: str,
    drive: str,
    file_size: int,
    file_mtime: float,
    db_path: Optional[Path] = None,
) -> dict:
    """Embed a file's content and store in memory system."""
    db = db_path or DB_PATH
    start_time = time.time()

    # Chunk the content
    chunk_size = 4000
    chunks = []
    for i in range(0, len(content), chunk_size):
        chunk = content[i : i + chunk_size]
        if chunk.strip():
            chunks.append(chunk)

    if not chunks:
        return {"filepath": filepath, "chunks": 0, "embedded": 0, "time": 0}

    # Get embedding engine
    try:
        from src.memory.embeddings import get_engine

        engine = get_engine()
    except Exception as e:
        logger.warning(f"Failed to get embedding engine: {e}")
        return {
            "filepath": filepath,
            "chunks": len(chunks),
            "embedded": 0,
            "time": time.time() - start_time,
        }

    conn = sqlite3.connect(str(db))
    cursor = conn.cursor()

    embedded = 0

    for i, chunk in enumerate(chunks):
        chunk_id = f"file_{file_hash[:12]}_chunk_{i}"

        try:
            embedding = engine.embed_text(chunk)
            if embedding:
                vec_blob = struct.pack(f"<{EMBED_DIM}f", *embedding)
                cursor.execute(
                    "INSERT OR REPLACE INTO memory_embeddings (memory_id, model, dim, vec) VALUES (?, ?, ?, ?)",
                    (chunk_id, OLLAMA_MODEL, EMBED_DIM, vec_blob),
                )

                cursor.execute(
                    "INSERT OR REPLACE INTO file_chunks (chunk_id, filepath, chunk_index, content, embedding_id) VALUES (?, ?, ?, ?, ?)",
                    (chunk_id, filepath, i, chunk[:5000], chunk_id),
                )

                cursor.execute(
                    "INSERT OR REPLACE INTO memories (id, kind, scope, content, created_at, updated_at, meta_json, text, tier, archived) VALUES (?, 'file', 'global', ?, ?, ?, ?, ?, 'long_term', 0)",
                    (
                        chunk_id,
                        chunk[:5000],
                        time.strftime("%Y-%m-%dT%H:%M:%S"),
                        time.strftime("%Y-%m-%dT%H:%M:%S"),
                        json.dumps({"filepath": filepath, "type": file_type, "drive": drive, "chunk": i}),
                        chunk[:5000],
                    ),
                )

                embedded += 1
        except Exception as e:
            logger.debug(f"Failed to embed chunk {i} of {filepath}: {e}")

    cursor.execute(
        "INSERT OR REPLACE INTO file_index (filepath, file_hash, file_type, drive, size, mtime, indexed_at, chunk_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            filepath,
            file_hash,
            file_type,
            drive,
            file_size,
            file_mtime,
            time.strftime("%Y-%m-%dT%H:%M:%S"),
            embedded,
        ),
    )

    conn.commit()
    conn.close()

    elapsed = time.time() - start_time
    return {
        "filepath": filepath,
        "chunks": len(chunks),
        "embedded": embedded,
        "time": elapsed,
    }


def get_indexed_count(db_path: Optional[Path] = None) -> dict:
    """Get count of indexed files."""
    db = db_path or DB_PATH
    conn = sqlite3.connect(str(db))
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM file_index")
    total_files = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM file_chunks")
    total_chunks = cursor.fetchone()[0]

    cursor.execute("SELECT drive, COUNT(*) FROM file_index GROUP BY drive")
    by_drive = dict(cursor.fetchall())

    cursor.execute("SELECT file_type, COUNT(*) FROM file_index GROUP BY file_type")
    by_type = dict(cursor.fetchall())

    conn.close()

    return {
        "total_files": total_files,
        "total_chunks": total_chunks,
        "by_drive": by_drive,
        "by_type": by_type,
    }


def init_chroma(db_path: str = "context/memory/file_chroma"):
    """Initialize ChromaDB collection for file embeddings.
    
    Args:
        db_path: Path to ChromaDB storage directory.
        
    Returns:
        ChromaDB collection object.
    """
    import chromadb
    from pathlib import Path
    
    client = chromadb.PersistentClient(path=str(Path(db_path)))
    collection = client.get_or_create_collection(
        name="file_embeddings",
        metadata={
            "hnsw:space": "cosine",
            "hnsw:construction_ef": 200,
            "hnsw:search_ef": 50,
            "hnsw:M": 32,
        }
    )
    return collection
