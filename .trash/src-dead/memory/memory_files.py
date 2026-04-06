"""Markdown memory file management with YAML frontmatter.

Adapted from Claude Code's proven pattern:
- MEMORY.md as entrypoint (200 lines max, 25KB max)
- Topic files for detail, MEMORY.md for index
- YAML frontmatter with type, description, created_at, updated_at
"""

import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from src.memory.memory_types import MemoryType, parse_memory_type

# Constants from Claude Code's proven limits
MAX_ENTRYPOINT_LINES = 200
MAX_ENTRYPOINT_BYTES = 25_000
MAX_MEMORY_FILES = 200
FRONTMATTER_MAX_LINES = 30


@dataclass
class MemoryFile:
    """A single memory markdown file."""

    filename: str
    filepath: str
    memory_type: Optional[MemoryType]
    description: Optional[str]
    created_at: float
    updated_at: float
    content: str = ""
    frontmatter: dict = field(default_factory=dict)

    @property
    def age_days(self) -> float:
        """Age of the memory in days."""
        return (time.time() - self.created_at) / 86400

    @property
    def mtime_iso(self) -> str:
        """Modification time as ISO string."""
        return datetime.fromtimestamp(self.updated_at, tz=timezone.utc).isoformat()


def parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from markdown content."""
    match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
    if not match:
        return {}

    frontmatter_text = match.group(1)
    result = {}
    for line in frontmatter_text.split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def create_memory_file(
    memory_dir: str,
    filename: str,
    memory_type: MemoryType,
    description: str,
    content: str,
) -> str:
    """Create a new memory markdown file with frontmatter."""
    os.makedirs(memory_dir, exist_ok=True)
    filepath = os.path.join(memory_dir, filename)

    now = datetime.now(timezone.utc).isoformat()
    frontmatter = (
        f"---\n"
        f"type: {memory_type.value}\n"
        f"description: {description}\n"
        f"created_at: {now}\n"
        f"updated_at: {now}\n"
        f"---\n"
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(frontmatter + content)

    return filepath


def read_memory_file(filepath: str) -> Optional[MemoryFile]:
    """Read a memory markdown file and parse its frontmatter."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        frontmatter = parse_frontmatter(content)
        body = content.split("---\n", 2)[-1] if "---\n" in content else content
        # Parse timestamps - handle both ISO strings and floats
        def parse_ts(val):
            if not val:
                return time.time()
            try:
                return float(val)
            except ValueError:
                try:
                    return datetime.fromisoformat(val).timestamp()
                except Exception:
                    return time.time()

        return MemoryFile(
            filename=os.path.basename(filepath),
            filepath=filepath,
            memory_type=parse_memory_type(frontmatter.get("type")),
            description=frontmatter.get("description"),
            created_at=parse_ts(frontmatter.get("created_at")),
            updated_at=parse_ts(frontmatter.get("updated_at")),
            content=body.strip(),
            frontmatter=frontmatter,
        )
    except Exception:
        return None


def scan_memory_files(memory_dir: str) -> List[MemoryFile]:
    """Scan memory directory for .md files, parse frontmatter, return headers.

    Sorted newest-first, capped at MAX_MEMORY_FILES.
    """
    if not os.path.exists(memory_dir):
        return []

    md_files = []
    for root, _, files in os.walk(memory_dir):
        for f in files:
            if f.endswith(".md") and f != "MEMORY.md":
                md_files.append(os.path.join(root, f))

    # Cap at MAX_MEMORY_FILES
    md_files = md_files[:MAX_MEMORY_FILES]

    results = []
    for filepath in md_files:
        mem = read_memory_file(filepath)
        if mem:
            results.append(mem)

    # Sort newest-first
    results.sort(key=lambda m: m.updated_at, reverse=True)
    return results[:MAX_MEMORY_FILES]


def format_memory_manifest(memories: List[MemoryFile]) -> str:
    """Format memory headers as a text manifest for LLM prompts.

    One line per file: [type] filename (timestamp): description
    """
    lines = []
    for m in memories:
        tag = f"[{m.memory_type.value}] " if m.memory_type else ""
        ts = m.mtime_iso
        if m.description:
            lines.append(f"- {tag}{m.filename} ({ts}): {m.description}")
        else:
            lines.append(f"- {tag}{m.filename} ({ts})")
    return "\n".join(lines)


def truncate_entrypoint_content(raw: str) -> str:
    """Truncate MEMORY.md content to line and byte caps.

    Line-truncates first (natural boundary), then byte-truncates at the
    last newline before the cap so we don't cut mid-line.
    """
    trimmed = raw.strip()
    content_lines = trimmed.split("\n")
    line_count = len(content_lines)
    byte_count = len(trimmed)

    was_line_truncated = line_count > MAX_ENTRYPOINT_LINES
    was_byte_truncated = byte_count > MAX_ENTRYPOINT_BYTES

    if not was_line_truncated and not was_byte_truncated:
        return trimmed

    truncated = (
        "\n".join(content_lines[:MAX_ENTRYPOINT_LINES])
        if was_line_truncated
        else trimmed
    )

    if len(truncated) > MAX_ENTRYPOINT_BYTES:
        cut_at = truncated.rfind("\n", 0, MAX_ENTRYPOINT_BYTES)
        truncated = truncated[: cut_at if cut_at > 0 else MAX_ENTRYPOINT_BYTES]

    reason_parts = []
    if was_byte_truncated and not was_line_truncated:
        reason_parts.append(
            f"{byte_count} bytes (limit: {MAX_ENTRYPOINT_BYTES}) — entries are too long"
        )
    elif was_line_truncated and not was_byte_truncated:
        reason_parts.append(f"{line_count} lines (limit: {MAX_ENTRYPOINT_LINES})")
    elif was_line_truncated and was_byte_truncated:
        reason_parts.append(f"{line_count} lines and {byte_count} bytes")

    reason = ", ".join(reason_parts)
    return (
        truncated + f"\n\n> WARNING: MEMORY.md is {reason}. Only part was loaded. "
        "Keep index entries to one line under ~200 chars; "
        "move detail into topic files."
    )


def update_memory_file(
    filepath: str, content: str, description: Optional[str] = None
) -> bool:
    """Update an existing memory file with new content."""
    try:
        mem = read_memory_file(filepath)
        if not mem:
            return False

        now = datetime.now(timezone.utc).isoformat()
        frontmatter = mem.frontmatter.copy()
        frontmatter["updated_at"] = now
        if description:
            frontmatter["description"] = description

        fm_text = (
            "---\n" + "\n".join(f"{k}: {v}" for k, v in frontmatter.items()) + "\n---\n"
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(fm_text + content)

        return True
    except Exception:
        return False
