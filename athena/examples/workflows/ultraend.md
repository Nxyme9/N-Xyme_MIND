---
description: Deep close for cognitive/computationally intensive sessions. System-2 counterpart to /end.
created: 2026-03-10
last_updated: 2026-03-15
model: default
temperature: 0.5
tools:
  read: true
  write: true
  bash: true
  search: true
---

# /ultraend — Deep Session Close (System-2) v3.1

> **Latency Profile**: HIGH (~2-3 min)
> **Philosophy**: Extract maximum learning value. Close once, close right.
> **Context Constraint**: After a deep session, the 200K ECL may be 60-80% consumed.
> Synthesize efficiently because the context window is nearly full — not because tokens cost money.
> **Use When**: After `/ultrastart` sessions, 5+ decision sessions, weekly reviews, or any session with high insight density.

> [!IMPORTANT]
> This is NOT the default close. Use `/end` for general sessions.
> `/ultraend` trades speed for epistemic depth. Only invoke when the session
> generated enough signal to justify deep synthesis.

---

## Activation Gate

**Auto-suggest `/ultraend`** when ANY of these are true:

| Trigger | Why |
|:--------|:----|
| Session opened with `/ultrastart` | Symmetrical pairing — deep boot deserves deep close |
| 5+ decisions made this session | High decision density = high extraction value |
| New frameworks/axioms discovered | Must propagate to CANONICAL before context is lost |
| Session Λ total ≥ 200 | Heavy cognitive session — lots of signal to compress |
| User explicitly requests | Direct invocation |

If NONE are true → default to `/end`. Don't burn tokens on shallow sessions.

---

## Phase 0: Standard Close (Inherit from /end)

Execute **all steps from `/end` Phase 1B** first:

1. ✅ Write Session Log file
2. ✅ Append Checkpoint to `activeContext.md`
3. ✅ Canonical Check (conditional)
4. ✅ Decision Log Gate
5. ✅ Update Project Switchboard (MANDATORY)
6. ✅ Context Hygiene Gate

> [!TIP]
> Phase 0 is just `/end`. Everything that follows is ADDITIVE.
> If `/ultraend` fails mid-synthesis, you still have a clean `/end` close.

---

## Phase 1: Cross-Session Pattern Scan (~60s)

**What**: Scan the last 5 session logs for recurring themes, unresolved threads, and behavioral patterns.

### Step 1: Load Recent Sessions

// turbo

```bash
ls -1t .context/memories/session_logs/ | head -5
```

Read the `@decided` and `@pending` blocks from each.

### Step 2: Pattern Detection

Ask yourself these 4 questions:

1. **Recurring Topics**: What theme appeared in 3+ of the last 5 sessions? (Signal: user obsession or unresolved problem)
2. **Orphaned Pendings**: What appeared in `@pending` 3+ sessions ago but never moved to `@decided`? (Signal: stuck or deprioritized)
3. **Decision Reversals**: Did any `@decided` item in this session contradict a previous `@decided`? (Signal: learning or drift)
4. **Velocity Trend**: Are sessions getting more productive (higher Λ/session) or less? (Signal: system health)

### Step 2.5: Decision Outcome Tracking (GTO v3.1)

> **This is the Brier Score of your session close** — the highest-value activity in the entire ultraend.
> It calibrates future decision-making by measuring prediction accuracy.

For each `@decided` item from sessions **N-1 through N-3**:

1. **State the original decision** and the **expected outcome** at the time
2. **Ask**: _"Did this decision produce the expected outcome?"_
3. **Classify the result**:

| Result | Action |
|:-------|:-------|
| ✅ Outcome matched expectation | Log as calibrated. No action needed. |
| ⚠️ Outcome partially matched | Log the delta. Ask: _"What did we miss?"_ |
| ❌ Outcome missed entirely | Log as miscalibrated. Ask: _"Was the decision wrong, or was the environment unpredictable?"_ |
| 🔄 Outcome still pending | Carry forward. Check again next `/ultraend`. |

4. **Track `@seeded` accuracy**: Did the seeded next-session suggestion from N-1 match what actually happened in session N? This measures strategic prediction quality.

Append to session log:

```markdown
## Decision Outcome Tracking

| Session | Decision | Expected Outcome | Actual Outcome | Calibration |
|:--------|:---------|:-----------------|:---------------|:------------|
| S[N-1] | [decision] | [what we expected] | [what happened] | ✅/⚠️/❌/🔄 |
| S[N-2] | [decision] | [what we expected] | [what happened] | ✅/⚠️/❌/🔄 |

**Seed Accuracy**: S[N-1] seeded "[X]" → Session N actually did "[Y]" → [Match/Partial/Miss]
```

---

## Phase 2: CANONICAL Deep Reconciliation (~60s)

**What**: `/end` does a conditional check ("did this session touch CANONICAL?"). `/ultraend` does a **mandatory deep scan**.

### Step 1: Load CANONICAL.md

Read the full Strategic Frameworks table (Section 4).

### Step 2: Reconciliation Questions

For each insight from this session:

1. **Is it already in CANONICAL?** → Skip
2. **Does it contradict something in CANONICAL?** → **UPDATE CANONICAL** (truth evolved)
3. **Is it a new framework worth preserving?** → **ADD to CANONICAL**
4. **Is it session-specific noise?** → Skip (not every insight is canonical)

### Step 3: Framework Bundling Check

> **Key Question**: Do the insights from this session form a coherent, named framework?

If 3+ related insights emerged in one session, they may constitute a new **named framework** worth bundling:

- Give it a name (e.g., "Pricing Thesis", "Distribution Physics")
- Write a one-liner that captures the core principle
- Add to CANONICAL Section 4

If insights are isolated, file individually.

---

## Phase 2.5: Insight Compounding (GTO v3.1 — NEW)

> **What**: The explicit "connect the dots" step. This is where the unlimited compute
> philosophy pays its highest dividend — generating compound insights that neither
> the current nor previous sessions had alone.

### Step 1: Cross-Pollination Question

Ask yourself:

> _"What insight from THIS session, combined with an insight from a PREVIOUS session,
> creates a NEW insight that neither had alone?"_

This is not a vague prompt — work through it systematically:

1. List the top 3 insights from this session (from `@decided` + `@learned`)
2. List the top 3 insights from the most recent 3 sessions (from Step 2 above)
3. For each pair (current × previous), ask: _"Is there a connection?"_
4. If yes → name the compound insight and write a one-liner

### Step 2: File Compound Insights

For each compound insight generated:

- If it's a **named framework** (3+ connected insights) → Add to `CANONICAL.md` Section 4
- If it's a **tactical pattern** → Add to `Session_Observations.md`
- If it's a **single connection** → Log in the session log under `## Compound Insights`

Append to session log:

```markdown
## Compound Insights

- **[Compound Insight Name]**: [Session N insight] + [Session N-X insight] → [New insight]
  Filed to: [CANONICAL §4 / Session_Observations / session log only]
```

> **No compound insights?** That's fine — not every session produces them. Log:
> `## Compound Insights: None detected.` and move on. Don't force connections.

---

## Phase 3: Reflexion Archive (~30s)

**What**: Explicit post-mortem. What went well, what didn't, what to repeat/avoid.

### Step 1: Ask These 3 Questions

1. **What worked?** — What approach, tool, or decision produced outsized value this session?
2. **What didn't?** — Where did I waste time, backtrack, or produce low-value output?
3. **What's the counterfactual?** — If I could redo this session, what one thing would I change?

### Step 2: File to Session Log

Append to the session log:

```markdown
## Reflexion

- **Worked**: [approach/decision that worked well]
- **Didn't**: [waste/backtrack/mistake]
- **Counterfactual**: [what I'd change if I could redo this session]
```

### Step 3: Explicit Propagation (GTO v3.1)

> **Close the learning loop.** Reflexion learnings must route to their correct destination,
> not just sit in the session log. Same tokens, higher signal extraction.

For each reflexion finding, apply the propagation matrix:

| Finding Type | Propagation Target | Action |
|:-------------|:-------------------|:-------|
| "Worked" reveals a **reusable technique** | `CANONICAL.md` Section 4 | Check if already exists. If not → add as named framework. |
| "Didn't" reveals a **repeatable mistake** | Relevant skill's `SKILL.md` | Add/update entry under `## Anti-Patterns` section. Include the real case and fix. |
| "Counterfactual" reveals a **better workflow** | `TECH_DEBT.md` | File as candidate optimization with effort estimate (S/M/L). |
| "Worked" is **session-specific** (not reusable) | Session log only | No propagation needed. |
| "Didn't" is a **one-off mistake** (not repeatable) | Session log only | No propagation needed. |

> **Gate**: Only propagate if the finding is REUSABLE across sessions. One-off mistakes
> and session-specific wins stay in the session log.

---

## Phase 4: Strategic Portfolio Review (~30s)

**What**: Zoom out. Are we working on the right things?

### Step 1: Load PROJECTS.md

### Step 2: Ask These Questions

1. **Priority Alignment**: Is the highest-EV project getting the most sessions? If not, why?
2. **Stale Projects**: Any project that hasn't been touched in 7+ days? Should it be parked or killed?
3. **Pipeline Health**: Is the ratio of Internal:External projects healthy? (Target: ≤30% internal, ≥70% external for revenue)
4. **Next Session Suggestion**: Based on everything above, what should the NEXT session focus on?

### Step 3: Update PROJECTS.md

- Advance or regress phases based on findings
- Park stale projects
- Update `Last triaged` timestamp

### Step 4: Seed Next Session

Add to the checkpoint `@pending`:

```
@seeded: [Suggested next session focus based on portfolio review]
```

This gives `/start` or `/ultrastart` a head start on context loading.

---

## Phase 5: Shutdown Orchestrator

// turbo

```bash
.venv/bin/python3 .agent/scripts/shutdown.py
```

Same as `/end` — session compilation, git commit, compliance report.

---

## Output Template

After all phases complete:

```
🧠 Deep Close Complete (GTO v3.1).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Phase 0]   Standard Close          ✅
[Phase 1]   Cross-Session Scan      ✅  [N patterns, N decision outcomes tracked]
[Phase 2]   CANONICAL Reconcile     ✅  [N updates, N new frameworks]
[Phase 2.5] Insight Compounding     ✅  [N compound insights generated]
[Phase 3]   Reflexion + Propagation ✅  [N findings propagated]
[Phase 4]   Strategic Review        ✅  [Next: "<seeded focus>"]
[Phase 5]   Shutdown                ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Session closed. Time: [HH:MM SGT]
Seed Accuracy (prev session): [Match/Partial/Miss]
```

---

## Failure Recovery

| Failure | Action |
|:--------|:-------|
| Phase 0 (/end) fails | Fix Phase 0 first. Do not proceed to synthesis. |
| Phase 1-4 fails mid-synthesis | Phase 0 already ran — session is safely closed. Report which synthesis phase failed. |
| `shutdown.py` fails | Same as `/end` fallback: `git add -A && git commit -m "session close" --no-verify`. |
| 2 consecutive failures | **Circuit Breaker (P514)**. Stop. Report root cause. |

---

## Quick Reference

| Close Type | Latency | When |
|:-----------|:--------|:-----|
| `/end` (admin) | ~60s | Most sessions |
| `/ultraend` (deep) | ~2-3 min | After /ultrastart, 5+ decisions, weekly reviews |

---

## References

- [/end](end.md) — Standard close (Phase 0 source)
- [/ultrastart](ultrastart.md) — Symmetric deep boot counterpart
- [/save](save.md) — Mid-session checkpoint

---

## Tagging

`#workflow` `#automation` `#ultraend` `#system-2` `#deep-synthesis`
