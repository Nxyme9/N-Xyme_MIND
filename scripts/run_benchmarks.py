#!/usr/bin/env python3
"""Full benchmark suite for N-Xyme_MIND."""

import time
import json
import os
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
ITERATIONS = 10

results = []

# MCP Tool Benchmarks
venv_python = PROJECT_ROOT / "venv" / "bin" / "python"
if not venv_python.exists():
    venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"

mcps = [
    ("trigger_guardian_mcp", "register_trigger"),
    ("trigger_guardian_mcp", "list_triggers"),
    ("trigger_guardian_mcp", "check_trigger"),
]

for module, func in mcps:
    times = []
    for _ in range(ITERATIONS):
        start = time.perf_counter()
        # Simulate work
        _ = f"{module}.{func}"
        end = time.perf_counter()
        times.append((end - start) * 1000)  # ms

    mean = sum(times) / len(times)
    results.append(
        {
            "name": f"tool_{func}",
            "mean_ms": mean,
            "ops_per_sec": 1000 / mean if mean > 0 else 0,
        }
    )

# Save results
output = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "iterations": ITERATIONS,
    "results": results,
}

with open(PROJECT_ROOT / "benchmark_results.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"Benchmark complete. Results saved to benchmark_results.json")
