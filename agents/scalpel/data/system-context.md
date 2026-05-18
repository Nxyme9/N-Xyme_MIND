# Scalpel Context — N-Xyme System State

## What We've Been Fighting

### 1. The Identity Problem (THE core struggle)

**The issue:** When opencode spawns a subagent via `task`, the subagent's tool calls carry NO agent identity to MCP servers.

**What we tried:**
- **Plugin hook (`tool.execute.before`)** — `input.agent` is always undefined/empty for subagents. Dead end.
- **Environment variables** (`MCP_CLIENT_AGENT`, `OPENCODE_AGENT`, etc.) — opencode doesn't set these for subagent processes. Dead end.
- **Session ID parsing** — subagent tool call args don't include `session_id` or `task_id`. Dead end.
- **Shared state file** (`data/active-agent.json`) — plugin writes to it on `task` call, MCP servers read it. But timing: subagent spawns before the plugin's AFTER hook fires. Race condition.
- **`_agent` field injection** — we assumed opencode injects `_agent` into MCP tool call arguments for ALL servers (like it does for nx_agents Rust). It doesn't. Only the Rust server checks for it because it was designed to.

**The actual solution:** XTUI (`bins/xtui`) injects `_agent` explicitly on every MCP tool call. It's a hack — `args["_agent"] = agent` before every call — but it WORKS. The MCP servers read `_agent` from args and gate per agent via `tools.json`.

### 2. Plugin Fragility

- `tool.execute.before` hook fires inconsistently — fires for built-in tools, sometimes for MCP tools, but `input.agent` is always empty
- `tool.execute.after` fires more reliably but too late for permission enforcement
- Every plugin modification requires an opencode restart to take effect
- Plugin syntax errors crash silently — one bad string escape and the whole plugin stops firing

### 3. Python String Escaping (silent failures)

Every time we modified files via `python3 -c` with inline string replacement, the escaping broke. `\n` became literal newlines in strings, quote matching failed, indentation got corrupted. We wasted hours on fixes that silently didn't apply. **The fix:** use heredocs (`<< 'PYEOF'`) or write files directly with `write_tool`.

### 4. MCP Process Management

- Killing an MCP server doesn't trigger opencode to restart it
- Only a full opencode restart reconnects MCP servers
- Manually starting MCP servers in background doesn't connect to opencode's routing
- When bash_mcp was killed, we lost our only way to run shell commands (catch-22)

### 5. Denied Too Aggressively

We set root `permission` to deny ALL built-in tools (`bash`, `write`, `edit`, `read`, `glob`, `grep`) before the MCP replacements were registered and working. This created a catch-22: couldn't use built-in tools to fix the config, and MCP tools weren't available yet. **Recovery:** `megatools_edit_config` still worked because MCP tools bypass the built-in permission check (they have different names like `edit_config` vs `edit`).

### 6. JSON Trailing Commas

Every edit that removed an item from an object or array left a trailing comma. opencode's JSON parser rejects trailing commas. The `nx-validate` script catches and fixes these, but opencode itself fails hard. **Fix:** always double-check JSON after removing entries.

### 7. nx_agents Rust MCP

The `bins/nx_agents` Rust binary (32 tools) consistently fails to return tools when opencode calls `tools/list`. Likely causes:
- `ort` crate (ONNX Runtime) linking to incompatible CUDA libraries
- Binary compiled for different system configuration
- ONNX model loading timeout (30s timeout may not be enough)

It works when tested directly via `echo '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | timeout 5 bins/nx_agents` — so the binary itself works. The issue is opencode's MCP lifecycle management.

### 8. Zombie MCP Servers

When we removed the `opencode_admin` MCP from config, the old server process kept running and its tools kept showing up in the UI. Had to manually `pkill -f opencode-admin-mcp` to kill it. opencode doesn't clean up MCP processes when config changes.

### 9. Subagent vs Main Agent Confusion

When the main AI session uses `task` to delegate to a subagent:
- The task tool call goes through the plugin (fires BEFORE and AFTER hooks)
- The subagent spawns as a new internal session
- The subagent's tool calls go through the same plugin hooks
- But `input.agent` is always "default" or undefined
- The subagent's identity is NEVER conveyed to MCP servers

This is THE fundamental problem. Everything else stems from it.

### 10. `_agent` Field Not Universal

Only the nx_agents Rust server checks `args.get("_agent")` in tool call arguments. This is a custom extension, not part of the MCP protocol or opencode's standard behavior. Other MCP servers (bash_mcp, megatools) don't receive `_agent` from opencode — it must be injected manually.

---

## What We Want

### The Dream Architecture

```
                      ┌─────────────────┐
                      │    XTUI / CLI    │   ← User interface
                      └────────┬────────┘
                               │ _agent injected
                               ▼
                      ┌─────────────────┐
                      │  opencode-core   │   ← Custom build from opencode source
                      │  (5 packages)    │     with proper _agent propagation
                      └────────┬────────┘
                               │
               ┌───────────────┼───────────────┐
               ▼               ▼               ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │ bash-mcp │   │megatools │   │ bmad-mcp │
        │          │   │ -mcp     │   │ (skills) │
        └──────────┘   └──────────┘   └──────────┘
```

### Key Requirements

1. **Agent identity propagates NATIVELY** — Every MCP tool call includes `_agent` from the framework, not from a hack
2. **Per-agent gating at MCP level** — Already works via `tools.json`
3. **Subagents inherit correct identity** — When Sisyphus delegates to Hephaestus, the bash_mcp server sees "Hephaestus - Builder", not "default"
4. **No plugin required for identity** — The plugin should only handle audit/logging, not identity injection
5. **One config file** — `config/nx_agents.json` is the source of truth, `opencode.json` is minimal
6. **All tools through MCP** — Built-in tools (bash, write, edit, read, glob, grep) are denied at root, MCP replacements handle everything with proper gating
7. **No zombie processes** — MCP server lifecycle managed properly
8. **Resilient to restarts** — Everything comes back clean without manual intervention

### The Two Paths Forward

**Path A — Custom opencode build (opencode-custom/)**
- Fork opencode source, strip 14 of 19 packages
- Fix `_agent` propagation at the source
- Build agent-aware MCP bridge
- Replace `bins/xtui` with proper CLI
- Cost: significant engineering effort

**Path B — XTUI + MCP proxy (current approach)**
- Keep using opencode as-is for AI chat
- XTUI handles identity injection at the frontend
- MCP proxy server can inject `_agent` for non-XTUI workflows
- Cost: works now, but is a hack

### The BMAD Workflow We Need

For any complex undertaking, the protocol should be:
1. `bmad-create-architecture` — Design decisions
2. `bmad-create-epics-and-stories` — Break into work units
3. `bmad-create-story` — Detailed story spec
4. `bmad-dev-story` — Implementation
5. `bmad-code-review` — Adversarial review
6. `bmad-retrospective` — Lessons learned

### Current State (Working)

- ✅ XTUI with `_agent` injection for tool calls
- ✅ 3 MCP servers (bash, megatools, bmad) with per-agent gating
- ✅ All built-in tools denied at root, everything through MCP
- ✅ 16 agents defined with proper permissions
- ✅ 10 agents have customized tools.json
- ✅ Scalpel agent with decompiler decision tree + BMAD awareness
- ✅ Session memory persistence
- ✅ 3-layer permission enforcement (plugin → config → MCP)
- ✅ Audit logging of all tool calls
- ✅ Delete-bypass detection (edit→empty, write→tiny)

### Current State (Broken)

- ❌ nx_agents Rust MCP (32 tools) fails to register — need to fix or recompile
- ❌ no-code-sisyphus SKILL.md in plugins/ loads into all agents (contaminates builder prompts)
- ❌ `_agent` injection is a frontend hack, not system-level
- ❌ Subagent identity not propagated by opencode
- ❌ Plugin modifications require restart

### What Should Guide Every Decision

1. **Everything through MCP** — No built-in tools for agents, only MCP with gating
2. **Agent identity everywhere** — Every tool call knows who's calling
3. **No hacks** — If it feels fragile, it will break
4. **Self-documenting** — Every component knows its purpose
5. **Resilient** — Restarting should fix things, not break them
