# Masterplan: MCP Gap Fixes & Enhancement

## Overview

This masterplan addresses ALL gaps identified from the deep audit of 8 parallel agents. Contains ~108 tools across 12 MCP packages with critical issues requiring immediate fixes.

---

## Phase 1: Priority 1 — BROKEN/BLOCKING (Today)

### 1.1 Fix Stale Context

| Item | File | Issue | Fix |
|------|------|-------|-----|
| **activeContext.md** | `.context/memory_bank/activeContext.md` | Last updated April 7 - stale | Add auto-refresh hook on session start in nx-context-mcp |

**Delegate to**: `hephaestus` (single file fix)

### 1.2 Fix Missing Router Module

| Item | File | Issue | Fix |
|------|------|-------|-----|
| **Missing src/memory/router** | `packages/nx-context-mcp/nx_context_mcp/__init__.py` | Tools `query_unified_memory`, `search_unified` depend on missing module | Create stub or remove broken tools |

**Delegate to**: `hephaestus` (single file fix)

### 1.3 Fix Hardcoded Paths

| Item | File | Issue | Fix |
|------|------|-------|-----|
| **Hardcoded project root** | `packages/orchestration/bmad/context_injector.py:90` | `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND` hardcoded | Use `get_project_root()` pattern |

**Delegate to**: `hephaestus` (single file fix)

---

## Phase 2: Priority 2 — ERROR HANDLING (This Week)

### 2.1 Fix Bare Except Handlers

**Files with bare `except:`**:
- `packages/orchestration/__init__.py:78`
- `packages/orchestration/tool_categories.py`
- `packages/memory_core/mcp_server.py`
- `packages/learning_engine/adaptive_router.py`
- `packages/intelligence/router/unified.py`

**Delegate to**: `hephaestus` (parallel - 5 files)

### 2.2 Add Input Validation

**All MCP tools need Pydantic models** - create validation layer:
- `packages/memory_core/schemas.py` - Memory tool input schemas
- `packages/learning_engine/schemas.py` - Learning tool input schemas
- `packages/intelligence/schemas.py` - Intelligence tool input schemas

**Delegate to**: `hephaestus` (3 files, can parallel)

---

## Phase 3: Priority 3 — MISSING FEATURES (This Week)

### 3.1 Add Circuit Breaker to Orchestration

| Item | File | Issue | Fix |
|------|------|-------|-----|
| **No circuit breaker** | `packages/orchestration/` | Repeated failures not throttled | Add CircuitBreaker class similar to learning_engine |

**Delegate to**: `hephaestus`

### 3.2 Add Rate Limiting

| Item | File | Issue | Fix |
|------|------|-------|-----|
| **No rate limiting** | `packages/orchestration/tasks/dispatcher.py` | No tool call throttling | Add TokenBucket rate limiter |

**Delegate to**: `hephaestus`

### 3.3 Add Context Freshness Validation

| Item | File | Issue | Fix |
|------|------|-------|-----|
| **No timestamp validation** | `packages/nx-context-mcp/` | Memory bank files not validated | Add TTL/freshness check to context tools |

**Delegate to**: `hephaestus`

### 3.4 Add Connection Pooling

| Item | File | Issue | Fix |
|------|------|-------|-----|
| **No async DB** | `packages/learning_engine/db.py` | Blocking SQLite | Add async SQLite connection pool |

**Delegate to**: `hephaestus`

---

## Phase 4: Priority 4 — OPTIMIZATION (This Month)

### 4.1 Balance Tool Categories

| Item | File | Issue | Fix |
|------|------|-------|-----|
| **Category imbalance** | `packages/orchestration/tool_categories.py` | EXECUTION: 28 keywords, QUALITY: 17 | Normalize keyword counts |

**Delegate to**: `hephaestus`

### 4.2 Integrate Style Learner

| Item | File | Issue | Fix |
|------|------|-------|-----|
| **Style learner unused** | `packages/nx-context-mcp/style_learner.py` | Records but never called | Hook into delegation flow |

**Delegate to**: `hephaestus`

### 4.3 Add Lazy Loading

| Item | File | Issue | Fix |
|------|------|-------|-----|
| **All tools load at startup** | All MCP packages | 50-80 tool breaking point | Implement FastMCP Provider pattern |

**Delegate to**: `hephaestus`

### 4.4 Add Tool Schema Caching

| Item | File | Issue | Fix |
|------|------|-------|-----|
| **Schemas not cached** | `packages/orchestration/tool_cache.py` | Only descriptions cached | Add schema caching |

**Delegate to**: `hephaestus`

---

## Delegation Instructions (PARALLEL EXECUTION)

### Wave A: Immediate (Priority 1 - 3 files)

```bash
# ALL 3 CAN RUN IN PARALLEL - no dependencies between them
task(subagent_type="hephaestus", prompt="Fix stale context in nx-context-mcp. Task: Update activeContext.md to auto-refresh on session start. File: packages/nx-context-mcp/. Context: Current file is stale since April 7. REQUIRED TOOLS: read, write. MUST DO: Create hook that refreshes timestamp on session start. Context: Working directory /home/nxyme/N-Xyme_CODE/N-Xyme_MIND", run_in_background=false, load_skills=[])

task(subagent_type="hephaestus", prompt="Fix missing router dependency in nx-context-mcp. Task: Fix or remove broken tools query_unified_memory and search_unified. File: packages/nx-context-mcp/nx_context_mcp/__init__.py. Context: These tools depend on src/memory/router which doesn't exist. REQUIRED TOOLS: read, edit. MUST DO: Either create stub module or remove broken tool definitions. Context: Working directory /home/nxyme/N-Xyme_CODE/N-Xyme_MIND", run_in_background=false, load_skills=[])

task(subagent_type="hephaestus", prompt="Fix hardcoded project root in context_injector.py. Task: Replace hardcoded path with dynamic project root. File: packages/orchestration/bmad/context_injector.py line 90. Context: Path /home/nxyme/N-Xyme_CODE/N-Xyme_MIND is hardcoded. REQUIRED TOOLS: read, edit. MUST DO: Replace with get_project_root() or os.getcwd() pattern. Context: Working directory /home/nxyme/N-Xyme_CODE/N-Xyme_MIND", run_in_background=false, load_skills=[])
```

### Wave B: Error Handling (Priority 2 - 5 files)

```bash
# CAN RUN IN PARALLEL - different files
task(subagent_type="hephaestus", prompt="Fix bare except handlers in orchestration __init__.py. Task: Replace bare except: with specific exception handling. File: packages/orchestration/__init__.py line 78. Context: Has bare except: that silently swallows errors. REQUIRED TOOLS: read, edit. MUST DO: Add specific exception types (ValueError, TypeError, IOError), add logging, add user-facing error feedback. Context: Working directory /home/nxyme/N-Xyme_CODE/N-Xyme_MIND", run_in_background=false, load_skills=[])

task(subagent_type="hephaestus", prompt="Fix bare except handlers in tool_categories.py. Task: Replace bare except: with specific exception handling. File: packages/orchestration/tool_categories.py. Context: Has bare except: that silently swallows errors. REQUIRED TOOLS: read, edit. MUST DO: Add specific exception types, add logging. Context: Working directory /home/nxyme/N-Xyme_CODE/N-Xyme_MIND", run_in_background=false, load_skills=[])

task(subagent_type="hephaestus", prompt="Fix bare except handlers in memory_core mcp_server.py. Task: Replace bare except: with specific exception handling. File: packages/memory_core/mcp_server.py. Context: Has bare except clauses that silently fail. REQUIRED TOOLS: read, edit. MUST DO: Add specific exception types, add error logging, add user feedback. Context: Working directory /home/nxyme/N-Xyme_CODE/N-Xyme_MIND", run_in_background=false, load_skills=[])

task(subagent_type="hephaestus", prompt="Fix error handling in intelligence router. Task: Replace bare except Exception with specific handling. File: packages/intelligence/router/unified.py. Context: 20+ try/except with bare except Exception as e - no specific handling. REQUIRED TOOLS: read, edit. MUST DO: Add specific exception types per operation, add structured error codes, add proper propagation. Context: Working directory /home/nxyme/N-Xyme_CODE/N-Xyme_MIND", run_in_background=false, load_skills=[])

task(subagent_type="hephaestus", prompt="Create input validation schemas. Task: Create Pydantic validation models for MCP tools. Files: packages/memory_core/schemas.py, packages/learning_engine/schemas.py, packages/intelligence/schemas.py. Context: No input validation on MCP tool parameters. REQUIRED TOOLS: write, read. MUST DO: Create Pydantic models for each tool's input parameters. Include: search_memories, record_outcome, route_task. Context: Working directory /home/nxyme/N-Xyme_CODE/N-Xyme_MIND", run_in_background=false, load_skills=[])
```

### Wave C: Missing Features (Priority 3 - 4 items)

```bash
# THESE HAVE DEPENDENCIES - run sequentially or with care
task(subagent_type="hephaestus", prompt="Add circuit breaker to orchestration. Task: Add CircuitBreaker class to packages/orchestration/. File: New file packages/orchestration/circuit_breaker.py. Context: No circuit breaker - repeated failures not throttled. REQUIRED TOOLS: write. MUST DO: Create CircuitBreaker with states (closed/open/half-open), failure threshold, cooldown period, methods: call(), on_success(), on_failure(). Reference: packages/learning_engine/rl/circuit_breaker.py for pattern. Context: Working directory /home/nxyme/N-Xyme_CODE/N-Xyme_MIND", run_in_background=false, load_skills=[])

task(subagent_type="hephaestus", prompt="Add rate limiting to task dispatcher. Task: Add TokenBucket rate limiter. File: packages/orchestration/tasks/dispatcher.py. Context: No tool call throttling. REQUIRED TOOLS: read, edit. MUST DO: Add rate_limit parameter, implement token bucket algorithm, track per-agent rates. Context: Working directory /home/nxyme/N-Xyme_CODE/N-Xyme_MIND", run_in_background=false, load_skills=[])

task(subagent_type="hephaestus", prompt="Add context freshness validation. Task: Add TTL/freshness check to context tools. Files: packages/nx-context-mcp/nx_context_mcp/__init__.py. Context: Memory bank files not validated for freshness. REQUIRED TOOLS: read, edit. MUST DO: Add timestamp validation, warn if context older than 24h, add last_updated tracking. Context: Working directory /home/nxyme/N-Xyme_CODE/N-Xyme_MIND", run_in_background=false, load_skills=[])

task(subagent_type="hephaestus", prompt="Add connection pooling to learning_engine. Task: Add async SQLite connection pool. File: packages/learning_engine/db.py. Context: Blocking SQLite with no pooling. REQUIRED TOOLS: read, edit. MUST DO: Add aiosqlite or asyncpg pool, implement connection reuse, add context manager. Context: Working directory /home/nxyme/N-Xyme_CODE/N-Xyme_MIND", run_in_background=false, load_skills=[])
```

### Wave D: Optimization (Priority 4 - 4 items)

```bash
task(subagent_type="hephaestus", prompt="Balance tool category keywords. Task: Normalize keyword counts in tool_categories.py. File: packages/orchestration/tool_categories.py. Context: EXECUTION has 28 positive keywords, QUALITY has 17. REQUIRED TOOLS: read, edit. MUST DO: Add more positive keywords to QUALITY, INTEGRATION categories. Balance the distribution. Context: Working directory /home/nxyme/N-Xyme_CODE/N-Xyme_MIND", run_in_background=false, load_skills=[])

task(subagent_type="hephaestus", prompt="Integrate style learner into delegation. Task: Hook style_learner.py into orchestration flow. Files: packages/nx-context-mcp/style_learner.py, packages/orchestration/tasks/dispatcher.py. Context: Style learner records data but is never called. REQUIRED TOOLS: read, edit. MUST DO: Call record_delegation() during agent routing, integrate style context into tool suggestions. Context: Working directory /home/nxyme/N-Xyme_CODE/N-Xyme_MIND", run_in_background=false, load_skills=[])

task(subagent_type="hephaestus", prompt="Add lazy loading to MCP tools. Task: Implement FastMCP Provider pattern for on-demand loading. Files: packages/memory_core/mcp_server.py, packages/learning_engine/mcp_server.py. Context: All tools load at startup - hitting 50-80 breaking point. REQUIRED TOOLS: read, edit. MUST DO: Implement @provider decorator pattern, lazy import heavy dependencies, defer tool registration. Context: Working directory /home/nxyme/N-Xyme_CODE/N-Xyme_MIND", run_in_background=false, load_skills=[])

task(subagent_type="hephaestus", prompt="Add tool schema caching. Task: Add schema caching to tool_cache.py. File: packages/orchestration/tool_cache.py. Context: Only descriptions cached, schemas regenerated each time. REQUIRED TOOLS: read, edit. MUST DO: Add schema caching with TTL, cache key includes tool name + version, integrate with existing cache. Context: Working directory /home/nxyme/N-Xyme_CODE/N-Xyme_MIND", run_in_background=false, load_skills=[])
```

---

## Atomic Commit Strategy

| Wave | Files | Commit Message |
|------|-------|----------------|
| 1 | 3 | fix: resolve critical blocking issues |
| 2 | 5 | fix: add proper error handling |
| 3 | 4 | feat: add missing resilience features |
| 4 | 4 | perf: optimize tool loading and caching |

---

## Success Criteria

| Priority | Metric | Target |
|----------|--------|--------|
| P1 | Broken tools | 0 |
| P2 | Bare except handlers | 0 |
| P3 | Circuit breakers | All packages |
| P4 | Lazy loading | 50%+ tools |
