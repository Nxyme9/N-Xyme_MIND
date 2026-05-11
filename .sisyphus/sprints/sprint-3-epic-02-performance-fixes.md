---
epic_id: E-102
title: "Performance Fixes"
priority: P1
stories: 5
points: 13
created: 2026-05-11
sprint: sprint-3
status: pending
bmad_agents:
  lead: Amelia (dev)
  architect: Winston (S-202 architecture review)
---

# Epic E-102: Performance Fixes

**Priority:** P1 | **Stories:** 5 | **Points:** 13 | **Risk:** MEDIUM

## Epic Goal

Eliminate performance anti-patterns that cause unnecessary resource consumption and latency. Focus on connection pooling, async correctness, and model instance reuse.

## Rationale

- Performance scored 92/100 (A) — the GGUF system itself is excellent
- 5 anti-patterns identified that reduce efficiency
- skill_loader async issue is P0-adjacent (silent failures, not just performance)
- DirectLlamaClient per-request instantiation is the highest-impact fix

## Success Criteria

1. All async handlers properly awaited (not returning coroutine objects)
2. Single Llama() instance reused across all requests
3. Connection pools utilized for HTTP calls
4. No blocking sleep calls in async contexts
5. No orphan threads in async code paths

---

## Story S-201: skill_loader Async Handlers Await Fix

**Story ID:** S-201 | **Points:** 3 | **Priority:** HIGH | **TDD:** Test-First | **DEPENDS:** None | **BLOCKS:** S-203, S-204, S-205, S-305

### What
Fix async handlers (`_batch_handler`, `_remember_handler`, etc.) called without `await`. Coroutines never execute — silent failure.

### File
`/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nxyme_core/skill_loader.py`

### Root Cause
`execute_skill` is not `async def`. Async handlers are called as `self.handler(**kwargs)` where `handler` may be a coroutine. Without `await`, the coroutine object is returned but never executed.

### Acceptance Criteria
- AC-201.1: `execute_skill` becomes `async def`
- AC-201.2: Async handlers detected via `asyncio.iscoroutinefunction()` or `inspect.iscoroutine()`
- AC-201.3: Async handlers called with `await`; sync handlers called normally
- AC-201.4: All existing tests pass; new test verifies coroutines actually execute
- AC-201.5: No callers of `execute_skill` break (update call sites to `await`)

### QA Commands
```bash
# Verify coroutines execute (not return coroutine objects)
pytest tests/nxyme_core/test_skill_loader.py -v -k async
python3 -c "
import asyncio
from nxyme_core.skill_loader import SkillLoader
async def test():
    sl = SkillLoader()
    result = await sl.execute_skill('test_skill', {})
    print(f'Result: {result}')
    print(f'Type: {type(result)}')
asyncio.run(test())
"
```

### Implementation Pattern
```python
async def execute_skill(self, skill_name: str, context: dict) -> Any:
    handler = self._get_handler(skill_name)
    if asyncio.iscoroutinefunction(handler):
        return await handler(**context)
    return handler(**context)
```

### Atomic Commit
```
fix(skill_loader): await async handlers in execute_skill
```

---

## Story S-202: DirectLlamaClient Llama() Instance Reuse

**Story ID:** S-202 | **Points:** 3 | **Priority:** HIGH | **TDD:** Test-First | **DEPENDS:** None

### What
New `Llama()` instance created per request. Model reloaded from disk every time (~2-5s per request). Fix: single instance in `__init__`, reuse across methods.

### File
`/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_engine/nx_engine/engine/unified.py` (or DirectLlamaClient)

### Root Cause
Every `generate()` or `chat()` call creates a new `Llama()` instance, triggering model loading from disk. With GGUF models (Q4_K_M), this means ~2-5s latency per request.

### Acceptance Criteria
- AC-202.1: `Llama()` instance created once in `__init__` or module-level singleton
- AC-202.2: All `generate()`/`chat()` methods use the shared instance
- AC-202.3: Benchmark confirms no model reload per request
- AC-202.4: Sustained <1s latency over 100 consecutive requests
- AC-202.5: Thread-safe access (Llama.cpp is not thread-safe; use lock or context per request)

### QA Commands
```bash
# Benchmark: should show no model reload
python3 -c "
import time
from nx_engine.engine.unified import DirectLlamaClient
client = DirectLlamaClient()
times = []
for i in range(100):
    start = time.time()
    client.generate('Hello', max_tokens=10)
    times.append(time.time() - start)
print(f'Avg latency: {sum(times)/len(times):.3f}s')
print(f'Min: {min(times):.3f}s, Max: {max(times):.3f}s')
"
# Should be consistent ~0.1-0.3s, not 2-5s
```

### Implementation Pattern
```python
class DirectLlamaClient:
    def __init__(self, model_path: str, **kwargs):
        self._model_path = model_path
        self._llama: Optional[Llama] = None

    def _get_llama(self) -> Llama:
        if self._llama is None:
            self._llama = Llama(model_path=self._model_path, ...)
        return self._llama

    def generate(self, prompt: str, **kwargs):
        return self._get_llama()(prompt, **kwargs)
```

### Atomic Commit
```
perf(direct_llama): reuse Llama instance instead of per-request
```

---

## Story S-203: tool_caller httpx Session Pooling

**Story ID:** S-203 | **Points:** 2 | **Priority:** MEDIUM | **TDD:** Test-First | **DEPENDS:** S-201

### What
New `httpx.AsyncClient()` created per call. Connection pooling bypassed. Fix: store as class attribute, reuse.

### File
`/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_engine/nx_engine/local_llm/tool_caller.py`

### Root Cause
Each `tool_caller` method creates `httpx.AsyncClient()`. TCP handshake + TLS handshake adds ~100-500ms per call. With connection pool, reuse costs ~0ms.

### Acceptance Criteria
- AC-203.1: `httpx.AsyncClient()` stored as class attribute in `__init__`
- AC-203.2: Reused across all `tool_call()` calls
- AC-203.3: Proper cleanup on `__aenter__`/`__aexit__` or `close()`
- AC-203.4: Benchmark confirms reduced latency (pool reuse vs new client)

### QA Commands
```bash
# Check connection reuse
python3 -c "
import asyncio
import httpx
from nx_engine.local_llm.tool_caller import ToolCaller

async def test():
    tc = ToolCaller()
    # First call - new connection
    await tc.tool_call({'name': 'test', 'parameters': {}})
    # Second call - should reuse connection
    await tc.tool_call({'name': 'test', 'parameters': {}})

asyncio.run(test())
"
# Use tcpdump or netstat to verify connection reuse
```

### Atomic Commit
```
perf(tool_caller): pool httpx AsyncClient for connection reuse
```

---

## Story S-204: batching_engine Async Health Check

**Story ID:** S-204 | **Points:** 3 | **Priority:** MEDIUM | **TDD:** Test-First | **DEPENDS:** S-201

### What
`time.sleep(2)` blocking call in async context. Fix: replace with `asyncio.wait_for(async_health_check(), timeout=2.0)`.

### File
`/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/src/batching_engine.py` (line ~77)

### Root Cause
Using `time.sleep(2)` in an async function blocks the entire event loop. All other async tasks are paused during the 2s sleep.

### Acceptance Criteria
- AC-204.1: `time.sleep(2)` replaced with `await asyncio.wait_for(health_check(), timeout=2.0)`
- AC-204.2: Health check completes within 2s timeout
- AC-204.3: No blocking sleep in async context
- AC-204.4: Other async tasks continue to run during health check

### QA Commands
```bash
# Verify no blocking
python3 -c "
import asyncio
import time

async def test_no_blocking():
    results = []
    async def health_check():
        await asyncio.sleep(0.1)
        return 'healthy'
    
    start = time.time()
    # This should not block other tasks
    result = await asyncio.wait_for(health_check(), timeout=2.0)
    elapsed = time.time() - start
    print(f'Health check: {result}, elapsed: {elapsed:.3f}s')
    # Should be ~0.1s, not 2s
    assert elapsed < 1.0, f'Blocking detected: {elapsed}s'
    print('No blocking detected')

asyncio.run(test_no_blocking())
"
```

### Atomic Commit
```
refactor(batching): replace sync sleep with async health check
```

---

## Story S-205: brain.py Threading → Asyncio Task

**Story ID:** S-205 | **Points:** 2 | **Priority:** MEDIUM | **TDD:** Test-First | **DEPENDS:** S-201

### What
`threading.Thread` used for RAG instead of `asyncio.create_task`. Orphan thread detection gap. Fix: replace with task tracking.

### File
`/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_engine/nx_engine/local_llm/brain.py`

### Root Cause
Using `threading.Thread` in async code creates threads that aren't tracked by the asyncio event loop. Orphan thread detection is complex.

### Acceptance Criteria
- AC-205.1: `threading.Thread` replaced with `asyncio.create_task()`
- AC-205.2: Tasks tracked in a set (`self._tasks: set[asyncio.Task]`)
- AC-205.3: Tasks cancelled properly on shutdown (`task.cancel()` + `await asyncio.gather(*tasks, return_exceptions=True)`)
- AC-205.4: No orphan threads after test run
- AC-205.5: Async context properly maintained

### QA Commands
```bash
# Check for orphan threads
python3 -c "
import asyncio
import threading
import sys

original_thread_count = threading.active_count()
print(f'Initial threads: {original_thread_count}')

async def test():
    async def background_task():
        await asyncio.sleep(0.1)
        return 'done'
    
    task = asyncio.create_task(background_task())
    result = await task
    print(f'Task result: {result}')
    print(f'Threads after task: {threading.active_count()}')
    assert threading.active_count() == original_thread_count, 'Orphan thread detected!'

asyncio.run(test())
print('No orphan threads detected')
"

# Also verify task cancellation works
python3 -c "
import asyncio

async def test_cancellation():
    tasks = set()
    
    async def long_task():
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            print('Task cancelled')
            raise
    
    for i in range(5):
        task = asyncio.create_task(long_task())
        tasks.add(task)
    
    # Cancel all
    for task in tasks:
        task.cancel()
    
    await asyncio.gather(*tasks, return_exceptions=True)
    print(f'Remaining tasks: {len(tasks)}')

asyncio.run(test_cancellation())
"
```

### Atomic Commit
```
refactor(brain): replace threading.Thread with asyncio.create_task
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
| Wave 1 | Day 1-2 | S-201: skill_loader async fix | Solo (BLOCKS all others) |
| Wave 1 | Day 1-2 | S-202: DirectLlamaClient pooling | PARALLEL with S-201 |
| Wave 2 | Day 3-5 | S-203, S-204, S-205 | PARALLEL (all depend on S-201) |

**Critical Path:** S-201 → S-203/S-204/S-205
**Estimated Speedup:** 40% faster than sequential (2 waves vs 5 sequential)

---

## Definition of Done

All of the following must be true for this epic to be DONE:

1. All async handlers properly awaited — no coroutine objects returned
2. Single Llama() instance reused — no model reload per request
3. httpx connection pool utilized — measurable latency reduction
4. No `time.sleep()` in async contexts — event loop never blocked
5. No orphan threads — all tasks properly tracked and cancelled
6. All 5 commits merged with passing CI
7. Performance audit score improves from **92/100 to 95+/100**