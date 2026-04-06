#!/usr/bin/env python3
"""
Cleanup Module — Remove deleted files and stale embeddings from index.

Provides:
- cleanup_deleted_files(): Remove files from registry that no longer exist
- cleanup_stale_embeddings(): Remove orphaned embeddings (no corresponding file)
- get_cleanup_stats(): Return cleanup statistics
- cleanup_all(): Run all cleanup operations

Connects to file_registry.py (SQLite) and file_embedder.py (ChromaDB + SQLite).
"""

import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Any
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default drives to check (configurable via env vars)
DEFAULT_DRIVES = [
    os.environ.get("NX_DRIVE_LIBRARY", "/mnt/Library"),
    os.environ.get("NX_DRIVE_WIN_LIBRARY", "/mnt/WIN_LIBRARY"),
    os.environ.get("NX_DRIVE_NXYME_CORE", "/mnt/NXYME_CORE"),
    os.environ.get("NX_DRIVE_NXYME_IMAGES", "/mnt/NXYME_IMAGES"),
    os.environ.get("NX_DRIVE_BACKUP", "/mnt/backup"),
]

# Default database paths
DEFAULT_REGISTRY_DB = "context/memory/memory.db"
DEFAULT_EMBED_DB = "context/memory/file_chroma"
SQLITE_TABLE = "file_chunks"


def _get_db_connection(db_path: str) -> sqlite3.Connection:
    """Get SQLite connection with WAL mode and proper settings."""
    project_root = Path(__file__).parent.parent.parent
    full_path = project_root / db_path

    conn = sqlite3.connect(str(full_path), timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def _get_sqlite_path(db_path: str) -> Path:
    """Get SQLite database path for file_chunks."""
    project_root = Path(__file__).parent.parent.parent
    return project_root / db_path / "file_chunks.db"


def _init_chroma(db_path: str = DEFAULT_EMBED_DB):
    """Initialize ChromaDB client."""
    import chromadb

    project_root = Path(__file__).parent.parent.parent
    chroma_path = project_root / db_path

    if not chroma_path.exists():
        return None

    client = chromadb.PersistentClient(path=str(chroma_path))
    try:
        collection = client.get_or_create_collection(name="file_embeddings")
        return collection
    except Exception:
        return None


def cleanup_deleted_files(
    db_path: str = DEFAULT_REGISTRY_DB,
    drives: list[str] | None = None,
    batch_size: int = 100,
) -> dict[str, Any]:
    """
    Remove files from registry that no longer exist on disk.

    Args:
        db_path: Path to SQLite registry database.
        drives: List of drive paths to check (None = use defaults).
        batch_size: Number of files to delete per batch.

    Returns:
        Dictionary with:
        - files_removed: Number of files removed from registry
        - errors: List of error messages
        - duration_seconds: Time taken
        - checked_files: Number of files checked
    """
    start_time = time.time()
    drives = drives or DEFAULT_DRIVES

    files_removed = 0
    errors = []
    checked_files = 0

    # Valid drive prefixes (for filtering registry entries)
    valid_prefixes = tuple(
        drive.rstrip("/") + "/" for drive in drives if os.path.exists(drive)
    )

    try:
        conn = _get_db_connection(db_path)

        # Get all files from registry
        cursor = conn.execute("SELECT file_path FROM file_registry")
        all_files = [row[0] for row in cursor.fetchall()]
        conn.close()

        checked_files = len(all_files)

        # Group files by existence check
        files_to_remove = []
        for filepath in all_files:
            try:
                if not os.path.exists(filepath):
                    files_to_remove.append(filepath)
            except Exception as e:
                logger.debug(f"Error checking {filepath}: {e}")
                # If we can't check, assume it exists (conservative)

        # Batch delete files that don't exist
        if files_to_remove:
            conn = _get_db_connection(db_path)

            for i in range(0, len(files_to_remove), batch_size):
                batch = files_to_remove[i : i + batch_size]
                placeholders = ",".join("?" * len(batch))

                try:
                    cursor = conn.execute(
                        f"DELETE FROM file_registry WHERE file_path IN ({placeholders})",
                        batch,
                    )
                    files_removed += cursor.rowcount
                except Exception as e:
                    errors.append(f"Batch delete failed: {e}")

                conn.commit()

            conn.close()

            logger.info(f"Removed {files_removed} deleted files from registry")
        else:
            logger.info("No deleted files found in registry")

    except Exception as e:
        errors.append(f"cleanup_deleted_files failed: {e}")
        logger.error(f"Cleanup deleted files failed: {e}")

    duration = time.time() - start_time

    return {
        "files_removed": files_removed,
        "errors": errors,
        "duration_seconds": round(duration, 3),
        "checked_files": checked_files,
    }


def cleanup_stale_embeddings(
    db_path: str = DEFAULT_EMBED_DB,
) -> dict[str, Any]:
    """
    Remove orphaned embeddings (embeddings without corresponding files).

    Checks both ChromaDB collection and SQLite table, removing entries
    where the source file no longer exists on disk.

    Args:
        db_path: Path for ChromaDB storage.

    Returns:
        Dictionary with:
        - embeddings_removed: Number of embeddings removed
        - errors: List of error messages
        - duration_seconds: Time taken
        - checked_embeddings: Number of embeddings checked
    """
    start_time = time.time()
    embeddings_removed = 0
    errors = []
    checked_embeddings = 0

    try:
        # Get SQLite path for file_chunks
        sqlite_path = _get_sqlite_path(db_path)

        if not sqlite_path.exists():
            logger.info(
                f"SQLite database not found at {sqlite_path}, skipping stale embedding cleanup"
            )
            return {
                "embeddings_removed": 0,
                "errors": [],
                "duration_seconds": round(time.time() - start_time, 3),
                "checked_embeddings": 0,
            }

        conn = sqlite3.connect(str(sqlite_path))

        # Get all unique file_paths from file_chunks
        cursor = conn.execute("SELECT DISTINCT file_path FROM file_chunks")
        file_paths = [row[0] for row in cursor.fetchall()]
        checked_embeddings = len(file_paths)

        # Find files that don't exist anymore
        stale_files = []
        for filepath in file_paths:
            try:
                if not os.path.exists(filepath):
                    stale_files.append(filepath)
            except Exception:
                pass  # Conservative: keep if can't check

        # Remove embeddings for stale files
        if stale_files:
            total_removed = 0

            for filepath in stale_files:
                try:
                    # Delete from SQLite
                    cursor = conn.execute(
                        "DELETE FROM file_chunks WHERE file_path = ?",
                        (filepath,),
                    )
                    total_removed += cursor.rowcount
                except Exception as e:
                    errors.append(
                        f"Failed to delete stale embeddings for {filepath}: {e}"
                    )

            conn.commit()

            # Also try to remove from ChromaDB
            collection = _init_chroma(db_path)
            if collection is not None:
                try:
                    # Get all IDs and their metadata, filter by stale files
                    # ChromaDB doesn't support direct deletion by metadata filter for batch
                    # So we'll need to query and delete
                    for filepath in stale_files:
                        try:
                            results = collection.get(where={"file_path": filepath})
                            if results and results.get("ids"):
                                collection.delete(ids=results["ids"])
                        except Exception as e:
                            errors.append(
                                f"Failed to delete from ChromaDB for {filepath}: {e}"
                            )
                except Exception as e:
                    errors.append(f"ChromaDB cleanup failed: {e}")

            embeddings_removed = total_removed
            logger.info(f"Removed {embeddings_removed} stale embeddings")
        else:
            logger.info("No stale embeddings found")

        conn.close()

    except Exception as e:
        errors.append(f"cleanup_stale_embeddings failed: {e}")
        logger.error(f"Cleanup stale embeddings failed: {e}")

    duration = time.time() - start_time

    return {
        "embeddings_removed": embeddings_removed,
        "errors": errors,
        "duration_seconds": round(duration, 3),
        "checked_embeddings": checked_embeddings,
    }


def get_cleanup_stats(db_path: str = DEFAULT_REGISTRY_DB) -> dict[str, Any]:
    """
    Get cleanup statistics for the registry and embeddings.

    Args:
        db_path: Path to SQLite registry database.

    Returns:
        Dictionary with:
        - total_files_in_registry: Total files tracked
        - total_embeddings: Total embeddings in ChromaDB
        - estimated_missing_files: Count of files that don't exist (estimated)
        - stale_embeddings_count: Count of orphaned embeddings
    """
    stats = {
        "total_files_in_registry": 0,
        "total_embeddings": 0,
        "estimated_missing_files": 0,
        "stale_embeddings_count": 0,
    }

    try:
        # Get registry count
        conn = _get_db_connection(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM file_registry")
        stats["total_files_in_registry"] = cursor.fetchone()[0] or 0
        conn.close()
    except Exception as e:
        logger.error(f"Failed to get registry stats: {e}")

    try:
        # Get ChromaDB count
        collection = _init_chroma(DEFAULT_EMBED_DB)
        if collection:
            stats["total_embeddings"] = collection.count()
    except Exception as e:
        logger.error(f"Failed to get ChromaDB count: {e}")

    try:
        # Estimate missing files (sample check)
        conn = _get_db_connection(db_path)
        cursor = conn.execute("SELECT file_path FROM file_registry LIMIT 1000")
        sample_files = [row[0] for row in cursor.fetchall()]
        conn.close()

        missing_count = 0
        for filepath in sample_files:
            try:
                if not os.path.exists(filepath):
                    missing_count += 1
            except Exception:
                pass

        # Extrapolate to total
        if sample_files:
            ratio = missing_count / len(sample_files)
            total = stats["total_files_in_registry"]
            stats["estimated_missing_files"] = int(total * ratio)
    except Exception as e:
        logger.error(f"Failed to estimate missing files: {e}")

    try:
        # Count stale embeddings
        sqlite_path = _get_sqlite_path(DEFAULT_EMBED_DB)
        if sqlite_path.exists():
            conn = sqlite3.connect(str(sqlite_path))

            # Get unique file paths and check existence
            cursor = conn.execute("SELECT DISTINCT file_path FROM file_chunks")
            file_paths = [row[0] for row in cursor.fetchall()]

            stale_count = 0
            for filepath in file_paths:
                try:
                    if not os.path.exists(filepath):
                        # Count chunks for this file
                        chunk_cursor = conn.execute(
                            "SELECT COUNT(*) FROM file_chunks WHERE file_path = ?",
                            (filepath,),
                        )
                        stale_count += chunk_cursor.fetchone()[0] or 0
                except Exception:
                    pass

            stats["stale_embeddings_count"] = stale_count
            conn.close()
    except Exception as e:
        logger.error(f"Failed to count stale embeddings: {e}")

    return stats


def cleanup_all(
    db_path: str = DEFAULT_REGISTRY_DB,
    drives: list[str] | None = None,
) -> dict[str, Any]:
    """
    Run all cleanup operations.

    Args:
        db_path: Path to SQLite registry database.
        drives: List of drive paths to check.

    Returns:
        Dictionary with combined results:
        - deleted_files_result: Result from cleanup_deleted_files
        - stale_embeddings_result: Result from cleanup_stale_embeddings
        - total_files_removed: Sum of files removed
        - total_embeddings_removed: Sum of embeddings removed
        - duration_seconds: Total time taken
        - errors: Combined error list
    """
    start_time = time.time()
    drives = drives or DEFAULT_DRIVES

    # Run both cleanup operations
    deleted_result = cleanup_deleted_files(db_path, drives)
    stale_result = cleanup_stale_embeddings(DEFAULT_EMBED_DB)

    # Combine results
    all_errors = deleted_result.get("errors", []) + stale_result.get("errors", [])

    duration = time.time() - start_time

    return {
        "deleted_files_result": deleted_result,
        "stale_embeddings_result": stale_result,
        "total_files_removed": deleted_result.get("files_removed", 0),
        "total_embeddings_removed": stale_result.get("embeddings_removed", 0),
        "duration_seconds": round(duration, 3),
        "errors": all_errors,
    }


# Package exports
__all__ = [
    "cleanup_deleted_files",
    "cleanup_stale_embeddings",
    "get_cleanup_stats",
    "cleanup_all",
    "DEFAULT_DRIVES",
    "DEFAULT_REGISTRY_DB",
    "DEFAULT_EMBED_DB",
]
