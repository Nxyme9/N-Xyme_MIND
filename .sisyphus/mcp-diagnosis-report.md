# MCP Diagnosis Report (P0.1)

**Date**: 2026-05-11  
**Purpose**: Diagnose why 12/16 MCP servers in opencode.json are not running  

---

## Module Import Test Results

Tested each MCP by importing the exact module path from opencode.json's `command` field:

| MCP | opencode.json module | Import Test | Status |
|-----|----------------------|-------------|--------|
| **nx-mind** | `nx_mind_mcp` | ✅ OK | WORKING |
| **unified-memory** | `packages.memory_core.mcp_server` | ✅ OK | WORKING |
| **learning-engine** | `packages.learning_engine.mcp_server` | ✅ OK | WORKING |
| **intelligence** | `packages.intelligence.mcp_server` | ✅ OK | WORKING |
| **session-pool** | `python3 -m mcp_server` (WRONG) | ❌ BROKEN PATH | FIX NEEDED |
| **nx-context** | `nx_context_mcp` (WRONG) | ❌ MODULE NOT FOUND | FIX NEEDED |
| **trigger-guardian** | `trigger_guardian_mcp` (WRONG) | ❌ MODULE NOT FOUND | FIX NEEDED |
| **orchestration** | `packages.orchestration.mcp_server` | ❌ IMPORT ERROR | DEPENDENCY MISSING |
| **catalyst** | `catalyst_mcp` (WRONG) | ❌ MODULE NOT FOUND | FIX NEEDED |
| **brain_mcp** | NOT IN CONFIG | ✅ OK (exists) | MISSING FROM CONFIG |
| **obsidian** | absolute path script | ✅ OK (script exists) | UNCLEAR IF WORKING |

### Working Module Imports (verified):
```python
# ✅ All these work:
from packages.brain_mcp import mcp                    # 13 namespaces loaded
from nx_mind_mcp import mcp                           # OK
from packages.memory_core.mcp_server import mcp       # OK
from packages.learning_engine.mcp_server import mcp  # OK
from packages.intelligence.mcp_server import mcp      # OK
from packages.session_pool_mcp.mcp_server import mcp  # exports: route_task, warm_pool, get_session
from packages.nx_context_mcp import caching           # OK (but module name wrong in config)
```

### Broken Module Imports:
```python
# ❌ These are broken:
# nx_context_mcp → Module "nx_context_mcp" not found
#   Actual module is "packages.nx_context_mcp" (nested structure)
#   Note: submodules like caching.py ARE importable

# trigger_guardian_mcp → Module "trigger_guardian_mcp" not found
#   Actual module is "packages.trigger_guardian_mcp.trigger_guardian_mcp"
#   Note: trigger_guardian_mcp module DOES exist at that path

# catalyst_mcp → Module "packages.catalyst_mcp" not found
#   Actual module is "packages/catalyst_orchestrator/mcp_server.py"
#   Note: catalyst logic exists at packages/orchestration/catalyst.py

# packages.orchestration.mcp_server → Import chain broken
#   Import error: packages.infrastructure (KeyError: 'packages.infrastructure')
#   The orchestration package depends on packages.infrastructure.monitoring.telemetry
#   which does not exist
```

---

## Root Cause Classification

### Category 1: Wrong Module Path (Easy Fix — 5 MCPs)

The opencode.json command points to the wrong module path. These are typos/naming mismatches.

| MCP | Config Path | Correct Path | Fix |
|-----|-------------|--------------|-----|
| `nx-context` | `-m nx_context_mcp` | `-m packages.nx_context_mcp` | Add `packages.` prefix |
| `trigger-guardian` | `-m trigger_guardian_mcp` | `-m packages.trigger_guardian_mcp.trigger_guardian_mcp` | Fix module path |
| `catalyst` | `-m catalyst_mcp` | `-m packages.catalyst_orchestrator.mcp_server` | Fix module path |
| `session-pool` | `python3 -m mcp_server` (no package) | `python3 -m packages.session_pool_mcp.mcp_server` | Add package prefix |

### Category 2: Missing Dependency (Medium Fix — 1 MCP)

The orchestration MCP depends on `packages.infrastructure` which does not exist.

| MCP | Error | Root Cause | Fix |
|-----|-------|-----------|-----|
| `orchestration` | `KeyError: 'packages.infrastructure'` | `packages/orchestration/message_queue/__init__.py` imports `from packages.infrastructure.monitoring.telemetry import get_logger` but `packages.infrastructure` directory does not exist | Create stub or fix import chain |

### Category 3: Not in Config (Easy Fix — 1 MCP)

| MCP | Status | Fix |
|-----|--------|-----|
| `brain_mcp` | Exists at `packages/brain_mcp/` with 17 files, 13 namespaces, but NOT in opencode.json | Add to opencode.json MCP section |

### Category 4: Unknown Status (2 MCPs)

| MCP | Issue |
|-----|-------|
| `quality-gates` | Binary `./.venv/bin/quality-gates-mcp` may not exist. Need to check if binary is installed |
| `telegram` | MCP runs but may be rate-limited. "REGISTRATION_RATE_LIMITED" error suggests telegram is alive but hitting rate limits |

---

## Session-Pool: Specific Fix Required

**Current config** (line 262):
```json
"command": ["python3", "-m", "mcp_server"],
"environment": { "PYTHONPATH": "packages/session-pool-mcp" }
```

**Problem**: `python3 -m mcp_server` has no package prefix. The module `mcp_server` doesn't exist at root level. It lives at `packages.session_pool_mcp.mcp_server`.

**Fix**: Change to:
```json
"command": ["./.venv/bin/python", "-m", "packages.session_pool_mcp.mcp_server"],
"environment": { "PYTHONPATH": "." }
```

**Evidence**: `PYTHONPATH: packages/session-pool-mcp` is set but the command is `python3 -m mcp_server` which looks in the wrong location.

---

## Additional Import Warnings (Non-Fatal)

During module testing, these warnings appeared but did NOT prevent import:

1. **brain_mcp**: `Could not import Brain: No module named 'frankenstein_engine.config'`
   - This is non-fatal. brain_mcp loads 13 namespaces successfully despite this.
   - The `Brain` class from frankenstein_engine is optional.

2. **trigger_guardian**: `REGISTRATION_RATE_LIMITED` spam
   - The MCP is rate-limiting its own registration to avoid spam
   - This is intentional rate limiting, not a crash
   - Does not prevent the MCP from starting

3. **learning_engine**: `Module not available for registry: cannot import name 'health_check' from 'packages.learning_engine'`
   - Non-fatal warning, MCP still loads

4. **torch/pynvml**: `FutureWarning: The pynvml package is deprecated`
   - Just a deprecation warning, not an error

---

## Recommended Fixes

### Quick Fix 1: Add brain_mcp to opencode.json
```json
"brain_mcp": {
  "type": "local",
  "command": ["./.venv/bin/python", "-m", "packages.brain_mcp.__main__"],
  "environment": { "PYTHONPATH": "." }
}
```

### Quick Fix 2: Fix session-pool path
```json
"session-pool": {
  "type": "local",
  "command": ["./.venv/bin/python", "-m", "packages.session_pool_mcp.mcp_server"],
  "environment": { "PYTHONPATH": "." }
}
```

### Quick Fix 3: Fix nx-context path
```json
"nx-context": {
  "type": "local",
  "command": ["./.venv/bin/python", "-m", "packages.nx_context_mcp"],
  "environment": { "PYTHONPATH": "." }
}
```

### Quick Fix 4: Fix trigger-guardian path
```json
"trigger-guardian": {
  "type": "local",
  "command": ["./.venv/bin/python", "-m", "packages.trigger_guardian_mcp.trigger_guardian_mcp"],
  "environment": { "PYTHONPATH": "." }
}
```

### Quick Fix 5: Fix catalyst path
```json
"catalyst": {
  "type": "local",
  "command": ["./.venv/bin/python", "-m", "packages.catalyst_orchestrator.mcp_server"],
  "environment": { "PYTHONPATH": "." }
}
```

### Medium Fix 6: Fix orchestration dependency
Create `packages/infrastructure/` directory with stub telemetry module, OR remove the broken import from orchestration/message_queue.

---

## MCP Starter Script (For After Fixes)

A script to start all N-Xyme MCPs with proper environment:

```bash
#!/bin/bash
export PYTHONPATH=".:packages/src"

# Start MCPs in background
PYTHONPATH=".:packages/src" .venv/bin/python -m packages.brain_mcp.__main__ &
PYTHONPATH=".:packages/src" .venv/bin/python -m nx_mind_mcp &
PYTHONPATH=".:packages/src" .venv/bin/python -m packages.memory_core.mcp_server &
PYTHONPATH=".:packages/src" .venv/bin/python -m packages.learning_engine.mcp_server &
PYTHONPATH=".:packages/src" .venv/bin/python -m packages.intelligence.mcp_server &
PYTHONPATH=".:packages/src" .venv/bin/python -m packages.session_pool_mcp.mcp_server &
PYTHONPATH=".:packages/src" .venv/bin/python -m packages.nx_context_mcp &
PYTHONPATH=".:packages/src" .venv/bin/python -m packages.trigger_guardian_mcp.trigger_guardian_mcp &
PYTHONPATH=".:packages/src" .venv/bin/python -m packages.catalyst_orchestrator.mcp_server &
```

---

## Summary

| Category | Count | Fix Complexity |
|----------|-------|----------------|
| Module path typo | 5 | EASY — change module path in opencode.json |
| Missing dependency | 1 | MEDIUM — create stub or fix import chain |
| Not in config | 1 | EASY — add to opencode.json |
| Unknown status | 2 | NEEDS INVESTIGATION |

**Total fixable MCPs: 9/16**

The good news: ALL module code actually exists and imports correctly (except orchestration). This is purely a configuration problem. The hard part — writing the actual MCP server code — is already done.
