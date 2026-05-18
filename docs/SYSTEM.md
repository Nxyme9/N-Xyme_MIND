# Holographic Memory System

## Architecture

Three-tier memory hierarchy:

```
EPHEMERAL (model context, ~8K tokens)
    ↓ What's relevant RIGHT NOW
SHORT-TERM ← HOLOGRAPHIC VECTOR INDEX (this system)
    ↓ Background migration (planned)
LONG-TERM (dense embeddings, FAISS GPU, 20-40ms)
```

## How It Works

### Ingestion
Every `memory_ingest` call:
1. Text is prefixed with content-type (`code:`, `query:`, `decision:`, `error:`, `summary:`)
2. `dense_embed()` generates a vector — currently TF-IDF (64-dim), auto-upgrades to ONNX (768-dim) when model file appears
3. Vector + metadata appended to `data/memory/vectors/ingest.jsonl` (write-ahead log)
4. In-memory index updated instantly

### Search
Every `memory_search` call:
1. Query embedded with `search_query:` prefix
2. Cosine similarity against all stored vectors: **2-5μs**
3. Recency boost applied: `score = 0.85 × cosine + 0.15 × recency`
4. Top-k results returned with relevance labels (high/medium/low)

### Persistence
- Append-only `.jsonl` file survives restarts
- Loaded at startup (recent 1000 lines)
- Write-ahead log: never overwritten, never corrupted
- Snapshot index (`.idx`) planned for faster cold starts

## Current State

| Metric | Value |
|--------|-------|
| Vector dimension | 64 (TF-IDF sparse) |
| Search latency (100 vecs) | **2-5μs** |
| Cross-process recall | ✅ 107 vectors persisted |
| Storage | 153 bytes/vector |
| Content types | code, query, decision, error, summary |

## Upgrade Path

When a 768-dim ONNX embedding model is placed at `data/memory/models/embedding.onnx`:
1. `dense_embed()` auto-detects it
2. Immediately switches to dense vectors
3. All subsequent ingests use 768-dim
4. Search quality improves — semantic matching instead of keyword
5. No recompilation, no restart needed (new vectors only)

## Benchmarks

| Test | Result |
|------|--------|
| Exact keyword recall | **0.751** score |
| Partial match recall | **0.575** score |
| Ingestion (100 docs) | **96ms total** |
| Search (10 vecs) | **<1ms** |
| Search (100 vecs) | **<1ms** |
| Cold load (1000 vecs) | **<2ms** |

## Commands

```
memory_ingest(session_id, content, content_type)
memory_search(session_id, query, k)
```

## File Locations

```
data/memory/vectors/ingest.jsonl    → write-ahead log (append-only)
data/memory/models/embedding.onnx   → ONNX model (drop-in upgrade)
data/memory/synapses/               → outcomes, decisions, stats
```
