# Rule 16: Background Delegation (Don't Close Parent Sessions)

## The Problem

When Atlas delegates to Sisyphus workers, Atlas's window closes and stops working.

**Root cause**: Synchronous delegation ends the parent session.

```
WRONG (closes parent):
Atlas → delegates to Sisyphus → Atlas window closes → manual restart needed

RIGHT (keeps parent open):
Atlas → launches Sisyphus in background → Atlas continues working → Sisyphus completes → Atlas gets result
```

## The Solution: Background Tasks

Use `run_in_background=true` for ALL delegation. This keeps the parent session alive.

### Before (WRONG — closes parent)
```python
# This CLOSES Atlas's window
task(
    session_id="ses_atlas",
    subagent_type="Sisyphus",
    prompt="Execute task X",
    run_in_background=False  # SYNCHRONOUS — blocks and closes parent
)
```

### After (RIGHT — keeps parent open)
```python
# This KEEPS Atlas's window open
task_id = task(
    session_id="ses_atlas",
    subagent_type="Sisyphus",
    prompt="Execute task X",
    run_in_background=True  # ASYNCHRONOUS — parent continues
)

# Later, Atlas checks results
result = background_output(task_id=task_id)
```

## The Delegation Protocol

```
Atlas (parent session)
├─ Reads TODOs from global memory
├─ For EACH TODO:
│   ├─ Launch Sisyphus worker in BACKGROUND (run_in_background=true)
│   ├─ Get task_id back immediately
│   ├─ Continue to next TODO (don't wait)
│   ├─ Later: check background_output(task_id) for results
│   └─ Mark complete in global memory
└─ Atlas window STAYS OPEN throughout
```

## Implementation

### Atlas Delegation Pattern
```python
# Atlas reads TODOs
todos = read_global_todos()

# Launch workers in background (don't wait)
task_ids = []
for todo in todos[:5]:  # 5 parallel workers
    task_id = task(
        session_id="ses_atlas",
        subagent_type="sisyphus-junior",
        prompt=f"Execute: {todo['task']}",
        run_in_background=True  # KEY: keeps Atlas alive
    )
    task_ids.append(task_id)

# Atlas continues working while workers run
# Check results later
for task_id in task_ids:
    result = background_output(task_id=task_id)
    if result.status == "completed":
        mark_todo_complete(result.todo_id)
```

### Sisyphus Worker Pattern
```python
# Worker runs in background
# When done, result is available via background_output()
# Parent (Atlas) doesn't close
```

## The Rule

> **ALWAYS use run_in_background=true for delegation. NEVER use synchronous delegation (run_in_background=false) when delegating from a primary agent. This keeps the parent session alive and the window open.**
