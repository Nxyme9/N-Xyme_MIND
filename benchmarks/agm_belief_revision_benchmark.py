#!/usr/bin/env python3
"""Benchmarks for AGM belief revision (Phase 1.2).

Benchmarks measure belief set operations at scale:
- Contraction operation (1000 iterations)
- Revision operation performance
- Entailment checking performance
- Conflict detection at scale
"""

import logging
import statistics
import time
from dataclasses import dataclass

from packages.memory_store.conflict_resolver import (
    AGMResolver,
    BeliefSet,
    MemoryConflictResolver,
)

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

    for _ in range(iterations):
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
        operations=iterations / (total / 1000),
    )


def benchmark_contraction_1000() -> BenchmarkResult:
    """Benchmark: contraction operation (1000 iterations)."""
    agm = AGMResolver()

    def do_contract():
        # Create fresh belief set each iteration
        K = BeliefSet(
            frozenset(
                {
                    "P is true",
                    "Q is true",
                    "R is true",
                    "S is true",
                    "T is true",
                    "U is true",
                }
            )
        )
        # Contract one belief
        result = agm.contract(K, "P is true")
        return result

    return run_benchmark("Contraction operation", 1000, do_contract)


def benchmark_revision_1000() -> BenchmarkResult:
    """Benchmark: revision operation (1000 iterations)."""
    agm = AGMResolver()

    def do_revision():
        # Create fresh belief set each iteration
        K = BeliefSet(frozenset({"P is true", "Q is true", "R is true"}))
        # Revise with potentially conflicting belief
        result = agm.revise(K, "P is false")
        return result

    return run_benchmark("Revision operation", 1000, do_revision)


def benchmark_expansion_1000() -> BenchmarkResult:
    """Benchmark: expansion operation (1000 iterations)."""
    agm = AGMResolver()

    def do_expand():
        K = BeliefSet(frozenset({"P is true"}))
        result = agm.expand(K, "Q is true")
        return result

    return run_benchmark("Expansion operation", 1000, do_expand)


def benchmark_entailment_checking() -> BenchmarkResult:
    """Benchmark: entailment checking performance."""
    agm = AGMResolver()

    # Create a large belief set
    large_beliefs = frozenset([f"P{i} is true" for i in range(100)])
    K = BeliefSet(large_beliefs)

    def do_entailment():
        # Check entailment for each proposition
        for i in range(10):
            _ = agm.support_entails(K, f"P{i} is true")
        return

    return run_benchmark("Entailment checking (10 queries)", 100, do_entailment)


def benchmark_inconsistency_detection() -> BenchmarkResult:
    """Benchmark: conflict detection at scale."""
    agm = AGMResolver()

    def do_inconsistent():
        # Create 10 belief sets, 3 of which are contradictory
        sets = [
            BeliefSet(frozenset({f"P{i} is true" for i in range(10)})) for _ in range(7)
        ]
        # Add contradictory sets
        sets.append(BeliefSet(frozenset({"P0 is false"})))
        sets.append(BeliefSet(frozenset({"P1 is false"})))
        sets.append(BeliefSet(frozenset({"P2 is false"})))

        result = agm.inconsistent(*sets)
        return result

    return run_benchmark("Inconsistency detection (10 sets)", 500, do_inconsistent)


def benchmark_memory_conflict_resolver() -> BenchmarkResult:
    """Benchmark: MemoryConflictResolver check_conflict."""
    resolver = MemoryConflictResolver()

    def do_check_conflict():
        new_content = "P is true and Q is true and R is true"
        existing = [(f"mem{i}", f"S{i} is true") for i in range(50)]
        # Add one conflicting memory
        existing.append(("conflict", "P is false"))

        conflicts = resolver.check_conflict("new_mem", new_content, existing)
        return conflicts

    return run_benchmark("MemoryConflictResolver (51 memories)", 500, do_check_conflict)


def benchmark_contraction_with_conflict() -> BenchmarkResult:
    """Benchmark: contraction with conflict resolution."""
    agm = AGMResolver()

    def do_contract_conflict():
        K = BeliefSet(frozenset({"P is true", "P is false", "Q is true", "R is true"}))
        result = agm.contract(K, "P is false")
        return result

    return run_benchmark("Contraction with conflict", 1000, do_contract_conflict)


def benchmark_large_belief_set_operations() -> BenchmarkResult:
    """Benchmark: operations on large belief sets (100+ beliefs)."""
    agm = AGMResolver()

    # Create large belief set (200 beliefs)
    large_beliefs = frozenset([f"P{i} is true" for i in range(200)])
    K = BeliefSet(large_beliefs)

    def do_large_operations():
        # Revise with new belief
        result = agm.revise(K, "new belief")
        # Check entailment
        _ = agm.support_entails(result, "P0 is true")
        return result

    return run_benchmark("Large belief set (200 beliefs)", 100, do_large_operations)


def benchmark_multiple_revisions() -> BenchmarkResult:
    """Benchmark: multiple sequential revisions."""
    agm = AGMResolver()

    def do_multiple_revisions():
        K = BeliefSet()
        # Perform 10 revisions
        for i in range(10):
            K = agm.revise(K, f"P{i} is true")
        return K

    return run_benchmark(
        "Multiple revisions (10 sequential)", 100, do_multiple_revisions
    )


def benchmark_negation_operations() -> BenchmarkResult:
    """Benchmark: negation generation for large sets."""
    agm = AGMResolver()

    def do_negate():
        for _ in range(100):
            _ = agm._negate("P is true")
            _ = agm._negate("color = red")
            _ = agm._negate("value != 42")
        return

    return run_benchmark("Negation generation (300 ops)", 100, do_negate)


def benchmark_equality_neq_operations() -> BenchmarkResult:
    """Benchmark: equality/inequality operations."""
    agm = AGMResolver()

    def do_eq_neq():
        K = BeliefSet(frozenset({"x = a", "y = b", "z = c"}))
        # Revise with conflicting values
        K = agm.revise(K, "x = b")
        K = agm.revise(K, "y = c")
        return K

    return run_benchmark("Equality/Inequality revisions", 1000, do_eq_neq)


def run_all_benchmarks() -> list[BenchmarkResult]:
    """Run all benchmarks and return results."""
    results = []

    print("\n" + "=" * 60)
    print("AGM BELIEF REVISION BENCHMARKS")
    print("=" * 60)

    # Core AGM operations
    results.append(benchmark_contraction_1000())
    print(format_result(results[-1]))

    results.append(benchmark_revision_1000())
    print(format_result(results[-1]))

    results.append(benchmark_expansion_1000())
    print(format_result(results[-1]))

    # Advanced operations
    results.append(benchmark_entailment_checking())
    print(format_result(results[-1]))

    results.append(benchmark_inconsistency_detection())
    print(format_result(results[-1]))

    results.append(benchmark_memory_conflict_resolver())
    print(format_result(results[-1]))

    # Scale tests
    results.append(benchmark_contraction_with_conflict())
    print(format_result(results[-1]))

    results.append(benchmark_large_belief_set_operations())
    print(format_result(results[-1]))

    results.append(benchmark_multiple_revisions())
    print(format_result(results[-1]))

    results.append(benchmark_negation_operations())
    print(format_result(results[-1]))

    results.append(benchmark_equality_neq_operations())
    print(format_result(results[-1]))

    return results


def main():
    """Run all benchmarks and display results."""
    results = run_all_benchmarks()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"\nTotal benchmarks run: {len(results)}")
    print(f"Total time: {sum(r.total_time_ms for r in results):.2f} ms")

    # Find fastest and slowest
    fastest = min(results, key=lambda r: r.mean_ms)
    slowest = max(results, key=lambda r: r.mean_ms)
    print(f"\nFastest: {fastest.name} ({fastest.mean_ms:.4f} ms)")
    print(f"Slowest: {slowest.name} ({slowest.mean_ms:.4f} ms)")


if __name__ == "__main__":
    main()
