#!/usr/bin/env python3
"""
Auto-Embed Pipeline — Automatic embedding of memories.

Provides:
- embed_memory(memory_id, content): Embed single memory via Ollama
- embed_batch(memory_ids_and_contents): Embed multiple in batches
- auto_embed_on_save(memory_id, content): Check if embedded, embed if not
- backfill_missing_embeddings(): Scan and embed memories without embeddings

Uses Ollama (nomic-embed-text, 768 dims) with non-blocking threading.
Graceful degradation if Ollama unavailable.
"""

import logging
import os
import queue
import sqlite3
import struct
import threading
from pathlib import Path
from typing import List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "nomic-embed-text"
DB_PATH = Path(os.environ.get("NX_MIND_DB_PATH", str(Path(__file__).parent.parent.parent / "context/memory/mind_from_mind.db")))
EMBED_DIM = 768

_pending_embedding_queue: queue.Queue = queue.Queue()
_embedding_thread: Optional[threading.Thread] = None
_ollama_available: bool = True


def _get_db_connection() -> sqlite3.Connection:
    """Get DB connection."""
    return sqlite3.connect(DB_PATH)


def _check_ollama_available() -> bool:
    """Check if Ollama is running."""
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{OLLAMA_URL}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


def _embed_via_ollama(text: str) -> Optional[List[float]]:
    """Generate embedding via Ollama /api/embeddings endpoint."""
    try:
        # Truncate to 2048 chars (safer limit for embedding models)
        truncated = text[:2048]
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": OLLAMA_MODEL, "prompt": truncated},
            )
            resp.raise_for_status()
            data = resp.json()
            embedding = data.get("embedding")
            if embedding and len(embedding) == EMBED_DIM:
                return embedding
    except Exception as e:
        logger.debug(f"Ollama embedding failed: {e}")
    return None


def _save_embedding_to_db(memory_id: str, embedding: List[float]) -> bool:
    """Save embedding to memory_embeddings table."""
    try:
        vec_blob = struct.pack(f"<{EMBED_DIM}f", *embedding)
        conn = _get_db_connection()
        conn.execute(
            "INSERT OR REPLACE INTO memory_embeddings (memory_id, model, dim, vec) VALUES (?, ?, ?, ?)",
            (memory_id, OLLAMA_MODEL, EMBED_DIM, vec_blob),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to save embedding for {memory_id}: {e}")
        return False


def _has_existing_embedding(memory_id: str) -> bool:
    """Check if memory already has an embedding."""
    try:
        conn = _get_db_connection()
        cursor = conn.execute(
            "SELECT 1 FROM memory_embeddings WHERE memory_id = ?",
            (memory_id,),
        )
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception:
        return False


def embed_memory(memory_id: str, content: str) -> bool:
    """
    Embed a single memory via Ollama.

    Args:
        memory_id: Unique identifier for the memory
        content: Text content to embed

    Returns:
        True if embedding was successful, False otherwise
    """
    global _ollama_available

    if not _ollama_available:
        if not _check_ollama_available():
            logger.warning(f"Ollama unavailable, cannot embed memory {memory_id}")
            _pending_embedding_queue.put((memory_id, content))
            return False
        _ollama_available = True

    embedding = _embed_via_ollama(content)
    if embedding is None:
        logger.warning(f"Failed to generate embedding for {memory_id}")
        _ollama_available = False
        _pending_embedding_queue.put((memory_id, content))
        return False

    success = _save_embedding_to_db(memory_id, embedding)
    if success:
        logger.info(f"Embedded memory {memory_id}")
    return success


def embed_batch(
    memory_ids_and_contents: List[Tuple[str, str]], batch_size: int = 10
) -> int:
    """
    Embed multiple memories in batches.

    Args:
        memory_ids_and_contents: List of (memory_id, content) tuples
        batch_size: Number of memories to process per batch

    Returns:
        Number of successfully embedded memories
    """
    global _ollama_available

    if not _ollama_available:
        if not _check_ollama_available():
            logger.warning("Ollama unavailable, queueing batch for later")
            for memory_id, content in memory_ids_and_contents:
                _pending_embedding_queue.put((memory_id, content))
            return 0
        _ollama_available = True

    success_count = 0
    for i in range(0, len(memory_ids_and_contents), batch_size):
        batch = memory_ids_and_contents[i : i + batch_size]
        for memory_id, content in batch:
            embedding = _embed_via_ollama(content)
            if embedding is None:
                logger.warning(f"Failed to generate embedding for {memory_id}")
                _ollama_available = False
                continue
            if _save_embedding_to_db(memory_id, embedding):
                success_count += 1

    logger.info(
        f"Batch complete: {success_count}/{len(memory_ids_and_contents)} embedded"
    )
    return success_count


def auto_embed_on_save(memory_id: str, content: str) -> bool:
    """
    Convenience wrapper: check if already embedded, embed if not.

    Args:
        memory_id: Unique identifier for the memory
        content: Text content to embed

    Returns:
        True if already had embedding or was successfully embedded, False on failure
    """
    if _has_existing_embedding(memory_id):
        logger.debug(f"Memory {memory_id} already has embedding, skipping")
        return True

    return embed_memory(memory_id, content)


def backfill_missing_embeddings(batch_size: int = 20, max_memories: Optional[int] = None) -> dict[str, int]:
    """
    Scan for memories without embeddings and embed them.

    Args:
        batch_size: Number of memories to process per batch
        max_memories: Optional limit on total memories to process

    Returns:
        dict with statistics: processed, success, failed, remaining
    """
    stats = {"processed": 0, "success": 0, "failed": 0, "remaining": 0}
    start_time = None
    
    try:
        conn = _get_db_connection()
        
        # First, get count of memories without embeddings
        cursor = conn.execute(
            """
            SELECT COUNT(*) FROM memories m
            LEFT JOIN memory_embeddings e ON m.id = e.memory_id
            WHERE e.memory_id IS NULL 
              AND m.content IS NOT NULL 
              AND length(m.content) > 10
            """
        )
        stats["remaining"] = cursor.fetchone()[0]
        conn.close()
        
        if stats["remaining"] == 0:
            logger.info("No memories need embedding")
            return stats
        
        logger.info(f"Found {stats['remaining']} memories without embeddings")
        start_time = __import__("time").time()
        
        while True:
            # Check if we've hit the max_memories limit
            if max_memories and stats["processed"] >= max_memories:
                break
                
            conn = _get_db_connection()
            cursor = conn.execute(
                """
                SELECT m.id, m.content FROM memories m
                LEFT JOIN memory_embeddings e ON m.id = e.memory_id
                WHERE e.memory_id IS NULL 
                  AND m.content IS NOT NULL 
                  AND length(m.content) > 10
                LIMIT ?
                """,
                (batch_size,),
            )
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                break

            memory_ids_and_contents = [(row[0], row[1]) for row in rows]
            
            # Track individual results
            for memory_id, content in memory_ids_and_contents:
                stats["processed"] += 1
                try:
                    if embed_memory(memory_id, content):
                        stats["success"] += 1
                    else:
                        stats["failed"] += 1
                except Exception as e:
                    logger.error(f"Failed to embed {memory_id}: {e}")
                    stats["failed"] += 1
                
                # Progress report every 50
                if stats["processed"] % 50 == 0:
                    elapsed = __import__("time").time() - start_time if start_time else 0
                    logger.info(
                        f"Progress: {stats['processed']}/{stats['remaining']} processed, "
                        f"{stats['success']} success, {stats['failed']} failed, "
                        f"{elapsed:.1f}s elapsed"
                    )

        # Final statistics
        elapsed = __import__("time").time() - start_time if start_time else 0
        stats["elapsed_seconds"] = round(elapsed, 1)
        
        # Update remaining count
        conn = _get_db_connection()
        cursor = conn.execute(
            """
            SELECT COUNT(*) FROM memories m
            LEFT JOIN memory_embeddings e ON m.id = e.memory_id
            WHERE e.memory_id IS NULL 
              AND m.content IS NOT NULL 
              AND length(m.content) > 10
            """
        )
        stats["remaining"] = cursor.fetchone()[0]
        conn.close()

        logger.info(
            f"Backfill complete: {stats['processed']} processed, "
            f"{stats['success']} success, {stats['failed']} failed, "
            f"{stats['remaining']} remaining, {elapsed:.1f}s"
        )
        return stats

    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        return stats


_shutdown_event = threading.Event()


def _embedding_worker():
    """Background worker that processes queued embeddings."""
    while not _shutdown_event.is_set():
        try:
            memory_id, content = _pending_embedding_queue.get(timeout=5)
            logger.info(f"Processing queued embedding for {memory_id}")
            embed_memory(memory_id, content)
            _pending_embedding_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Embedding worker error: {e}")


def start_background_embedding():
    """Start the background embedding thread."""
    global _embedding_thread
    if _embedding_thread is None or not _embedding_thread.is_alive():
        _embedding_thread = threading.Thread(target=_embedding_worker, daemon=True)
        _embedding_thread.start()
        logger.info("Background embedding thread started")


def stop_background_embedding():
    """Signal the background embedding thread to stop gracefully."""
    global _embedding_thread
    _shutdown_event.set()
    if _embedding_thread and _embedding_thread.is_alive():
        _embedding_thread.join(timeout=10)
        logger.info("Background embedding thread stopped")


# ---------------------------------------------------------------------------
# Forgetting Curve Integration — Ebbinghaus decay for memory archival
# ---------------------------------------------------------------------------


def apply_forgetting_curve(db_path: str = DB_PATH, threshold: float = 0.2,
                           dry_run: bool = True) -> dict:
    """Apply Ebbinghaus forgetting curve to identify stale memories.

    Memories with retrievability below threshold are marked for archival
    or re-embedding review.

    Args:
        db_path: Path to the memory database
        threshold: Retrievability threshold below which memory is stale
        dry_run: If True, only report what would be archived

    Returns:
        dict with counts of stale, archived, and reviewed memories
    """
    from src.memory.core.forgetting import ForgettingCurve, ebbinghaus_retrievability

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all memories with embeddings and their timestamps
    cursor.execute("""
        SELECT me.memory_id, m.created_at, m.updated_at
        FROM memory_embeddings me
        LEFT JOIN memories m ON me.memory_id = m.id
        WHERE m.created_at IS NOT NULL
    """)

    fc = ForgettingCurve()
    stale_memories = []
    total_checked = 0

    for memory_id, created_at, updated_at in cursor.fetchall():
        total_checked += 1
        try:
            # Calculate age in days
            from datetime import datetime, timezone
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            age_seconds = (datetime.now(timezone.utc) - dt).total_seconds()
            age_days = age_seconds / 86400

            # Calculate retrievability using Ebbinghaus curve
            # Stability defaults to 30 days for unreviewed memories
            stability_days = 30.0
            retrievability = ebbinghaus_retrievability(age_days, stability_days)

            if retrievability < threshold:
                stale_memories.append({
                    "memory_id": memory_id,
                    "age_days": round(age_days, 1),
                    "retrievability": round(retrievability, 3),
                })
        except Exception:
            continue

    # Archive stale memories if not dry run
    archived_count = 0
    if not dry_run and stale_memories:
        for mem in stale_memories:
            try:
                cursor.execute(
                    "UPDATE memories SET archived = 1 WHERE id = ?",
                    (mem["memory_id"],)
                )
                archived_count += 1
            except Exception:
                continue
        conn.commit()

    conn.close()

    result = {
        "total_checked": total_checked,
        "stale_count": len(stale_memories),
        "archived_count": archived_count,
        "threshold": threshold,
        "dry_run": dry_run,
        "stale_samples": stale_memories[:10],  # First 10 for review
    }

    logger.info(
        f"Forgetting curve: {total_checked} checked, "
        f"{len(stale_memories)} stale, {archived_count} archived "
        f"(threshold={threshold}, dry_run={dry_run})"
    )
    return result

def get_pending_count() -> int:
    """Get count of pending embeddings in queue."""
    return _pending_embedding_queue.qsize()


def main():
    """Standalone entry point for the embedding pipeline."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="Auto-embed pipeline")
    parser.add_argument(
        "command",
        choices=["backfill", "status"],
        help="Command to run",
    )
    args = parser.parse_args()

    if args.command == "backfill":
        start_background_embedding()
        # Run backfill - now returns dict with statistics
        stats = backfill_missing_embeddings(batch_size=20)
        logger.info(f"Backfill complete: {stats['processed']} processed, "
                    f"{stats['success']} success, {stats['failed']} failed, "
                    f"{stats['remaining']} remaining, {stats.get('elapsed_seconds', 0)}s")
        print(f"\n=== Backfill Statistics ===")
        print(f"Processed: {stats['processed']}")
        print(f"Success:   {stats['success']}")
        print(f"Failed:    {stats['failed']}")
        print(f"Remaining: {stats['remaining']}")
        print(f"Time:      {stats.get('elapsed_seconds', 'N/A')}s")

    elif args.command == "status":
        ollama_status = "available" if _check_ollama_available() else "unavailable"
        conn = _get_db_connection()
        cursor = conn.execute("SELECT COUNT(*) FROM memory_embeddings")
        embedded_count = cursor.fetchone()[0]
        cursor = conn.execute("SELECT COUNT(*) FROM memories")
        total_memories = cursor.fetchone()[0]
        conn.close()
        pending = get_pending_count()

        print(f"Ollama: {ollama_status}")
        print(f"Embedded: {embedded_count}/{total_memories}")
        print(f"Pending queue: {pending}")


if __name__ == "__main__":
    main()
