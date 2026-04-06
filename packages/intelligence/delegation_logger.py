"""Delegation Logger — Log and visualize delegation chains.

Ported from bin/delegation-log.sh.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from packages.intelligence.db import SQLiteStore
    HAS_STATE_DB = True
except ImportError:
    HAS_STATE_DB = False


def _log_sqlite(
    db_path: Path,
    task_id: str,
    agent: str,
    level: str,
    status: str,
    tokens: int,
    timestamp: str,
) -> str:
    """Log delegation to SQLite."""
    if not HAS_STATE_DB:
        return _log_jsonl(
            db_path.parent.parent, task_id, agent, level, status, tokens, timestamp
        )

    try:
        db = StateDB(db_path)
        delegation = Delegation(
            task_id=task_id,
            agent=agent,
            level=level,
            status=status,
            tokens=tokens,
            timestamp=timestamp,
        )
        db.add_delegation(delegation)
        return f"Logged: {task_id} → {agent} ({level}) → {status} ({tokens} tokens)"
    except Exception as e:
        return _log_jsonl(
            db_path.parent.parent, task_id, agent, level, status, tokens, timestamp
        )


def _log_jsonl(
    root_dir: Path,
    task_id: str,
    agent: str,
    level: str,
    status: str,
    tokens: int,
    timestamp: str,
) -> str:
    """Log delegation to JSONL file fallback."""
    log_dir = root_dir / ".sisyphus" / "delegation-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "delegations.jsonl"

    entry = {
        "timestamp": timestamp,
        "task_id": task_id,
        "agent": agent,
        "level": level,
        "status": status,
        "tokens": tokens,
    }

    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return f"Logged: {task_id} → {agent} ({level}) → {status} ({tokens} tokens)"


def _show_sqlite(db_path: Path, count: int) -> str:
    """Show recent delegations from SQLite."""
    if not HAS_STATE_DB:
        return _show_jsonl(db_path.parent.parent, count)

    try:
        db = StateDB(db_path)
        rows = db.get_delegations(limit=count)

        lines = [f"=== Recent Delegations (last {count}) ===", ""]
        for row in rows:
            ts = row.timestamp[:19]
            lines.append(
                f"  {ts:19s} | {row.task_id:20s} | {row.agent:20s} | "
                f"{row.level:4s} | {row.status:10s} | {row.tokens} tokens"
            )

        stats = db.get_delegation_stats()
        lines.append("")
        lines.append(f"Total delegations logged: {stats['total']}")
        if stats["total"] > 0:
            lines.append(
                f"Success rate: {stats['success_rate']}% ({stats['success']}/{stats['total']})"
            )

        return "\n".join(lines)
    except Exception:
        return _show_jsonl(db_path.parent.parent, count)


def _show_jsonl(root_dir: Path, count: int) -> str:
    """Show recent delegations from JSONL file."""
    log_file = root_dir / ".sisyphus" / "delegation-logs" / "delegations.jsonl"

    if not log_file.exists():
        return "No delegation logs found."

    lines = [f"=== Recent Delegations (last {count}) ===", ""]

    try:
        with open(log_file) as f:
            all_lines = [line.strip() for line in f if line.strip()]
    except Exception:
        return "No delegation logs found."

    for line in all_lines[-count:]:
        try:
            d = json.loads(line)
            tokens = d.get("tokens", 0)
            lines.append(
                f"  {d['timestamp'][:19]:19s} | {d['task_id']:20s} | "
                f"{d['agent']:20s} | {d['level']:4s} | {d['status']:10s} | "
                f"{tokens} tokens"
            )
        except json.JSONDecodeError:
            lines.append(f"  [CORRUPTED LINE] {line[:50]}...")

    total = len(all_lines)
    lines.append("")
    lines.append(f"Total delegations logged: {total}")

    if total > 0:
        success = sum(1 for line in all_lines if '"status": "success"' in line)
        rate = success * 100 // total
        lines.append(f"Success rate: {rate}% ({success}/{total})")

    return "\n".join(lines)


def log_delegation(
    task_id: str,
    agent: str,
    level: str,
    status: str,
    tokens: int = 0,
    root_dir: Path | None = None,
) -> str:
    """Log a delegation entry.

    Args:
        task_id: Unique task identifier.
        agent: Agent name that handled the task.
        level: Complexity level (e.g., L1, L2).
        status: Outcome status (success/fail).
        tokens: Token count used.
        root_dir: Project root directory.

    Returns:
        Confirmation message.
    """
    root_dir = Path(__file__).parent.parent.parent.parent

    state_db = root_dir / ".sisyphus" / "state.db"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if state_db.exists() and HAS_STATE_DB:
        try:
            db = StateDB(state_db)
            delegation = Delegation(
                task_id=task_id,
                agent=agent,
                level=level,
                status=status,
                tokens=tokens,
                timestamp=timestamp,
            )
            db.add_delegation(delegation)
            return f"Logged: {task_id} → {agent} ({level}) → {status} ({tokens} tokens)"
        except Exception:
            pass

    return _log_jsonl(root_dir, task_id, agent, level, status, tokens, timestamp)


def show_delegations(
    count: int = 10,
    root_dir: Path | None = None,
) -> str:
    """Show recent delegation logs.

    Args:
        count: Number of recent entries to show.
        root_dir: Project root directory.

    Returns:
        Formatted delegation log output.
    """
    if root_dir is None:
        root_dir = Path(__file__).parent.parent.parent.parent

    state_db = root_dir / ".sisyphus" / "state.db"

    if state_db.exists() and HAS_STATE_DB:
        return _show_sqlite(state_db, count)
    return _show_jsonl(root_dir, count)


class DelegationLogger:
    """Delegation logger with SQLite/JSONL fallback."""

    def __init__(self, root_dir: Path | None = None) -> None:
        self._root_dir = root_dir

    def log(
        self,
        task_id: str,
        agent: str,
        level: str,
        status: str,
        tokens: int = 0,
    ) -> str:
        return log_delegation(task_id, agent, level, status, tokens, self._root_dir)

    def show(self, count: int = 10) -> str:
        return show_delegations(count, self._root_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Delegation logger")
    subparsers = parser.add_subparsers(dest="action")

    log_parser = subparsers.add_parser("log", help="Log a delegation")
    log_parser.add_argument("task_id", help="Task ID")
    log_parser.add_argument("agent", help="Agent name")
    log_parser.add_argument("level", help="Complexity level")
    log_parser.add_argument("status", help="Status")
    log_parser.add_argument(
        "tokens", nargs="?", type=int, default=0, help="Token count"
    )

    show_parser = subparsers.add_parser("show", help="Show recent delegations")
    show_parser.add_argument(
        "count", nargs="?", type=int, default=10, help="Number to show"
    )

    args = parser.parse_args()

    if args.action == "log":
        result = log_delegation(
            args.task_id, args.agent, args.level, args.status, args.tokens
        )
        print(result)
    elif args.action == "show":
        result = show_delegations(args.count)
        print(result)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
