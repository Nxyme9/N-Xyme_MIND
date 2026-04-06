"""Multi-drive scanner for /mnt/* drives.

Scans all mounted drives, filters by file extensions,
computes xxhash for change detection, yields files one at a time.
"""

import hashlib
import logging
import os
import time
from pathlib import Path
from typing import Iterator, Optional, Set

logger = logging.getLogger(__name__)

# Default drives to scan
DEFAULT_DRIVES = [
    "/mnt/external",
    "/mnt/WIN_LIBRARY",
    "/mnt/NXYME_CORE",
    "/mnt/NXYME_IMAGES",
    "/mnt/backup",
]

# File extensions to include
INCLUDE_EXTS: Set[str] = {
    # Code
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".scala",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    # Config
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".env",
    ".xml",
    ".properties",
    # Documentation
    ".md",
    ".rst",
    ".txt",
    ".tex",
    ".org",
    # Documents
    ".pdf",
    ".docx",
}

# Directories to exclude
EXCLUDE_DIRS: Set[str] = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    "target",
    ".cache",
    ".idea",
    ".vscode",
    ".next",
    ".nuxt",
    "vendor",
    "eggs",
    "*.egg-info",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
}

# Max file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


def compute_file_hash(filepath: str) -> str:
    """Compute xxhash64 of file content (fallback to sha256)."""
    try:
        import xxhash

        h = xxhash.xxh64()
    except ImportError:
        h = hashlib.sha256()

    try:
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except (OSError, IOError) as e:
        logger.warning(f"Failed to hash {filepath}: {e}")
        return ""


def get_file_type(filepath: str) -> str:
    """Classify file by extension."""
    ext = Path(filepath).suffix.lower()
    if ext in {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".go",
        ".rs",
        ".java",
        ".cpp",
        ".c",
        ".h",
        ".hpp",
        ".cs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".scala",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
    }:
        return "code"
    elif ext in {
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".env",
        ".xml",
        ".properties",
    }:
        return "config"
    elif ext in {".md", ".rst", ".txt", ".tex", ".org"}:
        return "doc"
    elif ext in {".pdf", ".docx"}:
        return "document"
    else:
        return "other"


def scan_drives(
    drives: Optional[list] = None,
    include_exts: Optional[Set[str]] = None,
    exclude_dirs: Optional[Set[str]] = None,
    max_size: Optional[int] = None,
) -> Iterator[dict]:
    """Scan multiple drives and yield file info dicts.

    Args:
        drives: List of drive paths to scan (default: DEFAULT_DRIVES)
        include_exts: Set of file extensions to include (default: INCLUDE_EXTS)
        exclude_dirs: Set of directory names to exclude (default: EXCLUDE_DIRS)
        max_size: Maximum file size in bytes (default: MAX_FILE_SIZE)

    Yields:
        dict with: path, size, mtime, hash, type, drive
    """
    drives = drives or DEFAULT_DRIVES
    exts = include_exts or INCLUDE_EXTS
    excludes = exclude_dirs or EXCLUDE_DIRS
    max_sz = max_size or MAX_FILE_SIZE

    for drive in drives:
        drive_path = Path(drive)
        if not drive_path.exists() or not drive_path.is_dir():
            logger.warning(f"Drive not accessible: {drive}")
            continue

        logger.info(f"Scanning drive: {drive}")
        file_count = 0
        error_count = 0
        start_time = time.time()

        try:
            for root, dirs, files in os.walk(drive, followlinks=False):
                # Filter out excluded directories (modify in-place)
                dirs[:] = [d for d in dirs if d not in excludes]

                for filename in files:
                    filepath = os.path.join(root, filename)
                    ext = Path(filename).suffix.lower()

                    if ext not in exts:
                        continue

                    try:
                        stat = os.stat(filepath)
                        if stat.st_size > max_sz:
                            continue

                        file_hash = compute_file_hash(filepath)
                        file_type = get_file_type(filepath)

                        yield {
                            "path": filepath,
                            "size": stat.st_size,
                            "mtime": stat.st_mtime,
                            "hash": file_hash,
                            "type": file_type,
                            "drive": drive,
                        }
                        file_count += 1

                    except (OSError, IOError) as e:
                        error_count += 1
                        if error_count <= 10:
                            logger.debug(f"Skipping {filepath}: {e}")

        except (OSError, PermissionError) as e:
            logger.error(f"Failed to scan {drive}: {e}")

        elapsed = time.time() - start_time
        logger.info(
            f"Drive {drive}: {file_count} files, {error_count} errors, {elapsed:.1f}s"
        )
