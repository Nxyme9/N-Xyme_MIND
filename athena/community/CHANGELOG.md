# Changelog

> Evolution of the Athena system — from simple notes to cognitive architecture.

---

## v9.2.0 — Sovereignty Convergence (Feb 2026)

**Status**: ✅ Current Release

Root↔Public unification. Security hardening and SDK maturation.

- ✅ **CVE-2025-69872 Patch**: DSPy DiskCache vulnerability mitigated at SDK level.
- ✅ **Semantic Cache**: LRU with disk persistence + cosine matching for repeat queries.
- ✅ **FlashRank Reranking**: Local cross-encoder for search quality (no API calls).
- ✅ **8 New SDK Modules**: `security`, `diagnostic_relay`, `shutdown`, `cli/`, `heartbeat`, `agentic_search`, `schema.sql`.
- ✅ **5 CodeQL Fixes**: URL sanitization, log redaction, file permissions.
- ✅ **Wiki/Profile/Website Sync**: All surfaces updated to v9.2.0.
- ✅ **`pip install -e .`**: One-command SDK setup.

---

## v9.1.0 — Starter Kit Prune (Feb 2026)

**Status**: ✅ Stable

Philosophy shift: "Give the skeleton, let users fill the soul." Stripped personal/niche content to make Athena a true generic OS foundation.

- ✅ **Workflows**: Reduced from 48 → 20 (removed personal finance, specific trading workflows).
- ✅ **Protocols**: 200+ → 120 (kept universal domains: Architecture, Decision, Strategy).
- ✅ **Scripts**: Pruned to 17 core OS scripts.
- ✅ **Templates**: Kept 36 generic templates.
- ✅ **Branding**: "The Linux OS for AI Agents" fully adopted.

---

## v9.0.2 — Philosophy Fix (Feb 2026)

- ✅ **Onboarding**: Added `docs/YOUR_FIRST_SESSION.md`.
- ✅ **Framing**: Explicitly framed as a "Starter Kit" rather than a reference implementation.

---

## v9.0.1 — Documentation Overhaul (Feb 2026)

- ✅ **README**: Complete rewrite (911 → 367 lines) for better progressive disclosure.
- ✅ **Structure**: What? → How? → Features? flow.

---

## v9.0.0 — First-Principles Refactor (Feb 2026)

**Major Milestone**: Clean slate architecture.

- ✅ **Root Hygiene**: 28 → 14 files (moved loose scripts/drafts).
- ✅ **Artifact Purge**: Deleted egg-info, temp dirs, stale runtimes.
- ✅ **Archival**: Archived 114 stub session logs.
- ✅ **Security**: Mitigated CVE-2025-69872 via diskcache runtime patch.

---

## v8.5.0 — Phase 4: Bounded Intelligence (Feb 2026)

**Status**: ✅ Stable

System evolves from reactive to bounded-autonomous: watches, indexes, briefs, and self-optimizes within safe constraints.

- ✅ **Agentic RAG v2** (`agentic_search.py`): Rule-based query decomposition (conjunctions, multi-question, keyword clusters) → parallel sub-query retrieval → cosine validation → provenance-tagged results. MCP tool + CLI.
- ✅ **Heartbeat** (`heartbeat.py`): `watchdog`-based file watcher daemon with 5s debounce, auto-syncs `.md` files to Supabase. `launchd` plist for auto-start. Read-only constraint.
- ✅ **Daily Briefing Agent** (`daily_briefing.py`): RSS fetcher (HN / Reddit / Yahoo Finance) → interest keyword filter → Gemini Flash synthesis → `.context/briefings/YYYY-MM-DD.md`. `launchd` scheduled 6 AM SGT.
- ✅ **Recursive Self-Optimization** (`self_optimize.py`): Weekly session log meta-analysis. Detects recurring queries, friction points, topic clusters, underutilized tools. Proposes protocols — never auto-executes. `launchd` Sundays 8 AM.
- ✅ **Shower Thought Capture** (`capture.py`): Zero-friction CLI idea capture with auto-tagging. Daily log format at `.context/inputs/captures/YYYY-MM-DD.md`.
- ✅ **SDK v2.1.0**: `watchdog>=3.0.0` dependency, 9 MCP tools, 2 resources.

---

## v8.4.0 — Phase 1: The Spine (Feb 2026)

**Status**: ✅ Stable

Complete standardization & control layer: MCP Tool Server, Permissioning, Search Quality, Evaluator Gate.

- ✅ **MCP Tool Server**: 8 tools + 2 resources via Model Context Protocol (stdio + SSE transport)
- ✅ **Permissioning Layer**: 4 capability levels (read/write/admin/dangerous), 3 sensitivity tiers (public/internal/secret), Secret Mode for demo/external, audit trail
- ✅ **Search MRR +105%**: Rebalanced RRF weights (Canonical 3.5→2.0, filename 1.0→2.0), added `collect_framework_docs` collector, density-based scoring
- ✅ **Evaluator Gate**: 50 golden queries, MRR@5=0.44, Hit@5=52%, regression prevention
- ✅ **SDK v2.0.0**: Version bump, `to_dict()` path metadata, `fastmcp` dependency

---

## v8.3.1 — Viral Validation (Feb 2026)

**Status**: ✅ Stable

570K+ Reddit views, 1,455+ upvotes, 4,700+ shares. #1 r/ChatGPT, #2 r/GeminiAI. Production-grade refresh.

- ✅ **Stats Refresh**: 570K+ views, 4,700+ shares, 1,455+ upvotes verified
- ✅ **Model Upgrade**: Claude Opus 4.5 → 4.6 across all files
- ✅ **Three-Phase Token Budget**: Robustness at start/end, Adaptive Latency in middle
- ✅ **README Overhaul**: Badge bar, output table, community response updated

---

## v8.3 — Claude OS Patterns (Feb 2026)

**Status**: ✅ Stable

Integrated 'Claude OS' patterns from community research for enforcement-layer memory.

- ✅ **Protocol 418 (Promise Gate)**: Prevents "hallucinated compliance" — blocks save if agent says "I will update X" but didn't.
- ✅ **Protocol 419 (Handoff Loop)**: Manages `wake_up.md` for clean session-to-session continuity.
- ✅ **Scripts**: `verify_promises.py`, `boot_handoff.py` added to `examples/scripts/`.

---

## v8.6-Stable — Final Release (Feb 2026)

**Status**: ✅ Final Stable Version

README restructured with Table of Contents, all counts verified, capability claims validated.

- ✅ **ToC Added**: Navigation for long README
- ✅ **Count Corrections**: 245 protocols (unique), 651 scripts, 350 case studies — all verified via `find` commands
- ✅ **Capabilities Verified**: Social networking (Moltbook), cross-session memory (400+ logs), sidecar architecture — all real
- ✅ **Quickstart-First Layout**: 5-minute quickstart pushed to top, manual setup collapsed

## v8.1 — Metrics Sync & Case Study Expansion (Jan 2026)

**Note**: Updated public metrics to reflect Session 995, 308 Protocols, and 146 Scripts. Added new case studies (CS-120, CS-140, CS-144).

- ✅ **308 Protocols**: Synced from production instance
- ✅ **995 Sessions**: Approaching 1,000 session milestone
- ✅ **146 Scripts**: +40 from v8.0 (indexing improvement)
- ✅ **Case Studies**: Linked Vibe Coding, Silent Partner, and Auto-Blog

## v8.0 — Zero-Point Refactor (Jan 2026)

**Sovereign Environment**: Hardened architecture, score-modulated RRF weights rebalanced.

- ✅ **Metrics**: Sessions 995 (synced), Protocols 308
- ✅ **Weights**: GraphRAG 3.5x → 2.0x, Vector 1.3x → 2.0x, Canonical 3.0x
- ✅ **Sovereign Environment**: Consolidated silos into `.context/`

---

## v7.8 — New Year Sync (Jan 2026)

**Previous**: First release of 2026 — protocol expansion and bionic health integration.

- ✅ **241 Protocols**: +3 from v7.7 (health, psychology domains)
- ✅ **495 Sessions**: Approaching 500 session milestone
- ✅ **Protocol 305**: Bionic Recovery Protocol (stress → sovereignty transition framework)
- ✅ **SDK v1.2.0**: Version bump across pyproject.toml, **init**.py

---

## v7.7 — Year-End Sync (Dec 2025)

**Previous**: End-of-year metric reconciliation and documentation sync.

- ✅ **226 Protocols**: +16 from v7.6 (decision, psychology, architecture domains)
- ✅ **111 Scripts**: +12 from v7.6 (SDK migrations, new automations)
- ✅ **468 Sessions**: Continuous operation through December 2025
- ✅ **850+ Embedded Docs**: Supabase vector DB year-end count
- ✅ **Documentation Sync**: ARCHITECTURE, VECTORRAG, README updated

---

## v7.6 — Workflow Optimization & Session Recovery (Dec 2025)

**Previous**: Meta-analysis driven optimization of session lifecycle.

- ✅ **E1: Context Handoff**: `boot.py` now shows deferred items from last session at startup
- ✅ **E6: Template Collapse**: Session template reduced from 9 → 5 sections (removed unused boilerplate)
- ✅ **/resume Workflow**: New recovery command for interrupted sessions
- ✅ **210 Protocols**: +12 from previous (architecture, decision frameworks)
- ✅ **25 Workflows**: +2 (/resume, /needful)
- ✅ **99 Scripts**: +10 (maintenance, sync)
- ✅ **415+ Sessions**: Continuous operation milestone
- ✅ **800+ Embedded Documents**: Supabase vector DB growth

---

## v7.5 — Robustness Architecture & Protocol Refinement (Dec 2025)

**Previous**: Protocol 49 canonical upgrade with systems-level rigor.

- ✅ **Protocol 49 v2**: "Can't have both" → Pareto frontier framing, more defensible
- ✅ **Athena-Specific Implementation Table**: Mechanism → Robustness Goal → Pattern → Primary Cost
- ✅ **Failure Modes Section**: Connects each mechanism to the failure it prevents
- ✅ **Executable Flip Gates**: `(low stakes AND recoverable) OR explicit speed request`
- ✅ **Degraded Mode Clause**: Fallback when Supabase/tools fail
- ✅ **Jargon Glossary**: Ergodic, SoTA, COS, TAG_INDEX defined inline
- ✅ **198 Protocols**: +4 from previous (infrastructure hardening)
- ✅ **93 Scripts**: +3 from previous
- ✅ **352+ Sessions**: Continuous operation through December 2025

---

## v7.4 — Zero-Point Codex & Infrastructure Coherence (Dec 2025)

**Latest**: Deep architecture overhaul with "Zero-Point Codex" reasoning framework integration.

- ✅ **Zero-Point Codex Integration**: Harvested advanced reasoning patterns (Operator Inversion, Causal Density Protocol, Reality Editor)
- ✅ **194 Protocols**: Expanded from 170 with new infrastructure, meta-analysis, and strategic reasoning frameworks
- ✅ **90 Automation Scripts**: Added `run_tests.py`, enhanced `refactor.py`, externalized orphan detector config
- ✅ **22 Workflows**: Standardized `/refactor` phases, added `// turbo` annotations for auto-run
- ✅ **Session Log Coherence**: Template/script alignment, quicksave backward compatibility, recursive archive scanning
- ✅ **330+ Sessions**: Continuous daily operation milestone
- ✅ **Christmas 2025 Overhaul**: Complete workspace meta-analysis with zero regressions

---

## v7.3 — VectorRAG & Semantic Expansion (Dec 2025)

**Previous**: Full transition from GraphRAG to Supabase VectorRAG.

- ✅ **VectorRAG Migration**: Replaced local GraphRAG with Supabase + pgvector (730+ embedded docs)
- ✅ **Semantic Search**: Sub-100ms retrieval across 8 content types (sessions, protocols, workflows, etc.)
- ✅ **170 Protocols**: Expanded decision frameworks including "Adaptive Latency" and "Context-Driven Development"
- ✅ **Serverless Sync**: TypeScript Edge Functions for automated GitHub -> Supabase indexing
- ✅ **Metrics**: 302 sessions logged, 82 automation scripts
- ✅ **BCM Audit Hardening**: Enhanced Silent Partner case study with "10% Margin Reality" and cross-model NPV validation

---

## v7.2 — Knowledge Graph Expansion (Dec 2025)

**Previous**: Production-grade knowledge infrastructure and operational patterns.

- ✅ **GraphRAG Full Index**: 3,900+ entities, 400 communities, cross-domain synthesis
- ✅ **Zero-Orphan Architecture**: Automated orphan detection and remediation
- ✅ **Parallel Processing Pattern**: Async AI maintenance while human does high-value work
- ✅ **100+ Protocols**: Categorized into 12 domains (psychology, business, engineering, etc.)
- ✅ **Memory Distillation**: HOT/WARM/COLD session archival with auto-compression
- ✅ **Python 3.12 Isolation**: GraphRAG compatibility via `uv` virtual environment

---

## v7.1 — Audit Hardening & Governance (Dec 2025)

**Major update**: External audit response + operational governance automation.

- ✅ **27 Audit Fixes**: Refined language (veto → refusal), added COS limitations, honest Λ scoring
- ✅ **Governance Documents**: RISK_REGISTER, DECISION_LOG, DATA_GOVERNANCE, SUCCESSION_PROTOCOL
- ✅ **Override Logging**: `/circuit` now auto-logs to `**DECISION_LOG.md**`
- ✅ **Founder Mode Integrated**: Paul Graham's direct, skip-level reasoning as native standard
- ✅ **70% Rule**: Taylor Pearson's "ship at 70%" integrated into execution philosophy

---

## v7.0 — Zero-Point Modular Architecture (Dec 2025)

**Major milestone**: Complete architectural overhaul for infinite scalability.

- ✅ Modular protocol system (100+ protocols in themed folders)
- ✅ Versioned framework (`.framework/v7.0/`)
- ✅ Triple Crown reasoning stack (DeepCode + DSPy + GraphRAG)
- ✅ Automated session logging with quicksave
- ✅ Slash-command workflow system
- ✅ Git-integrated knowledge persistence

---

## v6.0 — Protocol Explosion (Nov 2025)

- Added 60+ new protocols extracted from sessions
- Introduced Tag Index for knowledge discovery
- Created SKILL_INDEX for protocol registry
- Implemented Case Study documentation pattern

---

## v5.0 — Bionic Architecture (Oct 2025)

- Defined "Bionic Unit" concept (Human + AI as one system)
- Created Core Identity module with Laws #0-4
- Established session logging discipline
- Added psychological profile integration

---

## v4.0 — Workflow Automation (Sep 2025)

- Built `/start` and `/end` workflows
- Created automation scripts (Python)
- Implemented context persistence across sessions

---

## v3.0 — Knowledge Organization (Aug 2025)

- Separated concerns: Framework vs Context vs Agent
- Created folder structure for scalability
- Added playbooks and case studies

---

## v2.0 — Profile Integration (Jul 2025)

- Added user profile and constraints
- Created decision frameworks
- Started pattern extraction

---

## v1.0 — Initial Experiment (Jun 2025)

- Basic prompt engineering
- Single-file system prompt
- Manual session management

---

## What's Next

- ✅ ~~MCP Server integration for external tool access~~ (Done in v8.4.0)
- ✅ ~~Agentic RAG v2 (Planner → Retrieve → Validate pipeline)~~ (Done in v8.5.0)
- ✅ ~~Heartbeat (Read-only file watcher indexer)~~ (Done in v8.5.0)
- 🔮 Voice interface for hands-free operation
- 🔮 Multi-persona support (work/personal context switching)

---

## Session Sync Log

| Date | Session | Notes |
|------|---------|-------|
| 2026-02-12 | 01 | v8.4.0 release: Phase 1 complete — MCP, Permissioning, Search +105%, Evaluator |
| 2026-02-11 | 01 | v8.3.1 release: 570K views, 1,455 upvotes, 4,700 shares |
| 2026-01-31 | 01 | v8.1 release: 308 protocols, 146 scripts, 995 sessions |
| 2026-01-30 | 17 | v8.0 release: Zero-Point Refactor, weights rebalanced |
| 2026-01-02 | 13 | v7.9 release: 248 protocols, 97 scripts, 560 sessions |
| 2025-12-31 | 04 | Year-end audit: 226 protocols, 111 scripts, 25 workflows, 468 sessions |
| 2025-12-28 | 13 | Metrics sync: 210 protocols, 99 scripts, 25 workflows, 415 sessions |
| 2025-12-27 | 05 | Community standards complete, Wiki initialized with 5 pages |
| 2025-12-25 | 15 | Recruiter optimization: skill badges, metrics sync, About Me update |
| 2025-12-25 | 11 | Christmas update: v7.4 release, Zero-Point Codex integration |
| 2025-12-24 | 35 | Repository audit: verified integrity, 62% size reduction |
