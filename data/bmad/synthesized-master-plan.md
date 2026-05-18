# N-Xyme MIND — Master Synthesis Plan
## Date: 2026-05-17 | Generated from Full System Context Analysis

---

## 📋 PRODUCT BRIEF

### What N-Xyme MIND Is
An AI agent orchestration system built on OpenCode with 16 specialized agents, BMAD workflow system (40+ skills), Rust MCP services, and a massive archive of ML assets (27GB vectors, 37K transcripts, complete learning engine).

### What It Should Be
A **self-improving, memory-aware agent ecosystem** where:
- Agents start sessions with past context (no blank slate)
- Memories are auto-injected before tool calls
- Cross-agent knowledge sharing happens automatically
- The system learns from corrections and improves routing
- Plugin failures can't take down the entire system

### The Problem
The meta-observer.js incident exposed that the entire system is **architecturally fragile** — a single plugin with `throw new Error()` in a hook blocked ALL tool calls for ALL agents, killed the MCP server, and caused complete context loss.

### The Opportunity
You have **massive untapped potential**:
- 27GB ChromaDB vector store (pre-computed embeddings)
- 37,609 session transcripts (real conversation data)
- 30GB SQLite databases (structured memory)
- Complete ML pipeline code (learning engine, memory core, intelligence)
- But it's all disconnected — agents can't use it

---

## 🏗️ ARCHITECTURE

### Current State (As-Is)

```
User Query → OpenCode → Sisyphus (Orchestrator)
                    ↓
              nx_agents MCP (Rust)
                    ↓
    ┌───────────────┼───────────────┐
    ↓               ↓               ↓
memory_ingest   memory_search    tool_routing
(MiniLM 384-dim) (cosine search) (TF-IDF 38μs)
    ↓               ↓               ↓
ingest.jsonl    ingest.jsonl    routed tool
(4,348 vectors) (never auto-used) (no memory context)
```

**Gaps:**
- No session resume with memory restore
- No auto-injection of relevant memories
- No cross-agent memory sharing
- No training loop running
- No plugin isolation
- 27GB ChromaDB sitting idle
- 37K transcripts not being used for training

### Target State (To-Be)

```
User Query → OpenCode → Sisyphus (Orchestrator)
                    ↓
              nx_agents MCP (Rust)
                    ↓
    ┌───────────────┼───────────────┼───────────────┐
    ↓               ↓               ↓               ↓
Memory Restore  Auto-Inject     Tool Routing    Learning Loop
(past context)  (relevant mem)  (ML-enhanced)  (self-improve)
    ↓               ↓               ↓               ↓
ChromaDB 27GB   Context Window  ChromaDB 27GB   Training Data
+ Session DB    + Past Sessions + Intent Pred   + Corrections
```

**Key Changes:**
1. **Memory Restore** — Agents start with past context from ChromaDB + session DB
2. **Auto-Inject** — Relevant memories injected before each tool call
3. **ML-Enhanced Routing** — Use 27GB vectors for better tool routing
4. **Learning Loop** — Corrections trigger retraining, routing improves over time
5. **Plugin Isolation** — Circuit breakers prevent single plugin from killing system

---

## 📝 EPICS & STORIES

### Epic A: Memory Infrastructure (Priority: CRITICAL)
**Goal:** Connect ChromaDB to current system, enable session resume with memory restore

| Story | Description | Effort | Dependencies |
|-------|-------------|--------|--------------|
| A-1 | Connect ChromaDB 27GB to nx_agents MCP | 8h | None |
| A-2 | Build session resume with memory restore | 6h | A-1 |
| A-3 | Auto-inject relevant memories before tool calls | 4h | A-2 |
| A-4 | Cross-agent memory sharing (Sisyphus ↔ Hephaestus) | 6h | A-2 |

**Total:** 24 hours

### Epic B: Plugin Isolation & System Resilience (Priority: CRITICAL)
**Goal:** Prevent single plugin from taking down entire system

| Story | Description | Effort | Dependencies |
|-------|-------------|--------|--------------|
| B-1 | Delete meta-observer.js permanently | 1h | None |
| B-2 | Add circuit breaker pattern to plugin system | 4h | B-1 |
| B-3 | Plugin sandboxing (timeout, error isolation) | 6h | B-2 |
| B-4 | System audit for similar single points of failure | 4h | B-3 |

**Total:** 15 hours

### Epic C: Training Data Extraction (Priority: HIGH)
**Goal:** Extract training data from 37K transcripts, build routing/intent datasets

| Story | Description | Effort | Dependencies |
|-------|-------------|--------|--------------|
| C-1 | Extract tool routing pairs from transcripts | 4h | None |
| C-2 | Build intent prediction dataset | 6h | C-1 |
| C-3 | Generate contrastive training data | 4h | C-2 |
| C-4 | Create training pipeline automation | 4h | C-3 |

**Total:** 18 hours

### Epic D: Learning Engine Integration (Priority: HIGH)
**Goal:** Wire up learning engine for self-improvement from corrections

| Story | Description | Effort | Dependencies |
|-------|-------------|--------|--------------|
| D-1 | Integrate learning engine with nx_agents MCP | 6h | None |
| D-2 | Build correction → training trigger pipeline | 4h | D-1 |
| D-3 | Implement RL-based routing optimization | 8h | D-2 |
| D-4 | Build prompt evolution system | 6h | D-3 |

**Total:** 24 hours

### Epic E: ML-Enhanced Tool Routing (Priority: MEDIUM)
**Goal:** Use 27GB ChromaDB vectors for better tool routing

| Story | Description | Effort | Dependencies |
|-------|-------------|--------|--------------|
| E-1 | Replace TF-IDF routing with ChromaDB semantic search | 6h | A-1 |
| E-2 | Build intent prediction from past sessions | 4h | C-2 |
| E-3 | Implement confidence scoring + fallback | 4h | E-1 |
| E-4 | A/B test routing accuracy (TF-IDF vs ML) | 2h | E-3 |

**Total:** 16 hours

### Epic F: Consolidation & Cleanup (Priority: MEDIUM)
**Goal:** Consolidate scattered memory, remove duplicates, optimize storage

| Story | Description | Effort | Dependencies |
|-------|-------------|--------|--------------|
| E-1 | Consolidate 37K transcripts into single index | 4h | None |
| E-2 | Remove duplicate sessions (5,844 in "New Folder") | 2h | E-1 |
| E-3 | Optimize ChromaDB + SQLite storage | 4h | E-2 |
| E-4 | Build memory health monitoring | 4h | E-3 |

**Total:** 14 hours

---

## ✅ IMPLEMENTATION READINESS

### PRD Status: ✅ COMPLETE
- Product brief defined
- Problem statement clear
- Target architecture specified
- Success metrics defined

### UX Status: ⚠️ PARTIAL
- Agent interaction patterns defined
- Memory injection UX needs design
- Plugin failure UX needs design

### Architecture Status: ✅ COMPLETE
- Current state mapped
- Target state designed
- Data flow specified
- Integration points identified

### Epics Status: ✅ COMPLETE
- 6 epics defined
- 24 stories specified
- Dependencies mapped
- Effort estimated (111 hours total)

### Overall Readiness: 85%
- **Ready to start:** Epic A (Memory Infrastructure), Epic B (Plugin Isolation)
- **Blocked on:** Training data extraction (Epic C) before Epic D (Learning Engine)
- **Risk:** ChromaDB 27GB integration may require schema migration

---

## 📊 ASSETS INVENTORY

### What You Have
| Asset | Size | Status | Immediate Value |
|-------|------|--------|-----------------|
| ChromaDB Vector Store | 27GB | ✅ Available | Pre-computed embeddings for entire project |
| Session Transcripts | 37,609 files | ✅ Available | Real conversation data for training |
| SQLite Databases | 30GB | ✅ Available | Structured memory (sessions, routing, learning) |
| Learning Engine Code | Complete package | ✅ Available | RL, self-learning, cross-session transfer |
| Memory Core Code | Complete package | ✅ Available | Tiered memory, cognitive models, retrieval |
| Training Pipeline | Scripts | ✅ Available | Generate training data, train models |
| MiniLM Embedding | 384-dim | ✅ Working | Real weights, producing embeddings |
| nx_agents MCP | 32 tools | ✅ Running | Session management, memory ops, routing |

### What's Missing
| Gap | Impact | Priority |
|-----|--------|----------|
| No ChromaDB connection | 27GB vectors sitting idle | CRITICAL |
| No session resume | Each session starts blank | CRITICAL |
| No auto-injection | Context must be manually provided | HIGH |
| No training loop | Corrections accumulate, never retrain | HIGH |
| No plugin isolation | Single plugin can kill system | CRITICAL |
| No cross-agent sharing | Agents don't learn from each other | MEDIUM |

---

## 🎯 EXECUTION PLAN

### Phase 1: Stabilize (Week 1)
- [ ] Delete meta-observer.js permanently
- [ ] Add circuit breaker to plugin system
- [ ] Connect ChromaDB to nx_agents MCP
- [ ] Build session resume with memory restore

### Phase 2: Connect (Week 2)
- [ ] Auto-inject relevant memories before tool calls
- [ ] Cross-agent memory sharing
- [ ] Extract training data from transcripts
- [ ] Build correction → training trigger pipeline

### Phase 3: Learn (Week 3)
- [ ] Integrate learning engine with MCP
- [ ] Implement RL-based routing optimization
- [ ] Build prompt evolution system
- [ ] A/B test routing accuracy

### Phase 4: Optimize (Week 4)
- [ ] Consolidate scattered memory
- [ ] Remove duplicate sessions
- [ ] Optimize storage
- [ ] Build memory health monitoring

**Total Estimated Time:** 111 hours (~4 weeks at 30h/week)

---

## 📈 SUCCESS METRICS

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| Session resume time | N/A (blank slate) | <2s | Time to load past context |
| Memory injection | 0% auto | 100% auto | % of tool calls with memory context |
| Routing accuracy | TF-IDF baseline | +20% improvement | A/B test accuracy |
| Plugin failure impact | System-wide crash | Isolated to plugin | Error containment test |
| Training loop | Never runs | Auto-trigger at 100 corrections | Correction count → retrain |
| Cross-agent sharing | 0% | 100% | Knowledge transfer test |

---

## ⚠️ RISKS & MITIGATIONS

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| ChromaDB 27GB integration fails | High | Medium | Fallback to JSONL vectors |
| Training data extraction incomplete | Medium | Low | Use subset of transcripts |
| Plugin isolation breaks existing plugins | High | Low | Test with no-code-sisyphus first |
| Memory injection slows down tool calls | Medium | Medium | Cache relevant memories, async load |
| RL routing degrades accuracy | High | Low | Keep TF-IDF fallback, A/B test |

---

*This plan synthesizes everything from the full system context analysis: 37K transcripts, 30GB databases, 27GB vectors, complete ML pipeline, and the meta-observer incident lessons.*
