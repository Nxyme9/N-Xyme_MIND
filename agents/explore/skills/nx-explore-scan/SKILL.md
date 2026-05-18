---
name: nx-explore-scan
description: "Explore Scan — N patterns in parallel."
---

# nx-explore-scan

N patterns in parallel. Search multiple patterns simultaneously, aggregate results.

## Parallel Strategy
Identify INDEPENDENT sub-tasks. Fire them simultaneously via `task(..., run_in_background=true)`.
Collect results via `session_get`. Synthesize into single output.

## Serial Strategy
If sub-tasks depend on each other, chain them sequentially. Pass context between steps.

## Always
Call `session_prune(summary="...")` after complex work.
