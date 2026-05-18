# N-Xyme System Context — Mnemosyne Reference

## Architecture Overview
```
4 MCP Servers:
  - bash-mcp:     services/bash-mcp/server.py          (shell, delete-protected)
  - megatool-mcp: services/megatool-mcp/server.py       (55+ NAP tools)
  - bmad-mcp:     services/bmad-mcp/src/server.py       (72 BMAD skills)
  - nx_agents:    bins/nx_agents (Rust)                 (disabled)

2 Config Files (drift-prone):
  - opencode.json           → Primary: agents, MCP, plugins, models
  - config/nx_agents.json   → Custom N-Xyme keys

4 Core Agents:
  - Catalyst (sisyphus)     → Orchestrator. NEVER writes code.
  - Hephaestus              → Builder. Writes code, runs quality gates.
  - Atlas                   → Executor. Sprint plans, tracks, reports.
  - Hermes                  → Memory & Personal. Recall, therapy, support.

15+ Skills (loaded on demand by core agents)
```

## Agent File Structure
```
agents/<name>/
├── agent.js              ← System prompt (export default { name, skills, prompt })
├── tools/tools.json      ← Per-agent tool gating: { allowed: [...], blocked: [...] }
├── skills/<skill>/       ← Specialized skill workflows
│   ├── SKILL.md
│   └── workflow.md
└── data/                 ← Agent-specific context
```

## Agent Modes
- `primary` — talks to user, visible in agent list
- `subagent` — headless worker, spawned by other agents
- `all` — both visible and spawnable

## Session Data
```
data/sessions/*.jsonl         → Full session transcripts
data/memory/                  → Memory vectors, synapses, consciousness
data/memory/consolidated/     → Compacted sessions
```

## Known Failure Points (For Debugging)
1. task() drops identity — always use delegate_task or call_omo_agent
2. Config drift between opencode.json and nx_agents.json
3. rm is blocked server-side — use safe_delete
4. Restarting MCP servers from bash kills active connection
5. Agents using tools not in their tools.json allowed list
6. Quality gates skipped during build
7. Agent identity bleed (e.g., Catalyst writing code)
8. Former agents now skills — only 4 core agents

## Tool Naming Convention
All tools use snake_case NAP naming:
- file_read (not read_file)
- search_memory (not memory_search — though both may exist)
- delegate_task (not task)
- write_memory (not memory_write)
- safe_delete (not rm/delete)

## Identity Propagation
- delegate_task → identity IS propagated (parentSessionID, _agent)
- call_omo_agent → OMO-style, no blocking, identity propagated
- task() → identity IS DROPPED — NEVER use

## Session Protocol Pattern
All agent prompts have:
1. IDENTITY — who they are, what they NEVER do
2. CORE PROTOCOL — phased methodology
3. ANTI-HALLUCINATION — rules against inventing
4. RULES — hard constraints
5. TOOLS — what they can use and when
6. DELEGATION — who to delegate to
7. QUALITY GATE — verification checklist
