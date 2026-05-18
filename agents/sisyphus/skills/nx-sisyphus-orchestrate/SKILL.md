---
name: nx-sisyphus-orchestrate
description: "Orchestrate — analyze task, decide parallel vs serial, delegate to specialists, collect results, verify. For COMPLEX tasks only."
---

# Sisyphus Orchestrate

**Call this when the task has 3+ steps, needs multiple specialists, or scope is unclear.**

## Phase 0: Intent Gate
Classify as: [quick] respond directly | [deep] analyze | [delegate] → specialist | [complex] run this skill

## Phase 1: Decompose
Break the task into independent sub-tasks. Identify dependencies between them.

## Phase 2: Build Execution Plan
- **Independent tasks** → `[P]` run in parallel via `task(agent, run_in_background=true)`
- **Dependent tasks** → serial chain, pass context via `session_set`

| Group | Agent | Task | Dependencies | Expected |
|-------|-------|------|-------------|----------|
| [P] | oracle | architecture review | none | 2min |
| [P] | explore | codebase search | none | 1min |
| — | hephaestus | implement | oracle + explore | 5min |
| — | momus | review | hephaestus | 2min |

## Phase 3: Execute
- Fire all `[P]` groups simultaneously
- Collect results via `ralph_status` or `session_get`
- Feed results into next serial step

## Phase 4: Synthesize
Combine all outputs into a single coherent response. Note what each agent contributed.

## Phase 5: PRUNE
Call `session_prune(summary="...")` to save context before compaction.
