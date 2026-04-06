# N-Xyme MIND v1.0 — REVISED ULTIMATE MASTER PLAN

> **Philosophy**: "Stitch together what works from ALL sources, discard what failed."
> **Status**: ALL REVIEWS ADDRESSED — Oracle (7.1/10), Metis (24 issues), Momus (10 attacks) — FIXED
> **Research**: 4 rounds, 32+ agents, ~280+ patterns, 100+ repos
> **Reviews**: Metis (47 gaps) + Momus (47 issues) + Oracle (6 issues) + 5 Cross-Checks — ALL ADDRESSED

---

## 1. EXECUTIVE SUMMARY

| Metric | Original | REVISED |
|--------|----------|---------|
| **Total Phases** | 7 (P0-P6) | 7 (P0-P6) |
| **Total Waves** | 6 | 8 (Wave 3 split into 3a/3b/3c) |
| **Total Tasks** | 88 | 93 (+5 integration tasks) |
| **Total Files** | ~60 new, ~15 enhanced | ~60 new, ~15 enhanced |
| **Total Tests** | 190 | 215 (+25 integration/E2E) |
| **Estimated Sessions** | 18-24 (UNREALISTIC) | **35-45** (REALISTIC) |
| **Critical Path** | P0→L1→L2→L4→L5→L9→L13 | P0→L1→L2→L3→L4→L5→L9→L13 |
| **Parallel Speedup** | ~60% | ~65% (improved wave splitting) |

### Key Revisions from Reviews
| Issue | Fix Applied |
|-------|-------------|
| Session 50-limit death | ✅ Automated checkpoint after EVERY task |
| E2E testing insufficient | ✅ Expanded from 10 to 25+ tests |
| Timeline unrealistic | ✅ Revised to 35-45 sessions |
| Missing conftest.py | ✅ Added to P0 with MockLLM fixtures |
| No integration contracts | ✅ Added cross-layer contract document |
| Wave 3 bottleneck | ✅ Split into 3a/3b/3c sub-waves |
| MCP health monitoring | ✅ Added to L4 self-healing |
| No mock strategy | ✅ Added MockLLM + fixtures |
| Quality gate P0 errors | ✅ Fixed P0 gate schedule |
| Scope too ambitious | ✅ Phased v0.1→v0.2→v1.0 approach |

### Agent Delegation Model
| Role | Agent | Category/Type | Model |
|------|-------|---------------|-------|
| Orchestrator | Sisyphus | — | qwen3.6-plus-free (high) |
| Implementation | Hephaestus | category: deep | qwen3.6-plus-free (medium) |
| Complex Logic | Hephaestus | category: ultrabrain | qwen3.6-plus-free (high) |
| Architecture Review | Oracle | subagent_type: oracle | minimax-m2.5-free |
| Adversarial Review | Momus | subagent_type: momus | qwen3.6-plus-free (high) |
| Research | Explore/Librarian | subagent_type | minimax-m2.5-free |
| Light Tasks | Sisyphus-Junior | category: quick | minimax-m2.5-free |

### Skill Loading Rules (NEW from Metis)
| Task Type | Skills to Load |
|-----------|----------------|
| Git operations | `load_skills=['git-master']` |
| Browser/verification | `load_skills=['playwright']` |
| UI/UX tasks | `load_skills=['frontend-ui-ux']` |
| All other tasks | `load_skills=[]` |

---

## 2. PRE-IMPLEMENTATION WAVE (P0) — REVISED

| Task | Description | Agent | Category | Skills | QA |
|------|-------------|-------|----------|--------|-----|
| P0-T1 | Create conftest.py with MockLLM fixtures | Hephaestus | quick | [] | pytest --collect-only works |
| P0-T2 | Verify quality gate scripts (6 gates) | Hephaestus | quick | [] | All 6 scripts exit 0 |
| P0-T3 | Verify pyproject.toml dependencies | Hephaestus | quick | [] | pip install -e . succeeds |
| P0-T4 | Verify storage layer (SQLite + vector) | Hephaestus | quick | [] | SQLite created, vector initialized |
| P0-T5 | Create L1 test scaffolding | Hephaestus | deep | [] | Test imports pass |
| P0-T6 | Create integration test scaffolding | Hephaestus | deep | [] | Integration test imports pass |
| P0-T7 | Create MockLLM + fixtures for all layers | Hephaestus | deep | [] | MockLLM works in tests |

**Quality Gates for P0**: Gate 1 ✓, Gate 2 ✓, Gate 3 SKIP, Gate 4 SKIP, Gate 5 ✓, Gate 6 ✓

---

## 3. COMPLETE FILE INVENTORY (UNCHANGED)

### LAYER 1: Core Foundation (5 files)
| File | Status | Description |
|------|--------|-------------|
| `src/nxyme/core/governance.py` | NEW | 7-Layer AI Governance + EU AI Act + Triple-Lock + Doom Loop |
| `src/nxyme/core/sentinel.py` | NEW | Protocol 420 + K8s liveness/readiness probes + lifecycle state machine |
| `src/nxyme/core/flight_recorder.py` | NEW | HMAC-chained JSONL audit trail (SOC 2) |
| `src/nxyme/core/skill_telemetry.py` | NEW | OpenTelemetry + dead skill detection (30-day) |
| `src/nxyme/core/delta_manifest.py` | NEW | SHA-256 content hashing + versioned workspace |

### LAYER 2: Memory System (9 files)
| File | Status | Description |
|------|--------|-------------|
| `src/memory/core/hierarchical.py` | NEW | Working→Episodic→Semantic→Archival (MemGPT) |
| `src/memory/core/knowledge_graph.py` | NEW | Entities→Relations→Properties (Graphiti) |
| `src/memory/core/vector_index.py` | NEW | Hybrid BM25 + semantic with RRF reranking |
| `src/memory/core/sleep_cycle.py` | NEW | JOURNAL→CONSOLIDATE→RECALL (smysle/agent-memory) |
| `src/memory/core/forgetting.py` | NEW | Ebbinghaus decay R=e^(-t/S) |
| `src/memory/core/compaction.py` | NEW | Session summarization (Claw Compactor) |
| `src/memory/core/dossier_system.py` | NEW | Causal chain summaries (HMLR) |
| `src/memory/core/dream_consolidate.py` | NEW | LLM creative recombination (ENGRAM) |
| `src/memory/core/crypto_identity.py` | NEW | Ed25519 signing + memory transplant (ENGRAM) |

### LAYER 3: Self-Learning (3 files)
| File | Status | Description |
|------|--------|-------------|
| `src/learning/skill_lifecycle.py` | NEW | Proposed→Experimental→Active→Deprecated→Archived (NOVEL) |
| `src/learning/prompt_evolution.py` | NEW | Generate→Critique→Refine→Evaluate (PromptWizard) |
| `src/learning/self_learning.py` | NEW | Track outcomes → Extract patterns → Adapt |

### LAYER 4: Self-Healing (5 files — +1 MCP health)
| File | Status | Description |
|------|--------|-------------|
| `src/healing/health_monitor.py` | ENHANCE | Move from src/health_monitor.py + composite scoring + MCP health |
| `src/healing/self_healer.py` | ENHANCE | Move from src/self_healer.py + circuit breaker |
| `src/healing/auto_recovery.py` | NEW | 4-tier graceful degradation (openclaw) + MCP recovery |
| `src/healing/checkpoint_resume.py` | NEW | LangGraph-style state persistence |
| `src/healing/mcp_health.py` | NEW | MCP server health monitoring + circuit breakers |

### LAYER 5: Agent Orchestration (5 files)
| File | Status | Description |
|------|--------|-------------|
| `src/orchestration/sisyphus.py` | NEW | Plan executor + resilience middleware |
| `src/orchestration/prometheus.py` | NEW | Plan builder + validator + optimizer |
| `src/orchestration/hephaestus.py` | NEW | Implementation agent + progress tracker |
| `src/orchestration/a2a_protocol.py` | NEW | Google A2A Agent Cards + task delegation |
| `src/orchestration/network_orchestrator.py` | NEW | CrewAI hierarchical + fan-out parallel |

### LAYER 6: MCP Servers (5 servers)
| Server | Status | Description |
|--------|--------|-------------|
| `packages/athena-context-mcp/` | ENHANCE | 7 tools — Enhance existing bare package |
| `packages/nx-mind-mcp/` | ENHANCE | 7 tools — Enhance existing bare package |
| `packages/trigger-guardian-mcp/` | ENHANCE | 6 tools — Enhance existing bare package |
| `packages/memory-mcp/` | NEW | Full memory operations (NEW package) |
| `packages/eval-harness-mcp/` | NEW | Quality gates + regression detection (NEW package) |

### LAYER 7: Security (4 files)
| File | Status | Description |
|------|--------|-------------|
| `src/security/agent_sandbox.py` | NEW | Kernel-enforced sandbox (nono) |
| `src/security/jailbreak_detector.py` | NEW | Perplexity-based detection (PIGuard) |
| `src/security/permission_system.py` | NEW | Slowmist-style untrusted input handling |
| `src/security/output_guardrails.py` | NEW | OWASP-aligned validation |

### LAYER 8: Testing & Debugging (3 files)
| File | Status | Description |
|------|--------|-------------|
| `src/testing/agent_tracer.py` | NEW | strace for agents |
| `src/testing/test_harness.py` | NEW | claw-eval patterns |
| `src/testing/regression_detector.py` | NEW | agent-vcr time-travel |

### LAYER 9: Runtime & Execution (3 files)
| File | Status | Description |
|------|--------|-------------|
| `src/runtime/container_manager.py` | NEW | Podman isolation (kapsis) |
| `src/runtime/microvm_runtime.py` | NEW | Firecracker (arcbox) |
| `src/runtime/lifecycle_manager.py` | NEW | tmux-based (agent-manager-skill) |

### LAYER 10: Planning & Reasoning (3 files)
| File | Status | Description |
|------|--------|-------------|
| `src/planning/htn_planner.py` | NEW | Hierarchical task networks (GTPyhop) |
| `src/planning/temporal_planner.py` | NEW | Durable execution (exoclaw-temporal) |
| `src/planning/goal_reasoning.py` | NEW | SELFGOAL patterns |

### LAYER 11: Compression & Optimization (3 files)
| File | Status | Description |
|------|--------|-------------|
| `src/compression/token_compressor.py` | NEW | kompact patterns (40-70% savings) |
| `src/compression/kv_cache_manager.py` | NEW | AitherKVCache + TurboQuant |
| `src/compression/context_distiller.py` | NEW | Claw Compactor integration |

### LAYER 12: Tool Synthesis (3 files)
| File | Status | Description |
|------|--------|-------------|
| `src/tools/tool_generator.py` | NEW | Runtime tool generation |
| `src/tools/tool_verifier.py` | NEW | ToolBrain patterns |
| `src/tools/tool_composer.py` | NEW | Toolathlon benchmark patterns |

### LAYER 13: Infrastructure (4 components)
| Component | Status | Description |
|-----------|--------|-------------|
| `vpn/rotator.py` | ENHANCE | 429-adaptive + weighted LB |
| `_bmad/` | ENHANCE | BMAD workflows + 46 skills |
| `bin/` | ENHANCE | CLI tools (nxyme-health, nxyme-backup, nxyme-logs) |
| `tests/` | EXPAND | 215 tests across all layers |

---

## 4. REVISED IMPLEMENTATION WAVES

### WAVE 1: Foundation (L1)
**Dependencies**: P0 complete
**Parallel Tasks**: 3 (T1-T3 deep), then 2 (T4-T5 quick)

| Task | File | Agent | Category | Skills | QA |
|------|------|-------|----------|--------|-----|
| W1-T1 | `src/nxyme/core/flight_recorder.py` | Hephaestus | deep | [] | Hash chain verifies, tamper detected |
| W1-T2 | `src/nxyme/core/governance.py` | Hephaestus | deep | [] | 7 layers evaluate, EU AI Act classifies |
| W1-T3 | `src/nxyme/core/sentinel.py` | Hephaestus | deep | [] | State machine transitions, probes respond |
| W1-T4 | `src/nxyme/core/skill_telemetry.py` | Hephaestus | quick | [] | OpenTelemetry traces, dead skills detected |
| W1-T5 | `src/nxyme/core/delta_manifest.py` | Hephaestus | quick | [] | Versioning works, snapshots create/restore |

### WAVE 2: Memory System (L2)
**Dependencies**: W1 complete + P0-T4 (storage layer)
**Parallel Tasks**: 6 (T1-T6), then 3 (T7-T9)

| Task | File | Agent | Category | Skills | QA |
|------|------|-------|----------|--------|-----|
| W2-T1 | `src/memory/core/hierarchical.py` | Hephaestus | ultrabrain | [] | 4 layers work, eviction correct |
| W2-T2 | `src/memory/core/knowledge_graph.py` | Hephaestus | deep | [] | Entities/relations CRUD, temporal queries |
| W2-T3 | `src/memory/core/vector_index.py` | Hephaestus | deep | [] | Hybrid search, RRF reranking |
| W2-T4 | `src/memory/core/sleep_cycle.py` | Hephaestus | deep | [] | JOURNAL→CONSOLIDATE→RECALL cycle |
| W2-T5 | `src/memory/core/forgetting.py` | Hephaestus | ultrabrain | [] | Ebbinghaus curve accurate |
| W2-T6 | `src/memory/core/compaction.py` | Hephaestus | deep | [] | Session summarization works |
| W2-T7 | `src/memory/core/dossier_system.py` | Hephaestus | deep | [] | Causal chain summaries work |
| W2-T8 | `src/memory/core/dream_consolidate.py` | Hephaestus | deep | [] | LLM creative recombination works |
| W2-T9 | `src/memory/core/crypto_identity.py` | Hephaestus | deep | [] | Ed25519 signing works |

### WAVE 2.5: Self-Learning (L3) — NEW SEPARATE WAVE
**Dependencies**: W2 complete (L2-T9 crypto_identity)
**Parallel Tasks**: 3

| Task | File | Agent | Category | Skills | QA |
|------|------|-------|----------|--------|-----|
| W2.5-T1 | `src/learning/skill_lifecycle.py` | Hephaestus | deep | [] | State machine transitions, evaluation tracking |
| W2.5-T2 | `src/learning/prompt_evolution.py` | Hephaestus | deep | [] | Generate→Critique→Refine→Evaluate works |
| W2.5-T3 | `src/learning/self_learning.py` | Hephaestus | deep | [] | Track outcomes → Extract patterns → Adapt |

### WAVE 3a: Self-Healing Core (L4-T1, L4-T2)
**Dependencies**: W1 (sentinel for health), W2 (memory for state)
**Parallel Tasks**: 2

| Task | File | Agent | Category | Skills | QA |
|------|------|-------|----------|--------|-----|
| W3a-T1 | `src/healing/health_monitor.py` | Hephaestus | deep | [] | Composite scoring 0-100 + MCP health |
| W3a-T2 | `src/healing/self_healer.py` | Hephaestus | deep | [] | Circuit breaker state transitions |

### WAVE 3b: Orchestration Core (L5-T1, L5-T2, L5-T3)
**Dependencies**: W3a-T2 complete
**Parallel Tasks**: 3

| Task | File | Agent | Category | Skills | QA |
|------|------|-------|----------|--------|-----|
| W3b-T1 | `src/orchestration/sisyphus.py` | Hephaestus | deep | [] | Plan executor works |
| W3b-T2 | `src/orchestration/prometheus.py` | Hephaestus | deep | [] | Plan builder works |
| W3b-T3 | `src/orchestration/hephaestus.py` | Hephaestus | deep | [] | Implementation agent works |

### WAVE 3c: Advanced Features (L4-T3, L4-T4, L4-T5, L5-T4, L5-T5)
**Dependencies**: W3a + W3b complete
**Parallel Tasks**: 5

| Task | File | Agent | Category | Skills | QA |
|------|------|-------|----------|--------|-----|
| W3c-T1 | `src/healing/auto_recovery.py` | Hephaestus | deep | [] | 4-tier degradation works |
| W3c-T2 | `src/healing/checkpoint_resume.py` | Hephaestus | deep | [] | State persistence works |
| W3c-T3 | `src/healing/mcp_health.py` | Hephaestus | deep | [] | MCP health monitoring works |
| W3c-T4 | `src/orchestration/a2a_protocol.py` | Hephaestus | deep | [] | Agent Cards, task delegation |
| W3c-T5 | `src/orchestration/network_orchestrator.py` | Hephaestus | ultrabrain | [] | Hierarchical + parallel execution |

### WAVE 4: MCP + Security (L6 + L7)
**Dependencies**: W1 (governance for auth), W2 (memory for memory-mcp), W3c (orchestration)
**Parallel Tasks**: 5 (L6-T1-L6-T3), then 2 (L6-T4-L6-T5), then 4 (L7-T1-L7-T4)

| Task | File | Agent | Category | Skills | QA |
|------|------|-------|----------|--------|-----|
| W4-T1 | `packages/athena-context-mcp/` | Hephaestus | deep | [] | 7 tools respond correctly |
| W4-T2 | `packages/nx-mind-mcp/` | Hephaestus | deep | [] | 7 tools respond correctly |
| W4-T3 | `packages/trigger-guardian-mcp/` | Hephaestus | deep | [] | 6 tools respond correctly |
| W4-T4 | `packages/memory-mcp/` | Hephaestus | deep | [] | Memory operations work |
| W4-T5 | `packages/eval-harness-mcp/` | Hephaestus | deep | [] | Quality gates work |
| W4-T6 | `src/security/agent_sandbox.py` | Hephaestus | deep | [] | Sandbox enforced |
| W4-T7 | `src/security/jailbreak_detector.py` | Hephaestus | deep | [] | Perplexity detection works |
| W4-T8 | `src/security/permission_system.py` | Hephaestus | deep | [] | Permission system works |
| W4-T9 | `src/security/output_guardrails.py` | Hephaestus | deep | [] | Guardrails enforced |

### WAVE 5: Testing + Runtime + Planning (L8 + L9 + L10)
**Dependencies**: W3c (orchestration for runtime), W4 (security for testing)
**Parallel Tasks**: 6

| Task | File | Agent | Category | Skills | QA |
|------|------|-------|----------|--------|-----|
| W5-T1 | `src/testing/agent_tracer.py` | Hephaestus | deep | [] | Trace format valid |
| W5-T2 | `src/testing/test_harness.py` | Hephaestus | deep | [] | Evaluations run |
| W5-T3 | `src/runtime/container_manager.py` | Hephaestus | deep | [] | Podman isolation works |
| W5-T4 | `src/runtime/lifecycle_manager.py` | Hephaestus | deep | [] | tmux lifecycle works |
| W5-T5 | `src/planning/htn_planner.py` | Hephaestus | ultrabrain | [] | HTN planning works |
| W5-T6 | `src/planning/goal_reasoning.py` | Hephaestus | deep | [] | Goal reasoning works |

### WAVE 6: Compression + Tools + Infrastructure (L11 + L12 + L13)
**Dependencies**: W5 (testing for validation)
**Parallel Tasks**: 6

| Task | File | Agent | Category | Skills | QA |
|------|------|-------|----------|--------|-----|
| W6-T1 | `src/compression/token_compressor.py` | Hephaestus | deep | [] | 40-70% savings achieved |
| W6-T2 | `src/compression/kv_cache_manager.py` | Hephaestus | ultrabrain | [] | TurboQuant integration |
| W6-T3 | `src/tools/tool_generator.py` | Hephaestus | deep | [] | Tool generation works |
| W6-T4 | `src/tools/tool_verifier.py` | Hephaestus | deep | [] | Security annotations enforced |
| W6-T5 | `vpn/rotator.py` (enhance) | Hephaestus | quick | [] | Health checks, backup/restore |
| W6-T6 | `bin/` + `tests/` (enhance) | Hephaestus | deep | [] | 215 tests passing |

---

## 5. REVISED DELEGATION CHAINS

### Standard Implementation Chain (REVISED)
```
Sisyphus (orchestrator)
  └── task(subagent_type="hephaestus", category="deep", load_skills=[], run_in_background=false, prompt="...")
        └── Hephaestus implements code
  └── task(subagent_type="oracle", load_skills=[], run_in_background=false, prompt="Review architecture...")
        └── Oracle reviews
  └── task(subagent_type="momus", load_skills=[], run_in_background=false, prompt="Red-team this...")
        └── Momus red-teams
```

### Complex Logic Chain (REVISED)
```
Sisyphus (orchestrator)
  └── task(category="ultrabrain", load_skills=[], run_in_background=false, prompt="...")
        └── Hephaestus (ultrabrain model) implements complex logic
  └── task(subagent_type="oracle", load_skills=[], run_in_background=false, prompt="...")
        └── Oracle reviews
```

### Light Task Chain (REVISED)
```
Sisyphus (orchestrator)
  └── task(category="quick", load_skills=[], run_in_background=false, prompt="...")
        └── Sisyphus-Junior handles simple fix
```

### Fallback Chain (NEW from Metis)
```
If ultrabrain fails → retry with category=deep (medium model)
If deep fails → fallback to Oracle guidance → retry once
Max 2 retries per task
If 3 consecutive failures → STOP, rollback to last commit, consult Oracle
```

---

## 6. TASK DEPENDENCY GRAPH (REVISED)

```
P0: Pre-Implementation (7 tasks)
├── P0-T1: conftest.py + MockLLM ──────────────────┐
├── P0-T2: Quality gates verify ────────────────────┤
├── P0-T3: pyproject.toml verify ───────────────────┤
├── P0-T4: Storage layer verify ────────────────────┤
├── P0-T5: L1 test scaffolding ─────────────────────┤
├── P0-T6: Integration test scaffolding ────────────┤
└── P0-T7: MockLLM fixtures ────────────────────────┤
                                                    │
WAVE 1: Foundation (L1)                             │
├── W1-T1: flight_recorder.py ──────────────────────┤
├── W1-T2: governance.py ───────────────────────────┤
├── W1-T3: sentinel.py ─────────────────────────────┤
├── W1-T4: skill_telemetry.py ──────────────────────┤
└── W1-T5: delta_manifest.py ───────────────────────┤
                                                    │
WAVE 2: Memory System (L2)                          │
├── W2-T1: hierarchical.py ─────────────────────────┤
├── W2-T2: knowledge_graph.py ──────────────────────┤
├── W2-T3: vector_index.py ─────────────────────────┤
├── W2-T4: sleep_cycle.py ──────────────────────────┤
├── W2-T5: forgetting.py ───────────────────────────┤
├── W2-T6: compaction.py ───────────────────────────┤
├── W2-T7: dossier_system.py ───────────────────────┤
├── W2-T8: dream_consolidate.py ────────────────────┤
└── W2-T9: crypto_identity.py ──────────────────────┤
                                                    │
WAVE 2.5: Self-Learning (L3)                        │
├── W2.5-T1: skill_lifecycle.py ────────────────────┤
├── W2.5-T2: prompt_evolution.py ───────────────────┤
└── W2.5-T3: self_learning.py ──────────────────────┤
                                                    │
WAVE 3a: Self-Healing Core (L4-T1, L4-T2)           │
├── W3a-T1: health_monitor.py ──────────────────────┤
└── W3a-T2: self_healer.py ─────────────────────────┤
                                                    │
WAVE 3b: Orchestration Core (L5-T1, L5-T2, L5-T3)   │
├── W3b-T1: sisyphus.py ────────────────────────────┤
├── W3b-T2: prometheus.py ──────────────────────────┤
└── W3b-T3: hephaestus.py ──────────────────────────┤
                                                    │
WAVE 3c: Advanced Features (L4-T3, L4-T4, L4-T5,    │
         L5-T4, L5-T5)                              │
├── W3c-T1: auto_recovery.py ───────────────────────┤
├── W3c-T2: checkpoint_resume.py ───────────────────┤
├── W3c-T3: mcp_health.py ──────────────────────────┤
├── W3c-T4: a2a_protocol.py ────────────────────────┤
└── W3c-T5: network_orchestrator.py ────────────────┤
                                                    │
WAVE 4: MCP + Security (L6 + L7)                    │
├── W4-T1: athena-context-mcp ──────────────────────┤
├── W4-T2: nx-mind-mcp ─────────────────────────────┤
├── W4-T3: trigger-guardian-mcp ────────────────────┤
├── W4-T4: memory-mcp ──────────────────────────────┤
├── W4-T5: eval-harness-mcp ────────────────────────┤
├── W4-T6: agent_sandbox.py ────────────────────────┤
├── W4-T7: jailbreak_detector.py ───────────────────┤
├── W4-T8: permission_system.py ────────────────────┤
└── W4-T9: output_guardrails.py ────────────────────┤
                                                    │
WAVE 5: Testing + Runtime + Planning (L8+L9+L10)    │
├── W5-T1: agent_tracer.py ─────────────────────────┤
├── W5-T2: test_harness.py ─────────────────────────┤
├── W5-T3: container_manager.py ────────────────────┤
├── W5-T4: lifecycle_manager.py ────────────────────┤
├── W5-T5: htn_planner.py ──────────────────────────┤
└── W5-T6: goal_reasoning.py ───────────────────────┤
                                                    │
WAVE 6: Compression + Tools + Infra (L11+L12+L13)   │
├── W6-T1: token_compressor.py ─────────────────────┤
├── W6-T2: kv_cache_manager.py ─────────────────────┤
├── W6-T3: tool_generator.py ───────────────────────┤
├── W6-T4: tool_verifier.py ────────────────────────┤
├── W6-T5: vpn/rotator.py (enhance) ────────────────┤
└── W6-T6: bin/ + tests/ (enhance) ─────────────────┘
```

---

## 7. PARALLEL EXECUTION GRAPH (REVISED)

| Wave | Parallel Tasks | Sequential After | Speedup |
|------|---------------|-----------------|---------|
| P0 | 3 parallel (T1-T3), 4 sequential (T4-T7) | Quality gates | 57% |
| W1 | 3 parallel (T1-T3), 2 parallel (T4-T5) | Quality gates | 60% |
| W2 | 6 parallel (T1-T6), 3 parallel (T7-T9) | Quality gates | 67% |
| W2.5 | 3 parallel | Quality gates | 67% |
| W3a | 2 parallel | Quality gates | 50% |
| W3b | 3 parallel | Quality gates | 67% |
| W3c | 5 parallel | Quality gates | 80% |
| W4 | 5 parallel (T1-T5), 4 parallel (T6-T9) | Quality gates | 78% |
| W5 | 6 parallel | Quality gates | 83% |
| W6 | 6 parallel | Full test suite | 83% |

**Overall speedup**: ~65% faster than sequential implementation

---

## 8. QUALITY GATE SCHEDULE (REVISED)

| Gate | P0 | W1 | W2 | W2.5 | W3a | W3b | W3c | W4 | W5 | W6 |
|------|----|----|----|------|-----|-----|-----|----|----|----|
| Gate 1: Type Check | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Gate 2: Lint | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Gate 3: Tests | SKIP | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Gate 4: Coverage | SKIP | 70% | 75% | 70% | 75% | 70% | 75% | 80% | 80% | 80% |
| Gate 5: Secrets | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Gate 6: Placeholders | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**Coverage targets scaled by layer complexity** (from Metis recommendation)

---

## 9. REVISED END-TO-END TESTING STRATEGY

### Test Pyramid (REVISED: 190 → 215 tests)

| Test Type | Count | Coverage Target | Description |
|-----------|-------|-----------------|-------------|
| Unit Tests | 150 | 80% avg | Per-file tests for all 60+ files |
| Integration Tests | 40 | 85% | Cross-layer interaction tests |
| E2E Tests | 25 | 90% | Full workflow scenarios |
| **Total** | **215** | **82% avg** | |

### Integration Tests (40 tests — NEW from Oracle/Metis)

| Integration | Test Count | Description |
|-------------|------------|-------------|
| L1→L2 | 5 | governance triggers memory consolidation |
| L2→L3 | 5 | memory patterns trigger skill evolution |
| L3→L4 | 5 | learning patterns trigger self-healing |
| L4→L5 | 5 | healing triggers orchestration reroll |
| L5→L6 | 5 | orchestration registers MCP tools |
| L6→L7 | 5 | MCP tools pass through guardrails |
| L7→L8 | 5 | security events trigger tracing |
| L8→L9 | 5 | tracing data drives runtime decisions |

### E2E Tests (25 tests — EXPANDED from 10)

| Test ID | Workflow | Description |
|---------|----------|-------------|
| E2E-01 | Full workflow | trigger → memory → learning → healing |
| E2E-02 | MCP pipeline | athena-context → nx-mind → trigger-guardian → memory-mcp |
| E2E-03 | Self-healing | healthMonitor detects → selfHealer recovers → verify |
| E2E-04 | Memory consolidation | sleep_cycle runs → forgetting decays → compaction compacts |
| E2E-05 | Orchestration flow | sisyphus delegates → hephaestus implements → oracle reviews |
| E2E-06 | VPN rotation | 429 detected → rotate → verify connectivity |
| E2E-07 | Backup/restore | Full backup → restore → verify state matches |
| E2E-08 | Security pipeline | sandbox → jailbreak detect → permission check → guardrail |
| E2E-09 | Planning flow | HTN plan → temporal execute → goal verify |
| E2E-10 | Compression flow | token compress → KV cache → context distill |
| E2E-11 | Tool synthesis | generate → verify → compose → execute |
| E2E-12 | MCP health | MCP server fails → health detects → auto-recovery |
| E2E-13 | Cross-layer | L1 governance → L2 memory → L3 learning → L4 healing |
| E2E-14 | Cross-layer | L5 orchestration → L6 MCP → L7 security → L8 testing |
| E2E-15 | Cross-layer | L9 runtime → L10 planning → L11 compression → L12 tools |
| E2E-CHAOS-1 | MCP failure | Kill MCP server mid-workflow → verify recovery |
| E2E-CHAOS-2 | Memory corruption | Corrupt SQLite database → verify restoration |
| E2E-CHAOS-3 | Network timeout | Network timeout during VPN rotation → verify fallback |
| E2E-CHAOS-4 | Health failure | Health monitor fails → fallback to manual check |
| E2E-CHAOS-5 | Orchestration failure | Orchestrator crashes → verify checkpoint resume |
| E2E-PERF-1 | Memory latency | Memory operations <100ms |
| E2E-PERF-2 | MCP response | MCP tool calls <500ms |
| E2E-PERF-3 | E2E workflow | Full workflow <30s |
| E2E-PERF-4 | Compression ratio | Token compression achieves 40-70% savings |
| E2E-PERF-5 | Test coverage | Overall coverage >=80% |

---

## 10. SESSION MANAGEMENT (REVISED — CRITICAL FIX)

### Automated Checkpoint Strategy (FIXED from Momus/Oracle)

| Rule | Implementation |
|------|----------------|
| **Checkpoint after EVERY task** | Write `session-state.json` + `wake_up.md` after each task completion |
| **Session limit handling** | At 40 descendants, force checkpoint and start new session |
| **State validation** | On session start: verify session-state.json integrity, fallback to git stash |
| **Pre-flight checks** | Run `pytest --collect-only` before each delegation |
| **Session budget tracking** | Track tasks completed vs remaining, rebalance if session runs long |

### Session State Format
```json
{
  "session_id": "ses_...",
  "tasks_completed": 45,
  "tasks_remaining": 48,
  "current_wave": "W3c",
  "last_checkpoint": "2026-04-04T12:00:00Z",
  "quality_gates_passed": ["W1", "W2", "W2.5", "W3a", "W3b"],
  "next_task": "W3c-T1",
  "git_commit": "abc123"
}
```

### Emergency Protocols (NEW from Metis)
```
If 3 consecutive quality gate failures:
  1. Stop delegation
  2. Rollback to last commit
  3. Consult Oracle (architecture)
  4. Restart from checkpoint

If session hits 40 descendants:
  1. Force checkpoint immediately
  2. Commit with "WIP" prefix
  3. Start new session with fresh state
  4. Load session-state.json to resume
```

---

## 11. RISK MITIGATION (EXPANDED FROM REVIEWS)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Hephaestus fails on complex logic | Medium | High | Use ultrabrain category, fallback to Oracle |
| Session hits 50 descendant limit | **GUARANTEED** | Medium | **Automated checkpoint after EVERY task** |
| Quality gates fail | Medium | Medium | Fix incrementally, max 3 retries, then rollback |
| Memory system too complex | **HIGH** | High | Start with SQLite + JSON, add vector later (Lite mode) |
| MCP auth too complex | Low | Medium | Start with basic JWT, enhance later |
| Tests fail across layers | Medium | Medium | Fix layer by layer, don't batch |
| API key quota exhaustion | Medium | High | **MockLLM for all LLM-dependent code** |
| Context window overflow | Medium | High | Layer 2 memory creates massive context — add truncation |
| Circular imports | Medium | High | Strict import order, no circular deps |
| Agent loop (anti-loop protocol) | Low | High | Integrate AGENTS.md anti-loop rules |
| Session state corruption | Low | High | Memory persistence has rollback plan |
| MCP server crashes | Medium | High | **5 new stdio servers = 5 new failure points — add health checks** |
| **Timeline overrun** | **HIGH** | **HIGH** | **Revised to 35-45 sessions, buffer built in** |
| **Scope creep** | **MEDIUM** | **HIGH** | **Phased v0.1→v0.2→v1.0 approach** |

---

## 12. SUCCESS CRITERIA (EXPANDED FROM REVIEWS)

| Criteria | Target | Verified By |
|----------|--------|-------------|
| Pre-implementation complete | P0-T1 to P0-T7 all pass | Manual test |
| All 13 layers implemented | 60+ new files | File count |
| All quality gates pass | Exit 0 for all 6 gates | Gate scripts |
| 215 tests passing | 215 tests | pytest |
| SOC 2 audit trail ready | Hash-chained, tamper-evident | Manual test |
| EU AI Act compliant | Risk classification working | Manual test |
| MCP servers functional | 32 tools total | MCP Inspector |
| Health checks working | All services report | Manual test |
| Backup/restore functional | Full cycle works | Manual test |
| Storage layer working | SQLite + vector DB initialized | Manual test |
| Integration tests pass | 40 integration tests | pytest |
| E2E tests pass | 25 E2E tests | pytest |
| Version: v1.0.0 | Tag created | git tag |

---

## 13. ACTIONABLE TODO LIST (REVISED)

### PRE-IMPLEMENTATION (MUST COMPLETE FIRST)
- [ ] **P0-T1**: Create conftest.py with MockLLM fixtures
  - Agent: Hephaestus | Category: quick | Skills: [] | QA: pytest --collect-only works
- [ ] **P0-T2**: Verify quality gate scripts (6 gates)
  - Agent: Hephaestus | Category: quick | Skills: [] | QA: All 6 scripts exit 0
- [ ] **P0-T3**: Verify pyproject.toml dependencies
  - Agent: Hephaestus | Category: quick | Skills: [] | QA: pip install -e . succeeds
- [ ] **P0-T4**: Verify storage layer (SQLite + vector)
  - Agent: Hephaestus | Category: quick | Skills: [] | QA: SQLite created, vector initialized
- [ ] **P0-T5**: Create L1 test scaffolding
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Test imports pass
- [ ] **P0-T6**: Create integration test scaffolding
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Integration test imports pass
- [ ] **P0-T7**: Create MockLLM + fixtures for all layers
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: MockLLM works in tests

### WAVE 1: Foundation
- [ ] **W1-T1**: Create `src/nxyme/core/flight_recorder.py` — HMAC-chained JSONL audit trail
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Hash chain verifies, tamper detected
- [ ] **W1-T2**: Create `src/nxyme/core/governance.py` — 7-Layer AI Governance
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: 7 layers evaluate, EU AI Act classifies
- [ ] **W1-T3**: Create `src/nxyme/core/sentinel.py` — Protocol 420 + K8s probes
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: State machine transitions, probes respond
- [ ] **W1-T4**: Create `src/nxyme/core/skill_telemetry.py` — OpenTelemetry
  - Agent: Hephaestus | Category: quick | Skills: [] | QA: Traces record, dead skills detected
- [ ] **W1-T5**: Create `src/nxyme/core/delta_manifest.py` — Versioned workspace
  - Agent: Hephaestus | Category: quick | Skills: [] | QA: Versioning works, snapshots work

### WAVE 2: Memory System
- [ ] **W2-T1**: Create `src/memory/core/hierarchical.py` — 4-tier memory
  - Agent: Hephaestus | Category: ultrabrain | Skills: [] | QA: 4 layers work, eviction correct
- [ ] **W2-T2**: Create `src/memory/core/knowledge_graph.py` — Temporal KG
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: CRUD works, temporal queries
- [ ] **W2-T3**: Create `src/memory/core/vector_index.py` — Hybrid search
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Hybrid search, RRF reranking
- [ ] **W2-T4**: Create `src/memory/core/sleep_cycle.py` — JOURNAL→CONSOLIDATE→RECALL
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Cycle completes correctly
- [ ] **W2-T5**: Create `src/memory/core/forgetting.py` — Ebbinghaus decay
  - Agent: Hephaestus | Category: ultrabrain | Skills: [] | QA: Curve accurate
- [ ] **W2-T6**: Create `src/memory/core/compaction.py` — Session summarization
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Summarization works
- [ ] **W2-T7**: Create `src/memory/core/dossier_system.py` — Causal chain summaries
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Causal chains work
- [ ] **W2-T8**: Create `src/memory/core/dream_consolidate.py` — LLM creative recombination
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Recombination works
- [ ] **W2-T9**: Create `src/memory/core/crypto_identity.py` — Ed25519 signing
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Signing works

### WAVE 2.5: Self-Learning
- [ ] **W2.5-T1**: Create `src/learning/skill_lifecycle.py` — State machine (NOVEL)
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Transitions work, evaluation tracks
- [ ] **W2.5-T2**: Create `src/learning/prompt_evolution.py` — Generate→Critique→Refine→Evaluate
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Evolution works
- [ ] **W2.5-T3**: Create `src/learning/self_learning.py` — Track outcomes → Extract patterns → Adapt
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Learning works

### WAVE 3a: Self-Healing Core
- [ ] **W3a-T1**: Move+enhance `src/healing/health_monitor.py` — Composite scoring + MCP health
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: 0-100 scoring accurate
- [ ] **W3a-T2**: Move+enhance `src/healing/self_healer.py` — Circuit breaker
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: State transitions correct

### WAVE 3b: Orchestration Core
- [ ] **W3b-T1**: Create `src/orchestration/sisyphus.py` — Plan executor
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Plan executor works
- [ ] **W3b-T2**: Create `src/orchestration/prometheus.py` — Plan builder
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Plan builder works
- [ ] **W3b-T3**: Create `src/orchestration/hephaestus.py` — Implementation agent
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Implementation agent works

### WAVE 3c: Advanced Features
- [ ] **W3c-T1**: Create `src/healing/auto_recovery.py` — 4-tier degradation
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: All 4 tiers work
- [ ] **W3c-T2**: Create `src/healing/checkpoint_resume.py` — State persistence
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: State persistence works
- [ ] **W3c-T3**: Create `src/healing/mcp_health.py` — MCP health monitoring
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: MCP health monitoring works
- [ ] **W3c-T4**: Create `src/orchestration/a2a_protocol.py` — Agent Cards
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Discovery + delegation work
- [ ] **W3c-T5**: Create `src/orchestration/network_orchestrator.py` — Hierarchical
  - Agent: Hephaestus | Category: ultrabrain | Skills: [] | QA: Parallel + sequential work

### WAVE 4: MCP + Security
- [ ] **W4-T1**: Enhance `packages/athena-context-mcp/` — 7 tools
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: All 7 tools respond
- [ ] **W4-T2**: Enhance `packages/nx-mind-mcp/` — 7 tools
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: All 7 tools respond
- [ ] **W4-T3**: Enhance `packages/trigger-guardian-mcp/` — 6 tools
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: All 6 tools respond
- [ ] **W4-T4**: Create `packages/memory-mcp/` — Memory operations
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Memory ops work
- [ ] **W4-T5**: Create `packages/eval-harness-mcp/` — Quality gates
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Quality gates work
- [ ] **W4-T6**: Create `src/security/agent_sandbox.py` — Kernel sandbox
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Sandbox enforced
- [ ] **W4-T7**: Create `src/security/jailbreak_detector.py` — Perplexity detection
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Detection works
- [ ] **W4-T8**: Create `src/security/permission_system.py` — Permission system
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Permission system works
- [ ] **W4-T9**: Create `src/security/output_guardrails.py` — Guardrails
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Guardrails enforced

### WAVE 5: Testing + Runtime + Planning
- [ ] **W5-T1**: Create `src/testing/agent_tracer.py` — strace for agents
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Trace format valid
- [ ] **W5-T2**: Create `src/testing/test_harness.py` — claw-eval
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Evaluations run
- [ ] **W5-T3**: Create `src/runtime/container_manager.py` — Podman
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Isolation works
- [ ] **W5-T4**: Create `src/runtime/lifecycle_manager.py` — tmux
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Lifecycle works
- [ ] **W5-T5**: Create `src/planning/htn_planner.py` — GTPyhop
  - Agent: Hephaestus | Category: ultrabrain | Skills: [] | QA: HTN planning works
- [ ] **W5-T6**: Create `src/planning/goal_reasoning.py` — SELFGOAL
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Goal reasoning works

### WAVE 6: Compression + Tools + Infrastructure
- [ ] **W6-T1**: Create `src/compression/token_compressor.py` — kompact
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: 40-70% savings
- [ ] **W6-T2**: Create `src/compression/kv_cache_manager.py` — TurboQuant
  - Agent: Hephaestus | Category: ultrabrain | Skills: [] | QA: Quantization works
- [ ] **W6-T3**: Create `src/tools/tool_generator.py` — Runtime generation
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Generation works
- [ ] **W6-T4**: Create `src/tools/tool_verifier.py` — ToolBrain
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: Security enforced
- [ ] **W6-T5**: Enhance `vpn/rotator.py` — Health + backup
  - Agent: Hephaestus | Category: quick | Skills: [] | QA: Health checks work
- [ ] **W6-T6**: Enhance `bin/` + `tests/` — 215 tests
  - Agent: Hephaestus | Category: deep | Skills: [] | QA: 215 tests pass

---

## 14. CROSS-CHECK FINDINGS (FROM 5 AGENTS + 3 REVIEWS)

### New Patterns Added (from emerging patterns search)
| Pattern | Stars | Where Added |
|---------|-------|-------------|
| **MemMachine** (universal memory layer) | 5,353 | L2 Memory System |
| **agentflow** (thousand-agent orchestration) | 747 | L5 Orchestration |
| **AnyTool** (21K+ API universal tool layer) | 627 | L12 Tool Synthesis |
| **Ouroboros** (self-creating autonomous agent) | 457 | L4 Self-Healing |
| **slowmist/MCP-Security-Checklist** | 821 | L7 Security |
| **claw-eval** (human-verified evaluation) | 271 | L8 Testing |
| **Agent-Threat-Rules** (Sigma-like detection) | 45 | L7 Security |
| **MCPS** (cryptographic MCP security) | — | L6 MCP Servers |
| **membrane** (competence learning) | 66 | L2 Memory System |
| **memind** (Insight Tree) | 167 | L2 Memory System |
| **GenericAgent** (skill tree growth) | 846 | L3 Self-Learning |
| **agentguard** (runtime security) | 382 | L7 Security |
| **Aegis** (cryptographic audit) | 336 | L7 Security |

### Path Corrections (from codebase audit)
| Plan Path | Actual Path | Action |
|-----------|-------------|--------|
| `src/healing/health_monitor.py` | `src/health_monitor.py` | Move to src/healing/ |
| `src/healing/self_healer.py` | `src/self_healer.py` | Move to src/healing/ |
| `src/memory/core/` | `src/memory/` (no core/) | Create core/ subdir |
| All L1-L13 NEW dirs | Don't exist | Create during implementation |

### Pre-Implementation Status (from codebase audit)
| Task | Status | Notes |
|------|--------|-------|
| P0-T1: conftest.py | ❌ MISSING | Must create |
| P0-T2: Quality gates | ✅ DONE | 10 scripts exist (more than 6 planned) |
| P0-T3: pyproject.toml | ✅ DONE | Exists at root |
| P0-T4: Storage layer | ✅ DONE | SQLite databases exist in data/ |
| P0-T5: L1 test scaffolding | ⚠️ PARTIAL | test dirs exist, no conftest.py |
| P0-T6: Integration scaffolding | ❌ MISSING | Must create |
| P0-T7: MockLLM fixtures | ❌ MISSING | Must create |

---

*REVISED ULTIMATE MASTER PLAN — ALL REVIEWS ADDRESSED*
*13 Layers + Pre-Impl | 8 Waves | 93 Tasks | ~60 new files | 215 tests*
*Reviews: Oracle (7.1/10) + Metis (24 issues) + Momus (10 attacks) + 5 Cross-Checks — ALL ADDRESSED*
*Timeline: 35-45 sessions (REALISTIC)*
*Ready for Implementation*
