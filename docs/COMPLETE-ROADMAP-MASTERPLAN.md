# N-Xyme_MIND — Complete Roadmap Masterplan

> **Date:** 2026-04-07
> **Status:** Living Document
> **Version:** 2.0
> **Scope:** All completed, in-progress, and deferred work — with optimal delegation

---

## Executive Summary

N-Xyme_MIND is a production-ready AI agent orchestration workspace with 18 packages, 14 MCP servers, intelligent delegation, memory/learning systems, and BMAD workflows. The core system works. The remaining work falls into **three categories**:

1. **Integration** — Components exist but aren't wired into the pipeline
2. **Infrastructure** — Project structure, dependency management, deployment
3. **Enhancement** — New capabilities that extend the system

**Total estimated effort:** ~40 hours across 8 phases, designed for parallel delegation.

---

## Current State Assessment

### ✅ Completed (Phases 1-16)

| Phase | What | Evidence |
|-------|------|----------|
| 1-4 | Foundation, MCP servers, agent configs | 18 packages in `packages/` |
| 5-10 | Memory system, routing, learning | `packages/memory_core/`, `packages/learning_engine/`, `packages/intelligence/` |
| 11 | Quality gates, health monitoring | 15 gates in `bin/quality-gates/`, 3 health levels |
| 12 | Claude Code Patterns | 9/9 patterns implemented |
| 13 | Local LLM Optimization | 6/6 optimizations, tool calling verified |
| 14 | Cross-Session Memory | Session state sharing verified |
| 15 | Archive Gold Extraction | 5/5 drive scanning components |
| 16 | Golden Spine | 3-layer health check operational |

### 🔄 Partially Done

| Component | Status | Gap |
|-----------|--------|-----|
| Neo4j Backend | Code complete, not running | Falls back to SQLite |
| CrossEncoderReranker | Code complete, optional | Requires `sentence-transformers` |
| Hindsight MCP | Implemented | Not fully wired into memory_core |
| Memory Consolidation | Router + wrappers built | Trigger actions not wired |
| MCP Servers | 8 configured in opencode.json | 18 packages exist, not all exposed |

### ❌ Not Started / Deferred

| Item | Effort | Impact |
|------|--------|--------|
| uv Workspace Adoption | 6hr | High — dependency management |
| Intelligence Component Integration | 12hr | Critical — 8 components orphaned |
| BMAD Workflow Wiring | 8hr | Medium — orchestration layer |
| MCP Consolidation | 6hr | Medium — 8→4 servers |
| Standalone System Packaging | 16hr | High — portability |
| Observability (Langfuse) | 4hr | Low — debugging |

---

## Roadmap: Phase 17-24

### Phase 17: uv Workspace Adoption

**Goal:** Convert from pip-based to uv workspace monorepo with single lockfile.

**Why:** Industry standard for Python monorepos. Eliminates 6 scattered venvs. Single `uv.lock` ensures consistent deps.

**Sub-tasks:**

| # | Task | Effort | Delegation |
|---|------|--------|------------|
| 17.1 | Create root `pyproject.toml` with workspace config | 1hr | `category="quick"` |
| 17.2 | Add `pyproject.toml` to each package (18 packages) | 2hr | `subagent_type="hephaestus"` — parallel waves of 6 |
| 17.3 | Define inter-package workspace dependencies | 1hr | `subagent_type="hephaestus"` |
| 17.4 | Run `uv sync` and resolve conflicts | 1hr | `category="quick"` |
| 17.5 | Update all MCP server launch commands in opencode.json | 1hr | `subagent_type="hephaestus"` |
| 17.6 | Remove old venv directories, update Makefile | 1hr | `category="quick"` |

**Delegation Strategy:**
```
Wave 1 (parallel x3):
  - 17.1: quick (root pyproject.toml)
  - 17.2a: hephaestus (packages 1-6 pyproject.toml)
  - 17.2b: hephaestus (packages 7-12 pyproject.toml)

Wave 2 (parallel x2):
  - 17.2c: hephaestus (packages 13-18 pyproject.toml)
  - 17.3: hephaestus (workspace dependencies)

Wave 3 (sequential):
  - 17.4: quick (uv sync + resolve)
  - 17.5: hephaestus (update opencode.json)
  - 17.6: quick (cleanup)
```

**Success Criteria:**
- `uv sync` succeeds with 0 conflicts
- All 18 MCP servers start via `uv run`
- `uv.lock` committed
- No standalone venv directories remain

---

### Phase 18: Intelligence Component Integration

**Goal:** Wire 8 orphaned intelligence components into the delegation pipeline.

**Why:** Audit found 23 intelligence components, only 7 connected. The other 16 are dead code or unused.

**Sub-tasks:**

| # | Task | Effort | Delegation |
|---|------|--------|------------|
| 18.1 | Audit: classify 16 orphaned components (keep/merge/delete) | 2hr | `subagent_type="oracle"` |
| 18.2 | Wire ML Router into unified_router.py | 2hr | `subagent_type="hephaestus"` |
| 18.3 | Wire Skill Registry into agent selection | 1hr | `subagent_type="hephaestus"` |
| 18.4 | Wire Health Monitor into routing decisions | 1hr | `subagent_type="hephaestus"` |
| 18.5 | Wire Context Sharing into session start | 2hr | `subagent_type="hephaestus"` |
| 18.6 | Wire Task Decomposer into delegation flow | 2hr | `subagent_type="hephaestus"` |
| 18.7 | Wire Prompt Templates into delegation prompts | 1hr | `subagent_type="hephaestus"` |
| 18.8 | Remove/consolidate orphaned components | 1hr | `subagent_type="hephaestus"` |
| 18.9 | Integration tests for full pipeline | 2hr | `subagent_type="hephaestus"` |

**Delegation Strategy:**
```
Wave 1 (sequential — must complete first):
  - 18.1: oracle (audit + classification report)

Wave 2 (parallel x4, after 18.1):
  - 18.2: hephaestus (ML Router wiring)
  - 18.3: hephaestus (Skill Registry wiring)
  - 18.4: hephaestus (Health Monitor wiring)
  - 18.5: hephaestus (Context Sharing wiring)

Wave 3 (parallel x3, after Wave 2):
  - 18.6: hephaestus (Task Decomposer wiring)
  - 18.7: hephaestus (Prompt Templates wiring)
  - 18.8: hephaestus (orphan cleanup)

Wave 4 (sequential):
  - 18.9: hephaestus (integration tests + verification)
```

**Success Criteria:**
- All 8 advanced components connected to pipeline
- 0 orphaned imports in `packages/intelligence/`
- Integration tests pass for full delegation flow
- Pipeline uses: Health Check → Context Load → Task Decompose → Skill Match → ML Predict → Template Render → Agent → Outcome

---

### Phase 19: Memory Consolidation Completion

**Goal:** Complete the memory consolidation architecture — wire trigger actions, finish Hindsight integration.

**Why:** Memory router and wrappers built (Sprint 1+2 done), but trigger actions and session handoff not wired.

**Sub-tasks:**

| # | Task | Effort | Delegation |
|---|------|--------|------------|
| 19.1 | Wire `consolidate_episodes` trigger action | 1hr | `subagent_type="hephaestus"` |
| 19.2 | Wire `sync_session_to_memory` trigger action | 1hr | `subagent_type="hephaestus"` |
| 19.3 | Full Hindsight MCP → memory_core integration | 2hr | `subagent_type="hephaestus"` |
| 19.4 | Session handoff with merged context from all backends | 2hr | `subagent_type="hephaestus"` |
| 19.5 | Add `/memory-status` CLI command | 1hr | `subagent_type="hephaestus"` |
| 19.6 | Memory consolidation integration tests | 1hr | `subagent_type="hephaestus"` |

**Delegation Strategy:**
```
Wave 1 (parallel x2):
  - 19.1: hephaestus (consolidate_episodes trigger)
  - 19.2: hephaestus (sync_session_to_memory trigger)

Wave 2 (parallel x2):
  - 19.3: hephaestus (Hindsight integration)
  - 19.4: hephaestus (session handoff)

Wave 3 (parallel x2):
  - 19.5: hephaestus (CLI command)
  - 19.6: hephaestus (integration tests)
```

**Success Criteria:**
- Both trigger actions functional
- Hindsight MCP fully integrated into memory_core
- Session handoff merges context from all backends
- `/memory-status` shows backend health

---

### Phase 20: MCP Server Consolidation

**Goal:** Consolidate 8 MCP servers → 4 unified servers by domain.

**Why:** Industry best practice is domain-grouped single-responsibility servers. Currently 8 separate stdio servers with overlapping concerns.

**Current MCP Servers (8):**
1. `sequential-thinking` — npx external
2. `context7` — npx external
3. `nx-mind` — local Python
4. `unified-memory` — local Python
5. `learning-engine` — local Python
6. `intelligence` — local Python
7. `quality-gates` — local Python
8. `telegram` — npx external

**Target (4):**
1. **External** (keep as-is): `sequential-thinking`, `context7`, `telegram`
2. **Core MCP** (unified): Merge `nx-mind` + `unified-memory` + `learning-engine` + `intelligence` → single `n-xyme-core` server

**Sub-tasks:**

| # | Task | Effort | Delegation |
|---|------|--------|------------|
| 20.1 | Design unified MCP server API (tool catalog merge) | 1hr | `subagent_type="oracle"` |
| 20.2 | Create `packages/core-mcp/` with merged tool registry | 2hr | `subagent_type="hephaestus"` |
| 20.3 | Migrate nx-mind tools to core-mcp | 1hr | `subagent_type="hephaestus"` |
| 20.4 | Migrate unified-memory tools to core-mcp | 1hr | `subagent_type="hephaestus"` |
| 20.5 | Migrate learning-engine tools to core-mcp | 1hr | `subagent_type="hephaestus"` |
| 20.6 | Migrate intelligence tools to core-mcp | 1hr | `subagent_type="hephaestus"` |
| 20.7 | Update opencode.json to use single core-mcp | 0.5hr | `category="quick"` |
| 20.8 | Test all 16+ tools work via unified server | 1hr | `subagent_type="hephaestus"` |

**Delegation Strategy:**
```
Wave 1 (sequential):
  - 20.1: oracle (design review — critical architecture decision)

Wave 2 (parallel x4, after 20.1):
  - 20.2: hephaestus (core-mcp scaffold)
  - 20.3: hephaestus (nx-mind migration)
  - 20.4: hephaestus (unified-memory migration)
  - 20.5: hephaestus (learning-engine migration)

Wave 3 (parallel x2):
  - 20.6: hephaestus (intelligence migration)
  - 20.7: quick (opencode.json update)

Wave 4 (sequential):
  - 20.8: hephaestus (integration testing)
```

**Success Criteria:**
- Single `n-xyme-core` MCP server with all tools
- opencode.json references 4 MCPs (3 external + 1 core)
- All tools respond correctly
- Startup time reduced

---

### Phase 21: BMAD Workflow Integration

**Goal:** Wire 92 BMAD workflows into the system orchestration layer.

**Why:** BMAD workflows exist in `_bmad/` but aren't connected to the agent delegation pipeline.

**Sub-tasks:**

| # | Task | Effort | Delegation |
|---|------|--------|------------|
| 21.1 | Audit: inventory all 92 workflows, classify by phase | 2hr | `subagent_type="explore"` |
| 21.2 | Create BMAD workflow executor in orchestration package | 2hr | `subagent_type="hephaestus"` |
| 21.3 | Wire workflow executor to Sisyphus delegation | 2hr | `subagent_type="hephaestus"` |
| 21.4 | Create phase-gate system (analysis → plan → solution → impl → test) | 2hr | `subagent_type="hephaestus"` |
| 21.5 | Integrate athena-context MCP for workflow context injection | 1hr | `subagent_type="hephaestus"` |
| 21.6 | Add workflow status tracking to nx-mind MCP | 1hr | `subagent_type="hephaestus"` |

**Delegation Strategy:**
```
Wave 1 (sequential):
  - 21.1: explore (workflow inventory + classification)

Wave 2 (parallel x3, after 21.1):
  - 21.2: hephaestus (workflow executor)
  - 21.3: hephaestus (Sisyphus wiring)
  - 21.4: hephaestus (phase-gate system)

Wave 3 (parallel x2):
  - 21.5: hephaestus (context injection)
  - 21.6: hephaestus (status tracking)
```

**Success Criteria:**
- BMAD workflows triggerable via Sisyphus delegation
- Phase gates enforced (can't skip from analysis → implementation)
- Workflow status visible via nx-mind MCP tools
- Context injected at each phase transition

---

### Phase 22: Neo4j Production Activation

**Goal:** Switch from SQLite fallback to Neo4j as the primary graph store.

**Why:** `Neo4jGraphStore` class is complete but never activated. Neo4j provides proper graph queries that SQLite can't.

**Sub-tasks:**

| # | Task | Effort | Delegation |
|---|------|--------|------------|
| 22.1 | Verify Neo4j installation and connectivity | 0.5hr | `category="quick"` |
| 22.2 | Create Neo4j migration script (SQLite → Neo4j) | 1hr | `subagent_type="hephaestus"` |
| 22.3 | Update graph_store.py to use Neo4j as primary | 1hr | `subagent_type="hephaestus"` |
| 22.4 | Add Neo4j health check to health monitoring | 0.5hr | `category="quick"` |
| 22.5 | Test graph queries against Neo4j | 1hr | `subagent_type="hephaestus"` |
| 22.6 | Update Makefile and startup scripts | 0.5hr | `category="quick"` |

**Delegation Strategy:**
```
Wave 1 (parallel x2):
  - 22.1: quick (Neo4j connectivity check)
  - 22.2: hephaestus (migration script)

Wave 2 (parallel x2):
  - 22.3: hephaestus (primary store switch)
  - 22.4: quick (health check)

Wave 3 (parallel x2):
  - 22.5: hephaestus (graph query tests)
  - 22.6: quick (Makefile update)
```

**Success Criteria:**
- Neo4j running and accessible on port 7474/7687
- All graph data migrated from SQLite
- `Neo4jGraphStore` is primary, SQLite is fallback only
- Health check reports Neo4j status

---

### Phase 23: Standalone System Packaging

**Goal:** Package N-Xyme_MIND as a standalone, installable system.

**Why:** Currently requires manual setup. Target: `curl | bash` or `uv tool install` experience.

**Sub-tasks:**

| # | Task | Effort | Delegation |
|---|------|--------|------------|
| 23.1 | Create installable package with uv (`uv tool install`) | 2hr | `subagent_type="hephaestus"` |
| 23.2 | Create bootstrap script for fresh machine setup | 2hr | `subagent_type="hephaestus"` |
| 23.3 | Create systemd user services for MCP servers | 1hr | `subagent_type="hephaestus"` |
| 23.4 | Create configuration wizard (first-run setup) | 2hr | `subagent_type="hephaestus"` |
| 23.5 | Package documentation (README, quickstart, troubleshooting) | 2hr | `category="writing"` |
| 23.6 | Create versioned release with CHANGELOG | 1hr | `category="quick"` |

**Delegation Strategy:**
```
Wave 1 (parallel x3):
  - 23.1: hephaestus (uv tool packaging)
  - 23.2: hephaestus (bootstrap script)
  - 23.3: hephaestus (systemd services)

Wave 2 (parallel x2):
  - 23.4: hephaestus (config wizard)
  - 23.5: writing (documentation)

Wave 3 (sequential):
  - 23.6: quick (release + CHANGELOG)
```

**Success Criteria:**
- `uv tool install n-xyme-mind` works on fresh machine
- Bootstrap script sets up all dependencies
- MCP servers auto-start via systemd
- First-run wizard guides configuration
- Documentation covers all use cases

---

### Phase 24: Observability & Monitoring

**Goal:** Add Langfuse observability and real-time monitoring dashboard.

**Why:** Currently no visibility into agent performance, token usage, or routing decisions over time.

**Sub-tasks:**

| # | Task | Effort | Delegation |
|---|------|--------|------------|
| 24.1 | Install and configure Langfuse | 1hr | `subagent_type="hephaestus"` |
| 24.2 | Add Langfuse tracing to delegation pipeline | 2hr | `subagent_type="hephaestus"` |
| 24.3 | Create real-time monitoring dashboard (web or TUI) | 3hr | `category="visual-engineering"` |
| 24.4 | Add alerting for critical failures | 1hr | `subagent_type="hephaestus"` |
| 24.5 | Create monitoring runbooks | 1hr | `category="writing"` |

**Delegation Strategy:**
```
Wave 1 (parallel x2):
  - 24.1: hephaestus (Langfuse install + config)
  - 24.2: hephaestus (pipeline tracing)

Wave 2 (parallel x2):
  - 24.3: visual-engineering (dashboard)
  - 24.4: hephaestus (alerting)

Wave 3 (sequential):
  - 24.5: writing (runbooks)
```

**Success Criteria:**
- Langfuse captures all delegation events
- Dashboard shows real-time agent status, token usage, routing decisions
- Alerts fire on critical failures
- Runbooks cover all failure modes

---

## Phase Dependency Graph

```
Phase 17 (uv Workspace)
    │
    ├──→ Phase 18 (Intelligence Integration)
    │       │
    │       └──→ Phase 19 (Memory Consolidation)
    │               │
    │               └──→ Phase 20 (MCP Consolidation)
    │                       │
    │                       └──→ Phase 23 (Standalone Packaging)
    │
    ├──→ Phase 21 (BMAD Integration) [independent, can run parallel]
    │
    └──→ Phase 22 (Neo4j Activation) [independent, can run parallel]

Phase 24 (Observability) [independent, can run anytime]
```

**Recommended Execution Order:**
1. **Phase 17** — Foundation (blocks most others)
2. **Phase 18** — Critical integrations (highest impact)
3. **Phase 19** — Memory completion (depends on 18)
4. **Phase 20** — MCP consolidation (depends on 19)
5. **Phase 21** — BMAD wiring (parallel with 18-20)
6. **Phase 22** — Neo4j (parallel with 18-20)
7. **Phase 23** — Packaging (depends on 20)
8. **Phase 24** — Observability (anytime)

---

## Delegation Summary Matrix

| Phase | Primary Agent | Category | Parallel Waves | Est. Hours |
|-------|--------------|----------|----------------|------------|
| 17 | hephaestus + quick | Implementation | 3 waves | 7hr |
| 18 | oracle + hephaestus | Architecture + Implementation | 4 waves | 14hr |
| 19 | hephaestus | Implementation | 3 waves | 8hr |
| 20 | oracle + hephaestus | Architecture + Implementation | 4 waves | 8.5hr |
| 21 | explore + hephaestus | Research + Implementation | 3 waves | 10hr |
| 22 | hephaestus + quick | Implementation | 3 waves | 4.5hr |
| 23 | hephaestus + writing + quick | Implementation + Docs | 3 waves | 10hr |
| 24 | hephaestus + visual-engineering + writing | Implementation + UI + Docs | 3 waves | 8hr |

**Total: ~70 hours across 8 phases**

---

## Quick-Start: What to Do Next

If you want to proceed, the recommended starting point is **Phase 17** (uv Workspace Adoption), as it unblocks everything else.

Say "start phase 17" and I'll begin delegating.

Or pick any other phase — each is self-contained and can be started independently (except 19→20→23 chain).
