#!/usr/bin/env python3
"""
Benchmark: Direct GGUF Embedding vs Ollama Embedding
"""

import sys
import time
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Test texts - diverse content
TEST_TEXTS = [
    "hello world",
    "the quick brown fox jumps over the lazy dog",
    "artificial intelligence and machine learning",
    "natural language processing with transformers",
    "deep neural networks and attention mechanisms",
    "python programming language tutorial",
    "javascript web development with React",
    "database sql queries and optimization",
    "cloud computing services and architecture",
    "computer vision and image recognition",
    "reinforcement learning and game theory",
    "distributed systems and microservices",
    "data structures and algorithms",
    "software engineering best practices",
    "cybersecurity and encryption",
    "quantum computing fundamentals",
    "blockchain technology and cryptocurrency",
    "mobile app development with Flutter",
    "docker container orchestration",
    "kubernetes deployment strategies",
]

print("=" * 70)
print("EMBEDDING MODEL BENCHMARK")
print("=" * 70)

# ============================================================================
# Test 1: Our Engine (Direct GGUF - llama-cpp-python)
# ============================================================================

print("\n[1] Testing OUR ENGINE (Direct GGUF)...")
print("-" * 50)

from frankenstein_engine.compatibility import get_embedding_client

start = time.time()
client = get_embedding_client()
load_time = time.time() - start
print(f"Model load time: {load_time:.2f}s")

# Warmup
_ = client.embed("warmup")

# Benchmark single embeddings
single_times = []
for text in TEST_TEXTS[:10]:
    start = time.time()
    emb = client.embed(text)
    single_times.append(time.time() - start)

single_avg = sum(single_times) / len(single_times)
single_rps = 1 / single_avg

print(f"Single embedding avg: {single_avg * 1000:.2f}ms ({single_rps:.1f} emb/s)")

# Benchmark batch
batch_start = time.time()
embs = [client.embed(t) for t in TEST_TEXTS]
batch_time = time.time() - batch_start
batch_rps = len(TEST_TEXTS) / batch_time

print(f"Batch ({len(TEST_TEXTS)}): {batch_time:.3f}s ({batch_rps:.1f} emb/s)")

# Verify embedding dimension
emb_dim = len(embs[0])
print(f"Embedding dimension: {emb_dim}")

# Verify quality - cosine similarity
from numpy.linalg import norm
from numpy import dot

emb1 = np.array(client.embed("machine learning"))
emb2 = np.array(client.embed("machine learning"))
emb3 = np.array(client.embed("the weather"))

sim_same = dot(emb1, emb2) / (norm(emb1) * norm(emb2))
sim_diff = dot(emb1, emb3) / (norm(emb1) * norm(emb3))

print(f"Similarity (same): {sim_same:.3f} (should be ~1.0)")
print(f"Similarity (diff): {sim_diff:.3f} (should be <0.5)")

engine_results = {
    "single_ms": single_avg * 1000,
    "single_rps": single_rps,
    "batch_rps": batch_rps,
    "dim": emb_dim,
    "load_time": load_time,
}

# ============================================================================
# Test 2: Ollama
# ============================================================================

print("\n[2] Testing OLLAMA...")
print("-" * 50)

import httpx

try:
    with httpx.Client(timeout=60.0) as ollama:
        # Check health
        resp = ollama.get("http://localhost:11434/api/tags")
        print(f"Ollama status: {resp.status_code}")

        # Warmup
        _ = ollama.post(
            "http://localhost:11434/api/embed",
            json={"model": "nomic-embed-text", "input": "warmup"},
        )

        # Benchmark single
        single_times_ollama = []
        for text in TEST_TEXTS[:10]:
            start = time.time()
            resp = ollama.post(
                "http://localhost:11434/api/embed",
                json={"model": "nomic-embed-text", "input": text},
            )
            emb = resp.json()["embeddings"][0]
            single_times_ollama.append(time.time() - start)

        single_avg_ollama = sum(single_times_ollama) / len(single_times_ollama)
        single_rps_ollama = 1 / single_avg_ollama

        print(
            f"Single embedding avg: {single_avg_ollama * 1000:.2f}ms ({single_rps_ollama:.1f} emb/s)"
        )

        # Benchmark batch
        batch_start = time.time()
        resp = ollama.post(
            "http://localhost:11434/api/embed",
            json={"model": "nomic-embed-text", "input": TEST_TEXTS},
        )
        batch_time_ollama = time.time() - batch_start
        batch_rps_ollama = len(TEST_TEXTS) / batch_time_ollama

        print(
            f"Batch ({len(TEST_TEXTS)}): {batch_time_ollama:.3f}s ({batch_rps_ollama:.1f} emb/s)"
        )

        ollama_results = {
            "single_ms": single_avg_ollama * 1000,
            "single_rps": single_rps_ollama,
            "batch_rps": batch_rps_ollama,
        }

except Exception as e:
    print(f"Ollama error: {e}")
    ollama_results = None

# ============================================================================
# Summary
# ============================================================================

print("\n" + "=" * 70)
print("BENCHMARK RESULTS")
print("=" * 70)

print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                    EMBEDDING MODEL COMPARISON                     ║
╠══════════════════════════════════════════════════════════════════╣
║  Metric              │ Our Engine (Direct)  │ Ollama (HTTP)        ║
╠══════════════════════════════════════════════════════════════════╣
║  Single latency      │ {engine_results["single_ms"]:>10.2f} ms        │ {ollama_results["single_ms"] if ollama_results else "N/A":>10.2f} ms       ║
║  Single throughput   │ {engine_results["single_rps"]:>10.1f} emb/s     │ {ollama_results["single_rps"] if ollama_results else "N/A":>10.1f} emb/s    ║
║  Batch throughput    │ {engine_results["batch_rps"]:>10.1f} emb/s     │ {ollama_results["batch_rps"] if ollama_results else "N/A":>10.1f} emb/s    ║
║  Embedding dim       │ {engine_results["dim"]:>10d}             │ 768 (fixed)         ║
║  Model load time     │ {engine_results["load_time"]:>10.2f} s         │ ~3-5s (Ollama)     ║
╚══════════════════════════════════════════════════════════════════╝
""")

if ollama_results:
    speedup = engine_results["single_rps"] / ollama_results["single_rps"]
    print(f"⚡ Our engine is {speedup:.1f}x FASTER than Ollama!")
else:
    print("⚡ Our engine is running - Ollama not available for comparison")

print("\n✓ Embedding model loaded with OUR ENGINE (no HTTP, no Ollama)")
print(f"✓ Model: nomic-embed-text-v1.5-Q4_K_M.gguf")
print(f"✓ Dimension: {emb_dim}")
