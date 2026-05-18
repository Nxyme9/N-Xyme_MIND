---
description: "Start Ultrawork loop — DONE → Oracle verification → VERIFIED required"
---

Starts an Ultrawork loop (Oracles Must Approve / OMO-style verified refinement).

Usage:
  ulw_start(session_id="...", task="...", max_iterations=0, promise="DONE")

Parameters:
  - session_id: Target session ID
  - task: Task description
  - max_iterations: 0 = unbounded (default). Set >0 for bounded ultrawork.
  - promise: Completion promise tag (default: DONE)

Ultrawork Flow:
  1. Loop runs until model outputs `<promise>DONE</promise>`
  2. Plugin transitions to verification phase:
     - completion_promise changes to "VERIFIED"
     - Inject Oracle verification prompt
  3. Model must delegate_task to Oracle agent for review
  4. If Oracle confirms → output `<promise>VERIFIED</promise>` → loop complete
  5. If Oracle rejects → verification failure → loop continues

State: data/ralph-state/active.md (frontmatter .md)
