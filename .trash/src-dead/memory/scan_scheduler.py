#!/usr/bin/env python3
"""Periodic full scan with hash-based change detection.

This module provides periodic scanning of all drives with incremental
processing - only files that have changed since the last scan are processed.

Uses:
- drive_scanner for file discovery
- file_registry for hash-based change detection
- file_embedder for embedding new/changed files
"""

import logging
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from .multi_drive_scanner import (
    scan_drives,
    DEFAULT_DRIVES,
    INCLUDE_EXTS as DEFAULT_INCLUDE_EXTS,
    EXCLUDE_DIRS as DEFAULT_EXCLUDE_DIRS,
)
from .drive_embedder import (
    init_file_tables,
    needs_reindex,
    embed_file_content,
    get_indexed_count,
)
from .content_extractor import extract_content

logger = logging.getLogger(__name__)

# Configuration
SQLITE_DB = "context/memory/scan_scheduler.db"
MIN_INTERVAL_HOURS = 1
DEFAULT_INTERVAL_HOURS = 24

# Global scheduler state
_scheduler_running = False
_scheduler_timer: Optional[threading.Timer] = None
_scheduler_lock = threading.Lock()
_scan_status: dict[str, Any] = {
    "last_scan": None,
    "next_scan": None,
    "files_scanned": 0,
    "files_changed": 0,
    "files_embedded": 0,
    "errors": [],
    "is_running": False,
}


def _get_db_path() -> Path:
    """Get SQLite database path for scan metadata."""
    project_root = Path(__file__).parent.parent.parent
    return project_root / SQLITE_DB


def _init_scan_db() -> bool:
    """Initialize scan metadata table in SQLite."""
    db_path = _get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scan_metadata (
                id INTEGER PRIMARY KEY,
                last_scan_time TEXT,
                last_interval_hours INTEGER,
                total_files_scanned INTEGER DEFAULT 0,
                total_files_changed INTEGER DEFAULT 0,
                total_files_embedded INTEGER DEFAULT 0,
                total_errors INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_scan_metadata_time 
            ON scan_metadata(last_scan_time)
        """)
        # Initialize if empty
        cursor = conn.execute("SELECT COUNT(*) FROM scan_metadata")
        if cursor.fetchone()[0] == 0:
            conn.execute("INSERT INTO scan_metadata (id) VALUES (1)")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to initialize scan database: {e}")
        return False


def _update_scan_metadata(
    last_scan_time: str,
    interval_hours: int,
    files_scanned: int,
    files_changed: int,
    files_embedded: int,
    errors_count: int,
) -> None:
    """Update scan metadata in SQLite."""
    db_path = _get_db_path()

    try:
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        conn.execute(
            """UPDATE scan_metadata SET 
               last_scan_time = ?,
               last_interval_hours = ?,
               total_files_scanned = total_files_scanned + ?,
               total_files_changed = total_files_changed + ?,
               total_files_embedded = total_files_embedded + ?,
               total_errors = total_errors + ?
               WHERE id = 1""",
            (
                last_scan_time,
                interval_hours,
                files_scanned,
                files_changed,
                files_embedded,
                errors_count,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to update scan metadata: {e}")


def _read_scan_metadata() -> dict[str, Any]:
    """Read scan metadata from SQLite."""
    db_path = _get_db_path()

    try:
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        cursor = conn.execute(
            """SELECT last_scan_time, last_interval_hours, total_files_scanned,
               total_files_changed, total_files_embedded, total_errors
               FROM scan_metadata WHERE id = 1"""
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "last_scan_time": row[0],
                "interval_hours": row[1],
                "total_files_scanned": row[2],
                "total_files_changed": row[3],
                "total_files_embedded": row[4],
                "total_errors": row[5],
            }
    except Exception as e:
        logger.debug(f"Failed to read scan metadata: {e}")

    return {
        "last_scan_time": None,
        "interval_hours": DEFAULT_INTERVAL_HOURS,
        "total_files_scanned": 0,
        "total_files_changed": 0,
        "total_files_embedded": 0,
        "total_errors": 0,
    }


def run_periodic_scan(
    drives: list[str],
    include_exts: set[str],
    exclude_dirs: set[str],
    interval_hours: int = DEFAULT_INTERVAL_HOURS,
) -> dict[str, Any]:
    """Run a periodic scan of all drives with hash-based change detection.

    Args:
        drives: List of drive paths to scan
        include_exts: Set of file extensions to include
        exclude_dirs: Set of directory names to skip
        interval_hours: Interval between scans (default: 24)

    Returns:
        Dictionary with scan results:
        - files_scanned: Total files discovered
        - files_changed: Files that changed since last scan
        - files_embedded: Files successfully embedded
        - errors: List of error messages
        - duration_seconds: Time taken for scan
    """
    global _scan_status

    start_time = time.time()
    files_scanned = 0
    files_changed = 0
    files_embedded = 0
    errors: list[str] = []

    # Initialize file tables
    init_file_tables()

    logger.info(f"Starting periodic scan of {len(drives)} drives")

    try:
        # Scan all drives using new pipeline
        for f in scan_drives(drives=drives, include_exts=include_exts, exclude_dirs=exclude_dirs):
            files_scanned += 1

            try:
                # Check if file needs re-indexing
                if not needs_reindex(f["path"], f["hash"]):
                    continue

                files_changed += 1

                # Extract content
                content = extract_content(f["path"], f["type"], max_chars=20000)
                if not content or len(content) < 50:
                    continue

                # Embed the file
                result = embed_file_content(
                    f["path"], content, f["hash"], f["type"],
                    f["drive"], f["size"], f["mtime"]
                )

                if result.get("embedded", 0) > 0:
                    files_embedded += 1

                # Progress logging every 100 files
                if files_scanned % 100 == 0:
                    logger.info(
                        f"Scan progress: {files_scanned} scanned, {files_changed} changed, {files_embedded} embedded"
                    )

            except Exception as e:
                errors.append(f"Processing error {f['path']}: {e}")
                logger.warning(f"Error processing {f['path']}: {e}")
                continue

    except Exception as e:
        errors.append(f"Scan error: {e}")
        logger.error(f"Fatal scan error: {e}")

    duration = time.time() - start_time

    # Update status
    now = datetime.now()
    next_scan = now + timedelta(hours=interval_hours)

    with _scheduler_lock:
        _scan_status["last_scan"] = now.isoformat()
        _scan_status["next_scan"] = next_scan.isoformat()
        _scan_status["files_scanned"] = files_scanned
        _scan_status["files_changed"] = files_changed
        _scan_status["files_embedded"] = files_embedded
        _scan_status["errors"] = errors[-10:]  # Keep last 10 errors

    # Persist metadata
    _update_scan_metadata(
        last_scan_time=now.isoformat(),
        interval_hours=interval_hours,
        files_scanned=files_scanned,
        files_changed=files_changed,
        files_embedded=files_embedded,
        errors_count=len(errors),
    )

    logger.info(
        f"Scan complete: {files_scanned} scanned, {files_changed} changed, "
        f"{files_embedded} embedded, {len(errors)} errors, {duration:.1f}s"
    )

    return {
        "files_scanned": files_scanned,
        "files_changed": files_changed,
        "files_embedded": files_embedded,
        "errors": errors,
        "duration_seconds": round(duration, 2),
    }


def _scheduler_callback(interval_hours: int) -> None:
    """Internal callback for periodic scheduler."""
    global _scheduler_running, _scheduler_timer

    if not _scheduler_running:
        return

    # Run the scan
    run_periodic_scan(
        drives=DEFAULT_DRIVES,
        include_exts=DEFAULT_INCLUDE_EXTS,
        exclude_dirs=DEFAULT_EXCLUDE_DIRS,
        interval_hours=interval_hours,
    )

    # Schedule next run
    with _scheduler_lock:
        if _scheduler_running:
            interval_seconds = max(interval_hours * 3600, MIN_INTERVAL_HOURS * 3600)
            _scheduler_timer = threading.Timer(
                interval_seconds, _scheduler_callback, [interval_hours]
            )
            _scheduler_timer.daemon = True
            _scheduler_timer.start()
            logger.info(f"Scheduled next scan in {interval_hours} hours")


def start_scheduler(interval_hours: int = DEFAULT_INTERVAL_HOURS) -> bool:
    """Start periodic scanning in background thread.

    Args:
        interval_hours: Hours between scans (default: 24, minimum: 1)

    Returns:
        True if scheduler started successfully, False otherwise
    """
    global _scheduler_running, _scheduler_timer

    # Enforce minimum interval
    interval_hours = max(interval_hours, MIN_INTERVAL_HOURS)

    with _scheduler_lock:
        if _scheduler_running:
            logger.warning("Scheduler already running")
            return False

        # Initialize database
        if not _init_scan_db():
            logger.error("Failed to initialize scan database")
            return False

        _scheduler_running = True
        _scan_status["is_running"] = True

        # Calculate initial delay (start on next interval boundary)
        now = datetime.now()
        next_run = now + timedelta(hours=interval_hours)
        _scan_status["next_scan"] = next_run.isoformat()

        # Start first timer
        interval_seconds = interval_hours * 3600
        _scheduler_timer = threading.Timer(
            interval_seconds, _scheduler_callback, [interval_hours]
        )
        _scheduler_timer.daemon = True
        _scheduler_timer.start()

        logger.info(f"Scheduler started with {interval_hours} hour interval")
        return True


def stop_scheduler() -> bool:
    """Stop the periodic scheduler.

    Returns:
        True if scheduler stopped successfully
    """
    global _scheduler_running, _scheduler_timer

    with _scheduler_lock:
        if not _scheduler_running:
            logger.warning("Scheduler not running")
            return False

        _scheduler_running = False
        _scan_status["is_running"] = False

        if _scheduler_timer is not None:
            _scheduler_timer.cancel()
            _scheduler_timer = None

        logger.info("Scheduler stopped")
        return True


def get_scan_status() -> dict[str, Any]:
    """Get current scan status.

    Returns:
        Dictionary with current status:
        - last_scan: ISO timestamp of last scan completion
        - next_scan: ISO timestamp of next scheduled scan
        - files_scanned: Files discovered in last scan
        - files_changed: Files that needed processing in last scan
        - files_embedded: Files successfully embedded in last scan
        - errors: List of recent error messages
        - is_running: Whether scheduler is active
    """
    with _scheduler_lock:
        return {
            "last_scan": _scan_status.get("last_scan"),
            "next_scan": _scan_status.get("next_scan"),
            "files_scanned": _scan_status.get("files_scanned", 0),
            "files_changed": _scan_status.get("files_changed", 0),
            "files_embedded": _scan_status.get("files_embedded", 0),
            "errors": _scan_status.get("errors", []),
            "is_running": _scan_status.get("is_running", False),
        }


# Package exports
__all__ = [
    "run_periodic_scan",
    "start_scheduler",
    "stop_scheduler",
    "get_scan_status",
    "DEFAULT_DRIVES",
    "DEFAULT_INCLUDE_EXTS",
    "DEFAULT_EXCLUDE_DIRS",
    "DEFAULT_INTERVAL_HOURS",
    "MIN_INTERVAL_HOURS",
]
