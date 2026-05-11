# N-Xyme MIND Full System Synthesis Plan

> **Generated:** 2026-04-12
> **Goal:** Connect frontend to backend for 100% functioning system

---

## AUDIT RESULTS

### Frontend Status (✅ Complete)
- 51 TypeScript files
- 7 pages: chat, dashboard, memory, orchestration, settings, auth, root
- 21 components (UI + custom)
- 4 zustand stores
- 10+ hooks for API/WebSocket/Agent handling
- API routes: /api/backend/{health,agents,mcp,settings}
- Build: ✅ Passes

### Backend Packages (📦 Exist, Not Wired)
| Package | Files | Status |
|---------|-------|--------|
| `orchestration` | 80+ | Has MCP server (mcp_server.py), tries localhost:8765 |
| `memory_core` | 30+ | Has MCP server, not running |
| `learning_engine` | 50+ | Has MCP server, not running |
| `nx_brain_mcp` | 15+ | Main gateway, needs startup |
| `intelligence` | 15+ | Routing logic |
| `local_llm` | 10+ | GGUF inference scripts |

### The Gap
1. **No MCP server running** on port 8765
2. **Frontend calls fail** → fallback to mock data
3. **No real LLM connection** (GGUF not wired)

---

## IMPLEMENTATION PHASES

### Phase 1: MCP Gateway (Priority 1)
**Goal:** Start MCP server so frontend can connect to Python packages

| Step | Action | Effort |
|------|--------|--------|
| 1.1 | Check if nx_brain_mcp MCP server starts | Small |
| 1.2 | Add `tools_list` endpoint if missing | Small |
| 1.3 | Verify frontend → MCP connection | Small |
| 1.4 | Wire memory_core MCP to frontend | Medium |

### Phase 2: Real Backend APIs
**Goal:** Replace mock data with real Python package calls

| Step | Action | Effort |
|------|--------|--------|
| 2.1 | Fix /api/backend/agents → call MCP tools_list | Small |
| 2.2 | Fix /api/backend/memory → call memory_core | Medium |
| 2.3 | Fix /api/backend/chat → call orchestration | Medium |
| 2.4 | Fix /api/backend/orchestration → call tasks | Medium |

### Phase 3: Authentication & Real-time
**Goal:** Add auth + streaming

| Step | Action | Effort |
|------|--------|--------|
| 3.1 | Configure NextAuth provider | Small |
| 3.2 | Add JWT middleware | Small |
| 3.3 | Add SSE streaming to MCP | Medium |
| 3.4 | Replace polling with SSE in hooks | Medium |

### Phase 4: LLM Integration
**Goal:** Connect GGUF inference for actual chat

| Step | Action | Effort |
|------|--------|--------|
| 4.1 | Verify GGUF server running (8086/8088) | Small |
| 4.2 | Create inference MCP gateway | Medium |
| 4.3 | Wire chat → LLM | Medium |
| 4.4 | Add model selection/routing | Medium |

### Phase 5: Gold Standard Features
**Goal:** Add features from industry research

| Feature | Complexity | Priority |
|---------|------------|----------|
| Model Selection UI | Medium | 1 |
| Hybrid Codebase Indexing (AST+Vector) | High | 2 |
| MCP Integration | Medium | 3 |
| Project Rules/Memory | Medium | 4 |
| Inline Editing (Cmd+K) | Low-Medium | 5 |
| Git Integration | Medium | 6 |
| Multi-File Agent Mode | High | 7 |
| Terminal Integration | Medium | 8 |
| Background Agents | High | 9 |
| Codebase Visualization | High | 10 |

---

## CURRENT STATE (UPDATED: 2026-04-12)

### What We've Accomplished ✅

| Component | Status | Details |
|-----------|--------|---------|
| MCP Server (port 8765) | ✅ Running | Fixed dead code, now running |
| HTTP Gateway (port 8766) | ✅ Running | All endpoints working |
| Frontend → Gateway | ✅ Connected | API routes updated to 8766 |
| Frontend Build | ✅ Passes | `npm run build` succeeds |
| /tools_list endpoint | ✅ Working | Returns 10 agents |
| /system_health_check | ✅ Working | Returns connections |

### Current Architecture

```
Frontend (Next.js)          HTTP Gateway          MCP Server          Python Packages
┌─────────────┐            ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐
│ API Routes  │───────X───►│ localhost:8766│───►│ localhost:8765│──►│ memory_core      │
│ (port 3000) │            │ /tools_list   │    │ (stdio/SSE)   │    │ orchestration    │
│             │            │ /health_check │    └──────────────┘    │ learning_engine  │
│ Mock Data   │            │ /memory_*     │                          │ intelligence     │
└─────────────┘            └──────────────┘                          └──────────────────┘
```

### What's Working
- ✅ HTTP Gateway running on port 8766
- ✅ MCP server running on port 8765 (fixed from previous shutdown bug)
- ✅ Frontend build passes
- ✅ Basic endpoints (/, /tools_list, /system_health_check)

### What's NOT Connected (Next Steps)
1. Real MCP tool calls (gateway returns stubs)
2. memory_core package (need actual implementation)
3. learning_engine package (need actual implementation)
4. GGUF inference (not wired to chat)
5. Authentication (NextAuth not configured)

---

## IMMEDIATE NEXT STEPS (Priority Order)

### Priority 1: Fix Real MCP Tool Calls
- [x] HTTP Gateway running on port 8766 ✅
- [x] MCP Server running on port 8765 ✅
- [ ] Make HTTP gateway actually call MCP server tools (MCP uses stdio, not HTTP)
- [ ] Implement actual memory operations (not stubs)
- [ ] Test end-to-end: frontend → gateway → MCP

### Priority 2: Wire Backend Packages
- [ ] Connect memory_core to HTTP gateway
- [ ] Connect learning_engine to HTTP gateway
- [ ] Add actual tool implementations

### Priority 3: LLM Integration
- [ ] Verify GGUF server running
- [ ] Wire chat to GGUF inference
- [ ] Add model selection UI

### Priority 4: Auth & Streaming
- [ ] Configure NextAuth
- [ ] Add SSE for real-time

---

## SUCCESS CRITERIA (Updated)

| Metric | Status |
|--------|--------|
| Frontend → Backend | ✅ Connected via HTTP Gateway |
| Mock data | ⚠️ Still fallback (need real implementations) |
| Chat → LLM | ❌ Not wired |
| Memory → SQLite | ❌ Not wired |
| Agents → Execute | ⚠️ Gateway returns stubs |
| Build | ✅ Passes |