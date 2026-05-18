#!/usr/bin/env python3
"""
Session Memory Ingest - N-Xyme pattern from gstack.

Walks session files from data_chaos, extracts tool_use/tool_result entries,
and writes structured summaries to memory synapses.

Pattern: incremental ingestion with mtime fast-path, typed pages, state tracking.
"""

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional
import fnmatch


# ─────────────────────────────────────────────────────────────────────────────
# Types (matching gstack PageRecord pattern)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ToolEntry:
    """A single tool_use or tool_result entry."""
    entry_type: str  # "tool_use" or "tool_result"
    timestamp: str
    tool_name: str
    tool_input: dict
    tool_output: Optional[dict] = None
    duration_ms: Optional[int] = None


@dataclass
class SessionSummary:
    """Structured summary of a session file."""
    slug: str
    session_id: str
    start_time: str
    end_time: str
    type: str = "session-summary"
    tool_calls: int = 0
    tool_results: int = 0
    unique_tools: list = field(default_factory=list)
    entries: list = field(default_factory=list)
    source_path: str = ""
    size_bytes: int = 0
    content_sha256: str = ""


@dataclass
class IngestState:
    """State tracking for incremental ingestion (gstack pattern)."""
    schema_version: int = 1
    last_writer: str = "ingest-sessions.py"
    last_full_walk: Optional[str] = None
    sessions: dict = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
SOURCE_DIR = BASE_DIR / "archive/data_chaos/data_chaos"
OUTPUT_DIR = BASE_DIR / "data/memory/synapses"
STATE_FILE = OUTPUT_DIR / "ingest-state.json"
SUMMARIES_FILE = OUTPUT_DIR / "session-summaries.jsonl"


# ─────────────────────────────────────────────────────────────────────────────
# Core Functions
# ─────────────────────────────────────────────────────────────────────────────

def ensure_output_dirs() -> None:
    """Create output directories if they don't exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def compute_file_hash(path: Path, max_bytes: int = 1024 * 1024) -> str:
    """Hash first 1MB of file (gstack pattern for change detection)."""
    try:
        with open(path, "rb") as f:
            data = f.read(max_bytes)
        return hashlib.sha256(data).hexdigest()
    except Exception:
        return ""


def get_file_mtime_ns(path: Path) -> int:
    """Get modification time in nanoseconds."""
    try:
        return int(path.stat().st_mtime * 1e6)
    except Exception:
        return 0


def file_changed_since_state(path: Path, state: IngestState) -> bool:
    """Check if file has changed since last ingest (gstack mtime fast-path)."""
    entry = state.sessions.get(str(path))
    if not entry:
        return True

    current_mtime = get_file_mtime_ns(path)
    if current_mtime != entry.get("mtime_ns"):
        # Check hash - if same content, just update mtime
        current_hash = compute_file_hash(path)
        if current_hash == entry.get("sha256"):
            entry["mtime_ns"] = current_mtime
            return False
        return True
    return False


def load_state() -> IngestState:
    """Load ingest state from file."""
    if not STATE_FILE.exists():
        return IngestState()

    try:
        data = json.loads(STATE_FILE.read_text())
        return IngestState(
            schema_version=data.get("schema_version", 1),
            last_writer=data.get("last_writer", "ingest-sessions.py"),
            last_full_walk=data.get("last_full_walk"),
            sessions=data.get("sessions", {})
        )
    except Exception:
        return IngestState()


def save_state(state: IngestState) -> None:
    """Save ingest state to file."""
    data = {
        "schema_version": state.schema_version,
        "last_writer": state.last_writer,
        "last_full_walk": state.last_full_walk,
        "sessions": state.sessions
    }
    STATE_FILE.write_text(json.dumps(data, indent=2))


def walk_session_files() -> Generator[Path, None, None]:
    """Walk source directory for ses_*.jsonl files."""
    if not SOURCE_DIR.exists():
        print(f"[warn] Source directory not found: {SOURCE_DIR}")
        return

    for entry in sorted(SOURCE_DIR.iterdir()):
        if entry.is_file() and fnmatch.fnmatch(entry.name, "ses_*.jsonl"):
            yield entry


def parse_session_file(path: Path) -> Optional[SessionSummary]:
    """Parse a session JSONL file and extract tool entries."""
    try:
        lines = path.read_text().splitlines()
        parsed_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                parsed_lines.append(json.loads(line))
            except json.JSONDecodeError:
                # Skip malformed lines (gstack handles partial)
                pass

        if not parsed_lines:
            return None

        # Extract session metadata
        session_id = path.stem  # e.g., "ses_2b42c3fefffesNT4puqZS2PEic"

        # Find start and end times
        timestamps = []
        tool_calls = 0
        tool_results = 0
        tool_names = set()
        entries = []

        for rec in parsed_lines:
            rec_type = rec.get("type", "")
            ts = rec.get("timestamp", "")
            if ts:
                timestamps.append(ts)

            if rec_type == "tool_use":
                tool_calls += 1
                tool_name = rec.get("tool_name", "unknown")
                tool_names.add(tool_name)
                entry = ToolEntry(
                    entry_type="tool_use",
                    timestamp=ts,
                    tool_name=tool_name,
                    tool_input=rec.get("tool_input", {})
                )
                entries.append(asdict(entry))

            elif rec_type == "tool_result":
                tool_results += 1
                tool_name = rec.get("tool_name", "unknown")
                # Calculate duration if we have both use and result timestamps
                # For now, just record the result
                entry = ToolEntry(
                    entry_type="tool_result",
                    timestamp=ts,
                    tool_name=tool_name,
                    tool_input=rec.get("tool_input", {}),
                    tool_output=rec.get("tool_output", {})
                )
                entries.append(asdict(entry))

        # Build summary
        start_time = min(timestamps) if timestamps else ""
        end_time = max(timestamps) if timestamps else ""

        # Create slug from session_id
        slug = f"sessions/{session_id}"

        # Get file stats
        stat = path.stat()
        content_hash = compute_file_hash(path)

        return SessionSummary(
            slug=slug,
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            tool_calls=tool_calls,
            tool_results=tool_results,
            unique_tools=sorted(tool_names),
            entries=entries,
            source_path=str(path),
            size_bytes=stat.st_size,
            content_sha256=content_hash
        )

    except Exception as e:
        print(f"[error] Failed to parse {path.name}: {e}")
        return None


def write_summary(summary: SessionSummary) -> None:
    """Write a session summary to the output JSONL file."""
    with open(SUMMARIES_FILE, "a") as f:
        f.write(json.dumps(asdict(summary), ensure_ascii=False) + "\n")


def ingest_session(path: Path, state: IngestState, dry_run: bool = False) -> bool:
    """Ingest a single session file."""
    if not file_changed_since_state(path, state):
        return False  # Skipped (unchanged)

    summary = parse_session_file(path)
    if not summary:
        return False  # Failed to parse

    if not dry_run:
        write_summary(summary)

    # Update state
    state.sessions[str(path)] = {
        "mtime_ns": get_file_mtime_ns(path),
        "sha256": summary.content_sha256,
        "ingested_at": datetime.now().isoformat(),
        "page_slug": summary.slug,
        "tool_calls": summary.tool_calls,
        "tool_results": summary.tool_results
    }

    return True


def probe_mode() -> dict:
    """Probe: count what would be ingested."""
    state = load_state()

    total_files = 0
    new_count = 0
    updated_count = 0
    unchanged_count = 0

    for path in walk_session_files():
        total_files += 1

        if str(path) not in state.sessions:
            new_count += 1
        elif file_changed_since_state(path, state):
            updated_count += 1
        else:
            unchanged_count += 1

    return {
        "total_files": total_files,
        "new_count": new_count,
        "updated_count": updated_count,
        "unchanged_count": unchanged_count
    }


def ingest_mode(incremental: bool = True, dry_run: bool = False, limit: int = 0) -> dict:
    """Ingest sessions: incremental (mtime fast-path) or bulk."""
    ensure_output_dirs()

    state = load_state()
    written = 0
    skipped = 0
    failed = 0

    # Clear summaries file for bulk mode (gstack overwrites)
    if not incremental and SUMMARIES_FILE.exists():
        SUMMARIES_FILE.unlink()

    for path in walk_session_files():
        if limit > 0 and written >= limit:
            break

        if incremental and not file_changed_since_state(path, state):
            skipped += 1
            continue

        try:
            success = ingest_session(path, state, dry_run)
            if success:
                written += 1
                print(f"[{written}] {path.name}")
            else:
                failed += 1
        except Exception as e:
            print(f"[error] {path.name}: {e}")
            failed += 1

    state.last_full_walk = datetime.now().isoformat()
    save_state(state)

    return {
        "written": written,
        "skipped": skipped,
        "failed": failed
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="N-Xyme session memory ingest")
    parser.add_argument("--probe", action="store_true", help="Count what would ingest, no writes")
    parser.add_argument("--incremental", action="store_true", default=True, help="mtime fast-path (default)")
    parser.add_argument("--bulk", action="store_true", help="Full walk, overwrite existing")
    parser.add_argument("--dry-run", action="store_true", help="Don't write, just report")
    parser.add_argument("--limit", type=int, default=0, help="Stop after N writes")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-file output")

    args = parser.parse_args()

    if args.probe:
        report = probe_mode()
        print("Session ingest probe")
        print("-" * 40)
        print(f"Total files:      {report['total_files']}")
        print(f"New (never seen): {report['new_count']}")
        print(f"Updated (mtime): {report['updated_count']}")
        print(f"Unchanged:        {report['unchanged_count']}")
        return

    incremental = not args.bulk
    result = ingest_mode(
        incremental=incremental,
        dry_run=args.dry_run,
        limit=args.limit
    )

    if not args.quiet:
        print(f"\nIngest complete ({'incremental' if incremental else 'bulk'}):")
        print(f"  written: {result['written']}")
        print(f"  skipped: {result['skipped']}")
        print(f"  failed:  {result['failed']}")
        print(f"  output:  {SUMMARIES_FILE}")


if __name__ == "__main__":
    main()