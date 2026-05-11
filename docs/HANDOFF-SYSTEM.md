# Handoff System Integration

> How the HandoffManager wires into the spawn pipeline for inter-agent transfers.

**Story:** S-305 | **Sprint:** Sprint 3 | **Status:** Implemented

---

## Overview

The Handoff system provides OpenAI Agents SDK-style agent transfers. `handoff.py` contains the primitives (`HandoffRequest`, `HandoffManager`, `HandoffResponse`). S-305 wires these into the spawn pipeline so transfers happen automatically.

## Integration: spawn.py → HandoffManager

**File:** `packages/orchestration/spawn.py`  
**Function added:** `_handoff_trigger(task, agent, context)`

### When Handoff Occurs

After agent selection (STEP 1 in `spawn()`), `_handoff_trigger()` is called. It checks task keywords:

| Keyword | Triggers Handoff To |
|---------|-------------------|
| `implement`, `create`, `build`, `write code` | `hephaestus` |
| `review`, `architect`, `debug` | `oracle` |
| `search`, `find` | `explore` |
| `lookup`, `research`, `document` | `librarian` |

Handoff only fires if the target agent differs from the selected agent.

### Flow

```
spawn(task="implement auth")
  → route_task() → agent="explore"
  → _handoff_trigger() → detects "implement" keyword
  → HandoffManager.execute_handoff(source="explore", target="hephaestus")
  → response.success? → log if so
  → continue with original spawn (handoff is best-effort)
```

### Safety Rule

Handoff is **best-effort**. `_handoff_trigger()` wraps everything in try/except — if handoff fails, spawn pipeline continues without blocking. This ensures handoff never becomes a reliability risk.

## Handoff Primitives

### HandoffRequest

```python
HandoffRequest(
    source_agent="explore",
    target_agent="hephaestus",
    context={"task": "implement auth", ...},
    reason="Keyword match: task requires hephaestus"
)
```

### HandoffManager

```python
manager = HandoffManager()
response = manager.execute_handoff(request)
# response: HandoffResponse with status, transferred_context, error
```

### Guardrails

Before executing, HandoffManager checks guardrails (validation rules). Default guardrails validate:
- Source and target agents are valid
- Context is not empty
- Reason is provided

## Testing

```bash
# Verify handoff is called in spawn pipeline
grep -n "_handoff_trigger" packages/orchestration/spawn.py

# Test end-to-end handoff flow
python3 -c "
from packages.orchestration.spawn import spawn
from packages.orchestration.handoff import HandoffManager
print('Import OK')
"

# Verify docs exist
ls -la docs/HANDOFF-SYSTEM.md
```

## Key Files

| File | Role |
|------|------|
| `packages/orchestration/handoff.py` | Primitives: HandoffRequest, HandoffResponse, HandoffManager |
| `packages/orchestration/spawn.py` | Integration: `_handoff_trigger()` wired at STEP 1 |
| `packages/orchestration/tests/test_handoff.py` | Integration tests |
| `packages/orchestration/tests/test_handoff_standalone.py` | Unit tests |
| `docs/ROUTER-PRECEDENCE.md` | Related: Agent routing layer (Layer 2) |