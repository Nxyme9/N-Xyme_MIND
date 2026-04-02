#!/usr/bin/env python3
"""
Global Todo Aggregator for OpenCode.

Aggregates todos from ALL sessions into ADHD-optimized views:
  - NOW:   3 highest-priority active tasks
  - TODAY: 7 tasks (active, no scroll)
  - WEEK:  20 tasks (full backlog)

Usage:
    python scripts/global-todos.py           # Human-readable dashboard
    python scripts/global-todos.py --json    # JSON output for piping
"""

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class TodoItem:
    """A single todo item with session origin metadata."""

    content: str
    status: str  # pending | in_progress | completed | cancelled
    priority: str  # high | medium | low
    session_id: str
    session_title: str = ""
    position: int = 0
    time_created: int = 0
    time_updated: int = 0


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
STATUS_ORDER = {"in_progress": 0, "pending": 1, "completed": 2, "cancelled": 3}

PRIORITY_ICONS = {"high": "[HIGH]", "medium": "[MED]", "low": "[LOW]"}
STATUS_ICONS = {
    "in_progress": "[~]",
    "pending": "[ ]",
    "completed": "[x]",
    "cancelled": "[-]",
}

NOW_LIMIT = 3
TODAY_LIMIT = 7
WEEK_LIMIT = 20


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def find_opencode() -> str:
    """Locate the opencode binary, checking PATH and common install locations."""
    # 1. Check PATH (works if opencode is in PATH)
    found = shutil.which("opencode")
    if found:
        return found

    # 2. Common Windows npm global locations (prefer .cmd on Windows)
    appdata = os.environ.get("APPDATA", "")
    candidates = [
        Path(appdata) / "npm" / "opencode.cmd",
        Path(appdata) / "npm" / "opencode",
        Path.home() / ".local" / "bin" / "opencode",
        Path("/usr/local/bin/opencode"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)

    print("[ERROR] 'opencode' not found. Ensure it is installed and in PATH.", file=sys.stderr)
    sys.exit(1)


def run_db_query(sql: str) -> list[dict]:
    """Execute a SQL query against the opencode database and return parsed JSON."""
    opencode_bin = find_opencode()
    print(f"DEBUG: run_db_query() using bin: {opencode_bin}", file=sys.stderr, flush=True)
    try:
        # Use shell=True on Windows for .cmd files
        use_shell = sys.platform == "win32"
        cmd = [opencode_bin, "db", sql, "--format", "json"]
        print(f"DEBUG: running command: {cmd}", file=sys.stderr, flush=True)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            shell=use_shell,
        )
        print(f"DEBUG: subprocess returned: {result.returncode}", file=sys.stderr, flush=True)
        if result.returncode != 0:
            print(f"[ERROR] DB query failed: {result.stderr.strip()}", file=sys.stderr)
            return []
        data = json.loads(result.stdout) if result.stdout.strip() else []
        print(f"DEBUG: parsed {len(data)} items from JSON", file=sys.stderr, flush=True)
        return data
    except FileNotFoundError:
        print("[ERROR] 'opencode' not found in PATH", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("[ERROR] DB query timed out", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse DB output: {e}", file=sys.stderr)
        return []


def get_all_sessions() -> list[dict]:
    """List all sessions with metadata."""
    return run_db_query("SELECT id, title, time_updated FROM session ORDER BY time_updated DESC")


def get_all_todos() -> list[TodoItem]:
    """Fetch all todos joined with session titles."""
    print("DEBUG: get_all_todos() called", file=sys.stderr, flush=True)
    rows = run_db_query("""
        SELECT
            t.content,
            t.status,
            t.priority,
            t.session_id,
            s.title AS session_title,
            t.position,
            t.time_created,
            t.time_updated
        FROM todo t
        LEFT JOIN session s ON s.id = t.session_id
        ORDER BY t.time_updated DESC
    """)
    print(f"DEBUG: run_db_query() returned {len(rows)} rows", file=sys.stderr, flush=True)
    return [
        TodoItem(
            content=r.get("content", ""),
            status=r.get("status", "pending"),
            priority=r.get("priority", "medium"),
            session_id=r.get("session_id", ""),
            session_title=r.get("session_title", "unknown"),
            position=r.get("position", 0),
            time_created=r.get("time_created", 0),
            time_updated=r.get("time_updated", 0),
        )
        for r in rows
    ]


def sort_todos(todos: list[TodoItem]) -> list[TodoItem]:
    """Sort by priority (high first), then status (in_progress first)."""
    return sorted(
        todos,
        key=lambda t: (
            PRIORITY_ORDER.get(t.priority, 1),
            STATUS_ORDER.get(t.status, 1),
        ),
    )


def aggregate_todos() -> list[TodoItem]:
    """Fetch and sort all todos across sessions."""
    print("DEBUG: aggregate_todos() called", file=sys.stderr, flush=True)
    todos = get_all_todos()
    print(f"DEBUG: get_all_todos() returned {len(todos)} items", file=sys.stderr, flush=True)
    return sort_todos(todos)


# ---------------------------------------------------------------------------
# View formatters
# ---------------------------------------------------------------------------


def _short_session(title: str, max_len: int = 20) -> str:
    """Truncate session title for display."""
    return title[:max_len] + "..." if len(title) > max_len else title


def format_now_view(todos: list[TodoItem]) -> list[TodoItem]:
    """NOW view: top 3 active (in_progress or pending) tasks."""
    active = [t for t in todos if t.status in ("in_progress", "pending")]
    return active[:NOW_LIMIT]


def format_today_view(todos: list[TodoItem]) -> list[TodoItem]:
    """TODAY view: top 7 non-completed tasks."""
    active = [t for t in todos if t.status not in ("completed", "cancelled")]
    return active[:TODAY_LIMIT]


def format_week_view(todos: list[TodoItem]) -> list[TodoItem]:
    """WEEK view: top 20 tasks (all statuses)."""
    return todos[:WEEK_LIMIT]


def print_view(title: str, todos: list[TodoItem], limit: int) -> None:
    """Print a single view section."""
    items = todos[:limit]
    print(f"\n=== {title} ({len(items)} tasks) ===")
    if not items:
        print("  (none)")
        return
    for i, t in enumerate(items, 1):
        pri = PRIORITY_ICONS.get(t.priority, "[?]")
        sta = STATUS_ICONS.get(t.status, "[?]")
        session = _short_session(t.session_title)
        content = t.content[:60] + "..." if len(t.content) > 60 else t.content
        print(f"  {i}. {pri} {sta} {content}")
        print(f"     from: {session}")


def print_dashboard(todos: list[TodoItem]) -> None:
    """Print the full ADHD-optimized dashboard."""
    print("=" * 60)
    print("  GLOBAL TODO DASHBOARD")
    print("=" * 60)

    print_view("NOW (Top 3 Priority)", format_now_view(todos), NOW_LIMIT)
    print_view("TODAY (Max 7)", format_today_view(todos), TODAY_LIMIT)
    print_view("WEEK (Max 20)", format_week_view(todos), WEEK_LIMIT)

    # Summary
    sessions = len({t.session_id for t in todos})
    print(f"\n{'=' * 60}")
    print(f"  Total: {len(todos)} todos across {sessions} sessions")
    print(f"{'=' * 60}\n")


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def to_json(todos: list[TodoItem]) -> dict:
    """Build JSON-serializable output with all three views."""
    return {
        "now": [asdict(t) for t in format_now_view(todos)],
        "today": [asdict(t) for t in format_today_view(todos)],
        "week": [asdict(t) for t in format_week_view(todos)],
        "total": len(todos),
        "sessions": len({t.session_id for t in todos}),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    json_mode = "--json" in sys.argv

    print("DEBUG: Starting main()", file=sys.stderr, flush=True)
    todos = aggregate_todos()
    print(f"DEBUG: Found {len(todos)} todos", file=sys.stderr, flush=True)

    if not todos:
        if json_mode:
            print(json.dumps({"now": [], "today": [], "week": [], "total": 0, "sessions": 0}))
        else:
            print("No todos found across any sessions.")
        return

    if json_mode:
        print(json.dumps(to_json(todos), indent=2))
    else:
        print_dashboard(todos)


if __name__ == "__main__":
    main()
