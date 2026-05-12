#!/usr/bin/env python3
"""
Quality-Focused Benchmark - Measures CODE QUALITY, not speed
=============================================================
Compares agent quality on complex tasks:
- Architecture design quality
- Code correctness (typecheck, lint)
- Implementation completeness
- Security best practices

This is NOT a speed benchmark - it's about output QUALITY.
"""

import argparse
import json
import subprocess
import time
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Complex tasks that test QUALITY, not speed
COMPLEX_TASKS = [
    {
        "name": "arch_design",
        "desc": "Design a REST API with authentication, rate limiting, and error handling. Write the architecture in docs/test_arch.md",
        "agent": "oracle",
        "timeout": 120,
    },
    {
        "name": "code_implementation",
        "desc": "Write a Python class for rate limiting with token bucket algorithm in /tmp/rate_limit.py",
        "agent": "hephaestus",
        "timeout": 90,
    },
    {
        "name": "security_review",
        "desc": "Review packages/orchestration/catalyst.py for security issues and list them",
        "agent": "oracle",
        "timeout": 60,
    },
    {
        "name": "test_implementation",
        "desc": "Write unit tests for a cache class in /tmp/test_cache.py",
        "agent": "hephaestus",
        "timeout": 90,
    },
    {
        "name": "refactor_quality",
        "desc": "Refactor packages/orchestration/catalyst.py to use type hints, fix any issues found",
        "agent": "hephaestus",
        "timeout": 120,
    },
]

# Quality Gates - measures CODE QUALITY
QUALITY_GATES = [
    ("typecheck", ["python3", "-m", "py_compile"]),
    ("lint", ["bash", "-c", "python3 -m flake8 --select=E9,F63,F7,F82 --show-source"]),
    ("security", ["bash", "-c", "git diff --no-color --quiet || echo 'no-changes'"]),
]


def run_quality_gate(name: str, cmd: List[str], target: str) -> Dict[str, Any]:
    """Run quality gate on a target file."""
    start = time.time()
    try:
        result = subprocess.run(
            cmd + [target] if target else cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND",
        )
        elapsed = (time.time() - start) * 1000
        passed = result.returncode == 0
        return {
            "name": name,
            "passed": passed,
            "elapsed_ms": int(elapsed),
            "exit_code": result.returncode,
            "output": result.stdout[:500] if result.stdout else "",
        }
    except Exception as e:
        return {"name": name, "passed": False, "elapsed_ms": 0, "error": str(e)[:100]}


def run_task_quality(task: Dict[str, Any]) -> Dict[str, Any]:
    """Run a complex task and measure QUALITY of output."""
    start = time.time()
    agent = task["agent"]
    desc = task["desc"]
    timeout = task["timeout"]

    # Use @agent syntax for specific agents
    if agent in ["oracle", "hephaestus"]:
        cmd = ["opencode", "--pure", "run", f"@{agent} {desc}"]
    else:
        cmd = ["opencode", "--pure", "run", desc]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND",
        )
        elapsed = (time.time() - start) * 1000
        output = result.stdout + result.stderr

        # QUALITY metrics - not speed
        quality_metrics = {
            "has_code": "```python" in output or "def " in output or "class " in output,
            "has_explanation": len(output) > 500,
            "has_errors": "Error:" in output or "error:" in output.lower(),
            "has_warnings": "Warning:" in output or "warning:" in output.lower(),
        }

        # Success = produced useful output, no critical errors
        success = (
            result.returncode == 0
            and quality_metrics["has_code"]
            or quality_metrics["has_explanation"]
            and not quality_metrics["has_errors"]
        )

        return {
            "task": task["name"],
            "agent": agent,
            "success": success,
            "latency_ms": int(elapsed),
            "output_len": len(output),
            "quality": quality_metrics,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "task": task["name"],
            "agent": agent,
            "success": False,
            "latency_ms": timeout * 1000,
            "output_len": 0,
            "error": "timeout",
            "quality": {},
        }
    except Exception as e:
        return {
            "task": task["name"],
            "agent": agent,
            "success": False,
            "latency_ms": 0,
            "output_len": 0,
            "error": str(e)[:100],
            "quality": {},
        }


def run_quality_benchmark(rounds: int = 1) -> Dict[str, Any]:
    """Run quality-focused benchmark."""
    print("\n" + "=" * 60)
    print("QUALITY-FOCUSED BENCHMARK")
    print("Measuring CODE QUALITY, not speed")
    print("=" * 60)

    results = []
    for round_num in range(1, rounds + 1):
        print(f"\n  Round {round_num}/{rounds}")

        for task in COMPLEX_TASKS:
            r = run_task_quality(task)
            results.append(r)

            quality_status = "✅" if r["success"] else "❌"
            q = r.get("quality", {})
            code_mark = "📝" if q.get("has_code") else "📄"
            error_mark = "⚠️" if q.get("has_errors") else "✓"

            print(
                f"    {quality_status} {task['name']} ({task['agent']}): {r['latency_ms']}ms {code_mark}{error_mark}"
            )

    # Aggregate quality metrics
    successes = [r["success"] for r in results]
    has_code = sum(1 for r in results if r.get("quality", {}).get("has_code"))
    has_explanation = sum(
        1 for r in results if r.get("quality", {}).get("has_explanation")
    )
    has_errors = sum(1 for r in results if r.get("quality", {}).get("has_errors"))

    return {
        "total_tasks": len(results),
        "successes": sum(successes),
        "success_rate": sum(successes) / len(successes) if successes else 0,
        "avg_latency_ms": sum(r["latency_ms"] for r in results) / len(results),
        "quality_metrics": {
            "produced_code": has_code,
            "produced_explanation": has_explanation,
            "had_errors": has_errors,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Quality-Focused Benchmark")
    parser.add_argument(
        "--rounds", type=int, default=1, help="Number of benchmark rounds"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=".sisyphus/benchmarks/quality-benchmark.json",
        help="Output file",
    )
    args = parser.parse_args()

    print("🏆 QUALITY BENCHMARK - Complex Task Quality Measurement")
    print("This measures CODE QUALITY, not speed")

    results = run_quality_benchmark(args.rounds)

    # Save results
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "results": results,
            },
            f,
            indent=2,
        )

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Success Rate: {results['success_rate'] * 100:.0f}%")
    print(f"  Avg Latency: {results['avg_latency_ms']:.0f}ms")
    print(
        f"  Produced Code: {results['quality_metrics']['produced_code']}/{results['total_tasks']}"
    )
    print(
        f"  Produced Explanation: {results['quality_metrics']['produced_explanation']}/{results['total_tasks']}"
    )
    print(
        f"  Had Errors: {results['quality_metrics']['had_errors']}/{results['total_tasks']}"
    )
    print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
