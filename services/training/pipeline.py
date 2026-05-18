#!/usr/bin/env python3
"""
pipeline.py — Training Data & Orchestration Learning Pipeline Daemon.

Extracts success/failure patterns from tool telemetry and outcome logs,
generates training examples, clusters repeating failures, produces
"lessons learned" summaries, and computes per-agent improvement curves.

Four-phase pipeline:
  1. INGEST — Read telemetry + outcome logs, merge, deduplicate
  2. EXTRACT — Reward signals (+1, +0.5, -1), pattern clusters, failure flags
  3. LEARN  — Success-rate tracking (daily/weekly/monthly), curriculum generation
  4. STORE  — Write training examples, summaries, metrics

Usage:
  python3 pipeline.py                    # foreground, continuous
  python3 pipeline.py --once             # single pass, exit
  python3 pipeline.py --daemon           # background (nohup)
  python3 pipeline.py --retrospective 7  # generate lessons for last N days

References:
  - Sutton & Barto "Reinforcement Learning" — bandit algorithms (Section 2)
  - DeepMind "Reward is Enough" (Silver et al. 2021) — reward signal design
  - Mnih et al. "Human-level control through deep reinforcement learning"
    (Nature 2015) — experience replay for past-failure learning
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

# ── Paths ──────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(os.environ.get(
    "NX_PROJECT_ROOT",
    Path(__file__).resolve().parent.parent.parent,
))

TELEMETRY_FILE = PROJECT_ROOT / "data" / "telemetry" / "tool-calls.jsonl"
OUTCOMES_FILE = PROJECT_ROOT / "data" / "learning" / "outcomes" / "log.jsonl"
TRAINING_DIR = PROJECT_ROOT / "data" / "training"
EXAMPLES_FILE = TRAINING_DIR / "examples.jsonl"
CURRICULUM_FILE = TRAINING_DIR / "curriculum.json"
LESSONS_FILE = TRAINING_DIR / "lessons-learned.jsonl"
METRICS_FILE = TRAINING_DIR / "metrics.json"
PROCESSED_FILE = TRAINING_DIR / ".processed_ids"
POSITIVE_REWARDS_FILE = TRAINING_DIR / "positive_replays.jsonl"
LOG_DIR = PROJECT_ROOT / "data" / "training" / "logs"

POLL_INTERVAL = 120           # seconds between ingest passes
REPEAT_FAILURE_THRESHOLD = 3  # same agent+tool+error > N → flag
REWARD_SUCCESS = 1.0
REWARD_USER_CORRECTION = 0.5
REWARD_ESCALATION = -1.0
REWARD_FAILURE = -0.5

# ── Logging ────────────────────────────────────────────────────────────────


def setup_logging(daemon: bool = False) -> logging.Logger:
    """Configure dual logging: file + optional stdout."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "pipeline.log"

    handlers = [logging.FileHandler(str(log_file))]
    if not daemon:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )
    return logging.getLogger("training_pipeline")


# ── Phase 1: INGEST ────────────────────────────────────────────────────────


def _read_jsonl(path: Path, logger: logging.Logger) -> list[dict]:
    """Read all valid JSON lines from a file. Returns [] if file missing."""
    if not path.exists():
        logger.debug(f"File not found (skipping): {path}")
        return []
    entries = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(f"Skipping malformed JSON line in {path.name}")
    except OSError as e:
        logger.error(f"Error reading {path}: {e}")
    logger.debug(f"Read {len(entries)} entries from {path.name}")
    return entries


def _load_processed_ids() -> set[str]:
    """Load set of already-processed content hashes."""
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE) as f:
            return {line.strip() for line in f if line.strip()}
    return set()


def _save_processed_id(content_id: str):
    """Append a processed content ID to the tracker."""
    with open(PROCESSED_FILE, "a") as f:
        f.write(content_id + "\n")


def _entry_hash(entry: dict) -> str:
    """Stable hash for deduplication across telemetry and outcome logs."""
    raw = json.dumps(entry, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def ingest(logger: logging.Logger) -> list[dict]:
    """
    Phase 1: Read telemetry + outcome logs, deduplicate against
    processed_ids, return new entries as normalised training records.
    """
    processed = _load_processed_ids()

    # Primary source: tool telemetry
    telemetry = _read_jsonl(TELEMETRY_FILE, logger)

    # Fallback source: outcome logs
    outcomes = _read_jsonl(OUTCOMES_FILE, logger)

    merged: list[dict] = []
    for entry in telemetry + outcomes:
        e_hash = _entry_hash(entry)
        if e_hash in processed:
            continue

        # Normalise into a training record
        record = _normalise_entry(entry, logger)
        if record is None:
            continue

        record["_hash"] = e_hash
        merged.append(record)
        processed.add(e_hash)

    logger.info(f"Ingested {len(merged)} new records "
                f"({len(telemetry)} telemetry, {len(outcomes)} outcomes)")
    return merged


def _normalise_entry(entry: dict, logger: logging.Logger) -> Optional[dict]:
    """
    Convert a raw telemetry or outcome entry into a canonical training record.

    Telemetry format (expected):
      { "agent", "tool", "params", "result": {"status":"ok"|"error","error":...},
        "ts", "session_id" }

    Outcome format (from learning_bridge.py):
      { "agent", "task", "success": bool, "latency_ms", "quality_score",
        "task_type", "timestamp" }
    """
    agent = entry.get("agent") or entry.get("_agent", "unknown")
    ts = entry.get("ts") or entry.get("timestamp") or entry.get("timestamp", 0)
    session = entry.get("session_id", entry.get("session", "unknown"))

    # ── Telemetry-style entry ──────────────────────────────────────────
    if "tool" in entry:
        tool = entry.get("tool", "unknown")
        params = entry.get("params", {})
        result = entry.get("result", {})

        if isinstance(result, dict):
            status = result.get("status", "unknown")
            error = result.get("error", "")
        elif isinstance(result, str):
            status = "error" if "error" in result.lower() or "fail" in result.lower() else "ok"
            error = result
        else:
            status = "unknown"
            error = ""

        success = status == "ok"
        outcome = "success" if success else "failure"
        reward = REWARD_SUCCESS if success else REWARD_FAILURE

        return {
            "agent": agent,
            "task": f"tool:{tool}",
            "tool": tool,
            "params": json.dumps(params, default=str)[:500],
            "approach_used": f"call {tool} with {json.dumps(params, default=str)[:200]}",
            "outcome": outcome,
            "reward": reward,
            "error": str(error)[:500],
            "user_feedback": "",
            "corrected_approach": "",
            "session": session,
            "ts": ts,
            "source": "telemetry",
        }

    # ── Outcome-style entry ────────────────────────────────────────────
    if "success" in entry:
        success = bool(entry["success"])
        task = entry.get("task", entry.get("task_type", "unknown"))
        quality = entry.get("quality_score", None)

        reward = REWARD_SUCCESS if success else REWARD_FAILURE
        if not success and entry.get("escalated", False):
            reward = REWARD_ESCALATION

        return {
            "agent": agent,
            "task": str(task)[:500],
            "tool": entry.get("tool", "unknown"),
            "params": "",
            "approach_used": str(task)[:300],
            "outcome": "success" if success else "failure",
            "reward": reward,
            "error": "",
            "user_feedback": "",
            "corrected_approach": "",
            "session": session,
            "ts": ts,
            "source": "outcome",
        }

    logger.debug(f"Unrecognised entry format: {list(entry.keys())}")
    return None


# ── Phase 2: EXTRACT ───────────────────────────────────────────────────────
# ⚠️ TODO: Fix pair format before running again.
# Current issue: captures "failure" but NOT "corrected_tool" — empty corrections.
# Fix: When outcome == "failure" AND corrected_approach exists, emit:
#   {"query": approach_used, "expected_tool": corrected_approach, "outcome": "corrected"}
# This gives the Q0.5 head proper positive/negative contrastive pairs.
# -- Nxyme9, May 18 03:00 -- do this before re-running pipeline.


def compute_rewards(records: list[dict], logger: logging.Logger) -> list[dict]:
    """
    Phase 2a: Attach reward signals to each record.
    Also marks user corrections (reward = 0.5) and escalations (reward = -1.0).
    """
    for rec in records:
        outcome = rec.get("outcome", "unknown")

        if outcome == "success":
            rec["reward"] = REWARD_SUCCESS
        elif outcome == "failure":
            rec["reward"] = REWARD_FAILURE
            # If user feedback contains a correction, boost
            feedback = rec.get("user_feedback", "")
            if feedback and len(feedback) > 10:
                rec["reward"] = REWARD_USER_CORRECTION
                rec["corrected_approach"] = feedback[:500]
        else:
            rec["reward"] = 0.0

        # Escalation detection by reward override in normalise
        if rec.get("escalated", False):
            rec["reward"] = REWARD_ESCALATION

    logger.info(f"Rewards computed: "
                f"success={sum(1 for r in records if r['reward'] == REWARD_SUCCESS)}, "
                f"correction={sum(1 for r in records if r['reward'] == REWARD_USER_CORRECTION)}, "
                f"failure={sum(1 for r in records if r['reward'] == REWARD_FAILURE)}, "
                f"escalation={sum(1 for r in records if r['reward'] == REWARD_ESCALATION)}")
    return records


def extract_failure_clusters(records: list[dict],
                             logger: logging.Logger) -> list[dict]:
    """
    Phase 2b: Cluster similar failures by agent + tool + normalised error.
    Returns cluster objects with count, representative examples.
    """
    failures = [r for r in records if r["outcome"] == "failure"]
    clusters: dict[str, list[dict]] = defaultdict(list)

    for rec in failures:
        agent = rec.get("agent", "unknown")
        tool = rec.get("tool", "unknown")
        error = _normalise_error(rec.get("error", ""))
        key = f"{agent}|{tool}|{error}"
        clusters[key].append(rec)

    results = []
    for key, members in sorted(clusters.items(),
                               key=lambda x: len(x[1]), reverse=True):
        agent, tool, error = key.split("|", 2)
        results.append({
            "agent": agent,
            "tool": tool,
            "error_pattern": error,
            "count": len(members),
            "repeat_flag": len(members) >= REPEAT_FAILURE_THRESHOLD,
            "example_error": (members[0].get("error", "")[:300]
                              if members else ""),
            "sample_sessions": list({m.get("session", "") for m in members}),
        })

    flagged = sum(1 for c in results if c["repeat_flag"])
    logger.info(f"Extracted {len(results)} failure clusters, "
                f"{flagged} flagged as repeating (>{REPEAT_FAILURE_THRESHOLD}x)")
    return results


def _normalise_error(error: str) -> str:
    """Normalise an error string to cluster similar messages."""
    if not error:
        return "no_error"

    # Lowercase, strip leading/trailing whitespace
    e = error.lower().strip()

    # Collapse specific values like IDs, ports, paths, numbers
    e = re.sub(r'\b\d+\b', '{N}', e)
    e = re.sub(r'/[\w./-]+', '{path}', e)
    e = re.sub(r'[\w.-]+@[\w.-]+', '{email}', e)
    e = re.sub(r'https?://\S+', '{url}', e)

    # Collapse common error prefixes
    e = re.sub(r'^(error|exception|failed|fatal):\s*', '', e)

    # Take first 120 chars max
    return e[:120]


# ── Phase 3: LEARN ─────────────────────────────────────────────────────────


def compute_success_rates(records: list[dict],
                          logger: logging.Logger) -> dict[str, dict]:
    """
    Phase 3a: Per-agent success rates over time windows.
    Returns { agent: { daily, weekly, monthly, overall } }.
    """
    now = time.time()
    day_ago = now - 86400
    week_ago = now - 7 * 86400
    month_ago = now - 30 * 86400

    agent_stats: dict[str, dict] = defaultdict(lambda: {
        "total": 0, "successes": 0, "failures": 0,
        "daily": {"total": 0, "successes": 0},
        "weekly": {"total": 0, "successes": 0},
        "monthly": {"total": 0, "successes": 0},
        "tools": defaultdict(lambda: {"total": 0, "successes": 0}),
    })

    for rec in records:
        agent = rec.get("agent", "unknown")
        tool = rec.get("tool", "unknown")
        ts = rec.get("ts", 0)
        success = rec.get("outcome") == "success"

        s = agent_stats[agent]
        s["total"] += 1
        s["successes"] += success
        s["failures"] += (1 - success)
        s["tools"][tool]["total"] += 1
        s["tools"][tool]["successes"] += success

        if ts >= day_ago:
            s["daily"]["total"] += 1
            s["daily"]["successes"] += success
        if ts >= week_ago:
            s["weekly"]["total"] += 1
            s["weekly"]["successes"] += success
        if ts >= month_ago:
            s["monthly"]["total"] += 1
            s["monthly"]["successes"] += success

    # Convert to plain dicts
    result = {}
    for agent, stats in agent_stats.items():
        def rate(s, t):
            return round(s / max(t, 1), 4)
        result[agent] = {
            "overall": {
                "total": stats["total"],
                "successes": stats["successes"],
                "failures": stats["failures"],
                "success_rate": rate(stats["successes"], stats["total"]),
            },
            "daily": {
                "total": stats["daily"]["total"],
                "successes": stats["daily"]["successes"],
                "success_rate": rate(stats["daily"]["successes"],
                                     stats["daily"]["total"]),
            },
            "weekly": {
                "total": stats["weekly"]["total"],
                "successes": stats["weekly"]["successes"],
                "success_rate": rate(stats["weekly"]["successes"],
                                     stats["weekly"]["total"]),
            },
            "monthly": {
                "total": stats["monthly"]["total"],
                "successes": stats["monthly"]["successes"],
                "success_rate": rate(stats["monthly"]["successes"],
                                     stats["monthly"]["total"]),
            },
            "tool_rates": {
                t: rate(v["successes"], v["total"])
                for t, v in stats["tools"].items()
            },
        }

    logger.info(f"Success rates computed for {len(result)} agents")
    return result


def generate_curriculum(failure_clusters: list[dict],
                        success_rates: dict[str, dict],
                        logger: logging.Logger) -> list[dict]:
    """
    Phase 3b: Generate a curriculum — which tasks should each agent
    practice based on failure patterns and low success rates.

    Returns list of { agent, task, priority, failure_count, suggested_focus }.
    """
    curriculum = []

    for cluster in failure_clusters:
        if not cluster["repeat_flag"]:
            continue

        agent = cluster["agent"]
        tool = cluster["tool"]
        error = cluster["error_pattern"]
        count = cluster["count"]

        # Check current success rate for this tool
        agent_rates = success_rates.get(agent, {})
        tool_rates = agent_rates.get("tool_rates", {})
        tool_rate = tool_rates.get(tool, 0.0)

        priority = "high" if count >= 5 else "medium"
        if tool_rate < 0.3:
            priority = "critical"

        curriculum.append({
            "agent": agent,
            "task_type": f"tool:{tool}",
            "focus_error": error,
            "failure_count": count,
            "current_success_rate": tool_rate,
            "priority": priority,
            "suggested_focus": (
                f"Practice '{tool}' calls — {count} failures with '{error}'. "
                f"Current success rate: {tool_rate:.0%}. "
                f"Suggested drill: {_suggest_drill(tool, error)}"
            ),
        })

    # Also add agents with low overall success rates, even if no cluster
    for agent, rates in success_rates.items():
        overall = rates.get("overall", {})
        if overall.get("total", 0) < 5:
            continue  # too few data points
        sr = overall.get("success_rate", 1.0)
        if sr < 0.5:
            # Check if already represented
            already = any(c["agent"] == agent for c in curriculum)
            if not already:
                curriculum.append({
                    "agent": agent,
                    "task_type": "general",
                    "focus_error": "low_overall_success",
                    "failure_count": overall.get("failures", 0),
                    "current_success_rate": sr,
                    "priority": "high",
                    "suggested_focus": (
                        f"Overall success rate {sr:.0%} ({overall['failures']}/{overall['total']} failures). "
                        f"Review recent failures and practice fundamentals."
                    ),
                })

    curriculum.sort(key=lambda c: {"critical": 0, "high": 1,
                                    "medium": 2, "low": 3}.get(c["priority"], 4))
    logger.info(f"Generated curriculum with {len(curriculum)} items")
    return curriculum


def _suggest_drill(tool: str, error: str) -> str:
    """Map a tool+error to a suggested practice drill."""
    tool_lower = tool.lower()
    error_lower = error.lower()

    if "file_read" in tool_lower or "file_write" in tool_lower:
        return "Verify file paths before read/write. Check permissions."
    if "delegate" in tool_lower or "task" in tool_lower:
        return "Verify agent name exists in config. Use delegate_task not task()."
    if "search" in tool_lower or "grep" in tool_lower or "glob" in tool_lower:
        return "Check regex syntax. Use correct pattern format."
    if "timeout" in error_lower or "time out" in error_lower or "timed out" in error_lower:
        return "Set explicit timeouts. Break long tasks into smaller ones."
    if "permission" in error_lower or "denied" in error_lower or "forbidden" in error_lower:
        return "Check agent tools.json for this tool in allowed list."
    if "not found" in error_lower or "missing" in error_lower:
        return "Verify existence before referencing. Use glob/grep first."
    if "config" in error_lower or "sync" in error_lower:
        return "Run config_sync after config edits. Validate with config_validate."

    return f"Analyse and correct '{error}' errors during '{tool}' calls. Document fix for reuse."


# ── Phase 4: STORE ─────────────────────────────────────────────────────────


def store_examples(records: list[dict], logger: logging.Logger) -> int:
    """Append new training examples to examples.jsonl."""
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(EXAMPLES_FILE, "a") as f:
        for rec in records:
            example = {
                "agent": rec.get("agent", "unknown"),
                "task": rec.get("task", ""),
                "approach_used": rec.get("approach_used", ""),
                "outcome": rec.get("outcome", "unknown"),
                "reward": rec.get("reward", 0.0),
                "user_feedback": rec.get("user_feedback", ""),
                "corrected_approach": rec.get("corrected_approach", ""),
                "tool": rec.get("tool", "unknown"),
                "error": rec.get("error", "")[:500],
                "source": rec.get("source", "unknown"),
                "ts": rec.get("ts", 0),
            }
            f.write(json.dumps(example, ensure_ascii=False) + "\n")
            count += 1
    logger.info(f"Stored {count} training examples to {EXAMPLES_FILE}")
    return count


def store_curriculum(curriculum: list[dict], logger: logging.Logger):
    """Write curriculum as JSON."""
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    with open(CURRICULUM_FILE, "w") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "total_items": len(curriculum),
            "items": curriculum,
        }, f, indent=2, ensure_ascii=False)
    logger.info(f"Curriculum written to {CURRICULUM_FILE} ({len(curriculum)} items)")


def store_lessons(failure_clusters: list[dict],
                  success_rates: dict[str, dict],
                  logger: logging.Logger) -> int:
    """
    Generate and store "lessons learned" summaries.
    Each lesson is a natural-language actionable insight derived from data.
    """
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    count = 0

    for cluster in failure_clusters:
        if not cluster["repeat_flag"]:
            continue
        agent = cluster["agent"]
        tool = cluster["tool"]
        error_pat = cluster["error_pattern"]
        cnt = cluster["count"]

        lesson = {
            "type": "repeated_failure",
            "agent": agent,
            "tool": tool,
            "error_pattern": error_pat,
            "failure_count": cnt,
            "lesson": (
                f"{agent} has failed {cnt}x during '{tool}' calls "
                f"with error pattern '{error_pat[:80]}'. "
                f"Recommended fix: {_suggest_drill(tool, error_pat)}"
            ),
            "generated_at": datetime.now().isoformat(),
        }
        with open(LESSONS_FILE, "a") as f:
            f.write(json.dumps(lesson, ensure_ascii=False) + "\n")
        count += 1

    # Agent-level improvement insights
    for agent, rates in success_rates.items():
        overall = rates.get("overall", {})
        daily = rates.get("daily", {})
        weekly = rates.get("weekly", {})

        if overall.get("total", 0) < 10:
            continue

        # Trend: compare daily to weekly
        daily_rate = daily.get("success_rate", 0)
        weekly_rate = weekly.get("success_rate", 0)

        if daily_rate < weekly_rate - 0.1 and daily.get("total", 0) >= 3:
            lesson = {
                "type": "declining_trend",
                "agent": agent,
                "tool": "all",
                "error_pattern": "declining_success_rate",
                "failure_count": overall.get("failures", 0),
                "lesson": (
                    f"{agent} success rate declining: "
                    f"{daily_rate:.0%} today vs {weekly_rate:.0%} weekly. "
                    f"Review recent {daily.get('total', 0)} tasks for issues."
                ),
                "generated_at": datetime.now().isoformat(),
            }
            with open(LESSONS_FILE, "a") as f:
                f.write(json.dumps(lesson, ensure_ascii=False) + "\n")
            count += 1

    logger.info(f"Generated {count} lessons learned")
    return count


def store_metrics(success_rates: dict[str, dict],
                  failure_clusters: list[dict],
                  curriculum: list[dict],
                  records_processed: int,
                  logger: logging.Logger):
    """Write aggregate metrics snapshot."""
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    metrics = {
        "generated_at": datetime.now().isoformat(),
        "records_processed_total": records_processed,
        "agents": len(success_rates),
        "failure_clusters": len(failure_clusters),
        "flagged_repeats": sum(1 for c in failure_clusters if c["repeat_flag"]),
        "curriculum_items": len(curriculum),
        "agent_summary": {
            agent: {
                "overall_success_rate": rates.get("overall", {}).get("success_rate", 0),
                "total_tasks": rates.get("overall", {}).get("total", 0),
                "daily_rate": rates.get("daily", {}).get("success_rate", 0),
                "weekly_rate": rates.get("weekly", {}).get("success_rate", 0),
            }
            for agent, rates in success_rates.items()
        },
    }
    with open(METRICS_FILE, "w") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    logger.info(f"Metrics written to {METRICS_FILE}")


# ── Positive Replay Buffer (Experience Replay) ─────────────────────────────

def update_replay_buffer(records: list[dict], logger: logging.Logger) -> int:
    """
    Maintain a replay buffer of high-reward experiences for contrastive
    learning (Mnih et al. 2015). Keeps successful outcomes + corrections
    for later training.
    """
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(POSITIVE_REWARDS_FILE, "a") as f:
        for rec in records:
            reward = rec.get("reward", 0)
            if reward >= REWARD_USER_CORRECTION:
                replay = {
                    "agent": rec.get("agent", "unknown"),
                    "task": rec.get("task", ""),
                    "approach": rec.get("approach_used", ""),
                    "correction": rec.get("corrected_approach", ""),
                    "reward": reward,
                    "ts": rec.get("ts", 0),
                }
                f.write(json.dumps(replay, ensure_ascii=False) + "\n")
                count += 1
    if count:
        logger.info(f"Added {count} positive examples to replay buffer")
    return count


# ── Retrospective ──────────────────────────────────────────────────────────


def generate_retrospective(days: int, logger: logging.Logger) -> dict:
    """
    Generate a retrospective report for the last N days.
    Reads all existing examples and produces a summary.
    """
    cutoff = time.time() - days * 86400
    records = _read_jsonl(EXAMPLES_FILE, logger)
    recent = [r for r in records if r.get("ts", 0) >= cutoff]

    if not recent:
        return {
            "days": days,
            "records_found": 0,
            "message": f"No training data in the last {days} days."
        }

    clusters = extract_failure_clusters(recent, logger)
    rates = compute_success_rates(recent, logger)
    curriculum = generate_curriculum(clusters, rates, logger)

    report = {
        "days": days,
        "records_found": len(recent),
        "agents_analysed": len(rates),
        "failure_clusters": len(clusters),
        "repeating_failures": [c for c in clusters if c["repeat_flag"]],
        "agent_rates": {
            a: r["overall"] for a, r in rates.items()
        },
        "curriculum_items": curriculum,
        "summary": (
            f"Analysed {len(recent)} training records across {len(rates)} agents "
            f"over the last {days} days. Found {len(clusters)} failure patterns "
            f"({sum(1 for c in clusters if c['repeat_flag'])} repeating). "
            f"Curriculum: {len(curriculum)} practice tasks assigned."
        ),
    }

    logger.info(f"Retrospective ({days}d): {report['summary']}")
    return report


# ── Main Pipeline ──────────────────────────────────────────────────────────


def run_pipeline(logger: logging.Logger,
                 retrospective_days: int = 0) -> dict:
    """
    Execute a single pass of the full pipeline.
    Returns summary dict of what was done.
    """
    logger.info("─" * 50)
    logger.info("TRAINING PIPELINE — Starting pass")
    logger.info("─" * 50)

    # Phase 1: INGEST
    logger.info("[1/4] INGEST — Reading telemetry and outcomes...")
    records = ingest(logger)
    if not records:
        logger.info("No new records to process. Skipping remaining phases.")
        return {"records_processed": 0, "message": "no_new_data"}

    # Phase 2: EXTRACT
    logger.info(f"[2/4] EXTRACT — Computing rewards and clusters...")
    records = compute_rewards(records, logger)
    failure_clusters = extract_failure_clusters(records, logger)

    # Phase 3: LEARN
    logger.info(f"[3/4] LEARN — Computing rates and curriculum...")
    success_rates = compute_success_rates(records, logger)
    curriculum = generate_curriculum(failure_clusters, success_rates, logger)

    # Phase 4: STORE
    logger.info(f"[4/4] STORE — Writing outputs...")
    examples_written = store_examples(records, logger)
    store_curriculum(curriculum, logger)
    lessons_written = store_lessons(failure_clusters, success_rates, logger)
    store_metrics(success_rates, failure_clusters, curriculum,
                  examples_written, logger)
    replay_written = update_replay_buffer(records, logger)

    # Track processed IDs
    for rec in records:
        if "_hash" in rec:
            _save_processed_id(rec["_hash"])

    summary = {
        "records_processed": len(records),
        "examples_written": examples_written,
        "failure_clusters": len(failure_clusters),
        "flagged_repeats": sum(1 for c in failure_clusters if c["repeat_flag"]),
        "curriculum_items": len(curriculum),
        "lessons_written": lessons_written,
        "replay_examples": replay_written,
        "agents_analysed": len(success_rates),
    }

    logger.info("─" * 50)
    logger.info(f"PIPELINE COMPLETE — {json.dumps(summary)}")
    logger.info("─" * 50)

    # Optionally run retrospective
    if retrospective_days > 0:
        logger.info(f"Generating {retrospective_days}-day retrospective...")
        retro = generate_retrospective(retrospective_days, logger)
        retro_path = TRAINING_DIR / f"retrospective-{retrospective_days}d.json"
        with open(retro_path, "w") as f:
            json.dump(retro, f, indent=2, ensure_ascii=False)
        logger.info(f"Retrospective written to {retro_path}")

    return summary


# ── Daemon loop ────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="N-Xyme Training Data Pipeline Daemon"
    )
    parser.add_argument("--once", action="store_true",
                        help="Run single pass and exit")
    parser.add_argument("--daemon", action="store_true",
                        help="Run in background (nohup)")
    parser.add_argument("--interval", type=int, default=POLL_INTERVAL,
                        help=f"Poll interval in seconds (default: {POLL_INTERVAL})")
    parser.add_argument("--retrospective", type=int, default=0,
                        help="Generate retrospective for N days after pipeline")
    args = parser.parse_args()

    logger = setup_logging(daemon=args.daemon)
    logger.info("=" * 50)
    logger.info("TRAINING DATA PIPELINE DAEMON")
    logger.info("=" * 50)
    logger.info(f"Telemetry:  {TELEMETRY_FILE}")
    logger.info(f"Outcomes:   {OUTCOMES_FILE}")
    logger.info(f"Training:   {EXAMPLES_FILE}")
    logger.info(f"Curriculum: {CURRICULUM_FILE}")
    logger.info(f"Lessons:    {LESSONS_FILE}")
    logger.info(f"Replay:     {POSITIVE_REWARDS_FILE}")
    logger.info(f"Interval:   {args.interval}s")

    # Ensure directories
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if args.once:
        result = run_pipeline(logger, retrospective_days=args.retrospective)
        print(json.dumps(result, indent=2))
        return

    # Continuous loop
    logger.info(f"Watching for new data every {args.interval}s...")
    while True:
        try:
            run_pipeline(logger)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
        time.sleep(args.interval)

    logger.info("Pipeline daemon stopped.")


if __name__ == "__main__":
    main()
