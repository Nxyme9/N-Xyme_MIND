# N-Xyme MIND - Integration Plan (Next 4 Steps)

> **Generated:** 2026-04-12
> **Current Status:** HTTP Gateway ✅, memory_core ✅, Frontend Build ✅

---

## Architecture Update

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ Frontend    │     │ HTTP Gateway    │     │ Python Packages  │
│ (port 3000) │────►│ (port 8766)     │────►│                  │
│             │     │ /memory_* ✅    │     │ memory_core ✅   │
│ API Routes  │     │ /tools_list ✅  │     │ orchestration ❌  │
│ → 8766      │     │ /health ✅      │     │ learning_engine ❌ │
└─────────────┘     └─────────────────┘     │ nx_brain_mcp ❌   │
                                              └──────────────────┘
```

**Verified Working:**
- ✅ `/tools_list` - Returns 5 real memory_core tools
- ✅ `/memory_get` - Returns real search results from SQLite/FAISS
- ✅ `/memory_write` - Creates memories with version_hash
- ✅ `/system_health_check` - Reports both MCPs connected
- ✅ Frontend build passes

---

## Step 1: Full Integration Test

### Goal
Verify frontend UI actually calls HTTP Gateway and receives real data.

### Actions

| # | Action | File | Method |
|---|--------|------|--------|
| 1.1 | Start HTTP Gateway in background | `packages/http_gateway.py` | `nohup python3 &` |
| 1.2 | Start frontend dev server | `frontend/` | `npm run dev` |
| 1.3 | Navigate to memory page | Browser | `localhost:3000/memory` |
| 1.4 | Check network tab for API calls | DevTools | Verify → `localhost:8766` |
| 1.5 | Test search - enter query | UI | Should return real results |

### Verification
- Frontend makes call to `http://localhost:8766/memory_get`
- Response contains real memory data (not mock)
- UI renders results correctly

### Files to Check
- `frontend/src/app/api/backend/mcp/route.ts` - Already routes to 8766
- `frontend/src/app/memory/page.tsx` - Uses memory hook
- `frontend/src/hooks/useMemory.ts` - If exists

---

## Step 2: Connect Orchestration & Learning Engine

### Goal
Add endpoints for task routing and agent management.

### Current HTTP Gateway Endpoints

| Endpoint | Status | Package |
|----------|--------|---------|
| `/tools_list` | ✅ | memory_core |
| `/memory_get` | ✅ | memory_core |
| `/memory_write` | ✅ | memory_core |
| `/system_health_check` | ✅ | memory_core |
| `/route_task` | ⚠️ | learning_engine (stub) |
| `/recall_session` | ⚠️ | memory_core (needs wiring) |
| `/find_context` | ⚠️ | memory_core (needs wiring) |

### Actions

| # | Action | Package | Endpoint |
|---|--------|---------|----------|
| 2.1 | Add orchestration tools to gateway | `packages/orchestration/mcp_server.py` | `/orchestration_execute` |
| 2.2 | Add learning_engine routing | `packages/learning_engine/router.py` | `/route_task` |
| 2.3 | Add session management | `packages/orchestration/session_pool.py` | `/session_*` |
| 2.4 | Add trigger registry | `packages/nx_brain_mcp/triggers.py` | `/trigger_*` |

### Implementation Pattern

```python
# Add to http_gateway.py

def _call_orchestration_execute(task: str, agent: str = None) -> dict:
    """Direct call to orchestration package."""
    try:
        from packages.orchestration.catalyst import orchestrate
        result = orchestrate(task)
        return result
    except Exception as e:
        return {"error": str(e)}

def _call_route_task(task_description: str) -> dict:
    """Direct call to learning_engine."""
    try:
        from packages.learning_engine import route_task as lr_route_task
        result = lr_route_task(task_description)
        return result
    except Exception as e:
        return {"error": str(e)}
```

### Verification
- `/route_task` returns level + agent + confidence (not stub)
- `/orchestration_execute` runs actual task

---

## Step 3: Add nx_brain_mcp and Orchestration MCP

### Goal
Connect the full MCP server (not just memory_core).

### Package Inventory

| Package | MCP Server | Tools | Status |
|---------|------------|-------|--------|
| `memory_core` | `mcp_server.py` | search, write, stats | ✅ Connected |
| `orchestration` | `mcp_server.py` | orchestrate, session_* | ❌ Not wired |
| `learning_engine` | `router.py` | route_task, record_outcome | ❌ Not wired |
| `nx_brain_mcp` | `__init__.py` | trigger_*, catalyst_* | ❌ Not wired |

### Actions

| # | Action | File |
|---|--------|------|
| 3.1 | Import orchestration MCP tools | `packages/orchestration/mcp_server.py` |
| 3.2 | Import learning_engine router | `packages/learning_engine/router.py` |
| 3.3 | Import nx_brain_mcp triggers | `packages/nx_brain_mcp/__init__.py` |
| 3.4 | Add endpoints for each tool group | `http_gateway.py` |

### Tool Groups to Add

```
orchestration:
  - orchestrate (run BMAD workflow)
  - session_get / session_return / session_warm_pool
  - catalyst_orchestrate / catalyst_detect_state

learning_engine:
  - route_task (optimal agent selection)
  - record_outcome (learning)
  - get_recommendations

nx_brain_mcp:
  - trigger_register / trigger_list / trigger_check
  - catalyst_list_workflows / catalyst_get_status
```

### Verification
- GET `/tools_list` returns ALL packages, not just memory_core
- Each tool group responds to test calls

---

## Step 4: Real User Flows

### Goal
Test actual user interactions end-to-end.

### User Flows to Test

| Flow | Steps | Expected |
|------|-------|----------|
| **Memory Search** | 1. Open /memory → 2. Type query → 3. Press enter | Real results from DB |
| **Memory Write** | 1. Click "Add Memory" → 2. Enter text → 3. Save | Memory appears in list |
| **Agent Routing** | 1. Open /orchestration → 2. Enter task → 3. See agent selection | Agent assigned |
| **Chat** | 1. Open /chat → 2. Type message → 3. See response | LLM responds |

### Actions

| # | Action | Check |
|---|--------|-------|
| 4.1 | Test memory search UI | Results render from API |
| 4.2 | Test memory write UI | New memory persists |
| 4.3 | Test orchestration page | Task routes to agent |
| 4.4 | Test chat page | GGUF server responds |

### Debug Checklist

- [ ] Frontend dev server running (port 3000)
- [ ] HTTP Gateway running (port 8766)
- [ ] Network tab shows calls to 8766
- [ ] Response is JSON (not error)
- [ ] Data matches expected schema

---

## Success Criteria

| Step | Criteria | Verification |
|------|----------|--------------|
| 1 | Frontend → Gateway → memory_core E2E | UI shows real data |
| 2 | /route_task returns ML recommendation | Not fallback stub |
| 3 | /tools_list shows 15+ tools | All packages wired |
| 4 | All 4 user flows work | No errors in UI |

---

## Dependencies

- HTTP Gateway must be running (`python3 packages/http_gateway.py`)
- Frontend must be running (`cd frontend && npm run dev`)
- memory_core verified working
- orchestration package has MCP server

## Files to Modify

1. `packages/http_gateway.py` - Add new endpoints
2. `frontend/src/hooks/useMemory.ts` - Ensure correct API call
3. `frontend/src/app/memory/page.tsx` - Verify data rendering

---

## Timeline Estimate

| Step | Complexity | Time |
|------|------------|------|
| 1. Integration Test | Low | 10 min |
| 2. Connect Packages | Medium | 30 min |
| 3. Add MCP Tools | Medium | 30 min |
| 4. User Flows | Medium | 20 min |
| **Total** | | ~90 min |

---

## Step Boundaries (Clarification)

- **Step 2**: Connect orchestration + learning_engine functions to gateway endpoints (make them actually work, not stubs)
- **Step 3**: Expand /tools_list to show ALL packages (not just memory_core) + add remaining endpoints

---

## Verification Commands

### Step 2 Verification

```bash
# Test route_task returns ML recommendation (not stub)
curl -s -X POST http://localhost:8766/route_task \
  -H "Content-Type: application/json" \
  -d '{"task_description": "fix the login bug"}' | jq .level

# Expected: 1-5 (not null), confidence > 0.5 (not fallback)
```

### Step 3 Verification

```bash
# Test tools_list returns 15+ tools
curl -s http://localhost:8766/tools_list | jq '.agents | length'

# Expected: 10+ (not just 5 from memory_core)
```

---

## Commit Strategy

```bash
# Step 1: Integration test
git add -A && git commit -m "test: add integration test - frontend to HTTP gateway"

# Step 2: Connect orchestration + learning engine  
git add -A && git commit -m "feat: wire orchestration endpoints to HTTP gateway"

# Step 3: Add full MCP tools
git add -A && git commit -m "feat: expose all MCP tool groups via HTTP gateway"

# Step 4: User flows
git add -A && git commit -m "test: add e2e user flow tests"
```