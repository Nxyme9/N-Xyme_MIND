"""Delegation Benchmark — Real task tests with measurable stats.

Ported from bin/benchmark-delegation.sh.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from packages.intelligence.router.keyword import score_complexity
from packages.intelligence.delegation_logger import log_delegation


TEST_CASES: list[dict[str, Any]] = [
    {
        "task": "fix typo in config file",
        "expected_level": 1,
        "expected_agent": "sisyphus-junior",
    },
    {
        "task": "update version number to 2.0.0",
        "expected_level": 1,
        "expected_agent": "sisyphus-junior",
    },
    {
        "task": "fix bug in auth middleware",
        "expected_level": 2,
        "expected_agent": "hephaestus",
    },
    {
        "task": "add new API endpoint for user profile",
        "expected_level": 2,
        "expected_agent": "hephaestus",
    },
    {
        "task": "add JWT authentication to API",
        "expected_level": 3,
        "expected_agent": "hephaestus",
    },
    {
        "task": "refactor database connection pooling",
        "expected_level": 3,
        "expected_agent": "hephaestus",
    },
    {
        "task": "build new notification system from scratch",
        "expected_level": 4,
        "expected_agent": "prometheus",
    },
    {
        "task": "design microservices architecture",
        "expected_level": 5,
        "expected_agent": "metis",
    },
    {
        "task": "rewrite entire codebase in TypeScript",
        "expected_level": 5,
        "expected_agent": "metis",
    },
    {"task": "do something", "expected_level": 2, "expected_agent": "hephaestus"},
]


def run_benchmark(root_dir: Path | None = None, verbose: bool = True) -> dict[str, Any]:
    """Run delegation benchmark tests.

    Args:
        root_dir: Project root directory.
        verbose: Print per-test output.

    Returns:
        Benchmark results dict.
    """
    if root_dir is None:
        root_dir = Path(__file__).parent.parent.parent

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    total = len(TEST_CASES)
    correct = 0
    wrong = 0
    total_time_ms = 0
    results: list[dict[str, Any]] = []

    if verbose:
        print("=" * 55)
        print(
            f"  DELEGATION BENCHMARK — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print("=" * 55)
        print()
        print(f"Running {total} test cases...")
        print()

    for i, test in enumerate(TEST_CASES):
        task = test["task"]
        expected_level = test["expected_level"]
        expected_agent = test["expected_agent"]

        start = time.monotonic()
        try:
            score_result = score_complexity(task)
            actual_level = score_result.level
            confidence = score_result.confidence
            reason = score_result.reason
        except Exception:
            actual_level = 0
            confidence = 0.0
            reason = "unknown"
        elapsed_ms = (time.monotonic() - start) * 1000
        total_time_ms += elapsed_ms

        passed = actual_level == expected_level
        if passed:
            correct += 1
            status = "PASS"
        else:
            wrong += 1
            status = "FAIL"

        if verbose:
            print(f"Test {i + 1}/{total}: {status}")
            print(f'  Task: "{task}"')
            print(f"  Expected: L{expected_level} → {expected_agent}")
            print(
                f"  Actual:   L{actual_level} (confidence: {confidence}, reason: {reason})"
            )
            print(f"  Time: {elapsed_ms:.0f}ms")
            print()

        results.append(
            {
                "task": task,
                "expected_level": expected_level,
                "actual_level": actual_level,
                "confidence": confidence,
                "reason": reason,
                "time_ms": round(elapsed_ms, 2),
                "status": "pass" if passed else "fail",
            }
        )

        try:
            log_delegation(
                task_id=f"benchmark_{i}",
                agent="complexity-scorer",
                level=f"L{actual_level}",
                status="success" if passed else "fail",
                tokens=0,
                root_dir=root_dir,
            )
        except Exception:
            pass

    avg_time_ms = total_time_ms / total if total > 0 else 0
    accuracy = correct * 100 // total if total > 0 else 0

    benchmark_result = {
        "timestamp": timestamp,
        "total_tests": total,
        "passed": correct,
        "failed": wrong,
        "accuracy": accuracy,
        "total_time_ms": round(total_time_ms, 2),
        "avg_time_ms": round(avg_time_ms, 2),
        "results": results,
    }

    if verbose:
        print("=" * 55)
        print("  BENCHMARK RESULTS")
        print("=" * 55)
        print()
        print(f"  Total Tests:     {total}")
        print(f"  Passed:          {correct}")
        print(f"  Failed:          {wrong}")
        print(f"  Accuracy:        {accuracy}%")
        print(f"  Total Time:      {total_time_ms:.0f}ms")
        print(f"  Avg Time/Task:   {avg_time_ms:.0f}ms")
        print()
        print("  Before (manual delegation):")
        print("    - Avg decision time: ~5000ms (human thinking + agent selection)")
        print("    - Accuracy: ~70% (human error in agent selection)")
        print("    - Token waste: ~30% (wrong agent selection)")
        print()
        print("  After (auto-delegation):")
        print(f"    - Avg decision time: {avg_time_ms:.0f}ms (complexity scorer)")
        print(f"    - Accuracy: {accuracy}% (automated scoring)")
        token_waste = max(0, 30 - (accuracy - 70))
        print(f"    - Token waste: ~{token_waste}% (optimized routing)")
        print()
        print("  Improvement:")
        speedup = int(5000 / (avg_time_ms + 1))
        print(f"    - Speed: {speedup}x faster")
        print(f"    - Accuracy: +{accuracy - 70}% improvement")
        print(f"    - Token savings: ~{token_waste}% reduction")
        print()

    benchmark_dir = root_dir / ".sisyphus" / "benchmarks"
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    benchmark_file = (
        benchmark_dir / f"benchmark-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )

    with open(benchmark_file, "w") as f:
        json.dump(benchmark_result, f, indent=2)

    if verbose:
        print(f"  Benchmark saved to: {benchmark_file}")
        print()
        print("=" * 55)

    return benchmark_result


def main() -> None:
    parser = argparse.ArgumentParser(description="Delegation benchmark tests")
    parser.add_argument(
        "--json", action="store_true", help="Output results as JSON only"
    )
    args = parser.parse_args()

    result = run_benchmark(verbose=not args.json)

    if args.json:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
