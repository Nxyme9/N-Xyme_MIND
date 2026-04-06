"""File metadata extraction for memory pipeline."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Extension to file type mapping
FILE_TYPE_MAP = {
    ".py": "code",
    ".js": "code",
    ".ts": "code",
    ".tsx": "code",
    ".jsx": "code",
    ".java": "code",
    ".c": "code",
    ".cpp": "code",
    ".h": "code",
    ".hpp": "code",
    ".go": "code",
    ".rs": "code",
    ".rb": "code",
    ".php": "code",
    ".swift": "code",
    ".kt": "code",
    ".scala": "code",
    ".cs": "code",
    ".html": "code",
    ".css": "code",
    ".scss": "code",
    ".sass": "code",
    ".less": "code",
    ".vue": "code",
    ".svelte": "code",
    ".sql": "code",
    ".sh": "code",
    ".bash": "code",
    ".zsh": "code",
    ".ps1": "code",
    ".r": "code",
    ".lua": "code",
    ".pl": "code",
    ".pm": "code",
    ".ex": "code",
    ".exs": "code",
    ".erl": "code",
    ".hs": "code",
    ".ml": "code",
    ".dart": "code",
    ".groovy": "code",
    ".gradle": "code",
    ".md": "doc",
    ".markdown": "doc",
    ".mdown": "doc",
    ".mkd": "doc",
    ".txt": "text",
    ".text": "text",
    ".log": "text",
    ".pdf": "doc",
    ".doc": "doc",
    ".docx": "doc",
    ".rtf": "doc",
    ".odt": "doc",
    ".json": "config",
    ".yaml": "config",
    ".yml": "config",
    ".toml": "config",
    ".ini": "config",
    ".cfg": "config",
    ".conf": "config",
    ".xml": "config",
    ".env": "config",
    ".gitignore": "config",
    ".dockerignore": "config",
    ".csv": "data",
    ".tsv": "data",
    ".jsonl": "data",
    ".parquet": "data",
    ".db": "data",
    ".sqlite": "data",
    ".sqlite3": "data",
}

# Extension to language mapping
LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".cs": "csharp",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".vue": "vue",
    ".svelte": "svelte",
    ".sql": "sql",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "zsh",
    ".ps1": "powershell",
    ".r": "r",
    ".lua": "lua",
    ".pl": "perl",
    ".pm": "perl",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".hs": "haskell",
    ".ml": "ocaml",
    ".dart": "dart",
    ".groovy": "groovy",
    ".gradle": "gradle",
    ".md": "markdown",
    ".markdown": "markdown",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".csv": "csv",
    ".tsv": "tsv",
    ".txt": "text",
    ".log": "log",
    ".pdf": "pdf",
    ".doc": "word",
    ".docx": "word",
}


def is_binary(file_path: str) -> bool:
    """Check if file is binary by reading first 8192 bytes for null bytes.

    Args:
        file_path: Path to the file to check.

    Returns:
        True if file appears to be binary, False otherwise.
    """
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(8192)
            if b"\x00" in chunk:
                return True
            return False
    except Exception as e:
        logger.warning(f"Failed to check binary status for {file_path}: {e}")
        return True  # Default to binary on error


def get_file_type(file_path: str) -> str:
    """Determine file type based on extension.

    Args:
        file_path: Path to the file.

    Returns:
        File type: code, doc, config, text, data, or other.
    """
    ext = Path(file_path).suffix.lower()
    return FILE_TYPE_MAP.get(ext, "other")


def get_language(file_path: str) -> str:
    """Get programming language based on file extension.

    Args:
        file_path: Path to the file.

    Returns:
        Language name or 'unknown'.
    """
    ext = Path(file_path).suffix.lower()
    return LANGUAGE_MAP.get(ext, "unknown")


def get_drive_name(file_path: str) -> str:
    """Extract drive name from file path.

    Extracts the first directory component after mount point.
    Example: /mnt/<drive>/path/file.py -> drive name

    Args:
        file_path: Path to the file.

    Returns:
        Drive name or empty string if not applicable.
    """
    try:
        # Normalize the path
        path = Path(file_path).resolve()
        parts = path.parts

        # Check for /mnt/ or /media/ mount points
        for i, part in enumerate(parts):
            if part in ("mnt", "media") and i + 1 < len(parts):
                return parts[i + 1]  # Return the drive name after /mnt/

        # For root-level paths, return first meaningful component
        for part in parts[1:]:
            if part and not part.startswith("."):
                return part
        return ""
    except Exception as e:
        logger.warning(f"Failed to extract drive name from {file_path}: {e}")
        return ""


def count_lines(file_path: str) -> int:
    """Count lines in a file (efficient for large files).

    Args:
        file_path: Path to the file.

    Returns:
        Number of lines, or 0 on error.
    """
    try:
        with open(file_path, "rb") as f:
            # Count newlines efficiently
            line_count = sum(1 for _ in f)
        return line_count
    except Exception as e:
        logger.warning(f"Failed to count lines for {file_path}: {e}")
        return 0


def estimate_importance(file_path: str, size_bytes: int) -> float:
    """Estimate importance score for a file based on path and size.

    Args:
        file_path: Path to the file.
        size_bytes: Size of the file in bytes.

    Returns:
        Importance score between 0.0 and 1.0.
    """
    score = 0.5  # Base score

    # Adjust by file type
    file_type = get_file_type(file_path)
    if file_type == "code":
        score += 0.2
    elif file_type == "config":
        score += 0.1
    elif file_type == "doc":
        score += 0.05

    # Adjust by path patterns (heuristic)
    path_lower = file_path.lower()

    # High priority patterns
    high_priority = ["/src/", "/lib/", "/core/", "/main/"]
    for pattern in high_priority:
        if pattern in path_lower:
            score += 0.15
            break

    # Lower priority patterns
    low_priority = ["/test/", "/tests/", "/docs/", "/example/"]
    for pattern in low_priority:
        if pattern in path_lower:
            score -= 0.1
            break

    # Adjust by size (reasonable size indicates meaningful content)
    if 1000 < size_bytes < 100000:  # 1KB to 100KB
        score += 0.05
    elif size_bytes < 100:  # Very small files might be stubs
        score -= 0.1
    elif size_bytes > 1000000:  # Very large files might be generated
        score -= 0.1

    # Clamp to 0-1 range
    return max(0.0, min(1.0, score))


def extract_metadata(file_path: str) -> Optional[dict]:
    """Extract comprehensive metadata from a file.

    Args:
        file_path: Path to the file.

    Returns:
        Dictionary with all metadata fields, or None if file doesn't exist.
    """
    # Handle missing files gracefully
    if not os.path.exists(file_path):
        logger.warning(f"File does not exist: {file_path}")
        return None

    try:
        # Get file stats
        stat = os.stat(file_path)

        # Get basic info
        path_obj = Path(file_path)

        metadata = {
            "file_path": str(path_obj.resolve()),
            "file_name": path_obj.name,
            "extension": path_obj.suffix.lower(),
            "size_bytes": stat.st_size,
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "drive": get_drive_name(file_path),
            "file_type": get_file_type(file_path),
            "language": get_language(file_path),
            "is_binary": is_binary(file_path),
            "line_count": 0,  # Default, will update for code files
            "importance": 0.0,  # Default, will calculate
        }

        # Add line count for code/text files
        if not metadata["is_binary"] and metadata["file_type"] in (
            "code",
            "doc",
            "text",
            "config",
        ):
            metadata["line_count"] = count_lines(file_path)

        # Calculate importance
        metadata["importance"] = estimate_importance(file_path, stat.st_size)

        return metadata

    except Exception as e:
        logger.error(f"Failed to extract metadata for {file_path}: {e}")
        return None
