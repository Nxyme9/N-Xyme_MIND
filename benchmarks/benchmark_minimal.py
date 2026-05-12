#!/usr/bin/env python3
"""
Minimal Benchmark - Quick measurement of OpenCode capabilities
"""

import subprocess
import time
import json
from pathlib import Path


def run_task(description, timeout=15):
    """Run single OpenCode task."""
    start = time.time()
    try:
        # Pipe input to opencode run
        result = subprocess.run(
            ["opencode", "--pure", "run"],
            input=description + "\n",
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND",
        )
        elapsed = (time.time() - start) * 1000
        output = result.stdout + result.stderr
        success = (
            result.returncode == 0 and len(output) > 50 and "Error" not in output[:200]
        )
        return {"success": success, "latency_ms": elapsed, "output_len": len(output)}
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "latency_ms": timeout * 1000,
            "output_len": 0,
            "error": "timeout",
        }
    except Exception as e:
        return {"success": False, "latency_ms": 0, "output_len": 0, "error": str(e)}


# Test tasks - simple enough to complete quickly
TASKS = [
    ("trivial", "What is 1+1?"),
    ("simple", "List 3 files in this directory"),
    ("search", "Find any Python file in packages/"),
]

print("=" * 50)
print("MINIMAL BENCHMARK - Vanilla OpenCode")
print("=" * 50)

results = []
for name, desc in TASKS:
    print(f"\nTask: {name}")
    r = run_task(desc)
    print(
        f"  Success: {r['success']}, Latency: {r['latency_ms']:.0f}ms, Output: {r['output_len']} chars"
    )
    if "error" in r:
        print(f"  Error: {r['error']}")
    results.append(r)

# Summary
successes = sum(1 for r in results if r["success"])
avg_latency = sum(r["latency_ms"] for r in results) / len(results)

print("\n" + "=" * 50)
print("SUMMARY")
print("=" * 50)
print(
    f"Success Rate: {successes}/{len(results)} ({100 * successes / len(results):.0f}%)"
)
print(f"Avg Latency: {avg_latency:.0f}ms")
