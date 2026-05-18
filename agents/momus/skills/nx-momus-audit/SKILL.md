---
name: nx-momus-audit
description: "Momus Audit — 5 lenses in parallel."
---

# nx-momus-audit

5 lenses in parallel. Check clarity/completeness/verifiability/consistency/feasibility simultaneously.

## Parallel Strategy
Identify INDEPENDENT sub-tasks. Fire them simultaneously via `task(..., run_in_background=true)`.
Collect results via `session_get`. Synthesize into single output.

## Serial Strategy
If sub-tasks depend on each other, chain them sequentially. Pass context between steps.

## Always
Call `session_prune(summary="...")` after complex work.
