---
name: nx-kairos-therapy
description: "Kairos Therapy — Techniques in parallel, session serial."
---

# nx-kairos-therapy

Techniques in parallel, session serial. Prepare worksheet+grounding+assessment simultaneously.

## Parallel Strategy
Identify INDEPENDENT sub-tasks. Fire them simultaneously via `task(..., run_in_background=true)`.
Collect results via `session_get`. Synthesize into single output.

## Serial Strategy
If sub-tasks depend on each other, chain them sequentially. Pass context between steps.

## Always
Call `session_prune(summary="...")` after complex work.
