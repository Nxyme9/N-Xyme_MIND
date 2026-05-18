# N-Xyme MIND — AGENTS.md (OMO Edition)

**Compact instruction file for OpenCode sessions.**

---

## THE NON-NEGOTIABLES

- **NO `rm` — EVER.** Use `safe_delete` (moves to `data/trash/`, 30-day recovery).
- **READ BEFORE WRITE.** Never edit a file you haven't read this session. Anti-hallucination rules at `data/anti-hallucination-rules.md`.
- **NO invented imports/tools.** Verify everything exists with grep/glob before referencing.
- **7 OMO AGENTS only** — defined in `agents/omo/*.agent.md`. All others disabled.

## ARCHITECTURE

```
Root: /home/nxyme/N-Xyme_CODE/N-Xyme_MIND

agents/omo/      → 7 OMO agent definitions (*.agent.md → compiled MCP servers)
services/        → 4 MCP servers (bash-mcp, megatool-mcp, bmad-mcp, nx_agents)
.opencode/       → 4 plugins, lib modules
config/          → nx_agents.json, megatools_per_agent.json
data/sessions/   → Session transcripts (*.jsonl)
data/memory/     → Memory vectors, synapses, consciousness
```

## THE 7 OMO AGENTS

| Agent | Archetype | Role | Model |
|-------|-----------|------|-------|
| **Catalyst** | Orchestrator | Classifies requests, routes to 6 specialists, verifies | deepseek-v4-flash-free |
| **Hephaestus** | Builder | Complex code, refactoring, quality gates | deepseek-v4-flash-free |
| **Sisyphus Jr** | Quick Writer | Simple edits, config changes, docs, fixes | minimax-m2.5-free |
| **Librarian** | Researcher | Web fetching, docs, OSS code, best practices | deepseek-v4-flash-free |
| **Explorer** | Searcher | Codebase search, patterns, file discovery | minimax-m2.5-free |
| **Momus** | Critic | 5-lens adversarial review | deepseek-v4-flash-free |
| **Metis** | Consultant | Pre-planning, assumptions, risks | deepseek-v4-flash-free |

## DELEGATION RULES

1. **Catalyst is entry point.** All requests route through Catalyst.
2. **One blocking delegate per specialist at a time.**
3. **Verify AFTER delegation** — trust but verify.
4. **Max 3 delegation hops.** Catalyst→Hephaestus→Momus = limit.
5. **Audit EVERY delegation.** `write_memory("delegation:{id}", {from, to, task, status})`.

## ROUTING TREE

```
INCOMING REQUEST
│
└── Catalyst (entry — always first)
    │
    ├── PHASE 0: Adaptive Router (complexity × confidence)
    │   SIMPLE+≥90% → Sisyphus Junior
    │   SIMPLE+70-89% → Sisyphus Junior (verify gate)
    │   COMPLEX+≥70% → Hephaestus
    │   COMPLEX+50-69% → Metis → Hephaestus
    │   RESEARCH → Librarian
    │   SEARCH → Explorer
    │   REVIEW → Momus
    │   PLAN → Metis
    │   UNKNOWN → load bmad-help → reroute
    │   Any+<30% → STOP + user report
    │
    ├── [CODE] → Hephaestus (complex) / Sisyphus Jr (simple)
    ├── [RESEARCH] → Librarian
    ├── [SEARCH] → Explorer
    ├── [REVIEW] → Momus
    ├── [PLAN] → Metis
    └── [UNKNOWN] → bmad-help → classify
```

## AGENT BOUNDARIES

| Agent | NEVER Does |
|-------|-----------|
| **Catalyst** | Write code, execute tools, bash. Classify + route only. |
| **Hephaestus** | Therapy, planning, research. Build + review only. |
| **Sisyphus Jr** | Complex multi-file changes. Simple edits only. |
| **Librarian** | Write code, edit files. Research only. |
| **Explorer** | Modify files. Read-only search. |
| **Momus** | Write code, modify plans. Review only. |
| **Metis** | Write code, execute. Analysis only. |

## AGENT FILES

Each agent is defined in `agents/omo/<name>.agent.md` with:
- YAML frontmatter (identity, model, permissions)
- IDENTITY section (role, boundaries)
- CORE PROTOCOL (phases)
- TOOLS section (available tools)
- SKILLS section (BMAD skills to load)
- DELEGATION templates
- ANTI-HALLUCINATION rules
- QUALITY GATE checklist

## BMAD SKILLS INTEGRATION

| Agent | Skills |
|-------|--------|
| **Catalyst** | adaptive-router, confidence-gate, bmad-help, bmad-catalyst-orchestration, bmad-brainstorming |
| **Hephaestus** | nx-hephaestus-hotload, nx-hephaestus-build, nx-hephaestus-quality-gates, nx-hephaestus-memory, bmad-code-review |
| **Sisyphus Jr** | nx-sisyphus-session-qol |
| **Librarian** | nx-librarian-deepdive, bmad-technical-research, bmad-domain-research |
| **Explorer** | nx-explore-scan |
| **Momus** | nx-momus-audit, bmad-review-adversarial-general, bmad-review-edge-case-hunter, bmad-code-review |
| **Metis** | confidence-gate, bmad-create-architecture, bmad-review-adversarial-general |

## MCP Servers

| Server | Purpose |
|--------|---------|
| `bash-mcp` | Shell execution with delete protection |
| `megatool-mcp` | 55+ NAP tools (file ops, search, config, agents) |
| `bmad-mcp` | 72 BMAD skills (planning, research, testing) |
| `nx_agents` | Rust MCP server (disabled) |

## CONTEXT LIMITS

| Model | Context | Output | Used By |
|-------|---------|--------|---------|
| deepseek-v4-flash-free | 1,048,576 | 384,000 | Catalyst, Hephaestus, Librarian, Momus, Metis |
| minimax-m2.5-free | 204,800 | 65,536 | Sisyphus Jr, Explorer |

## KNOWN ISSUES

- **`task()` drops identity** — use `delegate_task` or `call_omo_agent` instead
- **Non-OMO agent dirs remain on disk** (disabled in config) — agents/archive/ for cleanup
- **Config drift** — opencode.json and nx_agents.json must stay in sync
