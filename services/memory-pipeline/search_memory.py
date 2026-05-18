#!/usr/bin/env python3
"""
search_memory.py — Semantic search over embedded session vectors.

Loads sessions.jsonl, embeds query via ONNX model, computes cosine
similarity against all stored vectors, returns top-K results.

Usage:
  python3 search_memory.py "what did we do about auth" --top 5
  python3 search_memory.py "mojo router" --top 10
  python3 search_memory.py "decisions about embedding" --top 3 --min-score 0.3
"""

import argparse
import json
import os
import sys
import time

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

PROJECT_ROOT = os.environ.get(
    "NX_PROJECT_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)
VECTORS_FILE = os.path.join(PROJECT_ROOT, "data", "memory", "vectors", "sessions.jsonl")
ONNX_MODEL_PATH = os.path.join(PROJECT_ROOT, "data", "memory", "models", "embedding.onnx")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Lazy-loaded ONNX session + tokenizer
_session = None
_tokenizer = None


def _get_embedder():
    """Lazy-load ONNX model and tokenizer."""
    global _session, _tokenizer
    if _session is None:
        if not os.path.exists(ONNX_MODEL_PATH):
            print(f"ERROR: ONNX model not found at {ONNX_MODEL_PATH}", file=sys.stderr)
            sys.exit(1)
        _session = ort.InferenceSession(ONNX_MODEL_PATH)
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    return _session, _tokenizer


def embed(text: str) -> np.ndarray:
    """Embed a single text query, return normalized 384-dim vector."""
    session, tokenizer = _get_embedder()
    tokens = tokenizer(
        text,
        padding=True,
        truncation=True,
        return_tensors="np",
        max_length=128,
    )
    inputs = {inp.name: tokens[inp.name] for inp in session.get_inputs()}
    outputs = session.run(None, inputs)
    embedding = outputs[1] if len(outputs) > 1 else outputs[0]
    norm = np.linalg.norm(embedding, axis=1, keepdims=True)
    embedding = embedding / (norm + 1e-12)
    return embedding[0]


def load_vectors(filepath: str) -> list[dict]:
    """Load all embedded records from sessions.jsonl."""
    if not os.path.exists(filepath):
        print(f"ERROR: Vector file not found at {filepath}", file=sys.stderr)
        print("Run ingest_sessions.py first to generate it.", file=sys.stderr)
        sys.exit(1)

    records = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    dot = float(np.dot(a, b))
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def search(
    records: list[dict],
    query_vec: np.ndarray,
    top_k: int = 5,
    min_score: float = -1.0,
) -> list[dict]:
    """Search all records by cosine similarity, return sorted top-K."""
    results = []
    for rec in records:
        stored_vec = np.array(rec["vector"], dtype=np.float64)
        score = cosine_similarity(query_vec, stored_vec)
        if score >= min_score:
            results.append({"record": rec, "score": round(score, 6)})

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def format_result(r: dict, index: int) -> str:
    """Format a single search result for display."""
    rec = r["record"]
    score = r["score"]
    content = rec.get("content", "—")
    if len(content) > 150:
        content = content[:147] + "..."

    lines = [
        f"  [{index}] Score: {score:.6f}",
        f"       Agent: {rec.get('agent', '?')}  |  Session: {rec.get('session', '?')}",
        f"       Date: {rec.get('date', '?')}  |  Type: {rec.get('type', '?')}",
        f"       Content: {content}",
    ]
    rid = rec.get("id", "")
    if rid:
        lines.append(f"       ID: {rid}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Semantic search over embedded session memory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 search_memory.py "what did we do about auth"
  python3 search_memory.py "mojo router" --top 10
  python3 search_memory.py "embedding decisions" --top 3
        """,
    )
    parser.add_argument("query", type=str, help="Search query text")
    parser.add_argument("--top", type=int, default=5, help="Number of results (default: 5)")
    parser.add_argument("--min-score", type=float, default=-1.0, help="Minimum similarity score threshold")
    parser.add_argument("--file", type=str, default=VECTORS_FILE, help="Vector file path")

    args = parser.parse_args()

    # Load vectors
    print(f"Loading vectors from {args.file}...", file=sys.stderr)
    records = load_vectors(args.file)
    print(f"Loaded {len(records)} vector records", file=sys.stderr)

    if not records:
        print("No vectors found. Run ingest_sessions.py first.", file=sys.stderr)
        sys.exit(1)

    # Verify dimension
    sample_dim = len(records[0].get("vector", []))
    print(f"Vector dimension: {sample_dim}", file=sys.stderr)

    # Embed query
    print(f'Embedding query: "{args.query}"', file=sys.stderr)
    t0 = time.time()
    query_vec = embed(args.query)
    embed_us = int((time.time() - t0) * 1_000_000)
    print(f"Query embed: {embed_us} us | dim: {len(query_vec)}", file=sys.stderr)

    # Search
    print(f"Searching top-{args.top}...", file=sys.stderr)
    t0 = time.time()
    results = search(records, query_vec, top_k=args.top, min_score=args.min_score)
    search_us = int((time.time() - t0) * 1_000_000)
    print(f"Search: {search_us} us for {len(records)} vectors", file=sys.stderr)

    # Print results to stdout
    print(f"\n{'=' * 60}")
    print(f"SEARCH RESULTS: \"{args.query}\"")
    print(f"{'=' * 60}")
    print(f"Found {len(results)} matches (from {len(records)} total vectors)\n")

    if not results:
        print("  No matches found.")
    else:
        for i, r in enumerate(results, 1):
            print(format_result(r, i))
            print()

    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
