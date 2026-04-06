#!/usr/bin/env python3
"""
File Watcher — Real-time file monitoring with watchdog.

Provides:
- FileEventHandler: Handles file system events (create, modify, delete, move)
- start_watcher(): Start monitoring drives for changes
- stop_watcher(): Stop monitoring

Triggers re-embedding when files are modified, created, or deleted.
Integrates with file_embedder.py for processing changes.
"""

import logging
import os
import time
from pathlib import Path
from threading import Lock
from typing import Callable, Optional, Set

# Try to import watchdog, handle if not available
try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    FileSystemEventHandler = object  # type: ignore[misc,assignment]
    Observer = None  # type: ignore[misc,assignment]
    logger = logging.getLogger(__name__)
    logger.warning("watchdog library not installed. File watcher will be disabled.")

from .drive_scanner import DEFAULT_DRIVES, DEFAULT_EXCLUDE_DIRS, DEFAULT_INCLUDE_EXTS

logger = logging.getLogger(__name__)

# Debounce settings
DEBOUNCE_SECONDS = 5.0

# Global state
_observer: Optional[Observer] = None
_event_handler: Optional["FileEventHandler"] = None
_lock = Lock()


class FileEventHandler(FileSystemEventHandler):
    """
    Handles file system events and triggers re-embedding.

    Filters events by:
    - File extensions (only indexable files)
    - Excluded directories (node_modules, .git, etc.)

    Debounces rapid changes to avoid re-embedding the same file multiple times.
    """

    def __init__(
        self,
        include_exts: Optional[Set[str]] = None,
        exclude_dirs: Optional[Set[str]] = None,
    ):
        super().__init__()
        self.include_exts = include_exts or DEFAULT_INCLUDE_EXTS
        self.exclude_dirs = exclude_dirs or DEFAULT_EXCLUDE_DIRS
        self._debounce_timestamps: dict[str, float] = {}
        self._debounce_lock = Lock()

    def _should_process(self, file_path: str) -> bool:
        """Check if file should be processed based on filters."""
        # Get file extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.include_exts:
            return False

        # Check if in excluded directory
        path_parts = Path(file_path).parts
        for part in path_parts:
            if part in self.exclude_dirs:
                return False

        return True

    def _is_debounced(self, file_path: str) -> bool:
        """Check if file is in debounce period."""
        with self._debounce_lock:
            now = time.time()
            last_time = self._debounce_timestamps.get(file_path, 0)

            if now - last_time < DEBOUNCE_SECONDS:
                return True

            self._debounce_timestamps[file_path] = now
            return False

    def _read_file_content(self, file_path: str) -> Optional[str]:
        """Read file content for embedding."""
        try:
            # Check file size before reading (skip files > 10MB)
            if os.path.getsize(file_path) > 10 * 1024 * 1024:
                logger.debug(f"Skipping large file: {file_path}")
                return None

            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except (OSError, IOError) as e:
            logger.warning(f"Cannot read file {file_path}: {e}")
            return None

    def _remove_from_index(self, file_path: str) -> None:
        """Remove file from ChromaDB index."""
        # This would need implementation in file_embedder.py
        # For now, just log the action
        logger.info(f"Would remove from index: {file_path}")

    def _update_index(self, old_path: str, new_path: str) -> None:
        """Update file path in index after move/rename."""
        logger.info(f"Would update index: {old_path} -> {new_path}")

    def _embed_file(self, file_path: str, action: str) -> None:
        """Embed a file and log the result."""
        content = self._read_file_content(file_path)
        if content is None:
            return

        try:
            from .file_embedder import embed_file

            result = embed_file(file_path, content)
            logger.info(
                f"Embedded {action} file: {file_path} ({result.get('embedded', 0)} chunks)"
            )
        except Exception as e:
            logger.error(f"Failed to embed {file_path}: {e}")

    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return

        file_path = event.src_path

        if not self._should_process(file_path):
            return

        if self._is_debounced(file_path):
            return

        logger.info(f"File created: {file_path}")
        self._embed_file(file_path, "new")

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = event.src_path

        if not self._should_process(file_path):
            return

        if self._is_debounced(file_path):
            return

        logger.info(f"File modified: {file_path}")
        self._embed_file(file_path, "modified")

    def on_deleted(self, event):
        """Handle file deletion events."""
        if event.is_directory:
            return

        file_path = event.src_path

        if not self._should_process(file_path):
            return

        logger.info(f"File deleted: {file_path}")
        self._remove_from_index(file_path)

    def on_moved(self, event):
        """Handle file move/rename events."""
        if event.is_directory:
            return

        src_path = event.src_path
        dest_path = event.dest_path

        # Check if either path should be processed
        if not self._should_process(src_path) and not self._should_process(dest_path):
            return

        logger.info(f"File moved: {src_path} -> {dest_path}")
        self._update_index(src_path, dest_path)


def start_watcher(
    drives: Optional[list[str]] = None,
    include_exts: Optional[Set[str]] = None,
    exclude_dirs: Optional[Set[str]] = None,
) -> bool:
    """
    Start monitoring drives for file changes.

    Args:
        drives: List of drive paths to monitor (default: DEFAULT_DRIVES)
        include_exts: Set of file extensions to monitor (default: DEFAULT_INCLUDE_EXTS)
        exclude_dirs: Set of directories to skip (default: DEFAULT_EXCLUDE_DIRS)

    Returns:
        True if watcher started successfully, False otherwise.
    """
    global _observer, _event_handler

    if not WATCHDOG_AVAILABLE:
        logger.error("Cannot start watcher: watchdog library not installed")
        return False

    with _lock:
        if _observer is not None:
            logger.warning("Watcher already running")
            return False

    # Use defaults if not provided
    drives = drives or DEFAULT_DRIVES
    include_exts = include_exts or DEFAULT_INCLUDE_EXTS
    exclude_dirs = exclude_dirs or DEFAULT_EXCLUDE_DIRS

    # Create event handler
    _event_handler = FileEventHandler(include_exts, exclude_dirs)

    # Create observer
    _observer = Observer()

    # Schedule watches for each drive
    for drive in drives:
        if not os.path.exists(drive):
            logger.warning(f"Drive does not exist, skipping: {drive}")
            continue

        try:
            _observer.schedule(_event_handler, drive, recursive=True)
            logger.info(f"Watching: {drive}")
        except Exception as e:
            logger.error(f"Failed to watch {drive}: {e}")

    # Start the observer
    try:
        _observer.start()
        logger.info(f"File watcher started (debounce: {DEBOUNCE_SECONDS}s)")
        return True
    except Exception as e:
        logger.error(f"Failed to start observer: {e}")
        _observer = None
        _event_handler = None
        return False


def stop_watcher() -> bool:
    """
    Stop monitoring drives for file changes.

    Returns:
        True if watcher stopped successfully, False otherwise.
    """
    global _observer, _event_handler

    with _lock:
        if _observer is None:
            logger.warning("No watcher running")
            return False

    try:
        _observer.stop()
        _observer.join(timeout=5)
        logger.info("File watcher stopped")
    except Exception as e:
        logger.error(f"Error stopping watcher: {e}")
    finally:
        _observer = None
        _event_handler = None

    return True


def is_watcher_running() -> bool:
    """Check if file watcher is currently running."""
    with _lock:
        return _observer is not None and _observer.is_alive()


# ---------------------------------------------------------------------------
# Package Exports
# ---------------------------------------------------------------------------

__all__ = [
    "FileEventHandler",
    "start_watcher",
    "stop_watcher",
    "is_watcher_running",
]
