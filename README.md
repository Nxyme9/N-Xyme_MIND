# N-Xyme_MIND

Personal AI coding workspace powered by OpenCode + OMO multi-agent orchestration.

## Quick Start

```bash
cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
source env.sh
bash n-xyme-mind.sh
```

## Architecture

- **Frontend**: OpenCode TUI (v1.3.13)
- **Agent Layer**: OMO v3.14.0 (11 agents, 9 categories)
- **MCP Layer**: 4 global MCPs (sequential-thinking, memory, context7, filesystem)
- **Engine**: CATALYST (234 Python modules) + athena framework
- **VPN**: rotator.py with 9 provider plugins

## Agents

| Agent | Model | Role |
|-------|-------|------|
| Sisyphus | mimo-v2-pro-free | Orchestrator |
| Hephaestus | mimo-v2-pro-free | Implementation |
| Oracle | mimo-v2-pro-free | Architecture review |
| Explore | minimax-m2.5-free | Codebase search |
| Librarian | minimax-m2.5-free | External research |

## Configuration

- Global: `~/.config/opencode/` (base config)
- Project: `./opencode.json` (MCP overrides)
- Agents: `~/.config/opencode/oh-my-opencode.json` (agent definitions)
- Workspace: `./AGENTS.md` (workspace rules)

## Health Checks

```bash
bash bin/health-l0-blink.sh  # <1s pre-flight
bash bin/health-l1-pulse.sh  # <10s service check
bash bin/health-l2-vitals.sh # <60s deep integrity
```

## Bootstrap (Fresh Machine)

```bash
bash bootstrap.sh
```

## Sprint 2 — Security & Performance Hardening

### Security
- GitHub PAT removed from remote URL (was exposed)
- Pre-commit hook installed for secret scanning
- `.env.example` template created

### Configuration
- OMO config deduplicated (global is source of truth)
- Project `oh-my-opencode.json` is now minimal override only

### Performance
- athena venv slimmed: 5.6GB → 1.2GB (removed unused nvidia/torch/triton)
- Health checks: L0 7ms, L1 41ms, L2 216ms

### Cleanup
- Empty `src/agent/` and `src/agents/` directories removed
- Rules index created (33 rules organized by category)

### Portability
- `bootstrap.sh` now supports Arch/Debian/Fedora/RHEL
- All shebangs portable (`#!/usr/bin/env bash/python3`)

## 🚀 Complete LLM Routing System

### Features
- **Smart Routing**: Classifies tasks → routes to optimal provider
- **IP Rotation**: 8 SOCKS5 proxies bypass rate limits
- **Local Models**: llama3.2:3b + qwen2.5-coder:7b for fast local inference
- **Memory Learning**: Stores routing outcomes → improves over time
- **Auto-Recovery**: Health monitor restarts failed services automatically

### Quick Start
```bash
# Start all services
systemctl --user start model-router.service

# Verify health
bash bin/health-monitor.sh

# Launch TUI Dashboard
PYTHONPATH=. python3 -m src.tui.ultimate_dashboard

# Open OpenCode Desktop (routes through proxy automatically)
opencode-desktop
```

### System Status
- **Model Router**: ✅ Running on localhost:8080
- **SOCKS5 Proxies**: ✅ 8 running (ports 1080-1087)
- **Local Models**: ✅ llama3.2:3b, qwen2.5-coder:7b
- **Tests**: ✅ 79/79 passing
- **Health Monitor**: ✅ Active with auto-recovery

### Documentation
- [Complete System Guide](docs/complete-system-guide.md)
- [Model Router Documentation](docs/model-router.md)
- [Migration Guide](MIGRATION.md)
