# N-Xyme MIND v0.2 — Memory + Observability Plan

> **Philosophy**: "Add memory and observability so we can see what the agent is doing."
> **Status**: DEPENDS ON v0.1
> **Timeline**: 4-6 sessions
> **Inspired by**: Mem0 (memory-first), LangSmith (observability)

---

## 1. EXECUTIVE SUMMARY

v0.2 establishes the feedback loop — understanding what the agent is doing and remembering basic context. This phase adds the observability and memory layers that make debugging and contextual operation possible.

**What v0.2 Adds**:
- Session-scoped memory (hierarchical, basic)
- Execution tracing (agent_tracer)
- Test harness (basic scenario runner)
- Enhanced telemetry (full metrics)
- User preference storage (dossier)

**What v0.2 Excludes**:
- No knowledge graph
- No self-healing
- No security sandboxing
- No runtime containerization

---

## 2. LAYERS INCLUDED (NEW + ENHANCED)

### L1: Core Foundation (Enhanced from v0.1)
| File | Status | Description |
|------|--------|-------------|
| `src/nxyme/core/skill_telemetry.py` | ENHANCE | Full implementation with basic metrics |
| `src/nxyme/core/delta_manifest.py` | ENHANCE | Add layer version tracking |

### L2: Memory System (Basic)
| File | Status | Description |
|------|--------|-------------|
| `src/memory/core/hierarchical.py` | NEW | Session-scoped memory only |
| `src/memory/core/dossier_system.py` | NEW | User preference storage |
| `src/memory/core/sleep_cycle.py` | STUB | Not yet active |
| `src/memory/core/knowledge_graph.py` | DEFERRED | v0.3 |
| `src/memory/core/vector_index.py` | DEFERRED | v0.3 |
| `src/memory/core/forgetting.py` | DEFERRED | v0.3 |
| `src/memory/core/compaction.py` | DEFERRED | v0.3 |
| `src/memory/core/dream_consolidate.py` | DEFERRED | v0.5 |
| `src/memory/core/crypto_identity.py` | DEFERRED | v0.5 |

### L8: Testing & Debugging (Added)
| File | Status | Description |
|------|--------|-------------|
| `src/testing/agent_tracer.py` | NEW | Execution trace collection |
| `src/testing/test_harness.py` | NEW | Basic scenario runner |
| `src/testing/regression_detector.py` | DEFERRED | v0.3 |

### L6: MCP Servers (Enhanced)
| Server | Status | Description |
|--------|--------|-------------|
| `packages/memory-mcp/` | NEW | Basic memory operations (NEW package) |

---

## 3. IMPLEMENTATION TASKS

### W1: Enhanced Core (1 session)
| Task | File | Agent | Category | QA |
|------|------|-------|----------|-----|
| W1-T1 | Enhance `skill_telemetry.py` | Hephaestus | deep | Full metrics collection works |
| W1-T2 | Enhance `delta_manifest.py` | Hephaestus | quick | Layer version tracking works |

### W2: Memory System (2 sessions)
| Task | File | Agent | Category | QA |
|------|------|-------|----------|-----|
| W2-T1 | `src/memory/core/hierarchical.py` | Hephaestus | ultrabrain | Session-scoped memory works |
| W2-T2 | `src/memory/core/dossier_system.py` | Hephaestus | deep | User preferences stored |
| W2-T3 | `src/memory/core/sleep_cycle.py` | Hephaestus | deep | Stub exists, not active |

### W3: Testing & Debugging (1 session)
| Task | File | Agent | Category | QA |
|------|------|-------|----------|-----|
| W3-T1 | `src/testing/agent_tracer.py` | Hephaestus | deep | Trace collection works |
| W3-T2 | `src/testing/test_harness.py` | Hephaestus | deep | Scenario runner works |

### W4: MCP Enhancement (1 session)
| Task | File | Agent | Category | QA |
|------|------|-------|----------|-----|
| W4-T1 | `packages/memory-mcp/` | Hephaestus | deep | Basic memory operations work |

---

## 4. TESTING STRATEGY

### Unit Tests (30 tests)
| Layer | Test Count | Description |
|-------|------------|-------------|
| L1 Enhanced | 5 | Enhanced telemetry, version tracking |
| L2 Memory | 15 | Session memory, dossier, sleep cycle stub |
| L8 Testing | 10 | Tracer output, scenario runner |

### Integration Tests (10 tests — NEW)
| Test | Description |
|------|-------------|
| Memory persistence | Memory persists across sessions |
| Telemetry capture | Metrics captured during execution |
| Tracer validation | Execution traces provide actionable debugging |
| Dossier retrieval | User preferences retrieved correctly |
| Memory MCP | Memory MCP operations work end-to-end |

### Success Criteria
- [ ] Agent remembers user preferences from previous sessions
- [ ] Execution traces provide actionable debugging information
- [ ] Memory persists across session restarts
- [ ] 69 tests passing (25 v0.1 + 30 unit + 10 integration + 4 existing)

---

## 5. DEPENDENCIES

```
v0.1 Complete ──► W1 (Enhanced Core) ──► W2 (Memory) ──► W3 (Testing) ──► W4 (MCP)
```

---

## 6. QUALITY GATES

| Gate | v0.2 |
|------|------|
| Gate 1: Type Check | ✓ |
| Gate 2: Lint | ✓ |
| Gate 3: Tests | ✓ (69 tests) |
| Gate 4: Coverage | 75% |
| Gate 5: Secrets | ✓ |
| Gate 6: Placeholders | ✓ |

---

## 7. ATOMIC COMMIT STRATEGY

| Commit | Message | Files |
|--------|---------|-------|
| 0 | `feat(core): enhance telemetry and version tracking (v0.2)` | 2 L1 files |
| 1 | `feat(memory): implement basic memory system (v0.2)` | 3 L2 files |
| 2 | `feat(testing): add agent tracer and test harness (v0.2)` | 2 L8 files |
| 3 | `feat(mcp): add memory-mcp package (v0.2)` | memory-mcp |
| 4 | `test: add unit + integration tests for v0.2` | 40 tests |
| 5 | `chore: run quality gates, tag v0.2.0` | Various |

---

## 8. RISK MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Memory too complex | HIGH | HIGH | Start with SQLite only, skip vector DB |
| Tracer overhead | Medium | Medium | Sample traces, don't trace everything |
| Session limit hit | HIGH | Medium | Checkpoint after each wave |

---

*v0.2 Memory + Observability Plan — See what the agent is doing*
*4-6 sessions | 8 tasks | ~8 new files | 40 new tests*
