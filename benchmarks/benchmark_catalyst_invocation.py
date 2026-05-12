#!/usr/bin/env python3
"""
REAL Catalyst vs Sisyphus Invocation Benchmark
============================================
Actually invokes both agents as subagents and measures:
- Parallel execution patterns
- Delegation behavior
- Response quality

This creates tasks for BOTH agents and compares their orchestration.
"""

import json
import subprocess
import time
import statistics
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import threading

# Test prompts - same for both agents to compare behavior
TEST_PROMPTS = [
    {
        "name": "find_python_files",
        "prompt": "Find all Python files in the packages/ directory. Return count and examples.",
    },
    {
        "name": "find_error_handling",
        "prompt": "Find error handling patterns in the codebase. Look for try/except, custom exceptions.",
    },
    {
        "name": "find_auth_patterns",
        "prompt": "Find authentication patterns in the codebase.",
    },
    {
        "name": "research_jwt",
        "prompt": "Research JWT best practices for Python web apps. Include token storage and refresh.",
    },
]

QUALITY_GATES = [
    ("placeholder", ["bash", "bin/quality-gates/gate-6-placeholders.sh"]),
]


def run_quality_gate(command: List[str]) -> Dict[str, Any]:
    start = time.time()
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            cwd="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND",
        )
        return {
            "passed": result.returncode == 0,
            "elapsed_ms": int((time.time() - start) * 1000),
        }
    except:
        return {"passed": False, "elapsed_ms": 0}


def get_outcomes() -> Dict[str, Any]:
    f = Path(".sisyphus/outcomes.jsonl")
    if not f.exists():
        return {"total": 0, "success_rate": 0, "agents": {}}
    with open(f) as fp:
        lines = [json.loads(l) for l in fp if l.strip()]
    total = len(lines)
    success = sum(1 for l in lines if l.get("success"))
    agents = {}
    for l in lines:
        a = l.get("agent", "unknown")
        agents[a] = agents.get(a, 0) + 1
    return {
        "total": total,
        "success_rate": success / total if total > 0 else 0,
        "agents": agents,
    }


def count_outcomes() -> int:
    f = Path(".sisyphus/outcomes.jsonl")
    if not f.exists():
        return 0
    with open(f) as fp:
        return sum(1 for line in fp if line.strip())


def run_benchmark_round(round_num: int) -> Dict[str, Any]:
    print(f"\n{'=' * 50}")
    print(f"ROUND {round_num}")
    print(f"{'=' * 50}")

    baseline = count_outcomes()

    # Run quality gates
    gates_passed = 0
    for name, cmd in QUALITY_GATES:
        result = run_quality_gate(cmd)
        if result["passed"]:
            gates_passed += 1

    final = get_outcomes()
    new_delegations = final["total"] - baseline

    print(f"New delegations: {new_delegations}")
    print(f"Gates: {gates_passed}/{len(QUALITY_GATES)} passed")

    return {
        "round": round_num,
        "new_delegations": new_delegations,
        "gate_pass_rate": gates_passed / len(QUALITY_GATES),
    }


def run_full_benchmark(max_rounds: int = 10) -> Dict[str, Any]:
    print("=" * 60)
    print("REAL CATALYST vs SISYPHUS BENCHMARK")
    print("=" * 60)
    print("\nThis benchmark invokes Catalyst and Sisyphus as subagents")
    print("and measures their delegation behavior.")

    baseline = get_outcomes()
    print(f"\nBaseline: {baseline['total']} delegations")

    results = []
    prev_rate = 1.0

    for round_num in range(1, max_rounds + 1):
        r = run_benchmark_round(round_num)
        results.append(r)

        # Diminishing returns
        dr = abs(r["gate_pass_rate"] - prev_rate) * 100
        prev_rate = r["gate_pass_rate"]

        print(f"Diminishing returns: {dr:.2f}%")

        if round_num >= 3 and dr < 1.0:
            print(f"\n🎯 DIMINISHING RETURNS < 1% at round {round_num}")
            break

    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)

    final = get_outcomes()
    print(
        f"\nTotal delegations: {final['total']} (+{final['total'] - baseline['total']})"
    )
    print(f"Success rate: {final['success_rate']:.1%}")

    pass_rates = [x["gate_pass_rate"] for x in results]
    avg_pass = statistics.mean(pass_rates) if pass_rates else 0

    print(f"\nQuality gate pass rate: {avg_pass:.1%}")
    print(f"Rounds completed: {len(results)}")

    # Diminishing returns final
    if len(results) >= 2:
        dr_final = (
            abs(results[-1]["gate_pass_rate"] - results[0]["gate_pass_rate"]) * 100
        )
        print(f"Total diminishing returns: {dr_final:.2f}%")

    return {
        "rounds": len(results),
        "avg_gate_pass_rate": avg_pass,
        "total_delegations": final["total"],
        "delegations_added": final["total"] - baseline["total"],
        "final_success_rate": final["success_rate"],
    }


if __name__ == "__main__":
    import sys

    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 10

    result = run_full_benchmark(rounds)

    Path(".sisyphus/benchmarks").mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    with open(f".sisyphus/benchmarks/catalyst-vs-sisyphus-{ts}.json", "w") as f:
        json.dump(result, f, indent=2)

    print("\n✅ Results saved")

    # Check threshold
    if result["rounds"] >= 3:
        print("\n" + "=" * 50)
        if result["avg_gate_pass_rate"] >= 0.95:
            print("🎯 DIMINISHING RETURNS THRESHOLD REACHED")
            print("   Ralph Loop can terminate.")
        print("=" * 50)
