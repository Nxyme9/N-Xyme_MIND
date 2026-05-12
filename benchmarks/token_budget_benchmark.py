#!/usr/bin/env python3
"""Benchmarks for TokenBudgetTracker - Phase 2.2.

Benchmarks verify:
- track_usage operation (1000 iterations)
- check_budget performance
- Many agents (all 10 types) performance
"""

import sys
import os
import time
import statistics
from typing import List, Dict, Tuple

# Import directly to avoid package namespace issues
PROJECT_ROOT = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
import importlib.util

spec = importlib.util.spec_from_file_location(
    "token_budget", os.path.join(PROJECT_ROOT, "packages/orchestration/token_budget.py")
)
token_budget_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(token_budget_module)

TokenBudgetTracker = token_budget_module.TokenBudgetTracker
DEFAULT_BUDGETS = token_budget_module.DEFAULT_BUDGETS


def benchmark_track_usage(iterations: int = 1000) -> Dict[str, float]:
    """Benchmark track_usage operation.

    Returns:
        Dict with timing metrics
    """
    tracker = TokenBudgetTracker()
    times: List[float] = []

    for i in range(iterations):
        start = time.perf_counter()
        tracker.track_usage("hephaestus", 100)
        elapsed = (time.perf_counter() - start) * 1_000_000  # Convert to microseconds
        times.append(elapsed)

    return {
        "iterations": iterations,
        "mean_us": statistics.mean(times),
        "median_us": statistics.median(times),
        "stdev_us": statistics.stdev(times) if len(times) > 1 else 0,
        "min_us": min(times),
        "max_us": max(times),
        "total_ms": sum(times) / 1000,
    }


def benchmark_check_budget(iterations: int = 1000) -> Dict[str, float]:
    """Benchmark check_budget operation.

    Returns:
        Dict with timing metrics
    """
    tracker = TokenBudgetTracker()
    tracker.track_usage("hephaestus", 50000)  # Half budget

    times: List[float] = []

    for i in range(iterations):
        start = time.perf_counter()
        allowed, remaining = tracker.check_budget("hephaestus")
        elapsed = (time.perf_counter() - start) * 1_000_000
        times.append(elapsed)

    return {
        "iterations": iterations,
        "mean_us": statistics.mean(times),
        "median_us": statistics.median(times),
        "stdev_us": statistics.stdev(times) if len(times) > 1 else 0,
        "min_us": min(times),
        "max_us": max(times),
        "total_ms": sum(times) / 1000,
    }


def benchmark_all_agents(iterations: int = 100) -> Dict[str, Dict[str, float]]:
    """Benchmark all 10 agent types.

    Returns:
        Dict mapping agent to timing metrics
    """
    results = {}

    for agent in DEFAULT_BUDGETS:
        tracker = TokenBudgetTracker()
        times: List[float] = []

        for i in range(iterations):
            start = time.perf_counter()
            tracker.track_usage(agent, 1000)
            tracker.check_budget(agent)
            tracker.is_paused(agent)
            tracker.get_status(agent)
            elapsed = (time.perf_counter() - start) * 1_000_000
            times.append(elapsed)

        results[agent] = {
            "iterations": iterations,
            "budget": DEFAULT_BUDGETS[agent],
            "mean_us": statistics.mean(times),
            "median_us": statistics.median(times),
            "stdev_us": statistics.stdev(times) if len(times) > 1 else 0,
            "total_ms": sum(times) / 1000,
        }

    return results


def benchmark_reset_operations(iterations: int = 500) -> Dict[str, float]:
    """Benchmark reset operations.

    Returns:
        Dict with timing metrics
    """
    times_reset_single: List[float] = []
    times_reset_all: List[float] = []

    for i in range(iterations):
        # Benchmark reset_budget
        tracker = TokenBudgetTracker()
        tracker.track_usage("hephaestus", 50000)

        start = time.perf_counter()
        tracker.reset_budget("hephaestus")
        elapsed = (time.perf_counter() - start) * 1_000_000
        times_reset_single.append(elapsed)

        # Benchmark reset_all
        tracker.track_usage("hephaestus", 50000)
        tracker.track_usage("explore", 10000)

        start = time.perf_counter()
        tracker.reset_all()
        elapsed = (time.perf_counter() - start) * 1_000_000
        times_reset_all.append(elapsed)

    return {
        "iterations": iterations,
        "reset_single_mean": statistics.mean(times_reset_single),
        "reset_single_median": statistics.median(times_reset_single),
        "reset_all_mean": statistics.mean(times_reset_all),
        "reset_all_median": statistics.median(times_reset_all),
    }


def benchmark_full_cycles(iterations: int = 500) -> Dict[str, float]:
    """Benchmark full budget cycle (track + check + status).

    Returns:
        Dict with timing metrics
    """
    times: List[float] = []

    for i in range(iterations):
        tracker = TokenBudgetTracker()

        start = time.perf_counter()
        tracker.track_usage("hephaestus", 1000)
        allowed, remaining = tracker.check_budget("hephaestus")
        status = tracker.get_status("hephaestus")
        is_paused = tracker.is_paused("hephaestus")
        elapsed = (time.perf_counter() - start) * 1_000_000
        times.append(elapsed)

    return {
        "iterations": iterations,
        "mean_us": statistics.mean(times),
        "median_us": statistics.median(times),
        "stdev_us": statistics.stdev(times) if len(times) > 1 else 0,
        "min_us": min(times),
        "max_us": max(times),
        "total_ms": sum(times) / 1000,
    }


def run_benchmarks() -> None:
    """Run all benchmarks and print results."""
    print("=" * 60)
    print("Token Budget Benchmark Results - Phase 2.2")
    print("=" * 60)

    # 1. track_usage benchmark
    print("\n[1] track_usage benchmark (1000 iterations)")
    print("-" * 40)
    result = benchmark_track_usage(1000)
    print(f"  Mean:   {result['mean_us']:.2f} µs")
    print(f"  Median: {result['median_us']:.2f} µs")
    print(f"  Stdev:  {result['stdev_us']:.2f} µs")
    print(f"  Min:    {result['min_us']:.2f} µs")
    print(f"  Max:    {result['max_us']:.2f} µs")
    print(f"  Total:  {result['total_ms']:.2f} ms")

    # 2. check_budget benchmark
    print("\n[2] check_budget benchmark (1000 iterations)")
    print("-" * 40)
    result = benchmark_check_budget(1000)
    print(f"  Mean:   {result['mean_us']:.2f} µs")
    print(f"  Median: {result['median_us']:.2f} µs")
    print(f"  Stdev:  {result['stdev_us']:.2f} µs")
    print(f"  Total:  {result['total_ms']:.2f} ms")

    # 3. All agents benchmark
    print("\n[3] All 10 agent types benchmark (100 iterations each)")
    print("-" * 40)
    results = benchmark_all_agents(100)
    for agent, metrics in results.items():
        print(
            f"  {agent:18s}: {metrics['mean_us']:6.2f} µs (budget={metrics['budget']:5d})"
        )

    # 4. Reset operations benchmark
    print("\n[4] Reset operations benchmark (500 iterations)")
    print("-" * 40)
    result = benchmark_reset_operations(500)
    print(f"  reset_budget: mean={result['reset_single_mean']:.2f} µs")
    print(f"  reset_all:    mean={result['reset_all_mean']:.2f} µs")

    # 5. Full cycle benchmark
    print("\n[5] Full cycle benchmark (track + check + status + is_paused)")
    print("-" * 40)
    result = benchmark_full_cycles(500)
    print(f"  Iterations: {result['iterations']}")
    print(f"  Mean:      {result['mean_us']:.2f} µs")
    print(f"  Median:    {result['median_us']:.2f} µs")
    print(f"  Stdev:     {result['stdev_us']:.2f} µs")
    print(f"  Total:    {result['total_ms']:.2f} ms")

    print("\n" + "=" * 60)
    print("Benchmarks complete!")
    print("=" * 60)


if __name__ == "__main__":
    run_benchmarks()
