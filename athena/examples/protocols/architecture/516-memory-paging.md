---
protocol: 516
name: Memory Paging
domain: architecture
created: 2026-03-05
last_updated: 2026-03-05
status: active
---

# Protocol 516: Memory Paging (Agent-Controlled Context Management)

> **Source**: Letta/MemGPT (arXiv:2310.08560). Adapted from OS-inspired tiered memory to prompt-layer explicit memory commands.

## Problem

Athena's memory retrieval is currently **passive** — the Exocortex searches and returns whatever is most semantically relevant. The agent cannot explicitly control what enters or leaves working memory. This causes:

- Context pollution (irrelevant memories from other domains cluttering responses)
- Missing context (relevant memories not retrieved because the query didn't semantically match)
- No intentional forgetting (stale information persists at equal weight to current information)

## Mechanism

Grant the agent explicit memory management commands that operate on the knowledge base during task execution.

### Memory Operations

| Operation | What It Does | When to Use |
|---|---|---|
| **Page In** | Explicitly load a topic/domain into working memory via targeted Exocortex search | Entering a domain-specific task (e.g., "page in all Trading context") |
| **Page Out** | Mark current domain context as non-active; deprioritize in future retrieval | Switching domains (e.g., leaving Trading, entering Marketing) |
| **Pin** | Lock critical context into working memory; immune to compaction | Core axioms, active constraints, current task state |
| **Rewrite** | Update a specific memory block with corrected/current information | When a fact has changed (e.g., updated pricing, new decision) |

### Tiered Memory Model

| Tier | Biological Equivalent | Athena Implementation | Volatility |
|---|---|---|---|
| **Working Memory** | Prefrontal cortex | Active context window | Highest — cleared each session |
| **Core Blocks** | Long-term procedural | `userContext.md`, `productContext.md` | Low — agent-editable, pinned |
| **Episodic Recall** | Hippocampal replay | Session logs, quicksaves | Medium — searchable, decays |
| **Archival Semantic** | Neocortical consolidation | `.context/` knowledge base | Lowest — permanent, indexed |

### Implementation at Prompt Layer

These operations are **cognitive instructions**, not API calls. The agent executes them by:

1. **Page In**: Running a targeted `smart_search.py` query scoped to a specific domain tag
2. **Page Out**: Explicitly stating "I am leaving [domain] context" and not carrying forward domain-specific details
3. **Pin**: Including critical items in the structured context block that persists across turns
4. **Rewrite**: Updating the relevant `.md` file in the memory bank via file edit

### Integration with Homeostatic Pressure (P517)

When homeostatic pressure signals context saturation (>80%), the Maintenance system should:

1. Page out non-essential domain context
2. Compact episodic recall via `context-compactor`
3. Keep only pinned core blocks and current task state
4. Resume once context utilization drops below 60%

## Biological Analogy

The hippocampus does not passively store everything — it actively consolidates, pages important memories to the neocortex during sleep, and lets irrelevant traces decay. Memory paging gives Athena the same active management over its knowledge state.

## References

- [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560)
- [Protocol 502: Context Lifecycle](502-context-lifecycle.md)
- [Protocol 517: Homeostatic Pressure](517-homeostatic-pressure.md)
