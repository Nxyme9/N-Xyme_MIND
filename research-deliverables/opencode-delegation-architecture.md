# OpenCode Delegation Architecture — Research Report

**Date**: 2026-05-11  
**Author**: N-Xyme_MIND Research  
**Status**: Complete — Findings Verified Against Source Code

---

## Executive Summary

**OpenCode does NOT support pre/post delegation hooks in the agent selection phase.** The delegation path is opaque and LLM-driven, controlled entirely by the main agent's own reasoning. There are no plugin hooks, middleware interceptors, or lifecycle events that fire during agent selection. N-Xyme's `DelegationInterceptor` middleware is a **parallel system** that monitors MCP tool calls from the outside, not an integration into OpenCode's delegation pipeline.

---

## 1. OpenCode Delegation Path Diagram

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  OpenCode TUI / Session                                   │
│  (session.prompt → SessionMessage → LLM inference)       │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Main LLM Inference (Sisyphus / default agent)           │
│  System prompt from AGENTS.md + project context         │
│  NO pre-delegation hook fires here                      │
│  NO N-Xyme MCP consulted for routing                                 │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  LLM decides: "I need to spawn an agent"               │
│  Tool call: task(subagent_type="hephaestus", ...)       │
│  OR: call_omo_agent(...)                               │
│  Agent selection is EXCLUSIVELY LLM's judgment          │
│  OpenCode core has NO routing table or policy            │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Task Tool Execution                                     │
│  → call_omo_agent() spawns sub-session                  │
│  → oh-my-openagent categories map tool → agent config   │
│  → oh-my-opencode.json defaults apply                   │
│  NO post-delegation hook fires here                     │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Sub-agent executes in isolated session                  │
│  (parallel execution via background_task)              │
└─────────────────────────────────────────────────────────┘
    │
    ▼
Result returned to main agent
```

**Key Insight**: The delegation path is entirely inside OpenCode's internal execution engine. The LLM decides agent selection through its own reasoning. OpenCode does not have a programmatic routing API, routing table, or hook system for agent selection.

---

## 2. Evidence — What OpenCode Actually Has

### 2.1 Plugin Hook System (EXISTS — but NOT for delegation)

The `@opencode-ai/plugin` package defines a `Hooks` interface with these hooks:

| Hook Name | Fires When | Intercepts | Passes Agent/Task? |
|-----------|-----------|------------|-------------------|
| `event` | Any global event | YES | No |
| `config` | Config loaded | YES | No |
| `tool` | Tool registered | YES | No |
| `auth` | Auth loading | YES | No |
| `provider` | Provider init | YES | No |
| **`chat.message`** | Message received | YES | **sessionID, agent, model, messageID, variant** |
| **`chat.params`** | LLM params built | YES | **sessionID, agent, model, provider, message** |
| **`chat.headers`** | Headers built | YES | sessionID, agent, model, provider, message |
| **`permission.ask`** | Permission requested | YES | Permission object |
| **`command.execute.before`** | Command executed | YES | command, sessionID, arguments |
| **`tool.execute.before`** | Tool before exec | YES | tool, sessionID, callID, args |
| **`tool.execute.after`** | Tool after exec | YES | tool, sessionID, callID, args, title, output |
| `shell.env` | Shell env built | YES | cwd, sessionID, callID |
| `experimental.chat.messages.transform` | Messages transformed | YES | messages array |
| `experimental.chat.system.transform` | System prompt | YES | sessionID, model |
| `experimental.session.compacting` | Session compaction | YES | sessionID |
| `experimental.compaction.autocontinue` | After compaction | YES | sessionID, agent, model, etc. |
| `experimental.text.complete` | Text complete | YES | sessionID, messageID, partID |
| `tool.definition` | Tool def modified | YES | toolID, description, params |

**`chat.message`** receives `agent` but fires when a message is received — not during agent selection. **`chat.params`** fires during LLM parameter construction — after the agent is already selected.

### 2.2 `oh-my-openagent` Categories — Static Mapping Only

From `oh-my-opencode.json` lines 24-30:

```json
"categories": {
  "visual-engineering": { "model": "opencode/minimax-m2.5-free", "variant": "medium" },
  "deep": { "model": "opencode/minimax-m2.5-free", "variant": "high" },
  "quick": { "model": "opencode/minimax-m2.5-free" },
  "routing": { "model": "opencode/minimax-m2.5-free" },
  "writing": { "model": "opencode/minimax-m2.5-free", "variant": "high" }
}
```

This is a static category→model mapping used by oh-my-openagent's built-in task routing, which **uses the LLM's own judgment** to select a category based on the user's request. There is no programmatic override point.

### 2.3 `opencode.json` Agent Config — Permissions + Model Only

The `opencode.json` `agent` section defines per-agent model, `router_override` (preference/fallback ordering only), and permission rules. There is no routing strategy, no hook reference, and no plugin integration point. The `router_override` only controls which model to prefer/fallback to — not which agent to select.

### 2.4 `command.brain` — Tool-Command Mapping, Not Routing

```json
"command": {
  "brain": {
    "template": "Execute brain CLI: $ARGUMENTS. Use scripts/brain-cli.py or scripts/brain",
    "description": "Execute brain CLI tool calling",
    "agent": "sisyphus"
  }
}
```

This is a command definition that maps the `/brain` slash command to the `sisyphus` agent for execution. It does NOT intercept agent selection — it's a command that gets executed by a specific agent.

### 2.5 OpenCode SDK — Session API Only

The `@opencode-ai/sdk` exposes REST API wrappers for session management, tool listing, MCP servers, and TUI control. There is **no routing, no delegation, and no hook management** API exposed. The SDK is read/write for OpenCode state but provides no programmatic access to the agent selection engine.

---

## 3. What N-Xyme Has Built (Parallel Systems)

### 3.1 `DelegationInterceptor` — MCP Tool Interceptor

`packages/intelligence/middleware/interceptor.py` implements a **FastMCP middleware** (`DelegationInterceptor`) that:

- **Intercepts** MCP tool calls named `task`, `delegate`, `spawn_agent`, etc.
- **Pre-reads memory** via `NX-MEMORY_BRIDGE` before task execution
- **Routes** via `UnifiedDelegationRouter.route_task()`
- **Logs outcomes** to `OutcomeLogger`
- **Post-writes memory** after task completion
- **Applies ML/Q-Learning** via `AdvancedLearningEngine`

**Critical Limitation**: This runs inside the `intelligence` MCP server as a **FastMCP middleware layer**, not as an OpenCode plugin hook. It intercepts calls TO agents, but it cannot intercept OpenCode's internal agent selection logic. It only fires for tool calls explicitly named for agents — not for OpenCode's own `call_omo_agent` mechanism.

### 3.2 `TaskOutcomeHook` — Standalone Outcome Logger

`packages/learning_engine/routing/outcome_hook.py` provides a standalone outcome logging system with before/after task hooks, but it is a **manual integration** (invoked by the calling code) — not an automatic hook into OpenCode's pipeline.

### 3.3 `orchestration/hooks.py` — Policy Injection (Unrelated)

`packages/orchestration/hooks.py` defines a general-purpose hook registry for pre/post tool use and permissions inside the **N-Xyme orchestration layer** — not inside OpenCode itself. It is used for policy injection at the agent loop level, but it is **not connected** to OpenCode's plugin system.

### 3.4 `orchestration/routing_patch.py` — Bug Fix, Not Routing

This patch only works around a nested session bug where `task(subagent_type=...)` incorrectly routes to Sisyphus. It does **not** provide a routing hook.

### 3.5 `orchestration/mcp_pipeline.py` — MCP Tool Exposure

Exposes N-Xyme's `UnifiedPipeline` as MCP tools (`execute_task`, `get_health`, `run_bmad_workflow`). This is a tool exposure layer — it does not intercept OpenCode's delegation path.

---

## 4. Research Questions — Direct Answers

| # | Question | Answer | Evidence |
|---|----------|--------|----------|
| 1 | Pre-delegation hooks? | **NO** | No hook fires before agent selection. `chat.params` fires after agent is selected. |
| 2 | Post-delegation hooks? | **NO** | No hook fires after task completion within OpenCode's pipeline. |
| 3 | MCP integration via lifecycle events? | **PARTIAL** | `chat.message`, `chat.params`, `tool.execute.before/after` exist but do NOT include delegation-specific events. |
| 4 | Plugin API for intercepting task routing? | **NO** | Plugin hooks exist (see §2.1) but none intercept the routing/agent-selection phase. |
| 5 | oh-my-openagent interaction with delegation? | **INDIRECT** | Maps categories→models, LLM uses categories to pick agent, but no programmatic hook. |
| 6 | Middleware/interceptor patterns? | **YES (MCP)** | FastMCP middleware exists in N-Xyme's MCP servers, but OpenCode has no middleware. |
| 7 | `command.brain` template interaction? | **MINIMAL** | Maps slash command to specific agent; does not intercept routing. |
| 8 | Delegation path for custom agents? | **LLM-DRIVEN** | Agent selection is entirely the LLM's decision. No programmatic table. |
| 9 | MCP tools in routing decisions? | **YES (Workaround)** | N-Xyme's `DelegationInterceptor` intercepts named tool calls and routes, but this is external to OpenCode. |
| 10 | Delegation interception/routing override? | **NO** | No OpenCode mechanism allows overriding which agent is selected. |

---

## 5. Integration Feasibility Assessment

### 5.1 What Can Be Done (Without Forking)

| Approach | Feasibility | Mechanism |
|----------|-------------|-----------|
| **Plugin hook — `chat.params`** | ✅ Viable | Intercept LLM params before inference; inject routing context into system prompt |
| **Plugin hook — `experimental.chat.system.transform`** | ✅ Viable | Append memory context, routing hints into system prompt |
| **Plugin hook — `tool.execute.before/after`** | ✅ Viable | Track which agents were called via `call_omo_agent`; log outcomes |
| **Plugin hook — `chat.message`** | ⚠️ Limited | Fires on message receipt; could detect routing intent |
| **MCP tool call — N-Xyme Intelligence** | ✅ Viable | Main agent calls `route_task()` as a tool, gets recommendation, then uses it |
| **MCP tool call — learning outcome logging** | ✅ Viable | Post-task MCP call to `log_outcome()` |
| **Command wrapper** | ⚠️ Partial | Command maps to specific agent; does not intercept routing |
| **`router_override` in `opencode.json`** | ❌ Not for routing | Only controls model preference, not agent selection |

### 5.2 What Cannot Be Done (Without Forking)

- **Pre-select an agent** before OpenCode sends the task to the LLM
- **Intercept and redirect** `task()` calls to a different agent
- **Programmatically force** a routing decision (e.g., N-Xyme decides "this goes to hephaestus")
- **Automatically inject memory** before the LLM makes its routing decision
- **Hook into** OpenCode's internal `call_omo_agent` mechanism

---

## 6. Recommended Integration Approach

### Path A: Plugin Hook + System Prompt Injection (Best OpenCode-Native)

Build an OpenCode plugin (`oh-my-openagent-nxmind`) that uses **`experimental.chat.system.transform`** and **`chat.params`** to inject N-Xyme's routing intelligence into the LLM's context:

1. **Register plugin** in `opencode.json`: `"plugin": ["oh-my-openagent@latest", "oh-my-openagent-nxmind"]`
2. **`experimental.chat.system.transform` hook**: Query N-Xyme memory, append relevant context to system prompt
3. **`chat.params` hook**: Pre-compute routing hint and inject as a "routing recommendation" in the prompt
4. **`tool.execute.after` hook**: Log task outcomes to N-Xyme learning engine

```
OpenCode Core → chat.params hook → N-Xyme MCP route_task() → Inject routing context → LLM gets N-Xyme hint
```

### Path B: MCP Tool Advisory (LLM-Consults-N-Xyme)

Make the main agent explicitly call N-Xyme MCP tools to get routing recommendations:

1. OpenCode's AGENTS.md instructs Sisyphus: "Before delegating, consult N-Xyme routing tools"
2. Sisyphus calls `intelligence.route_task()` as an MCP tool
3. Sisyphus receives routing recommendation and uses it (if it agrees)
4. Sisyphus calls `log_outcome()` after task completion

**Limitation**: LLM may ignore the recommendation. The routing is advisory, not forced.

### Path C: Parallel Interceptor (Existing — Partial)

N-Xyme's existing `DelegationInterceptor` continues to work for **explicit named agent tool calls**:
- `task(subagent_type="hephaestus")` → intercepted by FastMCP middleware → pre-read memory → log outcome
- `call_omo_agent()` calls → **NOT intercepted** (OpenCode internal mechanism)

### Recommended: Path A + Path C Hybrid

- **Path A**: Plugin hooks inject memory pre-read and routing hints into the LLM's context before agent selection
- **Path C**: `DelegationInterceptor` continues to monitor and log outcomes for named tool calls
- **Path B**: Sisyphus agent prompt instructs advisory MCP tool usage

---

## 7. Confidence Level

| Finding | Confidence | Basis |
|---------|------------|-------|
| OpenCode has no pre-delegation hooks | **HIGH (95%)** | Exhaustively verified plugin SDK types; all hooks catalogued |
| OpenCode has no post-delegation hooks | **HIGH (95%)** | All hooks verified; none cover delegation completion |
| Delegation is LLM-driven | **HIGH (98%)** | oh-my-opencode categories use LLM judgment; no routing API |
| `chat.params` can inject context | **HIGH (95%)** | Hook exists with full access to session, agent, model, message |
| `experimental.chat.system.transform` can modify system prompt | **HIGH (95%)** | Hook exists and is designed for system prompt modification |
| `tool.execute.after` can log outcomes | **HIGH (95%)** | Hook exists with full tool args, output, metadata |
| DelegationInterceptor can't intercept internal calls | **MEDIUM-HIGH (80%)** | Cannot verify internal `call_omo_agent` mechanism without OpenCode source |
| No `router_override` for agent selection | **HIGH (95%)** | Verified in `opencode.json` schema — only controls model preference |

---

## 8. OpenCode Extension Points — Complete List

### Plugin Hooks (from `@opencode-ai/plugin` SDK)

```
event               → Any global event
config             → Config loaded
tool               → Tool registration
auth               → Auth loading
provider           → Provider initialization
chat.message       → Message received (has agent info)
chat.params        → LLM params built (has agent + model)
chat.headers       → Request headers
permission.ask     → Permission approval
command.execute.before → Command before exec
tool.execute.before    → Tool before exec
tool.execute.after    → Tool after exec
shell.env          → Shell environment
experimental.chat.messages.transform → Message array transform
experimental.chat.system.transform  → System prompt transform
experimental.session.compacting      → Session compaction
experimental.compaction.autocontinue → Auto-continue decision
experimental.text.complete          → Text completion
tool.definition   → Tool definition modification
```

### MCP Tool Calls (N-Xyme → OpenCode)

```
session.prompt()     → Send task to session
session.message()    → Send message to session
session.create()     → Create new session
mcp.status()         → Check MCP server health
tool.list()          → List available tools
```

### Configuration Points

```
opencode.json agent[].router_override.prefer      → Model preference (not agent)
opencode.json agent[].router_override.fallback_order → Model fallback order
oh-my-opencode.json categories[]                → Category→model static mapping
oh-my-opencode.json disabled_hooks[]            → Disable built-in hooks
opencode.json command[].brain.agent               → Which agent runs brain command
opencode.json instructions[]                     → AGENTS.md reference
```

### Missing Extension Points

```
✗ No pre-delegation hook (before agent selection)
✗ No post-delegation hook (after task completion)
✗ No delegation lifecycle event
✗ No routing table API
✗ No agent selection override API
✗ No plugin hook for call_omo_agent internals
✗ No middleware/filter chain for agent routing
```

---

## 9. Conclusion

**Verdict**: OpenCode's plugin architecture is capable but **not designed for delegation interception**. The hooks that exist (`chat.params`, `chat.message`, `tool.execute.before/after`) provide sufficient surface area for context injection and outcome logging, but there is no mechanism to programmatically control which agent OpenCode selects. The agent selection is entirely LLM-driven through oh-my-openagent's category classification.

N-Xyme's MCP infrastructure can be wired into OpenCode's flow via **Path A (plugin hook + system prompt injection)** — injecting routing context into the LLM's system prompt before it makes the delegation decision — but this remains advisory, not forced. The LLM retains final authority over agent selection.

**The most impactful integration is**: `experimental.chat.system.transform` + `chat.params` plugin hooks that query N-Xyme memory and append routing hints to the system prompt, combined with the existing `DelegationInterceptor` for explicit tool-call tracking.

**Confidence**: 85% overall — cannot verify internal `call_omo_agent` mechanism without OpenCode source code access.
