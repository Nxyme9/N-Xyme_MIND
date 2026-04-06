# N-Xyme_MIND — Bleeding Edge Memory Master Plan

> **Goal**: Transform N-Xyme_MIND from a solid memory system (top 30%) to bleeding edge (top 1%).
> **Based on**: 12 research papers, 8 production systems, complete architecture audit.
> **Timeline**: 4 phases, 8-12 weeks.

---

## Current State Assessment

| Metric | Current | Target |
|--------|---------|--------|
| Memories | 30K+ (raw, no consolidation) | 30K+ (consolidated, hierarchical) |
| Search | Hybrid (semantic + keyword + RRF) | Multi-graph + Observer/Reflector |
| Knowledge Graph | Keyword-based, single graph | 4 orthogonal graphs (semantic, temporal, causal, entity) |
| Forgetting | Static decay (not integrated) | Adaptive exponential decay (FadeMem) |
| Memory Types | 4 types (USER, FEEDBACK, PROJECT, REFERENCE) | 4 types + hierarchical levels (raw → episode → note → principle) |
| Learning | Feedback loops, preference modeling | Memory reconsolidation, trust-aware retrieval |
| Modalities | Text only | Text + code + image/audio embeddings |
| Cross-session | Session-scoped only | Cross-session transfer + temporal grounding |

---

## Phase 1: Intelligent Forgetting (Week 1-2) — "Stop the Noise"

**Research**: FadeMem (Alibaba + Peking University, Jan 2026) — 45% storage reduction proven.

### 1.1 Integrate Existing Forgetting Curve
- [ ] Wire `src/memory/core/forgetting.py` (Ebbinghaus curve) into main memory lifecycle
- [ ] Connect `src/memory/memory_age.py` decay to retrieval scoring
- [ ] Enable `src/memory/preference_model.py` in re-ranking pipeline

### 1.2 Implement FadeMem-Style Adaptive Decay
- [ ] Dual-layer memory hierarchy (active vs archive)
- [ ] Exponential decay modulated by 3 factors:
  - **Semantic relevance** (how related to current context)
  - **Access frequency** (how often retrieved)
  - **Temporal age** (how old the memory is)
- [ ] Automatic archival of low-score memories (not deletion — move to archive tier)

### 1.3 Memory Tiering
- [ ] Short-term (0-7 days): All memories, full access
- [ ] Medium-term (7-90 days): Decay-modulated access
- [ ] Long-term (90+ days): Archive, only high-score memories accessible
- [ ] Permanent: User-pinned memories, never decay

**Success criteria**: 30% reduction in active memory store, no loss of retrieval accuracy.

---

## Phase 2: Observer/Reflector Pattern (Week 2-4) — "Subconscious Processing"

**Research**: Mastra Observational Memory — 94.87% LongMemEval (highest ever recorded).

### 2.1 Observer Agent
- [ ] Background agent watches all agent conversations
- [ ] Converts raw messages into dense observations
- [ ] Drops raw messages after observation — context window stays stable
- [ ] No per-turn dynamic retrieval — predictable, cacheable context

### 2.2 Reflector Agent
- [ ] Background agent reviews observation log periodically
- [ ] Extracts patterns, contradictions, insights
- [ ] Updates knowledge graph with new relationships
- [ ] Triggers memory reconsolidation when conflicts detected

### 2.3 Context Window Optimization
- [ ] Two-section context: memory (observations) + message history (active conversation)
- [ ] Prompt-cacheable context — no dynamic retrieval per turn
- [ ] Stable, reproducible context across sessions

**Success criteria**: Replace per-turn retrieval with continuous observation. 50% reduction in retrieval latency.

---

## Phase 3: Multi-Graph Architecture (Week 4-6) — "Reasoning Across Memory"

**Research**: MAGMA (UT Dallas, Jan 2026) — 4 orthogonal graphs, policy-guided traversal.

### 3.1 Split Knowledge Graph into 4 Views
- [ ] **Semantic Graph**: Concept relationships, topic clustering
- [ ] **Temporal Graph**: Event timelines, session sequences
- [ ] **Causal Graph**: Cause-effect relationships, decision chains
- [ ] **Entity Graph**: Projects, technologies, people, files

### 3.2 Graph Algorithms
- [ ] BFS/DFS for multi-hop traversal (2-3 hops)
- [ ] PageRank for entity importance scoring
- [ ] Community detection for topic clustering
- [ ] Path finding for causal chain reconstruction

### 3.3 Policy-Guided Retrieval
- [ ] Query intent classification → graph selection policy
- [ ] "What happened when?" → Temporal Graph
- [ ] "Why did X cause Y?" → Causal Graph
- [ ] "What do I know about Z?" → Semantic + Entity Graphs
- [ ] Multi-graph fusion for complex queries

### 3.4 Relational Versioning (Supermemory)
- [ ] `updates` — handles contradictions ("My favorite color is now Green")
- [ ] `extends` — supplements without contradiction (adding job title)
- [ ] `derives` — second-order logic inferred from combining memories

### 3.5 Dual-Layer Temporal Grounding
- [ ] `documentDate` — when the conversation took place
- [ ] `eventDate` — when the event described actually occurred

**Success criteria**: Multi-hop reasoning across 2-3 graph hops. 85%+ accuracy on temporal queries.

---

## Phase 4: Memory Reconsolidation + Hierarchical Memory (Week 6-8)

**Research**: HiMem (Jan 2026) — hierarchical memory with self-evolution.

### 4.1 Memory Reconsolidation
- [ ] When retrieved memory conflicts with new info → auto-revise
- [ ] Conflict detection via semantic similarity + temporal ordering
- [ ] Revision logging (track what changed and why)
- [ ] User notification for significant revisions

### 4.2 Hierarchical Memory Levels
- [ ] **Raw**: Unprocessed conversation chunks (store-then-extract paradigm)
- [ ] **Episode**: Topic-aware event segmentation (surprise detection)
- [ ] **Note**: Stable knowledge via multi-stage extraction
- [ ] **Principle**: Abstracted rules and patterns from multiple notes

### 4.3 Cross-Session Transfer
- [ ] Promote important session memories to long-term storage
- [ ] Session summary generation at end of each session
- [ ] Cross-session pattern detection
- [ ] Learning from past session outcomes

### 4.4 Trust-Aware Retrieval (Membrane)
- [ ] Score memories by competence/trust, not just relevance
- [ ] Track memory source reliability
- [ ] Decay trust for unverified memories
- [ ] Boost trust for user-confirmed memories

### 4.5 Store-Then-Extract Paradigm (Kioxia)
- [ ] Store raw conversation chunks alongside extracted memories
- [ ] Extract on-demand for unpredicted queries
- [ ] Don't lose information in the extraction pipeline

**Success criteria**: Hierarchical memory with 4 levels. Auto-reconsolidation on conflict. Cross-session learning.

---

## Phase 5: Multimodal + Distributed (Week 8-12) — "Beyond Text"

### 5.1 Multimodal Memory (MemVerse)
- [ ] Image embedding support (CLIP or similar)
- [ ] Code embedding support (CodeBERT or similar)
- [ ] Audio embedding support (Whisper embeddings)
- [ ] Unified retrieval across modalities

### 5.2 Context Virtualization (OMEGA)
- [ ] Checkpoint/resume for session state
- [ ] Auto-capture hooks for decisions and errors
- [ ] Session state serialization
- [ ] Cross-instance state sync

### 5.3 Distributed Memory
- [ ] Memory sync across multiple instances
- [ ] Conflict resolution for concurrent writes
- [ ] Eventual consistency model
- [ ] Offline-first with sync on reconnect

### 5.4 Importance Scoring (WideMem)
- [ ] YMYL (Your Money Your Life) prioritization
- [ ] Critical memory protection (never decay)
- [ ] User-defined importance levels
- [ ] Automatic importance inference from context

**Success criteria**: Multimodal memory with image/code/audio support. Distributed sync across instances.

---

## Implementation Priority (ROI Ranking)

| Priority | Feature | Effort | Impact | ROI |
|----------|---------|--------|--------|-----|
| 1 | Intelligent Forgetting (FadeMem) | Low | High | 🔴 |
| 2 | Observer/Reflector (Mastra) | Medium | Critical | 🔴 |
| 3 | Memory Reconsolidation (HiMem) | Medium | High | 🔴 |
| 4 | Relational Versioning (Supermemory) | Low | Medium | 🟡 |
| 5 | Multi-Graph Architecture (MAGMA) | High | Critical | 🟡 |
| 6 | Dual-Layer Temporal Grounding | Low | Medium | 🟡 |
| 7 | Episodic Context Preservation (E-mem) | Medium | High | 🟡 |
| 8 | Store-Then-Extract (Kioxia) | Low | Medium | 🟢 |
| 9 | Multimodal Memory (MemVerse) | High | Medium | 🟢 |
| 10 | Context Virtualization (OMEGA) | Medium | Medium | 🟢 |
| 11 | Trust-Aware Retrieval (Membrane) | Medium | Medium | 🟢 |
| 12 | Distributed Memory | High | Low | 🟢 |

---

## Success Metrics

| Metric | Current | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 |
|--------|---------|---------|---------|---------|---------|---------|
| Active memories | 30K+ | 20K (-30%) | 20K | 20K | 15K (-50%) | 15K |
| Retrieval latency | ~200ms | ~200ms | ~100ms (-50%) | ~150ms | ~150ms | ~150ms |
| Multi-hop reasoning | ❌ | ❌ | ❌ | ✅ (2-3 hops) | ✅ (2-3 hops) | ✅ (2-3 hops) |
| Memory consolidation | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Cross-session transfer | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Multimodal support | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Distributed sync | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| LongMemEval score | ~70% | ~75% | ~85% | ~90% | ~92% | ~95% |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Forgetting deletes important memories | Archive tier (not deletion), user-pinned memories never decay |
| Observer/Reflector adds latency | Run asynchronously, no impact on user-facing latency |
| Multi-graph complexity | Start with 2 graphs (semantic + temporal), add causal + entity later |
| Reconsolidation conflicts | Log all revisions, user notification for significant changes |
| Multimodal storage costs | Store embeddings only, not raw media |
| Distributed sync conflicts | Eventual consistency, last-write-wins with conflict logging |

---

## Quick Wins (Week 1)

These can be done immediately with existing code:

1. **Wire forgetting.py** into router.py retention pipeline (exists but not integrated)
2. **Enable learning adapter re-ranking** by default in router.py (exists but minimal usage)
3. **Add KG relationship scoring** based on frequency (simple enhancement)
4. **Activate preference_model.py** in re-ranking pipeline (exists but unused)
5. **Integrate sleep_cycle.py** for background memory processing (exists but not wired)

**Expected impact**: 15% improvement in retrieval quality, 20% reduction in noise, zero new code.
