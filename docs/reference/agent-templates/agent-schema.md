# Agent Builder — Agent Definition Schema

An agent in this system = 4 files + 1 config entry.

## Structure

```
agents/<name>/
├── agent.js              ← System prompt (the agent's identity and rules)
├── tools/tools.json      ← Tool allowlist (what tools the agent can use)
├── skills/<skill-name>/  ← BMAD skill files (optional, for workflow skills)
│   ├── SKILL.md
│   └── workflow.md
└── data/                 ← Working directory (session memory, artifacts)
```

## Config Entry

In `opencode.json` (and synced to `config/nx_agents.json`):

```json
"Agent Name - Role": {
  "description": "One-line what this agent does",
  "mode": "primary | subagent | all",
  "model": "opencode/model-name",
  "permission": {"bash": "allow", "write": "allow", ...},
  "prompt": "{file:/path/to/agents/name/agent.js}"
}
```

## Archetype Templates

### 1. Tool-User (most agents)
- Has specific tools for a domain
- Instructions define WHEN to use each tool
- Example: Scalpel, Explore, Oracle

### 2. Builder (primary agents)
- Has ALL tools (bash, write, edit, read, glob, grep)
- Instructions focus on methodology and quality
- Example: Hephaestus, Sisyphus, Agent Builder

### 3. Reader (subagent, analysis)
- Only read, glob, grep, search tools
- No write/edit/bash
- Example: Momus, Oracle, Librarian

### 4. Conversational (all mode)
- Primarily ask/question tools
- Limited file access
- Example: Kairos, Jarvis, Metis

### 5. Specialist (domain expert)
- Domain-specific toolset (e.g., websearch+webfetch for research)
- Instructions are domain-heavy
- Example: Mr. White, Vision Analyst

## agent.js Structure

```
IDENTITY — Who the agent is (one paragraph)
PERSONALITY — How it behaves (optional)
CORE PROTOCOL — Phased methodology (if multi-step)
RULES — Hard constraints (anti-hallucination, safety)
TOOLS — When to use each tool (optional, for tool-heavy agents)
QUALITY GATE — What verification looks like before done
```

## permission Rules

Root denies all built-in tools. Agents override via per-agent `permission`:
```json
"permission": {"bash": "allow", "write": "allow", ...}
```

Tools not listed in the override default to root's value (deny).
