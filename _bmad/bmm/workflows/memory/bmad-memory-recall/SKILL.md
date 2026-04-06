---
name: bmad-memory-recall
description: Recall relevant context from unified memory across all sources. Use when the user says "recall context", "what do we know about", "what was discussed about", or "refresh my memory on".
argument-hint: "[topic or query to recall] [--sources opencode|graphiti|memory|all]"
---

# Memory Recall Skill

## Overview

This skill retrieves relevant context from the unified memory system, searching across:
- **opencode.db**: Past session messages and conversations
- **Graphiti**: Knowledge graph with entities and relations
- **Memory MCP**: Cross-session knowledge graph

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

Use the unified_memory_mcp tools to search:

```python
# Import and search
from src.unified_memory_mcp import search_opencode, search_graphiti

# Search opencode.db for relevant messages
opencode_results = search_opencode(query, limit=10)

# Search Graphiti for related entities
graphiti_results = search_graphiti(query, limit=10)

# Also query memory MCP for cross-session context
# Use memory_search_nodes tool
```

### Stage 2: Rank Results

Score each result by:
- **Relevance**: How closely it matches the query
- **Recency**: Newer sessions are generally more relevant
- **Source quality**: Direct messages > inferred relations

### Stage 3: Synthesize

Combine the top results into a coherent summary:

```markdown
## Memory Recall: {query}

### From OpenCode Sessions
{top 3-5 message excerpts}

### From Knowledge Graph
{relevant entities and relations}

### Cross-Session Context
{key insights from memory MCP}

---
Sources: {list of sources used}
Results: {total found}
```

## Output Format

Always return structured JSON:

```json
{
  "status": "success",
  "query": "{search query}",
  "results": {
    "opencode": [{...}],
    "graphiti": [{...}],
    "memory": [{...}]
  },
  "summary": "{synthesized context}",
  "sources_used": ["opencode", "graphiti", "memory"],
  "total_results": {count}
}
```

## Error Handling

If memory sources are unavailable:
- Log warning but continue with available sources
- Report partial results if any sources fail
- Never fabricate context — say "no relevant memories found"