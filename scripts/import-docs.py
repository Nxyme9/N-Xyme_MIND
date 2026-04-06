#!/usr/bin/env python3
"""Import critical N-Xyme_MIND_Docs plans into the memory system.

Reads all markdown files from /home/nxyme/Escritorio/N-Xyme_MIND_Docs/,
chunks them, embeds them, and stores in the existing memory system.
"""

import logging
import os
import sqlite3
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DOCS_DIR = Path("/home/nxyme/Escritorio/N-Xyme_MIND_Docs")
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DB_PATH = PROJECT_ROOT / "context/memory/mind_from_mind.db"
EMBED_DIM = 768
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "nomic-embed-text"

# Track imported docs
IMPORTED_TABLE = "imported_docs"


def init_db():
    """Ensure imported_docs tracking table exists."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {IMPORTED_TABLE} (
            filename TEXT PRIMARY KEY,
            imported_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def is_imported(filename):
    """Check if a doc has already been imported."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        f"SELECT 1 FROM {IMPORTED_TABLE} WHERE filename = ?", (filename,)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None


def mark_imported(filename):
    """Mark a doc as imported."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        f"INSERT OR REPLACE INTO {IMPORTED_TABLE} (filename, imported_at) VALUES (?, ?)",
        (filename, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def embed_text(text):
    """Embed text via Ollama."""
    import httpx

    try:
        resp = httpx.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": OLLAMA_MODEL, "prompt": text},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["embedding"]
    except Exception as e:
        logger.warning(f"Ollama embedding failed: {e}")
        return None


def chunk_document(content, max_chunk_size=2000):
    """Split document into chunks by paragraphs."""
    paragraphs = content.split("\n\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) > max_chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def store_memory(memory_id, kind, content, meta_json, embedding):
    """Store a memory chunk with embedding."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """INSERT OR REPLACE INTO memories
               (id, kind, scope, thread_id, content, created_at, updated_at, meta_json, text, tags, score)
               VALUES (?, 'doc', 'global', ?, ?, ?, ?, ?, ?, NULL, NULL)""",
            (
                memory_id,
                memory_id,
                content[:5000],
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
                meta_json,
                content[:5000],
            ),
        )

        if embedding:
            vec_blob = struct.pack(f"<{EMBED_DIM}f", *embedding)
            conn.execute(
                "INSERT OR REPLACE INTO memory_embeddings VALUES (?, ?, ?, ?)",
                (memory_id, OLLAMA_MODEL, EMBED_DIM, vec_blob),
            )

        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to store memory {memory_id}: {e}")
        return False
    finally:
        conn.close()


def import_doc(filepath):
    """Import a single document."""
    filename = filepath.name
    if is_imported(filename):
        logger.info(f"Skipping already imported: {filename}")
        return 0

    content = filepath.read_text(encoding="utf-8")
    chunks = chunk_document(content)

    imported = 0
    for i, chunk in enumerate(chunks):
        memory_id = f"doc_{filename}_chunk_{i}"
        meta = f'{{"filename": "{filename}", "chunk": {i}, "total_chunks": {len(chunks)}, "source": "nxyme_docs"}}'

        # Embed first chunk (or all if small)
        embedding = None
        if i == 0 or len(chunks) <= 3:
            embedding = embed_text(chunk[:4000])

        if store_memory(memory_id, "doc", chunk, meta, embedding):
            imported += 1

    if imported > 0:
        mark_imported(filename)
        logger.info(f"Imported {filename}: {imported} chunks")

    return imported


def main():
    """Import all critical docs."""
    logger.info(f"Scanning {DOCS_DIR} for markdown files...")

    if not DOCS_DIR.exists():
        logger.error(f"Docs directory not found: {DOCS_DIR}")
        sys.exit(1)

    init_db()

    md_files = sorted(DOCS_DIR.glob("*.md"))
    logger.info(f"Found {len(md_files)} markdown files")

    # Check which need importing
    to_import = [f for f in md_files if not is_imported(f.name)]
    logger.info(f"{len(to_import)} files need importing")

    total_imported = 0
    for i, filepath in enumerate(to_import):
        logger.info(f"[{i + 1}/{len(to_import)}] {filepath.name}")
        count = import_doc(filepath)
        total_imported += count

    # Update knowledge graph
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.memory.knowledge_graph import KnowledgeGraph

        g = KnowledgeGraph()
        for filepath in md_files:
            g.add_entity(
                filepath.stem,
                "document",
                {
                    "path": str(filepath),
                    "size": filepath.stat().st_size,
                    "source": "nxyme_docs",
                },
            )
        g.save()
        logger.info(f"Knowledge graph updated: {g.get_stats()}")
    except Exception as e:
        logger.warning(f"Knowledge graph update failed: {e}")

    logger.info(f"Import complete: {total_imported} chunks from {len(to_import)} files")


if __name__ == "__main__":
    main()
