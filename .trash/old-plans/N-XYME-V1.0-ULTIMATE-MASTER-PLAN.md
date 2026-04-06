# N-Xyme MIND v1.0 — ULTIMATE MASTER PLAN

> **Philosophy**: "Stitch together what works from ALL sources, discard what failed."
> **Status**: Research Complete — Ready for Implementation
> **Research**: 4 rounds, 32+ agents, ~280+ patterns, 100+ repos
> **Reviews**: Metis (47 gaps) + Momus (47 issues) + Cross-Check (5 agents) — ALL ADDRESSED
> **Coverage**: 87% against 2026 industry standards

---

## 1. EXECUTIVE SUMMARY

### Project Overview
| Metric | Value |
|--------|-------|
| **Total Phases** | 7 (P0-P6) |
| **Total Waves** | 6 + Pre-Implementation |
| **Total Tasks** | 88 (83 implementation + 5 pre-impl) |
| **Total Files to Create** | ~60 new files |
| **Total Files to Enhance** | ~15 existing files |
| **Total Tests** | 190+ (unit + integration + E2E) |
| **Estimated Timeline** | 18-24 sessions |
| **Critical Path** | P0 → L1 → L2 → L4 → L5 → L9 → L13 |
| **Parallel Speedup** | ~60% vs sequential |

### Success Criteria (v1.0)
- [ ] All 13 layers implemented with 60+ new files
- [ ] All 6 quality gates pass (exit 0)
- [ ] 190+ tests passing (80%+ coverage)
- [ ] SOC 2 audit trail ready (HMAC-chained)
- [ ] EU AI Act compliant (7-layer governance)
- [ ] 5 MCP servers functional (32+ tools)
- [ ] Self-healing operational (4-tier degradation)
- [ ] E2E workflow tests passing
- [ ] Version tagged v1.0.0

---

## 2. DELEGATION AGENT MATRIX

| Role | Agent | Category/Type | Model | Use Case |
|------|-------|---------------|-------|----------|
| **Orchestrator** | Sisyphus | — | qwen3.6-plus-free (high) | Task delegation, orchestration |
| **Implementation** | Hephaestus | category: deep | qwen3.6-plus-free (medium) | Standard implementation |
| **Complex Logic** | Hephaestus | category: ultrabrain | qwen3.6-plus-free (high) | Complex algorithms |
| **Light Tasks** | Sisyphus-Junior | category: quick | minimax-m2.5-free | Simple fixes |
| **Architecture** | Oracle | subagent_type: oracle | minimax-m2.5-free | Design review |
| **Red-Team** | Momus | subagent_type: momus | qwen3.6-plus-free (high) | Adversarial testing |
| **Research** | Explore | subagent_type: explore | minimax-m2.5-free | Codebase search |
| **External** | Librarian | subagent_type: librarian | minimax-m2.5-free | Web research |

---

## 3. COMPLETE DELEGATION MATRIX (88 TASKS)

### PHASE 0: PRE-IMPLEMENTATION (P0.1-P0.5)

| Task ID | Description | Agent | Category | run_in_background | Dependencies | Duration | QA Criteria |
|---------|-------------|-------|----------|-------------------|--------------|----------|-------------|
| P0.1 | Create pytest infrastructure (conftest.py) | Hephaestus | quick | false | None | 10m | pytest --collect-only works |
| P0.2 | Enhance quality gates (ensure all 6 exit 0) | Hephaestus | quick | false | None | 15m | All 6 gates exit 0 |
| P0.3 | Verify pyproject.toml dependencies | Hephaestus | quick | false | None | 10m | pip install -e . succeeds |
| P0.4 | Verify storage layer (SQLite + vector) | Hephaestus | quick | false | None | 10m | SQLite in data/ works |
| P0.5 | Create L1 test scaffolding | Hephaestus | deep | false | P0.1 | 20m | Test imports pass |

### PHASE 1: CORE FOUNDATION (L1) — Wave 1

| Task ID | Description | Agent | Category | run_in_background | Dependencies | Duration | QA Criteria |
|---------|-------------|-------|----------|-------------------|--------------|----------|-------------|
| L1-T1 | Create flight_recorder.py (HMAC-chained JSONL) | Hephaestus | deep | false | P0.5 | 45m | Hash chain verifies, tamper detected |
| L1-T2 | Create governance.py (7-Layer AI + EU AI Act) | Hephaestus | deep | false | P0.5 | 60m | 7 layers evaluate, EU classifies |
| L1-T3 | Create sentinel.py (Protocol 420 + K8s probes) | Hephaestus | deep | false | P0.5 | 45m | State machine transitions |
| L1-T4 | Create skill_telemetry.py (OpenTelemetry) | Hephaestus | quick | false | L1-T1 | 30m | Traces record, dead skills detected |
| L1-T5 | Create delta_manifest.py (SHA-256 versioning) | Hephaestus | quick | false | L1-T1 | 30m | Versioning works, snapshots work |

### PHASE 2: MEMORY SYSTEM (L2) + SELF-LEARNING (L3) — Wave 2

| Task ID | Description | Agent | Category | run_in_background | Dependencies | Duration | QA Criteria |
|---------|-------------|-------|----------|-------------------|--------------|----------|-------------|
| L2-T1 | Create hierarchical.py (4-tier memory) | Hephaestus | ultrabrain | false | L1-T3 | 90m | 4 layers work, eviction correct |
| L2-T2 | Create knowledge_graph.py (Graphiti patterns) | Hephaestus | deep | false | L1-T3 | 60m | Entities/relations CRUD |
| L2-T3 | Create vector_index.py (Hybrid BM25+semantic) | Hephaestus | deep | false | L2-T2 | 60m | Hybrid search, RRF reranking |
| L2-T4 | Create sleep_cycle.py (JOURNAL→CONS→RECALL) | Hephaestus | deep | false | L2-T1 | 60m | Cycle completes correctly |
| L2-T5 | Create forgetting.py (Ebbinghaus decay) | Hephaestus | ultrabrain | false | L2-T1 | 45m | Curve accurate |
| L2-T6 | Create compaction.py (Session summarization) | Hephaestus | deep | false | L2-T4 | 45m | Summarization works |
| L2-T7 | Create dossier_system.py (Causal chains) | Hephaestus | deep | false | L2-T6 | 45m | Causal summaries work |
| L2-T8 | Create dream_consolidate.py (LLM recombination) | Hephaestus | deep | false | L2-T7 | 45m | Dream consolidation works |
| L2-T9 | Create crypto_identity.py (Ed25519 signing) | Hephaestus | deep | false | L2-T8 | 30m | Identity signing works |
| L3-T1 | Create skill_lifecycle.py (NOVEL state machine) | Hephaestus | deep | false | L2-T9 | 60m | Transitions work |
| L3-T2 | Create prompt_evolution.py (Generate→Critique→Refine) | Hephaestus | deep | false | L3-T1 | 60m | Evolution cycle works |
| L3-T3 | Create self_learning.py (Outcome tracking) | Hephaestus | deep | false | L3-T2 | 45m | Pattern extraction works |

### PHASE 3: SELF-HEALING (L4) + ORCHESTRATION (L5) — Wave 3

| Task ID | Description | Agent | Category | run_in_background | Dependencies | Duration | QA Criteria |
|---------|-------------|-------|----------|-------------------|--------------|----------|-------------|
| L4-T1 | Move+enhance health_monitor.py → src/healing/ | Hephaestus | deep | false | L1-T3 | 45m | Composite scoring 0-100 |
| L4-T2 | Move+enhance self_healer.py → src/healing/ | Hephaestus | deep | false | L4-T1 | 45m | Circuit breaker transitions |
| L4-T3 | Create auto_recovery.py (4-tier degradation) | Hephaestus | deep | false | L4-T2 | 60m | All 4 tiers work |
| L4-T4 | Create checkpoint_resume.py (LangGraph persistence) | Hephaestus | deep | false | L4-T3 | 45m | Checkpoint/restore works |
| L5-T1 | Create sisyphus.py (Plan executor) | Hephaestus | deep | false | L4-T4 | 60m | Execution works |
| L5-T2 | Create prometheus.py (Plan builder) | Hephaestus | deep | false | L5-T1 | 60m | Plan building works |
| L5-T3 | Create hephaestus.py (Implementation agent) | Hephaestus | deep | false | L5-T2 | 45m | Progress tracking works |
| L5-T4 | Create a2a_protocol.py (Google A2A Agent Cards) | Hephaestus | deep | false | L5-T3 | 60m | Discovery + delegation work |
| L5-T5 | Create network_orchestrator.py (CrewAI hierarchical) | Hephaestus | ultrabrain | false | L5-T4 | 90m | Parallel + sequential work |

### PHASE 4: MCP SERVERS (L6) + SECURITY (L7) — Wave 4

| Task ID | Description | Agent | Category | run_in_background | Dependencies | Duration | QA Criteria |
|---------|-------------|-------|----------|-------------------|--------------|----------|-------------|
| L6-T1 | Enhance athena-context-mcp (7 tools) | Hephaestus | deep | false | L2-T9, L5-T1 | 60m | All 7 tools respond |
| L6-T2 | Enhance nx-mind-mcp (7 tools) | Hephaestus | deep | false | L2-T1, L5-T2 | 60m | All 7 tools respond |
| L6-T3 | Enhance trigger-guardian-mcp (6 tools) | Hephaestus | deep | false | L5-T3 | 45m | All 6 tools respond |
| L6-T4 | Create memory-mcp (NEW, 8 tools) | Hephaestus | deep | false | L2-T1 | 60m | Memory operations work |
| L6-T5 | Create eval-harness-mcp (NEW, 6 tools) | Hephaestus | deep | false | L5-T3 | 60m | Quality gates work |
| L7-T1 | Create agent_sandbox.py (Kernel enforcement) | Hephaestus | deep | false | L5-T5 | 60m | Sandbox enforced |
| L7-T2 | Create jailbreak_detector.py (Perplexity-based) | Hephaestus | deep | false | L7-T1 | 45m | Detection works |
| L7-T3 | Create permission_system.py (Slowmist patterns) | Hephaestus | deep | false | L7-T2 | 45m | Permissions enforced |
| L7-T4 | Create output_guardrails.py (OWASP validation) | Hephaestus | deep | false | L7-T3 | 45m | Guardrails block attacks |

### PHASE 5: TESTING (L8) + RUNTIME (L9) + PLANNING (L10) — Wave 5

| Task ID | Description | Agent | Category | run_in_background | Dependencies | Duration | QA Criteria |
|---------|-------------|-------|----------|-------------------|--------------|----------|-------------|
| L8-T1 | Create agent_tracer.py (strace for agents) | Hephaestus | deep | false | L5-T3 | 45m | Trace format valid |
| L8-T2 | Create test_harness.py (claw-eval patterns) | Hephaestus | deep | false | L8-T1 | 60m | Evaluations run |
| L8-T3 | Create regression_detector.py (agent-vcr) | Hephaestus | deep | false | L8-T2 | 45m | Time-travel works |
| L9-T1 | Create container_manager.py (Podman isolation) | Hephaestus | deep | false | L5-T5 | 60m | Isolation works |
| L9-T2 | Create microvm_runtime.py (Firecracker) | Hephaestus | deep | false | L9-T1 | 60m | MicroVM works |
| L9-T3 | Create lifecycle_manager.py (tmux-based) | Hephaestus | deep | false | L9-T2 | 45m | Lifecycle works |
| L10-T1 | Create htn_planner.py (GTPyhop) | Hephaestus | ultrabrain | false | L5-T5 | 90m | HTN planning works |
| L10-T2 | Create temporal_planner.py (Durable execution) | Hephaestus | deep | false | L10-T1 | 60m | Temporal planning works |
| L10-T3 | Create goal_reasoning.py (SELFGOAL patterns) | Hephaestus | deep | false | L10-T2 | 60m | Goal reasoning works |

### PHASE 6: COMPRESSION (L11) + TOOLS (L12) + INFRASTRUCTURE (L13) — Wave 6

| Task ID | Description | Agent | Category | run_in_background | Dependencies | Duration | QA Criteria |
|---------|-------------|-------|----------|-------------------|--------------|----------|-------------|
| L11-T1 | Create token_compressor.py (kompact patterns) | Hephaestus | deep | false | L10-T3 | 60m | 40-70% savings |
| L11-T2 | Create kv_cache_manager.py (TurboQuant) | Hephaestus | ultrabrain | false | L11-T1 | 90m | Quantization works |
| L11-T3 | Create context_distiller.py (Claw Compactor) | Hephaestus | deep | false | L11-T2 | 60m | Distillation works |
| L12-T1 | Create tool_generator.py (Runtime generation) | Hephaestus | deep | false | L11-T3 | 60m | Generation works |
| L12-T2 | Create tool_verifier.py (ToolBrain patterns) | Hephaestus | deep | false | L12-T1 | 45m | Security enforced |
| L12-T3 | Create tool_composer.py (Toolathlon) | Hephaestus | deep | false | L12-T2 | 60m | Composition works |
| L13-T1 | Enhance vpn/rotator.py (429-adaptive) | Hephaestus | quick | false | None | 30m | Health checks work |
| L13-T2 | Enhance _bmad/ workflows (46 skills) | Hephaestus | quick | false | None | 30m | Workflows accessible |
| L13-T3 | Enhance bin/ CLI tools | Hephaestus | deep | false | None | 45m | All CLI tools work |
| L13-T4 | Create E2E test suite (Full workflow) | Hephaestus | deep | false | L13-T3 | 90m | E2E tests pass |

---

## 4. PHASE-BY-PHASE EXECUTION PLAN

### PHASE 0: PRE-IMPLEMENTATION (P0)
**Duration**: 2 sessions | **Tasks**: 5

**Goals**:
- Ensure pytest infrastructure works
- Verify quality gates exit 0
- Confirm storage layer operational

**Parallel Opportunities**: P0.1-P0.3 can run in parallel

**Quality Gates**:
- Run: `pytest tests/ --collect-only`
- Run: `./bin/quality-gates/gate-all.sh`
- Verify: All exit 0

**Review Checkpoint**: Oracle reviews P0.5 test scaffolding

**Rollback**: If P0 fails, revert to last known good state

---

### PHASE 1: CORE FOUNDATION (L1)
**Duration**: 3 sessions | **Tasks**: 5

**Goals**:
- Implement 5 core governance files
- Establish HMAC-chained audit trail
- Create 7-layer AI governance

**Parallel Opportunities**: L1-T1, L1-T2, L1-T3 run in parallel (deep tasks)

**Quality Gates**:
- Run: `./bin/quality-gates/gate-1-py-typecheck.sh`
- Run: `./bin/quality-gates/gate-2-py-lint.sh`
- Run: `pytest tests/unit/core/ -v`
- Verify: 85%+ coverage on core/

**Review Checkpoint**: 
- Oracle reviews L1 architecture
- Momus red-teams governance logic

**Rollback**: If L1 fails, git checkout the src/nxyme/core/ directory

---

### PHASE 2: MEMORY + LEARNING (L2 + L3)
**Duration**: 4 sessions | **Tasks**: 12

**Goals**:
- Implement 9 memory system files
- Implement 3 self-learning files
- Create hierarchical memory with forgetting

**Parallel Opportunities**: L2-T1-L2-T6 run in parallel, then L2-T7-L2-T9

**Quality Gates**:
- Run: `./bin/quality-gates/gate-1-py-typecheck.sh`
- Run: `./bin/quality-gates/gate-2-py-lint.sh`
- Run: `pytest tests/unit/memory/ tests/unit/learning/ -v`
- Verify: 85%+ coverage on memory/

**Review Checkpoint**:
- Oracle reviews memory architecture
- Momus stress-tests forgetting curve

**Rollback**: If L2/L3 fails, git checkout src/memory/ and src/learning/

---

### PHASE 3: SELF-HEALING + ORCHESTRATION (L4 + L5)
**Duration**: 4 sessions | **Tasks**: 9

**Goals**:
- Move health_monitor.py and self_healer.py to src/healing/
- Implement 4 self-healing files
- Implement 5 orchestration files

**Parallel Opportunities**: L4-T1-T4-T2 parallel, L5-T1-L5-T3 parallel

**Quality Gates**:
- Run: `./bin/quality-gates/gate-1-py-typecheck.sh`
- Run: `./bin/quality-gates/gate-2-py-lint.sh`
- Run: `pytest tests/unit/healing/ tests/unit/orchestration/ -v`
- Verify: 80%+ coverage

**Review Checkpoint**:
- Oracle reviews orchestration design
- Momus tests circuit breaker failure modes

**Rollback**: If L4/L5 fails, git checkout src/healing/ and src/orchestration/

---

### PHASE 4: MCP + SECURITY (L6 + L7)
**Duration**: 3 sessions | **Tasks**: 9

**Goals**:
- Enhance 3 existing MCP servers
- Create 2 new MCP servers
- Implement 4 security files

**Parallel Opportunities**: L6-T1-L6-T3 parallel, L7-T1-L7-T3 parallel

**Quality Gates**:
- Run: `./bin/quality-gates/gate-1-py-typecheck.sh`
- Run: `./bin/quality-gates/gate-2-py-lint.sh`
- Run: `./bin/quality-gates/gate-5-secrets.sh`
- Run: `pytest tests/unit/mcp/ tests/unit/security/ -v`
- Verify: 85%+ coverage on security/

**Review Checkpoint**:
- Oracle reviews MCP protocol
- Momus tests jailbreak attempts

**Rollback**: If L6/L7 fails, git checkout packages/ and src/security/

---

### PHASE 5: TESTING + RUNTIME + PLANNING (L8 + L9 + L10)
**Duration**: 3 sessions | **Tasks**: 9

**Goals**:
- Implement 3 testing/debugging files
- Implement 3 runtime files
- Implement 3 planning files

**Parallel Opportunities**: L8-T1-L8-T2 parallel, L9-T1-L9-T2 parallel

**Quality Gates**:
- Run: `./bin/quality-gates/gate-1-py-typecheck.sh`
- Run: `./bin/quality-gates/gate-2-py-lint.sh`
- Run: `pytest tests/unit/testing/ tests/unit/runtime/ tests/unit/planning/ -v`
- Verify: 80%+ coverage

**Review Checkpoint**:
- Oracle reviews planning algorithms
- Momus tests HTN planner edge cases

**Rollback**: If L8/L9/L10 fails, git checkout src/testing/, src/runtime/, src/planning/

---

### PHASE 6: COMPRESSION + TOOLS + INFRASTRUCTURE (L11 + L12 + L13)
**Duration**: 3 sessions | **Tasks**: 10

**Goals**:
- Implement 3 compression files
- Implement 3 tool synthesis files
- Enhance infrastructure (VPN, BMAD, bin)
- Create full E2E test suite

**Parallel Opportunities**: L11-T1-L11-T2 parallel, L12-T1-L12-T2 parallel

**Quality Gates**:
- Run: ALL quality gates
- Run: `pytest tests/ -v --cov=src --cov-fail-under=80`
- Run: `./bin/quality-gates/gate-6-placeholders.sh`
- Verify: 190+ tests pass, 80%+ coverage

**Review Checkpoint**:
- Oracle reviews final architecture
- Momus performs full red-team
- Full E2E workflow test

**Rollback**: If Phase 6 fails, git checkout entire src/, packages/, vpn/, bin/

---

## 5. END-TO-END TESTING STRATEGY

### Test Pyramid

```
        ┌─────────────┐
        │    E2E     │  ← Full workflow (10 tests)
        │   (10)     │
        ├─────────────┤
        │ Integration │  ← Cross-layer (30 tests)
        │   (30)     │
        ├─────────────┤
        │    Unit    │  ← Per-layer (150 tests)
        │   (150)    │
        └─────────────┘
```

### Unit Tests (150 tests)
| Layer | Test File | Count | Coverage Target |
|-------|-----------|-------|-----------------|
| L1 | `tests/unit/core/test_*.py` | 25 | 85% |
| L2 | `tests/unit/memory/test_*.py` | 30 | 85% |
| L3 | `tests/unit/learning/test_*.py` | 15 | 80% |
| L4 | `tests/unit/healing/test_*.py` | 15 | 80% |
| L5 | `tests/unit/orchestration/test_*.py` | 15 | 80% |
| L6 | `tests/unit/mcp/test_*.py` | 15 | 80% |
| L7 | `tests/unit/security/test_*.py` | 15 | 85% |
| L8 | `tests/unit/testing/test_*.py` | 10 | 80% |
| L9 | `tests/unit/runtime/test_*.py` | 10 | 80% |
| L10 | `tests/unit/planning/test_*.py` | 10 | 80% |
| L11 | `tests/unit/compression/test_*.py` | 10 | 80% |
| L12 | `tests/unit/tools/test_*.py` | 10 | 80% |

### Integration Tests (30 tests)
- Cross-layer workflows
- MCP server communication
- Self-healing triggers
- Memory consolidation cycles

### E2E Tests (10 tests)
- Full workflow: trigger → memory → learning → healing
- VPN rotation workflow
- MCP server health checks
- Backup/restore cycle

### Performance Benchmarks
- Memory latency <100ms
- MCP response <500ms
- E2E workflow <30s

### Security Tests
- Jailbreak attempt detection
- Permission escalation prevention
- Output guardrail validation

### Chaos Tests
- Simulate MCP server failure
- Simulate memory corruption
- Simulate network timeout

### Regression Tests
- Run previous test suite
- Detect behavioral drift
- Time-travel debugging

---

## 6. DELEGATION CHAIN PATTERNS

### Pattern A: Standard Implementation
```
Sisyphus (orchestrator)
  └── task(category="deep", load_skills=[], run_in_background=false, prompt="...")
        └── Hephaestus implements code
        └── Returns: success/fail + proof
  └── task(subagent_type="oracle", load_skills=[], run_in_background=false, prompt="Review...")
        └── Oracle reviews
        └── Returns: approve/reject + feedback
```

### Pattern B: Complex Logic (ultrabrain)
```
Sisyphus (orchestrator)
  └── task(category="ultrabrain", load_skills=[], run_in_background=false, prompt="...")
        └── Hephaestus (high model) implements complex logic
        └── Returns: implementation + complexity analysis
```

### Pattern C: Review Cycle
```
Sisyphus (orchestrator)
  └── task(subagent_type="oracle", load_skills=[], run_in_background=false, prompt="Review architecture...")
        └── Oracle reviews
        └── Returns: issues list
  └── task(subagent_type="momus", load_skills=[], run_in_background=false, prompt="Red-team...")
        └── Momus red-teams
        └── Returns: vulnerabilities list
  └── Hephaestus fixes issues
  └── Retry until both pass
```

### Pattern D: Light Tasks
```
Sisyphus (orchestrator)
  └── task(category="quick", load_skills=[], run_in_background=false, prompt="...")
        └── Sisyphus-Junior handles simple fix
        └── Returns: success/fail
```

### Pattern E: Research
```
Sisyphus (orchestrator)
  └── task(subagent_type="explore", description="Search codebase", run_in_background=true, prompt="Find...")
  └── task(subagent_type="librarian", description="External docs", run_in_background=true, prompt="Research...")
        └── Parallel exploration
        └── Returns: findings
```

---

## 7. RISK MITIGATION PER PHASE

### Phase 0: Pre-Implementation
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| conftest.py fails | Low | Medium | Use minimal pytest fixtures |
| Quality gates fail | Medium | Medium | Fix incrementally, max 3 retries |

### Phase 1: Core Foundation
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| HMAC chain breaks | Medium | High | Add verification test |
| EU AI Act complex | Medium | Medium | Start with tier 1 only |
| State machine bugs | Medium | High | Add state transition tests |

### Phase 2: Memory + Learning
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Memory too complex | **HIGH** | High | Start with SQLite only (Lite mode) |
| Forgetting curve wrong | Medium | Medium | Validate against Ebbinghaus |
| Vector DB unavailable | Medium | Medium | Fallback to JSON file |

### Phase 3: Self-Healing + Orchestration
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Circuit breaker loops | Medium | High | Add max retry limit |
| Orchestration deadlock | Medium | High | Add timeout + dead agent detection |
| Checkpoint corruption | Low | High | Add checksum verification |

### Phase 4: MCP + Security
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| MCP auth fails | Medium | Medium | Start with no auth |
| Jailbreak false positives | Medium | Medium | Tune perplexity threshold |
| Sandbox escape | Low | Critical | Defense in depth |

### Phase 5: Testing + Runtime + Planning
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| HTN planner slow | Medium | Medium | Add caching |
| Container failure | Medium | High | Fallback to subprocess |
| MicroVM unavailable | High | Medium | Use Podman only |

### Phase 6: Compression + Tools + Infrastructure
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Compression ineffective | Medium | Low | Accept lower savings |
| Tool generation bugs | Medium | High | Add verification before use |
| E2E tests fail | **HIGH** | High | Fix layer by layer, don't batch |

### Cross-Cutting Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Session hits 50 limit | **GUARANTEED** | Medium | Manual checkpoint, batch delegations |
| API key quota exhaust | Medium | High | Use MockLLM for tests |
| Context overflow | Medium | High | Add truncation |

---

## 8. ATOMIC COMMIT STRATEGY

### Commit 0: Pre-Implementation
```
chore: add pytest infrastructure and verify quality gates
- tests/conftest.py (new)
- bin/quality-gates/* (enhanced)
```
**Files**: P0.1, P0.2

### Commit 1: Core Foundation
```
feat(core): implement Layer 1 - Core Foundation
- src/nxyme/core/flight_recorder.py
- src/nxyme/core/governance.py
- src/nxyme/core/sentinel.py
- src/nxyme/core/skill_telemetry.py
- src/nxyme/core/delta_manifest.py
```
**Files**: L1-T1 to L1-T5

### Commit 2: Memory System
```
feat(memory): implement Layer 2 - Memory System (9 files)
- src/memory/core/hierarchical.py
- src/memory/core/knowledge_graph.py
- src/memory/core/vector_index.py
- src/memory/core/sleep_cycle.py
- src/memory/core/forgetting.py
- src/memory/core/compaction.py
- src/memory/core/dossier_system.py
- src/memory/core/dream_consolidate.py
- src/memory/core/crypto_identity.py
```
**Files**: L2-T1 to L2-T9

### Commit 3: Self-Learning
```
feat(learning): implement Layer 3 - Self-Learning (3 files)
- src/learning/skill_lifecycle.py
- src/learning/prompt_evolution.py
- src/learning/self_learning.py
```
**Files**: L3-T1 to L3-T3

### Commit 4: Self-Healing
```
feat(healing): implement Layer 4 - Self-Healing (4 files)
- src/healing/health_monitor.py (moved+enhanced)
- src/healing/self_healer.py (moved+enhanced)
- src/healing/auto_recovery.py
- src/healing/checkpoint_resume.py
```
**Files**: L4-T1 to L4-T4

### Commit 5: Agent Orchestration
```
feat(orchestration): implement Layer 5 - Agent Orchestration (5 files)
- src/orchestration/sisyphus.py
- src/orchestration/prometheus.py
- src/orchestration/hephaestus.py
- src/orchestration/a2a_protocol.py
- src/orchestration/network_orchestrator.py
```
**Files**: L5-T1 to L5-T5

### Commit 6: MCP Servers
```
feat(mcp): implement Layer 6 - MCP Servers (5 servers)
- packages/athena-context-mcp/ (enhanced)
- packages/nx-mind-mcp/ (enhanced)
- packages/trigger-guardian-mcp/ (enhanced)
- packages/memory-mcp/ (new)
- packages/eval-harness-mcp/ (new)
```
**Files**: L6-T1 to L6-T5

### Commit 7: Security
```
feat(security): implement Layer 7 - Security (4 files)
- src/security/agent_sandbox.py
- src/security/jailbreak_detector.py
- src/security/permission_system.py
- src/security/output_guardrails.py
```
**Files**: L7-T1 to L7-T4

### Commit 8: Testing & Debugging
```
feat(testing): implement Layer 8 - Testing & Debugging (3 files)
- src/testing/agent_tracer.py
- src/testing/test_harness.py
- src/testing/regression_detector.py
```
**Files**: L8-T1 to L8-T3

### Commit 9: Runtime
```
feat(runtime): implement Layer 9 - Runtime (3 files)
- src/runtime/container_manager.py
- src/runtime/microvm_runtime.py
- src/runtime/lifecycle_manager.py
```
**Files**: L9-T1 to L9-T3

### Commit 10: Planning
```
feat(planning): implement Layer 10 - Planning (3 files)
- src/planning/htn_planner.py
- src/planning/temporal_planner.py
- src/planning/goal_reasoning.py
```
**Files**: L10-T1 to L10-T3

### Commit 11: Compression
```
feat(compression): implement Layer 11 - Compression (3 files)
- src/compression/token_compressor.py
- src/compression/kv_cache_manager.py
- src/compression/context_distiller.py
```
**Files**: L11-T1 to L11-T3

### Commit 12: Tool Synthesis
```
feat(tools): implement Layer 12 - Tool Synthesis (3 files)
- src/tools/tool_generator.py
- src/tools/tool_verifier.py
- src/tools/tool_composer.py
```
**Files**: L12-T1 to L12-T3

### Commit 13: Infrastructure
```
feat(infra): enhance Layer 13 - Infrastructure
- vpn/rotator.py (enhanced)
- _bmad/ (enhanced)
- bin/ (enhanced)
```
**Files**: L13-T1 to L13-T3

### Commit 14: E2E Tests
```
test: add integration and E2E tests for all layers
- tests/integration/test_core.py (enhanced)
- tests/e2e/ (new)
```
**Files**: L13-T4

### Commit 15: Final Verification
```
chore: run all quality gates and finalize v1.0
- Fix any remaining issues
- Tag v1.0.0
```
**Verification**: All gates pass, 190+ tests pass

---

## 9. QUALITY GATE SCHEDULE

### Per-Phase Gate Execution

| Phase | Gate 1 | Gate 2 | Gate 3 | Gate 4 | Gate 5 | Gate 6 |
|-------|--------|--------|--------|--------|--------|--------|
| P0 | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| L1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| L2 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| L3 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| L4 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| L5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| L6 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| L7 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| L8 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| L9 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| L10 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| L11 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| L12 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| L13 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### Gate Commands

| Gate | Command | Pass Criteria |
|------|---------|---------------|
| Gate 1: Type Check | `./bin/quality-gates/gate-1-py-typecheck.sh` | Exit 0 |
| Gate 2: Lint | `./bin/quality-gates/gate-2-py-lint.sh` | Exit 0 |
| Gate 3: Tests | `pytest tests/unit/ -v` | All pass |
| Gate 4: Coverage | `pytest --cov=src --cov-fail-under=80` | 80%+ |
| Gate 5: Secrets | `./bin/quality-gates/gate-5-secrets.sh` | Exit 0 |
| Gate 6: Placeholders | `./bin/quality-gates/gate-6-placeholders.sh` | Exit 0 (warning ok) |

### Retry Strategy
- **Max 3 retries** per gate
- If Gate 1 fails → fix types, retry
- If Gate 2 fails → fix lint, retry
- If Gate 3 fails → fix tests, retry
- If Gate 4 fails → add missing tests
- If Gate 5 fails → remove secrets, abort commit
- If Gate 6 fails → replace placeholders (warning only)

---

## 10. SESSION MANAGEMENT

### Session Limits
- **Max 50 descendants** per session
- **Checkpoint every 10 tasks**
- **Manual state save** to `.sisyphus/session-state.json`

### Checkpoint Strategy
```
After every wave completion:
1. Write session-state.json (current_task, last_agent, progress)
2. Write wake_up.md (briefing for next session)
3. Verify all files created match todo list
4. Test imports in new session before continuing
```

### Continuation Protocol
```
On session start:
1. Read .sisyphus/session-state.json
2. If last_agent != current_agent → read wake_up.md
3. Resume from current_task
4. Run quick health check (pytest --collect-only)
5. Continue delegation
```

### Anti-Loop Rules
- Max 3 attempts per task
- Mandatory reflection before retry
- Action fingerprinting (detect A→B→A patterns)
- Escalation ladder: L0→L1→L2→L3→L4→user

---

## 11. ACTIONABLE TODO LIST

### PHASE 0: PRE-IMPLEMENTATION (Session 1-2)

| Task | Phase | Wave | Agent | Category | Skills | Dependencies | QA | Duration |
|------|-------|------|-------|----------|--------|--------------|-----|----------|
| P0.1 | P0 | — | Hephaestus | quick | [] | None | pytest --collect-only works | 10m |
| P0.2 | P0 | — | Hephaestus | quick | [] | None | All 6 gates exit 0 | 15m |
| P0.3 | P0 | — | Hephaestus | quick | [] | None | pip install -e . succeeds | 10m |
| P0.4 | P0 | — | Hephaestus | quick | [] | None | SQLite in data/ works | 10m |
| P0.5 | P0 | — | Hephaestus | deep | [] | P0.1 | Test imports pass | 20m |

### PHASE 1: CORE FOUNDATION (Session 3-5)

| Task | Phase | Wave | Agent | Category | Skills | Dependencies | QA | Duration |
|------|-------|------|-------|----------|--------|--------------|-----|----------|
| L1-T1 | L1 | W1 | Hephaestus | deep | [] | P0.5 | Hash chain verifies | 45m |
| L1-T2 | L1 | W1 | Hephaestus | deep | [] | P0.5 | 7 layers evaluate | 60m |
| L1-T3 | L1 | W1 | Hephaestus | deep | [] | P0.5 | State machine transitions | 45m |
| L1-T4 | L1 | W1 | Hephaestus | quick | [] | L1-T1 | Traces record | 30m |
| L1-T5 | L1 | W1 | Hephaestus | quick | [] | L1-T1 | Versioning works | 30m |

### PHASE 2: MEMORY + LEARNING (Session 6-9)

| Task | Phase | Wave | Agent | Category | Skills | Dependencies | QA | Duration |
|------|-------|------|-------|----------|--------|--------------|-----|----------|
| L2-T1 | L2 | W2 | Hephaestus | ultrabrain | [] | L1-T3 | 4 layers work | 90m |
| L2-T2 | L2 | W2 | Hephaestus | deep | [] | L1-T3 | Entities/relations CRUD | 60m |
| L2-T3 | L2 | W2 | Hephaestus | deep | [] | L2-T2 | Hybrid search works | 60m |
| L2-T4 | L2 | W2 | Hephaestus | deep | [] | L2-T1 | Cycle completes | 60m |
| L2-T5 | L2 | W2 | Hephaestus | ultrabrain | [] | L2-T1 | Curve accurate | 45m |
| L2-T6 | L2 | W2 | Hephaestus | deep | [] | L2-T4 | Summarization works | 45m |
| L2-T7 | L2 | W2 | Hephaestus | deep | [] | L2-T6 | Causal summaries | 45m |
| L2-T8 | L2 | W2 | Hephaestus | deep | [] | L2-T7 | Dream consolidation | 45m |
| L2-T9 | L2 | W2 | Hephaestus | deep | [] | L2-T8 | Identity signing | 30m |
| L3-T1 | L3 | W2 | Hephaestus | deep | [] | L2-T9 | Transitions work | 60m |
| L3-T2 | L3 | W2 | Hephaestus | deep | [] | L3-T1 | Evolution cycle | 60m |
| L3-T3 | L3 | W2 | Hephaestus | deep | [] | L3-T2 | Pattern extraction | 45m |

### PHASE 3: SELF-HEALING + ORCHESTRATION (Session 10-13)

| Task | Phase | Wave | Agent | Category | Skills | Dependencies | QA | Duration |
|------|-------|------|-------|----------|--------|--------------|-----|----------|
| L4-T1 | L4 | W3 | Hephaestus | deep | [] | L1-T3 | Scoring 0-100 | 45m |
| L4-T2 | L4 | W3 | Hephaestus | deep | [] | L4-T1 | Circuit breaker | 45m |
| L4-T3 | L4 | W3 | Hephaestus | deep | [] | L4-T2 | 4-tier works | 60m |
| L4-T4 | L4 | W3 | Hephaestus | deep | [] | L4-T3 | Checkpoint/restore | 45m |
| L5-T1 | L5 | W3 | Hephaestus | deep | [] | L4-T4 | Execution works | 60m |
| L5-T2 | L5 | W3 | Hephaestus | deep | [] | L5-T1 | Plan building | 60m |
| L5-T3 | L5 | W3 | Hephaestus | deep | [] | L5-T2 | Progress tracking | 45m |
| L5-T4 | L5 | W3 | Hephaestus | deep | [] | L5-T3 | Discovery works | 60m |
| L5-T5 | L5 | W3 | Hephaestus | ultrabrain | [] | L5-T4 | Parallel works | 90m |

### PHASE 4: MCP + SECURITY (Session 14-16)

| Task | Phase | Wave | Agent | Category | Skills | Dependencies | QA | Duration |
|------|-------|------|-------|----------|--------|--------------|-----|----------|
| L6-T1 | L6 | W4 | Hephaestus | deep | [] | L2-T9, L5-T1 | 7 tools respond | 60m |
| L6-T2 | L6 | W4 | Hephaestus | deep | [] | L2-T1, L5-T2 | 7 tools respond | 60m |
| L6-T3 | L6 | W4 | Hephaestus | deep | [] | L5-T3 | 6 tools respond | 45m |
| L6-T4 | L6 | W4 | Hephaestus | deep | [] | L2-T1 | Memory ops work | 60m |
| L6-T5 | L6 | W4 | Hephaestus | deep | [] | L5-T3 | Quality gates work | 60m |
| L7-T1 | L7 | W4 | Hephaestus | deep | [] | L5-T5 | Sandbox enforced | 60m |
| L7-T2 | L7 | W4 | Hephaestus | deep | [] | L7-T1 | Detection works | 45m |
| L7-T3 | L7 | W4 | Hephaestus | deep | [] | L7-T2 | Permissions enforced | 45m |
| L7-T4 | L7 | W4 | Hephaestus | deep | [] | L7-T3 | Guardrails block | 45m |

### PHASE 5: TESTING + RUNTIME + PLANNING (Session 17-19)

| Task | Phase | Wave | Agent | Category | Skills | Dependencies | QA | Duration |
|------|-------|------|-------|----------|--------|--------------|-----|----------|
| L8-T1 | L8 | W5 | Hephaestus | deep | [] | L5-T3 | Trace valid | 45m |
| L8-T2 | L8 | W5 | Hephaestus | deep | [] | L8-T1 | Evaluations run | 60m |
| L8-T3 | L8 | W5 | Hephaestus | deep | [] | L8-T2 | Time-travel works | 45m |
| L9-T1 | L9 | W5 | Hephaestus | deep | [] | L5-T5 | Isolation works | 60m |
| L9-T2 | L9 | W5 | Hephaestus | deep | [] | L9-T1 | MicroVM works | 60m |
| L9-T3 | L9 | W5 | Hephaestus | deep | [] | L9-T2 | Lifecycle works | 45m |
| L10-T1 | L10 | W5 | Hephaestus | ultrabrain | [] | L5-T5 | HTN works | 90m |
| L10-T2 | L10 | W5 | Hephaestus | deep | [] | L10-T1 | Temporal works | 60m |
| L10-T3 | L10 | W5 | Hephaestus | deep | [] | L10-T2 | Goal reasoning | 60m |

### PHASE 6: COMPRESSION + TOOLS + INFRASTRUCTURE (Session 20-24)

| Task | Phase | Wave | Agent | Category | Skills | Dependencies | QA | Duration |
|------|-------|------|-------|----------|--------|--------------|-----|----------|
| L11-T1 | L11 | W6 | Hephaestus | deep | [] | L10-T3 | 40-70% savings | 60m |
| L11-T2 | L11 | W6 | Hephaestus | ultrabrain | [] | L11-T1 | Quantization works | 90m |
| L11-T3 | L11 | W6 | Hephaestus | deep | [] | L11-T2 | Distillation works | 60m |
| L12-T1 | L12 | W6 | Hephaestus | deep | [] | L11-T3 | Generation works | 60m |
| L12-T2 | L12 | W6 | Hephaestus | deep | [] | L12-T1 | Security enforced | 45m |
| L12-T3 | L12 | W6 | Hephaestus | deep | [] | L12-T2 | Composition works | 60m |
| L13-T1 | L13 | W6 | Hephaestus | quick | [] | None | Health checks | 30m |
| L13-T2 | L13 | W6 | Hephaestus | quick | [] | None | Workflows work | 30m |
| L13-T3 | L13 | W6 | Hephaestus | deep | [] | None | CLI tools work | 45m |
| L13-T4 | L13 | W6 | Hephaestus | deep | [] | L13-T3 | E2E tests pass | 90m |

---

## 12. TDD-ORIENTED IMPLEMENTATION NOTES

### Test-First Checklist
Before writing each file:
1. ✅ Write test in `tests/unit/[layer]/test_[module].py`
2. ✅ Run test → FAIL (expected)
3. ✅ Implement module
4. ✅ Run test → PASS
5. ✅ Run quality gates
6. ✅ Commit

### Mock Strategy
- Use `unittest.mock` for external APIs
- Use `pytest.fixture` for shared test data
- Use `conftest.py` for cross-test configuration

### Test Categories
- **Happy path**: Basic functionality works
- **Edge cases**: Empty inputs, boundary values
- **Error cases**: Network failures, malformed input
- **Security**: Injection attempts, permission escalation

---

## 13. SUMMARY

| Metric | Value |
|--------|-------|
| **Total Sessions** | 18-24 |
| **Total Phases** | 7 (P0 + L1-L6) |
| **Total Tasks** | 88 |
| **Total Files** | ~60 new, ~15 enhanced |
| **Total Tests** | 190+ |
| **Total Commits** | 16 |
| **Success Rate Target** | 100% gates pass, 100% tests pass |

---

*ULTIMATE MASTER PLAN — v1.0 Implementation*
*Ready for Execution | All Research Complete | All Reviews Addressed*
