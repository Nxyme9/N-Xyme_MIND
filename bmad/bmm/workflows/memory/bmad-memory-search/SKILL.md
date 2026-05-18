---
name: bmad-memory-search
description: Search across all memory sources for specific information. Use when the user says "search memories", "find in memory", "search for", or "look up in memory".
argument-hint: "[search query] [--limit N] [--sources vectors|holographic|consciousness|all]"
---

# Memory Search Skill

## Overview

This skill performs deep searches across all N-Xyme memory sources to find specific information. Unlike recall (which brings contextual summaries), search returns specific matches.

## On Activation

1. **Parse the search request:**
   - Extract the exact search query
   - Determine result limit (default: 10)
   - Determine which sources to search: vectors, holographic, consciousness
   
2. **Route** — proceed to Stage 1.

## Stages

| # | Stage | Purpose |
|---|-------|---------|
| 1 | Search All Sources | Query each memory system |
| 2 | Deduplicate | Remove duplicate results |
| 3 | Rank | Sort by relevance |
| 4 | Present | Format for user |

### Stage 1: Search All Sources

Execute searches using available MCP tools:

```python
# Semantic search over 156K session vectors (ONNX embedding)
search_memory(query="your search topic", k=10, min_score=-1.0)

# Aggregate all 3 sources in one call
pull_global_context(query="your search topic", sources=["vectors", "holographic", "consciousness"], top_k=10, min_score=0.0)

# For known IDs
read_memory(memoryId="mem_1234567890")

# Browse by category
list_memory(category="architecture")
```

## Output Format

```json
{
  "status": "success",
  "query": "{search query}",
  "results": [
    {
      "source": "vectors|holographic|consciousness",
      "content": "{result content}",
      "timestamp": "{ISO timestamp}",
      "relevance": 0.95
    }
  ],
  "total_results": {count},
  "deduplicated": {count}
}
```

## Error Handling

- If a source fails: log warning, continue with available sources
- No results from any source: return empty results, not fabricated content
- Rate limiting: back off and retry once if rate limited