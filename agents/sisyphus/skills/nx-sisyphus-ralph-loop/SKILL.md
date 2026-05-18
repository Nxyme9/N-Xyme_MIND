---
name: nx-sisyphus-ralph-loop
description: "Ralph Loop protocol — iterative self-improvement loop. Use for coding, refactoring, debugging, or any multi-step task."
---

## ACTIVATION
Call `ralph_start(session_id, task, promise="DONE", max_iterations=N)` to begin.

## ITERATION
Call `ralph_iterate(session_id, loop_id, output)` after each step.
The loop continues until output contains the promise or max iterations reached.

## MONITOR
Call `ralph_status(session_id, loop_id)` to check progress.
Returns `it`, `max`, `active`, `estimated_time`.

## COMPLETION
Loop ends when promise is fulfilled ("DONE" found in output) or max iterations hit.
Call `ralph_cancel(session_id, loop_id)` to abort early.

## BEST PRACTICE
- Set promise to the completion condition: "TESTS_PASS", "ALL_DONE", etc.
- Set max_iterations to prevent infinite loops
- Check iteration count: loop stops automatically at max

## AGENTS
- Preferred by: Sisyphus (orchestrator), Prometheus (planner)
- Also used by: Hephaestus (implementation), Momus (review cycles)
