---
type: system-knowledge
status: active
date: 2026-04-09
tags: [system, mind, architecture, golden-spine]
related: [[N-XYME_MIND_Evolution], [N-XYME_CATALYST_System]]
rating: 10
---

# N-XYME MIND GOLDEN SPINE v1

## 8-Folder Contract Structure

| Folder | Purpose |
|--------|---------|
| 00_launch | Bootstrap entry point |
| 00_spine | Isolated spine config (no router/provider deps) |
| 01_core | Orchestration, routing, lifecycle, state |
| 02_cortex | LLM targets, registries, GPU/CPU/hybrid |
| 03_contracts | Stable schemas, interfaces, protocols |
| 04_config | Configuration files |
| 05_tools | Automation helpers |
| 06_runs | Runtime artifacts |
| 07_clients | CLI, apps, pipelines |
| 08_docs | Architecture, decisions, audits |

## Core Components (01_core)

| File | Role |
|------|------|
| orchestrator.py | Main orchestration engine |
| router.py | Task routing logic |
| plugin_runner.py | Plugin execution |
| memory_index.py | Memory indexing |
| retrieval.py | Content retrieval |
| decision_ledger.py | Decision tracking |
| strategy_snapshot.py | Strategy snapshots |
| cortex_pack.py | Cortex bundle packaging |
| eval_harness.py | Evaluation harness |

## Tools (05_tools)

| Tool | Function |
|------|----------|
| nxm_doctor.py | Health diagnostics |
| nxm_learn.py | Pattern scanning |
| nxm_query.py | Index rebuild/queries |
| nxm_pack.py | Cortex pack creation |
| nxm_run.py | Runtime execution |
| nxm_llama_server.ps1 | Local llama-server |
| nxm-route-win.ps1 | Windows routing |

## Audit Status: PASS (Sprints 1-7)
- 01_core/: PASS
- 02_cortex/: PASS
- 03_contracts/: PASS
- 04_config/: PASS
- 05_tools/: PASS
- 06_runs/: PASS
- 08_docs/: PASS
- _snapshots/: PASS

## Bootstrap Rules (CODEX.md)
- ENGINE_Live assumptions
- SSB + AM + SL state authority check before routing
- Fallback: scaffolding only, verify state, emit STATUS BLOCK

---

*Source: `/mnt/WIN_LIBRARY/_NXYME_ARCHIVE/1_N-Xyme M.I.N.D/`*
