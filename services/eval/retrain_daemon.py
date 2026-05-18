#!/usr/bin/env python3
"""
Background retrain daemon — watches corrections.jsonl, triggers retrain at 100.
"""
import json
import os
import time
import subprocess
import sys

CORRECTIONS = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/data/memory/corrections.jsonl"
TRIGGER = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/data/memory/retrain.trigger"
TRAINER = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/services/rosenna_trainer/train.py"
GOLDEN = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/services/eval/golden_tests.py"
OUTPUT_MODEL = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/data/memory/models/rosenna-hot.gguf"
TRAIN_DATA = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/data/training/"


def count_corrections() -> int:
    """Count lines in corrections file."""
    if not os.path.exists(CORRECTIONS):
        return 0
    with open(CORRECTIONS) as f:
        return len([l for l in f if l.strip()])


def check_and_retrain():
    """Check correction count and trigger retrain if threshold reached."""
    correction_count = count_corrections()
    print(f"Corrections: {correction_count}")

    if correction_count >= 100:
        print(f"Threshold reached ({correction_count} >= 100) — triggering retrain...")

        # Run golden tests first
        print("Running golden tests...")
        result = subprocess.run(
            [sys.executable, GOLDEN],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print(f"Golden tests stderr: {result.stderr}")

        # Ensure output directory exists
        os.makedirs(os.path.dirname(OUTPUT_MODEL), exist_ok=True)

        # Run trainer
        print("Running trainer...")
        train_result = subprocess.run(
            [sys.executable, TRAINER,
             "--data", TRAIN_DATA,
             "--output", OUTPUT_MODEL],
            capture_output=True,
            text=True
        )
        if train_result.returncode == 0:
            print(f"Training complete: {OUTPUT_MODEL}")
        else:
            print(f"Training failed: {train_result.stderr}")

        # Clear trigger file
        if os.path.exists(TRIGGER):
            os.remove(TRIGGER)
            print("Cleared retrain trigger")

        print("Retrain complete")
        return True

    return False


if __name__ == "__main__":
    print("=" * 60)
    print("RETRAIN DAEMON — Running in watch mode")
    print(f"Watching: {CORRECTIONS}")
    print(f"Threshold: 100 corrections")
    print("=" * 60)

    while True:
        check_and_retrain()
        time.sleep(60)  # Check every minute