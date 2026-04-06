"""Recursive file discovery with filtering and progress tracking.

This module provides drive scanning capabilities for Wave 2 (content extraction)
and Wave 3 (embedding). Uses generators for memory efficiency and ThreadPoolExecutor
for parallel drive scanning.
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Iterator, Optional


# Default configuration
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

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def scan_drive(
    drive_path: str,
    include_exts: Optional[set] = None,
    exclude_dirs: Optional[set] = None,
    max_size: int = MAX_FILE_SIZE,
) -> Iterator[str]:
    """Scan a single drive and yield file paths matching criteria.

    Args:
        drive_path: Root path to scan
        include_exts: Set of file extensions to include (default: DEFAULT_INCLUDE_EXTS)
        exclude_dirs: Set of directory names to skip (default: DEFAULT_EXCLUDE_DIRS)
        max_size: Maximum file size in bytes (default: 10MB)

    Yields:
        File paths that match the filter criteria
    """
    if include_exts is None:
        include_exts = DEFAULT_INCLUDE_EXTS
    if exclude_dirs is None:
        exclude_dirs = DEFAULT_EXCLUDE_DIRS

    if not os.path.exists(drive_path):
        return

    for root, dirs, files in os.walk(drive_path):
        # Modify dirs in-place to skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for filename in files:
            filepath = os.path.join(root, filename)

            # Check file extension
            ext = os.path.splitext(filename)[1].lower()
            if ext not in include_exts:
                continue

            # Check file size
            try:
                if os.path.getsize(filepath) > max_size:
                    continue
            except (OSError, IOError):
                # Skip files we can't access
                continue

            yield filepath


def scan_all_drives(
    drives: list,
    include_exts: Optional[set] = None,
    exclude_dirs: Optional[set] = None,
    max_size: int = MAX_FILE_SIZE,
    max_workers: int = 5,
) -> Iterator[str]:
    """Scan multiple drives in parallel using ThreadPoolExecutor.

    Args:
        drives: List of drive paths to scan
        include_exts: Set of file extensions to include (default: DEFAULT_INCLUDE_EXTS)
        exclude_dirs: Set of directory names to skip (default: DEFAULT_EXCLUDE_DIRS)
        max_size: Maximum file size in bytes (default: 10MB)
        max_workers: Maximum number of parallel threads (default: 5)

    Yields:
        File paths from all drives matching the filter criteria
    """

    def scan_single_drive(drive_path: str) -> Iterator[str]:
        return scan_drive(drive_path, include_exts, exclude_dirs, max_size)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all drives for parallel scanning
        futures = {executor.submit(scan_single_drive, drive): drive for drive in drives}

        # Yield results as they come in
        for future in futures:
            try:
                for filepath in future.result():
                    yield filepath
            except Exception as e:
                # Log but don't stop on individual drive errors
                drive = futures[future]
                print(f"Error scanning {drive}: {e}")


def get_file_types(file_path: str) -> str:
    """Determine file type category based on extension.

    Args:
        file_path: Path to the file

    Returns:
        File type category: 'code', 'doc', 'config', 'data', or 'other'
    """
    ext = os.path.splitext(file_path)[1].lower()

    # Code files
    code_exts = {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".sh",
        ".bash",
        ".rb",
        ".go",
        ".rs",
        ".java",
        ".c",
        ".cpp",
        ".h",
    }
    if ext in code_exts:
        return "code"

    # Documentation
    doc_exts = {".md", ".txt", ".rst", ".pdf", ".docx", ".odt"}
    if ext in doc_exts:
        return "doc"

    # Configuration
    config_exts = {".json", ".yaml", ".yml", ".toml", ".ini", ".conf", ".cfg"}
    if ext in config_exts:
        return "config"

    # Data formats
    data_exts = {".csv", ".xml", ".sql", ".db", ".sqlite"}
    if ext in data_exts:
        return "data"

    return "other"


def estimate_scan_time(drive_path: str) -> dict:
    """Estimate scan time and file count for a drive.

    Performs a quick sample of the directory structure to estimate
    how many files will be found and how long the scan will take.

    Args:
        drive_path: Root path to estimate

    Returns:
        Dictionary with 'estimated_files' (int) and 'estimated_time_seconds' (float)
    """
    if not os.path.exists(drive_path):
        return {"estimated_files": 0, "estimated_time_seconds": 0.0}

    sample_files = 0
    sample_dirs = 0
    start_time = time.time()

    # Sample first few directories
    for root, dirs, files in os.walk(drive_path):
        sample_dirs += len(dirs)
        sample_files += len(files)

        # Stop after 5 seconds or 1000 files
        if time.time() - start_time > 5 or sample_files > 1000:
            break

    elapsed = time.time() - start_time

    # If we didn't find anything, assume minimal scan
    if sample_files == 0:
        return {"estimated_files": 0, "estimated_time_seconds": 0.1}

    # Extrapolate based on sample
    # Assume average 100 files per directory
    total_estimated = sample_files * 10

    # Estimate time: ~100 files/second for simple walk
    estimated_time = total_estimated / 100

    return {
        "estimated_files": total_estimated,
        "estimated_time_seconds": round(estimated_time, 2),
    }
