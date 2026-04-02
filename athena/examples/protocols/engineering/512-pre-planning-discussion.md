---
created: 2026-03-04
last_updated: 2026-03-04
source: "GSD (Get Shit Done) — discuss-phase pattern. Adapted for Athena."
---

# Protocol 512: Pre-Planning Discussion (Gray Area Resolution)

> **Purpose**: Resolve ambiguity *before* specification. Capture user preferences on gray areas so the planner doesn't guess wrong.  
> **Trigger**: Any task entering `spec-driven-dev` (P107). Fires before interrogation.  
> **Source**: Adapted from GSD's `discuss-phase` command (24K⭐ spec-driven system).

---

## Problem Statement

LLMs generate plausible-looking plans that miss user intent on *gray areas* — decisions where multiple valid approaches exist. The spec-driven-dev skill (P107) interrogates for edge cases but doesn't separate **preference capture** from **formal specification**. Result: agents guess, users spend 67% of time reviewing and fixing.

---

## The Protocol

### Step 1: Gray Area Detection

Analyze the task scope. Identify *decisions the user hasn't explicitly made* by category:

| Category | Gray Area Examples |
|---|---|
| **UI/Visual** | Layout style, density, interaction patterns, empty states, responsive breakpoints |
| **API/Backend** | Response format, error handling, auth flow, rate limiting, pagination |
| **Data** | Schema design, validation rules, migration strategy, caching |
| **Content** | Tone, structure, depth, naming conventions |
| **Architecture** | Monolith vs modular, state management, dependency choices |
| **Scope** | v1 vs v2 cutoff, "nice-to-have" vs "must-have" boundary |

### Step 2: Present Decision Points

For each gray area, present as a **numbered decision point** with:

```
DECISION [N]: [Gray Area Name]
  Context:  [Why this matters]
  Default:  [What the agent would assume]
  Options:  [A] Default | [B] Alternative | [C] Alternative
```

> **Rule**: Always provide a sensible default. User can accept by just saying "defaults are fine" for speed.

### Step 3: Capture Decisions

Record resolutions. Output: **CONTEXT.md** (or equivalent inline context block).

```markdown
## Discussion Decisions (P512)

| # | Decision | Resolution | Rationale |
|---|----------|------------|-----------|
| 1 | Layout style | Card grid | User preference |
| 2 | Error handling | Toast notifications | Default accepted |
| 3 | Auth flow | JWT + httpOnly cookies | Security requirement |
```

### Step 4: Feed Forward

The CONTEXT.md feeds directly into:

- **Research** (knows what patterns to investigate)
- **Spec drafting** (knows which decisions are locked)
- **Execution** (no guessing on resolved gray areas)

---

## Integration

```
[User Request] → P512 (Discuss) → P107 (Spec) → P500 (Solve) → Execution
                    ↑                                              
              "What do you prefer?"                           
              NOT "What do you want?"                         
```

P512 asks *preference* questions (layout, style, approach).  
P107 asks *requirement* questions (edge cases, constraints, validation).  
Different cognitive modes. Don't collapse them.

---

## Anti-Patterns

| Anti-Pattern | Correction |
|---|---|
| Skipping discussion on "obvious" tasks | Even simple tasks have 2-3 gray areas. 30 seconds of discussion saves 30 minutes of rework. |
| Asking too many questions | Cap at **5-7 decision points** per phase. Group related decisions. |
| Not providing defaults | Always suggest a default. Reduces user cognitive load. |
| Re-discussing resolved decisions | Once captured in CONTEXT.md, decisions are **locked** unless user reopens. |

---

## Cross-References

- [Protocol 107: Spec-Driven Development](../coding/107-spec-driven-development.md) — Step 2 in the chain
- [Protocol 500: GTO Problem Solver](../decision/500-gto-problem-solver.md) — Phase 0 classification
- [Skill: spec-driven-dev](../../skills/research/synthetic-parallel-reasoning/SKILL.md) — Execution wrapper

## Tags

# protocol #engineering #planning #discussion #gray-areas #512-pre-planning-discussion
