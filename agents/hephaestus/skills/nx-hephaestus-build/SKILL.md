---
name: nx-hephaestus-build
description: "Hephaestus Build — Independent files in parallel."
---

# nx-hephaestus-build

Independent files in parallel. Decompose → identify independents → fire in parallel → merge.

## Parallel Strategy
Identify INDEPENDENT sub-tasks. Fire them simultaneously via `task(..., run_in_background=true)`.
Collect results via `session_get`. Synthesize into single output.

## Serial Strategy
If sub-tasks depend on each other, chain them sequentially. Pass context between steps.

## Always
Call `session_prune(summary="...")` after complex work.
