#!/usr/bin/env python3
"""
Model Heartbeat — Orchestrator
Chains: fetch models → diff against previous snapshot → notify on changes.
Designed for CI/CD / cron execution with tokenless public endpoints.

Usage:
    # Full run (fetch, diff, notify)
    python run_heartbeat.py

    # Dry-run: fetch and diff but skip notification
    python run_heartbeat.py --dry-run

    # Override data directory
    python run_heartbeat.py --data-dir /path/to/data

Exit codes:
    0  — success, no changes detected
    10 — success, changes detected and notified
    1  — error during fetch
"""

import json
import os
import shutil
import sys
import argparse
from datetime import datetime, timezone
from typing import Any


# ── Constants ───────────────────────────────────────────────────────────────

HERE = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_FILE = "snapshot_latest.json"
PREV_SNAPSHOT_FILE = "snapshot_prev.json"


# ── Steps ────────────────────────────────────────────────────────────────────

def step_fetch(data_dir: str) -> dict:
    """Run fetch_models.py and return the new snapshot dict."""
    import subprocess

    fetch_script = os.path.join(HERE, "fetch_models.py")
    if not os.path.exists(fetch_script):
        print(f"[heartbeat] ERROR: fetch_models.py not found at {fetch_script}", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(
        [sys.executable, fetch_script, "--output-dir", data_dir],
        capture_output=False,  # let output show
    )
    if result.returncode != 0:
        print(f"[heartbeat] fetch_models.py exited with code {result.returncode}", file=sys.stderr)
        sys.exit(1)

    # Read the snapshot just written
    snapshot_path = os.path.join(data_dir, SNAPSHOT_FILE)
    with open(snapshot_path) as f:
        return json.load(f)


def step_diff(data_dir: str, dry_run: bool = False) -> dict | None:
    """Compare current snapshot to previous. Returns diff dict or None if no prev."""
    prev_path = os.path.join(data_dir, PREV_SNAPSHOT_FILE)
    curr_path = os.path.join(data_dir, SNAPSHOT_FILE)

    if not os.path.exists(prev_path):
        print("[heartbeat] No previous snapshot found — this appears to be the first run.")
        print("[heartbeat] Saving current snapshot as baseline. No notification sent.")
        # Copy current as previous for next run
        if not dry_run:
            _copy_snapshot(curr_path, prev_path)
        return None

    from diff_models import compute_diff

    prev_snap: dict = json.load(open(prev_path))
    curr_snap: dict = json.load(open(curr_path))

    diff = compute_diff(prev_snap, curr_snap)

    # Print summary
    stats = diff["stats"]
    print(f"[heartbeat] Diff summary: +{stats['added_count']} / -{stats['removed_count']} / ~{stats['changed_count']} / !{stats['expiring_soon_count']}")

    return diff


def step_notify(diff: dict, dry_run: bool = False) -> None:
    """Send notification if changes detected."""
    from diff_models import diff_has_changes

    if not diff_has_changes(diff):
        print("[heartbeat] No changes detected — skipping notification.")
        return

    if dry_run:
        print("[heartbeat] DRY RUN: would send notification with:")
        # Still print the notification to stdout
        from notify import format_message
        print(format_message(diff))
        return

    # Send via notify.py
    import subprocess

    notify_script = os.path.join(HERE, "notify.py")
    if not os.path.exists(notify_script):
        print(f"[heartbeat] WARNING: notify.py not found — printing diff to stdout", file=sys.stderr)
        from notify import format_message
        print(format_message(diff))
        return

    # Pass diff as JSON on stdin for notify to consume
    proc = subprocess.run(
        [sys.executable, notify_script, "--stdin", "--telegram"],
        input=json.dumps(diff),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(f"[heartbeat] notify.py exited with code {proc.returncode}", file=sys.stderr)
        print(f"[heartbeat] stderr: {proc.stderr}", file=sys.stderr)
    else:
        print(f"[heartbeat] Notification sent.")
    
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)


def step_rotate_snapshot(data_dir: str) -> None:
    """Rename current snapshot as previous for next cycle."""
    curr_path = os.path.join(data_dir, SNAPSHOT_FILE)
    prev_path = os.path.join(data_dir, PREV_SNAPSHOT_FILE)

    if os.path.exists(curr_path):
        _copy_snapshot(curr_path, prev_path)
        print(f"[heartbeat] Rotated: {SNAPSHOT_FILE} → {PREV_SNAPSHOT_FILE}")


def _copy_snapshot(src: str, dst: str) -> None:
    """Copy snapshot file, preserving metadata if possible."""
    shutil.copy2(src, dst)


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Model Heartbeat Orchestrator")
    parser.add_argument("--data-dir", default=os.path.join(HERE, "data"),
                        help="Directory for snapshot storage (default: ./data)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch and diff but skip notification")
    parser.add_argument("--skip-fetch", action="store_true",
                        help="Skip fetch step (use existing snapshot for re-diff)")
    args = parser.parse_args()

    data_dir = os.path.abspath(args.data_dir)
    os.makedirs(data_dir, exist_ok=True)

    print("═══ Model Heartbeat ════════════════════════════════════════════")
    print(f"  Data dir: {data_dir}")
    print(f"  Dry run:  {args.dry_run}")
    print()

    # Step 1: Fetch
    if args.skip_fetch:
        print("[heartbeat] Skipping fetch (--skip-fetch)")
    else:
        print("── Step 1: Fetch ──")
        step_fetch(data_dir)
        print()

    # Step 2: Diff
    print("── Step 2: Diff ──")
    diff = step_diff(data_dir, dry_run=args.dry_run)
    print()

    # Step 3: Notify (only if we have a diff and changes exist)
    if diff is not None:
        print("── Step 3: Notify ──")
        step_notify(diff, dry_run=args.dry_run)
        print()

    # Step 4: Rotate snapshot for next run
    print("── Step 4: Rotate ──")
    step_rotate_snapshot(data_dir)
    print()

    print("═══ Heartbeat complete ═════════════════════════════════════════")

    if diff is None:
        return 0  # first run, baseline created
    from diff_models import diff_has_changes
    return 10 if diff_has_changes(diff) else 0


if __name__ == "__main__":
    sys.exit(main())
