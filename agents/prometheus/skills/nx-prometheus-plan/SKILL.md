---
name: nx-prometheus-plan
description: "Prometheus Plan — Plan N workstreams."
---

# nx-prometheus-plan

Plan N workstreams. Decompose → dependency graph → parallel groups → verification gates.

## Parallel Strategy
Identify INDEPENDENT sub-tasks. Fire them simultaneously via `call_omo_agent(agent, task)`.
Collect results via `task_status(task_id)` or `bg_events(session_id)`.
Synthesize into single output.

## Serial Strategy
If sub-tasks depend on each other, chain them sequentially using `delegate_task(agent, task)`.
Pass context between steps: describe what the previous step produced.

## Always
Summarize complex work for parent session. Use `context_prune(session_id)` if context gets large.

## Verification
After all sub-tasks complete:
1. Collect all results
2. Verify each against its acceptance criteria
3. Flag any gaps or inconsistencies
4. Report final synthesis with confidence level
