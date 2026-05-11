---
epic_id: E-104
title: "Agent System Polish"
priority: P1
stories: 4
points: 8
created: 2026-05-11
sprint: sprint-3
status: pending
bmad_agents:
  lead: Amelia (dev)
---

# Epic E-104: Agent System Polish

**Priority:** P1 | **Stories:** 4 | **Points:** 8 | **Risk:** LOW

## Epic Goal

Polish agent system internals: add persistence where missing, fix concurrency issues, deduplicate code, and consolidate configuration.

## Rationale

- Agent System scored 80/100 (B+)
- Q-Learning in-memory loss is a real usability issue
- Session state file corruption from concurrent writes is a data integrity risk
- Duplicate route definitions are maintenance burden

## Success Criteria

1. Q-Learning weights persist across restarts
2. Session state writes are protected with file locking
3. All routes defined once (no duplicates)
4. Single canonical env.sh for all scripts

---

## Story S-401: Q-Learning Persistence

**Story ID:** S-401 | **Points:** 2 | **Priority:** MEDIUM | **TDD:** Test-First | **DEPENDS:** None

### What
Q-Learning in-memory only. All learned routing lost on service restart. Cold-start every time. Add disk persistence.

### Files
- `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/nx_routing.py`
- `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/learning_engine/`
- `data/qlearning/` (create for persistence)

### Root Cause
`record_outcome()` updates in-memory Q-table only. No save to disk. No load on startup.

### Persistence Strategy Options
1. **SQLite**: Structured queries, good for large state
2. **JSON**: Simple, human-readable, fine for small state
3. **SQLite JSON columns**: Hybrid approach

### Acceptance Criteria
- AC-401.1: Q-Learning weights saved to disk on `record_outcome()` (debounced, not every call)
- AC-401.2: Q-Learning weights loaded from disk on startup
- AC-401.3: Persistence verified across process restarts
- AC-401.4: Weights file is append-safe (use temp file + rename)
- AC-401.5: Handles missing/corrupted weight file gracefully (reinitialize)

### QA Commands
```bash
# Test persistence across restarts
python3 -c "
from nx_routing import AdaptiveRouter
r = AdaptiveRouter()
r.record_outcome('test_task', 'openrouter', True, 100)
print('Weight after record:', r.get_weight('test_task', 'openrouter'))
"
# Restart Python
python3 -c "
from nx_routing import AdaptiveRouter
r = AdaptiveRouter()
print('Weight after restart:', r.get_weight('test_task', 'openrouter'))
print('Persistence: SUCCESS' if r.get_weight('test_task', 'openrouter') else 'FAIL')
"

# Verify file exists
ls -la data/qlearning/
```

### Implementation Pattern
```python
import json
from pathlib import Path
from filelock import FileLock  # Or fcntl.flock

class QLearningPersistence:
    def __init__(self, path: str, save_interval: int = 10):
        self.path = Path(path)
        self.save_interval = save_interval
        self._dirty_count = 0

    def record_outcome(self, task: str, agent: str, success: bool, latency_ms: int):
        # Update in-memory
        self._update_q_table(task, agent, success, latency_ms)
        self._dirty_count += 1

        # Debounced save
        if self._dirty_count >= self.save_interval:
            self.save()

    def save(self):
        # Atomic write: temp file + rename
        temp = self.path.with_suffix('.tmp')
        with open(temp, 'w') as f:
            json.dump(self.q_table, f)
        temp.rename(self.path)
        self._dirty_count = 0

    def load(self):
        if self.path.exists():
            with open(self.path) as f:
                self.q_table = json.load(f)
```

### Atomic Commit
```
feat(qlearning): persist routing weights to disk
```

---

## Story S-402: Session State File Locking

**Story ID:** S-402 | **Points:** 2 | **Priority:** MEDIUM | **TDD:** Test-First | **DEPENDS:** None

### What
.sisyphus/session-state.json has no file locking. Concurrent writes from multiple tabs = corruption risk.

### Files
- `.sisyphus/session-state.json`
- `src/omo_orchestrator/session_manager.py` (or similar)

### Root Cause
Multiple OpenCode instances (tabs) write to the same session-state.json without coordination.

### Acceptance Criteria
- AC-402.1: `fcntl.flock()` (Unix) or `msvcrt.locking()` (Windows) used for file locking
- AC-402.2: Lock acquired before read, held during write, released after
- AC-402.3: Concurrent write test passes — no corrupted state
- AC-402.4: Lock timeout prevents deadlocks (e.g., 5 second timeout)
- AC-402.5: Graceful handling if lock cannot be acquired

### QA Commands
```bash
# Test concurrent writes
python3 -c "
import concurrent.futures
from src.omo_orchestrator.session_manager import SessionManager

def write_session(i):
    sm = SessionManager()
    sm.update_session({'iteration': i})
    return i

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(write_session, i) for i in range(100)]
    results = [f.result() for f in futures]

# Check for corruption
import json
with open('.sisyphus/session-state.json') as f:
    state = json.load(f)
print(f'Final state: {state}')
print('No corruption: SUCCESS' if 'iteration' in state else 'FAIL')
"
```

### Implementation Pattern
```python
import fcntl
import contextlib

@contextlib.contextmanager
def file_lock(path: str, timeout: float = 5.0):
    lock_path = f'{path}.lock'
    with open(lock_path, 'w') as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

class SessionManager:
    def update_session(self, updates: dict):
        with file_lock(self.state_file):
            with open(self.state_file, 'r+') as f:
                state = json.load(f)
                state.update(updates)
                f.seek(0)
                json.dump(state, f)
                f.truncate()
```

### Atomic Commit
```
fix(session): add file locking for concurrent writes
```

---

## Story S-403: brain_mcp Duplicate Route Deduplication

**Story ID:** S-403 | **Points:** 2 | **Priority:** MEDIUM | **TDD:** Test-First | **DEPENDS:** None

### What
brain_mcp/__init__.py has 3 routes defined twice. Deduplicate.

### File
`/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/brain_mcp/__init__.py` (lines ~575-636)

### Root Cause
Route definitions duplicated during merge or copy-paste error.

### Acceptance Criteria
- AC-403.1: Each route defined exactly once (no duplicates)
- AC-403.2: All routes functional — can be called via MCP protocol
- AC-403.3: No broken references after deduplication
- AC-403.4: Functional test passes for all routes

### QA Commands
```bash
# Check for duplicates
python3 -c "
from brain_mcp import app  # MCP app
routes = [r.path for r in app.routes]
print(f'Total routes: {len(routes)}')
print(f'Unique routes: {len(set(routes))}')
if len(routes) != len(set(routes)):
    from collections import Counter
    dupes = [r for r, c in Counter(routes).items() if c > 1]
    print(f'Duplicates: {dupes}')
    raise ValueError(f'Duplicate routes found: {dupes}')
print('No duplicates: SUCCESS')
"

# Verify all routes work
python3 -m brain_mcp  # Should start without errors
```

### Atomic Commit
```
fix(brain_mcp): deduplicate route definitions
```

---

## Story S-404: env.sh Consolidation

**Story ID:** S-404 | **Points:** 2 | **Priority:** HIGH | **TDD:** Verification | **DEPENDS:** None

### What
Two conflicting env.sh files (venvs/athena vs .venv). Consolidate into single canonical file.

### Files
- `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/env.sh` (root)
- `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/bin/env.sh` (bin)

### Root Cause
`env.sh` in root points to `venvs/athena`. `bin/env.sh` points to `.venv`. Scripts source different files.

### Acceptance Criteria
- AC-404.1: Single canonical `env.sh` at project root
- AC-404.2: `bin/env.sh` either removed or symlinked to root
- AC-404.3: All scripts source the same `env.sh`
- AC-404.4: `source env.sh` works from any directory
- AC-404.5: VENV_PATH set correctly in canonical file

### QA Commands
```bash
# Check for conflicts
grep -r "VENV_PATH" env.sh bin/env.sh
cat env.sh | grep VENV_PATH
cat bin/env.sh 2>/dev/null | grep VENV_PATH || echo "bin/env.sh does not exist"

# Verify all scripts source correct file
grep -r "source.*env.sh" --include="*.sh" .
grep -r "\. .*env.sh" --include="*.sh" . | grep -v "Binary"

# Test sourcing
cd /tmp && source /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/env.sh && echo "VENV: $VIRTUAL_ENV"
```

### Atomic Commit
```
refactor(env): consolidate duplicate env.sh files
```

---

## Quality Gates (All Stories)

| Gate | Command | Must Pass |
|------|---------|-----------|
| Typecheck | `mypy src/` | Zero errors |
| Lint | `ruff check src/` | Zero errors |
| Format | `ruff format --check src/` | Zero diffs |
| Tests | `pytest tests/ -v` | All pass |
| Secrets | `gitleaks detect --verbose` | Zero leaks |

---

## Timeline & Parallel Execution

| Wave | Day | Stories | Parallel |
|------|-----|---------|----------|
| Wave 1 | Day 3-6 | S-401, S-402, S-403, S-404 | ALL PARALLEL |

**Estimated Speedup:** 60% faster than sequential (1 wave vs 4 sequential)

---

## Definition of Done

All of the following must be true for this epic to be DONE:

1. Q-Learning weights persist across restarts (verified by restart test)
2. Concurrent session writes don't corrupt state
3. Each brain_mcp route defined exactly once
4. Single canonical env.sh sourced by all scripts
5. All 4 commits merged with passing CI
6. Agent System audit score improves from **80/100 to 88+/100**