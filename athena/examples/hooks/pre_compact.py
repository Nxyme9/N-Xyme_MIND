#!/usr/bin/env python3
"""
PreCompact Hook: Auto-Quicksave Before Context Compaction

Stolen from: shanraisshan/claude-code-best-practice hooks pattern.
Purpose: Ensures no knowledge is lost when context window is compacted.
Runs OUTSIDE the agentic loop — deterministic, zero LLM overhead.

Usage:
  Called automatically before any compaction event.
  Can also be triggered manually: python3 .agent/hooks/pre_compact.py
"""

import subprocess
import sys
import os
from datetime import datetime

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


def get_current_session():
    """Find the current session log."""
    session_dir = os.path.join(PROJECT_ROOT, ".context", "memories", "session_logs")
    if not os.path.isdir(session_dir):
        return None

    today = datetime.now().strftime("%Y-%m-%d")
    sessions = sorted(
        [
            f
            for f in os.listdir(session_dir)
            if f.startswith(today) and f.endswith(".md")
        ],
        reverse=True,
    )

    return sessions[0] if sessions else None


def quicksave(summary: str):
    """Run quicksave.py with the given summary."""
    quicksave_path = os.path.join(PROJECT_ROOT, ".agent", "scripts", "quicksave.py")
    if not os.path.exists(quicksave_path):
        print("⚠️  quicksave.py not found, skipping")
        return False

    try:
        result = subprocess.run(
            [sys.executable, quicksave_path, summary],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            print(f"✅ Pre-compact quicksave complete")
            return True
        else:
            print(f"⚠️  Quicksave returned non-zero: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("⚠️  Quicksave timed out")
        return False
    except Exception as e:
        print(f"❌ Quicksave error: {e}")
        return False


def main():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    session = get_current_session()

    print(f"🔄 PreCompact Hook triggered at {timestamp}")

    if session:
        summary = (
            f"[PreCompact Auto-Save] Context compaction triggered. Session: {session}"
        )
    else:
        summary = f"[PreCompact Auto-Save] Context compaction triggered at {timestamp}"

    quicksave(summary)
    print("✅ PreCompact hook complete — knowledge preserved before compaction")


if __name__ == "__main__":
    main()
