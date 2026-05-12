# Implementation Plan: Integrate Learning/Memory/Brain Systems into Execution Flow

**Generated:** 2026-04-14  
**Context:** Analysis found that learning/memory/brain systems are defined but NOT wired into main execution flow  
**Goal:** Make these systems mandatory integration points, not optional middleware

---

## Executive Summary

The learning, memory, and brain systems exist with sophisticated features (Q-learning routing, semantic memory, context injection), but they're buried in optional code paths with silent failures. This plan makes them mandatory integration points.

**Key Disconnects Found:**
1. `route_task()` never called BEFORE delegation — should get routing from learning system
2. `record_outcome()` is commented out — should log every task outcome
3. Memory injection disabled by default when `optimization_target="speed"`
4. Learning hooks registered but empty list by default

---

## Phase 1: Mandatory Outcome Recording (P0)

### Why: Creates the learning signal that feeds Q-Learning

**Current State:**
- Line 863 in `unified_pipeline.py`: `# Note: Full outcome logging would call nx_brain_mcp.learning_record_outcome` — NOT IMPLEMENTED
- Only `log_task_sequence()` is called, not `record_outcome()`

### Files to Modify:

| File | Changes |
|------|----------|
| `packages/orchestration/unified_pipeline.py` | Add `record_outcome()` call in Stage 6 |
| `packages/orchestration/spawn.py` (new) | Create unified spawn function with outcome logging |

### Implementation:

```python
# In unified_pipeline.py Stage 6 (after task completion):
async def _log_learning_outcome(self, task_id: str, agent: str, success: bool, duration_ms: int):
    """Mandatory outcome logging - NOT optional"""
    try:
        from packages.learning_engine.mcp_server import record_outcome
        await record_outcome(
            task=task_id,
            agent=agent,
            success=success,
            latency_ms=duration_ms,
            tokens_used=0  # Could extract from usage
        )
        logger.info(f"Outcome logged: task={task_id}, agent={agent}, success={success}")
    except Exception as e:
        logger.error(f"Failed to log outcome: {e}")
        # NEVER silently fail - log the failure itself
```

### Success Criteria:
- Every task completion logs outcome to SQLite
- Q-Learning weights actually update (not fake like before)

---

## Phase 2: Pre-Delegation Routing (P0)

### Why: Should get routing FROM learning system, not keyword matching

**Current State:**
- `agent_loop.py` delegates by keyword matching (`"fix typo" → sisyphus-junior`)
- Never calls `route_task()` from learning_engine

### Files to Modify:

| File | Changes |
|------|----------|
| `packages/orchestration/spawn.py` (new) | Create unified spawn with routing |
| `packages/orchestration/agent_loop.py` | Add route_task call before delegation |
| `packages/orchestration/delegation.py` | Integrate with AdaptiveRouter |

### Implementation:

```python
# In spawn() BEFORE delegating:
async def spawn(task: str, context: dict = None) -> TaskResult:
    # STEP 1: Get routing from learning system (NOT keyword matching)
    try:
        from packages.learning_engine.mcp_server import route_task
        routing = await route_task(task_description=task)
        agent = routing.get("agent", "hephaestus")  # fallback
        level = routing.get("level", 3)
        logger.info(f"Learning routing: task={task[:50]} → agent={agent} (L{level})")
    except Exception as e:
        logger.warning(f"Learning routing failed, using fallback: {e}")
        agent = _fallback_route(task)  # existing keyword matching
    
    # STEP 2: Execute with agent
    result = await _delegate_to_agent(agent, task, context)
    
    # STEP 3: Log outcome (Phase 1)
    await _log_outcome(task, agent, result.success, result.duration_ms)
    
    return result
```

### Success Criteria:
- `route_task()` called BEFORE every delegation
- Fallback to keyword matching only if learning fails
- Routing decision logged with task

---

## Phase 3: Pre-Dispatch Memory Injection (P0)

### Why: Production pattern from AutoGen, Claude Code — inject memories BEFORE agent sees prompt

**Current State:**
- Memory injection disabled when `optimization_target="speed"` (line 685)
- Uses 4-second timeout — silently skipped if times out
- Circuit breaker disables after 3 failures

### Files to Modify:

| File | Changes |
|------|----------|
| `packages/orchestration/memory_injector.py` | Remove speed override, make mandatory |
| `packages/orchestration/spawn.py` (new) | Add pre-dispatch memory injection |
| `packages/brain_mcp/namespaces/fingerprint.py` | Ensure get_full_injected_context works |

### Implementation:

```python
# In spawn() BEFORE agent execution:
async def _inject_memory_context(task: str, agent: str, max_tokens: int = 500) -> str:
    """Pre-dispatch memory injection - MANDATORY, not optional"""
    try:
        from packages.brain_mcp.namespaces.fingerprint import get_full_injected_context
        
        # Get injected context with timeout protection
        result = await asyncio.wait_for(
            get_full_injected_context(
                agent=agent,
                task=task,
                max_tokens=max_tokens
            ),
            timeout=3.0  # 3 second timeout, not 4
        )
        
        injected = result.get("injected_context", "")
        if injected:
            logger.info(f"Memory injected: {len(injected)} chars")
        return injected
        
    except asyncio.TimeoutError:
        logger.warning("Memory injection timed out, continuing without")
        return ""
    except Exception as e:
        logger.warning(f"Memory injection failed: {e}")
        return ""

# In spawn():
async def spawn(task: str, context: dict = None) -> TaskResult:
    # Get routing FIRST (Phase 2)
    agent = await _get_routing(task)
    
    # Inject memory SECOND
    memory_context = await _inject_memory_context(task, agent)
    
    # Merge with existing context
    enhanced_context = {**(context or {}), "memory_injection": memory_context}
    
    # Execute with enhanced context
    result = await _delegate_to_agent(agent, task, enhanced_context)
    
    # Log outcome THIRD
    await _log_outcome(task, agent, result.success, result.duration_ms)
    
    return result
```

### Changes to `unified_pipeline.py`:
```python
# REMOVE this line (685):
inject_memory = optimization_target != "speed"

# REPLACE with:
inject_memory = True  # ALWAYS inject, not conditional
```

### Success Criteria:
- Memory injection happens for EVERY task
- Timeout reduced from 4s to 3s with graceful fallback
- Speed override removed — always inject

---

## Phase 4: Register Learning Hooks in AgentLoop (P1)

### Why: AgentLoop has hooks system but empty list by default

**Current State:**
- `agent_loop.py` lines 353-354: `pre_hooks=[]`, `post_hooks=[]` — EMPTY
- Hooks exist but never registered

### Files to Modify:

| File | Changes |
|------|----------|
| `packages/orchestration/agent_loop.py` | Register learning hooks |
| `packages/orchestration/hooks.py` (new) | Create learning hooks module |

### Implementation:

```python
# In hooks.py:
class LearningHooks:
    """Hooks that record to learning system"""
    
    async def on_task_start(self, task_id: str, task: str, agent: str):
        """Log task start for latency tracking"""
        logger.debug(f"Task started: {task_id}")
    
    async def on_task_complete(self, task_id: str, task: str, agent: str, 
                                success: bool, duration_ms: int):
        """Log outcome for Q-Learning"""
        try:
            from packages.learning_engine.mcp_server import record_outcome
            await record_outcome(
                task=task,
                agent=agent,
                success=success,
                latency_ms=duration_ms
            )
        except Exception as e:
            logger.error(f"Hook outcome logging failed: {e}")

# In agent_loop.py:
def __init__(self, ...):
    # ADD learning hooks (NOT empty list)
    learning_hooks = LearningHooks()
    
    super().__init__(
        ...,
        pre_hooks=[learning_hooks.on_task_start],
        post_hooks=[learning_hooks.on_task_complete]
    )
```

### Success Criteria:
- AgentLoop calls hooks on every task start/complete
- Outcome logged to learning system automatically

---

## Phase 5: Explicit Learning Chain (P1)

### Why: Current learning is scattered across optional modules — create unified chain

**Current State:**
- Learning happens in: `lifecycle.py`, `session_hooks.py`, `router.py` — fragmented
- No single "learning chain" that all tasks go through

### Files to Modify:

| File | Changes |
|------|----------|
| `packages/orchestration/learning_chain.py` (new) | Create unified learning pipeline |
| `packages/orchestration/unified_pipeline.py` | Use learning chain |

### Implementation:

```python
# In learning_chain.py:
class LearningChain:
    """Unified chain: route → inject → execute → log → update"""
    
    def __init__(self):
        self.q_learning = QLearningEngine()
        self.memory = MemoryInjector()
        self.outcome_logger = OutcomeLogger()
    
    async def execute(self, task: str, context: dict = None) -> TaskResult:
        # Step 1: Get routing (Q-Learning)
        routing = await self.q_learning.route(task)
        
        # Step 2: Inject memory
        memory = await self.memory.inject(task, routing.agent)
        
        # Step 3: Execute
        result = await _delegate(routing.agent, task, {**context, "memory": memory})
        
        # Step 4: Log outcome
        await self.outcome_logger.log(
            task=task,
            agent=routing.agent,
            success=result.success,
            latency=result.duration_ms
        )
        
        # Step 5: Update Q-Learning weights
        await self.q_learning.update(routing, result)
        
        return result
```

### Integration in `unified_pipeline.py`:
```python
# Replace Stage 1-6 with learning chain:
learning_chain = LearningChain()
result = await learning_chain.execute(task, context)
```

### Success Criteria:
- Single entry point for all learning/memory operations
- Q-Learning weights update after every task
- Memory injection happens automatically

---

## Phase 6: Hard Dependencies (P1)

### Why: Current code uses optional imports with silent failures

**Current State:**
- Line 70-75 in `agent_loop.py`: wrapped in try/except → silently ignored
- No fallback chain

### Files to Modify:

| File | Changes |
|------|----------|
| `packages/orchestration/agent_loop.py` | Make dependencies required |
| `packages/orchestration/memory_injector.py` | Fail fast, not silent |

### Implementation:

```python
# REMOVE:
try:
    from packages.learning_engine import LearningEngine
except ImportError:
    logger.warning("Learning engine not available")
    LearningEngine = None

# REPLACE with hard import or explicit error:
from packages.learning_engine import LearningEngine
# If import fails, the entire system should fail loudly
# NOT silently continue without learning

# For optional features, use explicit config:
LEARNING_ENABLED = os.getenv("LEARNING_ENABLED", "true").lower() == "true"
if not LEARNING_ENABLED:
    logger.warning("Learning system DISABLED via config")
```

---

## Testing Plan

### Test 1: Outcome Logging
```bash
# Run a task and verify outcome logged
python -c "
import asyncio
from packages.learning_engine.mcp_server import record_outcome, get_outcomes

async def test():
    await record_outcome('test task', 'hephaestus', True, 1000)
    outcomes = await get_outcomes(limit=10)
    print(f'Outcomes: {len(outcomes)}')
    assert len(outcomes) > 0

asyncio.run(test())
"
```

### Test 2: Pre-Delegation Routing
```bash
# Verify route_task called BEFORE delegation
# Add logging to spawn() and check logs
```

### Test 3: Memory Injection
```bash
# Verify memory injected for every task
# Check logs for "Memory injected: X chars"
```

---

## Rollback Plan

If issues occur:
1. Revert `unified_pipeline.py` to remove memory override change
2. Comment out outcome logging if causing issues
3. Keep fallback routing as backup

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Outcome logging | 100% of tasks logged |
| Pre-dispatch routing | 100% of tasks routed via learning |
| Memory injection | 100% of tasks with memory context |
| Q-Learning updates | Weights update after every task |
| Latency impact | <100ms overhead from integration |

---

## Files to Modify Summary

```
packages/orchestration/
├── spawn.py                    # NEW - unified entry point
├── learning_chain.py          # NEW - unified learning pipeline
├── hooks.py                   # NEW - learning hooks
├── unified_pipeline.py        # MODIFY - remove speed override, add outcome logging
├── agent_loop.py              # MODIFY - register hooks, add route_task
├── memory_injector.py         # MODIFY - remove optional behavior
└── delegation.py              # MODIFY - integrate AdaptiveRouter
```

---

## Implementation Order

1. **Week 1**: Phase 1 + 2 (Outcome logging + Pre-delegation routing)
2. **Week 2**: Phase 3 (Pre-dispatch memory injection)
3. **Week 3**: Phase 4 + 5 (Hooks + Learning chain)
4. **Week 4**: Phase 6 + Testing + Rollback plan

---

## Notes

- All MCP tools should be called EXPLICITLY, not just available
- Learning should be MANDATORY, not optional
- No silent failures — log everything including failures
- Use research patterns from AutoGen, LangChain, Claude Code