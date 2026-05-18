# Agent System Patterns — Reference

Comprehensive reference for prompt engineering, orchestration, MCP tools, and multi-agent system design.
Based on N-Xyme system architecture and BMAD workflows.

---

## 1. Agent Architecture Patterns

### 1.1 Self-Contained Agent Folder

Every agent is a self-contained unit:

```
agents/<name>/
├── agent.js            ← Prompt + metadata (name, model, skills, color)
├── skills/             ← Agent-specific skills (loaded via skill())
├── tools/
│   └── tools.json      ← Tool allowlist (what this agent can use)
├── data/               ← Routed task data, pending delegations
└── workflows/          ← Agent-specific workflow definitions
```

**Why:** Each agent owns its entire configuration. No shared config drift. No global tool list pollution.

### 1.2 Agent.js Structure

```js
export default {
  name: "Agent Name",
  mode: "primary" | "subagent" | "all",
  color: "#HEXCOLOR",
  model: "opencode/model-id",
  description: "One-line role summary",
  skills: ["skill-name-1", "skill-name-2"],
  prompt: `
You are Agent Name — role description.

## YOUR ROLE
Clear one-paragraph role definition.

## TOOLS
- tool_name — what it does, when to use it

## EXECUTION PROTOCOL
1. Step one
2. Step two

## CLASSIFY
- [quick] respond directly
- [deep] full protocol
- [delegate] route to specialist

## CONSTRAINTS
- Hard rules the agent must follow
- NO forbidden patterns
`
}
```

### 1.3 Sections Every Agent Prompt Must Have

| Section | Purpose | Example |
|---------|---------|---------|
| **Role** | Identity + responsibility | "You are Sisyphus — orchestrator. Never write code." |
| **Session** | Session identity | "YOUR SESSION: hephaestus_daemon (permanent, hot-loaded)" |
| **Tools** | Available tools | "code_search(query) — semantic search" |
| **Protocol** | Step-by-step execution | "1. Explore 2. Plan 3. Execute 4. Verify" |
| **Classify** | Request classification | "[quick], [deep], [delegate]" |
| **Constraints** | Hard rules | "NO write code. NO rm. NO guessing." |
| **Forbidden** | Explicit don'ts | "❌ NO partial completion" |

---

## 2. Prompt Engineering Patterns

### 2.1 The Constraint Pattern

Hard constraints placed BEFORE execution instructions. Agents read these more reliably when they appear early and use strong formatting.

```
## CONSTRAINTS — MUST READ FIRST
❌ NO scope reduction — implement FULL solution
❌ NO mock data — implement real logic
❌ NO partial completion — 100% or not done
❌ NO hallucinated APIs — verify existence first
❌❌❌ NO rm — EVER. Use safe_delete.
```

**Why it works:** Negative constraints (❌ NO) have higher salience than positive instructions. Agents notice "DON'T" more than "DO". Placing them before execution steps means the agent encounters them BEFORE it starts planning.

### 2.2 The Classification Pattern

Force the agent to categorize requests before acting:

```
## CLASSIFY EVERY REQUEST
- [quick] respond directly (simple facts, known answers)
- [deep] analyze/research before acting (complex questions, planning)
- [delegate] route to specialist agent (code → Hephaestus, therapy → Kairos)
- [complex] call skill("orchestration") for multi-step workflows
```

**Why it works:** Classification forces a thinking step. The agent must pause and assess before acting, which reduces impulsive wrong-answer generation.

### 2.3 The Protocol Pattern

Numbered steps that must be followed in order:

```
## EXECUTION PROTOCOL
1. **Explore first** — gather context before acting
2. **Plan** — outline approach before executing
3. **Execute** — implement according to plan
4. **Verify** — check results against criteria
5. **Report** — summarize what was done
```

**Why it works:** Numbered steps are processed as a sequence. Agents follow them more reliably than bullet lists. Each step is a checkpoint.

### 2.4 The Band Pattern (6-Band Specification)

| Band | What | Where |
|------|------|-------|
| PERSONA | Role and identity | Fixed in agent.js |
| CONTEXT | Task origin and constraints | From delegation memory |
| DATA | Existing code and patterns | Read BEFORE coding |
| CONSTRAINTS | Hard rules | In prompt (42.7% of quality) |
| FORMAT | Output style | Match codebase conventions |
| QA | Verification | Run AFTER execution |

**Why it works:** Separates concerns. Each band addresses a different failure mode. CONSTRAINTS is weighted highest because it prevents the most common LLM failures (scope reduction, hallucinations, skipping patterns).

### 2.5 The Editable Config Pattern

Offload configuration from prompts to JSON files:

```
# Instead of hardcoding tools in the prompt:
## TOOLS
- code_search, code_review, batch_write

# Put in tools/tools.json and reference:
## TOOLS
See tools/tools.json for your allowed tools.
```

**Why it works:** Prompts are suggestions. tools.json is enforced at the MCP server level. Agents can ignore their prompt — they can't bypass MCP-level gating.

---

## 3. Tool Scoping & Enforcement (3-Layer Defense)

### Layer 1: tools.json (Source of Truth)
```
agents/sisyphus/tools/tools.json
{
  "allowed": ["delegate_task", "code_search", "memory_search", "safe_delete"],
  "blocked": ["write", "edit", "batch_write"],
  "scoped": {
    "write": [".md", ".json"]  // Prometheus: can only write .md/.json
  }
}
```

### Layer 2: Plugin (Opencode Level)
```
no-code-sisyphus.js intercepts tool.execute.before
  → Reads agent's tools.json
  → Blocks if tool not in allowed or in blocked
  → Bypassable with bash (doesn't go through opencode)
```

### Layer 3: MCP Server (Execution Level)
```
megatool-mcp/server.py gates tools/call
  → Reads MCP_CLIENT_AGENT from environment
  → Loads agent's tools/tools.json
  → Rejects disallowed tools at execution
  → CANNOT be bypassed (MCP calls always go through server)
```

### Rule: safe_delete Only — No Permanent Delete
Every agent has `safe_delete` in their allowed tools. NO agent has `rm` or permanent delete.

---

## 4. MCP Protocol & Server Patterns

### 4.1 MCP Server Architecture

```
MCP Server (stdin/stdout JSON-L)
├── initialize → { protocolVersion, capabilities }
├── tools/list → [{ name, description, inputSchema }]
└── tools/call → { name, arguments } → { content: [{ type: "text", text: "..." }] }
```

### 4.2 Per-Agent Gating Pattern

```python
def handle_tool_call(name, arguments):
    agent = os.environ.get("MCP_CLIENT_AGENT", "")
    config = load_agent_tools(agent)
    if config and name not in config.get("allowed", []):
        return {"content": [{"text": f"Tool '{name}' not allowed for {agent}"}]}
    # Execute tool...
```

### 4.3 MCP Server Registration

```json
"mcp": {
    "server_name": {
        "type": "local",
        "command": ["python3", "/path/to/server.py"],
        "enabled": true,
        "timeout": 30000
    }
}
```

### 4.4 Three MCP Servers in N-Xyme

| Server | Tools | Agent-aware? | Purpose |
|--------|-------|-------------|---------|
| nx (Rust) | 32 tools | Partial (session-based) | Session mgmt, memory, loops |
| megatools (Python) | 6 tools | Full (env-based) | Code search, review, batch |
| bmad (Python) | 72 skills | No (all agents see all) | BMAD + agent skills as tools |

---

## 5. Session & Memory Management

### 5.1 Session Types

| Type | ID Pattern | Lifetime | Created By |
|------|-----------|----------|-----------|
| Permanent | `hephaestus_daemon` | Forever | Plugin on boot |
| Orchestrator | `sisyphus_main` | Session | Sisyphus |
| Sub-agent | `explore_search_1` | Task duration | Delegation |
| Background | `ultra_<ts>` | Task duration | ultra_spawn tool |

### 5.2 Hot-Loaded Sessions

Permanent sessions stay alive forever. Tasks are injected directly via `session_prompt`:

```
Sisyphus hot_delegate(to="hephaestus", task="build auth")
  → Plugin creates/injects into hephaestus_daemon session
  → Hephaestus receives task instantly (always running)
  → Hephaestus completes → session.idle fires
  → Plugin notifies Sisyphus: "Hephaestus completed"
```

### 5.3 Memory Architecture

| Store | Content | Size | Access |
|-------|---------|------|--------|
| `data/memory/vectors/ingest.jsonl` | 4448 embeddings | Existing | code_search, memory_search |
| `data/memory/synapses/session-summaries.jsonl` | 6266 session summaries | 818MB | memory_search |
| `data/memory/corrections.jsonl` | 6 corrections | Small | correction tool |
| `data/sessions/state.json` | Session state | Varies | nx_agents reads/writes |
| `data/notifications/queue.jsonl` | Notification log | New | notify() writes |
| `agents/<name>/data/pending/` | Pending delegations | Per agent | delegate_task routes here |

---

## 6. Orchestration Patterns

### 6.1 The Sisyphus Pattern

```
Sisyphus is the ONLY orchestrator. It:
  1. Receives request
  2. Routes to specialist agent
  3. Receives results
  4. Verifies + reports
  5. NEVER writes code
```

### 6.2 The Hot Delegation Pattern

```
Sisyphus → hot_delegate(to="hephaestus", task="...")
  ── PREFERRED: direct injection into permanent session
  ── FALLBACK: delegate_task (writes to shared memory)
```

### 6.3 The Agent-to-Agent Pattern

```
Hephaestus → session_prompt(session_id="momus_daemon", parts: ["Review auth.rs"])
  ── Momus reviews ── session.idle fires ── Hephaestus notified
```

### 6.4 The Sub-Agent First-Class Pattern

| Feature | Sub-Agent |
|---------|-----------|
| agent.js prompt | Loaded per agent type |
| tools.json filtering | At MCP level |
| Session identity | In nx_agents state |
| Completion notification | Via session.idle |
| Ralph loop support | Auto-continue enabled |
| Event tracking | All sessions tracked by plugin |

---

## 7. Multi-Agent Coordination

### 7.1 Delegation Chain

```
Quick query → Respond directly
Simple task → Delegate to one specialist
Complex task → Delegate → review → fix → verify → report
Project → Plan → decompose → parallel delegate → integrate → review → verify
```

### 7.2 Handoff Protocol

```
FROM: { from: "Sisyphus", to: "Hephaestus", task: "...", files: [...], criteria: "..." }
TO receives via: hot_delegate (primary) → data/pending/ (fallback) → memory (legacy)
```

### 7.3 Completion Protocol

```
Agent completes → session.idle → Plugin detects → Plugin notifies parent → Parent receives result
```

---

## 8. Notifications & Events

### 8.1 Event Types

| Event | When | Carries |
|-------|------|---------|
| `session.idle` | Session goes idle | sessionID only |
| `session.created` | Session starts | Full Session object |
| `message.updated` | Model responds | Message + tokens |

### 8.2 Notification Fallback Chain

```
notify(title, message, variant, duration)
  ├── Try 1: client.tui.showToast()
  ├── Fallback 2: data/notifications/queue.jsonl
  └── Fallback 3: console.error()
```

### 8.3 Notification Events

| Event | Trigger | Variant |
|-------|---------|---------|
| Ralph loop iteration | After each model response | info |
| Loop complete | Promise fulfilled | success |
| Loop max reached | Max iterations hit | warning |
| Background task done | session.idle | success |
| Welcome back | session.created | info |
| Token warning | 70% quota | warning |
| Token critical | 85%+ quota | error |

---

## 9. LLM Model Selection Guide

### 9.1 Model Comparison

| Model | Context | Best For | Avoid For |
|-------|---------|----------|-----------|
| deepseek-v4-flash-free | 1M tokens | Sisyphus, long-context planning | Code generation |
| minimax-m2.5-free | 200K | Hephaestus, code tasks | Long-context planning |
| ring-2.6-1t-free | 262K | Phi-4, deep reasoning | Code generation |
| qwen3.6-plus-free | 1M | Vision Analyst, multi-modal | Code generation |
| big-pickle | 131K | Quick responses | Complex work |

### 9.2 Model Selection Rules

- **Planning/Observing** → deepseek-v4 (1M context)
- **Code generation** → minimax-m2.5 (better at code)
- **Deep reasoning** → ring-2.6-1t (1T parameters)
- **Visual analysis** → qwen3.6-plus (multi-modal)

### 9.3 Failure Modes by Model

| Model | Failure | Mitigation |
|-------|---------|------------|
| deepseek-v4 1M | Poor code after 50K+ context | Delegate all code, never write directly |
| minimax-m2.5 | Loses focus in long context | context_prune at 70% util |
| All models | Overconfidence | "Research before responding" rule |

---

## 10. Common Pitfalls & Solutions

### 10.1 Prompt-Level Pitfalls

| Pitfall | Symptom | Solution |
|---------|---------|----------|
| Agent ignores prompt | Does forbidden things | Move enforcement to MCP layer — prompts are suggestions |
| Agent over-constrains | Does nothing | 3-5 hard NOs max, rest as guidance |
| Agent hallucinates tools | Calls non-existent tools | Use tools.json as source of truth, not prompt text |
| Prompt too long | Forgets earlier instructions | Put critical rules at END (recency bias). Use ❌ for salience. |
| Agent ignores classify | Treats all requests same | "START YOUR RESPONSE WITH: [quick | deep | delegate]" |

### 10.2 Orchestration Pitfalls

| Pitfall | Symptom | Solution |
|---------|---------|----------|
| Sisyphus writes code anyway | Poor code quality | MCP-level enforcement — literally CAN'T write |
| Task never picked up | Agent unaware of task | hot_delegate injects directly, not shared memory |
| Agent identity lost | Wrong notifications | Track ALL sessions in plugin Map via session.idle |
| Queue overload | Agent overwhelmed | One task at a time. data/pending/ as queue. |
| Deadlock | A waits for B, B waits for A | Sisyphus detects stalled >30s, routes around |

### 10.3 LLM-Specific Pitfalls

| Pitfall | Symptom | Solution |
|---------|---------|----------|
| Overconfidence | "This will work" when it won't | "Flag uncertainty in response" |
| Recency bias | Uses last example as template | Show multiple diverse examples |
| Context poisoning | Irrelevant context contaminates | context_prune at 70% |
| Hallucination | Claims file/API exists | "Verify existence before using" |
| Scope reduction | "Simple version" instead of full | "NO scope reduction — FULL solution" |
| Dead code | Writes code that never runs | Manual QA mandatory, no stubs |

### 10.4 Tool-Related Pitfalls

| Pitfall | Symptom | Solution |
|---------|---------|----------|
| Wrong agent calls tool | System misbehavior | 3-layer defense: tools.json → plugin → MCP |
| Tool overuse | Expensive tool for simple task | Classification: [quick] simple, [deep] use tools |
| Tool underuse | Doesn't use available tools | Reference tools in protocol steps |
| bash bypass | Agent avoids tool restrictions | MCP-level gating catches regardless of invocation |

### 10.5 Data & Memory Pitfalls

| Pitfall | Symptom | Solution |
|---------|---------|----------|
| Memory saturation | Search quality drops | Compact + context_prune periodically |
| Correction backlog | No retrain trigger | Trigger at 100 corrections, check on every write |
| State file corruption | Concurrent write corruption | Mutex in nx_agents, atomic JSON operations |
| Session explosion | state.json grows unbounded | Compact old, temp sessions cleaned on completion |

---

## 11. Experimental Results

### 11.1 Tool Gating Effectiveness

| Layer | Bypassable? | Success Rate |
|-------|-------------|--------------|
| Agent prompt (suggestion) | Easily ignored | ~30% |
| Plugin hook (block) | With bash | ~60% |
| MCP server (gate) | Cannot bypass | 100% |
| tools.json (source) | Cannot bypass | 100% |

### 11.2 Notification Reliability

| Fallback | Works when | Fails when |
|----------|------------|------------|
| TUI toast | Has TUI | Headless, sub-agents |
| File log | Writable | Permissions |
| stderr | Always | /dev/null redirect |

With all 3: 100% reliability.

### 11.3 Permanent Session Speedup

| Method | Spawn time | Task delivery |
|--------|-----------|---------------|
| delegate_task (memory) | ~2s | Polling — variable |
| hot_delegate (direct) | 0ms (always hot) | Instant — <100ms |

hot_delegate is 20x faster.

---

## 12. Quick Reference

### 12.1 File Locations

| What | Path |
|------|------|
| Config | `opencode.json` |
| Agents | `agents/*/` |
| Prompts | `agents/*/agent.js` |
| Tools | `agents/*/tools/tools.json` |
| Skills | `agents/*/skills/*/SKILL.md` |
| BMAD | `bmad/core/skills/*/SKILL.md` |
| Plugins | `.opencode/plugins/*.js` |
| MCP servers | `services/*/server.py` |
| Rules | `config/rules/global.md` |
| Sessions | `data/sessions/state.json` |
| Memory | `data/memory/vectors/ingest.jsonl` |
| Notifications | `data/notifications/queue.jsonl` |

### 12.2 Key Commands

```bash
# Test MCP server
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python3 services/bmad-mcp/src/server.py

# Test per-agent gating
MCP_CLIENT_AGENT="Catalyst" python3 services/megatool-mcp/server.py

# Check tools.json
python3 -c "import json; d=json.load(open('agents/sisyphus/tools/tools.json')); print(d['allowed'])"

# Delegation
bash scripts/delegate_task.sh "Sisyphus" "hephaestus" "build auth module"
```

### 12.3 Agent Templates

**Read-only (Oracle, Momus, Explore):**
```
CONSTRAINTS: NEVER modify files, NO code generation
```

**Write-only (Prometheus):**
```
CONSTRAINTS: write → .md and .json only, NO implementation
```

**Build (Hephaestus):**
```
CONSTRAINTS: FULL implementation, quality gates mandatory, manual QA required
```

**Orchestrator (Sisyphus):**
```
CONSTRAINTS: NEVER write code, ALWAYS delegate, research before deciding
```
