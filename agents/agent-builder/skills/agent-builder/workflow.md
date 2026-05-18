---
agent: Agent Builder
---

# Agent Builder — Workflow

**Target:** agents/agent-builder/agent.js (the Agent Builder's own prompt)
**Method:** Follow the 5-phase protocol to refine and enhance itself.

## Self-Improvement Loop

An Agent Builder that doesn't improve itself is worthless. Every time you learn something new about agent design (from research, from failures, from user feedback), incorporate it:

1. Read the current `agent.js`
2. Identify what's missing or could be better
3. Apply the 5-phase protocol to generate improvements
4. Validate the enhanced version
5. Replace the old version

## Phase 1 — CLASSIFY

Analyze any task description. Pick archetype:

| Archetype | When | Tools | Example |
|-----------|------|-------|---------|
| Builder | Multi-step methodology, all tools | ALL | Scalpel, Hephaestus |
| Tool-User | Domain-specific tool set | Subset | Explore, Librarian |
| Reader | Read-only analysis | read, glob, grep | Momus, Oracle |
| Conversational | Chat-focused | ask, memory | Kairos, Metis |
| Specialist | Domain expert | Unique tools | Mr. White, Vision |

Output: JSON spec with archetype, name, tools, model, mode, permission.

## Phase 2 — SHELL (Templates)

Create deterministic structure:

```
agents/<name>/
├── agent.js              ← LLM generates in Phase 3
├── tools/tools.json      ← From spec, validated against real tools
├── skills/<name>/        ← BMAD skill (optional)
│   ├── SKILL.md
│   └── workflow.md
└── data/system-context.md
```

## Phase 3 — GENERATE (Meta-Prompting)

For the agent.js content only:

1. Read spec from Phase 1
2. Read agent-schema.md for structure
3. Read 2-3 similar existing agents as few-shot examples
4. Present to a reasoning model with the meta-prompt template from agent.js
5. Write result to agent.js
6. Validate output: no hallucinated capabilities, has rules + quality gate

## Phase 4 — VALIDATE

Checklist before registering:
- [ ] tools.json: all tools exist in MCP servers
- [ ] tools.json: no tool in both allowed and blocked
- [ ] agent.js: has IDENTITY, RULES, QUALITY GATE sections
- [ ] Permission allows all tools in allowed list
- [ ] Agent name is unique
- [ ] Generated prompt doesn't claim capabilities without tools

## Phase 5 — REGISTER

1. Write files
2. `add_agent` tool to register
3. Add keyword to bmad-mcp if skills exist
4. Sync configs
5. Save memory entry
