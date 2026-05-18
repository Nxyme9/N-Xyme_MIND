#!/usr/bin/env python3
"""Embedding service — wraps MiniLM CLI for MCP tool calls."""
import subprocess, json, os, sys, time

MINILM_CLI = os.path.expanduser("~/N-Xyme_CODE/N-Xyme_MIND/target/debug/minilm-cli")

_cache = {}
_cache_hits = 0
_cache_misses = 0

def embed(text: str) -> dict:
    """Get embedding for text. Uses cache for speed."""
    global _cache_hits, _cache_misses
    # Truncate to prevent huge cache keys
    cache_key = text[:200]
    if cache_key in _cache:
        _cache_hits += 1
        return _cache[cache_key]

    start = time.time()
    result = subprocess.run(
        [MINILM_CLI, text],
        capture_output=True, text=True, timeout=30
    )
    elapsed = time.time() - start

    if result.returncode != 0:
        return {"error": result.stderr.strip(), "dim": 0, "latency_ms": int(elapsed * 1000)}

    # Parse output
    lines = result.stdout.strip().split("\n")
    vec = None
    for line in lines:
        if "First 10 values:" in line:
            # Parse the vector data
            vec_str = line.split("First 10 values:")[1].strip().strip("[]...")
            vec = [float(x) for x in vec_str.split(",")]
            break

    if not vec:
        return {"error": "Failed to parse embedding", "dim": 0, "latency_ms": int(elapsed * 1000)}

    _cache[cache_key] = vec
    _cache_misses += 1
    return {"embedding": vec, "dim": len(vec), "latency_ms": int(elapsed * 1000)}

def cosine_similarity(a: list, b: list) -> float:
    dot = sum(x*y for x, y in zip(a, b))
    na = sum(x*x for x in a) ** 0.5
    nb = sum(x*x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0

def cache_stats() -> dict:
    total = _cache_hits + _cache_misses
    return {
        "size": len(_cache),
        "hits": _cache_hits,
        "misses": _cache_misses,
        "hit_rate": round(_cache_hits / total * 100, 1) if total > 0 else 0
    }

if __name__ == "__main__":
    # Test
    e1 = embed("Hello world")
    e2 = embed("test embedding")
    if "embedding" in e1 and "embedding" in e2:
        sim = cosine_similarity(e1["embedding"], e2["embedding"])
        print(f"Embedding dim: {e1['dim']}")
        print(f"Latency: {e1['latency_ms']}ms")
        print(f"Similarity: {sim:.4f}")
        print(f"Cache: {cache_stats()}")
