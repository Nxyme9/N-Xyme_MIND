#!/usr/bin/env python3
"""Reranker Benchmark - Phase 1.3.

Benchmarks actual performance of reranking layer:
- Reranking time for 100 candidates
- Fallback chain performance
- Precision improvement measurement
- Throughput (candidates/second)
"""

import time
import statistics
from typing import Any, Dict, List

from packages.memory_store.reranker import (
    CohereReranker,
    HuggingFaceReranker,
    PassThroughReranker,
    get_reranker,
    get_default_reranker,
    set_default_reranker,
    RerankedResult,
    RerankerConfig,
)


# =============================================================================
# Test Data Generation
# =============================================================================


def generate_candidates(n: int = 100) -> List[Dict]:
    """Generate n test candidates with varying relevance."""
    topics = [
        "Python",
        "JavaScript",
        "React",
        "JWT",
        "OAuth",
        "authentication",
        "API",
        "database",
        "SQL",
        "async",
        "await",
        "hooks",
        "context",
        "Redux",
        "Node.js",
        "Express",
        "MongoDB",
        "PostgreSQL",
        "Docker",
        "Kubernetes",
        "AWS",
        "CI/CD",
        "testing",
        "Jest",
        "pytest",
    ]

    candidates = []
    for i in range(n):
        topic = topics[i % len(topics)]
        candidates.append(
            {
                "source": "memory",
                "content": f"{topic} tutorial for beginners - {i}",
                "score": 0.5 + (0.5 * (n - i) / n),  # Decreasing scores
            }
        )

    return candidates


def create_relevance_test_candidates() -> List[Dict]:
    """Create candidates where raw score != true relevance."""
    # High score but NOT relevant to auth query
    return [
        {
            "source": "memory",
            "content": "Python list comprehension tutorial",
            "score": 0.95,
        },
        {"source": "memory", "content": "JWT token authentication", "score": 0.85},
        {"source": "memory", "content": "JavaScript arrays guide", "score": 0.80},
        {"source": "memory", "content": "OAuth2 authentication flow", "score": 0.75},
        {"source": "memory", "content": "React hooks tutorial", "score": 0.70},
        {"source": "memory", "content": "SAML authentication", "score": 0.65},
        {"source": "memory", "content": "Python async await", "score": 0.60},
        {"source": "memory", "content": "LDAP authentication", "score": 0.55},
        {"source": "memory", "content": "Python decorators", "score": 0.50},
        {"source": "memory", "content": "MFA authentication setup", "score": 0.45},
    ]


# =============================================================================
# Precision Metrics
# =============================================================================


def calculate_precision_at_k(
    candidates: List[RerankedResult], query: str, k: int = 3
) -> float:
    """Calculate precision@k for reranked results.

    Measures how many relevant results are in top-k positions.
    """
    top_k = candidates[:k]

    # Define what's actually relevant to auth query
    relevant_keywords = ["JWT", "OAuth", "SAML", "LDAP", "MFA", "authentication"]

    relevant_count = sum(
        1
        for r in top_k
        if any(kw.lower() in r.content.lower() for kw in relevant_keywords)
    )

    return relevant_count / min(k, len(candidates))


def compare_orderings(candidates: List[Dict], query: str) -> Dict[str, Any]:
    """Compare raw vs reranked ordering."""
    reranker = get_reranker()

    # Raw ordering by score
    raw = sorted(candidates, key=lambda x: x["score"], reverse=True)

    # Reranked
    reranked = reranker.rerank(query, candidates, top_k=len(candidates))

    # Calculate how many moved up vs down
    raw_order = {c["content"]: i for i, c in enumerate(raw)}

    moved_up = 0
    moved_down = 0
    unchanged = 0

    for new_rank, r in enumerate(reranked):
        old_rank = raw_order.get(r.content, new_rank)

        if old_rank > new_rank:
            moved_up += 1
        elif old_rank < new_rank:
            moved_down += 1
        else:
            unchanged += 1

    return {
        "moved_up": moved_up,
        "moved_down": moved_down,
        "unchanged": unchanged,
    }


# =============================================================================
# Benchmark: Reranking Time
# =============================================================================


def benchmark_rerank_time(n_candidates: int = 100, runs: int = 5) -> Dict[str, float]:
    """Benchmark time to rerank n candidates."""
    reranker = get_reranker()
    candidates = generate_candidates(n_candidates)
    query = "authentication tutorial"

    times = []

    for _ in range(runs):
        start = time.perf_counter()
        results = reranker.rerank(query, candidates, top_k=10)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    return {
        "n_candidates": n_candidates,
        "runs": runs,
        "mean_time_ms": statistics.mean(times) * 1000,
        "median_time_ms": statistics.median(times) * 1000,
        "min_time_ms": min(times) * 1000,
        "max_time_ms": max(times) * 1000,
        "stdev_ms": statistics.stdev(times) * 1000 if len(times) > 1 else 0,
    }


# =============================================================================
# Benchmark: Fallback Chain
# =============================================================================


def benchmark_fallback_chain() -> Dict[str, Any]:
    """Benchmark fallback chain performance."""
    results = {}

    # Test Cohere
    try:
        cohere = CohereReranker()
        available = cohere.is_available()
        results["cohere_available"] = available

        if available:
            start = time.perf_counter()
            candidates = generate_candidates(20)
            cohere.rerank("test", candidates, top_k=5)
            results["cohere_time_ms"] = (time.perf_counter() - start) * 1000
        else:
            results["cohere_time_ms"] = None
    except Exception as e:
        results["cohere_available"] = False
        results["cohere_error"] = str(e)

    # Test HuggingFace
    try:
        hf = HuggingFaceReranker()
        available = hf.is_available()
        results["hf_available"] = available

        if available:
            start = time.perf_counter()
            candidates = generate_candidates(20)
            hf.rerank("test", candidates, top_k=5)
            results["hf_time_ms"] = (time.perf_counter() - start) * 1000
        else:
            results["hf_time_ms"] = None
    except Exception as e:
        results["hf_available"] = False
        results["hf_error"] = str(e)

    # Test PassThrough
    try:
        pt = PassThroughReranker()

        start = time.perf_counter()
        candidates = generate_candidates(20)
        pt.rerank("test", candidates, top_k=5)
        results["passthrough_time_ms"] = (time.perf_counter() - start) * 1000
    except Exception as e:
        results["passthrough_error"] = str(e)

    return results


# =============================================================================
# Benchmark: Precision Improvement
# =============================================================================


def benchmark_precision_improvement() -> Dict[str, Any]:
    """Benchmark precision improvement from reranking."""
    reranker = get_reranker()

    candidates = create_relevance_test_candidates()
    query = "authentication"

    # Raw ordering
    raw = sorted(candidates, key=lambda x: x["score"], reverse=True)[:3]
    raw_contents = [c["content"] for c in raw]

    # Reranked
    reranked = reranker.rerank(query, candidates, top_k=3)
    reranked_contents = [r.content for r in reranked[:3]]

    # Relevant keywords
    relevant_keywords = ["JWT", "OAuth", "SAML", "LDAP", "MFA", "authentication"]

    # Count relevant in each ordering
    raw_relevant = sum(
        1
        for c in raw_contents
        if any(kw.lower() in c.lower() for kw in relevant_keywords)
    )

    reranked_relevant = sum(
        1
        for c in reranked_contents
        if any(kw.lower() in c.lower() for kw in relevant_keywords)
    )

    # Precision@3
    raw_precision = raw_relevant / 3
    reranked_precision = reranked_relevant / 3

    return {
        "query": query,
        "n_candidates": len(candidates),
        "raw_top3": raw_contents,
        "reranked_top3": reranked_contents,
        "raw_relevant_count": raw_relevant,
        "reranked_relevant_count": reranked_relevant,
        "raw_precision@3": raw_precision,
        "reranked_precision@3": reranked_precision,
        "precision_improvement": reranked_precision - raw_precision,
    }


# =============================================================================
# Benchmark: Throughput
# =============================================================================


def benchmark_throughput(
    n_candidates: int = 100, duration_sec: float = 2.0
) -> Dict[str, float]:
    """Benchmark throughput (candidates/second)."""
    reranker = get_reranker()
    candidates = generate_candidates(n_candidates)
    query = "authentication tutorial"

    # Warm up
    reranker.rerank(query, candidates[:10], top_k=5)

    # Count iterations over duration
    count = 0
    start = time.perf_counter()

    while time.perf_counter() - start < duration_sec:
        reranker.rerank(query, candidates, top_k=10)
        count += 1

    elapsed = time.perf_counter() - start

    return {
        "n_candidates": n_candidates,
        "iterations": count,
        "duration_sec": elapsed,
        "throughput_candidates_per_sec": (count * n_candidates) / elapsed,
    }


# =============================================================================
# Benchmark: Ordering Changes
# =============================================================================


def benchmark_ordering_changes(n: int = 50) -> Dict[str, Any]:
    """Measure how often reranking changes ordering."""
    candidates = generate_candidates(n)
    query = "Python authentication"

    comparison = compare_orderings(candidates, query)

    return {
        "n_candidates": n,
        "query": query,
        "moved_up": comparison["moved_up"],
        "moved_down": comparison["moved_down"],
        "unchanged": comparison["unchanged"],
        "pct_changed": (comparison["moved_up"] + comparison["moved_down"]) / n * 100,
    }


# =============================================================================
# Main Benchmark Runner
# =============================================================================


def run_benchmarks() -> Dict[str, Any]:
    """Run all benchmarks."""
    results = {}

    print("=" * 60)
    print("RERANKER BENCHMARK - Phase 1.3")
    print("=" * 60)

    # Determine which reranker is active
    active = get_default_reranker()
    results["active_reranker"] = active._name
    print(f"\nActive reranker: {active._name}")

    # 1. Reranking time
    print("\n[1] Reranking Time (100 candidates)...")
    try:
        time_results = benchmark_rerank_time(100, runs=5)
        results["rerank_time"] = time_results
        print(f"    Mean: {time_results['mean_time_ms']:.2f} ms")
        print(f"    Median: {time_results['median_time_ms']:.2f} ms")
        print(f"    Stdev: {time_results['stdev_ms']:.2f} ms")
    except Exception as e:
        results["rerank_time_error"] = str(e)
        print(f"    ERROR: {e}")

    # 2. Fallback chain
    print("\n[2] Fallback Chain...")
    try:
        fb_results = benchmark_fallback_chain()
        results["fallback_chain"] = fb_results
        print(
            f"    Cohere: available={fb_results.get('cohere_available')}, time={fb_results.get('cohere_time_ms')}"
        )
        print(
            f"    HuggingFace: available={fb_results.get('hf_available')}, time={fb_results.get('hf_time_ms')}"
        )
        print(f"    PassThrough: time={fb_results.get('passthrough_time_ms')}")
    except Exception as e:
        results["fallback_chain_error"] = str(e)
        print(f"    ERROR: {e}")

    # 3. Precision improvement
    print("\n[3] Precision Improvement...")
    try:
        prec_results = benchmark_precision_improvement()
        results["precision"] = prec_results
        print(f"    Query: {prec_results['query']}")
        print(f"    Raw precision@3: {prec_results['raw_precision@3']:.2f}")
        print(f"    Reranked precision@3: {prec_results['reranked_precision@3']:.2f}")
        print(f"    Improvement: {prec_results['precision_improvement']:.2f}")
        print(f"    Raw top-3: {prec_results['raw_top3']}")
        print(f"    Reranked top-3: {prec_results['reranked_top3']}")
    except Exception as e:
        results["precision_error"] = str(e)
        print(f"    ERROR: {e}")

    # 4. Throughput
    print("\n[4] Throughput...")
    try:
        tp_results = benchmark_throughput(100, duration_sec=1.0)
        results["throughput"] = tp_results
        print(
            f"    Throughput: {tp_results['throughput_candidates_per_sec']:.1f} candidates/sec"
        )
    except Exception as e:
        results["throughput_error"] = str(e)
        print(f"    ERROR: {e}")

    # 5. Ordering changes
    print("\n[5] Ordering Changes (50 candidates)...")
    try:
        order_results = benchmark_ordering_changes(50)
        results["ordering_changes"] = order_results
        print(f"    Moved up: {order_results['moved_up']}")
        print(f"    Moved down: {order_results['moved_down']}")
        print(f"    Unchanged: {order_results['unchanged']}")
        print(f"    % Changed: {order_results['pct_changed']:.1f}%")
    except Exception as e:
        results["ordering_error"] = str(e)
        print(f"    ERROR: {e}")

    print("\n" + "=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)

    return results


if __name__ == "__main__":
    results = run_benchmarks()

    # Optionally save results
    import json

    with open("benchmarks/reranker_results.json", "w") as f:
        # Convert any non-serializable values
        json.dump(results, f, default=str, indent=2)

    print("\nResults saved to benchmarks/reranker_results.json")
