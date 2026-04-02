"""
athena.core.skill_telemetry
============================

Lightweight skill/protocol usage tracking via JSONL append log.
Adapted from Zeude's ClickHouse-based Sensing Layer — simplified
for Athena's solo-operator, local-first architecture.

Philosophy: "You can't improve what you don't measure."

Usage:
    from athena.core.skill_telemetry import log_skill_invocation, get_skill_stats

    log_skill_invocation("Protocol 367", "2026-02-23-06", trigger="auto")
    stats = get_skill_stats(days=30)
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from athena.core.config import get_project_root


# --- CONFIGURATION ---


def _get_telemetry_path() -> Path:
    """Returns the path to the skill usage JSONL log."""
    root = get_project_root()
    telemetry_dir = root / ".athena"
    telemetry_dir.mkdir(parents=True, exist_ok=True)
    return telemetry_dir / "skill_usage.jsonl"


# --- CORE API ---


def log_skill_invocation(
    skill_name: str,
    session_id: str = "",
    trigger: str = "manual",
    metadata: Optional[dict] = None,
) -> dict:
    """
    Append a skill invocation record to the JSONL log.

    Args:
        skill_name: Name of the skill/protocol invoked (e.g., "Protocol 367")
        session_id: Current session ID (e.g., "2026-02-23-06")
        trigger: How it was invoked — "auto" (Phase 3 weaving) or "manual" (user called)
        metadata: Optional dict of extra context

    Returns:
        The record that was logged.
    """
    record = {
        "skill": skill_name,
        "session": session_id,
        "timestamp": datetime.now().isoformat(),
        "trigger": trigger,
    }
    if metadata:
        record["meta"] = metadata

    path = _get_telemetry_path()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return record


def log_skill_change(
    skill_name: str,
    change_type: str = "modified",
    filepath: str = "",
) -> dict:
    """
    Log when a skill file is added, modified, or deleted.
    Used by the daemon's hot-reload watcher.

    Args:
        skill_name: Name of the skill that changed
        change_type: "added" | "modified" | "deleted"
        filepath: Path to the skill file
    """
    record = {
        "event": "skill_change",
        "skill": skill_name,
        "change": change_type,
        "filepath": filepath,
        "timestamp": datetime.now().isoformat(),
    }

    path = _get_telemetry_path()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return record


def _read_log(days: Optional[int] = None) -> list[dict]:
    """
    Read the JSONL log and return records, optionally filtered by recency.

    Args:
        days: If set, only return records from the last N days.
    """
    path = _get_telemetry_path()
    if not path.exists():
        return []

    cutoff = None
    if days is not None:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                # Filter: only invocations (not skill_change events)
                if record.get("event") == "skill_change":
                    continue
                if cutoff and record.get("timestamp", "") < cutoff:
                    continue
                records.append(record)
            except json.JSONDecodeError:
                continue

    return records


def get_skill_stats(days: int = 30) -> dict:
    """
    Get aggregated skill usage statistics.

    Returns:
        {
            "total_invocations": int,
            "unique_skills": int,
            "skills": {
                "Protocol 367": {
                    "count": 12,
                    "last_used": "2026-02-23T05:00:00",
                    "sessions": ["2026-02-23-06", ...],
                    "auto_pct": 0.75
                },
                ...
            },
            "top_skills": [("Protocol 367", 12), ...],
        }
    """
    records = _read_log(days=days)

    skills: dict = {}
    for r in records:
        name = r.get("skill", "unknown")
        if name not in skills:
            skills[name] = {
                "count": 0,
                "last_used": "",
                "sessions": set(),
                "auto_count": 0,
            }
        skills[name]["count"] += 1
        skills[name]["last_used"] = max(
            skills[name]["last_used"], r.get("timestamp", "")
        )
        if r.get("session"):
            skills[name]["sessions"].add(r["session"])
        if r.get("trigger") == "auto":
            skills[name]["auto_count"] += 1

    # Serialize sets to lists and compute auto_pct
    result_skills = {}
    for name, data in skills.items():
        count = data["count"]
        result_skills[name] = {
            "count": count,
            "last_used": data["last_used"],
            "sessions": sorted(data["sessions"]),
            "auto_pct": round(data["auto_count"] / count, 2) if count > 0 else 0,
        }

    top_skills = sorted(
        result_skills.items(), key=lambda x: x[1]["count"], reverse=True
    )

    return {
        "total_invocations": len(records),
        "unique_skills": len(result_skills),
        "skills": result_skills,
        "top_skills": [(name, data["count"]) for name, data in top_skills[:10]],
    }


def get_dead_skills(
    known_skills: Optional[list[str]] = None, days: int = 90
) -> list[str]:
    """
    Return skills from the known_skills list that have never been invoked.

    Args:
        known_skills: List of all known skill/protocol names.
                      If None, returns an empty list (no baseline to compare).
        days: Timeframe to check for invocations.

    Returns:
        List of skill names that have 0 invocations in the period.
    """
    if not known_skills:
        return []

    stats = get_skill_stats(days=days)
    used = set(stats["skills"].keys())

    return [s for s in known_skills if s not in used]
