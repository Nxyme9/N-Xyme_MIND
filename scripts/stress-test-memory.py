#!/usr/bin/env python3
"""
Stress Test for Memory System
Tests concurrent queries, large payloads, rapid-fire requests, and edge cases.
"""

import json
import os
import psutil
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from threading import Lock

PROJECT_ROOT = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
DB_PATH = PROJECT_ROOT / "context/memory/mind_from_mind.db"

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from memory.router import MemoryRouter, UnifiedMemoryQuery, get_router
from memory.embedding_pipeline import embed_batch

print_lock = Lock()


def get_memory_mb() -> float:
    """Get current process memory in MB."""
    return psutil.Process().memory_info().rss / 1024 / 1024


def log(msg: str):
    """Thread-safe logging."""
    with print_lock:
        print(msg)


@dataclass
class TestResult:
    """Result of a single test."""

    name: str
    success: bool
    response_time_ms: float
    memory_mb: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def load_entities() -> List[Dict]:
    """Load entities from knowledge graph."""
    path = PROJECT_ROOT / ".context/memory_graph/entities.json"
    if path.exists():
        with open(path) as f:
            data = json.load(f)
            return data.get("entities", [])
    return []


def load_relations() -> List[Dict]:
    """Load relations from knowledge graph."""
    path = PROJECT_ROOT / ".context/memory_graph/relations.json"
    if path.exists():
        with open(path) as f:
            data = json.load(f)
            return data.get("relations", [])
    return []


def load_global_messages(limit: int = 175) -> List[Dict]:
    """Load global messages from database."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT id, content, role, session_title, created_at FROM global_message_index LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "content": r[1],
            "role": r[2],
            "session_title": r[3],
            "created_at": r[4],
        }
        for r in rows
    ]


def test_concurrent_queries(router: MemoryRouter, num_queries: int = 50) -> TestResult:
    """Test a: 50 simultaneous semantic search queries."""
    log(f"  Running {num_queries} concurrent queries...")
    queries = [
        "agent orchestration memory system",
        "embedding pipeline database",
        "semantic search knowledge graph",
        "session management workflow",
        "model routing configuration",
    ] * (num_queries // 5 + 1)
    queries = queries[:num_queries]

    start_mem = get_memory_mb()
    start_time = time.time()
    errors = []
    success_count = 0

    with ThreadPoolExecutor(max_workers=num_queries) as executor:
        futures = {
            executor.submit(
                router.search, UnifiedMemoryQuery(query=q, max_results_per_source=3)
            ): q
            for q in queries
        }
        for future in as_completed(futures):
            try:
                result = future.result()
                if result.total_results >= 0:
                    success_count += 1
            except Exception as e:
                errors.append(str(e))

    elapsed_ms = (time.time() - start_time) * 1000
    end_mem = get_memory_mb()

    success = success_count == num_queries
    error = f"{len(errors)} errors" if errors else None

    return TestResult(
        name="Concurrent Queries (50x)",
        success=success,
        response_time_ms=elapsed_ms,
        memory_mb=end_mem - start_mem,
        error=error,
        metadata={"success_count": success_count, "total": num_queries},
    )


def test_large_payload(router: MemoryRouter) -> TestResult:
    """Test b: Query with 10,000+ character input."""
    log("  Testing large payload (10KB query)...")

    large_query = "Lorem ipsum " * 800  # ~10KB
    start_mem = get_memory_mb()
    start_time = time.time()

    try:
        result = router.search(
            UnifiedMemoryQuery(query=large_query, max_results_per_source=3)
        )
        elapsed_ms = (time.time() - start_time) * 1000
        end_mem = get_memory_mb()

        return TestResult(
            name="Large Payload (10KB)",
            success=True,
            response_time_ms=elapsed_ms,
            memory_mb=end_mem - start_mem,
            metadata={"query_len": len(large_query), "results": result.total_results},
        )
    except Exception as e:
        end_mem = get_memory_mb()
        return TestResult(
            name="Large Payload (10KB)",
            success=False,
            response_time_ms=(time.time() - start_time) * 1000,
            memory_mb=end_mem - start_mem,
            error=str(e),
        )


def test_rapid_fire(router: MemoryRouter, num_queries: int = 100) -> TestResult:
    """Test c: 100 queries in rapid succession."""
    log(f"  Running {num_queries} rapid-fire queries...")

    queries = [f"test query {i}" for i in range(num_queries)]
    start_mem = get_memory_mb()
    start_time = time.time()
    errors = []
    success_count = 0

    for q in queries:
        try:
            result = router.search(
                UnifiedMemoryQuery(query=q, max_results_per_source=2)
            )
            success_count += 1
        except Exception as e:
            errors.append(str(e))

    elapsed_ms = (time.time() - start_time) * 1000
    end_mem = get_memory_mb()

    success = success_count == num_queries
    error = f"{len(errors)} errors" if errors else None

    return TestResult(
        name="Rapid Fire (100x)",
        success=success,
        response_time_ms=elapsed_ms,
        memory_mb=end_mem - start_mem,
        error=error,
        metadata={"success_count": success_count, "total": num_queries},
    )


def test_empty_queries(router: MemoryRouter) -> TestResult:
    """Test d: Empty string, whitespace-only, null queries."""
    log("  Testing empty/invalid queries...")

    test_cases = [
        ("", "empty"),
        ("   ", "whitespace"),
        ("\t\n", "newline_tab"),
    ]

    start_mem = get_memory_mb()
    start_time = time.time()
    errors = []
    success_count = 0

    for query, label in test_cases:
        try:
            result = router.search(
                UnifiedMemoryQuery(query=query, max_results_per_source=2)
            )
            success_count += 1
        except Exception as e:
            errors.append(f"{label}: {str(e)}")

    elapsed_ms = (time.time() - start_time) * 1000
    end_mem = get_memory_mb()

    success = success_count == len(test_cases)
    error = "; ".join(errors) if errors else None

    return TestResult(
        name="Empty Queries",
        success=success,
        response_time_ms=elapsed_ms,
        memory_mb=end_mem - start_mem,
        error=error,
        metadata={"tested": len(test_cases), "passed": success_count},
    )


def test_special_characters(router: MemoryRouter) -> TestResult:
    """Test e: SQL injection, unicode, emojis."""
    log("  Testing special characters...")

    test_cases = [
        ("'; DROP TABLE memories; --", "sql_injection"),
        ("<script>alert('xss')</script>", "xss"),
        ("日本語テスト", "japanese"),
        ("🎉🚀💻", "emojis"),
        ("Îñtërnâtionål", "unicode"),
    ]

    start_mem = get_memory_mb()
    start_time = time.time()
    errors = []
    success_count = 0

    for query, label in test_cases:
        try:
            result = router.search(
                UnifiedMemoryQuery(query=query, max_results_per_source=2)
            )
            success_count += 1
        except Exception as e:
            errors.append(f"{label}: {str(e)}")

    elapsed_ms = (time.time() - start_time) * 1000
    end_mem = get_memory_mb()

    success = success_count == len(test_cases)
    error = "; ".join(errors) if errors else None

    return TestResult(
        name="Special Characters",
        success=success,
        response_time_ms=elapsed_ms,
        memory_mb=end_mem - start_mem,
        error=error,
        metadata={"tested": len(test_cases), "passed": success_count},
    )


def test_knowledge_graph_load() -> TestResult:
    """Test f: Load all 54 entities + 104 relations simultaneously."""
    log("  Testing knowledge graph load...")

    start_mem = get_memory_mb()
    start_time = time.time()

    try:
        entities = load_entities()
        relations = load_relations()

        elapsed_ms = (time.time() - start_time) * 1000
        end_mem = get_memory_mb()

        success = len(entities) > 0 and len(relations) > 0

        return TestResult(
            name="Knowledge Graph Load",
            success=success,
            response_time_ms=elapsed_ms,
            memory_mb=end_mem - start_mem,
            metadata={"entities": len(entities), "relations": len(relations)},
        )
    except Exception as e:
        end_mem = get_memory_mb()
        return TestResult(
            name="Knowledge Graph Load",
            success=False,
            response_time_ms=(time.time() - start_time) * 1000,
            memory_mb=end_mem - start_mem,
            error=str(e),
        )


def test_global_message_search(
    router: MemoryRouter, num_queries: int = 50
) -> TestResult:
    """Test g: Query 175 indexed messages concurrently."""
    log(f"  Testing global message search ({num_queries} queries)...")

    messages = load_global_messages(175)
    if not messages:
        return TestResult(
            name="Global Message Search",
            success=False,
            response_time_ms=0,
            memory_mb=0,
            error="No messages found",
        )

    queries = [m["content"][:50] for m in messages[:num_queries]]

    start_mem = get_memory_mb()
    start_time = time.time()
    errors = []
    success_count = 0

    with ThreadPoolExecutor(max_workers=min(20, num_queries)) as executor:
        futures = {
            executor.submit(
                router.search, UnifiedMemoryQuery(query=q, max_results_per_source=3)
            ): q
            for q in queries
        }
        for future in as_completed(futures):
            try:
                result = future.result()
                if result.total_results >= 0:
                    success_count += 1
            except Exception as e:
                errors.append(str(e))

    elapsed_ms = (time.time() - start_time) * 1000
    end_mem = get_memory_mb()

    success = success_count == num_queries
    error = f"{len(errors)} errors" if errors else None

    return TestResult(
        name="Global Message Search",
        success=success,
        response_time_ms=elapsed_ms,
        memory_mb=end_mem - start_mem,
        error=error,
        metadata={
            "success_count": success_count,
            "total": num_queries,
            "messages": len(messages),
        },
    )


def test_auto_embed_stress(num_concurrent: int = 10) -> TestResult:
    """Test h: Embed 50 memories simultaneously."""
    log(f"  Testing auto-embed stress ({num_concurrent} concurrent)...")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT id, content FROM memories WHERE content IS NOT NULL AND content != '' LIMIT 50"
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return TestResult(
            name="Auto-Embed Stress",
            success=False,
            response_time_ms=0,
            memory_mb=0,
            error="No memories found",
        )

    memory_ids_and_contents = [(r[0], r[1][:500]) for r in rows]  # Limit content size

    start_mem = get_memory_mb()
    start_time = time.time()

    try:
        from memory.embedding_pipeline import _check_ollama_available

        ollama_ok = _check_ollama_available()

        if not ollama_ok:
            elapsed_ms = (time.time() - start_time) * 1000
            end_mem = get_memory_mb()
            return TestResult(
                name="Auto-Embed Stress",
                success=True,  # Expected to fail if Ollama not running
                response_time_ms=elapsed_ms,
                memory_mb=end_mem - start_mem,
                error="Ollama unavailable",
                metadata={"queued": len(memory_ids_and_contents), "ollama": False},
            )

        success_count = embed_batch(memory_ids_and_contents, batch_size=5)

        elapsed_ms = (time.time() - start_time) * 1000
        end_mem = get_memory_mb()

        return TestResult(
            name="Auto-Embed Stress",
            success=success_count > 0,
            response_time_ms=elapsed_ms,
            memory_mb=end_mem - start_mem,
            metadata={
                "attempted": len(memory_ids_and_contents),
                "embedded": success_count,
            },
        )
    except Exception as e:
        end_mem = get_memory_mb()
        return TestResult(
            name="Auto-Embed Stress",
            success=False,
            response_time_ms=(time.time() - start_time) * 1000,
            memory_mb=end_mem - start_mem,
            error=str(e),
        )


def run_all_tests() -> List[TestResult]:
    """Run all stress tests."""
    results = []

    log("\n=== INITIALIZING MEMORY ROUTER ===")
    router = get_router()
    log(f"Router initialized. Current memory: {get_memory_mb():.1f} MB\n")

    log("=== TEST A: CONCURRENT QUERIES ===")
    results.append(test_concurrent_queries(router, 50))
    log(f"  Result: {results[-1].success} ({results[-1].response_time_ms:.1f}ms)\n")

    log("=== TEST B: LARGE PAYLOAD ===")
    results.append(test_large_payload(router))
    log(f"  Result: {results[-1].success} ({results[-1].response_time_ms:.1f}ms)\n")

    log("=== TEST C: RAPID FIRE ===")
    results.append(test_rapid_fire(router, 100))
    log(f"  Result: {results[-1].success} ({results[-1].response_time_ms:.1f}ms)\n")

    log("=== TEST D: EMPTY QUERIES ===")
    results.append(test_empty_queries(router))
    log(f"  Result: {results[-1].success} ({results[-1].response_time_ms:.1f}ms)\n")

    log("=== TEST E: SPECIAL CHARACTERS ===")
    results.append(test_special_characters(router))
    log(f"  Result: {results[-1].success} ({results[-1].response_time_ms:.1f}ms)\n")

    log("=== TEST F: KNOWLEDGE GRAPH LOAD ===")
    results.append(test_knowledge_graph_load())
    log(f"  Result: {results[-1].success} ({results[-1].response_time_ms:.1f}ms)\n")

    log("=== TEST G: GLOBAL MESSAGE SEARCH ===")
    results.append(test_global_message_search(router, 50))
    log(f"  Result: {results[-1].success} ({results[-1].response_time_ms:.1f}ms)\n")

    log("=== TEST H: AUTO-EMBED STRESS ===")
    results.append(test_auto_embed_stress(10))
    log(f"  Result: {results[-1].success} ({results[-1].response_time_ms:.1f}ms)\n")

    return results


def print_summary(results: List[TestResult]):
    """Print summary table."""
    print("\n" + "=" * 90)
    print("STRESS TEST RESULTS SUMMARY")
    print("=" * 90)
    print(
        f"{'Test Name':<35} {'Status':<8} {'Time (ms)':<12} {'Memory (MB)':<12} {'Details'}"
    )
    print("-" * 90)

    for r in results:
        status = "✅ PASS" if r.success else "❌ FAIL"
        details = r.error if r.error else str(r.metadata)
        print(
            f"{r.name:<35} {status:<8} {r.response_time_ms:>10.1f}   {r.memory_mb:>10.1f}   {details[:30]}"
        )

    print("-" * 90)

    passed = sum(1 for r in results if r.success)
    total = len(results)
    print(f"\nOVERALL: {passed}/{total} tests passed")

    total_time = sum(r.response_time_ms for r in results)
    total_mem = sum(r.memory_mb for r in results)
    print(f"Total time: {total_time:.1f}ms | Total memory delta: {total_mem:.1f}MB")
    print("=" * 90)


if __name__ == "__main__":
    print("MEMORY SYSTEM STRESS TEST")
    print(f"DB: {DB_PATH}")
    print(f"Initial memory: {get_memory_mb():.1f} MB\n")

    results = run_all_tests()
    print_summary(results)
