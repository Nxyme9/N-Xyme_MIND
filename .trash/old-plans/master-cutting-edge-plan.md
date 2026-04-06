# N-Xyme_MIND — Master Plan: Cutting-Edge Local Hybrid LLM Orchestration

> **From**: Current state (691 tests, 0 vulns, 30K memories, 5 sources)
> **To**: Most cutting-edge local hybrid LLM orchestration platform
> **Timeline**: 6 phases, 12-16 weeks
> **Philosophy**: Local-first, hybrid cloud fallback, zero API key dependency

---

## Current State Assessment

| Metric | Current | Target |
|--------|---------|--------|
| Tests | 691 passing | 1000+ |
| Security | 0 vulns | 0 vulns |
| Memory sources | 5 | 8+ |
| Memory types | 4 (raw) | 4 types × 4 levels (hierarchical) |
| Knowledge graphs | 1 (keyword) | 4 orthogonal (semantic, temporal, causal, entity) |
| Learning | Feedback loops | Self-improving with reconsolidation |
| Models | OpenCode Zen free | Local + cloud hybrid with auto-failover |
| Context management | None | Intelligent compaction + session notes |
| Token awareness | None | Real-time estimation + cost control |
| Multi-modal | Text only | Text + code + image + audio |

---

## Phase 1: Foundation Hardening (Week 1-2) — "Stop the Bleeding"

**Goal**: Implement critical missing components from ant-source-code.

### 1.1 Token Estimation (from ant-source tokenEstimation.ts)
- [ ] `src/intelligence/token_estimator.py` — Accurate token counting for all models
- [ ] Integrate with cost_tracking.py for real-time cost awareness
- [ ] Add context window awareness to agent routing decisions
- **Source**: `ant-source-code-main/utils/tokenEstimation.ts`
- **Effort**: 2 hours

### 1.2 Context Compaction (from ant-source compact/)
- [ ] `src/intelligence/context_compact.py` — Intelligent context window management
- [ ] Implement conversation summarization when approaching limits
- [ ] Add priority-based context pruning (keep important, discard filler)
- **Source**: `ant-source-code-main/services/compact/`
- **Effort**: 3 hours

### 1.3 Task Lifecycle (from ant-source Task.ts + tasks/)
- [ ] `src/orchestration/task_lifecycle.py` — Full task state machine
- [ ] States: pending → running → paused → completed/failed/cancelled
- [ ] Add task persistence, resumption, and dependency tracking
- **Source**: `ant-source-code-main/Task.ts`, `ant-source-code-main/tasks/`
- **Effort**: 4 hours

### 1.4 Conversation History (from ant-source history.ts)
- [ ] `src/state/conversation_history.py` — Searchable conversation history
- [ ] Add fuzzy search, filtering by topic/agent/time
- [ ] Integrate with memory system for context-aware retrieval
- **Source**: `ant-source-code-main/history.ts`
- **Effort**: 3 hours

### 1.5 Request Recording/Replay (from ant-source vcr.ts)
- [ ] `src/intelligence/request_recorder.py` — API request recording
- [ ] Enable replay for debugging, testing, and conversation reconstruction
- [ ] Add privacy controls (redact sensitive data)
- **Source**: `ant-source-code-main/services/vcr.ts`
- **Effort**: 3 hours

**Success criteria**: All 5 components implemented, tested, integrated.

---

## Phase 2: Memory Revolution (Week 2-4) — "From Storage to Intelligence"

**Goal**: Transform memory system from search engine to cognitive intelligence.

### 2.1 Observer/Reflector Pattern (from Mastra OM — 94.87% LongMemEval)
- [ ] `src/memory/observer.py` — Background agent watches conversations
- [ ] `src/memory/reflector.py` — Background agent reviews observations
- [ ] Convert raw messages → dense observations → drop raw messages
- [ ] Stable, cacheable context windows (no per-turn retrieval)
- **Research**: Mastra Observational Memory
- **Effort**: 6 hours

### 2.2 Adaptive Forgetting (from FadeMem — 45% storage reduction)
- [ ] Enhance `src/memory/memory_freshness.py` with FadeMem decay
- [ ] Dual-layer memory hierarchy (active vs archive)
- [ ] Exponential decay modulated by: semantic relevance, access frequency, temporal age
- [ ] Automatic archival of low-score memories
- **Research**: FadeMem (arXiv:2601.18642)
- **Effort**: 4 hours

### 2.3 Multi-Graph Architecture (from MAGMA — UT Dallas)
- [ ] Split `src/memory/knowledge_graph.py` into 4 orthogonal graphs:
  - **Semantic Graph**: Concept relationships, topic clustering
  - **Temporal Graph**: Event timelines, session sequences
  - **Causal Graph**: Cause-effect relationships, decision chains
  - **Entity Graph**: Projects, technologies, people, files
- [ ] Add BFS/DFS multi-hop traversal (2-3 hops)
- [ ] Policy-guided graph selection based on query intent
- **Research**: MAGMA (arXiv:2601.03236)
- **Effort**: 8 hours

### 2.4 Memory Reconsolidation (from HiMem — hierarchical self-evolution)
- [ ] Enhance `src/memory/sleep_engine.py` with reconsolidation
- [ ] When retrieved memory conflicts with new info → auto-revise
- [ ] Conflict detection via semantic similarity + temporal ordering
- [ ] Revision logging (track what changed and why)
- **Research**: HiMem (arXiv:2601.06377)
- **Effort**: 4 hours

### 2.5 Relational Versioning (from Supermemory)
- [ ] Add `updates/extends/derives` relationship types to knowledge graph
- [ ] Handle contradictions explicitly ("My favorite color is now Green")
- [ ] Dual-layer temporal grounding: `documentDate` + `eventDate`
- **Research**: Supermemory
- **Effort**: 3 hours

### 2.6 Trust-Aware Retrieval (from Membrane)
- [ ] `src/memory/trust_scorer.py` — Score memories by competence/trust
- [ ] Track memory source reliability
- [ ] Decay trust for unverified memories
- [ ] Boost trust for user-confirmed memories
- **Research**: Membrane
- **Effort**: 3 hours

**Success criteria**: Memory system scores 90%+ on LongMemEval benchmark.

---

## Phase 3: Hybrid LLM Orchestration (Week 4-6) — "Local-First, Cloud-Fallback"

**Goal**: Implement cutting-edge hybrid LLM routing with local models as primary.

### 3.1 Local Model Integration
- [ ] `src/model_router/local_models.py` — Ollama model management
- [ ] Support: Llama 3.2 (1B/3B/8B), Mistral (7B), Phi-3 (3.8B), Gemma (2B/7B)
- [ ] Auto-download, auto-update, health monitoring
- [ ] VRAM management with automatic model swapping
- **Effort**: 6 hours

### 3.2 Hybrid Routing Strategy
- [ ] `src/model_router/hybrid_router.py` — Local-first, cloud-fallback routing
- [ ] Decision matrix:
  - **Simple tasks** → Local small model (Llama 3.2 3B)
  - **Complex reasoning** → Local medium model (Llama 3.2 8B)
  - **Creative tasks** → Cloud model (OpenCode Zen)
  - **Fallback** → Next available model in priority chain
- [ ] Cost-aware routing (prefer local when quality is sufficient)
- **Effort**: 6 hours

### 3.3 Model Optimization (from docs model-optimization.md)
- [ ] `src/model_router/model_optimizer.py` — Dynamic model selection
- [ ] Track per-model performance on task types
- [ ] Auto-tune temperature, top_p, max_tokens per task
- [ ] Implement speculative decoding for faster local inference
- **Source**: `N-Xyme_MIND_Docs/model-optimization.md`
- **Effort**: 6 hours

### 3.4 Context Window Management
- [ ] `src/intelligence/context_manager.py` — Intelligent context handling
- [ ] Implement sliding window with priority retention
- [ ] Add context compression for long conversations
- [ ] Support chunked context for large codebases
- **Effort**: 4 hours

### 3.5 Speculative Decoding
- [ ] `src/model_router/speculative_decode.py` — Fast local inference
- [ ] Use small model to draft, large model to verify
- [ ] 2-3x speedup for local model inference
- **Effort**: 4 hours

**Success criteria**: 80% of tasks handled locally, 20% cloud fallback, 50% cost reduction.

---

## Phase 4: Self-Improving Learning (Week 6-8) — "System That Learns"

**Goal**: Transform learning system from feedback loops to true self-improvement.

### 4.1 Cross-Session Transfer
- [ ] `src/learning/cross_session_transfer.py` — Learn from past sessions
- [ ] Extract decisions and outcomes from completed sessions
- [ ] Generalize to principles applicable to future sessions
- [ ] Store as global-scoped memories for all agents
- **Effort**: 4 hours

### 4.2 Delegation Learning Enhancement
- [ ] Enhance `src/intelligence/` with learned routing patterns
- [ ] Track which agents perform best on which task types
- [ ] Auto-adjust routing weights based on outcomes
- [ ] Implement A/B testing for routing strategies
- **Effort**: 4 hours

### 4.3 Self-Healing (from docs Layer4-Self-Healing)
- [ ] `src/healing/self_healing.py` — Automatic error recovery
- [ ] Detect recurring errors and apply fixes
- [ ] Learn from past fixes to prevent future errors
- [ ] Implement circuit breaker patterns for failing components
- **Source**: `N-Xyme_MIND_Docs/Layer4-Self-Healing-Implementation.md`
- **Effort**: 6 hours

### 4.4 Agent Orchestration Enhancement (from docs Layer5)
- [ ] `src/orchestration/agent_orchestration.py` — Advanced agent coordination
- [ ] Implement swarm patterns for complex tasks
- [ ] Add agent-to-agent communication protocol
- [ ] Implement task decomposition and parallel execution
- **Source**: `N-Xyme_MIND_Docs/Layer5-Agent-Orchestration.md`
- **Effort**: 6 hours

### 4.5 Planning/Reasoning (from docs LAYER10)
- [ ] `src/orchestration/planning_reasoning.py` — Advanced planning
- [ ] Implement multi-step planning with dependency tracking
- [ ] Add reasoning chains for complex decisions
- [ ] Implement plan validation and adjustment
- **Source**: `N-Xyme_MIND_Docs/LAYER10-PLANNING-REASONING.md`
- **Effort**: 6 hours

**Success criteria**: System improves routing accuracy by 20% over 30 days.

---

## Phase 5: Multi-Modal & Infrastructure (Week 8-12) — "Beyond Text"

**Goal**: Extend system to handle images, audio, code, and distributed operation.

### 5.1 Multi-Modal Memory (from MemVerse)
- [ ] `src/memory/multimodal.py` — Image/audio/code memory
- [ ] Image: CLIP embeddings + OCR + description
- [ ] Audio: Whisper transcription + embedding
- [ ] Code: CodeBERT embeddings + syntax analysis
- [ ] Unified retrieval across all modalities
- **Research**: MemVerse (arXiv:2512.03627)
- **Effort**: 8 hours

### 5.2 Voice Prompt Pipeline (from docs)
- [ ] `src/voice/pipeline.py` — Voice input processing
- [ ] Speech-to-text (Whisper local)
- [ ] Voice command recognition
- [ ] Audio response synthesis (optional)
- **Source**: `N-Xyme_MIND_Docs/voice-prompt-pipeline.md`
- **Effort**: 6 hours

### 5.3 Multi-Drive Scanner (from docs unified-pc-memory)
- [ ] `src/memory/multi_drive_scanner.py` — Scan all mounted drives
- [ ] Content extraction: code, PDF, DOCX, Markdown
- [ ] Incremental sync with watchdog
- [ ] Integration with memory router
- **Source**: `N-Xyme_MIND_Docs/unified-pc-memory.md`
- **Effort**: 8 hours

### 5.4 Distributed Memory Sync
- [ ] `src/memory/distributed_sync.py` — Cross-instance memory sync
- [ ] Event-sourced sync with conflict resolution
- [ ] Vector clock-based consistency
- [ ] Offline-first with sync on reconnect
- **Effort**: 8 hours

### 5.5 Context Virtualization (from OMEGA)
- [ ] `src/state/context_virtualization.py` — Checkpoint/resume
- [ ] Serialize session state for later resumption
- [ ] Auto-capture hooks for decisions and errors
- [ ] Cross-instance state transfer
- **Research**: OMEGA Memory
- **Effort**: 4 hours

**Success criteria**: Multi-modal memory with image/code/audio support. Distributed sync across instances.

---

## Phase 6: Production Excellence (Week 12-16) — "Industry Gold Standard"

**Goal**: Achieve production-ready status with monitoring, security, and performance.

### 6.1 Observability Stack
- [ ] Structured logging (structlog) across all modules
- [ ] Metrics endpoint (Prometheus-compatible)
- [ ] Distributed tracing (OpenTelemetry)
- [ ] Alerting for critical failures
- **Effort**: 6 hours

### 6.2 Performance Optimization
- [ ] Connection pooling for SQLite
- [ ] Caching layer for embedding engine
- [ ] Query result caching
- [ ] Lazy loading for large modules
- **Effort**: 4 hours

### 6.3 Security Hardening
- [ ] Input validation framework for all MCP tool arguments
- [ ] Credential rotation for VPN providers
- [ ] Sandbox escape prevention for agent bash access
- [ ] Rate limiting on all internal APIs
- **Effort**: 6 hours

### 6.4 Backup & Disaster Recovery
- [ ] Automated daily backup of all databases
- [ ] Backup rotation (7 daily, 4 weekly, 12 monthly)
- [ ] Restore procedure documented and tested
- [ ] Backup verification (checksum validation)
- **Effort**: 4 hours

### 6.5 API Documentation
- [ ] OpenAPI/Swagger spec for `src/api/` endpoints
- [ ] MCP tool documentation (auto-generated from schemas)
- [ ] Architecture decision records (ADRs)
- **Effort**: 4 hours

### 6.6 Docker Compose for Local Development
- [ ] Dockerfile for main application
- [ ] docker-compose.yml with all services
- [ ] Local development environment orchestration
- **Effort**: 4 hours

**Success criteria**: Production-ready with monitoring, security, and disaster recovery.

---

## Implementation Priority (ROI Ranking)

| Priority | Component | Effort | Impact | ROI | Phase |
|:---:|---|:---:|:---:|:---:|:---:|
| 1 | Token Estimation | 2h | 🔴 High | 🔴 | 1 |
| 2 | Context Compaction | 3h | 🔴 High | 🔴 | 1 |
| 3 | Task Lifecycle | 4h | 🔴 High | 🔴 | 1 |
| 4 | Observer/Reflector | 6h | 🔴 Critical | 🔴 | 2 |
| 5 | Adaptive Forgetting | 4h | 🔴 High | 🔴 | 2 |
| 6 | Multi-Graph Architecture | 8h | 🟠 High | 🟡 | 2 |
| 7 | Local Model Integration | 6h | 🔴 Critical | 🔴 | 3 |
| 8 | Hybrid Routing | 6h | 🔴 Critical | 🔴 | 3 |
| 9 | Memory Reconsolidation | 4h | 🟠 High | 🟡 | 2 |
| 10 | Cross-Session Transfer | 4h | 🟠 High | 🟡 | 4 |
| 11 | Self-Healing | 6h | 🟠 High | 🟡 | 4 |
| 12 | Multi-Modal Memory | 8h | 🟢 Medium | 🟢 | 5 |
| 13 | Voice Pipeline | 6h | 🟢 Medium | 🟢 | 5 |
| 14 | Distributed Sync | 8h | 🟢 Medium | 🟢 | 5 |
| 15 | Observability Stack | 6h | 🟡 Medium | 🟡 | 6 |

---

## Success Metrics

| Metric | Current | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Phase 6 |
|--------|---------|---------|---------|---------|---------|---------|---------|
| Tests | 691 | 750 | 800 | 850 | 900 | 950 | 1000+ |
| Memory sources | 5 | 5 | 5 | 5 | 6 | 8+ | 8+ |
| Memory types | 4 (raw) | 4 (raw) | 4×4 (hierarchical) | 4×4 | 4×4 | 4×4 | 4×4 |
| Knowledge graphs | 1 | 1 | 4 | 4 | 4 | 4 | 4 |
| Local model support | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Hybrid routing | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Multi-modal | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Self-healing | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Distributed sync | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Observability | Basic | Basic | Basic | Basic | Basic | ✅ | ✅ |
| LongMemEval score | ~70% | ~75% | ~90% | ~90% | ~92% | ~94% | ~95% |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| LLM cost explosion | Local-first routing, batch aggressively, rate-limit to daemon-only |
| Graph bloat | Auto-dedup with weekly `suggest_merges()` at 0.85 threshold |
| Consolidation loss | Always keep `source_ids`, support `expand(summary_id)` |
| Model compatibility | Abstract model interface, test with multiple providers |
| Memory corruption | Regular backups, checksum validation, migration rollback |
| Performance degradation | Connection pooling, caching, lazy loading, monitoring |

---

## Quick Wins (Week 1) — Zero New Code

These can be done immediately with existing code:

1. **Wire forgetting.py** into router.py retention pipeline (exists but not integrated)
2. **Enable learning adapter re-ranking** by default in router.py (exists but minimal usage)
3. **Activate preference_model.py** in re-ranking pipeline (exists but unused)
4. **Integrate sleep_cycle.py** for background memory processing (exists but not wired)
5. **Add KG relationship scoring** based on frequency (simple enhancement)

**Expected impact**: 15% improvement in retrieval quality, 20% reduction in noise.

---

## Execution Strategy

### Parallel Work Streams
```
Stream A (Foundation):     Phase 1.1 → 1.2 → 1.3 → 1.4 → 1.5
Stream B (Memory):         Phase 2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6
Stream C (LLM Routing):    Phase 3.1 → 3.2 → 3.3 → 3.4 → 3.5
Stream D (Learning):       Phase 4.1 → 4.2 → 4.3 → 4.4 → 4.5
Stream E (Infrastructure): Phase 5.1 → 5.2 → 5.3 → 5.4 → 5.5
Stream F (Production):     Phase 6.1 → 6.2 → 6.3 → 6.4 → 6.5 → 6.6
```

### Dependencies
- Phase 1 must complete before Phase 2 (foundation required for memory revolution)
- Phase 2 must complete before Phase 3 (memory intelligence required for hybrid routing)
- Phase 3 must complete before Phase 4 (local models required for self-improvement)
- Phase 4 must complete before Phase 5 (learning required for multi-modal)
- Phase 5 must complete before Phase 6 (infrastructure required for production)

---

## Final Vision

**N-Xyme_MIND v2.0**: The most cutting-edge local hybrid LLM orchestration platform.

- **Local-first**: 80% of tasks handled locally, 20% cloud fallback
- **Self-improving**: System learns from every interaction, gets smarter over time
- **Multi-modal**: Text, code, images, audio — all searchable and retrievable
- **Distributed**: Sync across multiple instances, offline-first
- **Production-ready**: Monitoring, security, disaster recovery
- **Zero API key dependency**: Works entirely with local models, cloud is optional
- **Industry gold standard**: 95%+ LongMemEval score, 1000+ tests, 0 security vulns

**This is not just an upgrade — it's a transformation from a smart search engine to a cognitive intelligence system.**
