---
name: nx-oracle-consult
description: "Oracle Consult — Analyze 3 subsystems concurrently."
---

# nx-oracle-consult

Analyze 3 subsystems concurrently. Read → evaluate → tradeoffs → recommend.

## Parallel Strategy
Identify INDEPENDENT sub-tasks. Fire them simultaneously via `task(..., run_in_background=true)`.
Collect results via `session_get`. Synthesize into single output.

## Serial Strategy
If sub-tasks depend on each other, chain them sequentially. Pass context between steps.

## Always
Call `session_prune(summary="...")` after complex work.
