---
description: Token Economy Mode — maximize output quality while minimizing token expenditure
created: 2026-03-28
last_updated: 2026-03-28
model: default
temperature: 0.5
tools:
  read: true
  write: true
  bash: true
  search: true
---

# /minmax — Token Economy Mode v1.0

> **Latency Profile**: ULTRA-LOW (~1K token activation)
> **Philosophy**: Maximum signal per token. Every token must earn its place.
> **Use When**: Pay-per-token pricing, context window pressure, low-complexity sessions, or deliberate efficiency training.
> **Composable**: Activate BEFORE `/start` or `/ultrastart` to constrain their boot behavior.

> [!IMPORTANT]
> This is an **inverted optimization** from the default Maximum Compute Doctrine.
>
> | Mode | Optimization Function | When |
> |:-----|:---------------------|:-----|
> | **Normal** | `maximize(quality)` — tokens are free | Flat-rate subscription |
> | **Minmax** | `maximize(quality / tokens)` — every token has a cost | Pay-per-token, context pressure, efficiency drill |
>
> The doctrine doesn't change: depth still matters. What changes is the
> **willingness to spend tokens on speculative loads**. In Normal mode,
> speculative loading is free so you load everything. In Minmax mode,
> speculative loading has a cost so you load only what you'll USE.

---

## Phase 1: Activation (~500 tokens)

When the user invokes `/minmax`:

### Step 1: Classify Session Objective

Before loading ANYTHING, ask one question:

> **"What's the one thing this session needs to accomplish?"**

If the user already stated it (or `@seeded` from last session is clear), skip the question and infer.

### Step 2: Set Mode Flag

Confirm activation with:

```
⚡ Minmax Mode Active.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Objective: [inferred or stated]
Boot: Selective (task-aware)
Search: Surgical (--limit 3)
Output: Dense (signal > prose)
Close: Micro-default
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**That's it.** Phase 1 is the entire "workflow" — the rest of this file defines behavioral rules that persist for the session.

---

## Behavioral Rules (Active for entire session)

### Rule 1: Selective Boot

When `/start` or `/ultrastart` follows `/minmax`:

**For `/start`** (already lean — minimal changes):
- Skip `productContext.md` unless session is about system identity/philosophy
- Load only the `@pending` + `@seeded` lines from `activeContext.md`, not the full header block
- Skip Protocol 528 scan (execution awareness) — defer to `/end`

**For `/ultrastart`** (major savings — this is where the big wins are):

Instead of loading all framework modules, use this task-routing table:

| Session Objective | Load These Modules Only | Skip | Est. Tokens |
|:-----------------|:-----------------------|:-----|:------------|
| Client deliverable (capstone, code) | Core_Identity, Output_Standards | Others | ~5K |
| Consulting / business strategy | Core_Identity, System_Principles, Operating_Principles | Others | ~8K |
| Trading / risk analysis | Core_Identity, System_Principles | Others | ~5K |
| Therapy / IFS / psychology | Core_Identity, Athena_Profile, User_Profile_Core | Others | ~6K |
| System maintenance / refactor | Core_Identity, System_Manifest | Others | ~4K |
| Research / deep analysis | Core_Identity, Output_Standards, System_Principles | Others | ~8K |
| General / mixed | Core_Identity + let JIT handle the rest | Others | ~3K |

> **Core_Identity is ALWAYS loaded.** It contains the Laws. Everything else is conditional.

**CANONICAL.md**: Load Sections 2 (Laws) + 3 (Active Decisions) only. Skip Sections 4-5 (Strategic Frameworks, User Profile) — retrievable via Exocortex if needed.

**Semantic Bridge**: Run ONE targeted search query (not two broad ones). Max `--limit 3`.

**Threat Playbooks**: Skip entirely unless session objective involves crisis/risk.

### Rule 2: Per-Turn Token Discipline

| Dimension | Normal Mode | Minmax Mode |
|:----------|:-----------|:------------|
| **Λ default** | STANDARD (robustness bias) | SNIPER (efficiency bias) — upgrade to STANDARD only when Λ ≥ 15 |
| **Search** | `--limit 5-15` per query | `--limit 3` per query, max 1 search per turn |
| **Output format** | Full prose + reasoning | Tables > bullets > prose. Same signal, fewer words. |
| **Co-activation** | Auto-cascade downstream clusters | One cluster at a time. No speculative pre-loading. |
| **Reflexion journaling** | Every error | Only on errors that cost > 2 turns to fix |
| **Quicksave** | After every STANDARD+ turn | After session, not per-turn |
| **Adaptive loading** | Load full file when triggered | Load surgical excerpt (start/end lines) when possible |
| **Code output** | Full files with comments | Minimal diff — change only what's needed, skip explanatory comments |

### Rule 3: Response Density Standard

In Minmax mode, every response should follow the **Dense Output Protocol**:

1. **Lead with the answer.** No preamble, no "Let me think about this."
2. **Use tables for structured data.** A 5-row table < 50 words of prose saying the same thing.
3. **Use diffs for code changes.** Don't rewrite entire files.
4. **One search per turn max.** If you need more context, ask the user — they might already know.
5. **No restating what the user said.** They know what they said.
6. **No hedging unless genuinely uncertain.** "This might work" wastes tokens. "Do X" doesn't.

> **Quality floor**: Minmax mode reduces TOKEN volume, not REASONING quality.
> A 200-token response with the right answer > a 2,000-token response with the right answer + 1,800 tokens of explanation nobody asked for.
> If the user wants depth, they'll ask. Default to concise.

### Rule 4: Session Close (Minmax Override)

When closing a Minmax session:

- **Default to MICRO close** (Phase 1A of `/end`) unless 3+ decisions were made
- **Skip**: CANONICAL check, Decision Log Gate, Context Hygiene Gate
- **Skip**: PROJECTS.md update IF session didn't touch any active project
- **Always write**: Session log + checkpoint block (minimum viable state preservation)
- **Defer**: `shutdown.py` full pipeline → run `--micro` variant only

**Checkpoint format** (compressed):

```markdown
## S[N] (Minmax): [TOPIC]

- [One-line summary]

[[ S__ |
@focus: [topic]
@status: Closed (Minmax)
@decided: [decisions, if any]
@pending: [carry from previous]
@seeded: [next focus]
!checkpoint ]]
```

> No `## Session Learnings` block unless a genuine reusable insight emerged.
> No `## Session Closed` ceremony — the checkpoint IS the close.

---

## Token Budget Reference

Estimated token usage under Minmax mode vs Normal:

| Activity | Normal (/start) | Normal (/ultrastart) | Minmax (/start) | Minmax (/ultrastart) |
|:---------|:----------------|:--------------------|:----------------|:--------------------|
| **Boot** | ~2K | ~60K | ~1K | ~8-12K |
| **Per-turn (avg)** | ~3-5K | ~5-8K | ~1-2K | ~2-4K |
| **Close** | ~600 | ~2K | ~100 | ~300 |
| **10-turn session** | ~35K | ~115K | ~12K | ~30K |

> **Savings**: ~65-75% reduction vs normal mode. Quality floor maintained via surgical loading + JIT fallback.

---

## Anti-Patterns (Minmax-Specific)

| ❌ Don't | ✅ Do |
|:---------|:------|
| Load a file "just in case" | Load only when the current turn needs it |
| Run 3 parallel searches to "be thorough" | Run 1 targeted search with specific query |
| Write 500-word explanations for simple changes | Write the diff + one sentence of rationale |
| Default to STANDARD Λ for everything | Default to SNIPER, upgrade only when complexity demands it |
| Restate the user's question before answering | Answer directly |
| Load CANONICAL §4-5 at boot | Let JIT retrieve specific frameworks when referenced |
| Run full `shutdown.py` pipeline | Run `--micro` unless the session was substantive |

---

## Deactivation

Minmax mode deactivates automatically at session close. No carry-over to next session.

To deactivate mid-session: user says "normal mode" or "/fullload" — immediately revert to standard behavioral rules.

---

## Design Rationale

> **Why a standalone workflow instead of flags on existing workflows?**
>
> Law #4 (Modular Architecture): New capability = new protocol file, not monolith expansion.
> Existing workflows (`/start`, `/end`, `/ultrastart`, `/ultraend`) are already well-tuned
> for their contexts. Injecting conditional `--lean` logic into all four creates coupling
> and maintenance burden. A standalone mode toggle is composable, reversible, and zero-cost
> when unused.
>
> **Core Principle — Token Economy Doctrine**:
>
> On pay-per-token pricing, the optimization function inverts:
> - Normal: `cost(under-thinking) >> cost(over-thinking)` → load everything
> - Minmax: `cost(over-loading) >> cost(under-loading)` → load surgically
>
> Both modes maintain the same QUALITY floor. The difference is signal DENSITY —
> how much quality you extract per token spent.

---

## References

- [/start](start.md) — Standard boot (modified by Minmax Rule 1)
- [/ultrastart](ultrastart.md) — Deep boot (most savings from Minmax Rule 1)
- [/end](end.md) — Standard close (modified by Minmax Rule 4)

---

## Tagging

`#workflow` `#automation` `#minmax` `#token-economy` `#efficiency`
