#!/usr/bin/env python3
"""Training dashboard — shows accuracy, corrections, memory stats."""
import json
import os
import time
from datetime import datetime

MEM_PATH = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/data/memory/vectors/ingest.jsonl"
CORR_PATH = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/data/memory/corrections.jsonl"
TRIGGER = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/data/memory/retrain.trigger"


def show():
    """Display the training dashboard."""
    os.system('clear')
    print("=" * 50)
    print("  N-XYME TRAINING DASHBOARD")
    print("=" * 50)
    print()

    # Memory stats
    try:
        with open(MEM_PATH) as f:
            entries = [json.loads(l) for l in f if l.strip()]
        routes = sum(1 for e in entries if str(e.get('type', '')).startswith('route:'))
        decisions = sum(1 for e in entries if str(e.get('type', '')).startswith('decision:'))
        errors = sum(1 for e in entries if str(e.get('type', '')).startswith('error:'))
        tests = [e for e in entries if str(e.get('type', '')).startswith('test:')]

        print(f"  📊 MEMORY: {len(entries)} total entries")
        print(f"     Routes: {routes} | Decisions: {decisions} | Errors: {errors}")
        if tests:
            print(f"     Last golden test: {tests[-1].get('text', '')[:60]}")
        print()
    except Exception:
        pass

    # Correction count
    try:
        with open(CORR_PATH) as f:
            corr_count = len([l for l in f if l.strip()])
        print(f"  🔧 CORRECTIONS: {corr_count}/100 for retrain")
        bar = "█" * corr_count + "░" * (100 - corr_count) if corr_count <= 100 else "█" * 100
        print(f"     [{bar}]")
        print()
    except Exception:
        pass

    # Retrain status
    print(f"  🔄 RETRAIN: {'TRIGGERED (will run)' if os.path.exists(TRIGGER) else 'Idle'}")
    print()
    print(f"  Last updated: {datetime.now().strftime('%H:%M:%S')}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true", help="Auto-refresh every 3s")
    args = parser.parse_args()

    if args.watch:
        try:
            while True:
                show()
                time.sleep(3)
        except KeyboardInterrupt:
            print("\nDashboard stopped")
    else:
        show()