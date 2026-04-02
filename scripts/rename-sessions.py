#!/usr/bin/env python3
"""
Rename OpenCode sessions with Agent-N prefix format.

Updates the title column in SessionMetadata table of opencode.db
for predefined sessions. Uses parameterized SQL queries to prevent injection.

Usage:
    python rename-sessions.py              # Rename all sessions
    python rename-sessions.py --dry-run    # Preview changes only
    python rename-sessions.py --db PATH    # Custom database path
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# Session ID -> New Title mappings
SESSION_MAP = {
    "ses_2fcbf7bc": "Agent-1 - N-Xyme Catalyst JARVIS Build",
    "ses_2fbd64e6": "Agent-2 - Prometheus Planning",
    "ses_2fcbf8f2": "Agent-3 - Build Tasks",
    "ses_2fcbf8d7": "Agent-4 - Prometheus Build",
    "ses_2fcbf8b8": "Agent-5 - Build Session",
    "ses_2fcbf899": "Agent-6 - Build Session",
    "ses_2fcbf8608": "Agent-7 - MCP Local Tools",
    "ses_2fcbf7f9a": "Agent-8 - MCP Utility",
    "ses_2fcbf87c7": "Agent-9 - MCP Web Tools",
    "ses_2fcbf7d58": "Agent-10 - Performance Tuning",
}

# Possible column names for session ID in the table
SESSION_ID_COLUMNS = ["session_id", "session", "id"]


def find_opencode_db() -> Path | None:
    """Find opencode.db in standard locations."""
    candidates = [
        Path.home() / ".config" / "opencode" / "opencode.db",
        Path.home() / ".local" / "share" / "opencode" / "opencode.db",
        Path(".config") / "opencode" / "opencode.db",
    ]
    for path in candidates:
        if path.exists():
            return path.resolve()
    return None


def detect_session_column(conn: sqlite3.Connection) -> str | None:
    """Detect which column holds the session ID."""
    cursor = conn.execute("SELECT name FROM pragma_table_info('SessionMetadata')")
    columns = {row[0].lower() for row in cursor.fetchall()}
    for col in SESSION_ID_COLUMNS:
        if col.lower() in columns:
            return col
    return None


def get_current_title(conn: sqlite3.Connection, session_col: str, session_id: str) -> str | None:
    """Get current title for a session."""
    cursor = conn.execute(
        f"SELECT title FROM SessionMetadata WHERE {session_col} = ?",
        (session_id,),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def rename_session(
    conn: sqlite3.Connection,
    session_col: str,
    session_id: str,
    new_title: str,
    dry_run: bool = False,
) -> bool:
    """Rename a single session. Returns True if session existed."""
    current = get_current_title(conn, session_col, session_id)
    if current is None:
        return False

    if not dry_run:
        conn.execute(
            f"UPDATE SessionMetadata SET title = ? WHERE {session_col} = ?",
            (new_title, session_id),
        )
    return True


def rename_all(db_path: Path, dry_run: bool = False) -> tuple[int, int]:
    """Rename all sessions in SESSION_MAP. Returns (updated, total)."""
    conn = sqlite3.connect(str(db_path))
    try:
        session_col = detect_session_column(conn)
        if session_col is None:
            print("ERROR: Could not detect session ID column in SessionMetadata", file=sys.stderr)
            return 0, len(SESSION_MAP)

        updated = 0
        for session_id, new_title in SESSION_MAP.items():
            current_title = get_current_title(conn, session_col, session_id)
            if current_title is None:
                print(f"  SKIP  {session_id} - not found in database")
                continue

            if current_title == new_title:
                print(f"  SAME  {session_id} - already named '{new_title}'")
                updated += 1
                continue

            prefix = "DRY-RUN " if dry_run else ""
            print(f"  {prefix}UPDATE {session_id}")
            print(f"         FROM: {current_title}")
            print(f"         TO:   {new_title}")

            if not dry_run:
                conn.execute(
                    f"UPDATE SessionMetadata SET title = ? WHERE {session_col} = ?",
                    (new_title, session_id),
                )
            updated += 1

        if not dry_run:
            conn.commit()
        return updated, len(SESSION_MAP)
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Rename OpenCode sessions with Agent-N format")
    parser.add_argument("--db", type=Path, help="Path to opencode.db")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    args = parser.parse_args()

    # Resolve database path
    db_path = args.db or find_opencode_db()
    if db_path is None:
        print("ERROR: opencode.db not found in standard locations", file=sys.stderr)
        print("  Searched:", file=sys.stderr)
        print(f"    - {Path.home() / '.config' / 'opencode' / 'opencode.db'}", file=sys.stderr)
        print(
            f"    - {Path.home() / '.local' / 'share' / 'opencode' / 'opencode.db'}",
            file=sys.stderr,
        )
        sys.exit(2)

    print(f"Database: {db_path}")
    if args.dry_run:
        print("Mode: DRY RUN (no changes will be made)")
    print()

    updated, total = rename_all(db_path, dry_run=args.dry_run)

    print()
    if updated == total:
        print(f"SUCCESS: Renamed all {total} sessions")
    else:
        print(f"PARTIAL: Renamed {updated} of {total} sessions")

    sys.exit(0 if updated > 0 else 1)


if __name__ == "__main__":
    main()
