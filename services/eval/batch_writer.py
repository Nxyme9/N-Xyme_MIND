#!/usr/bin/env python3
"""Batch writer — spawn background agent to generate multiple files."""
import subprocess
import json
import sys

DAEMON = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/services/mojo-router/src/daemon"


def route_query(query: str, msg_id: str = "bw") -> dict:
    """Send query to daemon for routing."""
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


def batch_write(spec: str, files: list[str]) -> dict:
    """Spawn Hephaestus agent to write multiple files from a spec.

    Args:
        spec: Description of what to build
        files: List of file paths to generate

    Returns:
        Dict with results for each file
    """
    results = {}

    print("=" * 60)
    print(f"BATCH WRITER — Spec: {spec}")
    print("=" * 60)

    for f in files:
        query = f"delegate code writing: {spec} — write {f}"
        result = route_query(query, f"bw_{f}")

        tool = result.get("tool", "?")
        results[f] = result

        print(f"  📄 {f}")
        print(f"     → routed to: {tool}")
        print(f"     confidence: {result.get('confidence', 0):.2f}")

    print("=" * 60)
    print(f"Queued {len(files)} files for generation")
    print("=" * 60)

    return results


def demo():
    """Demo: test batch writer with sample spec."""
    print("\n" + "=" * 60)
    print("BATCH WRITER DEMO")
    print("=" * 60)

    # Test spec: simple utility files
    spec = "create simple Python utility module with helper functions"
    files = [
        "/tmp/demo_utils.py",
        "/tmp/demo_helpers.py",
        "/tmp/demo_config.py",
    ]

    results = batch_write(spec, files)

    # Show routing distribution
    tools_used = {}
    for f, r in results.items():
        t = r.get("tool", "unknown")
        tools_used[t] = tools_used.get(t, 0) + 1

    print("\nRouting Summary:")
    for tool, count in tools_used.items():
        print(f"  {tool}: {count} file(s)")

    return results


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo()
    else:
        # Interactive mode: read spec and files from stdin
        print("Batch Writer - Enter spec + files (Ctrl-D to execute):")
        spec = input("Spec: ").strip()
        print("Files (one per line, empty to done):")
        files = []
        while True:
            try:
                f = input().strip()
                if f:
                    files.append(f)
            except EOFError:
                break

        if spec and files:
            batch_write(spec, files)
        else:
            print("Usage: batch_writer.py --demo  # Run demo")
            print("   or: batch_writer.py        # Interactive mode")