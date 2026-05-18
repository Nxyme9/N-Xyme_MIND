---
name: nx-orchestration-spawn
description: "Spawn agent tasks via N-Xyme orchestration system."
---

# nx-orchestration-spawn

## Purpose
Spawn agent tasks via N-Xyme orchestration system.

## Tools
- `spawn(agent, task)` - spawn task, returns immediately
- `task_status(task_id)` - check result

## Usage
```python
spawn(agent="hephaestus", task="fix the login bug")
task_status(task_id="task_xxx")
```

## Requirements
- orchestration MCP must be loaded
- Python packages.orchestration module available
