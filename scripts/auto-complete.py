#!/usr/bin/env python3
"""
N-Xyme Auto-Complete Hook
Runs after every task completion:
1. Git push if changes exist
2. Store learning in Graphiti
3. Update notepad
"""

import subprocess
import sys
import os
import json
import requests
from datetime import datetime
from pathlib import Path

# Import centralized Graphiti configuration
try:
    from jarvis.config.graphiti_config import GRAPHITI_RPC_URL as GRAPHITI_URL
except ImportError:
    GRAPHITI_URL = os.getenv("GRAPHITI_RPC_URL", "http://localhost:8001/json-rpc")
CATALYST_DIR = Path(os.environ.get("CATALYST_DIR", Path(__file__).resolve().parent.parent))


def git_status():
    """Check if there are uncommitted changes."""
    r = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=str(CATALYST_DIR),
    )
    return r.stdout.strip()


def git_push(message: str):
    """Stage, commit, and push changes."""
    subprocess.run(["git", "add", "."], cwd=str(CATALYST_DIR))
    subprocess.run(["git", "commit", "-m", message], cwd=str(CATALYST_DIR))
    subprocess.run(["git", "push"], cwd=str(CATALYST_DIR))
    print(f"[AUTO-PUSH] Pushed: {message}")


def store_in_graphiti(name: str, content: str, tags: list = None):
    """Store episode in Graphiti knowledge graph."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "graphiti_add_episode",
        "params": {
            "name": name,
            "episode_body": content,
            "source": "auto-complete-hook",
            "source_description": f"Task completion at {datetime.now().isoformat()}",
        },
    }
    try:
        requests.post(GRAPHITI_URL, json=payload, timeout=10)
        print(f"[GRAPHITI] Stored: {name}")
    except Exception as e:
        print(f"[GRAPHITI] Error: {e}")


def update_notepad(category: str, content: str):
    """Append to .sisyphus notepad."""
    notepad_dir = CATALYST_DIR / ".sisyphus" / "notepads" / "auto"
    notepad_dir.mkdir(parents=True, exist_ok=True)
    notepad_file = notepad_dir / f"{category}.md"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## [{timestamp}] Auto-captured\n{content}\n"

    with open(notepad_file, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"[NOTEPAD] Updated: {category}.md")


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python auto-complete.py <task_id> [--learning 'text'] [--decision 'text'] [--push]"
        )
        sys.exit(1)

    task_id = sys.argv[1]
    learning = None
    decision = None
    should_push = "--push" in sys.argv

    # Parse arguments
    for i, arg in enumerate(sys.argv):
        if arg == "--learning" and i + 1 < len(sys.argv):
            learning = sys.argv[i + 1]
        elif arg == "--decision" and i + 1 < len(sys.argv):
            decision = sys.argv[i + 1]

    print(f"\n{'=' * 50}")
    print(f"  AUTO-COMPLETE: {task_id}")
    print(f"{'=' * 50}")

    # 1. Store learning in Graphiti
    if learning:
        store_in_graphiti(f"learning-{task_id}", learning)
        update_notepad("learnings", f"### Task: {task_id}\n{learning}")

    # 2. Store decision in Graphiti
    if decision:
        store_in_graphiti(f"decision-{task_id}", decision)
        update_notepad("decisions", f"### Task: {task_id}\n{decision}")

    # 3. Git push if requested and changes exist
    if should_push:
        changes = git_status()
        if changes:
            git_push(f"feat({task_id}): auto-push on completion")
        else:
            print("[GIT] No changes to push")

    print(f"{'=' * 50}")
    print(f"  COMPLETE")
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    main()
