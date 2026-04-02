---
created: 2026-03-04
last_updated: 2026-03-04
source: "GSD (Get Shit Done) — fresh context per plan. Adapted for Athena."
---

# Protocol 513: Context Isolation (Anti-Context-Rot)

> **Purpose**: Prevent quality degradation from context window accumulation. Each execution unit runs in isolated context.  
> **Trigger**: Any multi-task execution session (development, research, analysis).  
> **Source**: Adapted from GSD's "fresh context per plan" architecture.

---

## Problem Statement

Context rot is the #1 quality killer in long agentic sessions. As the context window fills:

```
╔═══════════════════════════════════════════════════════════╗
║  CONTEXT WINDOW DEGRADATION CURVE                         ║
║                                                           ║
║  Quality                                                  ║
║  ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    ║
║  ██████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░    ║
║  ████████████████████████████████████░░░░░░░░░░░░░░░░    ║
║  ████████████████████████████████████████████░░░░░░░░    ║
║  100%      80%         60%          40%       COLLAPSE    ║
║                                                           ║
║  0%        25%         50%          75%       100%        ║
║  Context Window Fill →                                    ║
╚═══════════════════════════════════════════════════════════╝
```

Quality degrades ~linearly until 60% fill, then collapses non-linearly. The fix: **don't accumulate context across tasks**.

---

## The Protocol

### Rule 1: Isolation by Default

Each execution task gets its own context boundary. Pass only what's needed:

| What to Pass | What NOT to Pass |
|---|---|
| The specific plan/task description | Full conversation history |
| Relevant source files (max 5) | All previously viewed files |
| STATE.md (accumulated decisions) | Debug logs from prior tasks |
| Project context (PROJECT.md / design.md) | Unrelated research |

### Rule 2: Context Budget by Query Class

| Query Class | Max Context Load | Isolation Method |
|---|---|---|
| **SNIPER** (Λ < 10) | 2K tokens | Inline — no isolation needed |
| **STANDARD** (Λ 10-30) | 10K tokens | Subagent or fresh session segment |
| **ULTRA** (Λ > 30) | 30K tokens | Mandatory subagent with explicit handoff |

### Rule 3: State Handoff Protocol

Between isolated tasks, transfer state via structured artifact — never raw conversation:

```markdown
## Task Handoff (P513)

### Completed
- [x] Task 1: User model created (src/models/user.ts)
- [x] Task 2: Auth endpoint (src/api/auth/login.ts)

### State
- DB schema: PostgreSQL, Drizzle ORM
- Auth: JWT + httpOnly cookies (P512 decision #3)
- Tests: Vitest, 4 passing

### Next Task Context
- Task 3 needs: User model (task 1) + Auth endpoint (task 2)
- Files to load: src/models/user.ts, src/api/auth/login.ts
```

### Rule 4: Rot Detection & Compaction Trigger

| Signal | Action |
|---|---|
| Context window > 60% full | Trigger `context-compactor` skill |
| Task count > 5 in single session | Mandatory state snapshot + fresh context |
| Agent starts repeating itself or losing coherence | Immediate compaction + handoff |
| Session exceeds 2 hours wall-clock | Checkpoint via `/save` |

---

## Wave Execution Integration

When running multi-task plans (see `git-worktree-swarm`):

```
WAVE 1 (parallel, isolated contexts)
├── Task A: Fresh context → Execute → Commit → Output state
├── Task B: Fresh context → Execute → Commit → Output state

[State merge: A.state + B.state → combined handoff]

WAVE 2 (parallel, isolated contexts)  
├── Task C: Fresh context + A.state → Execute → Commit
├── Task D: Fresh context + B.state → Execute → Commit
```

Each task in a wave runs in full isolation. State merges between waves.

---

## Anti-Patterns

| Anti-Pattern | Correction |
|---|---|
| "Just keep going" in a long session | Checkpoint every 5 tasks or 60% context |
| Passing entire codebase as context | Pass only files the current task will touch |
| No state handoff between tasks | Always output structured state for the next task |
| Compacting too aggressively | Preserve decision history (P512 CONTEXT.md) — compact conversation, not decisions |

---

## Relationship to Existing Protocols

- **`context-compactor` skill**: P513 is *proactive* isolation; compactor is *reactive* cleanup. Use both.
- **Protocol 510 (Adaptive Depth)**: Context budget aligns with Λ scoring — SNIPER doesn't need isolation, ULTRA mandates it.
- **Protocol 43 (Micro-Commit)**: Each isolated task produces an atomic commit — natural alignment.

---

## Cross-References

- [Skill: context-compactor](../../skills/research/synthetic-parallel-reasoning/SKILL.md) — Reactive compaction
- [Protocol 510: Adaptive Depth](../architecture/510-adaptive-depth.md) — Query classification
- [Protocol 43: Micro-Commit](43-micro-commit-protocol.md) — Commit discipline
- [Skill: git-worktree-swarm](../../skills/research/synthetic-parallel-reasoning/SKILL.md) — Wave execution

## Tags

# protocol #engineering #context #isolation #anti-rot #513-context-isolation
