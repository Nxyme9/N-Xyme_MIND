# Execution Tracker — N-Xyme_MIND

**Generated:** 2026-05-17  
**Revision:** 2026-05-17 v2 — Archive findings incorporated from Librarian  
**Generator:** Masterplan (Atlas-class)  
**Sources:** `data/sessions/state.json`, `data/bmad/architecture.md`, `data/bmad/stories/*.md`, `.opencode/plugins/*.js`, filesystem audit, archive inventory (`archive/data_chaos/`)

**Key Discovery:** Many components previously marked "Missing" / "Not built" actually **EXIST** in the archive at `archive/data_chaos/data_chaos/`. The C++ inference engine, Python training pipeline (42 generations), structured training data (5,900+ examples + 47K transcripts), 43-module intelligence package, reference architecture, and golden test sets are all present. The task has shifted from **build-from-scratch** to **extraction + consolidation + Rust porting**. See Section 12 for full Archive Inventory.

---

## 1. ACTIVE RALPH LOOPS

### 1.1 `ralph_metaobserver` — Active 🟢

| Field | Value |
|-------|-------|
| **Session ID** | `ralph_metaobserver` |
| **Loop ID** | `l1778982458230573147` |
| **Task** | Build meta-observer: 64-dim signal classifier + hardcoded rules + online training loop |
| **Promise** | `MetaObserver_BUILT_AND_TESTED` |
| **Iteration** | **1 / 50** (2%) |
| **Active** | ✅ **YES** |
| **Last Output** | *"Picking up meta-observer build. 100 ideas collected. Need: 1) 64-dim signal classifier in Rust minilm 2) Adaptive circuit breaker plugin 3) Online training loop from failures."* |

**Status:** Early stage — iteration 1/50. Just started building. The meta-observer plugin file does NOT exist yet in `.opencode/plugins/`.

### 1.2 `ses_1cdb97ea4ffeX5Qx1hyYxX9Iaa` (l_integrate_v1) — Active 🟢

| Field | Value |
|-------|-------|
| **Session ID** | `ses_1cdb97ea4ffeX5Qx1hyYxX9Iaa` |
| **Loop ID** | `l_integrate_v1` |
| **Task** | INTEGRATE ALL COMPONENTS: Connect daemon.mojo → engine.mojo → Rosetta bridge. daemon gets load/embed/generate message types. Low-confidence TF-IDF falls back to Rosetta embedding. Full three-tier routing working end to end. |
| **Promise** | `ALL_INTEGRATED` |
| **Iteration** | **0 / 20** (0%) |
| **Active** | ✅ **YES** |

**Status:** Brand new — no iterations executed yet. Fresh session created at 1778974971.

### 1.3 `ralph_rosetta_final` — Stalled 🟡

| Field | Value |
|-------|-------|
| **Session ID** | `ralph_rosetta_final` |
| **Loop ID** | `l1778967946788351933` |
| **Task** | Retrain Rosetta with 25 tools + wire into MCP ask() as tier 3 |
| **Promise** | `ROSETTA_TRAINED_AND_WIRED` |
| **Iteration** | **0 / 10** |
| **Active** | ❌ **NO** (never started) |

**Status:** Never executed. Replaced by higher-priority meta-observer work.

### 1.4 `ralph_rosetta` — Stalled 🟡

| Field | Value |
|-------|-------|
| **Session ID** | `ralph_rosetta` |
| **Loop ID** | `l1778964639187211966` |
| **Iteration** | **3 / 15** |
| **Active** | ❌ **NO** |
| **Last Output** | *"Mojo v1 persistent daemon wired. Cold: 38ms. Hot: 88-204μs. All three tiers: Rust(11μs) Mojo(88μs) LLM(seconds). Promise 2/3 done."* |

**Status:** 2/3 promise done. Replaced by `ralph_rosetta_final`.

### 1.5 `ralph_mojo` — Stalled 🟡

| Field | Value |
|-------|-------|
| **Session ID** | `ralph_mojo` |
| **Loop ID** | `l1778962424381916198` |
| **Iteration** | **2 / 20** |
| **Active** | ❌ **NO** |

**Status:** Mojo router deliverable ✅ DONE. Should be closed.

---

## 2. PENDING DELEGATIONS

### 2.1 Auth Middleware — 3 Duplicate Delegations 🟡 (EXISTS as Python ref)

| Session | Task | To | File | Call Count | Status |
|---------|------|----|------|-----------|--------|
| `hephaestus` | implement auth middleware | hephaestus | `src/auth.rs` | 10 | 🟡 **EXISTS IN ARCHIVE** |
| `hephaestus_auth` | implement auth middleware | (self) | `src/auth.rs` | 0 | 🟡 **EXISTS IN ARCHIVE** |
| `test` | implement auth middleware | hephaestus | `src/auth.rs` | 6 | 🟡 **EXISTS IN ARCHIVE** |

**⚠️ ARCHIVE REALITY:** Reference implementation EXISTS at `archive/.../packages/intelligence/permission_engine.py` (213 lines). 43-module intelligence package provides full auth/API patterns in Python. Task is **Rust port of existing reference**, not build-from-scratch. Still needs `src/` directory creation.

### 2.2 Mojo Router Delegation — Complete (Not Updated) 🟢

| Session | Task | To | File | Status |
|---------|------|----|------|--------|
| `hephaestus_mcp` | build Mojo tool router | hephaestus | `services/mojo-router/` | 🟢 **DONE** — not marked in state.json |

**✅ REALITY:** Mojo router is fully implemented and compiled (23 .mojo files).

### 2.3 Rosetta Training Data 🟢 (EXISTS in archive)

| Session | Task | To | File | Status |
|---------|------|----|------|--------|
| `hephaestus_rosetta` | Generate 250 training pairs | hephaestus | `training/mojo_rosetta.jsonl` | 🟢 **ARCHIVE HAS ALL DATA** |

**✅ ARCHIVE REALITY:** Archive has **5,900+ structured training examples** (nx_trainer/data/*.jsonl) + **47K session transcripts** + golden test sets: `training/test.jsonl` (73 examples) + `training/by-category/chat/test.jsonl` (516 examples). Task is **extraction + curation**, not generation. The `rosetta_v8_complete_train.jsonl` (1,000+ pairs) already exists in archive.

### 2.4 Rosetta Engine Wiring 🟡 (EXISTS — compiled binary)

| Session | Task | To | File | Status |
|---------|------|----|------|--------|
| `hephaestus_ros` | wire Rosetta GGUF to nx_engine | hephaestus | `engine/` + `services/` | 🟡 **COMPILED BINARY EXISTS** |

**✅ ARCHIVE REALITY:** Compiled C++ binary EXISTS at `archive/.../src/engine/build/frankenstein-engine`. Engine source: 502 lines CUDA-capable C++ (`engine.cpp`). 107–127 t/s inference speed. Task is: **extract binary to `engine/` directory + build HTTP API wrapper**. No rebuild needed.

### 2.5 API Route 🟡 (Patterns exist in archive)

| Session | Task | To | File | Status |
|---------|------|----|------|--------|
| `hephaestus_api` | build API route | (self) | `src/api.rs` | 🟡 **REFERENCE PATHS EXIST** |

**⚠️ ARCHIVE REALITY:** Reference API patterns exist in archive's 43-module intelligence package (Python). `packages/intelligence/router/` has Rust/PyO3 compiled output showing routing architecture. Still needs Rust port, but design patterns are established.

---

## 3. ARCHITECTURE DECISIONS STATUS

### AD-1: Meta-Observer Plugin ❌ NOT BUILT

| Aspect | Status | Details |
|--------|--------|---------|
| Plugin file | ❌ **NOT CREATED** | No `meta-observer.js` in `.opencode/plugins/` |
| 64-dim signal classifier | ❌ **NOT BUILT** | |
| 3 hooks (execute.before, messages.transform, session.created) | ❌ **NOT BUILT** | |
| Training loop integration | ❌ **NOT BUILT** | |
| Ralph loop active | 🟡 **IN PROGRESS** | Iteration 1/50 on `ralph_metaobserver` |

**Fix:** Continue `ralph_metaobserver` loop. Create `meta-observer.js` plugin with classifier + hooks.

### AD-2: Ralph Loop Auto-Continuation ❌ BROKEN

| Aspect | Status | Details |
|--------|--------|---------|
| Plugin exists | ✅ `ralph-autoloop.js` (115 lines) | |
| Completion detection BEFORE increment | ❌ **WRONG ORDER** | Lines 31-38: `increment` happens first (`loop.it = (loop.it \|\| 0) + 1`), THEN check promise |
| OMO pattern followed | ❌ **NO** | Should: detect completion → if done clear → increment → promptAsync |
| File frontmatter state storage | ❌ **NOT IMPLEMENTED** | Uses state.json instead of `.sisyphus/ralph-loop.local.md` |
| `session.deleted` handler | ❌ **MISSING** | |
| `session.error` handler | ❌ **MISSING** | |

**Fix:** Reorder: detect promise → check completion FIRST → then increment. Add missing handlers.

### AD-3: Plugin Architecture ❌ NOT IMPLEMENTED

| Aspect | Status | Details |
|--------|--------|---------|
| Target: 3 plugins max | ❌ 5 plugins | ralph-autoloop.js, llm-pitfalls.js, auto-memory.js, nx-session-loop-bridge.js, no-code-sisyphus.js |
| llm-pitfalls.js merged into meta-observer | ❌ **NOT MERGED** | |
| auto-memory.js merged into meta-observer | ❌ **NOT MERGED** | |
| nx-session-loop-bridge.js assessed | ❌ **NOT ASSESSED** | |

**Fix:** Merge `auto-memory.js` and `llm-pitfalls.js` into `meta-observer.js`. Assess `nx-session-loop-bridge.js`.

### AD-4: MiniLM GGUF Weights ❌ NOT LOADED

| Aspect | Status | Details |
|--------|--------|---------|
| MiniLM Rust engine | ✅ COMPILED (1411 lines) | |
| Random weights | ❌ GARBAGE OUTPUT | Weights not loaded from GGUF |
| GGUF alignment bug | ❌ **UNFIXED** | `data_start` offset calculation wrong |
| ONNX model (86.6 MB) | ✅ EXISTS | Graph constants hard to extract |
| GGUF model (20 MB) | ✅ EXISTS | Q4_K_M quantized, 101 tensors |
| `services/minilm/src/weights.rs` | ❌ **BUG NOT FIXED** | |

**Fix:** Fix alignment padding calculation in `weights.rs`. After parsing tensor info, pad to next `alignment` boundary.

### AD-5: Online Training Loop ❌ NOT BUILT

| Aspect | Status | Details |
|--------|--------|---------|
| Classification outcome logging | ❌ **NOT BUILT** | |
| Correction-triggered retrain | ❌ **NOT BUILT** | |
| Mini-batch weight update (every 100 corrections) | ❌ **NOT BUILT** | |
| Meta-observer integration | ❌ **NOT BUILT** | Depends on AD-1 |

**Fix:** Implement after AD-1 meta-observer is built.

### AD-6: Model Routing by Task Type ❌ NOT BUILT

| Aspect | Status | Details |
|--------|--------|---------|
| Task-type detection | ❌ **NOT BUILT** | |
| Model recommendation per task | ❌ **NOT BUILT** | |
| Performance tracking per model | ❌ **NOT BUILT** | |
| Meta-observer .messages.transform hook | ❌ **NOT BUILT** | Depends on AD-1 |

**Fix:** Implement in meta-observer's `messages.transform` hook after AD-1.

### AD-7: Data Pipeline Integration ⚠️ PARTIAL — Archive Has Training Data

| Path | Status | Archive Equivalent |
|------|--------|--------------------|
| `data/sessions/` | ✅ EXISTS — agent-named sessions | — |
| `data/audit/` | ✅ EXISTS — tool call audit trail | — |
| `data/memory/vectors/ingest.jsonl` | ✅ EXISTS | — |
| `data/memory/synapses/` | ❌ **NOT CREATED** | — |
| `data/learning/` | ❌ **NOT CREATED** | — |
| `data/training/` | ❌ **NOT CREATED** | ✅ **EXISTS** at `archive/.../training/` (test/train/val splits, by-category) |
| `training/` | ❌ **NOT CREATED** | ✅ **EXISTS** at `archive/.../nx_trainer/data/` (42 generations of training data, 5,900+ examples) |
| `training/transcripts/` | ❌ **NOT CREATED** | ✅ **EXISTS** at `archive/.../training/transcripts/` (47K session transcripts) |

**Revised Status:** 5/8 paths missing locally but 3 of those have archive equivalents. Extraction task, not creation.

### AD-8: Session Issues — 85% Unfixed

| Issue | Status | Fix |
|-------|--------|-----|
| Ralph Loop auto-continue broken | ❌ | AD-2: OMO pattern fix |
| Meta-observer not built | ❌ | AD-1: Single plugin |
| BMAD workflows interrupt building | ⚠️ | AD-3: Planning artifacts at boundaries |
| No-code enforcement inconsistent | ⚠️ | AD-3: Plugin enabled + delegate gate |
| Plugin accumulation (7→5 files) | ⚠️ | AD-3: Consolidate to 3 |
| MiniLM GGUF weights not loading | ❌ | AD-4: Fix alignment calc |
| Session transcripts in `unknown/` | ✅ **FIXED** | |
| LLM pitfalls plugin too rigid | ⚠️ | AD-1: Adaptive circuit breaker |
| MCP error handlers fragile | ⚠️ | Needs testing |
| Mojo daemon has no ML capability | ❌ | LLama.cpp FFI (archived) |
| Model routing doesn't exist | ❌ | AD-6: Task type routing |
| Online training loop doesn't exist | ❌ | AD-5: Every 100 corrections → retrain |

**Pass/Fail:** 1/12 fixed ✅ | 11/12 unfixed ❌/⚠️

---

## 4. MOMUS/METIS FINDINGS

*Note: Dedicated review artifact not located. Findings derived from architecture gap analysis and story-code comparison.*

### Critical Issues (7)

| # | Finding | Status | Context |
|---|---------|--------|---------|
| C1 | **Stories describe already-built features** | 🟡 **CONFIRMED** | Stories 1.1 (daemon), 1.2 (TF-IDF), 1.3 (error handling) all describe existing code. Marked "ready-for-dev" but already implemented. |
| C2 | **No meta-observer exists despite 100 ideas** | 🔴 **OPEN** | AD-1 defines it. Ralph loop at iteration 1/50. |
| C3 | **Ralph loop order is wrong** | 🔴 **OPEN** | AD-2: increment before detect vs OMO pattern. |
| C4 | **GGUF alignment bug blocks real weights** | 🔴 **OPEN** | AD-4: engine uses random weights. No semantic output. |
| C5 | **No feedback/training loop** | 🔴 **OPEN** | AD-5: system doesn't learn from corrections. |
| C6 | **No task-type model routing** | 🔴 **OPEN** | AD-6: each task uses the same model regardless of fit. |
| C7 | **5 plugins instead of 3** | 🟡 **OPEN** | AD-3: accumulation without consolidation. |

### High Issues (19)

| # | Finding | Status | Area |
|---|---------|--------|------|
| H1 | `src/` directory missing — auth scaffolding blocked | 🟡 | Infrastructure — but auth ref EXISTS in archive at `packages/intelligence/permission_engine.py` (213 lines). Rust port needed. |
| H2 | `training/` directory missing — Rosetta training blocked | 🟡 | Infrastructure — all training data EXISTS in archive at `nx_trainer/data/` (5,900+ examples, 47K transcripts). Extraction task. |
| H3 | `engine/` directory missing — GGUF wiring blocked | 🟡 | Infrastructure — compiled C++ engine binary EXISTS at `src/engine/build/frankenstein-engine`. Extraction + API wrapper needed. |
| H4 | `src/api.rs` target doesn't exist | 🟡 | Infrastructure — API patterns exist in 43-module intelligence package. Rust port from Python ref. |
| H5 | 3 duplicate auth delegations in state.json | 🟡 | Session hygiene |
| H6 | 15+ stale test sessions polluting state | 🟡 | Session hygiene |
| H7 | `ralph_mojo` should be closed | 🟡 | Loop cleanup |
| H8 | `ralph_rosetta` should be closed | 🟡 | Loop cleanup |
| H9 | `hephaestus_mcp` delegation not marked done | 🟡 | State accuracy |
| H10 | `nx-session-loop-bridge.js` may be redundant | 🟡 | Plugin audit |
| H11 | Mojo version may have changed (0.26.2 → 1.0.0b1) | 🟡 | Compatibility |
| H12 | No daemon watchdog/auto-restart | 🟡 | Reliability |
| H13 | Session log mining not started | 🟡 | Analytics — 47K session transcripts exist in archive at `training/transcripts/`. Mining pre-primed. |
| H14 | No auto-digest generation | 🔴 | Continuity |
| H15 | Mojo daemon has no ML capability | 🟡 | Capability gap — compiled C++ CUDA engine EXISTS in archive (107-127 t/s). Can be wired via FFI/extraction rather than built from scratch. |
| H16 | LLM pitfalls plugin too rigid | 🟡 | AD-1 integration |
| H17 | MCP error handlers fragile | 🟡 | Needs testing |
| H18 | BMAD workflows interrupt building | 🟡 | AD-3 pattern |
| H19 | Session transcripts still in `unknown/` directory pattern | ⚠️ | Partially fixed |

**Pass/Fail:** 0/7 critical fixed | 5/19 high mitigated by archive findings (H1→🟡, H2→🟡, H3→🟡, H4→🟡, H13→🟡, H15→🟡)

---

## 5. REMAINING WORK — 5 UNBUILT + 4 EXTRACTION ITEMS

### 5.1 Build Items (Genuinely Need Creation)

| Item | AD | Build Status | Blocked By | Effort Est | Priority |
|------|----|-------------|-----------|------------|----------|
| **Meta-Observer Plugin** | AD-1 | ❌ NOT BUILT (in progress: loop 1/50) | — | 2-3h | 🔴 **P0** |
| **Ralph Loop OMO Fix** | AD-2 | ❌ BROKEN (wrong order) | — | 30min | 🔴 **P0** |
| **GGUF Weight Loading** | AD-4 | ❌ UNFIXED (alignment bug) | — | 1-2h | 🔴 **P1** |
| **Online Training Loop** | AD-5 | ❌ NOT BUILT | AD-1 (meta-observer) | 3-4h | 🟡 **P2** |
| **Model Task Routing** | AD-6 | ❌ NOT BUILT | AD-1 (meta-observer hook) | 2-3h | 🟡 **P2** |

**Pass/Fail:** 0/5 built ✅ | 5/5 not built ❌ (unchanged — these are genuinely new)

### 5.2 Extraction Items (Exist in Archive, Need Deployment)

| Item | Archive Path | Local Target | Extraction Effort | Rust Port? | Priority |
|------|-------------|--------------|-------------------|------------|----------|
| **C++ Inference Engine** | `archive/.../src/engine/engine.cpp` (502 lines, compiled binary) | `engine/frankenstein-engine` | 1h | No — C++ binary + HTTP wrapper | 🔴 **P0** |
| **Training Pipeline v42** | `archive/.../nx_trainer/train_v42.py` + 41 prior versions | `training/nx_trainer/` | 1h | No — Python training pipeline | 🔴 **P1** |
| **Golden Test Data** | `archive/.../training/test.jsonl` (73) + `by-category/chat/test.jsonl` (516) + by-category train/val splits | `data/training/golden/` | 30min | No — JSONL curation | 🟡 **P2** |
| **Auth/API Reference** | `archive/.../packages/intelligence/permission_engine.py` (213 lines), 43-module package | `src/auth.rs` + `src/api.rs` | 2-3h | ✅ **Yes — Rust port needed** | 🟡 **P2** |

**Extraction Pass/Fail:** 0/4 extracted ✅ | 4/4 in archive ❌ (not yet deployed)

---

## 6. CURRENT STORIES STATUS

### Story 1.1: Daemon Startup & Lifecycle ❌ REWRITE NEEDED

| Criteria | Verdict | Evidence |
|----------|---------|----------|
| Status in story | `ready-for-dev` | |
| Reality | ✅ **ALREADY BUILT** | `services/mojo-router/src/daemon.mojo` exists, compiled binary at `services/mojo-router/src/daemon` |
| Momus/Metis finding | ❌ **Describes existing feature** | Tasks like "Implement daemon startup" are already done |
| Verdict | 🔴 **Story should be marked COMPLETE or rewritten as documentation** | |

### Story 1.2: TF-IDF Routing Engine ❌ REWRITE NEEDED

| Criteria | Verdict | Evidence |
|----------|---------|----------|
| Status in story | `ready-for-dev` | |
| Reality | ✅ **ALREADY BUILT** | TF-IDF scoring in `services/mojo-router/src/main.mojo`, rust MCP integration, router tested at 88μs |
| Momus/Metis finding | ❌ **Describes existing feature** | All ACs are met by existing code |
| Verdict | 🔴 **Story should be marked COMPLETE or rewritten** | |

### Story 1.3: Error Handling & Graceful Degradation ❌ REWRITE NEEDED

| Criteria | Verdict | Evidence |
|----------|---------|----------|
| Status in story | `ready-for-dev` | |
| Reality | ⚠️ **PARTIALLY EXISTS** | `safe_run()` pattern exists in main.rs via `catch_unwind`, but testing incomplete |
| Momus/Metis finding | ❌ **Mostly describes existing feature** | Core error handling exists, edge case testing needed |
| Verdict | 🟡 **Rewrite as test/story for remaining edge cases** | |

### Story 1.4: Performance Metrics & Logging ⚠️ PARTIALLY BUILT

| Criteria | Verdict | Evidence |
|----------|---------|----------|
| Status in story | `ready-for-dev` | |
| Reality | ⚠️ **PARTIALLY EXISTS** | Routing logs exist in audit log; dedicated metrics endpoint NOT built |
| Momus/Metis finding | ⚠️ **Mixed — some exists, some doesn't** | Logging exists, p50/p95/p99 metrics endpoint, confidence degradation warning missing |
| Verdict | 🟡 **Partial rewrite + implement missing ACs** | |

**Pass/Fail:** 3/4 stories need major rewrite | 1/4 needs partial rewrite

---

## 7. OVERALL PASS/FAIL CHECKLIST

### Deliverable Checklist

| Deliverable | Criteria | Pass/Fail | Archive Note |
|------------|----------|-----------|-------------|
| Mojo TF-IDF Router | Sub-ms, 25 tools, compiled | ✅ **PASS** | — |
| Rust MCP Server | Session mgmt, audit, multi-mode | ✅ **PASS** | — |
| Meta-Observer Plugin | 3 hooks, 64-dim classifier, learning | ❌ **FAIL** (in progress) | Truly needs build |
| Ralph Loop OMO Fix | Detect before increment, 4 handlers | ❌ **FAIL** (wrong order) | Truly needs fix |
| Plugin Consolidation | Max 3 plugins | ❌ **FAIL** (5 plugins) | Design decision |
| GGUF Weight Loading | Real all-MiniLM-L6-v2 output | ❌ **FAIL** (random weights) | Truly needs fix |
| Online Training Loop | Corrections → retrain cycle | ❌ **FAIL** | Truly needs build (but training pipeline EXISTS) |
| Model Task Routing | Per-task model recommendation | ❌ **FAIL** | Truly needs build |
| Data Pipeline | Learning/, training/, synapses/ dirs | ⚠️ **PARTIAL** | Training data EXISTS in archive |
| Rosetta Training Data | 250 pairs, valid JSONL | ⚠️ **MITIGATED** | 5,900+ examples + rosetta_v8 complete + golden tests in archive |
| Auth Middleware | `src/auth.rs`, tests pass | ⚠️ **MITIGATED** | Python reference EXISTS (213 lines) — Rust port needed |
| API Route | `src/api.rs`, 200 OK | ⚠️ **MITIGATED** | Reference patterns exist in 43-module intelligence package |

**Pass/Fail (strict):** 2/12 ✅ PASS | 6/12 ❌ FAIL (truly missing) | 4/12 ⚠️ MITIGATED (exists in archive)  
**Previously:** 10/12 ❌ FAIL 🔜 Now **6/12 truly fail** — the "83% gap" is actually **50% gap** with extraction

### Infrastructure Checklist

| Item | Status | Archive Equivalent |
|------|--------|--------------------|
| `services/mojo-router/` (23 .mojo files) | ✅ EXISTS | — |
| `services/nx-agents-mcp/` (1723-line Rust) | ✅ EXISTS | — |
| `.opencode/plugins/ralph-autoloop.js` | ✅ EXISTS (needs fix) | — |
| `.opencode/plugins/no-code-sisyphus.js` | ✅ EXISTS | — |
| `.opencode/plugins/llm-pitfalls.js` | ✅ EXISTS (to merge) | — |
| `.opencode/plugins/auto-memory.js` | ✅ EXISTS (to merge) | — |
| `.opencode/plugins/nx-session-loop-bridge.js` | ✅ EXISTS (needs review) | — |
| `.opencode/plugins/meta-observer.js` | ❌ **NOT CREATED** | — |
| `data/bmad/architecture.md` | ✅ EXISTS | — |
| `data/bmad/stories/` (4 stories) | ✅ EXISTS (need rewriting) | — |
| `data/bmad/epics.md` (6 epics) | ✅ EXISTS | — |
| `data/bmad/plans/remaining-execution-plan.md` | ✅ EXISTS | — |
| `training/` | ❌ **NOT EXTRACTED** | ✅ **EXISTS** at `archive/.../training/` + `nx_trainer/data/` |
| `engine/` | ❌ **NOT EXTRACTED** | ✅ **EXISTS** compiled binary at `archive/.../src/engine/build/frankenstein-engine` |
| `src/` | ❌ **DOES NOT EXIST** | ⚠️ Python ref at `archive/.../packages/intelligence/` |
| `data/training/` | ❌ **NOT EXTRACTED** | ✅ **EXISTS** in archive training dirs |
| `data/memory/synapses/` | ❌ **NOT CREATED** | — (truly missing) |
| `data/learning/` | ❌ **NOT CREATED** | — (truly missing) |
| GGUF model (archive) | ✅ AVAILABLE (`qwen2.5-0.5b-q4.gguf`) | — |
| Old Rosetta training data (archive) | ✅ AVAILABLE (`rosetta_v8_complete_train.jsonl`) | — |
| Compiled C++ engine binary | ✅ AVAILABLE (`frankenstein-engine`, 502 lines CUDA) | — |
| ARCHITECTURE.md | ✅ AVAILABLE (600-line reference spec) | — |
| nx-agents.config.ts | ✅ AVAILABLE (177 lines, 18 agents) | — |

**Infrastructure Gap Revision:** Previously 7 directories missing. Now 4 truly missing (synapses/, learning/, src/, local engine/) — 3 exist in archive (training/, engine/, data/training/). Extraction gap, not creation gap.

---

## 8. DEPENDENCY GRAPH

```
┌──────────────────────────────────────────────────┐
│  AD-1: Meta-Observer        🔴 IN PROGRESS (1/50)│
│  └─ Creates meta-observer.js, classifier, hooks  │
└──────────────────────┬───────────────────────────┘
                       │
          ┌────────────┼────────────────┐
          ▼            ▼                ▼
┌─────────────────┐ ┌─────────┐ ┌──────────────┐
│ AD-2: Ralph Fix │ │AD-5:    │ │ AD-6: Model  │
│ 🔴 BROKEN       │ │Training │ │ Routing      │
│ Independent     │ │ Loop    │ │ 🔴 NOT BUILT │
│                  │ │ 🔴 NOT  │ │ Depends on   │
│ Fix: reorder    │ │ BUILT   │ │ AD-1 hook    │
│ detect/incr     │ │ Depends │ │              │
│                  │ │ AD-1    │ │              │
└─────────────────┘ └─────────┘ └──────────────┘

┌──────────────────────────────────────────────┐
│ AD-4: GGUF Weights     🔴 UNFIXED            │
│ Fix alignment calc in weights.rs             │
│ Independent — blocked only by engineering    │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ AD-3: Plugin Consolidation 🟡 NOT STARTED    │
│ Merge 5 → 3 plugins. Depends on AD-1 being  │
│ built (so llm-pitfalls.js + auto-memory.js   │
│ can merge INTO meta-observer.js)             │
└──────────────────────────────────────────────┘
```

**Critical Path:** Extraction workstream (engine + training + golden data) ⟂ Build workstream (AD-1 Meta-Observer) — can be done in PARALLEL  
**Fastest Path to Value:** Extraction items are pure copy/curation — fastest wins  
**Independent:** AD-2 (Ralph fix) + AD-4 (GGUF fix) — can be done in parallel  
**Must Wait:** AD-3 consolidation depends on AD-1 meta-observer existing  
**New Parallel Workstream:** ARCHIVE EXTRACTION — no dependency on any build item, can start immediately

---

## 9. RECOMMENDED NEXT ACTIONS

### Immediate — Build Fixes (Can Do Right Now — Parallel)

| # | Action | Type | Effort |
|---|--------|------|--------|
| 1 | **Fix AD-2: Ralph loop order** — swap detect/increment in `ralph-autoloop.js` | Code fix | 15min |
| 2 | **Fix AD-4: GGUF alignment** — fix `data_start` padding in `weights.rs` | Code fix | 30min |
| 3 | **Close stale loops** — `ralph_mojo` + `ralph_rosetta` | Admin | 5min |
| 4 | **Mark `hephaestus_mcp` as DONE** in state.json | Admin | 2min |
| 5 | **Consolidate 3× auth delegations** — keep one, remove duplicates | Admin | 5min |

### Immediate — Archive Extraction (New Priority Workstream) 🆕

| # | Action | Type | Effort | Source |
|---|--------|------|--------|--------|
| 6 | **Extract C++ engine** — copy `frankenstein-engine` binary + `engine.cpp` to `engine/` directory. Build HTTP API wrapper. | Extraction + API | 1-2h | `archive/.../src/engine/` |
| 7 | **Extract training pipeline** — copy `nx_trainer/train_v42.py` + data files to `training/nx_trainer/`. Verify LoRA config works. | Extraction | 1h | `archive/.../nx_trainer/` |
| 8 | **Create golden test set** — curate `training/test.jsonl` (73) + `by-category/chat/test.jsonl` (516) into `data/training/golden/`. Add README.md with split definitions. | Curation | 30min | `archive/.../training/` |
| 9 | **Index architecture docs** — copy `ARCHITECTURE.md` (600 lines) + `nx-agents.config.ts` (177 lines) to `data/bmad/reference/`. | Documentation | 15min | `archive/.../` root |

### Continue Ralph Loops

| # | Loop | Action |
|---|------|--------|
| 10 | `ralph_metaobserver` | Iterate 2/50 — build 64-dim classifier and hooks |
| 11 | `ses_1cdb97ea4ffeX5Qx1hyYxX9Iaa` | Start iteration 1/20 — connect daemon → engine → bridge |

### After Extraction Baseline (Then AD-1)

| # | Action | Depends On |
|---|--------|-----------|
| 12 | **Rust port of permission engine** — port `permission_engine.py` (213 lines) to `src/auth.rs` | Extraction items 6-9 complete |
| 13 | Merge `llm-pitfalls.js` + `auto-memory.js` into `meta-observer.js` | AD-1 built |
| 14 | Implement AD-5 online training loop (using extracted training pipeline) | AD-1 built + Extraction #7 |
| 15 | Implement AD-6 model routing | AD-1 built |
| 16 | Rewrite stories 1.1-1.4 as post-hoc docs or genuine TODOs | Momus/Metis findings |
| 17 | Wire C++ engine into Mojo daemon via FFI/HTTP | Extraction #6 complete |

### Session Cleanup

| # | Action |
|---|--------|
| 18 | Prune 15+ stale test sessions (`test`, `test1`, `test2`, `test3`, `bench`, etc.) |
| 19 | Run `session_prune(summary="...")` after cleanup |

### Priority Order (Revised with Archive Discovery)

```
1. P0: Fix Ralph loop (15min) + GGUF alignment (30min) — quick wins
2. P0: Extract C++ engine binary + HTTP wrapper (1-2h) — unblocks wiring
3. P0: Continue meta-observer loop (build work, no archive shortcut)
4. P1: Extract training pipeline + golden test set (1.5h) — unblocks training
5. P2: Rust port of auth/API from Python reference (2-3h)
6. P2: Online training loop + model routing (depends on meta-observer)
```

---

## 10. SUMMARY METRICS

| Metric | Count | vs Previous |
|--------|-------|-------------|
| **Total architecture decisions** | 8 (AD-1 through AD-8) | — |
| ✅ Fully built | 0 | — |
| 🟡 Partial / Needs fix | 3 (AD-2 broken, AD-3 partial, AD-7 partial) | — |
| 🔴 Not built | 5 (AD-1, AD-4, AD-5, AD-6, AD-8 issues) | — |
| **Active Ralph Loops** | 2 | — |
| **Stalled Ralph Loops** | 3 | — |
| **Pending delegations** | 6 (all now have archive references) | — |
| **Momus/Metis Critical Issues** | 7 — 0 fixed, 7 open | — |
| **Momus/Metis High Issues** | 19 — 6 mitigated by archive findings | **NEW** 🔄 H1,H2,H3,H4→🟡, H13→🟡, H15→🟡 |
| **Stories needing rewrite** | 4 (1.1-1.4) | — |
| **Pass checklist items** | 2/12 (17%) | — |
| **Fail checklist items** | ❌ **6/12 truly missing (50%)** | ↓ from 83% — **4 items mitigated by archive** |
| **Mitigated by archive** | ⚠️ **4/12 (33%)** — exists, needs extraction | **NEW** |
| **Infrastructure gaps** | 7 → **4 truly missing**, 3 exist in archive | ↓ from 7 |
| **Archive items found** | **6 major components** (engine, training, test data, auth ref, architecture spec, config spec) | **NEW** |
| **Extraction workstream** | 4 items — P0 engine binary, P1 training pipeline, P2 golden data, P2 auth Rust port | **NEW** |
| **85% issues unfixed** | ⚠️ **REVISED** — 50% truly unfixed, 33% extraction-mitigated, 17% pass | **UPDATED** |

---

## 11. PHASE 2 WORK ITEMS (from Remaining Execution Plan)

| Epic | Priority | Effort | Status | Depends On | Archive Note |
|------|----------|--------|--------|-----------|-------------|
| **A:** Mojo Daemon Auto-Restart + Embedding | P2 (#1) | 3-4h | 🟡 Not started — watchdog.sh, embed bridge wiring | AD-1 baseline | C++ engine EXISTS — extraction unblocks the embedding part |
| **C:** LSP Auto-Diagnose Plugin | P1 (#2) | 2-3h | 🔴 Not started | Nothing | — |
| **D:** Session Digest Plugin | P1 (#3) | 2-3h | 🔴 Not started | Nothing | — |
| **B:** nx-dictate Tray App | P3 (#4) | 6-8h | 🔴 Not started | Epic A | — |
| **E:** Training Feedback Loop | P3 (#5) | 6-8h | 🟡 **Pre-primed by archive** | Epic A | Training pipeline EXISTS (v42) — extraction task before loop can work |
| **F:** Session Log Mining | P4 (#6) | 4-5h | 🟡 **Pre-primed by archive** | Epics D, E | 47K session transcripts exist in archive — mining pre-primed |

**Note:** Epics C and D have ZERO dependencies — could start immediately for quick wins.  
**Archive Impact:** Epics E and F are pre-primed — the training pipeline and session transcripts already exist in archive, just need extraction. This reduces their effective effort by ~60%.

---

## 12. ARCHIVE INVENTORY — Librarian Findings

Discovered at `archive/data_chaos/data_chaos/`. Six major components found — shifts project from "build from scratch" to "extract + consolidate + Rust port."

### 12.1 Engine — Compiled C++ Inference Binary ✅ READY

| Property | Value |
|----------|-------|
| **Path** | `archive/.../src/engine/engine.cpp` (502 lines) + `build/frankenstein-engine` (compiled binary) |
| **Language** | C++ with CUDA |
| **Performance** | 107–127 tokens/second |
| **Status** | ✅ **Compiled and functional** |
| **Task** | Extract to `engine/` directory + build HTTP API wrapper |
| **Effort** | 1-2h (extraction + API wrapper) |
| **Priority** | 🔴 **P0** — unblocks engine wiring |

### 12.2 Training Pipeline — 42 Generations ✅ READY

| Property | Value |
|----------|-------|
| **Path** | `archive/.../nx_trainer/` — 42 training scripts (v1–v42) |
| **Latest** | `train_v42.py` — LoRA r=16, alpha=32, lr=2e-4 |
| **Supporting** | `unsloth_compiled_cache/`, `data/teacher_embeddings/` (8B teacher), benchmark scripts |
| **Status** | ✅ **Full pipeline exists** |
| **Task** | Copy latest pipeline to `training/nx_trainer/` + verify |
| **Effort** | 1h (extraction + verification) |
| **Priority** | 🔴 **P1** |

### 12.3 Golden Test Data ✅ READY

| Property | Value |
|----------|-------|
| **Path** | `archive/.../training/` |
| **Test sets** | `test.jsonl` (73 examples), `by-category/chat/test.jsonl` (516), `by-category/*/test.jsonl` (4 categories) |
| **Train/val splits** | `train.jsonl`, `val.jsonl` + per-category train/val |
| **Rosetta v8** | `nx_trainer/data/rosetta_v8_complete_train.jsonl` (1,000+ tool pairs) |
| **Session data** | `training/transcripts/` (47K session transcripts) |
| **Status** | ✅ **Rich dataset exists** |
| **Task** | Curate golden set → `data/training/golden/` |
| **Effort** | 30min |
| **Priority** | 🟡 **P2** |

### 12.4 Auth/API Reference — Permission Engine ⚠️ REFERENCE

| Property | Value |
|----------|-------|
| **Path** | `archive/.../packages/intelligence/` — 43 modules |
| **Key file** | `permission_engine.py` (213 lines) — full auth middleware in Python |
| **Supporting** | `router/` (Rust+PyO3 hybrid), `circuit_breaker/`, `delegation/`, `health_monitor/`, `context_manager/`, `intent_predictor/`, `fallback/`, `error_recovery/` |
| **Status** | ⚠️ **Reference exists, Rust implementation needed** |
| **Task** | Port to `src/auth.rs` + `src/api.rs` following established patterns |
| **Effort** | 2-3h (Rust port) |
| **Priority** | 🟡 **P2** |

### 12.5 Architecture Reference — Full Spec ✅ READY

| Property | Value |
|----------|-------|
| **ARCHITECTURE.md** | 600 lines — full system architecture, component relationships, data flow |
| **nx-agents.config.ts** | 177 lines — 18 agent definitions with routing rules |
| **Status** | ✅ **Complete specification** |
| **Task** | Copy to `data/bmad/reference/` for agent context |
| **Effort** | 15min |
| **Priority** | 🟢 **P3** (nice to have indexed) |

### 12.6 Training Data Files — Available JSONL

| File | Size | Content |
|------|------|---------|
| `nx_trainer/data/rosetta_v8_complete_train.jsonl` | 1,000+ pairs | Rosetta tool routing training |
| `nx_trainer/data/v4_real.jsonl` | ~1,500 | Real interaction training data |
| `nx_trainer/data/v3_final.jsonl` | ~1,200 | Cleaned v3 training |
| `nx_trainer/data/all_tools_data.jsonl` | ~2,000 | Comprehensive tool data |
| `nx_trainer/data/top40_train.jsonl` | ~800 | Top 40 tools focused |
| `training/train.jsonl` | ~1,000 | General training split |
| `training/by-category/chat/train.jsonl` | ~2,000 | Chat-specific training |
| `training/by-category/*/train.jsonl` | ~3,000 | Memory/code/reasoning splits |
| `training/interactions_20260515.jsonl` | Recent | Last 2 days interactions |
| `training/interactions_20260516.jsonl` | Recent | Latest day interactions |
| **Total structured** | **~5,900+ examples** | |
| **Session transcripts** | **~47,000** | In `training/transcripts/` |

### 12.7 Extraction Priority Matrix

| Item | Effort | Value | Dependencies Unblocked | Priority |
|------|--------|-------|----------------------|----------|
| C++ Engine (binary + HTTP wrapper) | 1-2h | 🟢 **HIGH** — live inference | Engine wiring, Rosetta integration, Mojo daemon ML | **P0** |
| Training Pipeline (copy v42 + verify) | 1h | 🟢 **HIGH** — training feedback loop | AD-5 online training, Epic E feedback loop | **P1** |
| Golden Test Set (curation) | 30min | 🟡 **MED** — eval harness | Rosetta verification, model benchmarking | **P2** |
| Auth Rust Port (from Python ref) | 2-3h | 🟡 **MED** — auth scaffolding | Auth middleware, API routes | **P2** |
| Architecture Docs (indexing) | 15min | 🔵 **LOW** — agent context | Better agent awareness | **P3** |

---

*Tracker generated by Masterplan. Use `session_prune(summary="...")` after processing. Active loops continue via ralph_start after session close.*
