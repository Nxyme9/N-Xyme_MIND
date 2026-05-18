#!/usr/bin/env python3
"""
Memory Search — TF-IDF search over ingested vectors and synapses.

Usage:
    python3 scripts/memory-search.py "query terms" [--top-k 5]
"""

import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

BASE_DIR = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
VECTORS_FILE = BASE_DIR / "data" / "memory" / "vectors" / "ingest.jsonl"
SYNAPSES_DIR = BASE_DIR / "data" / "memory" / "synapses"


def tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumeric, drop short tokens."""
    tokens = []
    for word in text.lower().split():
        cleaned = "".join(c for c in word if c.isalnum())
        if len(cleaned) >= 2:
            tokens.append(cleaned)
    return tokens


def load_vectors(path: Path) -> list[dict]:
    """Load vector entries from JSONL file."""
    docs = []
    if not path.exists():
        return docs
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                text = entry.get("content", "") or entry.get("text", "")
                if text:
                    docs.append({"id": entry.get("id", ""), "text": text, "source": "vectors"})
            except json.JSONDecodeError:
                continue
    return docs


def load_synapses(directory: Path) -> list[dict]:
    """Load synapse entries from all JSONL files in directory."""
    docs = []
    if not directory.exists():
        return docs
    for jsonl_file in sorted(directory.glob("*.jsonl")):
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    parts = []
                    for key in ("slug", "session_id", "type", "tool_name", "tool_input", "tool_output", "text", "content"):
                        val = entry.get(key, "")
                        if isinstance(val, dict):
                            parts.append(json.dumps(val))
                        elif isinstance(val, str) and val:
                            parts.append(val)
                    text = " ".join(parts)
                    if text:
                        docs.append({
                            "id": entry.get("session_id", entry.get("id", jsonl_file.stem)),
                            "text": text,
                            "source": f"synapses/{jsonl_file.name}",
                        })
                except json.JSONDecodeError:
                    continue
    return docs


def build_tfidf(documents: list[dict]):
    """Build TF-IDF index from documents. Returns (doc_vectors, idf, doc_tokens)."""
    doc_tokens = [tokenize(d["text"]) for d in documents]

    df = Counter()
    for tokens in doc_tokens:
        for token in set(tokens):
            df[token] += 1

    n_docs = len(documents)
    idf = {}
    for term, freq in df.items():
        idf[term] = math.log((n_docs + 1) / (freq + 1)) + 1

    doc_vectors = []
    for tokens in doc_tokens:
        tf = Counter(tokens)
        vec = {}
        for term, count in tf.items():
            tf_val = count / max(len(tokens), 1)
            vec[term] = tf_val * idf.get(term, 0)
        doc_vectors.append(vec)

    return doc_vectors, idf, doc_tokens


def cosine_similarity(vec_a: dict, vec_b: dict) -> float:
    """Compute cosine similarity between two sparse vectors."""
    common_keys = set(vec_a.keys()) & set(vec_b.keys())
    if not common_keys:
        return 0.0
    dot = sum(vec_a[k] * vec_b[k] for k in common_keys)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def search(query: str, top_k: int = 5) -> list[dict]:
    """Search memory with TF-IDF, return top-k results."""
    vectors = load_vectors(VECTORS_FILE)
    synapses = load_synapses(SYNAPSES_DIR)
    documents = vectors + synapses

    if not documents:
        return []

    doc_vectors, idf, doc_tokens = build_tfidf(documents)

    q_tokens = tokenize(query)
    q_tf = Counter(q_tokens)
    q_vec = {}
    for term, count in q_tf.items():
        tf_val = count / max(len(q_tokens), 1)
        q_vec[term] = tf_val * idf.get(term, 0)

    scored = []
    for i, doc_vec in enumerate(doc_vectors):
        score = cosine_similarity(q_vec, doc_vec)
        if score > 0:
            scored.append((score, documents[i]))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, doc in scored[:top_k]:
        text = doc["text"]
        display_text = text[:300] + "..." if len(text) > 300 else text
        results.append({
            "score": round(score, 4),
            "id": doc["id"],
            "source": doc["source"],
            "text": display_text,
        })

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/memory-search.py \"query\" [--top-k N]", file=sys.stderr)
        sys.exit(1)

    query = sys.argv[1]
    top_k = 5

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--top-k" and i + 1 < len(args):
            top_k = int(args[i + 1])
            i += 2
        else:
            i += 1

    results = search(query, top_k)

    output = {
        "query": query,
        "total_results": len(results),
        "results": results,
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
