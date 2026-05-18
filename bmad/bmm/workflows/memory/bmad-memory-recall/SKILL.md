---
name: bmad-memory-recall
description: Recall relevant context from unified memory across all sources. Use when the user says "recall context", "what do we know about", "what was discussed about", or "refresh my memory on".
argument-hint: "[topic or query to recall] [--sources vectors|holographic|consciousness|all]"
---

# Memory Recall Skill

## Overview

This skill retrieves relevant context from the N-Xyme memory system, searching across:
- **Session vectors** (`search_memory` tool): 156K+ embedded session vectors via ONNX semantic search
- **Holographic memory** (`read_memory` / `list_memory`): Structured JSON memory entries
- **Pull Global Context** (`pull_global_context` tool): Aggregated context from all 3 memory sources in one call

## On Activation

1. **Parse the recall request:**
   - Extract the topic/query from user input
   - Determine which sources to search (default: all)
   
2. **Route** — proceed to Stage 1.

## Stages

| # | Stage | Purpose |
|---|-------|---------|
| 1 | Query Memory | Search unified memory for relevant context |
| 2 | Rank Results | Prioritize by relevance and recency |
| 3 | Synthesize | Combine into coherent context summary |

### Stage 1: Query Memory

Use the available MCP tools to search across memory systems:

```python
# Semantic search over 156K embedded session vectors
# Uses ONNX embedding model + cosine similarity
# Returns ranked results with score, agent, session, date, type, content
search_memory(query="your search topic", k=5, min_score=-1.0)

# Aggregate context from all 3 memory sources in one call
# Sources: vectors (session vectors), holographic (JSON memory), consciousness (agent outcomes)
pull_global_context(query="your search topic", sources=["vectors", "holographic", "consciousness"], top_k=5, min_score=0.0)

# For known memory IDs, read specific entries
read_memory(memoryId="mem_1234567890")

# List entries by category
list_memory(category="architecture")
```

## Output Format

Always return structured JSON:

```json
{
  "status": "success",
  "query": "{search query}",
  "results": {
    "vectors": [{...}],
    "holographic": [{...}],
    "consciousness": [{...}]
  },
  "summary": "{synthesized context}",
  "sources_used": ["vectors", "holographic", "consciousness"],
  "total_results": {count}
}
```

## Error Handling

If memory sources are unavailable:
- Log warning but continue with available sources
- Report partial results if any sources fail
- Never fabricate context — say "no relevant memories found"