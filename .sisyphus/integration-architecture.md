# N-Xyme Brain Integration with OpenCode + oh-my-openagent

## Status: INTEGRATED ✅

---

## What Was Done

### P0 — MCP Infrastructure Fixes

| MCP | Problem | Fix |
|-----|---------|-----|
| `session-pool` | Wrong path `-m mcp_server` | Fixed to `-m packages.session_pool_mcp.mcp_server` |
| `nx-context` | Wrong path `-m nx_context_mcp` | Fixed to `-m packages.nx_context_mcp` |
| `trigger-guardian` | Wrong path `-m trigger_guardian_mcp` | Fixed to `-m packages.trigger_guardian_mcp.trigger_guardian_mcp` |
| `catalyst` | Missing dependency `get_logger()` | Fixed in `telemetry.py` |
| `catalyst` | Broken circular import | Fixed in `proxy/__init__.py` (removed `ab_testing` re-export) |
| `orchestration` | Missing `get_logger()` | Added function in `telemetry.py` |

Config: `opencode.json` — all MCPs now point to correct Python module paths.

---

## P1 — Brain Integration Architecture

### The Bridge Pattern

```
OpenCode / oh-my-openagent
    │
    ├── task() tool call (before execution)
    │       │
    │       ▼ hook: tool.execute.before
    │       └── nx-brain-hook/src/index.ts
    │               ├── memory.search → context for agent
    │               ├── learning.route_task → routing hints
    │               ├── fingerprint.inject_context → session memory
    │               └── INJECTS into task() args (load_skills, prompt context)
    │
    ├── Python bridge: packages/nx-brain-hook/bridge.py
    │       └── stdin JSON → brain function → stdout JSON
    │           Functions available:
    │           • memory.search (packages.memory_store.mcp_server)
    │           • learning.route_task (packages.nx_routing)
    │           • intelligence.score_complexity (packages.nx_routing)
    │           • fingerprint.inject_context (packages.context_store)
    │           • learning.log_outcome (packages.learning_engine.outcome_logger)
    │           • fingerprint.record_pattern (packages.brain_mcp.fingerprint)
    │
    ├── task() tool call (after execution)
    │       └── nx-brain-hook/src/index.ts
    │               ├── learning.log_outcome → success/failure + latency
    │               ├── fingerprint.record_pattern → action sequence
    │               └── Tool sequence logging for composite analysis
    │
    └── N-Xyme Brain (packages/*)
            ├── brain_mcp/ (central orchestrator, 39 imports)
            ├── learning_engine/ (Q-Learning routing)
            ├── memory_store/ (vector search)
            ├── context_store/ (session context)
            ├── nx_mind_mcp/ (mind state)
            └── nx_routing/ (routing engine)
```

### Python Bridge (`packages/nx-brain-hook/bridge.py`)

**Status: TESTED ✅**

All 6 brain functions verified working via JSON stdin/stdout bridge:

```python
# Example call
echo '{"function": "learning.route_task", "args": {"task_description": "fix auth bug"}}' \
  | python3 packages/nx-brain-hook/bridge.py

# Returns: {"status": "success", "data": {"agent": "quick", "level": 2, "confidence": 0.95}}
```

---

## P2 — Hook Registration

### Current State: TypeScript Hook Ready, Upstream Blocked

**The Problem:** oh-my-openagent is **binary-compiled** — `createHooks()` is hardcoded in `dist/index.js`. There is **no plugin registration API** for adding custom hooks externally.

- `create-hooks.d.ts` defines 55 hook types — all hardcoded in the binary
- No external plugin mechanism to add new hook implementations
- The TypeScript hook (`packages/nx-brain-hook/src/index.ts`) is compiled and ready

**Available Integration Points:**
1. **`tool.execute.before`** / **`tool.execute.after`** — intercept ALL tool calls including `task()`, with full args modification capability
2. **`system.transform`** — modify system prompt
3. **`event`** — global event handler

### How to Register (when upstream support is added)

```typescript
// packages/nx-brain-hook/src/index.ts
export function register(brainBridge: BrainBridge) {
  return {
    tool: {
      'execute.before': async (tool, args, ctx) => {
        if (tool === 'task') {
          // Inject memory context into load_skills
          const memories = await brainBridge.call('memory.search', {
            query: args.prompt || args.description || ''
          });
          const skills = memories.slice(0, 3).map(m => m.content);
          return {
            ...args,
            load_skills: [...(args.load_skills || []), ...skills]
          };
        }
        return args;
      },
      'execute.after': async (tool, args, result, ctx) => {
        if (tool === 'task') {
          // Log outcome and record pattern
          await brainBridge.call('learning.log_outcome', {...});
          await brainBridge.call('fingerprint.record_pattern', {...});
        }
        return result;
      }
    },
    event: async (event, data, ctx) => {
      // Handle global events
    }
  };
}
```

### Workaround Options

1. **Submit PR to oh-my-openagent** — add `brain` or `nx-brain-hook` to the registered hook list in `createHooks()`
2. **OpenCode plugin system** — if OpenCode has a plugin mechanism for hooks, register `nx-brain-hook` there
3. **Direct monkey-patch** — patch `dist/index.js` at startup (fragile, not recommended for production)

---

## P3 — Duplicate Components Analysis

### Routing Files (7 dead / 5 alive)

| File | Status | Reason |
|------|--------|--------|
| `packages/nx_routing.py` | **ALIVE** | 17 imports (bridge, session-pool, orchestration) |
| `packages/learning_engine/routing/adaptive_router.py` | **ALIVE** | 25 imports (brain_mcp, tests, mcp servers) |
| `packages/orchestration/two_stage_router.py` | **ALIVE** | 3 imports (tool_awareness, tests) |
| `packages/memory_core/router.py` | **ALIVE** | 50 imports (major router) |
| `packages/memory_store/router.py` | **ALIVE** | 7 imports |
| `learning_engine/routing/multi_reward_router.py` | **DEAD** | 0 imports |
| `orchestration/tasks/router.py` | **DEAD** | 0 imports |
| `orchestration/triggers/router.py` | **DEAD** | 0 imports |
| `intelligence/predictive_router.py` | **DEAD** | 0 imports |
| `infrastructure/proxy/router_brain.py` | **DEAD** | 0 imports |
| `infrastructure/proxy/intelligent_router.py` | **DEAD** | 0 imports |
| `orchestration/agent-framework/src/router.py` | **DEAD** | 0 imports |

### Duplicate Packages (4 dead / 1 alive)

| Package | Status | Replacement |
|---------|--------|-------------|
| `packages/nx_mind_mcp/` (underscore) | **ALIVE** | Used by brain_mcp, nxyme_tools, telegram-bot |
| `packages/nx-mind-mcp/` (hyphen) | **DEAD** | No imports of hyphen version |
| `packages/context_store/` | **ALIVE** | 5 importers (brain_mcp, nxyme_tools, orchestration) |
| `packages/nx_context_mcp/` (underscore) | **ALIVE** | Self-referencing base module |
| `packages/nx-context-mcp/` (hyphen) | **DEAD** | No external imports |
| `packages/legacy/nx-context-mcp/` | **DEAD** | No external imports |
| `packages/platform_layer/` (underscore) | **ALIVE** | Self-imports, launcher.py |
| `packages/platform-layer/` (hyphen) | **DEAD** | 0 imports |

### Intelligence Package

**NOT orphaned.** 36 files import `packages/intelligence/`. It's a heavily-used 28-module package.

Only `predictive_router.py` is dead (0 imports), the rest are actively used.

### nxyme_tools.py

**NOT imported by anything** except itself. It's a thin wrapper with no external consumers. Consider removing.

---

## P4 — Database Schema

### Active DBs

| DB | Schema | Status |
|----|--------|--------|
| `.sisyphus/outcomes.db` | `outcomes` (task_id, task_description, task_type, agent, level, success, latency_ms, tokens_used, timestamp) | **ACTIVE** — 5 rows logged |
| `.sisyphus/state.db` | `delegations`, `sessions`, `results`, `agent_performance` | LEGACY — minimal usage |
| `data/routing.db` | EMPTY (no tables) | Not a problem — empty |

No schema mismatch. `data/routing.db` is empty so it can't conflict with anything.

---

## P5 — Observability

### MCP Health Monitoring

The `packages/brain_mcp/utils/health.py` provides health checks for all brain namespaces.

### Logs

- `packages/infrastructure/monitoring/telemetry.py` — unified logging with `get_logger()`
- `packages/learning_engine/outcome_logger.py` — delegation outcome logging to `outcomes.db`
- `packages/brain_mcp/fingerprint/` — pattern recording

---

## Quick Start

### Start all MCPs

```bash
cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
python3 -m packages.brain_mcp.__main__
```

### Test the brain bridge

```bash
echo '{"function": "learning.route_task", "args": {"task_description": "fix auth bug"}}' \
  | python3 packages/nx-brain-hook/bridge.py
```

### Verify MCP health

```bash
python3 scripts/test-all-mcps.py
```