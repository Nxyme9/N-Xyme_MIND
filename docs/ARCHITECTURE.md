# N-Xyme_MIND — Architecture

> Comprehensive reference for the N-Xyme_MIND AI coding workspace. Covers system layers, component inventory, data flows, and deployment topology.

**Version:** Sprint 3  
**Audience:** System administrators, contributors, AI agents  
**Last updated:** Sprint 3 (Post-Sprint 2 Security & Performance Hardening)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Layer Architecture](#2-layer-architecture)
3. [Agent System](#3-agent-system)
4. [MCP Layer](#4-mcp-layer)
5. [Inference Engine](#5-inference-engine)
6. [Routing System](#6-routing-system)
7. [VPN & Proxy Infrastructure](#7-vpn--proxy-infrastructure)
8. [Configuration Model](#8-configuration-model)
9. [Data Storage](#9-data-storage)
10. [Deployment Topology](#10-deployment-topology)
11. [Security Model](#11-security-model)

---

## 1. System Overview

### High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                           OpenCode TUI                                 │
│                        (Desktop / Web Client)                          │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ stdio
┌──────────────────────────────────▼─────────────────────────────────────┐
│                         OMO Plugin (v3.14.0)                           │
│                      Agent Orchestration Layer                         │
│   Sisyphus → Catalyst → Hephaestus → Oracle → Explore → Librarian     │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ tool calls
┌──────────────────────────────────▼─────────────────────────────────────┐
│                         MCP Layer (62+ tools)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │  brain_mcp   │  │ memory_*    │  │ intelligence │  │  browser.*  │ │
│  │  (unified)   │  │ (12 tools)  │  │  (4 tools)  │  │  (6 tools)  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │  catalyst.*  │  │  session.*  │  │  learning.*  │                 │
│  │  (4 tools)   │  │  (4 tools)   │  │  (5 tools)   │                 │
│  └──────────────┘  └──────────────┘  └──────────────┘                 │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
             ┌───────────┐  ┌────────────┐  ┌────────────┐
             │  Local    │  │  Cloud     │  │  VPN       │
             │  GGUF     │  │  OpenRouter│  │  Rotation  │
             │ (RTX GPU) │  │  + Groq    │  │  + SOCKS5  │
             └───────────┘  └────────────┘  └────────────┘
```

### Component Count

| Category | Count | Notes |
|----------|-------|-------|
| Python packages | 48+ | Including MCP servers, routing, learning |
| MCP servers | 15+ | brain_mcp is central unified hub |
| Agent types | 11 | OMO v3.14.0 |
| Routing layers | 3 | Tool, Agent, Model |
| SOCKS5 proxies | 8 | Ports 1080-1087 |
| GGUF models | 4+ | llama3.2:3b, qwen2.5-coder:7b, etc. |
| Systemd services | 12 | User-level, in `~/.config/systemd/user/` |

### Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| TUI | OpenCode | v1.3.13 |
| Agent framework | OMO | v3.14.0 |
| MCP transport | stdio (local) | — |
| Local inference | llama.cpp (GGUF) | Server on port 8080 |
| Language | Python 3.11+ | Primary |
| GPU | NVIDIA RTX 3080 Ti | 12GB VRAM |
| OS | Linux (Arch-based) | Kernel 6.x |
| VPN rotation | SOCKS5 proxies | torshammer, provider plugins |

---

## 2. Layer Architecture

### Layer 1: TUI / Client

**Purpose:** User interaction entry point.

- OpenCode Desktop (desktop client with full TUI)
- OpenCode Web (browser-based)
- TUI Dashboard (`src.tui.ultimate_dashboard`) — custom monitoring interface

### Layer 2: Agent Orchestration (OMO)

**Purpose:** Multi-agent coordination, task decomposition, delegation.

The OMO plugin runs as a Sisyphus-Catalyst-Hephaestus triad:

```
Sisyphus (orchestrator) — Top-level task routing
  ├── Delegates to: Hephaestus (implementation), Oracle (review)
  ├── Spawns: Explore (search), Librarian (research)
  └── Consults: Oracle (architecture), Metis (pre-planning)

Catalyst (state detector) — Detects FLOW / FRICTION / ADAPT states
  └── Orchestrates BMAD workflows based on detected state

Hephaestus (implementation) — Executes code, runs tests
```

### Layer 3: MCP Layer

**Purpose:** Tool access abstraction. 62+ tools across 11 namespaces.

`brain_mcp` (`nx-brain-mcp`) is the **central unified hub** — single process registering tools from all capability areas. Other MCPs (memory_store, session-pool-mcp, etc.) exist as standalone servers but brain_mcp aggregates their tools.

### Layer 4: Tool Execution

**Purpose:** Actual work — file I/O, network calls, database queries.

- File operations: `read`, `write`, `glob`, `grep`, `lsp_*`
- Network: `fetch_*`, `brain_mcp.tunnel_*`, VPN rotation
- AI inference: GGUF llama-server, cloud APIs
- System: `bash`, `git_*`, health checks

### Layer 5: Infrastructure

**Purpose:** Networking, persistence, compute.

- GGUF inference engine (local GPU)
- Cloud model APIs (OpenRouter, Groq, Google)
- SOCKS5 proxy pool (8 rotating proxies)
- SQLite databases (routing_learning.db, memory, session state)
- File system (`.sisyphus/`, `data/`, `packages/`)

---

## 3. Agent System

### OMO Agent Roles

| Agent | Model | Primary Role | Secondary Role |
|-------|-------|-------------|----------------|
| **Sisyphus** | minimax-m2.5-free | Orchestrator — top-level task routing | Delegate to subagents |
| **Catalyst** | minimax-m2.5-free | State detection (FLOW/FRICTION/ADAPT) | BMAD workflow orchestration |
| **Hephaestus** | minimax-m2.5-free | Implementation — code, tests, builds | Quality gate execution |
| **Oracle** | minimax-m2.5-free | Architecture review | Debugging, hard problems |
| **Explore** | minimax-m2.5-free | Codebase search | Pattern discovery |
| **Librarian** | minimax-m2.5-free | External research | OSS code lookup, docs |
| **Prometheus** | minimax-m2.5-free | Planning | Work breakdown |
| **Metis** | minimax-m2.5-free | Pre-planning | Gap analysis, ambiguities |
| **Momus** | minimax-m2.5-free | Adversarial review | Work plan critique |
| **Atlas** | minimax-m2.5-free | Executor | Task execution |
| **Sisyphus-Junior** | minimax-m2.5-free | Light tasks | Trivial operations |

### Agent Delegation Tree

```
Sisyphus (root orchestrator)
├── Hephaestus
│   ├── Write code
│   ├── Run tests
│   └── Quality gates
├── Oracle
│   ├── Architecture decisions
│   ├── Hard debugging
│   └── Self-review
├── Explore
│   ├── Codebase grep
│   └── Pattern finding
├── Librarian
│   ├── Web search
│   ├── OSS lookup
│   └── Documentation
├── Prometheus → Plan tasks (with Metis gap analysis)
├── Metis → Pre-planning (ambiguity detection)
└── Momus → Adversarial review of plans
```

### Agent Configuration

- **Model selection:** Via `~/.config/opencode/oh-my-opencode.json` (global) or `opencode.json` (project override)
- **Skill injection:** Via `load_skills=["skill-name"]` in task() calls — project skills override builtin
- **Session pinning:** `route_task()` can pin an agent to a session for consistent model selection across multi-turn tasks

---

## 4. MCP Layer

### Central Hub: brain_mcp

**FastMCP server:** `nx-brain-mcp`  
**File:** `packages/brain_mcp/__init__.py`  
**Purpose:** Unified entry point for all N-Xyme capabilities. Dynamically registers 62+ tools across 11 namespaces.

```
namespace loop pattern:
  for namespace in [memory, context, mind, learning, intelligence, session, trigger, catalyst, browser, sqlite, fingerprint, tunnel]:
      _register_namespace_tools(namespace)
```

### MCP Tool Namespaces

| Namespace | Tools | Description |
|-----------|-------|-------------|
| `memory.*` | 6 | Memory search, write, recall, stats |
| `context.*` | 10 | Active/product/user context, BMAD agents/workflows |
| `mind.*` | 8 | MIND state, session history, project manifest |
| `learning.*` | 5 | Task routing, outcome recording, recommendations |
| `intelligence.*` | 4 | Task complexity scoring, available agents |
| `session.*` | 4 | Pool management, session get/return |
| `trigger.*` | 5 | Slash command registration and execution |
| `catalyst.*` | 4 | BMAD workflow orchestration |
| `browser.*` | 6 | Playwright-based browser automation |
| `sqlite.*` | 3 | SQL query against routing database |
| `fingerprint.*` | 10 | Cross-session context injection, user preferences |
| `tunnel.*` | 12 | API key rotation, model selection, chat routing |

### Standalone MCP Servers

| Server | Purpose | In brain_mcp? |
|--------|---------|--------------|
| `unified-memory` (memory_store) | Memory search/write | ✅ Via memory.* |
| `N-Xyme Session Pool` (session-pool-mcp) | Agent session management | ✅ Via session.* |
| `N-Xyme Learning Engine` (learning_engine) | Q-Learning routing | ✅ Via learning.* |
| `N-Xyme Intelligence` (intelligence) | Complexity scoring | ✅ Via intelligence.* |
| `N-Xyme Orchestration` (orchestration) | Spawn, task status | Via spawn.py |
| `N-Xyme Pipeline` (orchestration/mcp_pipeline) | BMAD workflow execution | Via catalyst.* |
| `nx_delegate` | Task delegation | Direct call |
| `N-Xyme Dictate` (dictate) | Speech transcription | Standalone |
| `N-Xyme Catalyst` (catalyst_orchestrator) | State detection | ✅ Via catalyst.* |
| `intelligent-router` (infrastructure/proxy) | Model-level routing | ❌ NOT wired |
| `sqlite` (sqlite-mcp) | SQLite access | ✅ Via sqlite.* |
| `athena-context` | Context injection | Via context.* |
| `playwright` | Browser automation | ✅ Via browser.* |
| `nx-mind` | MIND state | ✅ Via mind.* (deprecated) |
| `trigger-guardian` | Trigger execution | ✅ Via trigger.* |
| `brain_mcp` | Central unified hub | ✅ Central |

### Memory Architecture

```
memory_store (canonical)
  ├── MemoryRouter (semantic search)
  ├── MemoryManager (write/trust/forgetting)
  └── MemoryStore (SQLite persistence)

data/memory/
  ├── episodic.db       — Session events
  ├── semantic.db       — Knowledge base
  ├── procedural.db     — Agent patterns
  └── declarative.db    — Facts/statements
```

---

## 5. Inference Engine

### GGUF Local Inference

**Primary engine:** llama.cpp GGUF server (`llama-server`)  
**Port:** 8080  
**GPU:** NVIDIA RTX 3080 Ti (12GB VRAM)

#### Supported Models

| Model | Size | Purpose | Performance |
|-------|------|---------|-------------|
| `llama3.2:3b` | 2GB | Fast general tasks | 1,341+ tok/s |
| `qwen2.5-coder:7b-q4_k_m` | 4.3GB | Code generation | 471 tok/s |
| `qwen2.5-0.5b-instruct-q4_k_m` | ~350MB | Minimal tasks | ~1,300 tok/s |
| Custom GGUF files | Variable | Experimentation | Per file |

#### Optimization Flags

| Flag | Effect |
|------|--------|
| `-ngl 99` | GPU layer offloading (10-50x speedup) |
| `--flash-attn on` | Flash Attention (1.2-1.5x speedup) |
| `--flash-attn-type 2` | Latest kernel (2025+), +10% |
| `-ctk q4_0 -ctv q4_0` | KV cache quantization (2x context) |
| `-t 16` | Thread tuning |
| `--constrain --logits` | Constrained decoding for tool calling |

#### Health Monitoring

```bash
bash bin/health-monitor.sh      # Auto-recovery on failure
./gguf_manager.sh start/stop    # Service management
./start_llama_server.sh         # Full GPU optimization
```

### Cloud Inference

**Providers:** OpenRouter, Groq, Cerebras, DeepSeek, Google AI Studio, OpenCode Zen

**Routing:** Via `tunnel.*` namespace (brain_mcp) — automatic key rotation, fallback chains, circuit breakers.

**Fallback Chain:**
```
Local GGUF → OpenRouter (free tier) → Groq (fast) → DeepSeek (reasoning)
```

---

## 6. Routing System

See [docs/ROUTER-PRECEDENCE.md](ROUTER-PRECEDENCE.md) for detailed routing documentation.

### Three-Layer Routing Stack

```
Layer 1: Tool Routing     (TwoStageRouter)      → "Which tool?"
Layer 2: Agent Routing    (nx_routing)          → "Which agent?"
Layer 3: Model Routing   (intelligent_router_mcp) → "Which model?"
```

### Key Files

| File | Role |
|------|------|
| `packages/orchestration/two_stage_router.py` | Tool path selection (direct/rosetta_only/full) |
| `packages/nx_routing.py` | Agent routing + Q-Learning (SINGLE SOURCE OF TRUTH) |
| `packages/learning_engine/routing/adaptive_router.py` | Q-Learning feedback loop |
| `packages/intelligence/mcp_server.py` | Complexity scoring MCP tool |
| `packages/intelligence/router/unified.py` | Unified routing facade |

### Q-Learning System

- **Engine:** `QLearningEngine` from `packages/learning_engine/`
- **Persistence:** `data/qlearning/weights.json` (loaded on module init, saved on update)
- **Cold start:** First 50 decisions use heuristic fallback
- **Outcome logging:** `OutcomeLogger` → reward signal → Q-value update
- **Session pinning:** Explicit agent affinity per session

---

## 7. VPN & Proxy Infrastructure

### Proxy Pool

8 SOCKS5 proxies on ports 1080-1087:

| Proxy | Backend | Purpose |
|-------|---------|---------|
| Wireproxy-Proton-1 | WireGuard → ProtonVPN | General routing |
| Wireproxy-Proton-2 | WireGuard → ProtonVPN | Secondary |
| torshammer-1-3 | torshammer | High-volume |
| provider-1-3 | Various VPN providers | Fallback rotation |

### Rotation System

- **Manager:** `packages/infrastructure/vpn_rotation/manager.py`
- **Health check interval:** 300s (configurable via `VPN_HEALTH_INTERVAL`)
- **Auto-rotate:** On health failure, proxy failure, or manual trigger
- **Circuit breaker:** Per-proxy failure tracking, automatic bypass

### Model Router Proxy

Local HTTP proxy on port 8080 that routes requests:
- Path: `/v1/chat/completions`
- Routes based on: task complexity, model capability, proxy health
- Caches: Route decisions (L1 cache, max 200 entries)

---

## 8. Configuration Model

### Configuration Priority (highest to lowest)

1. **Environment variables** (`.env`) — runtime overrides
2. **Project config** (`opencode.json`) — MCP tool overrides
3. **Global agent config** (`~/.config/opencode/oh-my-opencode.json`) — model/param overrides
4. **Global base config** (`~/.config/opencode/opencode.json`) — foundation

### Key Configuration Files

| File | Purpose | Never commit? |
|------|---------|--------------|
| `.env` | Runtime secrets | ✅ NEVER |
| `.env.example` | Template for `.env` | ❌ Commit |
| `opencode.json` | Project MCP config | ❌ Commit |
| `AGENTS.md` | Workspace rules | ❌ Commit |
| `~/.config/opencode/opencode.json` | Global base | ❌ Modify |
| `~/.config/opencode/oh-my-opencode.json` | Global agents | ❌ Modify |
| `env.sh` | Environment sourcing | ❌ Commit secrets |

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `LOCAL_ROUTING_ENABLED` | `true` | Enable local routing |
| `LOCAL_QUALITY_THRESHOLD` | `0.7` | Min quality for local execution |
| `LOCAL_TIMEOUT_SECONDS` | `30` | Local routing timeout |
| `CLOUD_ESCALATION_MODE` | `auto` | When to escalate to cloud |
| `ROUTING_METRICS_ENABLED` | `true` | Emit routing metrics |
| `LOCAL_MODEL_POOL` | `llama3.2:3b,qwen2.5-coder:7b` | Available local models |
| `VPN_ENABLED` | `false` | Enable VPN rotation |
| `VPN_HEALTH_INTERVAL` | `300` | Health check interval (seconds) |
| `VPN_BACKENDS_CONFIG` | `configs/vpn/backends.json` | VPN backend config |

---

## 9. Data Storage

### Directory Structure

```
N-Xyme_MIND/
├── .sisyphus/              # Session state, routing learning DB
│   ├── sessions/          # Session transcripts
│   ├── routing_learning.db # Q-Learning weights
│   └── logs/              # Execution logs
├── data/                  # Persistent data
│   ├── qlearning/        # Q-Learning weights JSON
│   │   └── weights.json   # ← Committed (not secret)
│   ├── models/            # Cached model metadata
│   └── memory/            # Memory databases (episodic, semantic, etc.)
├── packages/              # MCP servers and Python packages
├── nx_engine/            # Frankenengine (GGUF tool calling)
├── athena/               # Athena framework (workflows, skills)
├── frontend/             # Next.js frontend
├── docs/                  # Documentation
├── configs/               # Non-secret configuration
│   └── vpn/              # VPN backend configs
├── bin/                   # Executable scripts
│   ├── health-*.sh        # Health checks
│   ├── env.sh             # Environment sourcing (redirect)
│   ├── quality-gates/    # CI/CD quality gates
│   └── *.sh               # Various utilities
├── _bmad/                 # BMAD agent configs
├── .context/              # Memory bank (activeContext.md, etc.)
└── .env                   # Runtime secrets (NOT committed)
```

### Database Schema (Key Tables)

| Database | Purpose | Key Tables |
|----------|---------|-----------|
| `.sisyphus/routing_learning.db` | Q-Learning routing | q_values, outcomes, routing_history |
| `data/memory/*.db` | Memory store | episodic, semantic, procedural, declarative |
| `opencode.db` | Session history | messages, sessions, agents |

---

## 10. Deployment Topology

### Development (Local)

```
User → OpenCode Desktop → localhost:8080 (GGUF) or localhost:11434 (Ollama)
                         → localhost:1080-1087 (SOCKS5 proxies)
                         → cloud APIs via VPN rotation
```

### Process Topology

| Process | Command | Ports |
|---------|---------|-------|
| OpenCode TUI | `opencode-desktop` | stdio |
| GGUF Server | `llama-server` | 8080 |
| SOCKS5 Proxies | `torshammer` / `wireproxy` | 1080-1087 |
| Model Router | `python3 -m packages.platform_layer.scripts.model.model_router` | 8080 |
| Health Monitor | `bash bin/health-monitor.sh` | — |
| Telegram Bot | `systemctl --user start telegram-bot.service` | — |

### Systemd Services (User-Level)

Located in `~/.config/systemd/user/`:

```
model-router.service      # Model router proxy
telegram-bot.service     # Telegram bot notifications
gguf-llama-server.service # GGUF inference server
health-monitor.service   # Auto-recovery monitoring
wireproxy-proton-*.service # VPN proxies (5 services)
borgmatic.service        # Backup service
web-frontend.service      # Next.js frontend (if deployed)
```

---

## 11. Security Model

### Secrets Management

| Secret | Storage | Access |
|--------|---------|--------|
| API keys | `.env` (runtime only) | Via `os.getenv()` |
| GitHub PAT | `.env` + `git config credential.helper` | Git operations only |
| Telegram bot token | `.env` | Telegram API calls |
| Notion/Obsidian keys | `.env` | Respective integrations |

**Rule:** No secrets in committed files. `.env.example` is the template — fill in real values locally.

### Secret Scanning

- **Pre-commit:** `git diff --staged` → `gitleaks detect --no-color` (S-102)
- **Dependencies:** `pip-audit --format=json` (S-103)
- **CI gate:** `gate-9-deps.sh` blocks commits with known CVEs

### Network Security

- All cloud API calls go through SOCKS5 proxies (VPN rotation)
- Model router proxies requests for telemetry control
- No exposed services on public network (all localhost)

### Hardening Status (Sprint 3)

| Check | Status |
|-------|--------|
| Secrets scan (gitleaks) | ✅ Implemented |
| CVE scanning (pip-audit) | ✅ Implemented |
| Hardcoded path fixes (systemd) | 🔲 Pending (S-501) |
| .env.example sync | 🔲 Pending (S-502) |

---

## Appendix A: Component Inventory

### Python Packages (48+)

| Package | Purpose | Lines |
|---------|---------|-------|
| `brain_mcp/` | Central unified MCP (62+ tools) | ~600 |
| `nx_routing.py` | Agent routing + Q-Learning | ~570 |
| `learning_engine/` | Q-Learning engine, outcome logging | ~800+ |
| `orchestration/` | Spawn, handoff, context loading | ~400+ |
| `intelligence/` | Complexity scoring, routing | ~400+ |
| `platform_layer/` | TUI, dashboard, model scripts | ~800+ |
| `memory_core/` | Memory storage, search, trust | ~500+ |
| `memory_store/` | Memory store wrapper | ~200 |
| `session-pool-mcp/` | Agent session pool | ~300 |
| `intelligent_router_mcp/` | Model-level routing (not wired) | ~2500 |
| `nx_engine/` | GGUF tool calling engine | ~500+ |
| `trigger_guardian_mcp/` | Slash command execution | ~700 |
| `catalyst_orchestrator/` | BMAD workflow execution | ~300 |
| `athena-context-mcp/` | Context injection | ~300 |
| `context_store/` | N-Xyme context | ~300 |
| `playwright-mcp/` | Browser automation | ~200 |
| `sqlite-mcp/` | SQLite access | ~200 |
| `nx_delegate/` | Task delegation | ~200 |
| `dictate/` | Speech transcription | ~200 |
| `infrastructure/proxy/` | Model router proxy | ~300 |

### Scripts (bin/)

| Script | Purpose |
|--------|---------|
| `health-l0-blink.sh` | Pre-flight check (<1s) |
| `health-l1-pulse.sh` | Service health check (<10s) |
| `health-l2-vitals.sh` | Deep integrity check (<60s) |
| `health-monitor.sh` | Auto-recovery monitoring |
| `env.sh` | Environment sourcing (redirect to root) |
| `quality-gates/gate-*.sh` | CI/CD quality gates |
| `start_llama_server.sh` | GGUF server with GPU flags |
| `gguf_manager.sh` | GGUF service management |
| `start_gguf_optimized.sh` | Optimized GGUF startup |

---

## Appendix B: Quality Gates

CI/CD pipeline gates (executed on every commit):

| Gate | Tool | Pass Criteria |
|------|------|---------------|
| 1. Type check | TypeScript check | No errors |
| 2. Lint | ESLint / Ruff | No errors |
| 3. Format | Prettier / Black | No diffs |
| 4. Tests | pytest | All pass |
| 5. Secrets scan | gitleaks | No findings |
| 6. Placeholder check | Custom grep | No TODO/FIXME/HACK |
| 7. Agent call check | Custom | Valid tool calls |
| 8. Security paths | Custom | No forbidden paths |
| 9. Dependencies | pip-audit | No known CVEs |
| 10. SAST | bandit | No high findings |
| 11. Coverage trend | pytest-cov | Not decreasing |

---

## Appendix C: Known Architectural Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| brain_mcp is central hub | Single entry point for 62+ tools | ✅ Implemented |
| nx_routing.py is single source of truth for agent routing | Consolidate 3 competing router implementations | ✅ Implemented |
| Q-Learning weights in data/qlearning/weights.json (committed) | Not secret, enables git history | ✅ Committed |
| Session state in .sisyphus/ (gitignored) | Large, session-specific | ✅ gitignored |
| SOCKS5 proxy pool for VPN rotation | Bypass rate limits across providers | ✅ 8 proxies |
| intelligent_router_mcp not wired | Model-level routing overlaps with tunnel.* | ⚠️ Not wired (S-304) |
| TwoStageRouter L1 cache has no TTL | Performance over freshness for repeated tasks | ⚠️ Known limitation |
| Session pinning is sticky | Consistent model selection for multi-turn tasks | ⚠️ Known limitation |