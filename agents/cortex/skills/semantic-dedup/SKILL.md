---
name: semantic-dedup
description: "Semantic Dedup — near-duplicate detection using cosine similarity > 0.95, keeps highest-quality version."
---

# Semantic Dedup

## Purpose
Detect and resolve near-duplicate memory entries using embedding similarity analysis. Keep the highest-quality version, mark duplicates as references.

## Detection Pipeline

### 1. INDEX
- List all memory entries in target scope: `search_memory()` or `list_memory()`
- Group by type (conversation, code, error, decision)
- For entries > 1000, sample in batches of 500

### 2. EMBED BATCH
- For each entry, ensure embedding exists (compute if missing)
- Compare in batches: 50 entries at a time to avoid overloading

### 3. SIMILARITY COMPARE
For each entry pair (A, B):
- Compute `cosine_sim = embed_similarity(A.vector, B.vector)`
- Thresholds:
  - **> 0.98** — Exact duplicate (identical content, possibly from different sessions)
  - **0.95 - 0.98** — Near-duplicate (same content, different framing)
  - **0.90 - 0.95** — Similar topic (different content, same subject)
  - **< 0.90** — Unique (keep both)

### 4. QUALITY SCORE
For each duplicate group, compute quality score:
| Factor | Weight | How to measure |
|--------|--------|----------------|
| Content length | 2x | Longer = more complete |
| Decision content | 10x | Contains decision keywords |
| Error content | 3x | Contains error info |
| Code content | 5x | Has code blocks |
| Recency | 2x | More recent = higher quality |
| Tool call detail | 1x | Has tool call traces |
| Completeness | 2x | Full vs truncated content |

Score = sum of (factor × weight)

### 5. DEDUP RESOLUTION
For duplicates (>0.95):
- Keep entry with highest quality score
- Mark duplicate entries as `status:duplicate_of:<kept_id>`
- Store reference chain: `dedup_chain: [A_id, B_id, C_id] → kept: A_id`
- DO NOT delete duplicates — just mark them

For exact duplicates (>0.98):
- If content is identical (byte-for-byte comparison confirms)
- Keep the one with more complete metadata (tags, dates)
- Update reference chain

### 6. CROSS-SOURCE DEDUP
- ChatGPT sessions commonly have duplicate conversations
- Same deepseek session may appear in multiple formats
- Cross-reference by content hash (SHA256 of first 500 chars)
- Group by content hash first, then by semantic similarity

## Reporting
```
Dedup Report:
  Total entries scanned: 12500
  Exact duplicates: 340 (2.7%)
  Near duplicates: 890 (7.1%)
  Similar topic: 2100 (16.8%)
  Unique: 9170 (73.4%)
  
  Kept (highest quality): 1230
  Marked as duplicates: 1230
  Storage saved (est): 340 MB
```

## NEVER
- Delete entries — always mark as duplicate with reference
- Dedup across different types (code vs conversation are never dupes)
- Auto-dedup without confirmation for importance > 7 entries
- Process more than 5000 entries in one batch (memory limits)

## ALWAYS
- Compute quality score before removing anything
- Maintain reference chain: `duplicate_of:<kept_id>`
- Report stats: found vs kept vs marked
- Verify by spot-checking 5% of matched pairs
