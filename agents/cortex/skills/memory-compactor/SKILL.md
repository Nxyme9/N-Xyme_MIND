---
name: memory-compactor
description: "Memory Compactor — clusters similar vectors, generates summaries, replaces with centroid embeddings."
---

# Memory Compactor

## Purpose
Reduce memory footprint by clustering similar vectors, generating concise summaries, and storing centroid embeddings. Never lose raw data — compacted entries reference the originals.

## Compaction Pipeline

### 1. SELECTION
Choose entries eligible for compaction:
- Importance < 20 (normal, low, noise buckets)
- Age > 30 days (established history)
- No decision tags (decisions are always kept full)
- Similarity clusters (entries that can be merged)

### 2. CLUSTERING
Use embedding similarity to form clusters:
- **Method**: Agglomerative clustering on cosine distance
- **Threshold**: Merge clusters when centroid cosine sim > 0.85
- **Min cluster size**: 3 entries (fewer than 3 = keep individual)
- **Max cluster size**: 20 entries (larger clusters sub-divide)
- **Distance metric**: `1 - cosine_similarity(a, b)`

### 3. CENTROID COMPUTATION
For each cluster:
- Compute centroid vector = mean of all member vectors
- This is a 384-dim average (works for MiniLM embeddings)
- Store as `embedding_centroid` in the compacted entry

### 4. SUMMARY GENERATION
For each cluster, generate a summary:
- **Extractive**: Pick 2-3 most representative entries (closest to centroid)
- **Abstractive**: Generate a 2-3 sentence summary of the cluster's content
  - "What this group is about"
  - "Key information preserved"
  - "Date range covered"
- Keep all unique tags from member entries (deduplicated)
- Merge dates to range: `date:2026-03..2026-05`

### 5. COMPACTED ENTRY FORMAT
```json
{
  "id": "compacted_<hash>",
  "type": "compacted",
  "summary": "3 sessions about MCP server configuration. Key decisions: use bash-mcp for shell, deno for TypeScript MCPs. Error patterns: module resolution failures.",
  "centroid": [0.123, -0.456, ...],
  "member_count": 12,
  "members": ["mem_abc123", "mem_def456", ...],
  "date_range": "2026-03..2026-05",
  "tags": ["agent:Sisyphus", "agent:Hephaestus", "topic:mcp", "topic:config", "type:compacted"],
  "importance": 15,
  "original_total_size_bytes": 128000,
  "compacted_size_bytes": 2400,
  "compression_ratio": "53x"
}
```

### 6. REPLACEMENT
- Write compacted entry to `data/memory/consolidated/`
- Mark all member entries as `status:compacted_into:<compacted_id>`
- DO NOT delete member entries — they remain readable but deprioritized
- Update search index to include centroid embedding

### 7. COMPRESSION TRACKING
Track over time:
```
Compaction Cycle 3:
  Clusters formed: 45
  Entries compacted: 520
  Storage before: 64 MB
  Storage after: 1.2 MB (compacted entries)
  Compression: 53x
  Search accuracy impact: -2% recall (acceptable)
```

## Cluster Quality Check
Before finalizing a cluster:
- All members are within 0.15 cosine distance of centroid
- No contradictory content in cluster (decision vs opposite decision)
- Summary captures 80%+ of unique information
- If quality < threshold, split cluster

## NEVER
- Compact importance > 20 entries
- Compact decisions (always preserved full)
- Delete original entries (always keep as readable)
- Create clusters with contradictory content
- Compact entries < 30 days old

## ALWAYS
- Compute and verify centroid quality
- Track compression ratio
- Maintain reference chain back to originals
- Report search accuracy impact
