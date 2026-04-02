---
description: Close session and update System Prompt files with new insights (lightweight)
created: 2025-12-09
last_updated: 2026-03-10
model: default
temperature: 0.5
tools:
  read: true
  write: true
  bash: true
  search: true
---

# /end — Session Close Script (GTO v3)

> **Latency Profile**: ULTRA-LOW (micro) / LOW (full)
> **Core Principle**: "Fast close. Match effort to session weight."

## Step 0: Session Classification Gate

Before any synthesis, classify the session:

| Session Type | Criteria | Path |
|:---|:---|:---|
| **MICRO** | ≤ 3 turns AND no new decisions/learnings/architecture changes | → Phase 1A (one-liner close) |
| **FULL** | Everything else | → Phase 1B (full synthesis) |

> **Default**: FULL. Only classify MICRO when **certain** the session was trivial.

---

## Phase 1A: Micro-Session Close (~100 tokens, ~5s)

1. **Append** to `activeContext.md`:

```markdown
## Session [DATE]-session-[N] ([Time of Day]): [ONE-LINE TOPIC]

- **[SNIPER/Micro]**: [One sentence summary of what happened].

## Session Closed

**Status**: ✅ Closed
**Time**: [HH:MM SGT]

[[ S__ |
@focus: Clear
@status: Paused — Session closed

@decided: No new decisions.
@pending: [Copy from previous checkpoint]
@seeded: [Suggested next session focus — what naturally comes next]

!checkpoint ]]
```

1. **Run micro shutdown**:

// turbo

```bash
python3 .agent/scripts/shutdown.py --micro
```

**Done.** No further steps.

---

## Phase 1B: Full Session Close

> [!IMPORTANT]
> **Dual-Write Architecture**: Session state is stored in two complementary files:
>
> - **`session_logs/`** → The archive. `shutdown.py` compiles these for learnings propagation, YAML metadata, and compliance.
> - **`activeContext.md`** → The running state. `/start` reads this for fast boot. Only the checkpoint block goes here.
>
> Both must be written. They serve different consumers.

### 1. Write Session Log File

Create `.context/memories/session_logs/[DATE]-session-[N].md` with:

```markdown
# Session Log: [DATE] (Session [N])

**Date**: [DATE]
**Time**: [START] - [END]
**Focus**: [Primary topic]

---

## 1. Agenda (The Plan)

- [x] [Task 1]
- [x] [Task 2]

---

## 2. Key Decisions & Insights (The Minutes)

* **Decision**: [What was decided and why]
- **Insight**: [What was learned]

---

## 3. Action Items (Next Steps)

| Action | Owner | Status |
|--------|-------|--------|
| [Next step] | Winston | Pending |

---

## Session Learnings

- [S] [System learning — propagated to SYSTEM_LEARNINGS.md by shutdown.py]
- [U] [User learning — propagated to USER_PROFILE.yaml by shutdown.py]

## Session Closed

**Status**: ✅ Closed
**Time**: [HH:MM SGT]

[[ S__ |
@focus: [Current Task/Project]
@status: [Active/Paused/Closed]

@decided: [Key Decision A], [Key Decision B]
@pending: [Next Step X], [Next Step Y]
@seeded: [Suggested next session focus — what naturally comes next]

!checkpoint ]]
```

> **`[S]` and `[U]` markers matter.** `shutdown.py` uses `extract_learnings()` to find these markers and propagate learnings to the correct files. Tag every learning.

### 2. Append Checkpoint to `activeContext.md`

Append **only** the summary block and checkpoint — not the full session log:

```markdown
## Session [DATE]-session-[N] ([Time of Day]): [TOPIC]

- [Summary of key decisions and learnings, 2-4 bullets max]

## Session Closed

**Status**: ✅ Closed
**Time**: [HH:MM SGT]

## Session Learnings

- [Learning 1]
- [Learning 2]

[[ S__ |
@focus: [Current Task/Project]
@status: [Active/Paused]

@decided: [Key Decision A], [Key Decision B]
@pending: [Next Step X], [Next Step Y]
@seeded: [Suggested next session focus — what naturally comes next]

!checkpoint ]]
```

### 3. Canonical Check (Conditional)

**Gate**: Did `@decided` in this session involve architecture changes, new protocols, new axioms, or constraint modifications?

- **If NO**: Skip entirely. Most sessions don't touch canonical rules.
- **If YES**: Load `.context/CANONICAL.md`. Ask: "Does any session learning contradict a fact here?" If yes → update immediately.

### 4. Decision Log Gate

Update `decisionLog.md` **only** if a decision involved:

- Money (pricing, spending, investment)
- Irreversible actions (publishing, deleting, committing to a client)
- Architecture changes (new protocols, cluster rewiring, skill additions)

All other decisions stay in `activeContext.md` only.

### 4.5. Execution Awareness (Protocol 528 — Advisory)

Before writing the `@pending` line in the checkpoint block:

1. **Scan** previous `[[ S__ ]]` checkpoint blocks in `activeContext.md`
2. For each item about to be written to `@pending`, count its consecutive appearances
3. If any item has been pending **7+ sessions**: quietly promote it to `@seeded` for next session's Phase 4

> This step is **advisory only** — it never blocks session close.
> See [Protocol 528](../../.agent/skills/protocols/architecture/528-execution-enforcement.md).

---

### 5. Update Project Switchboard (MANDATORY)

> [!CAUTION]
> **This step is NOT optional.** Every session close MUST review `PROJECTS.md` — even SNIPER sessions.
> Stale project state (e.g., completed items still marked 🔴 TODAY) causes compounding confusion across sessions.

**5a. Review & Update `.context/PROJECTS.md`:**

- **Advance phase** (e.g., ▓░░░░ → ▓▓░░░) if a milestone was hit
- **Update next action** to reflect current atomic step
- **Adjust urgency** if deadlines shifted
- **Close projects** → move to Completed table with date + outcome
- **Update `Last triaged` timestamp** to current datetime

**5b. Reconcile `@pending` in Checkpoint:**

Before writing the `@pending` line in the checkpoint block:

1. Load the previous checkpoint's `@pending` list
2. Cross-reference each item against current session decisions and `PROJECTS.md`
3. **Remove** any item that is now completed or moved to Completed table
4. **Add** any new pending items from this session
5. Write the reconciled list — never blindly copy-paste from the previous checkpoint

### 6. Context Hygiene Gate

**Gate**: Is `activeContext.md` > 1000 lines?

- **If NO**: Skip.
- **If YES**: Move all fully-closed session blocks (from `## Session` to `!checkpoint ]]`) older than the most recent 5 sessions into a one-liner summary in the `## Compacted Archive` section. Delete the full blocks.

> Format: `- **[Date] – [Topic]**: [One-line summary of decisions/learnings].`
> Rationale: Keeps `activeContext.md` under the boot-weight ceiling. `/start` surgical load stays fast.

---

## Phase 2: Shutdown Orchestrator

// turbo

```bash
python3 .agent/scripts/shutdown.py
```

**What it does** (single call, no subprocesses):

1. Session compilation (YAML metadata, Λ stats, R__ block, learnings propagation)
2. Harvest check (§0.7 enforcement — background)
3. Git commit & push (5s timeout, push is non-fatal)
4. Compliance report + reset
5. Pre-compaction state flush (OpenClaw pattern)
6. Auto-hygiene (background — `compress_sessions.py`)
7. Protocol heat map update (background, non-fatal — `protocol_heatmap.py --update`)

### Failure Recovery

| Failure | Action |
|:---|:---|
| `shutdown.py` errors on placeholders | Go back to Phase 1B Step 1. Synthesize properly. |
| Git push fails | Non-fatal. Session is still closed. Push manually or next session. |
| Script crashes / timeout | Fallback: `git add -A && git commit -m "session close" --no-verify 2>/dev/null; true`. Session is closed. File a reflexion. |
| 2 consecutive failures | **Circuit Breaker (P514)**. Stop. Report root cause. Do NOT retry. |

**Output**: "✅ Session closed. Time: [HH:MM SGT]"

> [!CAUTION]
> **Do NOT run `/push-public` inside `/end`.** Bilateral repo sync is a separate workflow. If `shutdown.py` attempts to push to `Athena-Public`, that is a bug.

---

## Quick Reference

| Session Type | Latency | Tokens |
|:---|:---|:---|
| MICRO (≤3 turns, no learnings) | ~5s | ~100 |
| FULL (everything else) | ~30-60s | ~600 |

---

## References

- [/save](save.md) — Mid-session checkpoint
- [/ultraend](ultraend.md) — Deep close (System-2 counterpart)

---

## Tagging

`#workflow` `#automation` `#end` `#lightweight`
