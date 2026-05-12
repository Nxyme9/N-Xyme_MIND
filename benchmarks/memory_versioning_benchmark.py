#!/usr/bin/env python3
"""Benchmarks for memory versioning feature (Phase 1.1)."""

import logging
import statistics
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List

from packages.memory_store.memory_manager import MemoryManager

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a benchmark."""

    name: str
    iterations: int
    total_time_ms: float
    mean_ms: float
    std_dev_ms: float
    min_ms: float
    max_ms: float
    operations: float


def format_result(result: BenchmarkResult) -> str:
    """Format benchmark result for display."""
    return (
        f"\n{result.name}\n"
        f"  Iterations:    {result.iterations}\n"
        f"  Total time:   {result.total_time_ms:.2f} ms\n"
        f"  Mean:        {result.mean_ms:.4f} ms\n"
        f"  Std Dev:     {result.std_dev_ms:.4f} ms\n"
        f"  Min/Max:     {result.min_ms:.4f} / {result.max_ms:.4f} ms\n"
        f"  Ops/sec:      {result.operations:.2f}"
    )


def run_benchmark(name: str, iterations: int, func) -> BenchmarkResult:
    """Run a benchmark and collect statistics."""
    times_ms = []

    for i in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times_ms.append((end - start) * 1000)

    total = sum(times_ms)
    mean = total / iterations
    std_dev = statistics.stdev(times_ms) if iterations > 1 else 0

    return BenchmarkResult(
        name=name,
        iterations=iterations,
        total_time_ms=total,
        mean_ms=mean,
        std_dev_ms=std_dev,
        min_ms=min(times_ms),
        max_ms=max(times_ms),
        operations=iterations / (total / 1000),  # ops per second
    )


def benchmark_write_1000_memories(temp_db_path: str) -> BenchmarkResult:
    """Benchmark: write 1000 memories, measure time per write."""

    def do_write():
        mm = MemoryManager(db_path=temp_db_path)
        mm.on_memory_write(
            memory_id=f"bench_mem_{id(do_write)}",
            content=f"Benchmark memory content {id(do_write)}",
            kind="episodic",
            scope="global",
        )

    # Use single manager for realistic test
    mm = MemoryManager(db_path=temp_db_path)
    times_ms = []

    for i in range(1000):
        start = time.perf_counter()
        mm.on_memory_write(
            memory_id=f"bench_mem_{i}",
            content=f"Benchmark memory content number {i}",
            kind="episodic",
            scope="global",
        )
        end = time.perf_counter()
        times_ms.append((end - start) * 1000)

    total = sum(times_ms)
    mean = total / 1000

    return BenchmarkResult(
        name="Write 1000 memories",
        iterations=1000,
        total_time_ms=total,
        mean_ms=mean,
        std_dev_ms=statistics.stdev(times_ms) if 1000 > 1 else 0,
        min_ms=min(times_ms),
        max_ms=max(times_ms),
        operations=1000 / (total / 1000),
    )


def benchmark_rollback_operation(temp_db_path: str) -> BenchmarkResult:
    """Benchmark: rollback operation (measure ms)."""
    mm = MemoryManager(db_path=temp_db_path)

    # Setup: create memory with multiple versions
    memory_id = "rollback_bench"
    for i in range(10):
        mm.on_memory_write(
            memory_id=memory_id,
            content=f"Version {i}",
        )

    # Get history to rollback to
    history = mm.get_version_history(memory_id)
    rollback_hash = (
        history[-1]["version_hash"] if len(history) > 1 else history[0]["version_hash"]
    )

    # Benchmark rollback
    times_ms = []
    for i in range(100):
        start = time.perf_counter()
        mm.rollback_to_version(memory_id=memory_id, version_hash=rollback_hash)
        end = time.perf_counter()
        times_ms.append((end - start) * 1000)

        # Re-create version to rollback to
        mm.on_memory_write(memory_id=memory_id, content=f"After rollback {i}")

    total = sum(times_ms)

    return BenchmarkResult(
        name="Rollback operation (100 iterations)",
        iterations=100,
        total_time_ms=total,
        mean_ms=total / 100,
        std_dev_ms=statistics.stdev(times_ms) if 100 > 1 else 0,
        min_ms=min(times_ms),
        max_ms=max(times_ms),
        operations=100 / (total / 1000),
    )


def benchmark_branch_creation(temp_db_path: str) -> BenchmarkResult:
    """Benchmark: branch creation overhead."""
    mm = MemoryManager(db_path=temp_db_path)
    times_ms = []

    for i in range(500):
        start = time.perf_counter()
        mm.create_branch(f"bench_branch_{i}")
        end = time.perf_counter()
        times_ms.append((end - start) * 1000)

    total = sum(times_ms)

    return BenchmarkResult(
        name="Branch creation (500 branches)",
        iterations=500,
        total_time_ms=total,
        mean_ms=total / 500,
        std_dev_ms=statistics.stdev(times_ms) if 500 > 1 else 0,
        min_ms=min(times_ms),
        max_ms=max(times_ms),
        operations=500 / (total / 1000),
    )


def benchmark_version_history_retrieval(temp_db_path: str) -> BenchmarkResult:
    """Benchmark: version history retrieval at scale."""
    mm = MemoryManager(db_path=temp_db_path)

    # Setup: create 100 memories with 10 versions each
    for i in range(100):
        for v in range(10):
            mm.on_memory_write(
                memory_id=f"scale_mem_{i}",
                content=f"Version {v} for memory {i}",
            )

    # Benchmark retrieval
    times_ms = []
    for i in range(100):
        start = time.perf_counter()
        mm.get_version_history(f"scale_mem_{i % 100}")
        end = time.perf_counter()
        times_ms.append((end - start) * 1000)

    total = sum(times_ms)

    return BenchmarkResult(
        name="Version history retrieval (100 queries)",
        iterations=100,
        total_time_ms=total,
        mean_ms=total / 100,
        std_dev_ms=statistics.stdev(times_ms) if 100 > 1 else 0,
        min_ms=min(times_ms),
        max_ms=max(times_ms),
        operations=100 / (total / 1000),
    )


def benchmark_branch_switching(temp_db_path: str) -> BenchmarkResult:
    """Benchmark: branch switching time."""
    mm = MemoryManager(db_path=temp_db_path)

    # Create branches
    branches = []
    for i in range(50):
        b = mm.create_branch(f"switch_branch_{i}")
        branches.append(b["id"])

    # Benchmark switching
    times_ms = []
    for i in range(200):
        branch_id = branches[i % len(branches)]
        start = time.perf_counter()
        mm.switch_branch(branch_id)
        end = time.perf_counter()
        times_ms.append((end - start) * 1000)

    total = sum(times_ms)

    return BenchmarkResult(
        name="Branch switching (200 switches)",
        iterations=200,
        total_time_ms=total,
        mean_ms=total / 200,
        std_dev_ms=statistics.stdev(times_ms) if 200 > 1 else 0,
        min_ms=min(times_ms),
        max_ms=max(times_ms),
        operations=200 / (total / 1000),
    )


def benchmark_merge_operation(temp_db_path: str) -> BenchmarkResult:
    """Benchmark: merge operation."""
    mm = MemoryManager(db_path=temp_db_path)

    # Create feature branch with memories
    feature = mm.create_branch("merge_feature")
    mm.switch_branch(feature["id"])

    for i in range(20):
        mm.on_memory_write(
            memory_id=f"merge_mem_{i}",
            content=f"Feature content {i}",
        )

    # Get main branch
    main = mm.store.get_branch_by_name("main")

    if not main:
        return BenchmarkResult(
            name="Merge operation (skipped - no main branch)",
            iterations=0,
            total_time_ms=0,
            mean_ms=0,
            std_dev_ms=0,
            min_ms=0,
            max_ms=0,
            operations=0,
        )

    # Benchmark merge
    start = time.perf_counter()
    result = mm.merge_branch(
        source_branch_id=feature["id"],
        target_branch_id=main["id"],
    )
    end = time.perf_counter()
    total_ms = (end - start) * 1000

    return BenchmarkResult(
        name="Merge operation (20 memories)",
        iterations=1,
        total_time_ms=total_ms,
        mean_ms=total_ms,
        std_dev_ms=0,
        min_ms=total_ms,
        max_ms=total_ms,
        operations=1 / (total_ms / 1000),
    )


def run_all_benchmarks():
    """Run all memory versioning benchmarks."""
    # Create temp database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "benchmark_memory.db"

        results: List[BenchmarkResult] = []

        print("\n" + "=" * 60)
        print("MEMORY VERSIONING BENCHMARKS")
        print("=" * 60)

        # Run each benchmark
        print("\nRunning benchmarks...")
        print("  1. Write 1000 memories")
        r1 = benchmark_write_1000_memories(str(db_path))
        results.append(r1)
        print(f"      Done: {r1.total_time_ms:.2f} ms total, {r1.mean_ms:.4f} ms/op")

        print("  2. Rollback operation")
        r2 = benchmark_rollback_operation(str(db_path))
        results.append(r2)
        print(f"      Done: {r2.total_time_ms:.2f} ms total, {r2.mean_ms:.4f} ms/op")

        print("  3. Branch creation")
        r3 = benchmark_branch_creation(str(db_path))
        results.append(r3)
        print(f"      Done: {r3.total_time_ms:.2f} ms total, {r3.mean_ms:.4f} ms/op")

        print("  4. Version history retrieval")
        r4 = benchmark_version_history_retrieval(str(db_path))
        results.append(r4)
        print(f"      Done: {r4.total_time_ms:.2f} ms total, {r4.mean_ms:.4f} ms/op")

        print("  5. Branch switching")
        r5 = benchmark_branch_switching(str(db_path))
        results.append(r5)
        print(f"      Done: {r5.total_time_ms:.2f} ms total, {r5.mean_ms:.4f} ms/op")

        print("  6. Merge operation")
        r6 = benchmark_merge_operation(str(db_path))
        results.append(r6)
        print(f"      Done: {r6.total_time_ms:.2f} ms total")

        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"\n{'Benchmark':<40} {'Mean (ms)':<12} {'Ops/sec':<12}")
        print("-" * 64)
        for r in results:
            print(f"{r.name:<40} {r.mean_ms:<12.4f} {r.operations:<12.2f}")

        print("\n" + "=" * 60)
        print("DETAILED RESULTS")
        print("=" * 60)
        for r in results:
            print(format_result(r))

        print("\n")


if __name__ == "__main__":
    run_all_benchmarks()
