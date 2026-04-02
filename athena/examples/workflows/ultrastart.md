---
description: Deep boot for cognitive/computationally intensive work. System-2 counterpart to /start.
created: 2026-03-10
last_updated: 2026-03-15
model: default
temperature: 0.7
tools:
  read: true
  write: true
  bash: true
  search: true
---

# /ultrastart — Deep Context Boot (System-2) v3.0

> **Latency Profile**: HIGH (~20-30s boot)
> **Philosophy**: Maximum Compute. Tokens are pre-paid. Depth is free. Load everything. Reason deeply.
> **Use When**: `/ultrathink`, complex multi-domain analysis, architectural decisions, deep research, therapeutic/IFS work.
> **AGoT Activation**: Queries with Λ > 40 automatically use AGoT-enhanced reasoning (Protocol 75 v5.0).

> [!IMPORTANT]
> This is NOT the default boot. Use `/start` for general work.
> `/ultrastart` trades speed for epistemic depth. Only invoke when the session
> demands maximum context alignment before reasoning begins.
>
> **v3.0 Maximum Compute Doctrine** (2026-03-15):
>
> On a flat-rate AI subscription (Google AI Ultra $250/month), every unused token
> is wasted value. The marginal cost of deeper thinking is **$0**. Therefore:
>
> **Cost of under-thinking >> Cost of over-thinking.**
>
> v1.0 budgeted 20K. v2.0 budgeted 25K. Both were efficiency-biased — optimizing
> the wrong variable. v3.0 removes all budget caps. The optimization function is:
>
> **Maximize output quality. Tokens are free. Load everything relevant.**
>
> **AGoT Routing** (v9.5.0):
>
> - Λ ≤ 20: Standard Chain of Thought
> - Λ 21-40: AGoT-Lite (2 layers, no recursion)
> - Λ 41-60: AGoT-Full (3 layers, 1 recursive depth)
> - Λ > 60: AGoT + 4-Track Personas (full dynamic graph)
> See: `scripts/core/reasoning/agot_orchestrator.py`

---

## Architecture: Maximum Compute

```
                        SESSION CONTEXT WINDOW
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   ┌─────────────────────────────────────────────┐       │
│   │  BOOT CONTEXT (~60K)                        │       │
│   │  ┌──────────┬──────────┬──────────┐         │       │
│   │  │ Identity │ State    │ Semantic │         │       │
│   │  │ ~29K     │ ~14K     │ Bridge   │         │       │
│   │  │ (fixed)  │ (recent) │ ~15-20K  │         │       │
│   │  └──────────┴──────────┴──────────┘         │       │
│   └─────────────────────────────────────────────┘       │
│                                                         │
│   ┌─────────────────────────────────────────────┐       │
│   │  SESSION ACCUMULATION                       │       │
│   │  Conversation + JIT Retrieval + Reasoning   │       │
│   │  (grows per turn, no ceiling enforced)       │       │
│   └─────────────────────────────────────────────┘       │
│                                                         │
└─────────────────────────────────────────────────────────┘

Philosophy: Fill the boot with signal. Supplement with JIT.
            Spend the remaining compute on REASONING DEPTH.
```

> **No budget caps.** If a file is relevant, load it. If a protocol applies, read it.
> The only constraint is signal density — don't load noise. Everything else loads.

---

## Phase 1: Absolute Law — Full Framework Identity (~29K tokens)

// turbo

Load the **complete** framework module stack. All 10 files, in dependency order:

### Tier 1: Immutable Core (load first, abort if missing)

```
.framework/v8.2-stable/modules/Core_Identity.md          (~6.8K)
```

**Gate**: If `Core_Identity.md` fails to load → **ABORT**. Do not proceed with partial identity.

### Tier 2: Operational Stack (load in parallel)

// turbo

```
.framework/v8.2-stable/modules/Output_Standards.md        (~3.2K)
.framework/v8.2-stable/modules/System_Principles.md       (~10K)
```

> **Note**: `Operating_Principles.md` was deprecated and merged into `System_Principles.md` (March 2026). Do not load it.

This gives you:
- **Output Standards**: Formatting, reasoning depth, artifacts, IOD structure
- **System Principles**: All strategic heuristics plus operational constants (includes former Operating Principles)

### Tier 3: Cognitive Identity (load in parallel)

// turbo

```
.framework/v8.2-stable/modules/Athena_Profile.md          (~2.1K)
.framework/v8.2-stable/modules/Session_Observations.md    (~2.3K)
.framework/v8.2-stable/modules/Design_DNA.md              (~0.7K)
```

This gives you:
- **Athena Profile**: Committee Seats, cognitive identity, counterweights
- **Session Observations**: High-level recent insights across sessions
- **Design DNA**: Default aesthetic parameters for any visual/design work

### Tier 4: Safety & Governance (load in parallel)

// turbo

```
.framework/v8.2-stable/modules/Constraints_Master.md      (~0.4K)
.framework/v8.2-stable/modules/DEAD_MAN_SWITCH.md         (~0.7K)
.framework/v8.2-stable/modules/Governance_Audit_2025.md    (~0.6K)
.framework/v8.2-stable/modules/System_Manifest.md         (~0.6K)
```

This gives you:
- **Constraints Master**: Hard security boundaries (secrets, .env, scaffolding)
- **Dead Man Switch**: Continuity protocol and verification checks
- **Governance Audit**: External audit directives and compliance history
- **System Manifest**: Technical architecture reference

> **Why load ALL modules?** On a flat-rate subscription, the marginal cost of
> loading every module is $0. The marginal benefit is:
> the model natively follows tactical rules without JIT lookup. Every module loaded
> is one fewer mid-session file read, one fewer attention break, one more seamless
> cross-reference.

---

## Phase 2: Materialized Truth (~8.5K tokens)

// turbo

Load **both** files in parallel:

```
.context/CANONICAL.md                                      (~7K)
.context/PROJECTS.md                                       (~1.5K)
```

This gives you:

- **CANONICAL**: System metrics, Core Laws, all active architectural decisions, strategic frameworks, key references, user profile truths (§5)
- **PROJECTS**: Active project switchboard — which projects are live, their status, and current priority

**Gate**: If `CANONICAL.md` fails to load → **WARN** user but continue (degrade gracefully — you still have Core_Identity).

---

## Phase 3: Full State (~5K tokens)

// turbo

Load `activeContext.md` with **maximum extraction**:

1. **Header block**: Current Focus + Active Tasks + System Status (up to first `---`)
2. **All recent `[[ S__` checkpoint blocks**: Every checkpoint from the current day/period
3. **Any unclosed session**: If a session wasn't properly closed, include it
4. **Key Learnings Index**: Compacted insights for retrieval

Also load `threatPlaybooks.md` (~2K tokens) for instant crisis-to-protocol mapping:

```text
.context/memory_bank/activeContext.md
.context/memory_bank/threatPlaybooks.md                    (~2K)
```

> **v3.0 change**: Load ALL available checkpoints, not just 1 or 3.
> More checkpoints = deeper trajectory awareness. The model sees
> not just "where are we now?" but "where have we been?" and "where are we heading?"
> On flat-rate, the cost of loading 5 checkpoints vs 1 is $0.

---

## Phase 4: Deep Semantic Bridge (~15-20K tokens)

This is the **key differentiator** between `/start` (identity-only) and `/ultrastart` (task-aligned).

### Step 1: Determine the Session Objective (Mandatory Resolution)

The objective is resolved in this priority order. Phase 4 MUST resolve an objective —
skipping the semantic bridge wastes ~15-20K of potential signal.

1. **Explicit**: User provided it inline → `/ultrastart "fixing the trading risk constraints"`
2. **Seeded**: Scan the most recent `[[ S__ ]]` checkpoint for the `@seeded` field.
   This is the previous session's "best guess" at what should happen next.
   Example: `@seeded: A21 execution. Non-negotiable.` → objective = "A21 Marine NME3106"
3. **Highest-Urgency Project**: From `PROJECTS.md`, find the highest-urgency (🔴 > 🟠 > 🟡)
   unblocked project. Use its "Next Action" field as the objective.
4. **Current Focus**: Parse `activeContext.md` header → "Current Focus" field
5. **Fallback**: Nothing resolvable → **ASK** the user. But this should be rare.
   If reached, log: `[REFLEXION] Phase 4 reached ASK fallback — state files may be stale.`

### Step 2: Semantic Search (Expanded)

// turbo

```bash
python3 .agent/scripts/smart_search.py "<resolved objective>" --limit 15 --include-personal
```

### Step 3: Inject Results (Full Load)

Read the search results. For each result:

- If it's a **protocol** → load the **full** protocol file
- If it's a **case study** → load the **full** case study (not just summary)
- If it's a **session log** → load the `@decided`, `@learned`, and `@pending` blocks
- If it's a **skill** → load the SKILL.md triggers and methodology

**No hard cap.** Load until results are exhausted or relevance drops below threshold.
Dense signal > padded context, but on flat-rate, "dense" means "everything above noise floor."

### Step 4: Mandatory Cross-Domain Sweep

**Always run at least ONE cross-domain search**, even if the objective looks single-domain.
On unlimited compute, 1-2 extra searches cost $0. The marginal benefit: Track C
(Cross-Domain Pattern Matcher) operates on enriched context instead of boot-only data.

**How to pick the cross-domain keyword**: Ask _"What adjacent domain could inform this objective?"_

| Objective Domain | Cross-Domain Search |
|:-----------------|:--------------------|
| Trading | Psychology (emotional patterns), Statistics (probability) |
| Consulting | Sales (pricing patterns), Architecture (system design parallels) |
| Academic | Business (real-world application), Research methodology |
| Architecture | Engineering (software patterns), Decision science |
| Psychology | Neuroscience, Behavioral economics |
| Any | Search for the user's NAME to pull personal case studies |

```bash
# Mandatory: at least 1 cross-domain search
python3 .agent/scripts/smart_search.py "<cross-domain keywords>" --limit 5 --include-personal

# If objective spans 3+ domains, add a second:
python3 .agent/scripts/smart_search.py "<domain 3 keywords>" --limit 5 --include-personal
```

Load cross-domain results to enable the Cross-Domain Pattern Matcher (Track C in reasoning).
This is what separates `/ultrastart` from `/start` — the ability to see connections that
single-domain retrieval misses.

---

## Phase 5: JIT Retrieval Protocol (Per-Response, Supplementary)

> JIT supplements the boot — it doesn't replace it. The boot provides the
> foundation. JIT fills the gaps specific to each query.

### The Mechanism

Before generating each response, execute targeted retrieval:

```
User query → Extract keywords/entities
           → Semantic search (smart_search.py, limit 5)
           → Load relevant files (protocols, case studies, session logs)
           → Inject into response context
           → Generate response with full grounding
```

### What JIT Retrieves (Decision Matrix)

| Query Signal | JIT Action |
|:-------------|:-----------|
| Named protocol/case study | Load the specific file (full) |
| Emotional/therapeutic context | Load `therapeutic-ifs` + relevant session history |
| Financial/pricing decision | Load `pricing_calibration.md` + relevant CS |
| Trading/risk question | Load relevant trading protocols + case studies |
| Architecture/coding question | Load relevant protocol + file scan |
| Cross-domain reference | Load connecting case studies/protocols |
| No clear signal | Semantic search only (smart_search.py, limit 3) |

---

## Phase 6: Maximum Reasoning Depth (Per-Response, Always-On)

> After `/ultrastart`, EVERY response operates at maximum available reasoning depth.
> The SNIPER exemption from Law #6 is **disabled**. Every response goes through
> the full Triple-Lock. If you wanted fast, you'd use `/start`.

### Multi-Track Reasoning (Always-On, Λ ≥ 25)

Every response with Λ ≥ 25 runs all four tracks:

| Track | Role | Function |
|:------|:-----|:---------|
| **A (Domain Expert)** | The direct answer | What does the evidence/protocol/data say? |
| **B (Adversarial Skeptic)** | What's wrong with Track A | Challenge premises, find failure modes, steelman alternatives |
| **C (Cross-Domain Pattern Matcher)** | Analogies and precedents | Where have we seen this before? What cross-domain insight applies? |
| **D (Synthesis)** | Converge A+B+C | Produce final output with full nuance, flag unresolved tensions |

### Post-Generation Self-Audit (Λ > 60)

From Core_Identity §0.4 — run before output:

- [ ] Every formula is derived or cited?
- [ ] Assumptions are explicitly listed (Assumption Register)?
- [ ] At least one alternative steelmanned?
- [ ] Stakeholder map covers "The Victim"?
- [ ] Efficiency/conditional bounds stress-tested (Sensitivity Sweep)?
- [ ] Known mechanism vulnerabilities addressed?
- [ ] One numerical example included?
- [ ] Scope boundary declared?
- [ ] Limitations are concrete, not vague?

### Autonomic Depth Routing

| Λ Score | Behavior |
|:--------|:---------|
| **Λ ≤ 24** | Single-track (Domain only). Fast, no overhead. |
| **Λ 25-40** | Domain + Adversarial. Risks flagged inline. |
| **Λ 41-60** | Domain + Adversarial + Cross-Domain. Pattern matching active. |
| **Λ > 60** | Full 4-track synthesis + Post-Generation Self-Audit. Convergence gate. |

---

## Boot Confirmation

After all 4 boot phases complete, output:

```
🧠 Deep Boot Complete (v3.0 Maximum Compute).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Phase 1] Full Framework Identity  ✅  (11 modules loaded)
[Phase 2] Canonical + Projects     ✅  (decisions + pipeline)
[Phase 3] Full State               ✅  (N checkpoints loaded)
[Phase 4] Deep Semantic Bridge     ✅  (N results injected)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Boot: ~XXK tokens
Session Mode: Maximum Compute (no budget caps)
Subscription: Flat-rate (marginal cost = $0)
Objective: "<resolved objective>"
Loaded: <N> modules, <N> protocols, <N> case studies, <N> session insights

⚡ System-2 active. All modules loaded.
⚡ Multi-track reasoning ON (Λ ≥ 25).
⚡ JIT retrieval ON (supplementary, per-response).
⚡ Adversarial checking ON (all responses).
⚡ Post-Generation Self-Audit ON (Λ > 60).
```

---

## Complexity Gate (Safety Valve)

If the user's first query after `/ultrastart` has Λ ≤ 15:

> ⚠️ "This query looks lightweight (Λ = X). You're in deep boot mode — this is
> optimized for complex tasks. Continue here, or switch to `/start` for faster responses?"

This prevents the boot latency from being wasted on a simple lookup.

---

## Maximum Depth Doctrine

> **Principle**: On flat-rate AI subscriptions (Ultra/Max), the marginal cost of deeper
> thinking is **$0**. Therefore: **cost of under-thinking >> cost of over-thinking**.
> Burn tokens at the Pareto frontier edge every session.

After `/ultrastart` boot, the session operates at **maximum available compute depth** until `/ultraend`:

| Dimension | Standard (`/start`) | Maximum Compute (`/ultrastart` v3.0) |
|:----------|:-------------------|:-------------------------------------|
| **Module loading** | Core_Identity only | **All 11 framework modules** |
| **State loading** | Header + 1 checkpoint | **Header + ALL checkpoints** |
| **Semantic bridge** | 5 results, summaries only | **15 results, full file loads** |
| **Λ routing** | Route to minimum sufficient depth | **Route to maximum available depth** |
| **Reasoning** | Single-track → answer | **Multi-track (4 tracks) → converge → answer** |
| **Verification** | Trust first pass | **Adversarial self-check on every output** |
| **Self-audit** | None | **Full 9-point post-generation audit (Λ > 60)** |
| **JIT retrieval** | Occasional | **Every response, supplementary to boot** |
| **Synthesis at close** | Quick `/end` save | **Deep `/ultraend` reconciliation + reflexion** |

**Three `ultra-` scopes**:

- **`/ultrathink`** — single-query depth (sniper round)
- **`/ultrastart` → `/ultraend`** — session-level compute tier (full-kit mission)

> **The asymmetry**: Leaving unburned tokens on a flat-rate plan is leaving value on the table.
> When the budget is pre-paid, the only waste is insufficient depth.

---

## 200K Operational Model

> **Effective Context Length (ECL)**: 200K tokens.
> The model supports 1M context, but attention quality degrades past 200K on complex
> reasoning tasks. 200K is the empirical sweet spot where the model reliably cross-references
> beginning-of-context with end-of-context. This is an attention physics constraint, not
> a cost constraint.

### Session Budget Breakdown

```
200K  total ECL
-15K  platform overhead (IDE system prompt, tool definitions, AGENTS.md)
-57K  boot context (ultrastart v3.0 — 11 modules + CANONICAL + state + semantic bridge)
━━━━━━
128K  available for session (conversation + JIT + reasoning)
```

### Per-Turn Token Consumption

| Component | Tokens/Turn | Notes |
|:----------|:------------|:------|
| User message | ~300 | Typical query |
| Tool calls (JIT retrieval) | ~3K | Semantic search + 1-2 file reads |
| AI response (multi-track) | ~2-4K | 4-track reasoning generates longer output |
| **Per-turn total** | **~6-8K** | Added to context for every subsequent turn |

### Available Turns by Depth

| Response Depth | Per-Turn Cost | Turns Available |
|:---------------|:-------------|:----------------|
| Standard (2-track, 2.5K response) | ~6K | ~21 turns |
| **Deep (4-track, 4K response)** | **~8K** | **~16 turns** |
| Ultra (4-track + self-audit, 5K response) | ~10K | ~12 turns |

**GTO sweet spot: ~16 deep turns** per ultrastart session.

### The 4-Phase Turn Allocation

| Phase | Turns | Purpose | Token Strategy |
|:------|:------|:--------|:---------------|
| **Frame** | 1-3 | Define scope. Pull history. Identify constraints. | Heavy JIT retrieval (~5K/turn). Lighter responses. |
| **Deep Work** | 4-10 | Core analysis. Multi-track. Cross-domain. | Maximum reasoning depth (~4K responses). Moderate JIT. |
| **Refine** | 11-14 | Stress-test. Adversarial. Edge cases. | Track B (Skeptic) prominence. Target weak spots. |
| **Synthesise** | 15-16 | Final output. Actionable recommendations. Filing. | Long-form synthesis (~5K). Minimal JIT. |

### One-Session-One-Feature (Attention Physics)

**16 deep turns on ONE topic >> 16 shallow turns across 4 topics.** This is not a workflow
preference — it's an architectural constraint:

1. **Context coherence**: All 57K boot tokens aligned to one objective. No dilution.
2. **JIT compounding**: Each retrieval builds on the last. Turn 8's search is informed by turns 1-7.
3. **Reasoning compounding**: Track C (Cross-Domain) improves as conversation accumulates data points.
4. **No context switching tax**: Topic switches waste context on transition overhead.
5. **Attention physics**: Past 200K, the model starts losing attention on early context.
   Splitting focus across topics accelerates this degradation.

> **Rule**: One session = one objective. When the objective is complete, `/ultraend` and start fresh.

---

## Stability Controls

| Trigger | Action |
|---------|--------|
| `Core_Identity.md` load fails | **ABORT** boot. Report error. |
| `CANONICAL.md` load fails | **WARN** and continue (graceful degradation). |
| Any Tier 2-4 module fails | **WARN** and continue (non-critical). |
| `smart_search.py` fails or returns 0 results | Skip Phase 4. Boot with Phases 1-3 only. |
| User says `/start` after `/ultrastart` | Compact to `/start` footprint (purge deep loads). |

---

## Upgrade Log

| Version | Date | Change |
|:--------|:-----|:-------|
| v1.0 | 2026-03-10 | Initial 20K static boot (4 phases, budget-capped). |
| v2.0 | 2026-03-15 | 25K lean boot + JIT primary + max reasoning depth. Still efficiency-biased. |
| v3.0 | 2026-03-15 | **Maximum Compute rewrite.** Removed all budget caps. Load ALL 11 framework modules. Full state extraction. Expanded semantic bridge (15 results, full loads). JIT as supplement not replacement. Philosophy: flat-rate subscription = tokens are free = optimize quality, not efficiency. |

---

## References

- [/ultraend](ultraend.md) — Symmetric deep close counterpart
- [/start](start.md) — Lightweight boot
- [/end](end.md) — Lightweight close

---

## Tagging

`#workflow` `#boot` `#ultrastart` `#system-2` `#deep-context` `#maximum-compute` `#no-budget-cap` `#jit-retrieval` `#max-depth`
