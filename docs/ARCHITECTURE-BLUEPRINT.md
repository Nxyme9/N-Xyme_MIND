# N-Xyme_MIND — Architecture Blueprint

> **Version**: 0.1 | **Status**: Sprint 2 Complete | **Next**: Sprint 3
> **Location**: `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/`
> **GitHub**: https://github.com/Nxyme9/N-Xyme_MIND_v0.1

---

## System Overview

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                        N-Xyme_MIND v0.1                                     ║
║              Personal AI Coding Workspace                                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║   ┌─────────────────────────────────────────────────────────────────────┐   ║
║   │                    OPENCODE TUI (Frontend)                          │   ║
║   │                    v1.3.13 | Free Models                            │   ║
║   └───────────────────────────┬─────────────────────────────────────────┘   ║
║                               │                                              ║
║   ┌───────────────────────────▼─────────────────────────────────────────┐   ║
║   │                    OMO PLUGIN v3.14.0                               │   ║
║   │         oh-my-openagent | 52 hooks | hashline_edit                  │   ║
║   └───────────────────────────┬─────────────────────────────────────────┘   ║
║                               │                                              ║
║   ┌───────────────────────────▼─────────────────────────────────────────┐   ║
║   │                    AGENT LAYER (11 Agents)                          │   ║
║   │                                                                     │   ║
║   │   ┌─────────┐  ┌───────────┐  ┌─────────┐  ┌──────────┐          │   ║
║   │   │Sisyphus │  │Hephaestus │  │ Oracle  │  │Prometheus│          │   ║
║   │   │Orchestr.│  │Implement. │  │Arch Rev.│  │ Planning │          │   ║
║   │   └─────────┘  └───────────┘  └─────────┘  └──────────┘          │   ║
║   │                                                                     │   ║
║   │   ┌─────────┐  ┌───────────┐  ┌─────────┐  ┌──────────┐          │   ║
║   │   │  Metis  │  │  Momus    │  │  Atlas  │  │  Explore │          │   ║
║   │   │Gap Anal.│  │Adversary  │  │Executor │  │  Search  │          │   ║
║   │   └─────────┘  └───────────┘  └─────────┘  └──────────┘          │   ║
║   │                                                                     │   ║
║   │   ┌──────────┐  ┌───────────────┐  ┌─────────────────┐            │   ║
║   │   │ Librarian│  │Sisyphus-Junior│  │Multimodal-Looker│            │   ║
║   │   │ Research │  │  Light Tasks  │  │  Vision (Omni)  │            │   ║
║   │   └──────────┘  └───────────────┘  └─────────────────┘            │   ║
║   └───────────────────────────┬─────────────────────────────────────────┘   ║
║                               │                                              ║
║   ┌───────────────────────────▼─────────────────────────────────────────┐   ║
║   │                    MCP LAYER (9 Servers)                            │   ║
║   │                                                                     │   ║
║   │   GLOBAL (6)                    PROJECT (3)                        │   ║
║   │   sequential-thinking           athena (Search+Memory)             │   ║
║   │   memory (Knowledge Graph)      github (GitHub API)                │   ║
║   │   context7 (Live Library)       hindsight (Global Memory)          │   ║
║   │   filesystem (Scoped Access)                                       │   ║
║   │   fetch (HTTP Requests)                                            │   ║
║   │   git (Version Control)                                            │   ║
║   └───────────────────────────┬─────────────────────────────────────────┘   ║
║                               │                                              ║
║   ┌───────────────────────────▼─────────────────────────────────────────┐   ║
║   │                    ENGINE LAYER                                     │   ║
║   │   CATALYST (245 modules) | BMAD (389 flows) | ATHENA (Framework)   │   ║
║   │   176 scripts | 33 rules | 10 quality gates                        │   ║
║   └───────────────────────────┬─────────────────────────────────────────┘   ║
║                               │                                              ║
║   ┌───────────────────────────▼─────────────────────────────────────────┐   ║
║   │                    INFRASTRUCTURE LAYER                             │   ║
║   │   Ollama (Local LLM) | VPN Rotator (9 providers) | Python venv     │   ║
║   │   Node.js v25 | uv v0.11 | ripgrep v15.1                          │   ║
║   └─────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## Agent Delegation Flow

```
                          ┌─────────────┐
                          │   USER      │
                          └──────┬──────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │      SISYPHUS          │
                    │    (Orchestrator)       │
                    │  mimo-v2-pro | high     │
                    └────────────┬───────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                   ▼
    ┌─────────────────┐ ┌───────────────┐ ┌─────────────────┐
    │   HEPHAESTUS    │ │    ORACLE     │ │   PROMETHEUS    │
    │ (Implementation)│ │(Architecture) │ │   (Planning)    │
    └────────┬────────┘ └───────┬───────┘ └────────┬────────┘
             │                  │                   │
             │                  ▼                   │
             │         ┌───────────────┐            │
             │         │    MOMUS      │            │
             │         │ (Adversarial) │            │
             │         └───────────────┘            │
             ▼                                      ▼
    ┌─────────────────┐                   ┌─────────────────┐
    │     ATLAS       │                   │     METIS       │
    │   (Executor)    │                   │  (Gap Analysis) │
    └────────┬────────┘                   └─────────────────┘
             │
    ┌────────┴────────┐
    ▼                 ▼
┌─────────────────┐ ┌─────────────────┐
│    EXPLORE      │ │   LIBRARIAN     │
│ (Codebase Search│ │(External Research│
└─────────────────┘ └─────────────────┘

RULES:
  • Max 2 levels: Sisyphus → Agent → Subagent (STOP)
  • Explore/Librarian: ALWAYS background
  • Review chain: Hephaestus → Oracle → Momus → merge
  • Never mix: same agent cannot write AND review
```

---

## Config Layering

```
Layer 1: GLOBAL (~/.config/opencode/)
  opencode.json          6 MCPs + permissions + model
  oh-my-opencode.json    11 agents + 9 categories
        │
        ▼
Layer 2: PROJECT (./)
  opencode.json          3 project MCPs (overrides)
  oh-my-opencode.json    Minimal (schema + comment)
  AGENTS.md              623 lines workspace rules
        │
        ▼
Layer 3: RUNTIME (./.opencode/) — AUTO-SYNCED
  opencode.json          Copy of project config
  data/                  Session databases

RULE: Global = base. Project = overrides. Runtime = copy.
```

---

## Health Check System

```
L0 BLINK (<1s) — Pre-flight
  ✅ Workspace readable
  ✅ opencode.json exists
  ✅ AGENTS.md exists
  ✅ No hardcoded paths
  ✅ Python venv exists

L1 PULSE (<10s) — Service Check
  ⚠️ Ollama alive (optional)
  ✅ 4 MCP binaries exist
  ✅ Python venv imports work
  ✅ OpenCode binary exists

L2 VITALS (<60s) — Deep Integrity
  ✅ Config JSON valid
  ✅ No broken symlinks
  ✅ Core Python deps intact
  ✅ Disk space >5GB
  ✅ AGENTS.md has task() rules
```

---

## File Structure

```
N-Xyme_MIND/                          9.4GB | 49K files
├── n-xyme-mind.sh                    🚀 Launcher
├── bootstrap.sh                      🔧 Setup (4 distros)
├── env.sh                            🌍 Environment
├── opencode.json                     📋 Config
├── AGENTS.md                         📜 Rules (623 lines)
├── docs/                             📚 Documentation
├── src/                              🐍 CATALYST (245 .py)
├── athena/                           🔍 Python MCP
├── venvs/athena/                     🐍 Venv (1.2GB)
├── vpn/                              🌐 VPN (9 providers)
├── bin/                              🔨 Scripts + gates
├── scripts/                          🤖 176 automation
├── _bmad/                            📋 BMAD (389 flows)
├── .sisyphus/                        🧠 Orchestration
├── context/                          💾 Memory
└── .github/workflows/ci.yml          🔄 CI
```

---

## Agent Model Map

```
TIER 1: ORCHESTRATORS (mimo-v2-pro-free)
  Sisyphus       temp=0.3  reasoning=high
  Hephaestus     temp=0.2  reasoning=medium
  Oracle         temp=0.1  reasoning=xhigh
  Prometheus     temp=0.4  reasoning=high
  Metis          temp=0.2  reasoning=high
  Momus          temp=0.1  reasoning=xhigh
  Atlas          temp=0.2  reasoning=medium

TIER 2: SPEED (minimax-m2.5-free)
  Explore        temp=0.1  reasoning=low
  Librarian      temp=0.3  reasoning=low
  Sisyphus-Junior temp=0.2 reasoning=low

TIER 3: VISION (mimo-v2-omni-free)
  Multimodal-Looker temp=0.2 reasoning=medium
```

---

## Sprint Roadmap

```
✅ SPRINT 1 — DEPLOYMENT (Complete)
  47,288 files deployed | 4 MCPs | 11 agents | GitHub

✅ SPRINT 2 — HARDENING (Complete)
  PAT secured | Pre-commit | Venv 5.6→1.2GB | CI | bootstrap 4 distros

🔄 SPRINT 3 — COMPLETENESS (Next)
  Fix venv | Ollama models | Tests | Prune stubs | BMAD integration | Docs

📋 SPRINT 4 — INTEGRATION (Planned)
  CATALYST modules | VPN configs | Trigger engine | BMAD workflows

🚀 SPRINT 5 — FEATURES (Future)
  Custom MCPs | Memory consolidation | Multi-machine sync
```

---

## Quick Reference

| What | Command |
|------|---------|
| Launch | `bash n-xyme-mind.sh` |
| Health | `bash bin/health-l0-blink.sh` |
| Bootstrap | `bash bootstrap.sh` |
| Gates | `bash bin/quality-gates/gate-all.sh` |
| Push | `git add -A && git commit && git push` |

---

*Generated by N-Xyme_MIND. 30+ agents. 47,288 files. Zero hardcoded paths.*
