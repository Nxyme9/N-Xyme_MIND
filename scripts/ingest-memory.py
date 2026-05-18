#!/usr/bin/env python3
"""
ingest-memory.py — GPU-accelerated memory ingestion.
Uses MiniLM via sentence-transformers on RTX 3080 Ti.
Stores 384-dim vectors in data/memory/vectors/<agent>/.

Usage:
  python3 scripts/ingest-memory.py                    # Full ingest
  python3 scripts/ingest-memory.py --quick            # 10 sessions
  python3 scripts/ingest-memory.py --incremental      # New only
"""

import hashlib, json, os, sys, time, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VECTORS_DIR = ROOT / "data" / "memory" / "vectors"
INDEX_FILE = ROOT / "data" / "memory" / "index.json"

SESSION_DIRS = [
    ROOT / "data" / "sessions",
    ROOT / "data" / "transcripts" / "external",
]

BATCH_SIZE = 512  # texts per ONNX batch


def load_embedder():
    """Load ONNX MiniLM model (compiled C++ backend, CPU)."""
    import onnxruntime as ort
    from transformers import AutoTokenizer

    model_path = str(ROOT / "data" / "memory" / "models" / "embedding.onnx")
    session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
    tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
    print(f"  ONNX MiniLM on CPU ({ort.__version__})")
    print(f"  outputs: {[o.name for o in session.get_outputs()]}")
    return session, tokenizer


def embed_batch(session, tokenizer, texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using ONNX MiniLM. Returns list of normalized 384-dim vectors."""
    if not texts:
        return []

    import numpy as np
    inputs = tokenizer(texts, padding=True, truncation=True, max_length=128, return_tensors='np')
    outputs = session.run(None, {
        'input_ids': inputs['input_ids'],
        'attention_mask': inputs['attention_mask']
    })

    # outputs[0] = token embeddings (batch, seq_len, 384)
    # outputs[1] = tanh (unused)
    token_embeds = outputs[0]
    attention_mask = inputs['attention_mask']

    # Mean pooling: average token embeddings, ignoring padding
    mask_expanded = np.expand_dims(attention_mask, axis=-1).astype(token_embeds.dtype)
    sum_embeds = np.sum(token_embeds * mask_expanded, axis=1)
    sum_mask = np.sum(mask_expanded, axis=1)
    pooled = sum_embeds / np.maximum(sum_mask, 1e-9)

    # L2 normalize
    norms = np.linalg.norm(pooled, axis=1, keepdims=True)
    normalized = pooled / np.maximum(norms, 1e-9)

    return [[float(v) for v in vec] for vec in normalized]


def get_processed_ids() -> set:
    if not INDEX_FILE.exists():
        return set()
    try:
        return set(json.loads(INDEX_FILE.read_text()).get("processed", []))
    except: return set()


def save_index(processed_ids: set, total: int):
    INDEX_FILE.write_text(json.dumps({
        "processed": sorted(processed_ids), "total": total,
        "last_updated": time.time(),
        "vector_dim": 384,
        "embedder": "all-MiniLM-L6-v2",
    }, indent=2))


def chunk_session(text: str, max_chars: int = 800) -> list[str]:
    """Split session into overlapping chunks (max_chars each)."""
    if len(text) <= max_chars:
        return [text]
    chunks = []
    lines = text.split("\n")
    current, current_len = [], 0
    for line in lines:
        if current_len + len(line) > max_chars and current:
            chunks.append("\n".join(current))
            current, current_len = [line], len(line)
        else:
            current.append(line)
            current_len += len(line)
    if current:
        chunks.append("\n".join(current))
    return chunks


def extract_agent(text: str) -> str:
    """Guess agent name from session text."""
    agents = ["hephaestus", "sisyphus", "catalyst", "momus", "metis",
              "explorer", "librarian", "kairos", "jarvis"]
    for line in text.split("\n")[:30]:
        l = line.lower()
        for a in agents:
            if a in l:
                return a
    return "unknown"


def process_file(filepath: Path, session, tokenizer, processed: set) -> list[dict]:
    """Process one session file. Returns list of vector entries."""
    sid = filepath.stem
    if sid in processed:
        return []

    try:
        raw = filepath.read_text(encoding="utf-8", errors="replace")
    except: return []

    if len(raw) < 100:
        return []

    chunks = chunk_session(raw)
    agent = extract_agent(raw)

    entries = []
    texts_to_embed = [c[:2000] for c in chunks]
    vectors = embed_batch(session, tokenizer, texts_to_embed)

    for i, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
        entries.append({
            "id": f"{sid}-{i}",
            "session_id": sid,
            "agent": agent,
            "content": chunk_text[:500],
            "vector": vector,
            "dim": len(vector),
            "source": str(filepath),
            "chunk": i,
            "timestamp": filepath.stat().st_mtime,
            "type": "session",
            "char_count": len(chunk_text),
        })

    return entries


def store_entries(entries: list[dict]):
    """Batch-store entries into agent-specific vector files."""
    by_agent = {}
    for e in entries:
        agent = e["agent"]
        if agent not in by_agent:
            by_agent[agent] = []
        by_agent[agent].append(e)

    for agent, agent_entries in by_agent.items():
        agent_dir = VECTORS_DIR / agent
        agent_dir.mkdir(parents=True, exist_ok=True)
        out_file = agent_dir / f"batch_{int(time.time())}.jsonl"
        with open(out_file, "w") as f:
            for e in agent_entries:
                f.write(json.dumps(e) + "\n")
        print(f"    stored {len(agent_entries)} → {agent}/", end=" ", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--incremental", action="store_true")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════╗")
    print("║   N-Xyme Memory Ingestion — GPU Batch   ║")
    print("╚══════════════════════════════════════════╝")

    t0 = time.time()

    print("\n[1/4] Loading ONNX MiniLM (compiled C++, CPU)...")
    session, tokenizer = load_embedder()

    print("\n[2/4] Scanning sessions...")
    processed_ids = get_processed_ids() if args.incremental else set()
    all_files = []
    for d in SESSION_DIRS:
        if d.exists():
            all_files.extend(sorted(d.glob("*.jsonl")))
    print(f"  total: {len(all_files)} files ({len(processed_ids)} already processed)")

    if args.quick:
        all_files = all_files[:10]

    print(f"\n[3/4] Ingesting {len(all_files)} sessions...")
    total_entries = 0
    total_files = 0
    batch_entries = []
    filenames_processed = []

    for idx, f in enumerate(all_files):
        entries = process_file(f, session, tokenizer, processed_ids)
        if entries:
            batch_entries.extend(entries)
            filenames_processed.append(f.stem)
            total_files += 1
            total_entries += len(entries)

        # Flush batch
        if len(batch_entries) >= BATCH_SIZE:
            store_entries(batch_entries)
            batch_entries = []

        if (idx + 1) % 500 == 0:
            print(f"\n  ...{idx+1}/{len(all_files)} files ({total_entries} chunks)")

    # Final flush
    if batch_entries:
        store_entries(batch_entries)

    print(f"\n[4/4] Saving index ({total_files} files)...")
    save_index(set(filenames_processed) | processed_ids, total_files)

    elapsed = time.time() - t0
    print(f"\n{'═' * 55}")
    print(f"  ✅ {total_files} sessions → {total_entries} GPU vectors")
    print(f"  ⏱  {elapsed:.1f}s ({total_entries/elapsed:.0f} vecs/sec)")
    print(f"  📁 Vectors in: data/memory/vectors/<agent>/*.jsonl")
    print(f"  🧠 Model: all-MiniLM-L6-v2 ONNX (384-dim) on CPU")
    print(f"{'═' * 55}")

    # Agent breakdown
    print("\nAgent breakdown (new vectors):")
    for agent_dir in sorted(VECTORS_DIR.iterdir()):
        if agent_dir.is_dir():
            count = sum(1 for f in agent_dir.glob("batch_*.jsonl") for _ in open(f))
            if count:
                print(f"  {agent_dir.name}: {count} vectors")


if __name__ == "__main__":
    main()
