# N-Xyme MIND v0.1 — MVP Release Plan

> **Philosophy**: "Prove the core agent loop works before adding sophistication."
> **Status**: READY FOR IMPLEMENTATION
> **Timeline**: 3-5 sessions
> **Inspired by**: CrewAI (core-first), LangChain (clean abstractions), Mem0 (memory foundation)

---

## 1. EXECUTIVE SUMMARY

v0.1 establishes that the core agent loop functions: Sisyphus can execute work sessions using Prometheus plans via Hephaestus implementations, with MCP tools providing capability extension.

**What v0.1 Proves**:
- The delegation model (Sisyphus → Prometheus → Hephaestus) is sound
- MCP tools can be invoked and return results
- Basic session state management works
- Quality gates catch issues

**What v0.1 Excludes**:
- No knowledge graph
- No self-healing
- No sophisticated planning
- No security layer
- No self-learning

---

## 2. LAYERS INCLUDED

### L1: Core Foundation (Minimal)
| File | Status | Description |
|------|--------|-------------|
| `src/nxyme/core/governance.py` | NEW | Basic session state management |
| `src/nxyme/core/sentinel.py` | NEW | Simple watchdog for catastrophic failures |
| `src/nxyme/core/flight_recorder.py` | NEW | Minimal session logging (debugging) |
| `src/nxyme/core/skill_telemetry.py` | STUB | No-op metrics collection |
| `src/nxyme/core/delta_manifest.py` | NEW | Version identification only |

### L5: Orchestration (Core Only)
| File | Status | Description |
|------|--------|-------------|
| `src/orchestration/sisyphus.py` | NEW | Main loop execution |
| `src/orchestration/prometheus.py` | NEW | Load and validate plans from docs/ |
| `src/orchestration/hephaestus.py` | NEW | Map plans to executors |
| `src/orchestration/a2a_protocol.py` | STUB | Protocol definitions only |
| `src/orchestration/network_orchestrator.py` | STUB | Basic task routing |

### L6: MCP Servers (Minimal Set)
| Server | Status | Description |
|--------|--------|-------------|
| `packages/athena-context-mcp/` | ENHANCE | 7 tools — Enhance existing |
| `packages/nx-mind-mcp/` | ENHANCE | 7 tools — Enhance existing |
| `packages/trigger-guardian-mcp/` | ENHANCE | 6 tools — Enhance existing |
| `packages/memory-mcp/` | DEFERRED | v0.2 |
| `packages/eval-harness-mcp/` | DEFERRED | v0.3 |

### L13: Infrastructure (Support)
| Component | Status | Description |
|-----------|--------|-------------|
| `bin/quality-gates/` | EXISTS | 6 gates already exist |
| `tests/integration/test_core.py` | EXISTS | 4 tests passing |
| `pyproject.toml` | EXISTS | At root |
| `tests/conftest.py` | NEW | MockLLM fixtures |

---

## 3. IMPLEMENTATION TASKS

### P0: Pre-Implementation (1 session)
| Task | File | Agent | Category | QA |
|------|------|-------|----------|-----|
| P0-T1 | `tests/conftest.py` | Hephaestus | quick | pytest --collect-only works |
| P0-T2 | Verify quality gates | Hephaestus | quick | All 6 scripts exit 0 |
| P0-T3 | Verify pyproject.toml | Hephaestus | quick | pip install -e . succeeds |
| P0-T4 | Create MockLLM fixtures | Hephaestus | deep | MockLLM works in tests |

### W1: Core Foundation (1 session)
| Task | File | Agent | Category | QA |
|------|------|-------|----------|-----|
| W1-T1 | `src/nxyme/core/flight_recorder.py` | Hephaestus | deep | Session logging works |
| W1-T2 | `src/nxyme/core/governance.py` | Hephaestus | deep | Session state management works |
| W1-T3 | `src/nxyme/core/sentinel.py` | Hephaestus | deep | Watchdog detects failures |
| W1-T4 | `src/nxyme/core/skill_telemetry.py` | Hephaestus | quick | Stub returns empty metrics |
| W1-T5 | `src/nxyme/core/delta_manifest.py` | Hephaestus | quick | Version identification works |

### W2: Orchestration Core (1-2 sessions)
| Task | File | Agent | Category | QA |
|------|------|-------|----------|-----|
| W2-T1 | `src/orchestration/sisyphus.py` | Hephaestus | deep | Main loop executes |
| W2-T2 | `src/orchestration/prometheus.py` | Hephaestus | deep | Plans load and validate |
| W2-T3 | `src/orchestration/hephaestus.py` | Hephaestus | deep | Plans map to executors |
| W2-T4 | `src/orchestration/a2a_protocol.py` | Hephaestus | quick | Protocol definitions exist |
| W2-T5 | `src/orchestration/network_orchestrator.py` | Hephaestus | quick | Basic task routing works |

### W3: MCP Enhancement (1 session)
| Task | File | Agent | Category | QA |
|------|------|-------|----------|-----|
| W3-T1 | `packages/athena-context-mcp/` | Hephaestus | deep | 7 tools respond |
| W3-T2 | `packages/nx-mind-mcp/` | Hephaestus | deep | 7 tools respond |
| W3-T3 | `packages/trigger-guardian-mcp/` | Hephaestus | deep | 6 tools respond |

---

## 4. TESTING STRATEGY

### Unit Tests (25 tests)
| Layer | Test Count | Description |
|-------|------------|-------------|
| L1 Core | 10 | Session state, logging, versioning |
| L5 Orchestration | 10 | Plan loading, execution, routing |
| L6 MCP | 5 | Tool invocation, response validation |

### Integration Tests (4 tests — EXISTING)
| Test | Description |
|------|-------------|
| test_core.py | Core agent loop execution |
| test_triggers.py | Trigger engine integration |
| test_vpn.py | VPN rotator integration |
| test_configs.py | Configuration validation |

### Success Criteria
- [ ] Agent can receive a task
- [ ] Plan loads from Prometheus
- [ ] Hephaestus executes via MCP tools
- [ ] Result returns successfully
- [ ] All quality gates pass
- [ ] 29 tests passing (25 unit + 4 integration)

---

## 5. DEPENDENCIES

```
P0 (Pre-impl) ──► W1 (Core) ──► W2 (Orchestration) ──► W3 (MCP)
```

No parallel execution in v0.1 — each wave depends on the previous.

---

## 6. QUALITY GATES

| Gate | v0.1 |
|------|------|
| Gate 1: Type Check | ✓ |
| Gate 2: Lint | ✓ |
| Gate 3: Tests | ✓ (29 tests) |
| Gate 4: Coverage | 70% |
| Gate 5: Secrets | ✓ |
| Gate 6: Placeholders | ✓ |

---

## 7. ATOMIC COMMIT STRATEGY

| Commit | Message | Files |
|--------|---------|-------|
| 0 | `chore: add conftest.py, MockLLM fixtures` | P0 files |
| 1 | `feat(core): implement L1 Core Foundation (v0.1)` | 5 L1 files |
| 2 | `feat(orchestration): implement L5 Orchestration (v0.1)` | 5 L5 files |
| 3 | `feat(mcp): enhance 3 MCP packages (v0.1)` | 3 MCP packages |
| 4 | `test: add unit tests for v0.1` | 25 unit tests |
| 5 | `chore: run quality gates, tag v0.1.0` | Various |

---

## 8. RISK MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Core loop doesn't work | Medium | HIGH | Test incrementally, rollback to commit 0 |
| MCP tools fail | Medium | HIGH | Use MockLLM for testing |
| Session limit hit | HIGH | Medium | Checkpoint after each wave |

---

## 9. SESSION MANAGEMENT

| Session | Tasks | Checkpoint |
|---------|-------|------------|
| Session 1 | P0-T1 to P0-T4 | Commit 0 |
| Session 2 | W1-T1 to W1-T5 | Commit 1 |
| Session 3 | W2-T1 to W2-T5 | Commit 2 |
| Session 4 | W3-T1 to W3-T3 | Commit 3 |
| Session 5 | Tests + quality gates | Commits 4-5, tag v0.1.0 |

---

*v0.1 MVP Plan — Prove the core agent loop works*
*3-5 sessions | 18 tasks | ~15 new files | 29 tests*
