# N-Xyme Bulletproof Master Plan
## Remaining Work: OMO Synthesis + Refactoring + Compilation

**Generated**: 2026-04-12
**Status**: PENDING EXECUTION

---

## Executive Summary

All 5 phases implemented with 100% benchmark pass rate (31/31 tests). Remaining work:
1. **OMO Synthesis** - Integrate 40+ hooks into N-Xyme
2. **Modular Refactoring** - Apply plug-and-play architecture
3. **Compilation Evaluation** - C++/Rust decision for performance-critical paths

**Success Criteria**: Every task has verification, error handling, and rollback plan.

---

## Phase A: OMO Synthesis (Priority: HIGH)

### A.1 Research Consolidation (Already Done)
- ✅ Librarian agent completed OMO v3.14.0→v3.17.0 research
- ✅ 40+ hooks identified: `agent-usage-reminder`, `keyword-detector`, `context-window-monitor`, `todo-continuation-enforcer`, etc.
- ✅ Category-based delegation patterns found
- ✅ Session recovery patterns identified

### A.2 Hook Integration Strategy

**Pattern 1: Keyword Trigger Hooks** (Passive Monitoring)
| Hook | N-Xyme Integration | Risk |
|------|-------------------|------|
| `keyword-detector` | Add to `orchestration/__init__.py` spawn() - detect "fix", "implement", "debug" | Low |
| `context-window-monitor` | Add to MCP server init - warn before 80% usage | Low |
| `agent-usage-reminder` | Add to outcome logging - periodic health checks | Low |

**Pattern 2: Category Delegation** (Active Routing)
| OMO Pattern | N-Xyme Equivalent | Gap |
|-------------|------------------|-----|
| Category-based agent selection | `AdaptiveRouter` in intelligence | Need to add category hints to spawn |
| Background agents | `run_in_background=True` in task() | Already implemented ✅ |
| Hook cadence system | `circuit_breaker.py` | Already implemented ✅ |

**Pattern 3: Session Recovery** (Resilience)
| OMO Pattern | N-Xyme Implementation |
|-------------|----------------------|
| Session state persistence | `nx-brain-mcp/mind_get_mind_state` ✅ |
| Agent handoff | `packages/orchestration/handoff.py` ✅ |
| Context injection | `orchestration/__init__.py` inject_memory ✅ |

### A.3 OMO Synthesis Tasks

```
A.3.1 Add keyword detection to spawn() 
      → File: packages/orchestration/__init__.py
      → Add: _detect_keywords(user_input) before routing
      → Verification: unit test with "fix bug", "add feature" inputs

A.3.2 Add context window monitoring
      → File: packages/orchestration/mcp_server.py
      → Add: check_context_usage() → warn if >80%
      → Verification: test with 100k token context

A.3.3 Add session recovery hooks
      → File: packages/orchestration/auto_reflection.py
      → Add: on_stuck() → save state, on_retry() → restore state
      → Verification: simulate stuck, verify recovery

A.3.4 Synthesize category delegation
      → File: packages/intelligence/router.py
      → Add: category_hint parameter to spawn
      → Verification: benchmark routing with/without hints
```

### A.4 Error Handling (OMO Synthesis)
- **If hook fails**: Log error, continue execution (fail-safe)
- **If hook times out**: Skip after 100ms, log warning
- **If hook crashes**: Catch exception, fallback to default behavior

---

## Phase B: Modular Refactoring (Priority: HIGH)

### B.1 Architecture Target (from Oracle)

```
nxyme_core/                    # Core interfaces (versioned, stable)
├── interfaces.py            # ABCs + protobuf definitions
├── config.py                # Schema for module configs
└── registry.py               # Plug-and-play discovery

modules/
├── nx_brain_mcp/            # MCP tool implementations (stay Python)
├── memory_core/             # Storage/retrieval layer (Rust candidate)
├── learning_engine/         # ML training/inference (C++ candidate)
├── orchestration/           # Agent lifecycle (stay Python)
└── intelligence/             # Intent prediction (stay Python)
```

### B.2 Interface Definitions

**Required per module**:
```python
class NXymeModule(ABC):
    @property
    def version(self) -> str: ...
    
    def health_check(self) -> Dict[str, Any]: ...
    
    def shutdown(self) -> None: ...
```

**Module boundaries** (no cross-module imports):
- `nx_brain_mcp` ↔ `memory_core`: Via MCP calls only
- `learning_engine` ↔ `orchestration`: Via event callbacks
- `intelligence` ↔ `orchestration`: Via routing results

### B.3 Refactoring Tasks

```
B.3.1 Create nxyme_core/interfaces.py
      → Define NXymeModule ABC
      → Define version schema (semver)
      → Define health_check response schema
      → Verification: mypy check, all modules implement

B.3.2 Create nxyme_core/registry.py
      → Module discovery via entry_points
      → Lazy loading with importlib
      → Verification: add dummy module, discover succeeds

B.3.3 Create nxyme_core/config.py
      → JSON schema for module configs
      → Validation on load
      → Verification: invalid config fails fast

B.3.4 Refactor nx_brain_mcp to use registry
      → Replace hard imports with registry.get()
      → Verification: all existing tests pass

B.3.5 Add health_check to each module
      → memory_core: store availability, index freshness
      → learning_engine: model loaded, routing functional
      → orchestration: agent pool healthy
      → intelligence: router responding
      → Verification: curl localhost:port/health returns 200

B.3.6 Create mock modules for testing
      → mock_memory_core.py (in-memory store)
      → mock_learning_engine.py (static predictions)
      → Verification: pytest with mocks passes
```

### B.4 Error Handling (Refactoring)
- **If module missing**: Raise ModuleNotFoundError with suggestion
- **If version mismatch**: Warn but continue with fallback
- **If health check fails**: Mark module degraded, not failed
- **If config invalid**: Fail fast at startup, not runtime

---

## Phase C: Compilation Evaluation (Priority: MEDIUM)

### C.1 Profiling Strategy

**Before any C++/Rust**:
1. Run `cProfile` on comprehensive benchmark
2. Identify top 20% functions taking 80% time
3. Hot paths: similarity search, vector operations, pattern matching

### C.2 Candidates for Compilation

| Module | Current | Recommendation | Rationale |
|--------|---------|---------------|-----------|
| memory_core/stores/vector.py | Python | **Rust via pybind11** | 10-50x speedup on similarity search |
| learning_engine/tool_patterns/analyzer.py | Python | **C++ via pybind11** | Matrix ops, pattern matching |
| intelligence/router.py | Python | Stay Python | Rapid iteration, A/B testing |
| orchestration/spawn.py | Python | Stay Python | I/O bound, async-heavy |

### C.3 Compilation Tasks

```
C.3.1 Profile current implementation
      → Run: python -m cProfile -o profile.stats bin/comprehensive_benchmark.py
      → Analyze: python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"
      → Output: List of hot paths with timing

C.3.2 Create Rust extension skeleton
      → File: nxyme_core/rust/src/lib.rs
      → Build: maturin develop (pyo3)
      → Verify: Python import works

C.3.3 Implement vector similarity in Rust
      → File: nxyme_core/rust/src/vector.rs
      → Algorithm: cosine similarity, HNSW indexing
      → Benchmark: vs current Python implementation

C.3.4 Decision gate
      → If Rust > 10x faster → keep
      → If Rust 2-10x faster → optional, profile first
      → If Rust < 2x faster → stay Python
```

### C.4 Error Handling (Compilation)
- **If build fails**: Revert to Python, log build error
- **If performance worse**: Revert, analyze why
- **If import fails**: Fall back to Python implementation

---

## Execution Order

```
Week 1:
├── A.3.1 Keyword detection (low risk, high value)
├── A.3.2 Context monitoring (low risk)
└── B.3.1-B.3.3 Core interfaces (foundation)

Week 2:
├── A.3.3 Session recovery hooks
├── B.3.4-B.3.6 Refactor nx_brain_mcp + health checks
└── A.3.4 Category delegation

Week 3:
├── C.3.1 Profiling
├── C.3.2 Rust skeleton
└── C.3.3 Vector similarity

Week 4:
├── C.3.4 Decision gate
├── Full integration test
└── Final benchmark
```

---

## Verification Checklist

### Every Task Must Have:
- [ ] Unit test (or inline verification)
- [ ] Error case handled
- [ ] Rollback plan (git revert or flag)
- [ ] Success metric defined

### Phase Completion Gates:
- **A (OMO)**: 4/4 tasks done + 90% hook coverage
- **B (Refactor)**: 6/6 tasks done + all tests pass
- **C (Compile)**: Decision made + benchmark showing impact

---

## Rollback Plans

| Task | Rollback Command |
|------|------------------|
| A.3.1-A.3.4 | `git checkout packages/orchestration/` |
| B.3.1-B.3.6 | `git checkout nxyme_core/` + delete if new |
| C.3.2-C.3.4 | `rm -rf nxyme_core/rust/` + `git checkout packages/` |

---

## Dependencies

```
A.3.1 (keyword)      → requires: packages/orchestration/__init__.py (exists)
A.3.2 (context)      → requires: packages/orchestration/mcp_server.py (exists)
A.3.3 (recovery)    → requires: packages/orchestration/auto_reflection.py (exists)
A.3.4 (category)    → requires: packages/intelligence/router.py (exists)

B.3.1 (interfaces)  → NEW FILE, blocks B.3.2-B.3.6
B.3.2 (registry)    → blocks B.3.4
B.3.3 (config)      → blocks B.3.4
B.3.4 (refactor)    → blocks B.3.5-B.3.6
B.3.5 (health)      → independent
B.3.6 (mocks)       → independent

C.3.1 (profile)     → blocks C.3.2-C.3.4
C.3.2-C.3.4         → independent of A, B
```

---

## Risk Matrix

| Task | Complexity | Risk | Mitigation |
|------|------------|------|------------|
| A.3.1 | Low | Hook never fires | Add to spawn() always, not conditional |
| A.3.2 | Low | Context check slow | Cache result, update every 10 calls |
| A.3.3 | Medium | Recovery state lost | Persist to SQLite before recovery |
| A.3.4 | Medium | Category mismatch | Default to current routing if no hint |
| B.3.1 | Medium | Interface change breaks tests | Keep backwards compatible |
| B.3.2 | Medium | Discovery fails | Fallback to hardcoded list |
| B.3.3 | Low | Config invalid | Fail fast with clear message |
| B.3.4 | High | Import breakage | Test each module individually first |
| C.3.1 | Low | Profile data unclear | Run twice, compare |
| C.3.2 | High | Build system issues | Use maturin, well-documented |
| C.3.3 | High | Algorithm wrong | Validate against Python first |
| C.3.4 | Low | Decision unclear | Default: stay Python |

---

## Success Metrics

| Metric | Target | Current | Delta |
|--------|--------|---------|-------|
| Benchmark pass rate | 100% | 100% | - |
| Hook coverage (OMO) | 90% (36/40) | 0% | +36 |
| Module health checks | 5/5 working | 0/5 | +5 |
| Profile data | Available | N/A | - |
| Rust extension | Compiles | N/A | - |

---

## Open Questions

1. **Q**: Should we upgrade OMO from v3.14.0 to v3.17.0?
   - **A**: Not required - N-Xyme has equivalent functionality. Upgrade if using OMO-specific hooks.

2. **Q**: Which modules need the most performance improvement?
   - **A**: Await C.3.1 profiling results. Likely: vector similarity, pattern matching.

3. **Q**: Should we use protobuf or JSON for interfaces?
   - **A**: JSON for simplicity (proto requires build step). Protobuf later if needed.

4. **Q**: How do we handle module versioning?
   - **A**: Semver in each module's `__version__` + core registry validates.

---

## Next Action

**START WITH**: A.3.1 (keyword detection) - lowest risk, highest value