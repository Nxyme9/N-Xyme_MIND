---
adr_id: ADR-001
title: "Memory Core vs Memory Store Consolidation"
status: accepted
date: 2026-05-11
deciders: Winston (architect), Sisyphus (orchestrator)
scorecard:
  consolidation_score: 90
  decision_confidence: high
  estimated_impact: medium
---

# ADR-001: Memory Core vs Memory Store Consolidation

## Status

**Accepted** — Deprecate memory_store, keep memory_core as canonical.

## Context

Two ~85% identical memory packages exist in `packages/`:
- **`memory_core`** — canonical (273 lines mcp_server.py, has `TrustAwareRetrieval`, `PriorityEngine`, `SleepEngine`, `MemoryReconsolidation`)
- **`memory_store`** — legacy shim (589 lines mcp_server.py, re-exports from memory_core via `__init__.py`)

Both implement the same MCP tool surface: `search_memories`, `get_memory_stats`, `recall_session`, `memory_write`, `memory_search`, `find_context`, `get_capabilities`, `health_check`.

The merge commit `3dd5a97` already consolidated cognitive/retention infrastructure into memory_core. The `memory_store/__init__.py` now delegates to `memory_core`. The `memory_store/mcp_server.py` has additional features (DelegationInterceptor, MemoryRouter integration) but these are non-essential augmentation — the core search/routing already lives in memory_core.

## Decision

**Deprecate memory_store** — keep as backwards-compat shim only.

### Rationale

1. **memory_core has the richer cognitive stack** — `TrustAwareRetrieval`, `PriorityEngine`, `SleepEngine`, `AdaptiveDecay` are all in memory_core. memory_store adds only optional wrappers (DelegationInterceptor, MemoryRouter) that don't change the API.
2. **memory_store already delegates** — since commit `3dd5a97`, `memory_store/__init__.py` re-exports from `memory_core`. It's a pure passthrough now.
3. **opencode.json reference** — `unified-memory` maps to `memory_store/mcp_server.py` (the shim). If we deprecate the shim, we point the MCP at memory_core directly.
4. **risk of merge** — merging two mcp_server.py files (273 vs 589 lines) risks subtle behavioral changes in the extra features. The 90% overlap masks real differences in the handling logic.

## Consequences

### Positive

- Single source of truth for memory search/routing logic
- All cognitive features (trust, priority, decay) in one package
- One fewer package to maintain, test, and audit
- opencode.json points to canonical implementation

### Negative

- memory_store/mcp_server.py has DelegationInterceptor (opt-in, not required for MCP to function) — lost if not re-implemented in memory_core before deprecation
- Any code directly importing `packages.memory_store.mcp_server` will break — requires import path update
- The `unified-memory` MCP tool name stays the same, server implementation changes

### Work Required

1. Re-implement DelegationInterceptor in memory_core (if used) OR acknowledge it as lost
2. Update opencode.json to point `unified-memory` at memory_core/mcp_server.py
3. Mark memory_store/mcp_server.py `@deprecated`
4. Update all imports referencing `memory_store.mcp_server` → `memory_core.mcp_server`
5. Archive memory_store/ to .archive/ or remove the mcp_server.py (keep __init__.py shim for backwards compat)

## Alternatives Considered

### Merge into single memory_core (rejected)

- Would require merging two mcp_server.py files with 316 line difference
- memory_store's extra features (DelegationInterceptor, MemoryRouter) are opt-in augmentations — not core MCP functionality
- High risk of subtle behavioral changes in edge cases
- The ADR process goal is clean architecture, not maximum code reduction

### Keep both (rejected)

- Already tried — diverged implementations caused maintenance burden
- Any bug fix must be applied twice (the original problem this ADR solves)
- Confusing for developers: which package to use?

## Verification

```bash
# canonical import works
python3 -c "from packages.memory_core import search, store, stats; print('OK')"

# shim still works (backwards compat)
python3 -c "from packages.memory_store import search, store, stats; print('OK')"

# MCP registration
grep "unified-memory" opencode.json
```

## Next Steps (AC-301 implementation)

- [ ] Re-implement DelegationInterceptor in memory_core/mcp_server.py (if actively used)
- [ ] Update opencode.json: `memory_store/mcp_server.py` → `memory_core/mcp_server.py`
- [ ] Mark memory_store/mcp_server.py `@deprecated`
- [ ] All tests pass: `pytest tests/ -v`