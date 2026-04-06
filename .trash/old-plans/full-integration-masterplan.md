# Full Integration Masterplan — Memory-Augmented Delegation

> **Goal**: Wire all intelligence modules into the actual delegation flow
> **Date**: 2026-04-05
> **Status**: READY FOR IMPLEMENTATION

---

## Current State vs Target State

### Current (Broken)
```
User → n-xyme-mind.sh → complexity-score.sh (bash) → Static L1-L5 table → Agent
```

### Target (Working)
```
User → n-xyme-mind.sh → unified_router.py → 
  1. Check triggers (fast, <1ms)
  2. Query memory for similar tasks (<50ms)
  3. Local model analysis for L3+ (2-5s, optional)
  4. Learning-based routing weights (<1ms)
  5. Fallback to keyword scoring (<1ms)
→ Optimal agent + outcome logging
```

---

## Phase 1: Core Integration (30 min)

### 1.1 Replace Bash Scorer with Python Router

**File**: `n-xyme-mind.sh`
**Change**: Replace `bash bin/complexity-score.sh` with Python unified router call

```bash
# BEFORE (line ~50):
LEVEL=$(bash bin/complexity-score.sh "$TASK" | python3 -c "import sys,json; print(json.load(sys.stdin)['level'])")

# AFTER:
LEVEL=$(python3 -c "
import asyncio
from src.intelligence.unified_router import get_unified_router
async def route():
    router = get_unified_router()
    result = await router.route_task('$TASK')
    print(result.level)
asyncio.run(route())
")
```

**Risk**: Low — fallback to keyword scoring if Python fails
**Test**: Run `n-xyme-mind.sh` with sample tasks

### 1.2 Add Outcome Logging Hook

**File**: `n-xyme-mind.sh` (after delegation completes)
**Change**: Log outcome to learning system

```bash
# AFTER delegation completes:
python3 -c "
import asyncio
from src.intelligence.unified_router import get_unified_router
async def log():
    router = get_unified_router()
    await router.record_outcome(
        task_id='$TASK_ID',
        task_description='$TASK',
        level=$LEVEL,
        agent='$AGENT',
        success=$SUCCESS,
        latency_ms=$LATENCY
    )
asyncio.run(log())
"
```

**Risk**: Low — fire-and-forget, doesn't block delegation
**Test**: Verify outcomes appear in routing weights

---

## Phase 2: MCP Tool Integration (1h)

### 2.1 Add Unified Router as MCP Tool

**File**: `src/memory/mcp_server_v2.py`
**Change**: Add `route_task` tool to MCP server

```python
@mcp.tool(tags={"routing", "intelligence"})
async def route_task(task_description: str) -> dict:
    """Route a task using the unified delegation router."""
    from src.intelligence.unified_router import get_unified_router
    router = get_unified_router()
    result = await router.route_task(task_description)
    return {
        "level": result.level,
        "agent": result.agent,
        "confidence": result.confidence,
        "strategy": result.strategy_used,
        "reason": result.reason,
        "alternatives": result.alternatives
    }
```

**Risk**: Low — additive change, doesn't break existing tools
**Test**: Call `route_task` via MCP protocol

### 2.2 Add Outcome Recording as MCP Tool

**File**: `src/memory/mcp_server_v2.py`
**Change**: Add `record_delegation_outcome` tool

```python
@mcp.tool(tags={"routing", "learning"})
async def record_delegation_outcome(
    task_id: str,
    task_description: str,
    level: int,
    agent: str,
    success: bool,
    latency_ms: float = 0,
    tokens_used: int = 0
) -> dict:
    """Record a delegation outcome for learning."""
    from src.intelligence.unified_router import get_unified_router
    router = get_unified_router()
    await router.record_outcome(
        task_id=task_id,
        task_description=task_description,
        level=level,
        agent=agent,
        success=success,
        latency_ms=latency_ms,
        tokens_used=tokens_used
    )
    return {"status": "ok"}
```

**Risk**: Low — additive change
**Test**: Call tool and verify weights update

---

## Phase 3: AGENTS.md Update (30 min)

### 3.1 Add Unified Routing Rules

**File**: `AGENTS.md`
**Change**: Add new delegation routing section

```markdown
## 🧠 Unified Delegation Routing

The system uses a 5-layer routing strategy with automatic fallback:

1. **Trigger-based** (<1ms) — Pattern matching for common tasks
2. **Memory-augmented** (<50ms) — Query past similar tasks
3. **Local model analysis** (2-5s) — Ollama complexity analysis for L3+
4. **Learning-based** (<1ms) — Optimize routing weights from outcomes
5. **Keyword fallback** (<1ms) — Static L1-L5 scoring (always available)

### Routing Flow

```
User Task → Triggers → Memory → Local Model → Learning → Keyword
     ↓         ↓          ↓           ↓           ↓          ↓
  Match?   Similar?   L3+?      Weights?   Fallback
     ↓         ↓          ↓           ↓           ↓          ↓
  Route     Route     Analyze    Optimize    Route
```

### Outcome Logging

Every delegation outcome is automatically logged to:
- Memory system (for future similarity queries)
- Learning system (for routing weight optimization)
- Outcome logger (for performance tracking)

### Configuration

- `src/intelligence/unified_router.py` — Main routing orchestrator
- `src/intelligence/memory_routing.py` — Memory-augmented routing
- `src/intelligence/local_model_analysis.py` — Local model complexity analysis
- `src/intelligence/routing_optimizer.py` — Learning-based weight optimization
- `src/intelligence/trigger_routing.py` — Trigger-based pattern matching
- `src/intelligence/outcome_logger.py` — Outcome logging and stats
```

### 3.2 Update Delegation Prompt Template

**File**: `AGENTS.md`
**Change**: Update delegation examples to use unified router

```markdown
### Example: Intelligent Delegation

```typescript
// Route task using unified router
task(
  subagent_type="hephaestus",
  load_skills=[],
  run_in_background=false,
  description="Add auth middleware",
  prompt="Route this task through the unified router first, then execute."
)
```
```

---

## Phase 4: Testing & Verification (30 min)

### 4.1 Integration Tests

**File**: `tests/test_unified_router_integration.py`
**Tests**:
1. `test_n_xyme_mind_uses_unified_router` — Verify n-xyme-mind.sh calls unified router
2. `test_outcome_logging_works` — Verify outcomes are logged after delegation
3. `test_mcp_route_task_tool` — Verify MCP tool works
4. `test_mcp_record_outcome_tool` — Verify outcome recording via MCP
5. `test_fallback_to_keyword` — Verify fallback works when memory/local model fail

### 4.2 End-to-End Test

```bash
# Test 1: Simple task
bash n-xyme-mind.sh "fix typo in config"
# Expected: L1 → sisyphus-junior (keyword or trigger)

# Test 2: Complex task
bash n-xyme-mind.sh "add JWT auth middleware"
# Expected: L3 → hephaestus (memory or local model)

# Test 3: Architecture task
bash n-xyme-mind.sh "redesign entire system"
# Expected: L5 → metis → prometheus → hephaestus

# Test 4: Verify outcome logging
python3 -c "
from src.intelligence.routing_optimizer import get_routing_optimizer
optimizer = get_routing_optimizer()
weights = optimizer.get_routing_weights()
print(f'Agents tracked: {len(weights)}')
"
```

---

## Phase 5: Performance Optimization (1h)

### 5.1 Async Delegation

**File**: `n-xyme-mind.sh`
**Change**: Run unified router asynchronously to avoid blocking

```bash
# Run routing in background, don't block startup
python3 -c "
import asyncio
from src.intelligence.unified_router import get_unified_router
async def prewarm():
    router = get_unified_router()
    # Prewarm memory router
    await router.route_task('warmup')
asyncio.run(prewarm())
" &
```

### 5.2 Local Model Caching

**File**: `src/intelligence/local_model_analysis.py`
**Change**: Cache local model results for similar tasks

```python
# Add LRU cache for local model results
from functools import lru_cache

@lru_cache(maxsize=100)
def _cached_analysis(task_hash: str) -> Optional[Dict]:
    # ... existing analysis logic
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|:-----|:-----------|:-------|:-----------|
| Python import fails | Low | High | Fallback to bash complexity-score.sh |
| Memory router unavailable | Medium | Low | Fallback to keyword scoring |
| Local model timeout | Medium | Low | 5s timeout, fallback to keyword |
| Outcome logging fails | Low | Low | Fire-and-forget, doesn't block |
| MCP tool registration fails | Low | Medium | Server starts without new tools |

---

## Implementation Order

| Step | Task | Effort | Dependencies |
|:-----|:-----|:-------|:-------------|
| 1 | Replace bash scorer with Python router | 30 min | None |
| 2 | Add outcome logging hook | 15 min | Step 1 |
| 3 | Add MCP route_task tool | 30 min | None |
| 4 | Add MCP record_outcome tool | 15 min | Step 3 |
| 5 | Update AGENTS.md | 30 min | Steps 1-4 |
| 6 | Integration tests | 30 min | Steps 1-5 |
| 7 | Performance optimization | 1h | Steps 1-6 |

**Total**: ~3.5 hours

---

## Success Criteria

- [ ] `n-xyme-mind.sh` uses unified router instead of bash scorer
- [ ] Outcomes are logged after each delegation
- [ ] MCP server has `route_task` and `record_delegation_outcome` tools
- [ ] AGENTS.md documents unified routing
- [ ] All integration tests pass
- [ ] Performance: <100ms for routing decisions (excluding local model)
- [ ] Fallback works when memory/local model unavailable
