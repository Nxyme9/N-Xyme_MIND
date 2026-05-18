---
name: nx-librarian-deepdive
description: "Librarian DeepDive — 3 parallel research threads — domain + tech + market."
---

# nx-librarian-deepdive

3 parallel research threads — domain + tech + market. Fire 3 explore/librarian calls, synthesize results.

## Parallel Strategy
Identify INDEPENDENT sub-tasks. Fire them simultaneously via `task(..., run_in_background=true)`.
Collect results via `session_get`. Synthesize into single output.

## Serial Strategy
If sub-tasks depend on each other, chain them sequentially. Pass context between steps.

## Always
Call `session_prune(summary="...")` after complex work.
