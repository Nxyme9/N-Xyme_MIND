#!/usr/bin/env python3
"""Benchmark script for TEMPR retrieval engine.

Compares:
- Semantic retrieval latency
- Keyword retrieval latency
- TEMPR (fused) retrieval latency
- Old router retrieval latency

Usage:
    python3 scripts/benchmark_retrieval.py [--queries 10] [--top-k 5]
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def benchmark_search(func, queries, top_k, name):
    """Benchmark a search function."""
    latencies = []
    total_results = 0

    for query in queries:
        start = time.time()
        results = func(query, top_k=top_k)
        elapsed = (time.time() - start) * 1000
        latencies.append(elapsed)
        total_results += len(results)

    return {
        "name": name,
        "queries": len(queries),
        "total_results": total_results,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2),
        "p50_latency_ms": round(sorted(latencies)[len(latencies) // 2], 2),
        "p95_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 2),
        "min_latency_ms": round(min(latencies), 2),
        "max_latency_ms": round(max(latencies), 2),
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark TEMPR retrieval engine")
    parser.add_argument(
        "--queries", type=int, default=10, help="Number of test queries"
    )
    parser.add_argument("--top-k", type=int, default=5, help="Results per query")
    args = parser.parse_args()

    # Test queries
    test_queries = [
        "memory system architecture",
        "self-learning implementation",
        "knowledge graph entities",
        "embedding pipeline",
        "daemon configuration",
        "MCP server tools",
        "file scanning",
        "priority engine",
        "preference model",
        "forgetting curve",
        "sleep cycle",
        "compaction",
        "hierarchical memory",
        "dossier system",
        "entity extraction",
    ]
    queries = test_queries[: args.queries]

    print("=" * 70)
    print("TEMPR RETRIEVAL BENCHMARK")
    print("=" * 70)
    print(f"Queries: {len(queries)}, Top-K: {args.top_k}")
    print()

    results = []

    # Benchmark semantic retriever
    print("Benchmarking semantic retriever...")
    from src.memory.retrievers.semantic import SemanticRetriever

    sr = SemanticRetriever()
    results.append(benchmark_search(sr.search, queries, args.top_k, "Semantic"))

    # Benchmark keyword retriever
    print("Benchmarking keyword retriever...")
    from src.memory.retrievers.keyword import KeywordRetriever

    kr = KeywordRetriever()
    results.append(benchmark_search(kr.search, queries, args.top_k, "Keyword"))

    # Benchmark TEMPR retriever
    print("Benchmarking TEMPR retriever...")
    from src.memory.retrievers.fusion import TEMPRRetriever

    tr = TEMPRRetriever()
    results.append(benchmark_search(tr.search, queries, args.top_k, "TEMPR"))

    # Benchmark old router
    print("Benchmarking old router...")
    from src.memory.router import get_unified_memory, UnifiedMemoryQuery

    def old_router_search(query, top_k):
        result = get_unified_memory(query, max_results=top_k)
        return result.results

    results.append(
        benchmark_search(old_router_search, queries, args.top_k, "Old Router")
    )

    # Print results
    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(
        f"{'Method':<15} {'Avg (ms)':<10} {'P50 (ms)':<10} {'P95 (ms)':<10} {'Min (ms)':<10} {'Max (ms)':<10} {'Results':<10}"
    )
    print("-" * 70)
    for r in results:
        print(
            f"{r['name']:<15} {r['avg_latency_ms']:<10} {r['p50_latency_ms']:<10} {r['p95_latency_ms']:<10} {r['min_latency_ms']:<10} {r['max_latency_ms']:<10} {r['total_results']:<10}"
        )

    print()
    print("=" * 70)
    print("BENCHMARK COMPLETE")
    print("=" * 70)

    # Save results
    output_path = Path(__file__).parent.parent / ".context" / "benchmark-retrieval.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
