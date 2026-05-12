---
type: system-knowledge
status: active
date: 2026-04-09
tags: [research, memory, architecture]
related: [[N-XYME_CATALYST_System], [Obsidian_Best_Practices]]
rating: 9
---

# LLM MEMORY ARCHITECTURE BEST PRACTICES

## Four Memory Types

| Type | What It Stores | N-Xyme Mapping |
|------|----------------|----------------|
| **Working** | Context window (200K-2M tokens) | session state, active context |
| **Episodic** | Events, logs, executions | session_list, session_read |
| **Semantic** | Extracted facts | memory bank files, Athena |
| **Procedural** | Skills, patterns | nx_mind, unified-memory |

## Dual-Layer Pattern (2026 Standard)

### Hot Path
- Recent messages + summarized state
- In context window, zero latency

### Cold Path
- External stores queried on demand
- Handles episodic + semantic beyond context

## Hybrid Retrieval

- **Semantic** — Embedding similarity
- **Keyword** — BM25 exact matches
- **Graph** — Relationship traversal
- **Temporal** — Recency weighting

## Consolidation Rules

- Summarize sessions → semantic facts
- Merge low-importance → patterns
- Archive episodic beyond retention
- 1 year → 50 descriptors (not 50k events)

## Forgetting is Intentional

- Temporal decay
- Relevance scoring
- Configurable retention (e.g., 90 days)

---

*Research: 2025-2026 best practices*
