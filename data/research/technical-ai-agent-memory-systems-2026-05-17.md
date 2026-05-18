---
stepsCompleted: [1,2,3,4,5,6]
inputDocuments: []
workflowType: 'technical-research'
research_type: 'technical'
research_topic: 'State-of-the-art AI Memory Systems & Vector Memory Architectures for Agent Platforms'
research_goals: 'Determine gold-standard architecture, chunking, deduplication, metadata, episodic/semantic separation, bleeding-edge features, and anti-patterns for N-Xyme_MIND (13K sessions, ONNX, local-only)'
date: '2026-05-17'
source_verification: true
---

# Technical Research Report: AI Memory Systems & Vector Architectures for Agent Platforms

**Date:** 2026-05-17
**Research Type:** Technical

---

## Executive Summary

The AI agent memory market reached **$6.27B in 2026** and is projected to grow to $28.45B by 2030 (35% CAGR). The industry has converged on a fundamental insight: *the model is not the product — the memory is*. An agent with a frontier-class model but no persistent memory is "a genius with amnesia."

This report synthesizes findings across 7 key questions, drawing on 30+ sources including production benchmarks (LOCOMO, LongMemEval), peer-reviewed research (ICLR 2026 MemAgents, HMAT, Synapse), and production system analysis (Mem0, Letta, Zep, Cognee, KektorDB).

**Key finding for N-Xyme_MIND:** With 13K session files, ONNX embeddings, local-only deployment — you are at exactly the scale where flat vector storage breaks down and hierarchical architectures become mandatory. Several design decisions in your current system are validated by bleeding-edge research; several others need fundamental rearchitecting.

---

## 1. Hierarchical Memory: How Leading Systems Organize

### Industry Consensus: Four-Layer Architecture

The 2026 production standard decomposes memory into four distinct tiers, inspired by both cognitive science and OS virtual memory:

| Layer | Analogy | Storage | Latency | Persistence | Capacity |
|-------|---------|---------|---------|-------------|----------|
| **In-Context (Working)** | CPU Registers | Context window | 0ms | Session only | 128K-10M tokens |
| **Episodic** | RAM / Event log | Vector DB + Time index | 50-200ms | Cross-session | Unlimited |
| **Semantic** | Hard Drive / Facts | Graph DB + KV store | 100-500ms | Permanent | Fact-scalable |
| **Procedural** | Muscle memory | Config + learned rules | Instant | Permanent | Small |

### How Specific Systems Implement This

**Letta (formerly MemGPT)** — UC Berkeley spin-off, $10M seed.
- **Core memory:** 2-4KB always in context (agent's self-understanding + current task)
- **Archival memory:** External vector store, no size limit, searchable via embedding
- **Recall memory:** Conversation history log, pageable in chunks
- **Control:** Agent manages all three tiers via function calls (`core_memory_replace`, `archival_memory_search`, `archival_memory_insert`)
- **Benchmark:** 93.4% accuracy on Deep Memory Retrieval vs 35.3% for recursive summarization
- **Influence:** This LLM-managed paging metaphor is Letta's core innovation — treating context window as RAM and external store as disk

**Mem0** — Most widely adopted memory layer (48K GitHub stars, $24M funding).
- **Three storage layers:** Vector (semantic search) + Graph (relationships) + Key-Value (preferences)
- **Four-scope model:** `user_id`, `agent_id`, `run_id`, `app_id` (plus optional `org_id`)
- **Automatic extraction:** Conversations → facts → storage, with built-in conflict detection
- **LOCOMO benchmark:** 66.9% accuracy, 0.71s median latency vs full-context 72.9%, 9.87s latency (14x token savings)
- **Graph-enhanced variant (Mem0g):** 68.4% accuracy, 1.09s latency

**ChatGPT Memory** (OpenAI, Feb 2024 + Apr 2025 update):
- **Two-tier:** "Saved memories" (explicit facts) + "Chat history" (insights from past conversations)
- **Process:** Facts converted to semantic embeddings → stored in vector database → retrieved at session start → injected as system-level instructions
- **User controls:** View, delete, toggle on/off memory; temporary chat bypasses memory
- **Limitation:** Flat memory — no knowledge graph, no typed relationships, no structured categories

**Claude Projects / Claude Code:**
- **Claude Projects:** Persistent *instructions* (claude.md + attached files), NOT persistent *memory*. Each conversation starts fresh.
- **Claude Code memory systems have 6 levels:**
  1. In-context (default — session-only)
  2. claude.md (instruction memory — persists via files)
  3. Structured SQL (episodic memory — for "what happened")
  4. Vector database (knowledge memory — semantic retrieval at scale)
  5. MCP-based tools (Recallium, MemClaw for cross-tool persistence)
  6. Cross-agent memory (shared brain via MCP protocol)
- **2026 breakthrough:** Claude added "Dreaming" — agents refine memories between sessions, pulling shared learnings across agents

**Cursor AI (2026 v2.6):**
- No built-in persistent memory model — relies on context window per session
- External memory via MCP tools (Recallium, cline-memory-bank)
- `.cursor/rules/memory-bank.mdc` for rule-based memory across sessions
- Intelligent indexing and real-time codebase context (not long-term memory)

**Devin (Cognition):** Proprietary — published details minimal but inferred architecture includes:
- Session-oriented memory per task
- Knowledge accumulation across projects
- Emphasis on tool-use history and environment state

### ⚡ N-Xyme_MIND Assessment

Your current architecture has **episodic memory (session data)** and is building **semantic memory (vectors)**. Missing: a distinct **working memory** (currently active agent context) and **procedural memory** (learned agent behavior rules). The "agent" gating in tools.json partially fills procedural, but there's no learned-cross-session behavior layer.

---

## 2. Gold-Standard Chunking Strategies

### The Hard Truth: One Strategy Does Not Fit All

A comprehensive 2026 benchmark of 7 chunking strategies across 50 academic papers revealed:

| Strategy | Chunks | Avg Size | Accuracy | Doc F1 | Best For |
|----------|--------|----------|----------|--------|----------|
| Recursive 512 (overlap 128) | 6,652 | 420 tokens | **67%** | 0.52 | **General-purpose — best all-rounder** |
| Recursive 256 | 13,594 | 210 tokens | **69%** | 0.33 | High-precision, code, decisions |
| Recursive 1024 | 3,456 | 820 tokens | 63% | **0.88** | Document coverage |
| Fixed 512 | 6,628 | 512 tokens | 65% | 0.48 | Baseline benchmarking only |
| Fixed 256 | 13,590 | 256 tokens | 66% | 0.32 | Quick prototyping |
| **Semantic chunking** | 17,481 | 43 tokens | **54%** | **0.42** | ❌ Collapses at scale |
| Proposition chunking | 19,223 | 38 tokens | 51% | 0.38 | ❌ Worse than semantic |

**Critical finding:** Semantic chunking *collapses at scale* — produced 17,481 tiny chunks averaging 43 tokens from 50 papers. While it found the right *pages* (Page F1 0.91), document-level retrieval collapsed (0.42 Doc F1) and accuracy dropped to 54%. The 46 disconnected tiny chunks destroyed narrative coherence.

### Recommended Multi-Strategy Approach for Agent Memory

Per-content-type chunking is the gold standard:

| Content Type | Strategy | Chunk Size | Overlap | Rationale |
|-------------|----------|------------|---------|-----------|
| **Session transcripts** | Recursive 256 | 210 tokens | 20% | Preserves conversational turns, high precision for recall |
| **Code blocks** | Recursive 512 | 420 tokens | 0% | Code needs complete functions — overlap creates noise |
| **Decisions/Key facts** | Recursive 128 | 100 tokens | 10% | Small precise chunks for exact retrieval |
| **System config/agent defs** | Document-level | Full file | N/A | These are short — embed as single units |
| **Summaries/compacted sessions** | Recursive 1024 | 820 tokens | 15% | Summaries are inherently condensed |

### Chunk Size Tradeoff

From the Redis 2026 chunking guide:
- **Smaller chunks (k=5):** Higher accuracy (67-69%) — 5 retrieval slots sample 5 different locations
- **Larger chunks (k=2-3):** Higher document F1 (0.88) — each chunk spans more document but fewer passages
- **Sweet spot:** Recursive 512 with 20% overlap for heterogeneous data

### ⚡ N-Xyme_MIND Recommendation

**DO NOT use semantic chunking** — it's the wrong choice for your 13K session files. Instead:
1. **Session transcripts → Recursive 256** (preserves turn boundaries)
2. **Session digests/summaries → Recursive 512** (compacted content)
3. **Agent definitions/config → Document-level** (short, high-value)
4. **Memory vectors → Recursive 128 with high overlap** (critical decisions need redundancy)
5. **Every chunk carries a `chunk_type` metadata field** for filtering

---

## 3. Semantic Deduplication Without Data Loss

### The State of the Art

**NVIDIA SemDeDup** (2023, refined through 2026):
1. Generate embeddings for all data points
2. Cluster into k clusters (k-means)
3. Compute pairwise cosine similarity within clusters
4. Identify duplicates at threshold (typically 0.92-0.97 cosine similarity)
5. **KEEP the representative with lowest similarity to cluster centroid** (most diverse)
6. Can remove up to 50% of data with minimal performance loss

**Mem0's conflict-aware deduplication:**
- **Recency wins:** Newer fact overrides older one when contradiction detected
- **Explicit confirmation:** For important changes, user confirms
- **One value per (subject + predicate):** Ensures agent has exactly one current value per fact
- **No silent loss:** Contradiction is detected and flagged, not silently dropped

**Production dedup strategies:**

| Strategy | Mechanism | Loss Risk | Best For |
|----------|-----------|-----------|----------|
| Exact match (hash) | MD5/SHA of content | None | Identical duplicates |
| Near-exact (MinHash LSH) | Jaccard similarity > 0.9 | Minimal | Near-identical sessions |
| **Semantic (cosine + k-means)** | Embed + cluster + threshold | **Controlled** | Concept-level dedup |
| Temporal (recency wins) | Compare timestamps | Possible | Preferences, facts |
| Importance-weighted | Keep if salience > 0.7 | Low | High-value decisions |

### ⚡ Critical: The N-Xyme Dedup Risk

Your system's existing dedup threshold (cosine > 0.95) is standard — but you MUST protect:
- **Agent decisions** (10x relevance): Exempt from automatic dedup or use lower threshold (0.98+)
- **Code references** (5x relevance): Dedup only exact/near-exact matches
- **Errors/failures** (3x relevance): Never dedup — each failure is unique data
- **Routine tool calls** (1x): Safe to dedup at 0.95

### ⚡ N-Xyme_MIND Recommendation

Implement **layered dedup** with `relevance_type` gating:

```
if chunk.relevance_type in (10x, 5x):
    threshold = 0.98  # Almost no dedup
    strategy = "exact_match_only"
elif chunk.relevance_type == 3x:
    threshold = 0.99  # Nearly exact
    strategy = "minhash"
else:  # 1x, 0.1x
    threshold = 0.95  # Aggressive
    strategy = "semantic+kmeans"
```

And always: **dedup moves to trash, never deletes permanently** (30-day recovery window).

---

## 4. Metadata Schema for Fast Filtering

### Production-Grade Schema Design

Based on analysis of Pinecone, Weaviate, Qdrant, Mem0, and Upstash metadata filtering patterns:

```json
{
  "vector": [0.123, 0.456, ...],
  "id": "mem_abc123def",
  
  "metadata": {
    // === CORE IDENTITY (used for pre-filtering) ===
    "agent_id": "hephaestus",           // Which agent created this
    "session_id": "ses_abc123",         // Source session
    "user_id": "nxyme",                 // Who triggered it
    
    // === TEMPORAL (time-range queries) ===
    "created_at": "2026-05-17T10:30:00Z",  // ISO 8601
    "session_date": "2026-05-16",          // Date-only for daily queries
    "ttl_days": 90,                        // Auto-expire after
    
    // === CLASSIFICATION (filter + routing) ===
    "type": "decision",                    // enum: decision | code | error | tool_call | system | preference | fact
    "relevance_score": 0.85,              // 0.0 - 1.0 (for importance-weighted retrieval)
    "salience": 0.75,                      // 0.0 - 1.0 (from salience scorer)
    "chunk_strategy": "recursive_256",     // How chunked
    
    // === TAGGING (multi-filter) ===
    "tags": ["rust", "memory-system", "refactor", "architecture-decisions"],
    "category": "code/refactor",           // Hierarchical category
    
    // === PROVENANCE ===
    "source_file": "data/sessions/ses_abc123.jsonl",
    "parent_id": "mem_def456",            // If this is a consolidation of another memory
    "is_summary": false,                   // Is this a compaction/summary?
    "compaction_round": 0,                // How many times consolidated
    
    // === RETRIEVAL CONTROL ===
    "embedding_model": "onnx-minilm-l6-v2", // Which model produced this
    "embedding_dim": 384,
    "content_hash": "sha256:abc...",       // For exact dedup
    
    // === AGENT PLATFORM SPECIFIC ===
    "project": "n-xyme-mind",
    "branch": "main",
    "tool_name": "delegate_task",          // If tool call
    "error_type": null,                    // If error
  }
}
```

### Pre-filtering vs Post-filtering

| Approach | Performance | Accuracy | When to Use |
|----------|-------------|----------|-------------|
| **Pre-filter** (filter-then-search) | Fast if selective | High | `agent_id`, `type`, `user_id` (low cardinality) |
| **Post-filter** (search-then-filter) | Slow if restrictive | Perfect | `tags`, `category` (high cardinality) |
| **Integrated** (into HNSW graph) | Best both worlds | High | Modern: Pinecone, Qdrant 1.10+ |

**Cardinality warning:** Fields like `timestamp_ms` or `session_id` have HIGH cardinality → will cause "flat scan" fallback. Use `session_date` (YYYY-MM-DD) instead of full timestamp for pre-filtering.

### ⚡ N-Xyme_MIND Recommendation

Your current metadata schema is sound but needs these additions:
1. **Add `session_date`** (date-only for efficient range queries)
2. **Add `chunk_type`** to enable type-specific retrieval strategies
3. **Add `salience`** (from relevance scorer) for importance-weighted retrieval
4. **Add `compaction_round`** to track consolidation depth
5. **Index on (`type`, `agent_id`, `session_date`)** for fast pre-filtering

---

## 5. Episodic vs Semantic Memory Separation

### Why This Distinction Matters

The ICLR 2026 MemAgents workshop in Rio de Janeiro definitively established: **the type of memory matters more than the amount.**

- **Episodic memory:** "On May 17 at 10:30 AM, the user asked me to refactor the auth module using JWTs." — timestamped, specific, indexable.
- **Semantic memory:** "The user prefers JWTs over session cookies." — distilled fact, no temporal context, single current value.

### The Consolidation Problem

The research from MAGMA, AdaMem, and MemAgrees identifies the critical architectural pattern:

```
Session → Episodic Store (raw) → Consolidation → Semantic Store (facts)
                                              ↓
                                    Periodic pruning of raw episodes
```

**Consolidation triggers:**
- **Salience threshold:** Events > 0.75 salience trigger semantic extraction
- **Session end:** Generate 3-5 sentence summary + extract key facts
- **Nth interaction:** After N interactions with same topic, consolidate known facts
- **User correction:** Explicit contradiction → UPDATE semantic fact, keep BOTH episodic records

### Architecture Pattern

```mermaid
Working Memory (Context Window)
    ↕ (agent-managed paging)
Episodic Memory (Vector DB + Time Index)
    ↓ (consolidation pass)
Semantic Memory (Graph/KV Store)
    ↓ (periodic compaction)
Archival Storage (Compressed summaries)
```

**Episodic needs dual indexing:**
1. **Timestamp index** for: "What happened last session?"
2. **Embedding index** for: "Have we seen this error before?"

**Semantic needs:**
- **Upsert semantics:** One value per (subject + predicate)
- **Versioning:** Track fact evolution (old_value → new_value)
- **Invalidation:** Mark stale facts rather than silently deleting

### Implementation from ICLR 2026: Synapse Architecture

The Synapse paper (arXiv:2601.02744) introduces a **Unified Episodic-Semantic Graph:**
- Raw interaction logs = episodic nodes
- Abstract concepts = semantic nodes
- Retrieval via **Spreading Activation:** input injects energy, propagates through temporal + causal edges
- **Lateral inhibition** suppresses irrelevant distractors
- Result: Surfaces structurally related info even without semantic similarity

### ⚡ N-Xyme_MIND Assessment

Your current architecture mixes episodic + semantic into one vector store. This will fail at scale because:
- A "user prefers JWTs" fact is retrieved alongside "on May 17 I ran cargo test" — dilution
- Temporal queries ("what happened yesterday") compete with semantic queries ("what's the auth pattern?")
- No consolidation pipeline — raw sessions accumulate forever

**Immediate action:** Separate your vector indices (or namespaces) into `episodic` and `semantic` with different retrieval strategies and write patterns.

---

## 6. Bleeding-Edge Features

### 6.1 Memory Graphs (Vector + Graph Hybrid)

The 2026 consensus is that vector-only memory is insufficient. Three patterns dominate:

| System | Approach | Key Innovation |
|--------|----------|----------------|
| **KektorDB** | In-memory HNSW + Temporal Knowledge Graph | Cognitive engine auto-consolidates, detects contradictions, time-decay |
| **Cognee** | Knowledge graph from unstructured data | Graph traversal + vector search for relation-aware retrieval |
| **Zep** | Hybrid vector + Temporal Knowledge Graph | Native message history + temporal reasoning |
| **Neo4j Agent Memory** | Single graph for all 3 memory types | Multi-agent shared brain via Cypher queries |
| **MemORAI** | Provenance-enriched graph | Every fact linked to turn-level provenance |

**Most impactful for N-Xyme:** KektorDB's approach of combining HNSW for similarity + temporal KG for relationships directly maps to your existing ONNX embedding pipeline.

### 6.2 Active Recall / Self-Improving Retrieval

**Evo-Memory (Google DeepMind, 2025):**
- Agents with self-evolving memory improved accuracy consistently
- Cut steps in HALF on ALFWorld (22.6 → 11.5)
- **Key finding:** Success depends on agent's ability to *refine and prune*, not just accumulate
- Smaller models matched larger ones with static context

**Anthropic Claude "Dreaming" (2026):**
- Agents refine memory between sessions
- Pull shared learnings across agents
- Keep knowledge up-to-date without manual intervention

**Mem0's Token-Efficient Algorithm:**
- 91.6 on LoCoMo
- 93.4 on LongMemEval
- Average 6,956 tokens per retrieval call vs ~26,000 for full-context

### 6.3 Cross-Session Pattern Detection

**HMAT (Hierarchical Memory Architecture for Tasks, 2026):**
- Three-tier: working + episodic + semantic
- +14.3% on WebArena, +8.7% on SWE-bench, +22.6% on PlanMarathon
- **Episodic memory** provides largest gain for error recovery
- **Semantic memory** dominates for tasks with repeating procedural structure

**A-MEM (Agentic Memory, arXiv:2502.12110):**
- Dynamic memory organization based on Zettelkasten principles
- Intelligent indexing + linking via ChromaDB
- Continuous memory evolution and refinement
- Agent-driven decision making for memory management

### 6.4 Memory Decay and Forgetting

Production systems in 2026 implement **active forgetting** as a feature:
- **Time-decay:** Memories older than TTL have reduced retrieval priority
- **Importance-weighted:** Low-importance memories decay faster
- **Contradiction-based:** When new fact contradicts old one, old one is flagged
- **Salience-gated:** Routine interactions decay quickly; high-salience events persist
- **The "forgetting curve"** from cognitive science maps to exponential decay in retrieval priority

### ⚡ N-Xyme_MIND Priority Recommendations (Bleeding Edge)

| Feature | Effort | Impact | Priority |
|---------|--------|--------|----------|
| Separate episodic/semantic indices | 2-3 days | Critical | **P0** |
| Add salience scoring pipeline | 3-5 days | High | **P1** |
| Implement session-end consolidation | 5-7 days | High | **P1** |
| Add memory graph (entity relationships) | 2-4 weeks | Medium | **P2** |
| Active forgetting / decay curves | 1-2 weeks | Medium | **P2** |
| Agent-managed memory (self-refine) | 3-4 weeks | Low | **P3** |
| Cross-session pattern detection | 4-6 weeks | Low | **P3** |

---

## 7. Anti-Patterns That Break at Scale (10K+ Sessions)

### Deadly Anti-Patterns (Guaranteed Failure)

**1. Flat vector storage with no hierarchy**
- Problem: Every session adds vectors to one undifferentiated pool
- At 10K sessions: Drowning in semantically similar but contextually irrelevant results
- Sign: Context poisoning — agent retrieves its own mistakes, reinforces them
- **Solution:** Hierarchical routing (domain → category → memory trace → episode)

**2. Using context window as memory**
- Problem: 1M token context = $3 per turn at Claude pricing; $6M/month for 400K conversations
- Lost-in-the-middle problem: Models lose accuracy on content in the middle of long contexts
- **Solution:** External memory with selective retrieval (14x token savings proven)

**3. Semantic chunking as default**
- Problem: Produces 43-token fragments — 54% accuracy, 0.42 Doc F1
- At 13K sessions: 100K+ tiny fragments, zero narrative coherence
- **Solution:** Recursive chunking with content-type-specific strategies

**4. No consolidation pipeline**
- Problem: Raw session data accumulates indefinitely
- At 10K sessions: Millions of individual events, retrieval becomes noise
- **Solution:** Session-end consolidation (3-5 sentence summary + fact extraction), archive raw events

**5. Synchronous memory writes**
- Problem: Every memory write blocks the response loop — adds 50-200ms per turn
- **Solution:** Async queue (in-process buffer → flush to store in background)

**6. Ignoring cardinality in metadata filtering**
- Problem: High-cardinality fields (`timestamp_ms`, `session_id`) force flat scans
- At 10K sessions: Every filtered query becomes O(n)
- **Solution:** Use date-truncated fields (`session_date`), keep cardinality low

### Warning Signs (Degradation Pattern)

From Aakash Sharan's "9 Ways Vector Databases Fail in Production":

```
1. Insertion/deletion churn → index fragmentation → recall drop
2. Vector drift (data distribution shifts) → centroid collapse
3. Metadata filter interaction → HNSW graph disconnect
4. Memory fragmentation → RAM ballooning
5. Disk offload latency → query timeout
6. Cached results serving → stale memories retrieved
7. Authentication overhead → per-user filtering latency
8. Shard miss rate → routing failures
9. Recall/latency parameter drift → unpredictable performance
```

### Cardinality-Induced Failures

From metadata filtering research at Pinecone (ICML 2025):

- **High-cardinality trap:** Fields like `user_id` with 10M unique values → metadata index larger than vector index → flat scan fallback
- **Missing field problem:** Vector DBs treat absent metadata as "hard no" — documents silently disappear from results
- **Multi-attribute latency:** AND/OR combinations add exponential complexity to query planner

### ⚡ N-Xyme_MIND Threat Assessment

| Anti-Pattern | Current Status | Risk Level |
|-------------|----------------|------------|
| Flat vector storage | ⚠️ Single store for all | **HIGH** — immediate risk at current scale |
| Context window as memory | ✅ Not used this way | Low |
| Semantic chunking | ✅ Using recursive | Low |
| No consolidation | ⚠️ Sessions accumulate raw | **HIGH** — critical to address |
| Sync writes | ❓ Unknown implementation | Medium — verify |
| Cardinality in filters | ⚠️ Need to audit metadata fields | Medium |
| No decay/forgetting | ⚠️ Unclear if implemented | Medium |

---

## Specific Recommendations for N-Xyme_MIND

### Immediate (Week 1-2)

1. **Split vector namespace** into `episodic` (raw sessions) and `semantic` (consolidated facts) with different retrieval strategies
2. **Add `session_date` metadata field** for efficient time-range pre-filtering
3. **Implement salience-gated dedup** — protect high-relevance chunks (decisions, code, errors) from aggressive dedup
4. **Audit current metadata schema** against the production schema in Section 4 — index on `(type, agent_id, session_date)`

### Short-term (Month 1)

5. **Build session-end consolidation pipeline:**
   - At session close → generate 3-5 sentence summary
   - Extract key facts (decisions, preferences, errors)
   - Write summary as high-salience synthetic episodic event
   - Archive raw turn events to cold storage
6. **Implement async memory writes** — queue events, flush background
7. **Add `relevance_score` to all chunks** (from existing relevance scorer)
8. **Set up monitoring:** retrieval hit rate, token savings, latency p50/p95/p99

### Medium-term (Month 2-3)

9. **Implement memory graphs** — extract entity-relationship triples from sessions → build lightweight knowledge graph
10. **Add temporal decay** — memories older than N days get reduced retrieval priority
11. **Build cross-session pattern detection** — track repeated error patterns, recurring user requests, frequent tool combinations
12. **Evaluate KektorDB or Cognee** as potential integrated memory backends

### Production Benchmarks to Target

| Metric | Current (est.) | Target | Source |
|--------|---------------|--------|--------|
| Retrieval recall@10 | ? | > 85% | Industry standard |
| Retrieval latency p50 | ? | < 100ms | Mem0 benchmark |
| Token savings vs full-context | ? | > 80% | Mem0 reports 90% |
| Dedup precision | ? | > 99% | No critical data loss |
| Session compaction ratio | ? | 10:1 | Raw → summary |

### Framework Recommendations by Use Case

| Use Case | Recommended System | Why |
|----------|-------------------|-----|
| General agent memory | **Mem0** (self-hosted OSS) | Full data control, 48K stars, mature |
| Long-horizon task memory | **Letta** | OS-style paging, agent-controlled |
| Multi-agent shared memory | **Neo4j agent-memory** | Single graph, shared across agents |
| Knowledge-intensive | **Cognee** | Knowledge graph from unstructured data |
| Enterprise compliance | **Zep** | Temporal KG + audit trails |
| Local-first, embedded | **KektorDB** | In-memory, HNSW + TKG, cognitive engine |
| **N-Xyme_MIND (current fit)** | **Mem0 + ONNX bridge** | OSS, local, vector + graph + KV, Apache 2.0 |

---

## Sources

1. Mem0, "State of AI Agent Memory 2026" (Apr 2026) — benchmarks, architectures, benchmarks
2. AI Magicx, "The AI Agent Memory Architecture Deep Dive" (Apr 2026) — four memory types
3. Fountain City Tech, "Agent Memory & Knowledge Systems Compared" (May 2026) — 5-system comparison
4. Digital Applied, "Agent Memory Architectures: Vector vs Graph vs Episodic" (Apr 2026)
5. Zylos Research, "AI Agent Memory Architectures" (Apr 2026) — Letta deep dive
6. ClawrXiv, "HMAT: Hierarchical Memory Architecture for Tasks" (Feb 2026) — long-horizon evaluation
7. Chanl Blog, "Your Agent Remembers Everything Except What Matters" (Mar 2026) — episodic vs semantic ICLR 2026
8. arXiv:2601.02744, "Synapse: Episodic-Semantic Memory via Spreading Activation"
9. arXiv:2603.29194, "Multi-Layered Memory Architectures for LLM Agents"
10. RunVecta, "We Benchmarked 7 Chunking Strategies" (2026) — chunking benchmark
11. Redis, "Best Chunking Strategies for RAG Pipelines" (Apr 2026)
12. NVIDIA NeMo, "Semantic Deduplication" — SemDeDup algorithm
13. Pinecone, "Accurate and Efficient Metadata Filtering in Serverless Vector DB" (ICML 2025)
14. Aakash Sharan, "9 Ways Vector Databases Fail in Production" (Mar 2026)
15. Mem0, "Memory Retrieval Strategies for AI Agents" (May 2026) — 5 retrieval shapes
16. Towards AI, "The State of AI Agent Memory in 2026" (May 2026)
17. GettyMaxim, "Comparing Agent Memory Architectures" (Oct 2025)
18. Atlan, "Agentic AI Memory vs Vector Database" (Apr 2026)
19. Neo4j, "When Your Agents Share a Brain" (Apr 2026)
20. GitHub IAAR-Shanghai/Awesome-AI-Memory — curated knowledge base (852 stars)
21. GetML, "How to Design Efficient Memory Architectures" (Nov 2025) — failure modes analysis
22. Machine Learning Mastery, "The 6 Best AI Agent Memory Frameworks 2026" (Apr 2026)
23. Let's Data Science, "AI Agent Memory Architecture: Zero to Production" (Mar 2026)
24. Google DeepMind, "Evo-Memory" (2025) — self-evolving memory
25. Shareuhack, "AI Agent Memory Architecture Guide: SQLite to Vector DB" (Apr 2026)
26. Iterathon, "AI Agent Memory Systems Cut Costs 60%" (Jan 2026)
27. BinaryTheme, "ChatGPT Memory Systems" (May 2026)
28. Pacific Research, "Memory Layers at Scale" (Meta, Dec 2024)
29. MindStudio, "Claude Code Memory Systems Explained" (Apr 2026)
30. Felo, "How to Add Persistent Memory to Claude Projects" (Apr 2026)
