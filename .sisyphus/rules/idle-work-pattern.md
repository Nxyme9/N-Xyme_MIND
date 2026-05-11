# Rule 12: Idle Work Pattern — Never Stop Thinking

## The Problem

When orchestrator says "waiting for completion," it stops. The system notifies when tasks complete, but the orchestrator has already ended its turn. The user has to prompt again to continue.

## The Root Cause

Treating background tasks like synchronous calls:
```
❌ Launch agents → Say "waiting" → Stop → User prompts → Continue
```

## The Solution

Background tasks are ASYNCHRONOUS. Always have idle work ready:
```
✅ Launch agents → Do non-dependent work → System notifies → Process results → Continue
```

## Idle Work Priority

| Priority | Work Type | Example |
|----------|-----------|---------|
| 1 | Process completed tasks | Check `background_output()` |
| 2 | Do non-dependent work | Documentation, planning, verification |
| 3 | Prepare for next wave | Read files, gather context |
| 4 | Optimize current state | Refactor, test, verify |

## Implementation

### Pattern 1: Immediate Continuation
After launching tasks, immediately check if any are done:
```python
# Launch 4 agents
task(agent="A", ...)
task(agent="B", ...)
task(agent="C", ...)
task(agent="D", ...)

# Immediately check for completions
for task_id in [bg_a, bg_b, bg_c, bg_d]:
    result = background_output(task_id=task_id)
    if result.status == "completed":
        process(result)
```

### Pattern 2: Non-Blocking Work
While waiting, do work that doesn't depend on background tasks:
- Create directory structure
- Write documentation
- Prepare config files
- Verify existing systems

### Pattern 3: Pipeline Preparation
While waiting for Wave 1, prepare for Wave 2:
- Read integration requirements
- Gather API documentation
- Prepare test scenarios

## The Rule

> **Never say "waiting for completion." Always have idle work ready. Process completed tasks immediately when notified. Keep the pipeline flowing.**

## Anti-Patterns

❌ **Don't**: Say "waiting for completion" and stop
❌ **Don't**: Wait for ALL tasks before processing ANY
❌ **Don't**: Block on one task while others are ready

✅ **Do**: Process tasks as they complete
✅ **Do**: Do non-dependent work while waiting
✅ **Do**: Keep the pipeline flowing

## Example: Correct Idle Work

```
[Launch 4 agents for Wave 1]
[While agents run:]
  → Create directory structure
  → Write README
  → Prepare config files
  → Check for completed agents
  → Process any that are done
  → Continue until all complete
```

## Example: Incorrect Pattern

```
[Launch 4 agents for Wave 1]
[Say "waiting for completion"]
[Stop]
[User has to prompt again]
[Continue]
```
