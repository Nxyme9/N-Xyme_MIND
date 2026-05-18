---
name: nx-total-opgrade
description: "Total system upgrade — plug every gap, activate all unprocessed data, apply highest-ROI changes across all agents, plugins, MCP, config, and infrastructure"
---

# NX-TOTAL-OPGRADE v1.0
**Bleeding-Edge LLM Cloud-Local Prompt Engineering Orchestration**
*Applies to: all agents, all plugins, all MCP servers, all configs, all archive data*

---

## WHAT THIS IS

A single coordinated upgrade that processes EVERY piece of unactivated data, closes EVERY known gap, and applies the highest-ROI change to every level of the N-Xyme stack simultaneously.

This is NOT incremental. This is a **system-wide refit**.

---

## LEVEL 1: PLUGIN — Build OMO-Style BackgroundManager

**ROI: Critical.** Fixes identity propagation + enables real parallel dispatch.

### What we know (from reverse-engineering OMO source)
- `client.session.create({ body: { parentID: sessionID } })` propagates identity via SDK
- `client.session.promptAsync()` fire-and-forgets tasks
- BackgroundManager polls `session.idle` + stability detection (10s unchanged messages)
- Circuit breakers: max tool calls, repetitive tool detection, max concurrency (5 per model key)
- `delegate_task` blocks and waits for sync result

### What we have already
- Ralph plugin has `session.created`, `message.updated`, `experimental.session.compacting` hooks
- Ralph plugin already registers custom tools (`tui_notify`, `self_prompt`, `session_prompt`, `ultra_spawn`, `hot_delegate`)
- `client.tui.showToast()` works (proven in no-code-sisyphus)

### Build these files

| File | Purpose | Depends On |
|------|---------|------------|
| `.opencode/plugins/omo-bridge.js` | BackgroundManager + call_omo_agent + delegate_task | nothing |
| `.opencode/plugins/omo-circuit-breaker.js` | Tool call limits, repetitive tool detection | omo-bridge |
| `.opencode/plugins/omo-concurrency.js` | FIFO queue per model/provider key | omo-bridge |

### Key code patterns to implement

```
// 1. Create child session WITH parentID (the fix for identity propagation)
const session = await client.session.create({
  body: { parentID: parentSessionID, title: taskDescription },
  query: { directory: parentDirectory },
})

// 2. Fire-and-forget the prompt
client.session.promptAsync({
  path: { id: session.id },
  body: { agent: targetAgent, parts: [{ type: "text", text: prompt }] }
})

// 3. Detect completion via message.updated + session.idle
// (already have message.updated hook in ralph plugin)
```

### Files to modify
- `.opencode/plugins/ralph-autoloop.js` — add BackgroundManager class, replace ultra_spawn with call_omo_agent
- `opencode.json` — disable built-in `task` tool (add to plugin config), register new plugin
- `.opencode/plugins/no-code-sisyphus.js` — update agent directory list (add cortex, sisyphus-junior, agent-builder)

### Verification
- Spawn a subagent via call_omo_agent → check child session has parentID
- Parent session receives completion toast
- Circuit breaker kills infinite loops (test with `while(true)` task)

---

## LEVEL 2: MCP — Fix the 5 Critical Bugs from Scalpel Audit

**ROI: High.** Prevents crashes + security holes. Quick wins.

### Bug 1: Undefined cache vars in megatool-mcp/server.py
**File:** `services/megatool-mcp/server.py:693-702`
**Fix:** Create SimpleCache class, instantiate `file_cache`, `search_cache`, `config_cache` before handlers
```
class SimpleCache:
    def __init__(self, ttl=300):
        self._data = {}
        self._ttl = ttl
        self._timestamps = {}
    def get(self, key):
        if key in self._data and time.time() - self._timestamps[key] < self._ttl:
            return self._data[key]
        return None
    def set(self, key, value):
        self._data[key] = value
        self._timestamps[key] = time.time()
```
**ROI:** Prevents NameError crash on cache_stats/cache_clear calls.

### Bug 2: ACTIVE_AGENT_FILE hoisting trap in no-code-sisyphus.js
**File:** `.opencode/plugins/no-code-sisyphus.js:62-204`
**Fix:** Move `const ACTIVE_AGENT_FILE = "..."` from line 204 to line 9 (before first function that uses it)
**ROI:** Prevents ReferenceError on every tool call audit.

### Bug 3: SQL injection in web_fetch
**File:** `services/megatool-mcp/server.py:~1100`
**Fix:** Replace string interpolation with `urllib.parse.quote(url)` or pass URL via stdin/args
```
# BEFORE (vulnerable):
f"import urllib.request; url = '{url}'"

# AFTER (safe):
import urllib.parse
safe_url = urllib.parse.quote(url, safe='/:?&=')
```
**ROI:** Critical security fix — currently any URL with `'` gives RCE.

### Bug 4: batch_write_bridge.py references non-existent binary
**File:** `services/mojo-router/src/batch_write_bridge.py:9`
**Fix:** Change `DAEMON = ".../daemon"` to `["python3", ".../daemon.py"]`
**ROI:** Unbreaks batch_write functionality.

### Bug 5: Config drift between opencode.json and nx_agents.json
**Fix:** Run `config_sync` tool, then audit manually for Hephaestus model, Explore permissions, Jarvis description
**ROI:** Prevents agents from running with wrong models/permissions.

---

## LEVEL 3: ARCHIVE DATA — Activate the Unprocessed Goldmine

**ROI: High.** We migrated 80+ files from `data_chaos` but never wired them in.

### What's sitting unprocessed

| Archive Package | Files | What It Does | Why We Need It |
|----------------|-------|--------------|----------------|
| `data/ml/src/learning_engine/` | 23 files | Q-Learning, Bandits for tool routing | Strategy 5 of unified router — currently unimplemented |
| `data/ml/src/intelligence/` | 31 files | Outcome prediction, agent selection | Picks best agent for a task based on history |
| `data/ml/src/memory_core/` | 26 files | Episodic memory, semantic memory, consolidation | Makes memory actually useful |
| `data/ml/src/local_llm/` | 19 files | Local inference, model loading | Offline-capable AI, no API costs |
| `archive/data_chaos/masterplans/` | 6 files | 828-line consolidation masterplan, brain architecture, learning masterplan | Already researched — told us what to build |

### Integration plan

| Step | What | File(s) | Depends On |
|------|------|---------|------------|
| 1 | Fix broken imports (15+ files have wrong paths) | `data/ml/src/learning_engine/*.py` | nothing |
| 2 | Uncomment `record_outcome()` calls | `data/ml/src/intelligence/router.py` | Step 1 |
| 3 | Wire Q-Learning into Strategy 5 of unified router | `services/megatool-mcp/unified_bridge.py` | Step 2 |
| 4 | Wire Bandits for tool selection | `services/megatool-mcp/server.py` | Step 1 |
| 5 | Hook consciousness_daemon into learning engine | `services/mojo-router/src/consciousness_daemon.py` | Steps 1-3 |
| 6 | Make MiniLM embeddings feed into memory_core | `services/mojorouter/src/embed_bridge.py`, `target/debug/minilm-cli` | Step 5 |

### Verification
- After Step 2: task outcomes appear in `data/learning/outcomes/log.jsonl`
- After Step 3: router starts preferring agents that succeeded on similar tasks
- After Step 6: memory searches return semantically relevant results

---

## LEVEL 4: AGENT PROMPTS — Fix Tool Name Rot

**ROI: Medium-High.** 6 agents call tools by wrong names — prompts are training the LLM wrong.

### The rot map (from Scalpel audit)

| Agent | Wrong Name | Correct Name |
|-------|-----------|-------------|
| Explore | `code_search()`, `memory_search()`, `grep()`, `glob()`, `read()`, `batch_read()` | `search_code`, `search_memory`, `file_grep`, `file_glob`, `file_read`, `file_batch_read` |
| Librarian | `websearch()`, `webfetch()` | `web_search`, `web_fetch` |
| Prometheus | `write`, `code_search` | `file_write`, `search_code` |
| Mr. White | `websearch`, `read`, `write`, `bash` | `web_search`, `file_read`, `file_write`, `bash` |
| Phi-4 | "compiled Rust tools" | no Rust tools exist — remove claim |
| Jarvis | "dictation routes here" | no dictation integration exists — update prompt |

### Fix per agent
```
# Pattern:
# agent/explore/agent.js:
#   grep() → file_grep()
#   glob() → file_glob()
#   read() → file_read()
#   batch_read() → file_batch_read()
#   code_search() → search_code()
#   memory_search() → search_memory()
```

### Verification
- After fix: each agent's prompt uses only tool names that exist in its tools.json allowed list
- No agent claims capabilities it doesn't have tools for

---

## LEVEL 5: INFRASTRUCTURE — Kill Dead Services, Consolidate, Env-ify

**ROI: Medium.** Reduces maintenance surface, prevents future bugs.

### Kill list
| File | Reason | Replacement |
|------|--------|-------------|
| `services/mojo-router/src/codex_daemon.py` | Duplicates code_search_bridge.py with worse path handling | Delete it |
| `services/mojo-router/src/event_daemon.py` | Spawns Python subprocess per event — slow | In-process routing via plugin |
| `.opencode/plugins/nx-agents.config.js` | "Auto-generated" but no generator exists — stale | Delete it |

### Consolidate
| Current | Target | Why |
|---------|--------|-----|
| `config/nx_agents.json` | merge into `opencode.json` | Two configs = drift factory |
| `bins/` scattered binaries | `bins/` with index | Know what's available |
| `services/megatool-mcp/server.py` (1924 lines) | Split into `file-tools.py`, `memory-tools.py`, `parallel-tools.py`, `admin-tools.py` | Maintainability |

### Add PROJECT_ROOT env var
Current: 30+ hardcoded `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND` paths
Fix: Add to `.bashrc` or opencode config, read from `os.environ.get('NXYME_ROOT', default)` in every service

---

## LEVEL 6: CONSCIOUSNESS — Real Embeddings, Not Fake

**ROI: Medium.** Currently `identity_vector` is always `None` — the "embedding space" is a lie.

### Current state
- `services/mojo-router/src/consciousness_daemon.py` tracks outcomes in JSON
- `identity_vector` is always `None` — no actual embeddings
- Claims "896-dim identity" but it's just outcome counters

### Fix
1. Use `target/debug/minilm-cli` (384-dim MiniLM) to embed agent identity
2. Store real embeddings in `data/memory/consciousness/{agent}.json`
3. Use `nx-tools_embed_text` to generate on first interaction
4. Evolve embeddings via exponential moving average on each outcome

### Verification
- `consciousness_identity(cortex)` returns non-null vector
- Similar agents (explore vs librarian) have closer embeddings than different ones (kairos vs hephaestus)

---

## LEVEL 7: LEARNING — Wire Outcome-Driven Routing

**ROI: Very High.** This is what makes the system "smart" vs just "obedient".

### Current state
- Outcomes logged to `data/learning/outcomes/log.jsonl`
- But NOTHING reads them — no learning loop
- `unified_bridge.py` calls `record_outcome()` but it's commented out

### Implementation
1. Uncomment `record_outcome()` in `services/megatool-mcp/unified_bridge.py`
2. Fix broken imports in `data/ml/src/intelligence/router.py`
3. Wire router into `services/megatool-mcp/server.py` tool dispatch
4. Add `learn_from_outcome` callback to BackgroundManager (Level 1)
5. After 10+ outcomes per agent, consciousness_daemon evolves identity

### What the learning loop looks like
```
Tool call → outcome (success/fail) → record_outcome()
  → Q-Learning updates agent_score[agent][task_type]
  → Bandit algorithm selects best agent for next similar task
  → Consciousness evolves identity embedding
  → Memory stores the lesson
```

---

## LEVEL 8: MCP — Split Megatool into Modular Files

**ROI: Medium-High.** 1924 lines is unmaintainable — one typo crashes all 47 tools.

### Split plan
| New File | Tools | Lines |
|----------|-------|-------|
| `services/megatool-mcp/file-tools.py` | file_read, write, edit, glob, grep, batch_read, project_map, safe_delete | ~300 |
| `services/megatool-mcp/memory-tools.py` | read/write/list_memory, search_memory/semantic, embed_text/similarity | ~250 |
| `services/megatool-mcp/admin-tools.py` | config_edit/validate/remove/sync, agent_add/list/edit, schema_check | ~300 |
| `services/megatool-mcp/parallel-tools.py` | parallel_task, task_status, session_tasks, bg_submit/status/list/cancel/events | ~350 |
| `services/megatool-mcp/web-tools.py` | web_fetch, web_search | ~200 |
| `services/megatool-mcp/review-tools.py` | review_code, review_adversarial | ~150 |
| `services/megatool-mcp/consciousness-tools.py` | consciousness_record/identity | ~100 |
| `services/megatool-mcp/server.py` | Router only — imports from above | ~200 |

---

## LEVEL 9: AGENT REGISTRATION — Register Missing Agents

**ROI: High.** Cortex and Sisyphus Junior have agent.js + tools.json but are NOT available.
Also: Sisyphus references `delegate_task` and `route_task` which don't exist.

### Fixes
1. Add Cortex to opencode.json with proper entry
2. Add Sisyphus Junior to opencode.json with proper entry (already there actually — check)
3. Implement `delegate_task` and `route_task` in megatool-mcp (or alias to existing tools)
4. Add missing agent directories to no-code-sisyphus.js resolve functions

---

## LEVEL 10: MONITORING — Health Checks + Log Rotation

**ROI: Medium.** Prevents unbounded disk growth + silent failures.

### Add
- `health` / `ping` tool to each MCP server
- Log rotation for: `data/audit/calls.jsonl`, `data/audit/alerts.jsonl`, `data/sessions/ralph-debug.log`, `data/sessions/nx-plugin.log`, `/tmp/nx-plugin-traffic.jsonl`
- Session archiver cron job (script exists at `data/scripts/archive-sessions.py`)

---

## DEPENDENCY MAP

```
Level 1 (Plugin BgManager) ───────────────────────┐
                                                   │
Level 2 (MCP Bug Fixes) ────────┐                 │
                                │                 ▼
Level 3 (Archive Data) ─────────┼─────────> Level 7 (Learning Loop)
                                │                 │
Level 4 (Agent Prompts) ────────┘                 │
                                                   │
Level 5 (Infrastructure) ────────┐                 ▼
                                 │         Level 10 (Monitoring)
Level 6 (Consciousness) ─────────┤
                                 │
Level 8 (MCP Split) ─────────────┤
                                 │
Level 9 (Agent Registration) ────┘
```

### Parallel batches
**Batch A (no deps):** Levels 2, 4, 5, 6, 8, 9, 10 — all can run simultaneously
**Batch B (depends on A):** Level 3 (needs L2 fixes for stable MCP)
**Batch C (depends on B):** Level 7 (needs L3 archive data working)
**Batch D (independent):** Level 1 — can run anytime, but best AFTER Levels 4+9 so agents can actually be dispatched

---

## RISK ASSESSMENT

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Level 1 breaks task dispatch | Medium | High | Roll back plugin file, keep old ralph-autoloop.js |
| Level 2.3 (web_fetch fix) breaks URL fetching | Low | Medium | Test with 10 URLs of varying complexity |
| Level 3 archive imports still broken | High | Medium | Fix incrementally, one file at a time, test each |
| Level 8 MCP split breaks server.py | Medium | Critical | Keep backup of original, test each new file independently |
| Config drift fix breaks agent loading | Low | Critical | Validate JSON after every change, keep backup of opencode.json |
| Learning loop (L7) makes bad routing decisions | Medium | Low | Start with epsilon-greedy (90% exploration), monitor for 100+ tasks before switching to exploitation |

---

## HIGHEST-ROI ORDER (if you can only do 3 things)

### ROI #1: Level 2 Bug Fixes (~30 min, prevents crashes)
Fix the 5 critical bugs. No new features — just stop bleeding.

### ROI #2: Level 4 Tool Name Fixes (~45 min, 6 agents)
Fix agent prompts to use correct tool names. Zero risk, immediate improvement in agent reliability.

### ROI #3: Level 7 Outcome Recording (~2 hours, enables learning)
Uncomment `record_outcome()`, fix broken imports in learning engine. This ONE change enables the entire self-improvement loop. After this, every task completion makes the system smarter.
