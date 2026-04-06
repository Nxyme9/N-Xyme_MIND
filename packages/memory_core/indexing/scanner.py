"""Scanner — File/drive scanner for memory indexing.

Combines:
- indexer.py: Main indexer CLI
- drive_scanner.py: Recursive file discovery
- multi_drive_scanner.py: Multi-drive scanning
- scan_config.py: Scan configuration
- scan_scheduler.py: Scan scheduling
"""

import logging
import os
from pathlib import Path
from typing import Iterator, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_DRIVES = [
    os.environ.get("NX_DRIVE_LIBRARY", "/mnt/Library"),
    "/mnt/WIN_LIBRARY",
    "/mnt/NXYME_CORE",
    "/mnt/NXYME_IMAGES",
    "/mnt/backup",
]

DEFAULT_INCLUDE_EXTS = {
    ".py",
    ".js",
    ".ts",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".pdf",
    ".docx",
    ".rst",
    ".sh",
    ".bash",
}

DEFAULT_EXCLUDE_DIRS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    "target",
    ".cache",
}


def scan_drive(
    drive_path: str,
    include_exts: Optional[set] = None,
    exclude_dirs: Optional[set] = None,
) -> Iterator[dict]:
    """Scan a single drive and yield file info dicts."""
    if include_exts is None:
        include_exts = DEFAULT_INCLUDE_EXTS
    if exclude_dirs is None:
        exclude_dirs = DEFAULT_EXCLUDE_DIRS

    if not os.path.exists(drive_path):
        return

    for root, dirs, files in os.walk(drive_path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for filename in files:
            filepath = os.path.join(root, filename)
            ext = os.path.splitext(filename)[1].lower()
            if ext not in include_exts:
                continue
            try:
                size = os.path.getsize(filepath)
                mtime = os.path.getmtime(filepath)
                yield {
                    "path": filepath,
                    "name": filename,
                    "ext": ext,
                    "size": size,
                    "mtime": mtime,
                    "drive": drive_path,
                }
            except (OSError, IOError):
                continue


def scan_drives(drives: Optional[List[str]] = None) -> Iterator[dict]:
    """Scan multiple drives."""
    drives = drives or DEFAULT_DRIVES
    for drive in drives:
        yield from scan_drive(drive)


class DriveScanner:
    """Drive scanner with configuration."""

    def __init__(
        self, drives: Optional[List[str]] = None, include_exts: Optional[set] = None
    ):
        self.drives = drives or DEFAULT_DRIVES
        self.include_exts = include_exts or DEFAULT_INCLUDE_EXTS

    def scan(self) -> Iterator[dict]:
        for drive in self.drives:
            yield from scan_drive(drive, self.include_exts)


class FileScanner:
    """Simple file scanner."""

    def __init__(self, root_path: str):
        self.root_path = root_path

    def scan(self) -> Iterator[dict]:
        yield from scan_drive(self.root_path)


__all__ = [
    "FileScanner",
    "DriveScanner",
    "scan_drives",
    "scan_drive",
    "DEFAULT_DRIVES",
    "DEFAULT_INCLUDE_EXTS",
]
