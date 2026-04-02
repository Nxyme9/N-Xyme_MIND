---
name: Execution Awareness (Advisory)
description: Lightweight advisory that surfaces long-pending tasks during boot. Suggests, never blocks. User decides.
trigger: "Surfaced during /start and /end. Advisory only — user can dismiss."
created: 2026-03-15
updated: 2026-03-15
version: 2.0
---

# Protocol 528: Execution Awareness (Advisory)

> **Principle**: The system's job is to surface information. The user's job is to decide what to do with it.
> This protocol **suggests** — it never blocks, harasses, or gates session close.

## Core Mechanic

Each `@pending` item carries an implicit **session counter** derived by scanning `activeContext.md` checkpoint blocks. The system uses this count to **surface awareness** — not to pressure action.

## Awareness Levels

| Sessions Pending | Level | System Behavior |
| :--- | :--- | :--- |
| 1–3 | 🟢 Normal | Listed in `@pending` as usual |
| 4–6 | 🟡 Noted | Quietly promoted to `@seeded` for next session's Phase 4 resolution |
| 7+ | 🔵 Surfaced | Mentioned once in boot output: `ℹ️ [TASK] — pending N sessions.` |

## What This Is NOT

- ❌ **Not a hard gate.** Session close is NEVER blocked.
- ❌ **Not confrontational.** No "START or KILL" ultimatums.
- ❌ **Not a guilt mechanism.** No carrying cost calculations.
- ❌ **Not unilateral action.** The system surfaces, the user decides.

## Boot Surfacing (🔵 Level)

When a task reaches 7+ sessions, the boot output includes a single neutral line:

```text
ℹ️ Long-pending: [TASK] — N sessions. (Dismiss with "noted" or act on it.)
```

That's it. One line. No follow-up. No escalation. If the user says "noted" or simply continues with a different topic, the system respects that and moves on.

## When the User Asks

If — and only if — the user explicitly asks "what's been pending?" or "what should I work on?", the system provides the full pending list with session counts. This is a **pull** model, not push.

## Opt-In Escalation

If the user explicitly opts in (e.g., "hold me accountable on A21" or "nag me about this"), the system can:

1. Promote the task to `@seeded` with a user-requested accountability tag
2. Surface it more prominently in boot output
3. Ask about progress at session close **if the user requested it**

This is user-initiated, not system-initiated.

## Integration Points

| Workflow | Where | What |
| :--- | :--- | :--- |
| `/end` (end.md) | Step 4.5 | Scan for 7+ session items, note in `@seeded` quietly |
| `/start` (start.md) | Phase 1 | Surface 🔵 items with one neutral line |

## Design Rationale

- **Law #0 (Subjective Utility)**: The user knows their priorities better than the system. Work debt is a valid, conscious choice.
- **Advisory, not enforcement**: The system is a tool, not a manager. It surfaces data; it doesn't make demands.
- **Pull > Push**: Information is available when requested, not forced when unwanted.

## Tags

`#protocol` `#architecture` `#advisory` `#awareness` `#non-blocking`
