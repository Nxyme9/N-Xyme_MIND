#!/usr/bin/env python3
"""
ingest_sessions.py — Read ALL .jsonl files under data/sessions/,
extract meaningful content, deduplicate, embed, and store as 384-dim
vectors in data/memory/vectors/sessions.jsonl.

Uses ONNX model directly for bulk embedding (bypasses bridge daemon
for throughput). Bridge daemon is used for search queries only.

Usage:
  python3 ingest_sessions.py
  python3 ingest_sessions.py --limit 1000  (limit chunks for testing)
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

PROJECT_ROOT = os.environ.get(
    "NX_PROJECT_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)
SESSIONS_DIR = os.path.join(PROJECT_ROOT, "data", "sessions")
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "data", "memory", "vectors", "sessions.jsonl")
ONNX_MODEL_PATH = os.path.join(PROJECT_ROOT, "data", "memory", "models", "embedding.onnx")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EXPECTED_DIM = 384
BATCH_SIZE = 256  # Embed this many texts at once for throughput


def get_agent_from_path(rel_path: str) -> str:
    """Extract agent name from session file's relative path (relative to data/sessions/)."""
    parts = rel_path.replace("\\", "/").split("/")
    if not parts:
        return "unknown"

    # Root-level file: chatgpt_xxx.jsonl or ses_xxx.jsonl
    if len(parts) == 1:
        fname = parts[0]
        if fname.startswith("chatgpt_"):
            return "chatgpt"
        if fname.startswith("deepseek_"):
            return "deepseek"
        if fname.startswith("ses_"):
            return "opencode"
        return "unknown"

    # Subdirectory: sisyphus/2026-05-16/file.jsonl or hephaestus/file.jsonl
    candidate = parts[0]
    known = {
        "hephaestus", "sisyphus", "unknown", "digests", "opencode",
        "deepseek", "chatgpt",
    }
    if candidate in known:
        return candidate
    return candidate  # Use directory name as agent


def get_date_from_path(rel_path: str) -> str:
    """Extract date from path if present."""
    parts = rel_path.replace("\\", "/").split("/")
    for p in parts:
        if p.count("-") == 2 and len(p) == 10 and p[0].isdigit():
            return p
    return ""


def extract_content(entry: dict) -> str | None:
    """
    Extract meaningful text content from a session JSON line.
    Returns a string or None if the entry carries no meaningful content.
    """
    # Explicit text/content fields
    for field in ("text", "content", "message", "query", "description"):
        if field in entry and isinstance(entry[field], str) and len(entry[field].strip()) > 3:
            val = entry[field].strip()
            prefix = entry.get("type", "")
            return f"{prefix}: {val}" if prefix else val

    tool = entry.get("tool", "")
    params = entry.get("params", {})
    result = entry.get("result", {})

    parts = []
    if tool:
        parts.append(f"tool:{tool}")

    if isinstance(params, dict):
        for k, v in params.items():
            if k in ("session_id", "_agent", "key") or v is None:
                continue
            if isinstance(v, (str, int, float, bool)) and len(str(v)) > 2:
                parts.append(f"{k}:{v}")
            elif isinstance(v, dict):
                sub = json.dumps(v, sort_keys=True)
                if len(sub) < 200:
                    parts.append(f"{k}:{sub}")

    if isinstance(result, dict):
        for k in ("status", "message", "error", "decision", "reason", "selected", "route"):
            if k in result and isinstance(result[k], str) and len(result[k]) > 2:
                parts.append(f"{k}:{result[k]}")
        if "route" in result:
            parts.append(f"routed:{result['route']}")
        if "best_tool" in result:
            parts.append(f"best_tool:{result['best_tool']}")

    if not parts:
        serialized = json.dumps(entry, sort_keys=True, default=str)
        if len(serialized) < 500:
            return serialized
        return None

    return " | ".join(parts)


def content_hash(text: str) -> str:
    """SHA-256 hash of content for deduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def find_all_session_files() -> list[tuple[str, str]]:
    """Walk data/sessions/ for .jsonl files. Returns [(abs_path, rel_path)]."""
    files = []
    base = Path(SESSIONS_DIR)
    if not base.exists():
        print(f"ERROR: Sessions directory not found: {SESSIONS_DIR}", file=sys.stderr)
        return files

    for path in sorted(base.rglob("*.jsonl")):
        if path.is_file():
            rel = str(path.relative_to(base))
            files.append((str(path), rel))

    print(f"Found {len(files)} session files under {SESSIONS_DIR}", file=sys.stderr)
    return files


def read_session_file(filepath: str) -> list[dict]:
    """Read all valid JSON lines from a session file."""
    entries = []
    try:
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if isinstance(entry, dict):
                        entries.append(entry)
                except json.JSONDecodeError:
                    pass  # silently skip malformed lines
    except Exception:
        pass
    return entries


def load_onnx_embedder():
    """Load ONNX model and tokenizer; return a batch embedding function."""
    if not os.path.exists(ONNX_MODEL_PATH):
        raise FileNotFoundError(
            f"ONNX model not found at {ONNX_MODEL_PATH}. "
            f"Set NX_PROJECT_ROOT or check path."
        )
    print(f"  Loading ONNX model from {ONNX_MODEL_PATH}...", file=sys.stderr)
    session = ort.InferenceSession(ONNX_MODEL_PATH)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    def embed_batch(texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, return list of normalized 384-dim vectors."""
        tokens = tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="np",
            max_length=128,
        )
        inputs = {inp.name: tokens[inp.name] for inp in session.get_inputs()}
        outputs = session.run(None, inputs)
        # all-MiniLM-L6-v2 ONNX: output[1] is pooled embedding
        embeddings = outputs[1] if len(outputs) > 1 else outputs[0]
        # L2 normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / (norms + 1e-12)
        return embeddings.tolist()

    # Warm up
    _ = embed_batch(["warmup"])
    print(f"  Model loaded, expected dim: {EXPECTED_DIM}", file=sys.stderr)
    return embed_batch


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Holographic memory ingestion")
    parser.add_argument("--limit", type=int, default=0, help="Limit chunks for testing")
    args = parser.parse_args()

    print("=" * 60, file=sys.stderr)
    print("HOLOGRAPHIC MEMORY INGESTION PIPELINE", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"  Sessions dir: {SESSIONS_DIR}", file=sys.stderr)
    print(f"  Output:       {OUTPUT_FILE}", file=sys.stderr)
    print(f"  Model:        {ONNX_MODEL_PATH}", file=sys.stderr)
    print(file=sys.stderr)

    # Step 1: Find all session files
    print("[1/5] Scanning session files...", file=sys.stderr)
    session_files = find_all_session_files()
    if not session_files:
        print("No session files found.", file=sys.stderr)
        return

    # Step 2: Extract content
    print("[2/5] Extracting content with dedup...", file=sys.stderr)
    seen_hashes: set[str] = set()
    chunks: list[dict] = []
    duplicates_skipped = 0
    t0 = time.time()

    for filepath, relpath in session_files:
        entries = read_session_file(filepath)
        if not entries:
            continue

        agent = get_agent_from_path(relpath)
        date = get_date_from_path(relpath)
        filename = os.path.basename(filepath)

        for entry in entries:
            content = extract_content(entry)
            if not content:
                continue

            c_hash = content_hash(content)
            if c_hash in seen_hashes:
                duplicates_skipped += 1
                continue
            seen_hashes.add(c_hash)

            ts = entry.get("ts", 0)
            entry_type = entry.get("type", "tool_call")

            chunks.append({
                "content": content,
                "hash": c_hash,
                "session": filename.replace(".jsonl", ""),
                "agent": agent,
                "date": date,
                "type": entry_type,
                "ts": ts,
                "file": relpath,
            })

            if args.limit and len(chunks) >= args.limit:
                break
        if args.limit and len(chunks) >= args.limit:
            break

    elapsed = time.time() - t0
    print(f"  Extracted {len(chunks)} unique chunks, skipped {duplicates_skipped} duplicates "
          f"in {elapsed:.1f}s", file=sys.stderr)

    if not chunks:
        print("No content extracted.", file=sys.stderr)
        return

    # Step 3: Load ONNX model for batch embedding
    print("[3/5] Loading ONNX embedder...", file=sys.stderr)
    try:
        embed_batch = load_onnx_embedder()
    except FileNotFoundError as e:
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(1)

    # Step 4: Embed all chunks in batches
    print(f"[4/5] Embedding {len(chunks)} chunks in batches of {BATCH_SIZE}...", file=sys.stderr)
    t0 = time.time()
    texts = [c["content"] for c in chunks]
    vectors: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        batch_vecs = embed_batch(batch)
        vectors.extend(batch_vecs)
        pct = min(100, int((i + len(batch)) / len(texts) * 100))
        if (i // BATCH_SIZE) % 4 == 0:  # Progress every 4th batch
            elapsed_so_far = time.time() - t0
            rate = (i + len(batch)) / max(elapsed_so_far, 0.01)
            eta = (len(texts) - (i + len(batch))) / max(rate, 1)
            print(f"    {pct}% | {i + len(batch)}/{len(texts)} chunks | "
                  f"{rate:.0f} chunks/s | ETA {eta:.0f}s", file=sys.stderr, end="\r")

    embedding_elapsed = time.time() - t0
    rate = len(texts) / max(embedding_elapsed, 0.01)
    print(f"\n    Embedded {len(vectors)} chunks in {embedding_elapsed:.1f}s "
          f"({rate:.0f} chunks/s)", file=sys.stderr)

    assert len(vectors) == len(chunks), f"Vector count mismatch: {len(vectors)} vs {len(chunks)}"
    assert len(vectors[0]) == EXPECTED_DIM, f"Expected {EXPECTED_DIM}-dim, got {len(vectors[0])}"

    # Step 5: Write output
    print(f"[5/5] Writing results to {OUTPUT_FILE}...", file=sys.stderr)
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "w") as out:
        for chunk, vector in zip(chunks, vectors):
            record = {
                "content": chunk["content"],
                "vector": vector,
                "dim": EXPECTED_DIM,
                "id": f"{chunk['session']}_{chunk['ts']}_{chunk['hash'][:8]}",
                "session": chunk["session"],
                "agent": chunk["agent"],
                "date": chunk["date"],
                "type": chunk["type"],
                "ts": chunk["ts"],
            }
            out.write(json.dumps(record) + "\n")

    total_elapsed = time.time() - t0 + elapsed  # rough total
    print(file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("INGESTION COMPLETE", file=sys.stderr)
    print(f"  Files scanned:     {len(session_files)}", file=sys.stderr)
    print(f"  Chunks extracted:  {len(chunks)}", file=sys.stderr)
    print(f"  Duplicates skipped:{duplicates_skipped}", file=sys.stderr)
    print(f"  Vectors stored:    {len(vectors)}", file=sys.stderr)
    print(f"  Vector dimension:  {EXPECTED_DIM}", file=sys.stderr)
    print(f"  Output:            {OUTPUT_FILE}", file=sys.stderr)
    print(f"  Total time:        {total_elapsed:.1f}s", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    return len(vectors)


if __name__ == "__main__":
    main()
