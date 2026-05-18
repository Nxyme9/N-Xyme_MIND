---
name: search-orchestrator
description: "Search Orchestrator — multi-filter search: by agent, date range, type, tags, relevance threshold."
---

# Search Orchestrator

## Purpose
Provide powerful, filtered search across all memory stores. Support multi-dimensional queries with semantic similarity, metadata filters, and result ranking.

## Search Modes

### 1. SEMANTIC SEARCH (Default)
Query → embed → cosine similarity → rank → filter → return
```
Input: "How did we fix the MCP identity problem?"
Flow:
  - embed_text(query) → query_vector (384-dim)
  - search_semantic(query, k=50) → candidate results
  - Apply metadata filters
  - Sort by relevance_score * cosine_sim
  - Return top-k with explanations
```

### 2. KEYWORD SEARCH
Pattern matching for exact terms.
```
Input: agent:Hephaestus type:error
Flow:
  - Parse query into structured filters
  - grep/glob memory index for matching entries
  - Sort by relevance_score
  - Return results
```

### 3. HYBRID SEARCH
Semantic + keyword combined.
```
Input: "MCP identity fix" agent:Sisyphus date:2026-05
Flow:
  - Extract structured filters (agent, date, type, tags)
  - Semantic search on query text
  - Filter semantically by structured criteria
  - Interleave results (70% semantic, 30% keyword)
  - Deduplicate and rank
```

## Filter Syntax
```
General query:   <free text>
Agent filter:    agent:<name>           (e.g., agent:Hephaestus)
Date range:      date:<YYYY-MM>         (single month)
                 date:<YYYY-MM..YYYY-MM> (range)
                 date:>2026-04          (after)
                 date:<2026-03          (before)
Content type:    type:<type>            (code, error, decision, conversation, plan)
Source filter:   source:<source>        (chatgpt, deepseek, nxyme, opencode)
Tag filter:      tag:<tag>              (any tag)
Importance:      importance:><score>    (importance:>20)
Recency:         recency:<d>            (recency:<7 = last week)
Combined:        <text> agent:X type:Y date:2026-05
```

## Result Ranking
```
final_score = cosine_similarity * 0.6 
            + relevance_score * 0.3 
            + recency_boost * 0.1
```

### Result Format
Each result includes:
```json
{
  "id": "mem_abc123",
  "content_preview": "First 200 chars...",
  "cosine_similarity": 0.87,
  "relevance_score": 45,
  "final_score": 72.3,
  "tags": ["agent:Hephaestus", "type:code", "date:2026-05"],
  "source": "ses_1d4f...",
  "recency": "3d",
  "explanation": "Matches 'MCP identity' semantics, high-confidence Hephaestus code"
}
```

## Search Quality Checks
- **Precision**: Returned results should be > 60% relevant (spot check)
- **Recall**: Top results should include expected matches for known queries
- **Latency**: Semantic search < 2s, keyword < 500ms
- If quality below threshold: switch to hybrid mode

## Usage Examples
```
Search: "vector embedding pipeline" agent:Cortex
  → Recent Cortex work on embedding pipeline

Search: "error" type:error importance:>10
  → Important errors across all sessions

Search: "architecture decision" type:decision agent:Sisyphus date:2026-05
  → Architecture decisions Sisyphus made this month

Search: "" source:chatgpt date:<2026-01
  → All old ChatGPT archives (for bulk operations)
```

## NEVER
- Search without any scope when there are > 1000 entries (filter by source at minimum)
- Return results without confidence scores
- Mix sources without labeling which is which
- Skip dedup in results (same content from different sessions)

## ALWAYS
- Show filter breakdown: what filters were applied, how many matched
- Report search latency
- Surface top-3 most relevant results highlighted
- Provide "did you mean?" suggestions for empty results
