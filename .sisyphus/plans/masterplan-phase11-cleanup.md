# N-Xyme_MIND Masterplan — Phase 11: System Cleanup & Restructure

> Created: 2026-04-07 | Priority: P0 (Foundation Fix)
> Source: 3-agent audit (Explore + Librarian + Oracle)
> Goal: Industry gold standard architecture — clean, consolidated, production-ready

---

## Current State Assessment

### What Works ✅
- **Memory Core**: 18 modules import clean, typed ABCs, migrations, hybrid search, cognitive layer
- **Learning Engine**: Q-Learning, AdaptiveRouter, OutcomeLogger, TaskWrapper, circuit breaker, retry logic
- **Retrieval Pipeline**: 6-stage execution (analysis → retrieve → RRF → MMR → cross-encoder → return)
- **Tests**: 232 passing, 7 e2e tests covering full pipeline
- **MCP Servers**: 4 servers with 12 tools exposed
- **Commits**: 13 on GitHub, all pushed

### What's Broken ❌
| Issue | Location | Impact | Severity |
|-------|----------|--------|----------|
| Duplicate `learning_engine` symlink | `packages/learning_engine` → `learning-engine` | Import confusion, git conflicts | P0 |
| 5 orphaned venvs inside packages/ | `nx-mind-mcp/venv`, `athena-context-mcp/venv`, etc. | Disk bloat, dependency drift | P0 |
| `hindsight_mcp.py` orphaned at root | Not in packages/, not wired | Can't be used, dead code | P1 |
| Routing split: intelligent_router vs learning_engine | Both claim routing authority | Conflicting decisions | P1 |
| 70+ dead test files | `.trash/tests-dead/` | Git bloat, confusion | P2 |
| 26 dead source dirs | `.trash/src-dead/` | Git bloat | P2 |
| `.legacy/` duplicates | 3 files duplicated from packages/ | Confusion | P2 |
| Empty `src/` dir | Only contains `.sisyphus/` | Confusion | P2 |
| 92 unused BMAD workflows | `_bmad/` YAML files | Dead code | P2 |
| Missing `__init__.py` files | `infrastructure/`, `local_llm/`, `data/` | Import issues | P2 |
| 7 MCP servers | Should be 3-4 | Complexity overhead | P2 |
| `hindsight-api` not installed | bootstrap.sh never ran | Missing memory consolidation | P1 |

### Multi-Venv Context (Deferred)
Multi-venvs were originally for running models in optimal Python environments (e.g., different CUDA versions, conflicting dependency trees). This is valid but deferred — we'll address it after structural cleanup.

---

## Target Architecture (Industry Gold Standard)

### Correct Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────┐
│                        platform_layer                               │
│  (CLI, TUI, dashboards, monitoring)                                 │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        infrastructure                               │
│  (resilience, proxy, network, VPN, circuit breakers, fallbacks)     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
┌──────────────────────────┐  ┌──────────────────────────────────────┐
│      memory_core         │  │          orchestration               │
│  • stores (vector,       │  │  • agents (sisyphus, hephaestus,     │
│    relational, graph)    │  │      oracle, explore, librarian)     │
│  • retrievers (TEMPR,    │  │  • tasks, sessions, governance       │
│    keyword, fusion)      │  │  • BMAD workflow integration         │
│  • cognitive (forgetting,│  │  • skill loading                     │
│    reconsolidation,      │  │                                      │
│    trust, priority)      │  │                                      │
│  • pipeline (6-stage)    │  │                                      │
│  • hindsight (LLM memory │  │                                      │
│    consolidation)        │  │                                      │
└──────────────┬───────────┘  └──────────────┬───────────────────────┘
               │                             │
               └──────────────┬──────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        intelligence                                 │
│  • router (model selection, VPN rotation, rate limiting)            │
│  • delegation (complexity scoring, agent optimization)              │
│  • review (security gates, quality checks)                          │
│  • learning (Q-Learning, outcomes, routing weights)                 │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
┌──────────────────────────┐  ┌──────────────────────────────────────┐
│  intelligent_router_mcp  │  │     unified-memory-mcp               │
│  (reads weights from LE, │  │  (memory_core + hindsight +          │
│   applies fallback chain)│  │   athena-context + nx-mind merged)   │
└──────────────────────────┘  └──────────────────────────────────────┘
```

### MCP Server Consolidation

| Current (7) | Target (4) | Rationale |
|-------------|------------|-----------|
| `nx-mind-mcp` | `unified-memory-mcp` | Merge all memory-related MCPs |
| `athena-context-mcp` | `unified-memory-mcp` | Same domain, redundant |
| `hindsight_mcp` | `unified-memory-mcp` | Memory consolidation layer |
| `intelligent_router_mcp` | `intelligent_router_mcp` | Keep — routing is separate domain |
| `trigger-guardian-mcp` | `orchestration/` (native) | Triggers belong in orchestration |
| `quality-gates-mcp` | `quality-gates-mcp` | Keep — specialized tool |
| `sqlite-mcp` | Remove | Use direct SQLite, no MCP needed |

---

## Extended Phase 11 Masterplan — With Optimal Delegation

> Based on: 3-agent audit (Explore + Librarian + Oracle)
> Industry standards: uv workspaces, MCP consolidation, single venv, comprehensive .gitignore

### Current State Inventory (17 Issues Found)

**P0 — CRITICAL (5 items)**
| # | Issue | Location | Action |
|---|-------|----------|--------|
| 1 | Duplicate learning_engine | `packages/learning_engine` (symlink) → `learning-engine` | Delete symlink |
| 2 | Dual routing implementations | `intelligent_router_mcp` vs `infrastructure/proxy/intelligent_router.py` | Merge into learning_engine |
| 3 | MCP venv path inconsistency | `venv` vs `.venv` vs `venvs/athena` across 12 MCPs | Standardize to single venv |
| 4 | Missing `__init__.py` | `packages/data/`, `packages/data/proxy/` | Create files |
| 5 | Orphaned routing DB | `packages/data/proxy/routing_outcomes.db` | Remove |

**P1 — HIGH (5 items)**
| # | Issue | Location | Action |
|---|-------|----------|--------|
| 6 | .gitignore gaps | Root `.gitignore` missing `__pycache__/`, `.egg-info/`, `venv/`, `.venv/` | Update |
| 7 | Dead directories | `.legacy/`, `.trash/src-dead/`, `.trash/tests-dead/` | Archive or delete |
| 8 | `.ruff_cache/` pollution | 16 subdirs | Add to `.gitignore` |
| 9 | venv naming | 3 MCP packages use `venv`, 1 uses `.venv` | Rename all to `.venv` |
| 10 | `.egg-info` artifacts | 5 MCP packages | Remove all |

**P2 — MEDIUM (4 items)**
| # | Issue | Location | Action |
|---|-------|----------|--------|
| 11 | MCP commands inconsistent | `opencode.json` — 21 MCPs, mixed python paths | Standardize |
| 12 | Missing `__main__.py` | `nx-mind-mcp`, others | Add for consistency |
| 13 | Root venv confusion | `.venv` vs `venv` both exist | Choose `.venv`, remove other |
| 14 | `data/proxy` structure | `packages/data/proxy/` has files but no `__init__.py` | Fix or remove |

**P3 — LOW (3 items)**
| # | Issue | Location | Action |
|---|-------|----------|--------|
| 15 | `__pycache__` pollution | `packages/*/__pycache__/` | Add to `.gitignore`, remove |
| 16 | `local_llm` isolation | `packages/local_llm/` has no dependencies | Integrate or document |
| 17 | `infrastructure/proxy` bloat | 20+ modules, some duplicate learning_engine | Audit for dedup |

---

### Optimal Delegation Chain (4 Hephaestus Delegations)

```
Sisyphus (Orchestrator)
    ↓
┌─────────────────────────────────────────────────────────────┐
│ WAVE 1 (Parallel — Independent, 15min)                     │
├─────────────────────────────────────────────────────────────┤
│ Hephaestus #1: P0 Critical Fixes                           │
│   - Delete symlink packages/learning_engine                │
│   - Create packages/data/__init__.py                       │
│   - Create packages/data/proxy/__init__.py                 │
│   - Remove orphaned routing DB                             │
│   - Delete .egg-info directories (5 packages)              │
│                                                            │
│ Hephaestus #2: .gitignore + Dead Code Cleanup              │
│   - Update .gitignore with all missing patterns            │
│   - Delete .legacy/ directory                              │
│   - Delete .ruff_cache/ directory                          │
│   - Delete __pycache__ directories                         │
│   - Clean root .venv vs venv confusion                     │
└─────────────────────────────────────────────────────────────┘
    ↓ (Verify Wave 1 — both must pass)
┌─────────────────────────────────────────────────────────────┐
│ WAVE 2 (Sequential — T11.3 depends on T11.1, 1hr)          │
├─────────────────────────────────────────────────────────────┤
│ Hephaestus #3: Routing Consolidation                       │
│   - Move MODEL_CAPABILITIES from intelligent_router_mcp    │
│     → learning_engine                                       │
│   - Forward route_task() from intelligent_router_mcp       │
│     → learning_engine                                       │
│   - Update imports in intelligent_router_mcp/__init__.py   │
│   - Backup routing DB before migration                     │
│                                                            │
│ Hephaestus #4: MCP Config Standardization                  │
│   - Standardize all MCP commands to use single venv        │
│   - Remove duplicate MCP entries from opencode.json        │
│   - Add __main__.py to MCP packages missing it             │
│   - Update hindsight_mcp integration                       │
└─────────────────────────────────────────────────────────────┘
    ↓ (Verify Wave 2)
┌─────────────────────────────────────────────────────────────┐
│ WAVE 3 (Sequential — Final Cleanup, 30min)                 │
├─────────────────────────────────────────────────────────────┤
│ Hephaestus #5: infrastructure/proxy Audit                  │
│   - Audit 20+ modules for duplicates with learning_engine  │
│   - Remove or consolidate duplicate code                   │
│   - Fix data/proxy structure                               │
│   - Integrate or document local_llm                        │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ FINAL: Verify all imports, run tests, commit, push         │
└─────────────────────────────────────────────────────────────┘
```

### Delegation Prompts (Ready to Fire)

**Hephaestus #1 (P0 Critical):**
```
TASK: Fix 5 critical issues in N-Xyme_MIND codebase.
1. Delete symlink: packages/learning_engine (symlink → learning-engine)
2. Create packages/data/__init__.py (empty file)
3. Create packages/data/proxy/__init__.py (empty file)
4. Delete orphaned DB: packages/data/proxy/routing_outcomes.db
5. Delete ALL .egg-info directories: find packages -name "*.egg-info" -type d -exec rm -rf {} +
MUST: Read files before deleting. Run py_compile on packages/ after. Do NOT commit.
MUST NOT: Delete learning-engine directory. Delete any non-.egg-info directories.
CONTEXT: Working directory: /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
```

**Hephaestus #2 (.gitignore + Dead Code):**
```
TASK: Clean up dead code and update .gitignore.
1. Read current .gitignore, add: __pycache__/, *.egg-info/, .ruff_cache/, venv/, .venv/, venvs/, .pytest_cache/, .coverage, htmlcov/, .mypy_cache/, dist/, build/, *.whl
2. Delete .legacy/ directory (all contents)
3. Delete .ruff_cache/ directory (all contents)
4. Delete ALL __pycache__ directories: find . -name "__pycache__" -type d -exec rm -rf {} +
5. If both .venv/ and venv/ exist at root, keep .venv/, delete venv/
MUST: Read .gitignore before editing. Verify deletions with ls. Do NOT commit.
MUST NOT: Delete .venv/ if it's the only venv. Delete any source code.
CONTEXT: Working directory: /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
```

**Hephaestus #3 (Routing Consolidation):**
```
TASK: Merge routing logic from intelligent_router_mcp into learning_engine.
1. Read intelligent_router_mcp/__init__.py — find MODEL_CAPABILITIES dict
2. Read learning_engine/mcp_server.py — find route_task function
3. Move MODEL_CAPABILITIES from intelligent_router_mcp → learning_engine/mcp_server.py
4. Update intelligent_router_mcp/__init__.py to import route_task from learning_engine instead of implementing its own
5. Backup routing DB: cp data/intelligent_router/routing_outcomes.db data/intelligent_router/routing_outcomes.db.bak
MUST: Read ALL reference files before writing. Preserve existing route_task functionality. Run py_compile on both files.
MUST NOT: Break existing MCP tools. Delete intelligent_router_mcp entirely. Lose routing history.
CONTEXT: Working directory: /home/nxyme/N-Xyme_CODE/N-Xyme_MIND. intelligent_router_mcp handles MODEL routing, learning_engine handles AGENT routing — merge into single source of truth.
```

**Hephaestus #4 (MCP Config Standardization):**
```
TASK: Standardize MCP server configuration in opencode.json.
1. Read opencode.json — find all MCP server entries
2. Standardize ALL python paths to use venvs/athena/bin/python (the shared venv)
3. Remove duplicate MCP entries (athena-context merged into athena, sqlite-mcp removed)
4. Add __main__.py to packages that are missing it: nx-mind-mcp, trigger-guardian-mcp
5. Update hindsight_mcp entry to use proper package path
MUST: Read opencode.json before editing. Validate JSON after editing. Run py_compile on all __main__.py files.
MUST NOT: Break working MCP servers. Remove servers that are actually used. Change npx-based MCPs.
CONTEXT: Working directory: /home/nxyme/N-Xyme_CODE/N-Xyme_MIND. 21 MCP servers currently, target is 12-15 after consolidation.
```

**Hephaestus #5 (Infrastructure Audit):**
```
TASK: Audit and clean up infrastructure/proxy and related packages.
1. Read all files in packages/infrastructure/proxy/ (20+ modules)
2. Identify duplicates with learning_engine (intelligent_router.py, learning_engine.py)
3. Remove or consolidate duplicate modules
4. Fix packages/data/proxy structure — either add proper __init__.py or remove
5. Integrate or document packages/local_llm/
MUST: Read ALL files before deleting. Check for imports before removing modules. Run py_compile after.
MUST NOT: Break infrastructure package. Remove modules that are imported elsewhere.
CONTEXT: Working directory: /home/nxyme/N-Xyme_CODE/N-Xyme_MIND. infrastructure/proxy has grown to 20+ modules, many duplicate learning_engine functionality.
```

### Effort Estimate (Updated)

| Wave | Tasks | Effort | Parallel? |
|------|-------|--------|-----------|
| Wave 1: Critical + Cleanup | Hephaestus #1 + #2 | 15min | ✅ Parallel |
| Wave 2: Routing + MCP Config | Hephaestus #3 + #4 | 1hr | ❌ Sequential |
| Wave 3: Infrastructure Audit | Hephaestus #5 | 30min | ❌ Sequential |
| **Total** | **5 delegations** | **~1.75hr** | |

### Risk Assessment (Updated)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Breaking imports after symlink removal | Low | Medium | Test all imports before commit |
| Routing merge loses model capabilities | Medium | High | Backup MODEL_CAPABILITIES before merge |
| MCP config breaks opencode.json | Medium | High | Validate JSON after every edit |
| infrastructure/proxy audit removes needed code | Low | Medium | Check imports before deleting |
| venv standardization breaks MCP servers | Medium | High | Test each MCP after config change |

### Success Criteria (All Must Pass)

- [ ] No symlink confusion in packages/
- [ ] No orphaned venvs in packages/
- [ ] `.legacy/` deleted
- [ ] `.ruff_cache/` deleted
- [ ] All packages have `__init__.py`
- [ ] `.gitignore` excludes all build artifacts
- [ ] Single routing source of truth (learning_engine)
- [ ] intelligent_router_mcp forwards to learning_engine
- [ ] MCP commands standardized in opencode.json
- [ ] All 232 tests still pass
- [ ] All imports work cleanly
- [ ] Committed and pushed

---

*Extended masterplan created: 2026-04-07 | 5 Hephaestus delegations, ~1.75hr total*

---

# Phase 12: Claude Code Pattern Extraction (from ant-source-code)

> Source: `/home/nxyme/Documentos/ant-source-code-main/` — **Claude Code v2.1.88 leaked source** (1,903 files, 35MB)
> Goal: Extract production-grade agent patterns before deletion

## What This Codebase Is

**Claude Code by Anthropic** — the industry standard for production AI coding agents. Not just "Claude with bash access" — a **governed execution environment** with 1,729 lines of agent loop engineering.

## Gold Patterns to Extract (Priority Order)

### P0: Core Agent Loop (query.ts — 1,729 lines)

| Pattern | Claude Code Implementation | N-Xyme_MIND Port |
|---------|---------------------------|------------------|
| **State machine loop** | `while(true)` with state object, 9 continue points | `asyncio` coroutine with explicit state dataclass |
| **10-step iteration** | Context → Budget → API → Stream → Error → Hooks → Budget → Tools → Attach → Loop | Same 10 steps in Python |
| **Circuit breakers** | `hasAttemptedReactiveCompact`, token budget tracking | Same pattern with Python dataclasses |
| **Tool call detection** | Watch for `tool_use` blocks during streaming (not `stop_reason`) | Stream parsing for tool calls |

**File to port**: `packages/orchestration/agent_loop.py` (new)

### P1: 4-Stage Context Compression

| Stage | What | When |
|-------|------|------|
| 1. Snip Compact | Trims overly long individual messages | Always first |
| 2. Micro Compact | Finer-grained editing based on `tool_use_id` | If stage 1 insufficient |
| 3. Context Collapse | Folds inactive regions into summaries | If stage 2 insufficient |
| 4. Auto Compact | Full compression when tokens approach threshold | Last resort |

**Rule**: Lightweight first, escalate only when needed. Never skip to heavy summarization.

**File to port**: `packages/memory_core/compression.py` (new, 4 compressor classes)

### P1: Streaming Tool Execution

```
Traditional: [LLM generates 5 calls] → [T1] → [T2] → [T3] → [T4] → [T5]  = 30s
Claude Code: [LLM generates 5 calls]
              [T1][T2][T3][T4]................... = 18s (40% faster)
```

**File to port**: `packages/orchestration/streaming_executor.py` (new)

### P1: Permission Modes (6 levels)

| Mode | Capabilities | Use Case |
|------|-------------|----------|
| `default` | Read-only | Sensitive work, first use |
| `acceptEdits` | Read + Edit | Iterating while gating commands |
| `plan` | Read + Plan | Research before modification |
| `auto` | All actions + safety classifier | Long-running tasks |
| `bypassPermissions` | All actions, no checks | Isolated containers only |
| `dontAsk` | Pre-approved tools only | Locked-down environments |

**File to port**: `packages/orchestration/permissions.py` (extend existing)

### P2: Tool Validation Layer (14-step pipeline)

1. Input validation → 2. Permission checks → 3. Pre-tool hooks → 4. Execution → 5. Post-tool hooks → 6. Analytics → 7. Result formatting → 8. Error handling → 9. Retry logic → 10. Cache check → 11. Rate limiting → 12. Output validation → 13. Context injection → 14. State update

**File to port**: `packages/orchestration/tool_pipeline.py` (new)

### P2: Hook System (Policy Injection)

| Hook | When | What |
|------|------|------|
| `PreToolUse` | Before every tool execution | Allow/deny/ask/defer |
| `PermissionRequest` | At approval boundary | Modify permissions |
| `PostToolUse` | After execution | Append context |
| `Compact` | Before/after compaction | Preserve critical info |

**File to port**: `packages/orchestration/hooks.py` (new)

### P2: Hierarchical Context Loading (CLAUDE.md pattern)

```
Current working directory
  ↓ (walks up tree)
Parent directories (all CLAUDE.md files)
  ↓
Path-scoped rules (auto-load when files in subdirectory read)
  ↓
Skills (matching current task)
  ↓
Auto memory (learned patterns from past sessions)
  ↓
MCP tool names
```

**File to port**: `packages/memory_core/context_loader.py` (new)

### P3: Subagent Isolation

- Custom prompts per subagent
- Tool allowlists/denylists
- Worktree isolation (Git worktree for blast-radius control)
- Permission modes per subagent
- Persistent memory options

**File to port**: `packages/orchestration/subagent_isolation.py` (new)

### P3: Static/Dynamic Prompt Boundary

```
SYSTEM_PROMPT = [static cacheable section] + SYSTEM_PROMPT_DYNAMIC_BOUNDARY + [dynamic per-request section]
```

If two requests share same static prefix byte-for-byte → API caches it → real cost savings.

**File to port**: `packages/orchestration/prompt_assembler.py` (new)

---

## Phase 12 Action Plan

| Task | Files | Effort | Priority |
|------|-------|--------|----------|
| T12.1: Agent loop state machine | `packages/orchestration/agent_loop.py` | 4hr | P0 |
| T12.2: 4-stage compression | `packages/memory_core/compression.py` | 3hr | P1 |
| T12.3: Streaming tool execution | `packages/orchestration/streaming_executor.py` | 3hr | P1 |
| T12.4: Permission modes | `packages/orchestration/permissions.py` | 2hr | P1 |
| T12.5: Tool validation pipeline | `packages/orchestration/tool_pipeline.py` | 3hr | P2 |
| T12.6: Hook system | `packages/orchestration/hooks.py` | 2hr | P2 |
| T12.7: Context loader | `packages/memory_core/context_loader.py` | 2hr | P2 |
| T12.8: Subagent isolation | `packages/orchestration/subagent_isolation.py` | 4hr | P3 |
| T12.9: Prompt assembler | `packages/orchestration/prompt_assembler.py` | 2hr | P3 |
| **Total** | **9 files** | **25hr** | |

---

# Phase 13: Local LLM Optimization

> Source: Existing Local LLM Optimization Master Plan
> Goal: Transform Ollama into production-grade system rivaling cloud APIs

## Current State

| Component | Status | Notes |
|-----------|--------|-------|
| Ollama API | ✅ Working | qwen2.5-coder:7b, llama3.2:3b available |
| Tool Calling | ✅ Working | 2-pass pipeline: model → tools → results |
| MCP Tools | ✅ Done | 23 tools with handlers registered |
| Generation Params | ✅ Optimized | temperature, top_p, num_ctx, etc. |
| Tool Schemas | ✅ Enhanced | Rich descriptions with use cases |
| Model Routing | ✅ Working | intelligent_router integration |

## Phase 13.1: RAG Context Injection (Pending)

**What**: Before LLM answers, search relevant context and inject into prompt.

**Implementation**: `packages/local_llm/rag_injector.py`
```python
class RAGContextInjector:
    async def inject_context(self, query: str, docs: List[Dict]) -> str:
        # 1. Embed query via Ollama (nomic-embed-text)
        # 2. Retrieve top-K relevant docs
        # 3. Build context string
        # 4. Return enhanced prompt
```

**When to use**: Code generation (inject patterns), debugging (inject errors), architecture questions (inject AGENTS.md)

## Phase 13.2: Tool Validation Layer (Pending)

**What**: Validate tool call arguments before execution.

**Implementation**: `packages/local_llm/tool_validator.py`
```python
class ToolCallValidator:
    def validate(self, tool_call: Dict) -> Tuple[bool, str]:
        # Check tool exists, required arguments, types
```

**Prevents**: Missing args, wrong types, invalid tool names

## Phase 13.3: LoRA Fine-Tuning (Optional)

| Parameter | Value |
|-----------|-------|
| Base model | qwen2.5-coder:7b (7GB) |
| LoRA adapter | ~100MB |
| GPU needed | ~6GB (we have 12GB) |
| LoRA Rank | 16-32 |
| Learning Rate | 2e-4 |
| Epochs | 1-3 |

**When to use**: Specific failure patterns, 500+ training examples, specialized domain

## Phase 13.4: Model Routing (Recommended)

```python
TASK_MODEL_MAP = {
    "code_generation": "qwen2.5-coder:7b",
    "reasoning": "qwen2.5:14b",
    "fast_simple": "llama3.2:1b",
    "general": "llama3.2:3b",
}
```

## Phase 13.5: Production Hardening

| Task | Description |
|------|-------------|
| Error Recovery | Retry with exponential backoff, max iterations |
| Monitoring | Track tool call success rate, latency per tool |
| Caching | Cache by semantic similarity, TTL-based invalidation |

## Phase 13 Action Plan

| Task | Effort | Status |
|------|--------|--------|
| T13.1: RAG Context Injection | 3hr | Pending |
| T13.2: Tool Validation Layer | 2hr | Pending |
| T13.3: Model Routing | 4hr | Pending |
| T13.4: Error Recovery | 2hr | Pending |
| T13.5: Monitoring | 2hr | Pending |
| T13.6: Caching | 3hr | Pending |
| T13.7: LoRA Fine-Tuning | 16hr | Optional |
| **Total** | **32hr** (16hr without LoRA) | |

---

# Phase 14: Cross-Session Memory Fix

> Source: Cross-Session Awareness Status Report
> Goal: Make memory automatic — not manual calls

## Current State

| Component | Status | Notes |
|-----------|--------|-------|
| Session state | ✅ Working | `.sisyphus/session-state.json` persists |
| Active context | ✅ Working | `.context/activeContext.md` loaded at start |
| Unified memory | ✅ Available | MCP tool exists, module import varies |
| Memory graph | ⚠️ Partial | Files exist, but test shows empty |

## What's Working
1. **Session continuity**: New sessions read `.sisyphus/wake_up.md`, `session-state.json`, `activeContext.md`
2. **Memory tools**: `memory_search`, `memory_write` available as MCP tools
3. **Self-learning**: Routing outcomes stored in `.sisyphus/routing.db`

## What's NOT Working (Gaps)
1. **No auto-injection**: OpenCode doesn't automatically read memory before responding or write after tasks
2. **Memory not wired**: `get_active_context` / `get_user_context` tools exist but not integrated into agent lifecycle

## Phase 14 Action Plan

| Task | Files | Effort | Priority |
|------|-------|--------|----------|
| T14.1: Auto-read memory on session start | `packages/orchestration/session_hooks.py` | 1hr | P0 |
| T14.2: Auto-write memory on task completion | `packages/learning_engine/task_wrapper.py` | 1hr | P0 |
| T14.3: Wire get_active_context into agent lifecycle | `packages/memory_core/mcp_server.py` | 2hr | P1 |
| T14.4: Fix memory graph (currently empty) | `packages/memory_core/stores/graph_store.py` | 2hr | P1 |
| T14.5: Cross-session knowledge transfer | `packages/learning_engine/session_hooks.py` | 2hr | P1 |
| **Total** | **5 tasks** | **8hr** | |

---

## Updated Deferred Items

| Item | Reason | Target Phase |
|------|--------|--------------|
| Multi-venv for model optimization | Valid use case, needs careful planning | Phase 15 |
| BMAD workflow integration | 92 workflows need individual review | Phase 16 |
| uv workspace adoption | Requires pyproject.toml restructuring | Phase 17 |
| Neo4j production backend | Requires Neo4j server running | Phase 18 |
| CrossEncoderReranker | Requires sentence-transformers | Phase 19 |

---

# Phase 15: Archive Gold Extraction

> Source: 3 archives totaling ~100GB+ of historical N-Xyme work
> Goal: Extract ALL valuable patterns before deletion

## Archive 1: /mnt/WIN_LIBRARY/_NXYME_ARCHIVE/ (Historical Archive)

### HIGH VALUE — Port Immediately

| Pattern | Source File | Port To | Value |
|---------|------------|---------|-------|
| **Golden Spine Architecture** | `BRICK_CODEX_GOLDEN_SPINE_V1_CONTINUE_BUNDLE1_3.md` | `docs/golden-spine.md` | 🔥🔥🔥 |
| **Decision Ledger** | `1_N-Xyme M.I.N.D/01_core/decision_ledger.py` | `packages/orchestration/decision_ledger.py` | 🔥🔥🔥 |
| **Evidence Cortex** | `1_N-Xyme M.I.N.D/02_cortex/evidence_cortex.py` | `packages/orchestration/evidence_cortex.py` | 🔥🔥🔥 |
| **Strategy Snapshots** | `1_N-Xyme M.I.N.D/01_core/strategy_snapshot.py` | `packages/orchestration/strategy_snapshot.py` | 🔥🔥 |
| **Model Registry** | `1_N-Xyme M.I.N.D/02_cortex/model_registry.py` | `packages/infrastructure/model_registry.py` | 🔥🔥 |
| **Backend Adapters** | `1_N-Xyme M.I.N.D/02_cortex/adapters/` (6 files) | `packages/infrastructure/backends/` | 🔥🔥 |
| **Loop Policy** | `1_N-Xyme M.I.N.D/01_core/loop_policy.md` | `packages/orchestration/loop_policy.py` | 🔥🔥 |
| **Pattern Analyzer** | `1_N-Xyme M.I.N.D/02_cortex/pattern_analyzer.py` | `packages/orchestration/pattern_analyzer.py` | 🔥 |

### MEDIUM VALUE — Study & Adapt

| Pattern | Source | Value |
|---------|--------|-------|
| Contract interfaces | `1_N-Xyme M.I.N.D/03_contracts/` | Medium |
| Router policies | `1_N-Xyme M.I.N.D/04_config/policies/` | Medium |
| Memory indexing | `1_N-Xyme M.I.N.D/04_config/memory/` | Medium |
| Session archiver | `99_Depricated/00_N-Xyme_MIND/memory/` | Medium |
| Agent identities | `99_Depricated/00_N-Xyme_MIND/agent_identities.json` | Medium |

## Archive 2: /mnt/NXYME_CORE/01_CODING/00_N-Xyme_CATALYST/ (CATALYST)

### HIGH VALUE

| Pattern | Source | Port To | Value |
|---------|--------|---------|-------|
| **AGENTS.md (v2)** | `AGENTS.md` | Compare with current | 🔥🔥 |
| **Agent identities** | `agent_identities.json` | Merge with current | 🔥🔥 |
| **BMAD workflows** | `_bmad/` | Merge with current | 🔥 |
| **Athena queue** | `.athena-queue/` | Study queue patterns | 🔥 |

## Archive 3: /mnt/Library/recovered/home-nxyme/N-Xyme_MIND/ (Recovered)

### HIGH VALUE

| Pattern | Source | Port To | Value |
|---------|--------|---------|-------|
| **MASTERPLAN.md** | `MASTERPLAN.md` | Merge with current plan | 🔥🔥🔥 |
| **HANDOFF.md** | `HANDOFF.md` | Session handoff patterns | 🔥🔥 |
| **Jarvis agent system** | `jarvis/`, `jarvis-standalone/` | Study agent patterns | 🔥🔥 |
| **Deprecated code** | `deprecated/` | Find lost features | 🔥 |
| **Historical configs** | `configs/` | Compare with current | 🔥 |

## Phase 15 Action Plan

| Task | Source | Effort | Priority |
|------|--------|--------|----------|
| T15.1: Copy Golden Spine docs | WIN_LIBRARY | 30min | P0 |
| T15.2: Port Decision Ledger | WIN_LIBRARY | 2hr | P0 |
| T15.3: Port Evidence Cortex | WIN_LIBRARY | 2hr | P0 |
| T15.4: Port Strategy Snapshots | WIN_LIBRARY | 1hr | P1 |
| T15.5: Port Model Registry + Backends | WIN_LIBRARY | 3hr | P1 |
| T15.6: Port Loop Policy | WIN_LIBRARY | 1hr | P1 |
| T15.7: Port Pattern Analyzer | WIN_LIBRARY | 2hr | P2 |
| T15.8: Merge MASTERPLAN.md | Recovered | 1hr | P0 |
| T15.9: Study Jarvis agent system | Recovered | 2hr | P1 |
| T15.10: Merge agent identities | CATALYST + WIN_LIBRARY | 1hr | P1 |
| **Total** | **10 tasks** | **15.5hr** | |

---

## Full Masterplan Summary (All Phases)

| Phase | Tasks | Effort | Status |
|-------|-------|--------|--------|
| **Phase 11**: System Cleanup | 22 | 6.5hr | Ready |
| **Phase 12**: Claude Code Patterns | 9 | 25hr | Planned |
| **Phase 13**: Local LLM Optimization | 7 | 32hr (16hr w/o LoRA) | Planned |
| **Phase 14**: Cross-Session Memory | 5 | 8hr | Planned |
| **Phase 15**: Archive Gold Extraction | 10 | 15.5hr | Planned |
| **Total** | **53 tasks** | **~87hr** (~71hr w/o LoRA) | |

---

*Masterplan updated: 2026-04-07 | Archive gold extraction added (3 archives, 100GB+)*
