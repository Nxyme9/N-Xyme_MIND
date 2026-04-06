#!/usr/bin/env python3
"""Migration script: JSON/JSONL state files → SQLite.

Usage:
    python3 bin/migrate-to-sqlite.py          # Dry run
    python3 bin/migrate-to-sqlite.py --apply  # Actually migrate
    python3 bin/migrate-to-sqlite.py --verify # Verify migration
"""

from __future__ import annotations

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
SISYPHUS = ROOT / ".sisyphus"

sys.path.insert(0, str(ROOT))

from src.state.db import StateDB
from src.state.models import Session, Delegation, AgentPerformance, Result


def dry_run() -> dict[str, int]:
    """Preview what would be migrated without writing to SQLite."""
    counts: dict[str, int] = {
        "sessions": 0,
        "delegations": 0,
        "agent_performance": 0,
        "results": 0,
    }

    session_file = SISYPHUS / "session-state.json"
    if session_file.exists():
        data = json.loads(session_file.read_text())
        print(
            f"  Session: last_agent={data.get('last_agent')}, current_task={data.get('current_task')}"
        )
        counts["sessions"] = 1
    else:
        print("  Session: file not found")

    delegations_file = SISYPHUS / "delegation-logs" / "delegations.jsonl"
    if delegations_file.exists():
        lines = delegations_file.read_text().strip().splitlines()
        valid = sum(1 for line in lines if line.strip())
        print(f"  Delegations: {valid} entries")
        counts["delegations"] = valid
    else:
        print("  Delegations: file not found")

    perf_file = SISYPHUS / "agent-performance.json"
    if perf_file.exists():
        data = json.loads(perf_file.read_text())
        entries = 0
        for k, v in data.items():
            if k == "last_updated":
                continue
            if isinstance(v, dict):
                entries += len(v)
        print(f"  Agent Performance: {entries} entries")
        counts["agent_performance"] = entries
    else:
        print("  Agent Performance: file not found")

    results_file = SISYPHUS / "results" / "index.json"
    if results_file.exists():
        data = json.loads(results_file.read_text())
        results = data.get("results", [])
        print(f"  Results: {len(results)} entries")
        counts["results"] = len(results)
    else:
        print("  Results: file not found")

    return counts


def apply_migration() -> dict[str, int]:
    """Migrate all JSON/JSONL files to SQLite."""
    db_path = SISYPHUS / "state.db"
    print(f"  Database: {db_path}")

    with StateDB(db_path) as db:
        counts = db.migrate_from_files(ROOT)

    print(f"\n  Migration complete:")
    for table, count in counts.items():
        print(f"    {table}: {count} records")

    return counts


def verify_migration() -> bool:
    """Verify that migration preserved all data."""
    db_path = SISYPHUS / "state.db"
    if not db_path.exists():
        print("  ERROR: Database file not found. Run migration first.")
        return False

    all_ok = True

    with StateDB(db_path) as db:
        # Verify session
        session_file = SISYPHUS / "session-state.json"
        if session_file.exists():
            session = db.get_active_session()
            if session:
                original = json.loads(session_file.read_text())
                if session.last_agent == original.get("last_agent", ""):
                    print("  Session: ✓ verified")
                else:
                    print(
                        f"  Session: ✗ mismatch (got {session.last_agent}, expected {original.get('last_agent')})"
                    )
                    all_ok = False
            else:
                print("  Session: ✗ not found in database")
                all_ok = False

        # Verify delegations
        delegations_file = SISYPHUS / "delegation-logs" / "delegations.jsonl"
        if delegations_file.exists():
            original_count = sum(
                1
                for line in delegations_file.read_text().strip().splitlines()
                if line.strip()
            )
            db_count = len(db.get_delegations(limit=10000))
            if db_count >= original_count:
                print(f"  Delegations: ✓ verified ({db_count} entries)")
            else:
                print(
                    f"  Delegations: ✗ count mismatch (db={db_count}, file={original_count})"
                )
                all_ok = False

        # Verify agent performance
        perf_file = SISYPHUS / "agent-performance.json"
        if perf_file.exists():
            original = json.loads(perf_file.read_text())
            original_entries = 0
            for k, v in original.items():
                if k == "last_updated":
                    continue
                if isinstance(v, dict):
                    original_entries += len(v)
            db_perf = db.get_all_agent_performance()
            db_entries = sum(len(v) for v in db_perf.values())
            if db_entries == original_entries:
                print(f"  Agent Performance: ✓ verified ({db_entries} entries)")
            else:
                print(
                    f"  Agent Performance: ✗ count mismatch (db={db_entries}, file={original_entries})"
                )
                all_ok = False

        # Verify results (may be empty)
        results_file = SISYPHUS / "results" / "index.json"
        if results_file.exists():
            original = json.loads(results_file.read_text())
            original_count = len(original.get("results", []))
            db_results = db.get_all_results()
            if len(db_results) == original_count:
                print(f"  Results: ✓ verified ({len(db_results)} entries)")
            else:
                print(
                    f"  Results: ✗ count mismatch (db={len(db_results)}, file={original_count})"
                )
                all_ok = False
        else:
            print("  Results: skipped (no original file)")

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="Migrate state files to SQLite")
    parser.add_argument("--apply", action="store_true", help="Apply migration")
    parser.add_argument("--verify", action="store_true", help="Verify migration")
    args = parser.parse_args()

    print("=" * 60)
    print("  State Migration: JSON/JSONL → SQLite")
    print("=" * 60)
    print()

    if not args.apply and not args.verify:
        print("DRY RUN — showing what would be migrated:")
        print()
        counts = dry_run()
        total = sum(counts.values())
        print(f"\n  Total records to migrate: {total}")
        print("\n  Run with --apply to migrate, --verify to verify.")
        return 0

    if args.apply:
        print("APPLYING MIGRATION...")
        print()
        counts = apply_migration()
        print()

    if args.verify:
        print("VERIFYING MIGRATION...")
        print()
        ok = verify_migration()
        print()
        if ok:
            print("  All verifications passed!")
            return 0
        else:
            print("  Some verifications failed. Check output above.")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
