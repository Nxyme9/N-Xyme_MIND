"""Memory Retention Policy — Prevents unbounded database growth.

Manages retention limits for the memory system:
- Archives old memories beyond retention window
- Runs VACUUM to reclaim space
- Reports storage statistics
"""

import logging
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default retention settings
DEFAULT_RETENTION_DAYS = 365  # Keep memories for 1 year
MAX_DB_SIZE_MB = 1024  # 1GB max before forced cleanup
VACUUM_THRESHOLD_MB = 500  # VACUUM if WAL file exceeds this

# Database paths (resolved at runtime)
MEMORY_DB = "context/memory/mind_from_mind.db"
LEARNING_DB = "context/memory/learning.db"
LEARNING_EVENTS_DB = "context/memory/learning_events.db"


def _resolve_db(db_path: str) -> Path:
    """Resolve database path relative to project root."""
    project_root = Path(__file__).resolve().parents[2]
    return project_root / db_path


def get_db_size_mb(db_path: str) -> float:
    """Get database file size in MB."""
    path = _resolve_db(db_path)
    if not path.exists():
        return 0.0
    return path.stat().st_size / (1024 * 1024)


def get_memory_count(db_path: str = MEMORY_DB) -> int:
    """Get total memory count."""
    path = _resolve_db(db_path)
    if not path.exists():
        return 0
    conn = sqlite3.connect(str(path))
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memories")
        return cursor.fetchone()[0]
    except Exception:
        return 0
    finally:
        conn.close()


def archive_old_memories(
    retention_days: int = DEFAULT_RETENTION_DAYS,
    db_path: str = MEMORY_DB,
) -> dict:
    """Archive memories older than retention window.

    Moves old memories to preferences_archive table instead of deleting,
    preserving data while freeing the main table.

    Returns dict with archived count and elapsed time.
    """
    path = _resolve_db(db_path)
    if not path.exists():
        return {"archived": 0, "error": "Database not found"}

    conn = sqlite3.connect(str(path))
    try:
        cursor = conn.cursor()

        # Ensure archive table exists
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS preferences_archive (
                id TEXT PRIMARY KEY,
                content TEXT,
                kind TEXT,
                scope TEXT,
                meta_json TEXT,
                tier TEXT,
                archived_at TEXT
            )
            """
        )

        cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()

        # Archive old memories (those without a created_at, use a heuristic)
        # Since memories table may not have created_at, archive by rowid order
        # keeping the most recent N memories
        cursor.execute("SELECT COUNT(*) FROM memories")
        total = cursor.fetchone()[0]

        # Keep most recent 20000 memories, archive the rest
        keep_count = 20000
        if total <= keep_count:
            return {"archived": 0, "total": total, "reason": "Under retention limit"}

        archive_count = total - keep_count

        # Get oldest memories to archive
        cursor.execute(
            """
            INSERT OR IGNORE INTO preferences_archive
                (id, content, kind, scope, meta_json, tier, archived_at)
            SELECT id, content, kind, scope, meta_json, tier, ?
            FROM memories
            ORDER BY rowid ASC
            LIMIT ?
            """,
            (datetime.now().isoformat(), archive_count),
        )

        # Delete archived memories
        cursor.execute(
            """
            DELETE FROM memories
            WHERE id IN (
                SELECT id FROM memories
                ORDER BY rowid ASC
                LIMIT ?
            )
            """,
            (archive_count,),
        )

        conn.commit()
        return {
            "archived": archive_count,
            "total": total,
            "remaining": keep_count,
        }

    except Exception as e:
        conn.rollback()
        return {"archived": 0, "error": str(e)}
    finally:
        conn.close()


def vacuum_database(db_path: str = MEMORY_DB) -> dict:
    """Run VACUUM to reclaim space from deleted rows.

    Returns dict with before/after sizes.
    """
    path = _resolve_db(db_path)
    if not path.exists():
        return {"error": "Database not found"}

    before_size = get_db_size_mb(db_path)
    start = time.time()

    conn = sqlite3.connect(str(path))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("VACUUM")
        conn.commit()
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

    after_size = get_db_size_mb(db_path)
    elapsed = time.time() - start

    return {
        "before_mb": round(before_size, 1),
        "after_mb": round(after_size, 1),
        "freed_mb": round(before_size - after_size, 1),
        "elapsed_seconds": round(elapsed, 1),
    }


def cleanup_learning_events(max_age_days: int = 90) -> dict:
    """Clean up old learning events.

    Returns dict with deleted count.
    """
    path = _resolve_db(LEARNING_EVENTS_DB)
    if not path.exists():
        return {"deleted": 0, "reason": "Database not found"}

    conn = sqlite3.connect(str(path))
    try:
        cursor = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=max_age_days)).isoformat()

        cursor.execute(
            "DELETE FROM events WHERE timestamp < ?",
            (cutoff,),
        )
        deleted = cursor.rowcount
        conn.commit()

        return {"deleted": deleted, "cutoff": cutoff}
    except Exception as e:
        conn.rollback()
        return {"deleted": 0, "error": str(e)}
    finally:
        conn.close()


def run_full_maintenance(
    retention_days: int = DEFAULT_RETENTION_DAYS,
    max_age_events_days: int = 90,
) -> dict:
    """Run full maintenance: archive, vacuum, cleanup.

    Returns dict with results from each step.
    """
    results = {
        "timestamp": datetime.now().isoformat(),
        "archive": archive_old_memories(retention_days),
        "vacuum": vacuum_database(),
        "learning_cleanup": cleanup_learning_events(max_age_events_days),
    }
    return results


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Memory retention policy manager")
    parser.add_argument("--archive", action="store_true", help="Archive old memories")
    parser.add_argument("--vacuum", action="store_true", help="Vacuum databases")
    parser.add_argument(
        "--cleanup-events", action="store_true", help="Clean old learning events"
    )
    parser.add_argument("--full", action="store_true", help="Run full maintenance")
    parser.add_argument(
        "--retention-days",
        type=int,
        default=DEFAULT_RETENTION_DAYS,
        help=f"Retention window in days (default: {DEFAULT_RETENTION_DAYS})",
    )
    args = parser.parse_args()

    if args.full:
        result = run_full_maintenance(args.retention_days)
        print(f"Archive: {result['archive']}")
        print(f"Vacuum: {result['vacuum']}")
        print(f"Learning cleanup: {result['learning_cleanup']}")
    else:
        if args.archive:
            print(archive_old_memories(args.retention_days))
        if args.vacuum:
            print(vacuum_database())
        if args.cleanup_events:
            print(cleanup_learning_events())
        if not (args.archive or args.vacuum or args.cleanup_events):
            # Just report current state
            print(f"Memory DB size: {get_db_size_mb(MEMORY_DB):.1f} MB")
            print(f"Memory count: {get_memory_count()}")
            print(f"Learning DB size: {get_db_size_mb(LEARNING_DB):.1f} MB")
            print(
                f"Learning events DB size: {get_db_size_mb(LEARNING_EVENTS_DB):.1f} MB"
            )
