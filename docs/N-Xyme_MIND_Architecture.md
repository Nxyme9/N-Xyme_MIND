# N-Xyme_MIND System Architecture

> A comprehensive mindmap of the N-Xyme_MIND intelligent agent orchestration system

---

## 🔧 ROOT CONFIGURATION

- `opencode.json` — Main config (446 lines, 11 agents, 14 MCPs, 9 providers)
- `oh-my-openagent.json` — Agent definitions
- `AGENTS.md` — Workspace rules (1308 lines)
- `.env` — API keys, tokens
- `triggers.json` — Action registry

---

## 🤖 AGENTS (11)

| Agent | Role | Model |
|-------|------|-------|
| **Sisyphus** | Primary orchestrator | `qwen3.6-plus-free` |
| **Prometheus** | Plan builder | `mimo-v2-pro-free` |
| **Hephaestus** | Implementation | `minimax-m2.5-free` |
| **Oracle** | Architecture review | `mimo-v2-pro-free` |
| **Momus** | Red-team / adversarial | `kimi-k2.5-free` |
| **Metis** | Pre-planning / gap analysis | `mimo-v2-pro-free` |
| **Explore** | Codebase search | `minimax-m2.5-free` |
| **Librarian** | External research | `minimax-m2.5-free` |
| **Atlas** | Plan executor | `minimax-m2.5-free` |
| **Sisyphus-Junior** | Trivial fixes | `llama3.2:3b` |
| **Multimodal-Looker** | Vision/media | `mimo-v2-omni-free` |

---

## 🔌 MCP SERVERS (14)

```
sequential-thinking  →  Chain-of-thought reasoning
context7             →  Live documentation lookup
nx-mind              →  Project state & session tracking
unified-memory       →  Cross-source memory search
learning-engine      →  Q-Learning routing, outcomes
intelligence         →  Predictive routing, load balancing
quality-gates        →  TypeScript/Python gates
telegram             →  Bot notifications
nx-context           →  Context injection
trigger-guardian     →  Command routing
orchestration        →  Agent task spawning
notion               →  Notion API integration
obsidian             →  Obsidian vault integration
github               →  GitHub API integration
```

---

## ☁️ PROVIDERS (9)

- **opencode** — Primary model provider
- **openrouter** — Routing layer
- **ollama** — Local models (qwen2.5-coder:7b)
- **lmstudio** — Local model management
- **gguf** — GGUF model format
- **anthropic** — Claude models
- **google** — Gemini models
- **deepseek** — DeepSeek models
- **xai** — xAI models (Grok)
- **cohere** — Cohere models

---

## 📦 CORE PACKAGES

### memory_core
- `daemon` — Background memory processes
- `router` — Memory routing logic
- `tier_manager` — Memory tier organization
- `self_healer` — Automatic error recovery

### learning_engine
- `self_learning` — Continuous learning
- `skill_lifecycle` — Skill tracking & evolution
- `prompt_evolution` — Prompt optimization

### intelligence
- `predictive_router` — ML-based routing
- `load_balancer` — Request distribution
- `circuit_breaker` — Failure isolation

### orchestration
- `agent_loop` — Agent execution loop
- `langgraph_workflow` — Graph-based workflows
- `react_agent` — ReAct agent implementation

---

## 📂 DIRECTORY STRUCTURE

### `.sisyphus/`
- Session state management
- Learning data
- Routing database (`routing.db`)

### `athena/`
- Core framework implementation

### `bin/`
- 71 scripts for:
  - Health checks (L0/L1/L2)
  - MCP server management
  - Model router

### `configs/`
- `model_router.json` — Model selection
- `ollama/` — Ollama configuration
- `vpn/` — VPN setup

### `packages/`
- 25 modular packages

### `_bmad/`
- BMAD workflows (phase 1-5)

---

## ❤️ HEALTH CHECKS

| Level | Script | Duration | Purpose |
|-------|--------|----------|---------|
| **L0** | `bin/health-l0-blink.sh` | <1s | Pre-flight checks |
| **L1** | `bin/health-l1-pulse.sh` | <10s | Service status |
| **L2** | `bin/health-l2-vitals.sh` | <60s | Deep diagnostics |

---

## 🚀 STARTUP SEQUENCE

```
bootstrap.sh  →  Fresh environment setup
      ↓
   env.sh     →  Environment variables
      ↓
n-xyme-mind.sh →  Main entry point
```

---

## 🧠 MEMORY & LEARNING ARCHITECTURE

### 5-Layer Routing Pipeline
```
Trigger Match → Memory Query → Local Model → Learning → Keyword Fallback
     ↓              ↓              ↓           ↓           ↓
   108k/s        13k/s         ML-based   Real-time    L1-L5
   matches       reads         analysis   weights      scoring
```

### Self-Learning System
- **Exploration Rate:** 20% — Try new strategies
- **Consolidation Rate:** 95% — Retain learned patterns
- **Q-Learning** — Routing optimization
- **Skill Lifecycle** — Track skill evolution

---

## 🔄 DELEGATION FLOW

```
User Request
     ↓
Sisyphus (orchestrator)
     ↓
┌────┴────┐
↓         ↓
Explore  Prometheus
(L1-L3)   (L4-L5)
     ↓         ↓
Hephaestus  Hephaestus
(implement)  (implement)
     ↓
  Oracle
(architecture review)
     ↓
  Momus
(red-team)
     ↓
   ✓ Complete
```

---

## 📊 KEY METRICS

- **Routing Predictions:** 388,902/sec
- **Trigger Matching:** 108,641/sec
- **MCP Tool Calls:** 3,872/sec
- **Outcomes Logged:** 346+
- **Agents Tracked:** 12
- **Triggers Configured:** 24

---

## 🛡️ SECURITY

- File access sandboxed to project directory
- Dangerous commands blocked
- Sensitive files protected (.env, .git)
- Security gates: gate-5-secrets, gate-8-security-paths

---

> Last Updated: 2026-04-09 | Version: 3.4