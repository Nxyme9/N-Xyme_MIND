#!/usr/bin/env python3
"""
Model Heartbeat — Diff Engine
Compares two snapshots (previous vs current) to detect:
  - New models added
  - Models removed
  - Models with changed properties (e.g., is_free flag flip, expiration_date change)

Usage:
    python diff_models.py --prev data/snapshot_prev.json --curr data/snapshot_latest.json
"""

import json
import sys
import argparse
from typing import Any


# ── Fields that matter for change detection ────────────────────────────────

WATCHED_FIELDS = {
    "expiration_date": "expiration",
    "is_free": "free tier status",
    "pricing": "pricing",
}

# Field renames for human-readable change descriptions
FIELD_LABELS = {
    "expiration_date": "Expiration date",
    "is_free": "Free tier",
    "pricing": "Pricing",
}


# ── Diff computation ───────────────────────────────────────────────────────

def load_snapshot(filepath: str) -> dict:
    """Load a snapshot JSON file."""
    with open(filepath) as f:
        return json.load(f)


def index_by_model_id(models: list[dict]) -> dict[str, dict]:
    """Build a {model_id: model} lookup dict."""
    return {m["model_id"]: m for m in models if m.get("model_id")}


def compute_diff(prev: dict, curr: dict) -> dict:
    """
    Compare two snapshots. Returns a structured diff:

    {
        "timestamp_prev": "ISO8601",
        "timestamp_curr": "ISO8601",
        "summary_prev": {provider: count},
        "summary_curr": {provider: count},
        "added": [normalized_model, ...],
        "removed": [normalized_model, ...],
        "changed": [
            {
                "model_id": "...",
                "provider": "...",
                "changes": {"field": {"old": ..., "new": ...}, ...}
            },
        ],
        "expiring_soon": [
            { "model_id": "...", "provider": "...", "expiration_date": "ISO" }
        ],
        "stats": {
            "added_count": int,
            "removed_count": int,
            "changed_count": int,
            "expiring_soon_count": int,
        }
    }
    """
    prev_models = prev.get("models", [])
    curr_models = curr.get("models", [])

    prev_index = index_by_model_id(prev_models)
    curr_index = index_by_model_id(curr_models)

    prev_ids = set(prev_index.keys())
    curr_ids = set(curr_index.keys())

    added_ids = curr_ids - prev_ids
    removed_ids = prev_ids - curr_ids
    common_ids = prev_ids & curr_ids

    added = [curr_index[mid] for mid in sorted(added_ids)]
    removed = [prev_index[mid] for mid in sorted(removed_ids)]

    # Detect field-level changes within the same model_id
    changed: list[dict] = []
    expiring_soon: list[dict] = []

    for mid in sorted(common_ids):
        prev_m = prev_index[mid]
        curr_m = curr_index[mid]
        changes = {}

        for field, label in WATCHED_FIELDS.items():
            old_val = prev_m.get(field)
            new_val = curr_m.get(field)
            if old_val != new_val:
                # Serialize to string for comparison (handles dict/list differences)
                if json.dumps(old_val, default=str, sort_keys=True) != json.dumps(new_val, default=str, sort_keys=True):
                    changes[field] = {"old": old_val, "new": new_val}

        if changes:
            changed.append({
                "model_id": mid,
                "provider": curr_m.get("provider", prev_m.get("provider")),
                "changes": changes,
            })

        # Check for upcoming expiration (OpenRouter-specific)
        exp_date = curr_m.get("expiration_date")
        if exp_date and exp_date != prev_m.get("expiration_date"):
            expiring_soon.append({
                "model_id": mid,
                "provider": curr_m.get("provider"),
                "expiration_date": exp_date,
            })

    return {
        "timestamp_prev": prev.get("timestamp", "unknown"),
        "timestamp_curr": curr.get("timestamp", "unknown"),
        "summary_prev": prev.get("summary", {}),
        "summary_curr": curr.get("summary", {}),
        "added": added,
        "removed": removed,
        "changed": changed,
        "expiring_soon": expiring_soon,
        "stats": {
            "added_count": len(added),
            "removed_count": len(removed),
            "changed_count": len(changed),
            "expiring_soon_count": len(expiring_soon),
        },
    }


def diff_has_changes(diff: dict) -> bool:
    """Return True if the diff contains any meaningful changes."""
    s = diff["stats"]
    return s["added_count"] > 0 or s["removed_count"] > 0 or s["changed_count"] > 0 or s["expiring_soon_count"] > 0


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Diff two model snapshots")
    parser.add_argument("--prev", required=True, help="Previous snapshot JSON")
    parser.add_argument("--curr", required=True, help="Current snapshot JSON")
    parser.add_argument("--json", action="store_true", help="Output raw JSON diff")
    args = parser.parse_args()

    prev = load_snapshot(args.prev)
    curr = load_snapshot(args.curr)
    diff = compute_diff(prev, curr)

    if args.json:
        print(json.dumps(diff, indent=2, default=str))
        return 0

    # Human-readable summary
    stats = diff["stats"]
    print("── Model Heartbeat: Diff ──────────────────────────────────────")
    print(f"  Period: {diff['timestamp_prev'][:19]} → {diff['timestamp_curr'][:19]}")
    print(f"  Added:   {stats['added_count']:>4} models")
    print(f"  Removed: {stats['removed_count']:>4} models")
    print(f"  Changed: {stats['changed_count']:>4} models")
    print(f"  Expiring: {stats['expiring_soon_count']:>4} models")

    if stats["added_count"] > 0:
        print(f"\n  ── New Models ({stats['added_count']}) ──")
        for m in diff["added"][:20]:  # limit output
            print(f"    + {m['model_id']:50s} [{m['provider']}]")
        if stats["added_count"] > 20:
            print(f"    ... and {stats['added_count'] - 20} more")

    if stats["removed_count"] > 0:
        print(f"\n  ── Removed Models ({stats['removed_count']}) ──")
        for m in diff["removed"][:20]:
            print(f"    - {m['model_id']:50s} [{m['provider']}]")
        if stats["removed_count"] > 20:
            print(f"    ... and {stats['removed_count'] - 20} more")

    if stats["changed_count"] > 0:
        print(f"\n  ── Changed Models ({stats['changed_count']}) ──")
        for c in diff["changed"][:20]:
            descs = []
            for field, vals in c["changes"].items():
                label = FIELD_LABELS.get(field, field)
                descs.append(f"{label}: {_brief(vals['old'])} → {_brief(vals['new'])}")
            print(f"    ~ {c['model_id']:50s} [{', '.join(descs)}]")

    if stats["expiring_soon_count"] > 0:
        print(f"\n  ── Expiring Models ({stats['expiring_soon_count']}) ──")
        for m in diff["expiring_soon"][:20]:
            print(f"    ! {m['model_id']:50s} expires {m['expiration_date'][:10]}")

    if not diff_has_changes(diff):
        print("\n  ✓ No changes detected.")

    # Return exit code: 0 = no changes, 10 = changes detected
    return 0 if not diff_has_changes(diff) else 10


def _brief(val: Any, max_len: int = 40) -> str:
    """Short representation of a value for display."""
    if val is None:
        return "None"
    s = json.dumps(val, default=str)
    return s[:max_len] + "..." if len(s) > max_len else s


if __name__ == "__main__":
    sys.exit(main())
