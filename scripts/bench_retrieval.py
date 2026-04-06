#!/usr/bin/env python3
"""Benchmark suite for memory+learning system.

Benchmarks:
1. Retrieval latency (query → results) — target <100ms
2. Memory write latency — target <50ms
3. Pipeline execution time (all 6 stages)
4. Memory usage (SQLite DB size growth)
5. Concurrent access throughput (multiple threads)
6. Q-Learning update latency
7. Large dataset scaling (100, 1000, 10000 memories)

Run: python3 scripts/bench_retrieval.py
Output: JSON to .sisyphus/benchmarks/retrieval-bench-YYYY-MM-DD.json
"""

from __future__ import annotations

import json
import os
import random
import statistics
import string
import sys
import tempfile
import threading
import time
import tracemalloc
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.memory_core.retrievers.pipeline import RetrievalPipeline
from packages.memory_core.router import MemoryRouter, UnifiedMemoryQuery
from packages.memory_core.stores.relational_store import RelationalStore
from packages.memory_core.stores.base import MemoryRecord
from packages.memory_core.memory_manager import MemoryManager


def generate_random_content(length: int = 200) -> str:
    """Generate random text content."""
    words = [
        "algorithm",
        "data",
        "system",
        "memory",
        "query",
        "search",
        "learning",
        "model",
        "vector",
        "embedding",
        "database",
        "cache",
        "index",
        "route",
        "pipeline",
        "benchmark",
        "performance",
        "latency",
    ]
    return " ".join(random.choices(words, k=length // 6))


def generate_memory_record(idx: int) -> MemoryRecord:
    """Generate a random memory record for testing."""
    return MemoryRecord(
        id=f"bench_mem_{idx}",
        content=generate_random_content(),
        kind=random.choice(["episodic", "semantic", "procedural"]),
        scope=random.choice(["session", "project", "global"]),
        tier=random.choice(["short_term", "medium_term", "long_term"]),
        metadata={
            "created_at": datetime.now().isoformat(),
            "bench_index": idx,
        },
    )


def calculate_percentile(values: List[float], percentile: float) -> float:
    """Calculate percentile from sorted values."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(len(sorted_vals) * percentile / 100)
    idx = min(idx, len(sorted_vals) - 1)
    return sorted_vals[idx]


def run_benchmark(
    func,
    num_runs: int = 10,
    warmup: int = 2,
) -> Dict[str, float]:
    """Run a benchmark function multiple times and compute statistics.

    Args:
        func: Callable that returns a latency in milliseconds
        num_runs: Number of times to execute
        warmup: Number of warmup runs before measuring

    Returns:
        Dict with mean, median, p95, p99, min, max
    """
    # Warmup runs
    for _ in range(warmup):
        func()

    # Actual benchmark runs
    latencies = []
    for _ in range(num_runs):
        latencies.append(func())

    return {
        "mean_ms": round(statistics.mean(latencies), 2),
        "median_ms": round(statistics.median(latencies), 2),
        "p95_ms": round(calculate_percentile(latencies, 95), 2),
        "p99_ms": round(calculate_percentile(latencies, 99), 2),
        "min_ms": round(min(latencies), 2),
        "max_ms": round(max(latencies), 2),
        "num_runs": num_runs,
    }


def bench_retrieval_latency(
    num_memories: int = 100,
    num_runs: int = 15,
) -> Dict[str, Any]:
    """Benchmark 1: Retrieval latency (query → results).

    Target: <100ms
    """
    # Setup: Create temp DB and populate with memories
    with tempfile.TemporaryDirectory() as tmpdir:
        bench_db = os.path.join(tmpdir, "retrieval_bench.db")
        store = RelationalStore(bench_db)

        # Insert test memories
        for i in range(num_memories):
            record = generate_memory_record(i)
            store.store(record)

        # Create router
        router = MemoryRouter()

        def measure_retrieval():
            query = UnifiedMemoryQuery(
                query="algorithm data system",
                max_results_per_source=10,
            )
            result = router.search(query)
            return result.query_time_ms

        stats = run_benchmark(measure_retrieval, num_runs=num_runs)

        return {
            "benchmark": "retrieval_latency",
            "target_ms": 100,
            "num_memories": num_memories,
            "metrics": stats,
            "passed": stats["median_ms"] < 100,
        }


def bench_memory_write_latency(
    num_runs: int = 15,
) -> Dict[str, Any]:
    """Benchmark 2: Memory write latency.

    Target: <50ms
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        bench_db = os.path.join(tmpdir, "write_bench.db")
        store = RelationalStore(bench_db)

        def measure_write():
            record = generate_memory_record(random.randint(10000, 99999))
            start = time.perf_counter()
            store.store(record)
            return (time.perf_counter() - start) * 1000

        stats = run_benchmark(measure_write, num_runs=num_runs)

        return {
            "benchmark": "memory_write_latency",
            "target_ms": 50,
            "metrics": stats,
            "passed": stats["median_ms"] < 50,
        }


def bench_pipeline_execution(
    num_runs: int = 15,
) -> Dict[str, Any]:
    """Benchmark 3: Pipeline execution time (all 6 stages).

    Stages: query_analysis, retrieve, rrf_fusion, mmr_rerank, cross_encoder_rerank, return
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        bench_db = os.path.join(tmpdir, "pipeline_bench.db")
        store = RelationalStore(bench_db)

        # Populate with memories
        for i in range(100):
            store.store(generate_memory_record(i))

        pipeline = RetrievalPipeline(db_path=bench_db, default_top_k=10)

        def measure_pipeline():
            result = pipeline.search("algorithm data system learning")
            return result.total_latency_ms

        stats = run_benchmark(measure_pipeline, num_runs=num_runs)

        # Get stage breakdown (average across runs)
        pipeline.search("test query")
        stage_metrics = pipeline._get_stage_metrics()

        return {
            "benchmark": "pipeline_execution",
            "target_ms": 150,  # 6 stages, allow some overhead
            "metrics": stats,
            "stages": list(stage_metrics.keys()),
            "stage_latencies": {
                k: v.get("latency_ms", 0) for k, v in stage_metrics.items()
            },
            "passed": stats["median_ms"] < 150,
        }


def bench_memory_usage(
    num_memories: int = 1000,
) -> Dict[str, Any]:
    """Benchmark 4: Memory usage (SQLite DB size growth)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        bench_db = os.path.join(tmpdir, "memory_usage_bench.db")

        # Start tracking memory
        tracemalloc.start()

        store = RelationalStore(bench_db)

        # Measure memory before writes
        before_snapshot = tracemalloc.take_snapshot()
        before_size = os.path.getsize(bench_db)

        # Write memories
        for i in range(num_memories):
            store.store(generate_memory_record(i))

        # Measure memory after writes
        after_snapshot = tracemalloc.take_snapshot()
        after_size = os.path.getsize(bench_db)

        # Calculate memory difference
        top_stats = after_snapshot.compare_to(before_snapshot, "lineno")
        total_memory_kb = sum(stat.size_diff for stat in top_stats[:10]) / 1024

        tracemalloc.stop()

        return {
            "benchmark": "memory_usage",
            "num_memories": num_memories,
            "db_size_before_kb": round(before_size / 1024, 2),
            "db_size_after_kb": round(after_size / 1024, 2),
            "db_size_growth_kb": round((after_size - before_size) / 1024, 2),
            "process_memory_kb": round(total_memory_kb, 2),
            "memory_per_record_b": round((after_size - before_size) / num_memories, 2)
            if num_memories > 0
            else 0,
        }


def bench_concurrent_access(
    num_threads: int = 8,
    num_operations: int = 100,
) -> Dict[str, Any]:
    """Benchmark 5: Concurrent access throughput.

    Multiple threads performing simultaneous reads.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        bench_db = os.path.join(tmpdir, "concurrent_bench.db")
        store = RelationalStore(bench_db)

        # Populate with memories
        for i in range(100):
            store.store(generate_memory_record(i))

        results = []
        barrier = threading.Barrier(num_threads)

        def worker(thread_id: int):
            local_results = []
            for i in range(num_operations // num_threads):
                # Wait for all threads to be ready
                barrier.wait()
                start = time.perf_counter()
                _ = store.search("algorithm", limit=10)
                local_results.append((time.perf_counter() - start) * 1000)
            results.extend(local_results)

        # Run concurrent benchmark
        threads = []
        start_time = time.perf_counter()
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        total_time = time.perf_counter() - start_time
        throughput = num_operations / total_time

        return {
            "benchmark": "concurrent_access",
            "num_threads": num_threads,
            "total_operations": num_operations,
            "total_time_ms": round(total_time * 1000, 2),
            "throughput_ops_per_sec": round(throughput, 2),
            "avg_latency_ms": round(statistics.mean(results), 2),
            "max_latency_ms": round(max(results), 2),
        }


def bench_q_learning_update(
    num_runs: int = 15,
) -> Dict[str, Any]:
    """Benchmark 6: Q-Learning update latency."""
    try:
        from packages.learning_engine.rl.q_learning import (
            QLearningEngine,
            QState,
            ActionType,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            q_db = os.path.join(tmpdir, "q_learning.db")

            # Initialize Q-Learning engine
            ql = QLearningEngine(db_path=q_db)

            def measure_update():
                # Create a state using from_context factory
                state = QState.from_context(
                    task="benchmark test query",
                    context={"query_length": 25, "has_filters": False},
                )
                # Perform update using correct ActionType enum
                start = time.perf_counter()
                ql.update(
                    state=state, action=ActionType.EXPLORE, reward=0.8, next_state=None
                )
                return (time.perf_counter() - start) * 1000

            stats = run_benchmark(measure_update, num_runs=num_runs)

            return {
                "benchmark": "q_learning_update",
                "target_ms": 20,
                "metrics": stats,
                "passed": stats["median_ms"] < 20,
            }
    except ImportError as e:
        return {
            "benchmark": "q_learning_update",
            "error": f"Import failed: {e}",
            "skipped": True,
        }


def bench_scaling(
    memory_counts: List[int] = [100, 1000, 10000],
) -> Dict[str, Any]:
    """Benchmark 7: Large dataset scaling.

    Tests retrieval performance with increasing dataset sizes.
    """
    results = []

    for count in memory_counts:
        with tempfile.TemporaryDirectory() as tmpdir:
            bench_db = os.path.join(tmpdir, f"scaling_{count}.db")
            store = RelationalStore(bench_db)

            # Populate
            for i in range(count):
                store.store(generate_memory_record(i))

            # Measure search
            latencies = []
            for _ in range(10):
                start = time.perf_counter()
                _ = store.search("algorithm", limit=10)
                latencies.append((time.perf_counter() - start) * 1000)

            results.append(
                {
                    "num_memories": count,
                    "avg_latency_ms": round(statistics.mean(latencies), 2),
                    "p95_latency_ms": round(calculate_percentile(latencies, 95), 2),
                    "db_size_kb": round(os.path.getsize(bench_db) / 1024, 2),
                }
            )

    return {
        "benchmark": "scaling",
        "scales": results,
        "linearity": "check_p95" if results else None,
    }


def run_all_benchmarks() -> Dict[str, Any]:
    """Run all benchmarks and return combined results."""
    print("Running benchmark suite for memory+learning system...")
    print("=" * 60)

    results = {
        "timestamp": datetime.now().isoformat(),
        "python_version": sys.version,
        "benchmarks": [],
    }

    # Benchmark 1: Retrieval latency
    print("\n[1/7] Benchmarking retrieval latency...")
    results["benchmarks"].append(bench_retrieval_latency())

    # Benchmark 2: Memory write latency
    print("[2/7] Benchmarking memory write latency...")
    results["benchmarks"].append(bench_memory_write_latency())

    # Benchmark 3: Pipeline execution
    print("[3/7] Benchmarking pipeline execution...")
    results["benchmarks"].append(bench_pipeline_execution())

    # Benchmark 4: Memory usage
    print("[4/7] Benchmarking memory usage...")
    results["benchmarks"].append(bench_memory_usage())

    # Benchmark 5: Concurrent access
    print("[5/7] Benchmarking concurrent access...")
    results["benchmarks"].append(bench_concurrent_access())

    # Benchmark 6: Q-Learning update
    print("[6/7] Benchmarking Q-Learning update...")
    results["benchmarks"].append(bench_q_learning_update())

    # Benchmark 7: Scaling
    print("[7/7] Benchmarking scaling...")
    results["benchmarks"].append(bench_scaling())

    # Summary
    passed = sum(1 for b in results["benchmarks"] if b.get("passed", False))
    total = sum(
        1
        for b in results["benchmarks"]
        if not b.get("skipped", False) and "passed" in b
    )

    results["summary"] = {
        "passed": passed,
        "total": total,
        "pass_rate": f"{passed}/{total}" if total > 0 else "N/A",
    }

    print("\n" + "=" * 60)
    print(f"Benchmark complete: {passed}/{total} passed")

    return results


def save_results(results: Dict[str, Any]) -> str:
    """Save benchmark results to JSON file."""
    # Ensure directory exists
    output_dir = Path(".sisyphus/benchmarks")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with date
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_file = output_dir / f"retrieval-bench-{date_str}.json"

    # Write results
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    return str(output_file)


def main():
    """Main entry point."""
    # Run all benchmarks
    results = run_all_benchmarks()

    # Save to file
    output_path = save_results(results)
    print(f"\nResults saved to: {output_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)

    for bench in results["benchmarks"]:
        name = bench.get("benchmark", "unknown")
        if bench.get("skipped"):
            print(f"  {name}: SKIPPED - {bench.get('error', 'unknown')}")
        elif bench.get("passed"):
            print(f"  {name}: PASSED")
        else:
            print(f"  {name}: FAILED")

        # Show key metrics
        if "metrics" in bench:
            metrics = bench["metrics"]
            target = bench.get("target_ms", "N/A")
            actual = metrics.get("median_ms", "N/A")
            print(f"    Target: <{target}ms | Actual: {actual}ms")

    print(f"\nTotal: {results['summary']['pass_rate']} passed")

    return 0 if results["summary"]["passed"] == results["summary"]["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
