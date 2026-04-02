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
