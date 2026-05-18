---
description: "Check loop status — iteration count, max, active state, ultrawork mode"
---

Check the current state of an active Ralph or Ultrawork loop.

Usage:
  ralph_status(session_id="...")

Returns JSON with: active, session_id, iteration, max_iterations,
completion_promise, ultrawork, verification_pending, strategy, started_at.

Reads from: data/ralph-state/active.md
