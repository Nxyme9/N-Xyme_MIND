---
description: "Start a persistent iterative loop — task, max_iterations, promise, ultrawork"
---

Starts a persistent iterative refinement loop using frontmatter .md state (survives restarts).

Usage:
  ralph_start(session_id="...", task="...", max_iterations=5, promise="DONE", ultrawork=false)

Parameters:
  - session_id: Target session ID
  - task: Task description for the loop
  - max_iterations: Max iterations (0 or omit for unbounded/ultrawork)
  - promise: Completion promise tag content (default: "DONE")
  - ultrawork: Enable Ultrawork mode with Oracle verification gate

Ultrawork mode:
  When ultrawork=true, detecting `<promise>DONE</promise>` transitions to verification
  phase. The model must call Oracle via delegate_task and Oracle must verify before
  the loop completes. Output `<promise>VERIFIED</promise>` only after Oracle confirms.

State file: data/ralph-state/active.md (frontmatter format)
