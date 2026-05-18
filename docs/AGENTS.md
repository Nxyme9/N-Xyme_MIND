# nx-agents: Agent Orchestration Platform

## Overview

nx-agents is a modular agent orchestration system. Each agent has its own folder with self-contained prompt, skills, and configuration. The primary orchestrator (Sisyphus) routes tasks to specialist sub-agents.

## Agents

| Agent | Mode | Role | Skills |
|-------|------|------|--------|
| Catalyst | primary | Plan, delegate, coordinate | orchestrate, spawn |
| Kairos - Personal Therapist | all | ADHD, CBT, executive function, RSD-safe | therapy, sessions |
| Oracle - Architecture | subagent | Read-only architecture consultant | consult |
| Momus - Critic | subagent | Adversarial review, find gaps | audit |
| Metis - Consultant | subagent | Pre-planning, surface assumptions | — |
| Hephaestus - Builder | subagent | Deep implementation with quality gates | build |
| Prometheus - Planner | subagent | Strategic planning with dependency ordering | plan |
| Mr. White - Chemistry | all | Lab procedures, safety, calculations | — |
| Phi-4 Reasoner | subagent | Multi-step logic, math, analysis | — |
| Vision Analyst | subagent | Visual/media analysis | — |
| Atlas - Plan Executor | primary | Plan execution, tracking & cross-agent coordination | track |
| System Architect | all | Live system awareness, change detection | map |
| Explore - Search | subagent | Codebase search | scan |
| Librarian - Research | subagent | External research, docs, best practices | deepdive |
| Jarvis - Personal Assistant | all | General assistant (voice removed) | — |

## Structure

```
nx-agents/
├── nx_agents.json          # Unified config: agents, models, routing
├── AGENTS.md               # This file
├── agents/                 # Agent definitions (folder per agent)
│   ├── sisyphus/agent.js   # Agent prompt + config
│   ├── sisyphus/skills/    # Agent-specific skills (SKILL.md files)
│   ├── kairos/
│   ├── ... (15 agents)
├── src/
│   ├── mcp/                # Rust MCP server (lightweight tools)
│   └── jailbreak-cli/      # Rust CLI tool
├── docs/
│   └── ARCHITECTURE.md     # Architecture documentation
├── bins/                   # Compiled binaries
├── config/
│   └── models.json         # Model overrides (legacy — use nx_agents.json)
└── plugin/                 # Legacy — agents migrated to agents/
```

## Key Principles

- **ADHD-aware design**: RSD-safe language, time-anchored tasks, external executive function
- **Quality gates**: typecheck → lint → test — all must pass before done
- **Adversarial review**: never the same agent writes and reviews code
- **Parallel execution**: independent tasks fire simultaneously

## Adding an Agent

1. Create `agents/{name}/agent.js` with `export default { name, mode, color, description, prompt }`
2. Add agent-specific skills to `agents/{name}/skills/{skill-name}/SKILL.md`
3. Register in `nx_agents.json` under the `agents` array
