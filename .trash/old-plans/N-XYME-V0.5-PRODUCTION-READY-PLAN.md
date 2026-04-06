# N-Xyme MIND v0.5 — Production-Ready Core Plan

> **Philosophy**: "Transition from prototype to production-ready system."
> **Status**: DEPENDS ON v0.3
> **Timeline**: 8-12 sessions
> **Inspired by**: Mem0 v1.0 (full memory), NeMo Guardrails (security), TurboQuant (compression)

---

## 1. EXECUTIVE SUMMARY

v0.5 represents the transition from prototype to production-ready system. This phase adds security, scaling infrastructure, and advanced memory features. The agent becomes suitable for non-critical production workloads.

**What v0.5 Adds**:
- Full memory system (knowledge graph, vector index, forgetting, compaction, dream, crypto)
- Self-learning (skill lifecycle, prompt evolution)
- Security layer (sandbox, jailbreak detection, permissions, guardrails)
- Runtime (lifecycle manager)
- Temporal planning
- Compression (token compressor, KV cache)
- Full MCP servers (eval-harness-mcp)

**What v0.5 Excludes**:
- No runtime containerization (Podman/Firecracker)
- No tool synthesis
- No full infrastructure automation

---

## 2. LAYERS INCLUDED (NEW + ENHANCED)

### L2: Memory System (Full)
| File | Status | Description |
|------|--------|-------------|
| `src/memory/core/knowledge_graph.py` | NEW | Entities→Relations→Properties |
| `src/memory/core/vector_index.py` | NEW | Hybrid BM25 + semantic with RRF |
| `src/memory/core/forgetting.py` | NEW | Ebbinghaus decay |
| `src/memory/core/compaction.py` | ENHANCE | Full session summarization |
| `src/memory/core/dream_consolidate.py` | NEW | LLM creative recombination |
| `src/memory/core/crypto_identity.py` | NEW | Ed25519 signing |
| `src/memory/core/sleep_cycle.py` | ENHANCE | Activate (was stub) |
| `src/memory/core/hierarchical.py` | ENHANCE | Full 4-tier (was session-only) |
| `src/memory/core/dossier_system.py` | ENHANCE | Full causal chains |

### L3: Self-Learning (Core)
| File | Status | Description |
|------|--------|-------------|
| `src/learning/skill_lifecycle.py` | NEW | Proposed→Experimental→Active→Deprecated→Archived |
| `src/learning/prompt_evolution.py` | NEW | Generate→Critique→Refine→Evaluate |
| `src/learning/self_learning.py` | NEW | Track outcomes → Extract patterns → Adapt |

### L7: Security (Core)
| File | Status | Description |
|------|--------|-------------|
| `src/security/agent_sandbox.py` | NEW | Kernel-enforced sandbox |
| `src/security/jailbreak_detector.py` | NEW | Perplexity-based detection |
| `src/security/permission_system.py` | NEW | Slowmist-style input handling |
| `src/security/output_guardrails.py` | NEW | OWASP-aligned validation |

### L9: Runtime (Basic)
| File | Status | Description |
|------|--------|-------------|
| `src/runtime/lifecycle_manager.py` | NEW | tmux-based lifecycle |
| `src/runtime/container_manager.py` | DEFERRED | v1.0 |
| `src/runtime/microvm_runtime.py` | DEFERRED | v1.0 |

### L10: Planning (Enhanced)
| File | Status | Description |
|------|--------|-------------|
| `src/planning/temporal_planner.py` | NEW | Durable execution |

### L11: Compression (Core)
| File | Status | Description |
|------|--------|-------------|
| `src/compression/token_compressor.py` | NEW | kompact patterns (40-70% savings) |
| `src/compression/kv_cache_manager.py` | NEW | AitherKVCache + TurboQuant |
| `src/compression/context_distiller.py` | NEW | Claw Compactor integration |

### L6: MCP Servers (Enhanced)
| Server | Status | Description |
|--------|--------|-------------|
| `packages/eval-harness-mcp/` | NEW | Quality gates + regression detection |

---

## 3. IMPLEMENTATION TASKS

### W1: Full Memory System (2-3 sessions)
| Task | File | Agent | Category | QA |
|------|------|-------|----------|-----|
| W1-T1 | Enhance `hierarchical.py` | Hephaestus | ultrabrain | Full 4-tier memory |
| W1-T2 | `knowledge_graph.py` | Hephaestus | deep | CRUD + temporal queries |
| W1-T3 | `vector_index.py` | Hephaestus | deep | Hybrid search + RRF |
| W1-T4 | `forgetting.py` | Hephaestus | ultrabrain | Ebbinghaus curve |
| W1-T5 | Enhance `compaction.py` | Hephaestus | deep | Full summarization |
| W1-T6 | `dream_consolidate.py` | Hephaestus | deep | Creative recombination |
| W1-T7 | `crypto_identity.py` | Hephaestus | deep | Ed25519 signing |
| W1-T8 | Enhance `sleep_cycle.py` | Hephaestus | deep | Activate cycle |
| W1-T9 | Enhance `dossier_system.py` | Hephaestus | deep | Full causal chains |

### W2: Self-Learning (1-2 sessions)
| Task | File | Agent | Category | QA |
|------|------|-------|----------|-----|
| W2-T1 | `skill_lifecycle.py` | Hephaestus | deep | State machine works |
| W2-T2 | `prompt_evolution.py` | Hephaestus | deep | Evolution works |
| W2-T3 | `self_learning.py` | Hephaestus | deep | Learning works |

### W3: Security (2 sessions)
| Task | File | Agent | Category | QA |
|------|------|-------|----------|-----|
| W3-T1 | `agent_sandbox.py` | Hephaestus | deep | Sandbox enforced |
| W3-T2 | `jailbreak_detector.py` | Hephaestus | deep | Detection works |
| W3-T3 | `permission_system.py` | Hephaestus | deep | Permissions work |
| W3-T4 | `output_guardrails.py` | Hephaestus | deep | Guardrails enforced |

### W4: Runtime + Planning + Compression (2 sessions)
| Task | File | Agent | Category | QA |
|------|------|-------|----------|-----|
| W4-T1 | `lifecycle_manager.py` | Hephaestus | deep | Lifecycle works |
| W4-T2 | `temporal_planner.py` | Hephaestus | deep | Temporal planning works |
| W4-T3 | `token_compressor.py` | Hephaestus | deep | 40-70% savings |
| W4-T4 | `kv_cache_manager.py` | Hephaestus | ultrabrain | TurboQuant works |
| W4-T5 | `context_distiller.py` | Hephaestus | deep | Distillation works |

### W5: MCP Enhancement (1 session)
| Task | File | Agent | Category | QA |
|------|------|-------|----------|-----|
| W5-T1 | `packages/eval-harness-mcp/` | Hephaestus | deep | Quality gates work |

---

## 4. TESTING STRATEGY

### Unit Tests (50 tests)
| Layer | Test Count | Description |
|-------|------------|-------------|
| L2 Memory (Full) | 15 | Knowledge graph, vector search, forgetting |
| L3 Self-Learning | 10 | Skill lifecycle, prompt evolution |
| L7 Security | 10 | Sandbox, jailbreak, permissions, guardrails |
| L9 Runtime | 5 | Lifecycle management |
| L10 Planning | 5 | Temporal planning |
| L11 Compression | 5 | Token compression, KV cache |

### Integration Tests (15 tests — NEW)
| Test | Description |
|------|-------------|
| Memory consolidation | sleep_cycle → forgetting → compaction |
| Self-learning loop | skill_lifecycle → prompt_evolution → self_learning |
| Security pipeline | sandbox → jailbreak → permissions → guardrails |
| Compression flow | token compress → KV cache → distill |
| MCP eval | eval-harness-mcp quality gates |

### Success Criteria
- [ ] Agent passes security benchmark
- [ ] Memory recall accuracy > 85%
- [ ] Handles 5+ concurrent sessions
- [ ] Token compression achieves 40-70% savings
- [ ] 199 tests passing (119 v0.3 + 50 unit + 15 integration + 15 existing)

---

## 5. DEPENDENCIES

```
v0.3 Complete ──► W1 (Full Memory) ──► W2 (Self-Learning) ──► W3 (Security) ──► W4 (Runtime+Planning+Compression) ──► W5 (MCP)
```

---

## 6. QUALITY GATES

| Gate | v0.5 |
|------|------|
| Gate 1: Type Check | ✓ |
| Gate 2: Lint | ✓ |
| Gate 3: Tests | ✓ (199 tests) |
| Gate 4: Coverage | 80% |
| Gate 5: Secrets | ✓ |
| Gate 6: Placeholders | ✓ |

---

## 7. ATOMIC COMMIT STRATEGY

| Commit | Message | Files |
|--------|---------|-------|
| 0 | `feat(memory): implement full memory system (v0.5)` | 9 L2 files |
| 1 | `feat(learning): implement self-learning (v0.5)` | 3 L3 files |
| 2 | `feat(security): implement security layer (v0.5)` | 4 L7 files |
| 3 | `feat(runtime): implement lifecycle manager (v0.5)` | 1 L9 file |
| 4 | `feat(planning): add temporal planner (v0.5)` | 1 L10 file |
| 5 | `feat(compression): implement compression layer (v0.5)` | 3 L11 files |
| 6 | `feat(mcp): add eval-harness-mcp (v0.5)` | eval-harness-mcp |
| 7 | `test: add tests for v0.5` | 65 tests |
| 8 | `chore: run quality gates, tag v0.5.0` | Various |

---

## 8. RISK MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Memory complexity explosion | HIGH | HIGH | Start with SQLite, add vector later |
| Security false positives | Medium | Medium | Tunable thresholds |
| Session limit hit | HIGH | Medium | Checkpoint after each wave |
| Compression breaks context | Medium | HIGH | Validate after compression |

---

*v0.5 Production-Ready Core Plan — Suitable for non-critical production*
*8-12 sessions | 22 tasks | ~22 new files | 65 new tests*
