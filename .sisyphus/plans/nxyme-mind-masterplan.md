# N-Xyme_MIND — COMPLETE MASTERPLAN

> 30+ agents across 5 source systems synthesized this plan.
> Every moving part documented. Every dependency mapped. Every step specified.
> Target: `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/`

---

## EXECUTIVE SUMMARY

Build a fully standalone, portable AI workspace called **N-Xyme_MIND** that:
- Uses OpenCode TUI as frontend
- Has OMO (oh-my-openagent v3.14.0) for multi-agent orchestration
- Has BMAD v6.2.0 for agile workflows
- Has 6 MCPs installed (sequential-thinking, memory, context7, filesystem, fetch, athena-protocol)
- Has athena-Public as Python MCP for memory/search/sessions
- Has GitHub MCP server for GitHub API
- Has a VPN rotator for rate limit mitigation
- Has a self-healing architecture
- Has OWASP LLM security
- Is fully portable (copy folder + bootstrap.sh = works on any machine)

---

## PHASE 0: CURRENT STATE AUDIT (What's Already Working)

### Verified Working Right Now
| Component | Version | Location | Status |
|-----------|---------|----------|--------|
| OpenCode | 1.3.13 | ~/.opencode/bin/opencode | RUNNING |
| OMO | v3.14.0 | ~/.config/opencode/node_modules/@opencode-ai/ | RUNNING |
| Node.js | v25.8.2 | npx/npm | RUNNING |
| Ollama | latest | localhost:11434 | RUNNING |
| Config | - | ~/.config/opencode/opencode.json | VALID |
| oh-my-opencode.json | - | ~/.config/opencode/oh-my-opencode.json | VALID |

### MCPs Installed (6 total)
| MCP | Package | Status |
|-----|---------|--------|
| sequential-thinking | @modelcontextprotocol/server-sequential-thinking | CACHED |
| memory | @modelcontextprotocol/server-memory | CACHED |
| context7 | @upstash/context7-mcp@latest | CACHED |
| filesystem | mcp-server-filesystem | CACHED |
| fetch | mcp-server-fetch-typescript | CACHED |
| athena-protocol | n0zer0d4y/athena-protocol (built) | BUILT |

### External Drives (Mapped)
| Drive | Mount Point | Content |
|-------|------------|--------|
| Library (5.5TB) | /run/media/nxyme/Library/ | nx_openmore, recovered/MIND |
| NXYME_CORE (894GB) | /mnt/NXYME_CORE/ | 01_CODING (CATALYST), 99_Depricated |
| NVMe root (1TB) | / | CachyOS, Ollama, OpenCode |

### External Drive Assets (Verified from 30+ agents)
```
/run/media/nxyme/Library/
├── nx_openmore/
│   ├── athena/                    # Python MCP server (winstonkoh87/Athena-Public)
│   ├── bin/
│   │   ├── rotator.py             # VPN rotator (863 lines)
│   │   ├── opencode-vpn           # VPN orchestrator (2133 lines)
│   │   ├── vpnsocks               # VPN command wrapper
│   │   ├── github-mcp-server      # Static Go binary
│   │   ├── providers/             # 8 VPN provider plugins
│   │   ├── repair-paths.sh        # Path fixer
│   │   ├── health-check.sh        # Health checker
│   │   └── quality-gates/         # CI gates
│   ├── config/opencode.json       # Source config (8 MCPs)
│   ├── AGENTS.md                  # 609 lines orchestration rules
│   ├── .sisyphus/                 # Rules, plans, handoffs
│   └── .claude/agents/            # explore.md, sisyphus.md
│
├── recovered/home-nxyme/N-Xyme_MIND/
│   ├── _bmad/                     # BMAD v6.2.0 (full framework)
│   ├── triggers.json              # Nervous system (538 lines)
│   ├── agent_identities.json      # Agent registry
│   ├── user-preferences.json      # ADHD priorities
│   ├── AGENTS.md                  # 10K chars, AI opinion system
│   ├── MASTERPLAN.md              # 18K chars, full blueprint
│   ├── MASTER_SYSTEM.md           # System architecture doc
│   ├── Makefile                   # Service management
│   ├── scripts/                   # 176 automation scripts
│   ├── .sisyphus/rules/           # 33 specialized rules
│   ├── .sisyphus/plans/           # 136 detailed plans
│   └── configs/vpn/               # VPN country mappings
│
/mnt/NXYME_CORE/01_CODING/00_N-Xyme_CATALYST/
│   ├── src/
│   │   ├── self_healer.py         # Autonomous healing (356 lines)
│   │   ├── anomaly_detection.py   # Z-score detection (332 lines)
│   │   ├── circuit_breaker.py     # CLOSED/OPEN/HALF_OPEN (140 lines)
│   │   ├── security_llm.py        # OWASP LLM Top 10 (1128 lines)
│   │   ├── a2a_agents.py          # Agent-to-Agent protocol (221 lines)
│   │   ├── react_agent.py         # ReAct reasoning (871 lines)
│   │   ├── reflexion_agent.py     # Self-improvement (1037 lines)
│   │   ├── model_router.py        # Model routing (287 lines)
│   │   ├── verification_engine.py # 3-layer verification (196 lines)
│   │   ├── focus_manager.py       # ADHD productivity (1206 lines)
│   │   ├── grounding.py           # Hallucination prevention (465 lines)
│   │   ├── audit_logger.py        # Audit trail (153 lines)
│   │   ├── event_bus.py           # Pub/sub (90 lines)
│   │   └── ... (100+ more modules)
│   ├── packages/
│   │   ├── security-agent/        # Command validation service
│   │   ├── code-health/           # A-F health dashboard
│   │   ├── session-manager/       # Session CRUD + handoffs
│   │   ├── agent-framework/       # Agent coordination
│   │   └── graphiti-memory/       # Graph memory system
│   ├── .heartbeat/                # 3-layer health monitoring
│   ├── configs/opencode/          # 26 agent YAML definitions
│   └── scripts/                   # Automation scripts
│
/mnt/NXYME_CORE/99_Depricated/
├── 00_N-Xyme_CODE/
│   ├── .opencode/agents/          # 8 YAML agent definitions
│   ├── .opencode/commands/        # 81 BMAD command files
│   └── .opencode/oh-my-opencode.json  # Config with mimo-v2-flash-free
└── NX_opencode/
    └── opencode/oh-my-opencode.json   # Additional config
```

---

## PHASE 1: DIRECTORY SKELETON (Create Structure)

### Create at `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/`

```bash
# Root structure
mkdir -p /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/
cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/

# Documentation
mkdir -p docs/schematics

# Core modules (from CATALYST)
mkdir -p src/agents
mkdir -p src/resilience
mkdir -p src/security
mkdir -p src/memory/brain
mkdir -p src/adhd
mkdir -p src/infrastructure
mkdir -p src/capture

# MCP servers
mkdir -p mcp/athena-protocol
mkdir -p mcp/code-health
mkdir -p mcp/session-manager

# Athena (Python)
mkdir -p athena/src/athena/core
mkdir -p athena/src/athena/memory
mkdir -p athena/src/athena/tools
mkdir -p athena/.context

# Jarvis
mkdir -p jarvis-new

# Python venvs
mkdir -p venvs/athena
mkdir -p venvs/jarvis

# Memory/persistence
mkdir -p context/memory
mkdir -p context/opencode
mkdir -p context/semantic

# Orchestration
mkdir -p .sisyphus/rules
mkdir -p .sisyphus/plans
mkdir -p .sisyphus/notepads
mkdir -p .sisyphus/handoffs

# BMAD
mkdir -p _bmad

# Automation scripts
mkdir -p scripts

# Model routing
mkdir -p modelrouter

# VPN system
mkdir -p vpn/providers/protonvpn/configs
mkdir -p vpn/providers/wireguard/configs
mkdir -p vpn/providers/mullvad/configs
mkdir -p vpn/providers/nordvpn/configs
mkdir -p vpn/providers/surfshark/configs
mkdir -p vpn/providers/oracle/configs
mkdir -p vpn/providers/azirevpn/configs
mkdir -p vpn/providers/windscribe/configs

# Binaries and scripts
mkdir -p bin/quality-gates

# OpenCode runtime
mkdir -p .opencode/data/sessions
mkdir -p .opencode/state
mkdir -p .opencode/cache

# Ollama models
mkdir -p .ollama/models

# GitHub CI
mkdir -p .github/workflows

# Tests
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p tests/smoke
mkdir -p tests/chaos

# Agent skills
mkdir -p .agents/skills

# Logs
mkdir -p logs

# Cache
mkdir -p .cache/npm
mkdir -p .cache/bun
mkdir -p .cache/uv
```

---

## PHASE 2: COPY ASSETS FROM EXTERNAL DRIVES

### 2.1 Copy from nx_openmore

```bash
SRC=/run/media/nxyme/Library/nx_openmore
DST=/home/nxyme/N-Xyme_CODE/N-Xyme_MIND

# Athena Python MCP server
cp -r $SRC/athena/* $DST/athena/

# VPN system
cp $SRC/bin/rotator.py $DST/vpn/
cp $SRC/bin/opencode-vpn $DST/vpn/
cp $SRC/bin/vpnsocks $DST/vpn/
cp -r $SRC/bin/providers/* $DST/vpn/providers/
chmod +x $DST/vpn/opencode-vpn $DST/vpn/vpnsocks

# GitHub MCP server
cp $SRC/bin/github-mcp-server $DST/bin/
chmod +x $DST/bin/github-mcp-server

# Utility scripts
cp $SRC/bin/repair-paths.sh $DST/bin/
cp $SRC/bin/health-check.sh $DST/bin/
cp -r $SRC/bin/quality-gates/* $DST/bin/quality-gates/
chmod +x $DST/bin/*.sh $DST/bin/quality-gates/*.sh

# AGENTS.md (609-line version)
cp $SRC/AGENTS.md $DST/

# Sisyphus orchestration
cp -r $SRC/.sisyphus/* $DST/.sisyphus/

# Claude agents
cp -r $SRC/.claude $DST/

# Git config
cp $SRC/.gitignore $DST/

# Source config (authoritative MCP definitions)
cp $SRC/config/opencode.json $DST/opencode.json.bak
```

### 2.2 Copy from recovered N-Xyme_MIND

```bash
SRC=/run/media/nxyme/Library/recovered/home-nxyme/N-Xyme_MIND
DST=/home/nxyme/N-Xyme_CODE/N-Xyme_MIND

# BMAD framework
cp -r $SRC/_bmad/* $DST/_bmad/

# Nervous system
cp $SRC/triggers.json $DST/
cp $SRC/agent_identities.json $DST/
cp $SRC/user-preferences.json $DST/

# Documentation
cp $SRC/MASTERPLAN.md $DST/docs/
cp $SRC/MASTER_SYSTEM.md $DST/docs/

# Service management
cp $SRC/Makefile $DST/

# Handoff
cp $SRC/HANDOFF.md $DST/docs/
cp $SRC/MEMORY_CONSOLIDATION.md $DST/docs/

# Scripts (176)
cp -r $SRC/scripts/* $DST/scripts/

# Sisyphus rules (merge — don't overwrite existing)
for f in $SRC/.sisyphus/rules/*.md; do
  [ -f "$f" ] && cp -n "$f" "$DST/.sisyphus/rules/"
done

# Plans
cp -r $SRC/.sisyphus/plans/* $DST/.sisyphus/plans/ 2>/dev/null || true

# VPN country mappings
cp -r $SRC/configs/vpn/* $DST/vpn/ 2>/dev/null || true
```

### 2.3 Copy from CATALYST

```bash
SRC=/mnt/NXYME_CORE/01_CODING/00_N-Xyme_CATALYST
DST=/home/nxyme/N-Xyme_CODE/N-Xyme_MIND

# Core Python modules
cp $SRC/src/self_healer.py $DST/src/resilience/
cp $SRC/src/anomaly_detection.py $DST/src/resilience/
cp $SRC/src/circuit_breaker.py $DST/src/resilience/
cp $SRC/src/verification_engine.py $DST/src/resilience/
cp $SRC/src/rate_limiter.py $DST/src/resilience/
cp $SRC/src/retry_handler.py $DST/src/resilience/
cp $SRC/src/error_handler.py $DST/src/resilience/

cp $SRC/src/security_llm.py $DST/src/security/
cp $SRC/src/audit_logger.py $DST/src/security/
cp $SRC/src/grounding.py $DST/src/security/

cp $SRC/src/a2a_agents.py $DST/src/agents/
cp $SRC/src/react_agent.py $DST/src/agents/
cp $SRC/src/reflexion_agent.py $DST/src/agents/
cp $SRC/src/model_router.py $DST/src/agents/
cp $SRC/src/intent_orchestration.py $DST/src/agents/
cp $SRC/src/agent_coordinator.py $DST/src/agents/
cp $SRC/src/tool_registry.py $DST/src/agents/
cp $SRC/src/permission_manager.py $DST/src/agents/
cp $SRC/src/thinking_effort.py $DST/src/agents/
cp $SRC/src/personality.py $DST/src/agents/
cp $SRC/src/context_injector.py $DST/src/agents/
cp $SRC/src/round_cap_enforcer.py $DST/src/agents/

cp $SRC/src/focus_manager.py $DST/src/adhd/
cp $SRC/src/quick_capture.py $DST/src/adhd/

cp $SRC/src/config_manager.py $DST/src/infrastructure/
cp $SRC/src/service_registry.py $DST/src/infrastructure/
cp $SRC/src/event_bus.py $DST/src/infrastructure/
cp $SRC/src/module_registry.py $DST/src/infrastructure/
cp $SRC/src/catalyst_orchestrator.py $DST/src/infrastructure/

cp $SRC/src/voice_capture.py $DST/src/capture/
cp $SRC/src/clipboard_monitor.py $DST/src/capture/
cp $SRC/src/screen_capture.py $DST/src/capture/
cp $SRC/src/capture_publisher.py $DST/src/capture/

cp $SRC/src/graphiti_memory.py $DST/src/memory/
cp $SRC/src/unified_memory.py $DST/src/memory/
cp $SRC/src/session_archiver.py $DST/src/memory/
cp $SRC/src/knowledge_graph.py $DST/src/memory/
cp $SRC/src/drift_detector.py $DST/src/memory/

# __init__.py files (create if missing)
for dir in src/agents src/resilience src/security src/memory src/memory/brain src/adhd src/infrastructure src/capture; do
  [ ! -f "$DST/$dir/__init__.py" ] && touch "$DST/$dir/__init__.py"
done

# Agent framework package
cp -r $SRC/packages/agent-framework/src/* $DST/src/agents/ 2>/dev/null || true

# Security agent
cp -r $SRC/packages/security-agent $DST/mcp/

# MCP servers from CATALYST
cp -r $SRC/packages/code-health $DST/mcp/
cp -r $SRC/packages/session-manager $DST/mcp/

# Agent definitions (26 YAML files)
mkdir -p $DST/agents
cp -r $SRC/configs/opencode/agents/* $DST/agents/ 2>/dev/null || true

# Agent registry (if exists)
[ -f $SRC/hephaestus/agent_registry.py ] && cp $SRC/hephaestus/agent_registry.py $DST/src/agents/

# Heartbeat system (convert to bash later)
mkdir -p $DST/bin/heartbeat
```

### 2.4 Copy from 99_Depricated

```bash
SRC=/mnt/NXYME_CORE/99_Depricated/00_N-Xyme_CODE
DST=/home/nxyme/N-Xyme_CODE/N-Xyme_MIND

# 81 BMAD commands
mkdir -p $DST/commands
cp -r $SRC/.opencode/commands/* $DST/commands/

# 8 agent YAML definitions
cp -r $SRC/.opencode/agents/* $DST/agents/

# oh-my-opencode config
cp $SRC/.opencode/oh-my-opencode.json $DST/oh-my-opencode-reference.json
```

### 2.5 Symlink opencode runtime

```bash
DST=/home/nxyme/N-Xyme_CODE/N-Xyme_MIND

# Symlink opencode binary (don't copy — stays in ~/.opencode/bin/)
ln -sf ~/.opencode/bin/opencode $DST/bin/opencode
```

---

## PHASE 3: FIX ALL HARDCODED PATHS

### 3.1 Python code (CRITICAL — crashes on other machines)

| File | Line | Broken | Fix |
|------|------|--------|-----|
| `athena/src/athena/core/health.py` | 53,60 | `/home/nxyme/nx_openmore/athena/.agent/chroma_db` | `Path(__file__).parent.parent.parent / ".agent" / "chroma_db"` |
| `athena/src/athena/memory/local_vectors.py` | 15 | Same | Same |
| `athena/athena.yaml` | 84 | `/home/nxyme/nx_openmore/context/` | `./context/` |
| `athena/src/athena/core/security.py` | 398 | `import dspy` | Comment out — dspy not installed |

### 3.2 Config files

| File | What | Fix |
|------|------|-----|
| `context/session-config/session-config.json` | `/home/nxyme/nx_openmore/` hardcoded | Relative paths |

### 3.3 Shebangs (ALL Python scripts)

```bash
find $DST -name "*.py" -exec sed -i '1s|#!/usr/bin/env python3.*|#!/usr/bin/env python3|' {} \;
find $DST -name "*.py" -exec sed -i '1s|#!/usr/bin/python3|#!/usr/bin/env python3|' {} \;
find $DST -name "*.py" -exec sed -i '1s|#!/usr/bin/python|#!/usr/bin/env python3|' {} \;
```

### 3.4 Run enhanced repair-paths.sh

```bash
cd $DST
./bin/repair-paths.sh
```

---

## PHASE 4: WRITE UNIFIED CONFIG

### 4.1 opencode.json (SINGLE CANONICAL)

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "opencode/mimo-v2-pro-free",
  "small_model": "opencode/minimax-m2.5-free",
  "plugin": ["oh-my-openagent@latest"],
  "mcp": {
    "sequential-thinking": {
      "type": "local",
      "command": ["npx", "-y", "@modelcontextprotocol/server-sequential-thinking"],
      "enabled": true,
      "timeout": 30000
    },
    "memory": {
      "type": "local",
      "command": ["npx", "-y", "@modelcontextprotocol/server-memory"],
      "enabled": true,
      "timeout": 15000
    },
    "context7": {
      "type": "local",
      "command": ["npx", "-y", "@upstash/context7-mcp@latest"],
      "enabled": true,
      "timeout": 30000
    },
    "filesystem": {
      "type": "local",
      "command": ["npx", "-y", "mcp-server-filesystem", "."],
      "enabled": true,
      "timeout": 15000
    },
    "fetch": {
      "type": "local",
      "command": ["npx", "-y", "mcp-server-fetch-typescript"],
      "enabled": true,
      "timeout": 15000
    },
    "athena-protocol": {
      "type": "local",
      "command": ["node", "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/mcp/athena-protocol/dist/index.js"],
      "environment": {
        "DEFAULT_LLM_PROVIDER": "ollama",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_MODEL_DEFAULT": "qwen2.5:14b"
      },
      "enabled": true,
      "timeout": 120000
    },
    "athena": {
      "type": "local",
      "command": ["./venvs/athena/bin/python", "-m", "athena.mcp_server"],
      "environment": {
        "PYTHONPATH": "./athena/src",
        "EMBEDDING_PROVIDER": "ollama"
      },
      "enabled": true,
      "timeout": 30000
    },
    "github": {
      "type": "local",
      "command": ["./bin/github-mcp-server", "stdio", "--toolsets", "all"],
      "environment": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
      },
      "enabled": true,
      "timeout": 30000
    },
    "hindsight": {
      "type": "local",
      "command": ["./venvs/athena/bin/python", "./hindsight_mcp.py"],
      "environment": {
        "HINDSIGHT_API_LLM_PROVIDER": "ollama",
        "HINDSIGHT_API_LLM_MODEL": "qwen2.5:14b",
        "HINDSIGHT_API_LLM_BASE_URL": "http://localhost:11434/v1",
        "HINDSIGHT_API_LLM_API_KEY": "ollama",
        "HINDSIGHT_API_LAZY_RERANKER": "1",
        "HINDSIGHT_API_SKIP_LLM_VERIFICATION": "1"
      },
      "enabled": true,
      "timeout": 30000
    }
  },
  "enabled_providers": ["opencode", "openrouter", "groq", "cerebras", "deepseek", "ollama"],
  "provider": {
    "opencode": {},
    "openrouter": {
      "options": { "apiKey": "${OPENROUTER_API_KEY}", "timeout": 60000 }
    },
    "groq": {
      "options": { "apiKey": "${GROQ_API_KEY}", "timeout": 30000 }
    },
    "cerebras": {
      "options": { "apiKey": "${CEREBRAS_API_KEY}", "timeout": 30000 }
    },
    "deepseek": {
      "options": { "apiKey": "${DEEPSEEK_API_KEY}", "timeout": 60000 }
    },
    "ollama": {
      "options": { "baseURL": "http://localhost:11434/v1", "timeout": 60000 }
    }
  },
  "permission": {
    "external_directory": "allow",
    "read": {
      "*.env": "deny",
      "*.env.*": "deny",
      "*.env.example": "allow",
      "*.key": "deny",
      "*.pem": "deny",
      "*": "allow"
    },
    "edit": {
      "*.env": "deny",
      "*.env.*": "deny"
    },
    "bash": {
      "*": "ask"
    }
  }
}
```

### 4.2 oh-my-opencode.json (Merged from both sources)

Merge the 11 agents from current config with the 11 agents from recovered MIND and the 8 agent YAMLs from N-Xyme_CODE. Final roster: 16 agents.

### 4.3 .env.example

```
# GitHub
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# OpenCode
OPENCODE_API_KEY=sk-xxxxxxxxxxxxxxxx

# OpenRouter
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxx

# Groq
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx

# Cerebras
CEREBRAS_API_KEY=csk-xxxxxxxxxxxxxxxx

# DeepSeek
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx

# Ollama (local, no key needed)
OLLAMA_API_KEY=ollama
```

---

## PHASE 5: INSTALL PYTHON ENVIRONMENTS

### 5.1 Create athena venv

```bash
cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND

# Check if uv is available
which uv || curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv
uv venv venvs/athena --python python3

# Install athena dependencies
uv pip install -e "athena[full]" --python venvs/athena/bin/python

# Install hindsight dependencies
uv pip install hindsight-api sentence-transformers --python venvs/athena/bin/python

# Fix shebangs
find venvs/athena -name "*.py" -exec sed -i '1s|#!.*python.*|#!/usr/bin/env python3|' {} \;
find venvs/athena/bin -type f -exec sed -i 's|#!.*python.*|#!/usr/bin/env python3|' {} \;
```

### 5.2 Create jarvis venv

```bash
# Only if jarvis is needed
uv venv venvs/jarvis --python python3
# Install jarvis deps later when ported to Linux
```

### 5.3 Copy hindsight_mcp.py

```bash
cp /run/media/nxyme/Library/nx_openmore/hindsight_mcp.py $DST/
cp -r /run/media/nxyme/Library/nx_openmore/hindsight_mcp $DST/
```

---

## PHASE 6: INSTALL OLLAMA MODELS

```bash
# Verify Ollama is running
curl -sf http://localhost:11434/api/tags || sudo systemctl start ollama

# Pull required models
ollama pull nomic-embed-text       # Embeddings for athena
ollama pull qwen2.5:14b            # LLM for hindsight + athena-protocol
ollama pull qwen2.5:3b             # Lightweight fallback

# Verify
ollama list
```

---

## PHASE 7: SETUP VPN ROTATOR

### 7.1 Install WireGuard tools

```bash
sudo pacman -S wireguard-tools  # or sudo apt install wireguard-tools
```

### 7.2 Download WireGuard configs

```bash
# ProtonVPN — download from https://protonvpn.com/account/wireguard
# Place .conf files in:
#   vpn/providers/protonvpn/configs/
#   vpn/providers/wireguard/configs/

# Each .conf should look like:
# [Interface]
# PrivateKey = ...
# Address = ...
# DNS = ...
# [Peer]
# PublicKey = ...
# Endpoint = ...
# AllowedIPs = 0.0.0.0/0, ::/0
```

### 7.3 Create provider configs

```bash
# Mullvad
echo '{"account_number":"YOUR_NUMBER"}' > vpn/providers/mullvad/config.json

# NordVPN
echo '{"username":"YOUR_USER","password":"YOUR_PASS"}' > vpn/providers/nordvpn/config.json

# Surfshark
echo '{"username":"YOUR_USER","password":"YOUR_PASS"}' > vpn/providers/surfshark/config.json
```

### 7.4 Test VPN

```bash
cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/vpn
./opencode-vpn --health
./opencode-vpn --start
```

---

## PHASE 8: CREATE LAUNCHER

### 8.1 `n-xyme-mind.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source environment
source "$ROOT/env.sh"

# Pre-flight check
if ! bash "$ROOT/bin/health-l0-blink.sh" 2>/dev/null; then
  echo "Health check failed. Run: bootstrap.sh"
  exit 1
fi

# Sync canonical config
cp "$ROOT/opencode.json" "$ROOT/.opencode/opencode.json"

# Launch
cd "$ROOT"
exec "$ROOT/bin/opencode" "$@"
```

### 8.2 `env.sh`

```bash
#!/usr/bin/env bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Python venv
export VIRTUAL_ENV="$ROOT/venvs/athena"
export PATH="$VIRTUAL_ENV/bin:$PATH"
export PYTHONPATH="$ROOT/athena/src"

# Ollama
export OLLAMA_MODELS="$ROOT/.ollama/models"

# MCP packages
export npm_config_cache="$ROOT/.cache/npm"
export BUN_CACHE_DIR="$ROOT/.cache/bun"
export UV_CACHE_DIR="$ROOT/.cache/uv"

# VPN proxy (if running)
# export HTTP_PROXY=http://127.0.0.1:18080
# export HTTPS_PROXY=http://127.0.0.1:18080

# Load API keys
[ -f "$ROOT/.env" ] && set -a && source "$ROOT/.env" && set +a
```

### 8.3 Health checks (tiered)

```bash
# bin/health-l0-blink.sh (<1s)
# - workspace readable?
# - opencode.json valid?
# - .env exists?
# - venv exists?

# bin/health-l1-pulse.sh (<10s)
# - Ollama running?
# - MCP packages importable?
# - disk >1GB?

# bin/health-l2-vitals.sh (<60s)
# - config drift?
# - broken symlinks?
# - Python deps intact?
```

---

## PHASE 9: GIT SETUP

```bash
cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND

git init
git add .
git commit -m "Initial N-Xyme_MIND scaffold"
```

### .gitignore (comprehensive)

```
# Secrets
.env
*.key
*.pem

# Python
__pycache__/
*.pyc
.venv/
venvs/

# Node
node_modules/
.cache/

# OpenCode
.opencode/data/
.opencode/cache/
.opencode/state/

# Ollama
.ollama/models/

# Logs
logs/

# VPN configs (sensitive)
vpn/providers/*/configs/*.conf
vpn/providers/*/config.json

# OS
.DS_Store
Thumbs.db
```

---

## PHASE 10: WRITE DOCUMENTATION

### docs/ARCHITECTURE.md
System overview, component diagram, data flow, startup sequence, failure modes.

### docs/MCP_REGISTRY.md
All 10 MCP servers with transport, runtime, timeout, tools exposed, dependencies.

### docs/AGENT_REGISTRY.md
All 16 agents with role, model, permissions, delegation chain.

### docs/DEPENDENCY_MAP.md
System deps (node, python, uv, ollama), Python deps, Node deps, Ollama models.

### docs/PORT_REGISTRY.md
OpenCode TUI, Ollama (11434), VPN proxy (18080), Graphiti (8001).

### docs/SECURITY.md
OWASP LLM Top 10 coverage, permission model, secret management.

### docs/SELF_HEALING.md
Health tiers, auto-repair, circuit breakers, anomaly detection.

### docs/VPN_ROTATION.md
Provider setup, proxy flow, 429 detection, rate limiting.

### docs/BOOTSTRAP.md
First-run guide for any machine.

### docs/TROUBLESHOOTING.md
Common issues, their causes, their fixes.

### docs/CHANGELOG.md
Version history.

---

## PHASE 11: CREATE BOOTSTRAP.SH

Complete bootstrap script that on ANY fresh Linux:
1. Detects OS (Arch/Debian/Fedora)
2. Installs node, bun, uv, ollama, wireguard-tools
3. Installs OMO
4. Installs all npx MCPs
5. Clones + builds athena-protocol
6. Pulls Ollama models
7. Creates Python venvs + installs deps
8. Fixes all shebangs
9. Fixes all hardcoded paths
10. Syncs configs
11. Creates all required directories
12. Runs health check
13. Reports success

---

## PHASE 12: FINAL VERIFICATION

```bash
cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND

# Health check
bash bin/health-l0-blink.sh
bash bin/health-l1-pulse.sh

# OpenCode starts
./n-xyme-mind.sh

# MCPs connect (check TUI status)
# All 10 should show "connected"

# Ollama responds
curl -sf http://localhost:11434/api/tags

# Python athena works
./venvs/athena/bin/python -m athena.mcp_server

# GitHub MCP works
./bin/github-mcp-server stdio --toolsets all

# VPN works (if configs set)
./vpn/opencode-vpn --health
```

---

## EXECUTION TIMELINE

| Phase | Time | Description |
|-------|------|-------------|
| 0 | 5 min | Audit current state |
| 1 | 5 min | Create directory skeleton |
| 2 | 10 min | Copy assets from external drives |
| 3 | 10 min | Fix hardcoded paths + shebangs |
| 4 | 15 min | Write unified config (opencode.json + oh-my-opencode.json) |
| 5 | 15 min | Install Python venvs + deps |
| 6 | 5 min | Pull Ollama models |
| 7 | 10 min | Setup VPN rotator |
| 8 | 10 min | Create launcher + health checks |
| 9 | 5 min | Git setup |
| 10 | 15 min | Write documentation |
| 11 | 15 min | Create bootstrap.sh |
| 12 | 10 min | Final verification |
| **TOTAL** | **~2.5 hours** | |

---

## WHAT THIS GIVES YOU

- **10 MCP servers** (all local stdio, zero network dependency for transport)
- **16 agents** (Sisyphus + 15 specialists with fallback chains)
- **81 BMAD commands** (full agile workflow library)
- **OWASP LLM security** (prompt injection, data redaction, output sanitization)
- **Self-healing** (anomaly detection, circuit breakers, auto-repair)
- **VPN rotation** (8 providers, 429 auto-recovery, rate limiting)
- **ADHD features** (focus modes, priority system, visual emblems)
- **176 automation scripts** (from recovered MIND)
- **Portable** (copy folder + bootstrap.sh = works anywhere)
- **One command**: `n-xyme-mind`

---

*Plan generated from 30+ agent investigations across 5 source systems.*
*Total research time: ~3 hours across 60+ tool calls.*
