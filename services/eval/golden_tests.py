#!/usr/bin/env python3
"""Golden test suite — measure routing accuracy."""
import subprocess
import json
import sys
import os
from datetime import datetime

DAEMON = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/services/mojo-router/src/daemon"
MEMORY_DIR = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/data/memory"
TRIGGER_FILE = os.path.join(MEMORY_DIR, "retrain.trigger")
RESULTS_FILE = os.path.join(MEMORY_DIR, "golden_results.jsonl")
ACCURACY_THRESHOLD = 90

# 25 queries (one per tool) — golden test corpus
GOLDEN = [
    ("start a new session", "session_start"),
    ("check session status", "session_status"),
    ("continue the last session", "continue_session"),
    ("welcome me back", "welcome_back"),
    ("what should I do next", "next_step"),
    ("save this note to memory", "memory_write"),
    ("read my notes", "memory_read"),
    ("list all memory keys", "memory_list"),
    ("prune context to save space", "context_prune"),
    ("show recent activity", "audit_log_recent"),
    ("start ralph loop", "ralph_start"),
    ("check ralph status", "ralph_status"),
    ("iterate ralph loop", "ralph_iterate"),
    ("cancel ralph loop", "ralph_cancel"),
    # ("inject dictated text", "dictate_inject"),  # REMOVED — voice dictation disconnected
    ("delegate to hephaestus", "delegate_to_hephaestus"),
    ("show project structure", "project_map"),
    ("read multiple files", "batch_read"),
    ("verify code quality", "code_verify"),
    ("delete this file safely", "safe_delete"),
    ("restore from trash", "trash_restore"),
    ("create new hephaestus task", "hephaestus_new_task"),
    ("ask for help", "ask"),
    ("log this decision", "decision_log"),
    ("delegate task to agent", "delegate_task"),
]


def run_daemon(query: str, msg_id: str = "golden") -> dict:
    """Send query to daemon and return parsed JSON response."""
    req = json.dumps({"type": "route", "query": query, "id": msg_id})
    proc = subprocess.run(
        [DAEMON],
        input=req + "\n",
        capture_output=True,
        text=True,
        timeout=5
    )
    if proc.returncode != 0:
        return {"type": "error", "message": proc.stderr}
    return json.loads(proc.stdout.strip())


def run_all() -> float:
    """Run all golden tests and return accuracy percentage."""
    correct = 0
    total = len(GOLDEN)
    results = []

    print("=" * 70)
    print("GOLDEN TEST SUITE — Routing Accuracy Benchmark")
    print("=" * 70)

    for i, (query, expected) in enumerate(GOLDEN, 1):
        result = run_daemon(query, f"golden_{i}")
        actual = result.get("tool", "")

        ok = actual == expected
        if ok:
            correct += 1
            status = "✅"
        else:
            status = "❌"

        print(f"{i:2d}. {status} '{query}'")
        print(f"    → {actual:30s} (expected {expected:30s})")
        results.append({"query": query, "expected": expected, "actual": actual, "correct": ok})

    pct = (correct / total) * 100
    print("=" * 70)
    print(f"Accuracy: {correct}/{total} = {pct:.0f}%")
    print("=" * 70)

    # Store results in memory
    _store_results(pct, results)

    # Create trigger file if accuracy below threshold
    if pct < ACCURACY_THRESHOLD:
        _create_trigger(pct)

    return pct


def _store_results(accuracy: float, results: list) -> None:
    """Store golden test results to memory."""
    record = {
        "type": "test:golden",
        "accuracy": accuracy,
        "date": datetime.now().isoformat(),
        "total": len(results),
        "correct": int(accuracy * len(results) / 100),
        "details": results
    }

    os.makedirs(MEMORY_DIR, exist_ok=True)
    with open(RESULTS_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")
    print(f"Stored results to {RESULTS_FILE}")


def _create_trigger(accuracy: float) -> None:
    """Create retrain trigger file."""
    os.makedirs(MEMORY_DIR, exist_ok=True)
    with open(TRIGGER_FILE, "w") as f:
        f.write(json.dumps({
            "reason": f"accuracy_below_threshold",
            "accuracy": accuracy,
            "threshold": ACCURACY_THRESHOLD,
            "date": datetime.now().isoformat()
        }) + "\n")
    print(f"⚠️  Created retrain trigger (accuracy {accuracy:.0f}% < {ACCURACY_THRESHOLD}%)")


if __name__ == "__main__":
    accuracy = run_all()
    sys.exit(0 if accuracy >= ACCURACY_THRESHOLD else 1)