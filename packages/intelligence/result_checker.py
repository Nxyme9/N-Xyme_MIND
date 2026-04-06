"""Result Store Checker — Pre-flight cache for delegation system.

Ported from bin/check-results.sh.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from packages.intelligence.db import SQLiteStore  # type: ignore[import]

    HAS_STATE_DB = True
except ImportError:
    HAS_STATE_DB = False

# Import StateDB from src
try:
    from src.tools.state.db import StateDB  # type: ignore[import]
except ImportError:
    StateDB = None


TTL_MAP: dict[int, int] = {1: 1, 2: 4, 3: 24, 4: 24, 5: 24}
RESEARCH_TTL_HOURS = 168

RESEARCH_KEYWORDS = ["search", "find", "explore", "research", "document"]


def _get_ttl(task: str) -> int:
    """Get TTL hours based on task complexity and keywords."""
    from packages.intelligence.router.keyword import score_complexity  # type: ignore[import]

    level = score_complexity(task).level
    ttl = TTL_MAP.get(level, 24)

    task_lower = task.lower()
    if any(kw in task_lower for kw in RESEARCH_KEYWORDS):
        return RESEARCH_TTL_HOURS
    return ttl


def _parse_timestamp(ts: str) -> datetime | None:
    """Parse ISO timestamp, handling Z suffix."""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _match_task(query: str, stored: str) -> bool:
    """Check if query matches stored task description."""
    query_lower = query.lower()
    stored_lower = stored.lower()
    query_words = set(query_lower.split())
    stored_words = set(stored_lower.split())
    overlap = len(query_words & stored_words)
    return overlap >= 3 or stored_lower in query_lower or query_lower in stored_lower


def _check_sqlite(db_path: Path, task: str, ttl_hours: int) -> dict[str, Any]:
    """Check results in SQLite database."""
    if not HAS_STATE_DB or StateDB is None:
        return {"found": False, "reason": "db unavailable"}

    try:
        db = StateDB(db_path)
        rows = (
            db._get_conn()
            .execute("SELECT * FROM results ORDER BY timestamp DESC")
            .fetchall()
        )
    except Exception:
        return {"found": False, "reason": "db unavailable"}

    now = datetime.now(timezone.utc)

    for row in rows:
        result_time = _parse_timestamp(row["timestamp"])
        if result_time is None:
            continue
        age_hours = (now - result_time).total_seconds() / 3600
        if age_hours > ttl_hours:
            continue

        if _match_task(task, row["task_description"]):
            return {
                "found": True,
                "result_path": row["result_path"],
                "task_id": row["task_id"],
                "agent": row["agent"],
                "age_hours": round(age_hours, 1),
                "ttl_hours": ttl_hours,
                "success": bool(row["success"]),
            }

    return {"found": False, "reason": "no matching results"}


def _check_json(store_path: Path, task: str, ttl_hours: int) -> dict[str, Any]:
    """Check results in JSON file fallback."""
    if not store_path.exists():
        return {"found": False, "reason": "result store not found"}

    try:
        with open(store_path) as f:
            store = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"found": False, "reason": "store unavailable"}

    results = store.get("results", [])
    now = datetime.now(timezone.utc)

    for result in results:
        result_time = _parse_timestamp(result.get("timestamp", ""))
        if result_time is None:
            continue
        age_hours = (now - result_time).total_seconds() / 3600
        if age_hours > ttl_hours:
            continue

        task_desc = result.get("task_description", "")
        if _match_task(task, task_desc):
            return {
                "found": True,
                "result_path": result.get("result_path", ""),
                "task_id": result.get("task_id", ""),
                "agent": result.get("agent", ""),
                "age_hours": round(age_hours, 1),
                "ttl_hours": ttl_hours,
                "success": result.get("success", False),
            }

    return {"found": False, "reason": "no matching results"}


def check_results(task: str, root_dir: Path | None = None) -> dict[str, Any]:
    """Check for cached results matching a task.

    Args:
        task: Task description to search for.
        root_dir: Project root directory.

    Returns:
        Dict with found status and result details.
    """
    if not task:
        return {"found": False, "reason": "empty input"}

    if root_dir is None:
        root_dir = Path(__file__).parent.parent.parent.parent

    ttl_hours = _get_ttl(task)
    state_db = root_dir / ".sisyphus" / "state.db"
    result_store = root_dir / ".sisyphus" / "results" / "index.json"

    if state_db.exists():
        return _check_sqlite(state_db, task, ttl_hours)
    return _check_json(result_store, task, ttl_hours)


class ResultChecker:
    """Stateless result checker wrapper."""

    def __init__(self, root_dir: Path | None = None) -> None:
        self._root_dir = root_dir

    def check(self, task: str) -> dict[str, Any]:
        return check_results(task, self._root_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-flight result cache checker")
    parser.add_argument("task", nargs="?", default="", help="Task description")
    args = parser.parse_args()

    result = check_results(args.task)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
