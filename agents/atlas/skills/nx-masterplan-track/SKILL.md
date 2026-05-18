---
name: nx-masterplan-track
description: "Atlas — Track progress across parallel workstreams."
---

# nx-masterplan-track

Track progress, dependencies, and blockers across multiple workstreams.

## Strategy
1. Check status of all ongoing tasks via `ralph_status`
2. Update dependency graph — what's blocking what
3. Surface completed items, stalled items, blockers
4. Recommend next actions for each workstream

## Always
Call `session_prune(summary="...")` after complex tracking work.
