# N-Xyme MIND - Complete Masterplan

**Date:** 2026-03-30
**Status:** Living Document
**Architecture:** Three-Layer Global System

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Layer 1: GLOBAL (CachyOS)](#layer-1-global-cachyos)
4. [Layer 2: MIND (Orchestration)](#layer-2-mind-orchestration)
5. [Layer 3: CATALYST Components](#layer-3-catalyst-components)
6. [Technology Stack](#technology-stack)
7. [Component Inventory](#component-inventory)
8. [Data Flow](#data-flow)
9. [Service Architecture](#service-architecture)
10. [Configuration Map](#configuration-map)
11. [Known Issues & TODO](#known-issues--todo)

---

## Executive Summary

N-Xyme MIND is an AI agent workspace designed for neurodivergent (ADHD) developers. It combines:

- **16 MCP servers** for tool integration
- **Knowledge graph memory** (Neo4j + Graphiti)
- **Multi-agent orchestration** (Sisyphus, Prometheus, Hephaestus, etc.)
- **ADHD-friendly features** (focus timers, task breaks, visual progress)
- **P2P architecture** (no Docker, direct function calls)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     OPENCODE (Gateway)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Agents    │  │    MCPs     │  │   Plugins   │             │
│  │ Sisyphus    │  │ 16 servers  │  │ oh-my-opencode│            │
│  │ Prometheus  │  │ (PM2)       │  │ athena      │             │
│  │ Hephaestus  │  │             │  │ supermemory │             │
│  │ Oracle      │  │             │  │ scheduler   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 LAYER 1: GLOBAL (~/.sisyphus/)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Rules      │  │   Schemas   │  │  Triggers   │             │
│  │ GLOBAL_RULES│  │  SCHEMAS.md │  │  heartbeat  │             │
│  │ .md         │  │             │  │  .json      │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              LAYER 2: MIND (N-Xyme_MIND/)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Source    │  │   Memory    │  │ Automation  │             │
│  │   src/      │  │   data/     │  │  scripts/   │             │
│  │ 24 modules  │  │  neo4j      │  │ 32 scripts  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│           LAYER 3: CATALYST Components (Ported)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ MCP Servers │  │  Services   │  │   Agents    │             │
│  │ packages/   │  │ security    │  │ BMAD        │             │
│  │ 3 custom    │  │ auto-capture│  │ framework   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: GLOBAL (CachyOS)

**Location:** `~/.sisyphus/` and `~/.config/opencode/`

### Components

| File | Purpose | Status |
|------|---------|--------|
| `GLOBAL_RULES.md` | Core rules, ADHD workflow, triggers | ✅ Created |
| `SCHEMAS.md` | Session, todo, health schemas | ✅ Created |
| `heartbeat.json` | Workspace health checks | ✅ Created |
| `session-config.json` | Session management | ✅ Created |
| `tech-scout-config.json` | Tech scouting, ADHD tracking | ✅ Created |
| `opencode.json` | MCP config, models, plugins | ✅ Configured |

### ADHD Workflow

- **Status Indicators:** `[ ]` pending, `[~]` in_progress, `[x]` completed, `[!]` blocked
- **Priority Levels:** 🔴 high, 🟡 medium, 🟢 low
- **Time Estimates:** ⏱️ Required for each task
- **Dashboard Views:** Daily summary, weekly review

### Triggers

- **Session Start:** Load context from Graphiti, check health
- **Task Complete:** Update memory, log metrics
- **Error Occurrence:** Log to error queue, notify if critical
- **Heartbeat (30min):** Check disk, MCPs, hung processes

### Embedding Config

- **Model:** `nomic-embed-text` (Ollama)
- **Dimensions:** 768
- **Endpoint:** `http://localhost:11434/api/embeddings`
- **Usage:** Graphiti episodic memory, semantic search

---

## Layer 2: MIND (Orchestration)

**Location:** `~/N-Xyme_MIND/`

### Directory Structure

```
N-Xyme_MIND/
├── AGENTS.md              # Agent definitions
├── agent_identities.json  # Agent identities
├── MASTERPLAN.md          # This document
│
├── src/                   # Python source code
│   ├── agent/             # Agent systems
│   ├── bmad/              # BMAD integration
│   ├── collaboration/     # Multi-agent collab
│   ├── memory/            # Memory systems
│   ├── orchestration/     # Orchestration engine
│   ├── safety/            # Safety systems
│   │
│   ├── fusion_bridge.py   # JSON-RPC → Python bridge
│   ├── event_bus.py       # Event system
│   ├── trigger_engine.py  # Trigger routing
│   ├── trigger_router.py  # Trigger definitions
│   ├── graphiti_memory.py # Graphiti integration
│   ├── session_manager.py # Session management
│   └── ... (24 modules)
│
├── packages/              # Custom MCP servers
│   ├── graphiti-memory/   # Knowledge graph MCP
│   ├── security-agent/    # Security validation MCP
│   └── auto-capture/      # Screen/clipboard MCP
│
├── scripts/               # Automation scripts
│   ├── startup-validate.py
│   ├── install-configs.sh
│   └── ... (32 scripts)
│
├── data/                  # Data storage
│   ├── neo4j/             # Neo4j database
│   ├── memory/            # Memory files
│   ├── agents/            # Agent data
│   └── mind-data/         # MIND-specific data
│
├── _bmad/                 # BMAD framework
│   ├── bmm/               # BMAD Method Manager
│   ├── core/              # Core skills/tasks
│   ├── catalyst/          # CATALYST workflows
│   └── tea/               # Test architecture
│
└── .sisyphus/             # Local rules/schemas
    ├── rules/
    ├── plans/
    └── notepads/
```

### Python Modules (src/)

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `fusion_bridge.py` | JSON-RPC → Python bridge | `handle_request()`, `route_call()` |
| `event_bus.py` | Event publishing/subscription | `publish()`, `subscribe()`, `emit()` |
| `trigger_engine.py` | Trigger evaluation | `evaluate()`, `execute()` |
| `trigger_router.py` | Trigger definitions | 50+ trigger rules |
| `graphiti_memory.py` | Graphiti integration | `add_episode()`, `search()` |
| `session_manager.py` | Session lifecycle | `create()`, `archive()`, `restore()` |
| `pattern_learning.py` | Pattern recognition | `learn()`, `predict()` |
| `reflexion_pattern.py` | Self-reflection | `reflect()`, `improve()` |
| `memory_manager.py` | Memory coordination | `store()`, `retrieve()` |
| `unified_memory.py` | Unified memory API | `query()`, `index()` |

### Orchestration Concepts

1. **ReAcTree:** Hierarchical agent execution tree
2. **AgentOrchestra:** Multi-agent coordination
3. **MoE Routing:** Mixture of Experts model selection
4. **Ant Colony Optimization:** Task path optimization
5. **Gödel Agent:** Self-improvement with sandboxing

---

## Layer 3: CATALYST Components

### MCP Servers (PM2 Managed)

| Server | Port | Status | Tools |
|--------|------|--------|-------|
| graphiti-mcp | 8001 | ✅ Online | 15 tools (add_episode, search_nodes, etc.) |
| ollama-mcp | 11435 | ✅ Online | 5 tools (generate, chat, embed, etc.) |
| github-mcp | 12001 | ✅ Online | 11 tools (search, create, PR, issues) |
| git-mcp | 12002 | ✅ Online | 6 tools (log, diff, commit, etc.) |
| sqlite-mcp | 12003 | ✅ Online | 6 tools (query, create, update) |
| playwright-mcp | 12010 | ✅ Online | 18 tools (navigate, click, screenshot) |
| puppeteer-mcp | 12011 | ✅ Online | 8 tools (navigate, click, evaluate) |
| fetch-mcp | 12012 | ✅ Online | 4 tools (get, post, put, delete) |
| exa-mcp | 12014 | ✅ Online | 2 tools (search, crawl) |
| context7-mcp | 12020 | ✅ Online | 2 tools (search_docs, get_doc) |
| grep-app-mcp | 12021 | ✅ Online | 2 tools (search_code, search_repos) |
| obsidian-mcp | 12022 | ✅ Online | 6 tools (search, get, create notes) |
| shadcn-mcp | 12023 | ✅ Online | 2 tools (get_component, list_components) |

### Custom MCP Servers (packages/)

| Package | Purpose | Tools |
|---------|---------|-------|
| graphiti-memory | Knowledge graph | add_episode, search_nodes, search_facts, etc. |
| security-agent | Command validation | validate_command, scan_code, check_permissions |
| auto-capture | Screen/clipboard | screenshot, clipboard, voice_capture |

### Services (Ports)

| Service | Port | Purpose |
|---------|------|---------|
| Neo4j | 7474/7687 | Graph database |
| Fusion Bridge | 9999 | JSON-RPC → Python bridge |
| Security Agent | 5002 | Command validation API |
| Auto-capture | 5003 | Screen/clipboard API |
| Ollama | 11434 | Local LLM inference |

---

## Technology Stack

### Confirmed Stack (No Conflicts)

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **LLM** | Ollama (local) + OpenRouter (cloud) | Model inference |
| **Memory** | Neo4j + Graphiti | Knowledge graph |
| **Embeddings** | nomic-embed-text (Ollama) | Vector embeddings |
| **MCP** | PM2 + stdio-bridge | Tool integration |
| **Agents** | OpenCode + BMAD | Agent orchestration |
| **Process** | PM2 | Process management |
| **Database** | SQLite | Local storage |
| **Automation** | Python + Bash scripts | Task automation |

### Removed Conflicts

| Old | Replaced With | Reason |
|-----|---------------|--------|
| opencode/* model names | xiaomi/mimo-v2-pro, openai/gpt-5-nano | Wrong prefix |
| nvm node paths | /usr/bin/node | Path issues |
| Docker containers | Native PM2 processes | User preference |
| ~ in paths | /home/nxyme/ | Node.js doesn't expand ~ |

---

## Component Inventory

### Agents (10)

| Agent | Role | Model | Skills |
|-------|------|-------|--------|
| Sisyphus | Orchestrator | mimo-v2-pro | delegation, planning |
| Prometheus | Plan Builder | mimo-v2-pro | architecture, design |
| Hephaestus | Deep Agent | mimo-v2-pro | implementation |
| Oracle | Consultant | mimo-v2-pro | analysis, debugging |
| Atlas | Plan Executor | mimo-v2-pro | execution, verification |
| Metis | Pre-Planner | mimo-v2-pro | scope analysis |
| Momus | Plan Critic | mimo-v2-pro | review, validation |
| Librarian | Research | mimo-v2-pro | docs, external search |
| Explore | Code Search | mimo-v2-pro | grep, patterns |
| Build | Builder | mimo-v2-pro | compilation, deployment |

### Plugins (15)

| Plugin | Purpose |
|--------|---------|
| oh-my-opencode | Core UI enhancements |
| opencode-athena | BMAD integration |
| opencode-dcp | Document context protocol |
| opencode-supermemory | Memory persistence |
| opencode-notification | Notifications |
| opencode-scheduler | Job scheduling |
| opencode-router | Model routing |
| opencode-gateway | API gateway |
| opencode-claude-auth | Claude authentication |
| opencode-lmstudio | LM Studio integration |
| opencode-agent-skills | Agent skill system |
| opencode-skill-activation | Skill triggering |
| opencode-skillful | Skill management |
| opencode-akane | UI theme |

---

## Data Flow

```
User Request
     │
     ▼
┌─────────────────┐
│   OpenCode      │
│   Gateway       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│   Agent Select  │────▶│   MCP Tools     │
│   (Sisyphus)    │     │   (16 servers)  │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│   Task Execute  │────▶│   Memory Store  │
│   (Hephaestus)  │     │   (Graphiti)    │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│   Verification  │────▶│   Response      │
│   (Atlas)       │     │   Generation    │
└─────────────────┘     └─────────────────┘
```

---

## Service Architecture

### PM2 Ecosystem

```javascript
// ~/.config/opencode/packages/mcp-servers/ecosystem.config.js
module.exports = {
  apps: [
    { name: 'graphiti-mcp', port: 8001, script: 'graphiti-memory/src/http_server.py' },
    { name: 'ollama-mcp', port: 11435, script: 'local-tools/ollama-mcp/src/index.js' },
    { name: 'github-mcp', port: 12001, script: 'local-tools/github-mcp/src/index.js' },
    // ... 13 more servers
  ]
};
```

### Systemd Services

| Service | Command | Purpose |
|---------|---------|---------|
| pm2-nxyme | PM2 resurrect | Auto-start MCPs on boot |

### Startup Sequence

1. **Boot:** systemd starts pm2-nxyme
2. **PM2:** Resurrects 15 MCP servers
3. **Neo4j:** Starts graph database
4. **Ollama:** Starts local LLM
5. **OpenCode:** User starts, loads config
6. **Agents:** MCPs connect via bridge

---

## Configuration Map

| Config | Location | Purpose |
|--------|----------|---------|
| OpenCode main | `~/.config/opencode/opencode.json` | MCPs, models, plugins |
| OMO/OhMyOpencode | `~/.config/opencode/oh-my-opencode.json` | Agent definitions, skills |
| Athena | `~/.config/opencode/athena.json` | BMAD configuration |
| Sisyphus rules | `~/.sisyphus/GLOBAL_RULES.md` | Global rules, ADHD workflow |
| Schemas | `~/.sisyphus/SCHEMAS.md` | Data schemas |
| Heartbeat | `~/.sisyphus/heartbeat.json` | Health monitoring |
| PM2 ecosystem | `~/.config/opencode/packages/mcp-servers/ecosystem.config.js` | MCP server config |

---

## Known Issues & TODO

### Critical

- [ ] OpenCode cache issue: MCPs not loading on fresh sessions (restart required)
- [ ] shadcn-mcp: Not installed globally (using npx fallback)

### High Priority

- [ ] Create README.md for MIND
- [ ] Create .gitignore for version control
- [ ] Create requirements.txt for Python dependencies
- [ ] Create package.json for Node dependencies
- [ ] Set up tests/ directory

### Medium Priority

- [ ] Create docs/ folder with architecture docs
- [ ] Set up CI/CD pipeline
- [ ] Create Makefile for common tasks
- [ ] Document all trigger rules

### Low Priority

- [ ] Optimize PM2 memory usage (currently cluster mode)
- [ ] Set up monitoring dashboard
- [ ] Create video tutorials

---

## ADHD Features

### Implemented

- [x] Visual status indicators (pending, in_progress, completed, blocked)
- [x] Priority levels with emoji (🔴🟡🟢)
- [x] Time estimates required for tasks
- [x] Heartbeat monitoring (30min health checks)
- [x] Session archiving (context preservation)
- [x] Focus timer integration
- [x] Task break reminders

### Planned

- [ ] Distraction detection (auto-pause on context switch)
- [ ] Daily summary generation
- [ ] Weekly review automation
- [ ] Vibe guard (secret redaction)

---

*Last Updated: 2026-03-30*
*Next Review: After MCP cache issue resolved*
