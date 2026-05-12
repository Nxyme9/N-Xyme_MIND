#!/usr/bin/env python3
"""
Catalyst vs Sisyphus Benchmark
================================
Compares orchestration quality and stats between Catalyst and Sisyphus agents.

Usage:
    python benchmark_catalyst_vs_sisyphus.py [--rounds N] [--output FILE]
"""

import argparse
import json
import subprocess
import time
import statistics
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Test tasks that represent different orchestration scenarios
BENCHMARK_TASKS = [
    {
        "name": "simple_research",
        "description": "Find all Python files in packages/",
        "agent": "explore",
        "expected_tools": ["glob", "read"],
    },
    {
        "name": "complex_research",
        "description": "Find authentication patterns across the codebase",
        "agent": "explore",
        "expected_tools": ["grep", "glob", "read"],
    },
    {
        "name": "external_research",
        "description": "Research best practices for JWT auth in Python",
        "agent": "librarian",
        "expected_tools": ["websearch", "codesearch"],
    },
    {
        "name": "multi_file_edit",
        "description": "Add logging to 3 files in packages/",
        "agent": "hephaestus",
        "expected_tools": ["read", "edit"],
    },
    {
        "name": "parallel_explore",
        "description": "Search for error handling patterns, auth patterns, and config patterns simultaneously",
        "agent": "explore",
        "expected_tools": ["grep", "glob"],
        "parallel_expected": True,
    },
]

# Quality gates to run after each task
QUALITY_GATES = [
    ("typecheck", ["bash", "bin/quality-gates/gate-1-py-typecheck.sh"]),
    ("lint", ["bash", "bin/quality-gates/gate-2-py-lint.sh"]),
    ("format", ["bash", "bin/quality-gates/gate-3-format.sh"]),
    ("placeholder", ["bash", "bin/quality-gates/gate-6-placeholders.sh"]),
]


def run_quality_gate(gate_name: str, command: List[str]) -> Dict[str, Any]:
    """Run a single quality gate and return results."""
    start = time.time()
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            cwd="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND",
        )
        elapsed = time.time() - start
        return {
            "name": gate_name,
            "passed": result.returncode == 0,
            "exit_code": result.returncode,
            "elapsed_ms": int(elapsed * 1000),
            "error": result.stderr[:500] if result.returncode != 0 else None,
        }
    except subprocess.TimeoutExpired:
        return {
            "name": gate_name,
            "passed": False,
            "exit_code": -1,
            "elapsed_ms": int((time.time() - start) * 1000),
            "error": "Timeout",
        }
    except Exception as e:
        return {
            "name": gate_name,
            "passed": False,
            "exit_code": -2,
            "elapsed_ms": int((time.time() - start) * 1000),
            "error": str(e)[:200],
        }


def run_all_gates() -> Dict[str, Any]:
    """Run all quality gates and return aggregated results."""
    results = {}
    for name, cmd in QUALITY_GATES:
        results[name] = run_quality_gate(name, cmd)

    passed = sum(1 for r in results.values() if r["passed"])
    total = len(results)

    return {
        "gates": results,
        "passed_count": passed,
        "total_count": total,
        "pass_rate": passed / total if total > 0 else 0,
    }


def get_routing_stats() -> Dict[str, Any]:
    """Get current routing statistics."""
    outcomes_file = Path(".sisyphus/outcomes.jsonl")
    if not outcomes_file.exists():
        return {"total_delegations": 0, "success_rate": 0}

    with open(outcomes_file) as f:
        outcomes = [json.loads(line) for line in f if line.strip()]

    total = len(outcomes)
    if total == 0:
        return {"total_delegations": 0, "success_rate": 0}

    success = sum(1 for o in outcomes if o.get("success"))

    # Per-agent stats
    agent_stats = {}
    for o in outcomes:
        agent = o.get("agent", "unknown")
        if agent not in agent_stats:
            agent_stats[agent] = {"success": 0, "total": 0, "latencies": []}
        agent_stats[agent]["total"] += 1
        if o.get("success"):
            agent_stats[agent]["success"] += 1
        if o.get("latency_ms"):
            agent_stats[agent]["latencies"].append(o["latency_ms"])

    # Calculate rates
    for agent, stats in agent_stats.items():
        if stats["total"] > 0:
            stats["success_rate"] = stats["success"] / stats["total"]
        if stats["latencies"]:
            stats["avg_latency_ms"] = statistics.mean(stats["latencies"])
        del stats["latencies"]  # Remove raw latencies

    return {
        "total_delegations": total,
        "success_rate": success / total,
        "agent_stats": agent_stats,
    }


def run_benchmark(rounds: int = 3) -> Dict[str, Any]:
    """Run the full benchmark."""
    print("=" * 60)
    print("CATALYST vs SISYPHUS BENCHMARK")
    print("=" * 60)

    # Get baseline routing stats before benchmark
    baseline_stats = get_routing_stats()
    print(f"\n📊 Baseline: {baseline_stats['total_delegations']} delegations")

    results = {
        "timestamp": datetime.now().isoformat(),
        "rounds": rounds,
        "baseline_stats": baseline_stats,
        "quality_gates": [],
        "orchestration_metrics": [],
    }

    # Run benchmark rounds
    for round_num in range(1, rounds + 1):
        print(f"\n🔄 Round {round_num}/{rounds}")

        # Run quality gates
        gate_results = run_all_gates()
        results["quality_gates"].append(gate_results)

        gates_passed = gate_results["passed_count"]
        gates_total = gate_results["total_count"]
        print(f"   Quality Gates: {gates_passed}/{gates_total} passed")

        # Get routing stats after this round
        current_stats = get_routing_stats()
        results["orchestration_metrics"].append(current_stats)

        new_delegations = (
            current_stats["total_delegations"] - baseline_stats["total_delegations"]
        )
        print(f"   New delegations: {new_delegations}")

        time.sleep(1)  # Brief pause between rounds

    # Calculate aggregate metrics
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    # Quality gate summary
    gate_pass_rates = []
    for round_result in results["quality_gates"]:
        gate_pass_rates.append(round_result["pass_rate"])

    avg_gate_pass = statistics.mean(gate_pass_rates) if gate_pass_rates else 0
    print(f"\n📋 Quality Gates:")
    print(f"   Pass rate: {avg_gate_pass:.1%}")

    # Final routing stats
    final_stats = get_routing_stats()
    delegations_this_run = (
        final_stats["total_delegations"] - baseline_stats["total_delegations"]
    )
    print(f"\n📈 Orchestration:")
    print(f"   Delegations this run: {delegations_this_run}")
    print(f"   Success rate: {final_stats['success_rate']:.1%}")

    # Agent breakdown
    print(f"\n🤖 Agent Usage:")
    for agent, stats in final_stats.get("agent_stats", {}).items():
        print(
            f"   {agent}: {stats['total']} tasks, {stats['success_rate']:.0%} success"
        )

    results["summary"] = {
        "avg_gate_pass_rate": avg_gate_pass,
        "delegations_this_run": delegations_this_run,
        "final_success_rate": final_stats["success_rate"],
        "agent_breakdown": final_stats.get("agent_stats", {}),
    }

    return results


def main():
    parser = argparse.ArgumentParser(description="Catalyst vs Sisyphus Benchmark")
    parser.add_argument(
        "--rounds", type=int, default=3, help="Number of benchmark rounds"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=".sisyphus/benchmarks/catalyst-benchmark.json",
        help="Output file",
    )
    args = parser.parse_args()

    results = run_benchmark(args.rounds)

    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to {output_path}")

    return results


if __name__ == "__main__":
    main()
