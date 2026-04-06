---
name: bmad-memory-search
description: Search across all memory sources for specific information. Use when the user says "search memories", "find in memory", "search for", or "look up in memory".
argument-hint: "[search query] [--limit N] [--sources opencode|graphiti|memory|all]"
---

# Memory Search Skill

## Overview

This skill performs deep searches across all unified memory sources to find specific information. Unlike recall (which brings contextual summaries), search returns specific matches.

## On Activation

1. **Parse the search request:**
   - Extract the exact search query
   - Determine result limit (default: 10)
   - Determine which sources to search
   
2. **Route** — proceed to Stage 1.

## Stages

| # | Stage | Purpose |
|---|-------|---------|
| 1 | Search All Sources | Query each memory system |
| 2 | Deduplicate | Remove duplicate results |
| 3 | Rank | Sort by relevance |
| 4 | Present | Format for user |

### Stage 1: Search All Sources

Execute searches in parallel:

```python
# OpenCode search
from src.unified_memory_mcp import search_opencode
opencode_results = search_opencode(query, limit=limit)

# Graphiti search  
from src.unified_memory_mcp import search_graphiti
graphiti_results = search_graphiti(query, limit=limit)

# Memory MCP search
# Use memory_search_nodes tool
```

### Stage 2: Deduplicate

Remove duplicate results:
- Same content from same session = keep one
- Similar content (>90% similar) = keep best match

### Stage 3: Rank

Sort results by:
1. **Exact match**: Query appears verbatim in result
2. **Keyword match**: Query keywords appear in result  
3. **Recency**: Newer results rank higher
4. **Source authority**: Direct memories > inferred

### Stage 4: Present

Format results clearly:

```markdown
## Memory Search: "{query}"

### OpenCode ({count} results)
- {timestamp}: {excerpt}
- {timestamp}: {excerpt}

### Graphiti ({count} results)
- {entity}: {related info}
- {entity}: {related info}

### Memory MCP ({count} results)
- {entity}: {observations}
```

## Output Format

```json
{
  "status": "success",
  "query": "{search query}",
  "results": [
    {
      "source": "opencode|graphiti|memory",
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