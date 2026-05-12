# N-Xyme MIND Frontend Master Plan
## Industry-Standard Cutting-Edge Frontend Synthesis

**Generated:** April 2026  
**Purpose:** Complete frontend overhaul for AI agent orchestration platform

---

## Executive Summary

Your project already has a solid foundation with **React 19 + Vite 8** in `telegram-dashboard`. The goal now is to elevate it to industry-standard cutting-edge with modern patterns.

**Recommendation:** Next.js 15 + React 19 + TanStack Query + Zustand + Shadcn/UI

---

## Current State Analysis

### Existing Frontend (What We Have)

| Package | Tech Stack | Status | Purpose |
|---------|-----------|--------|---------|
| `telegram-dashboard` | React 19 + Vite 8 + Telegram UI | **ACTIVE** | Primary SPA |
| `web_frontend` | Vanilla HTML/CSS + FastAPI | Legacy | Deprecated |
| `platform_layer/dashboard` | Python TUI + HTML | Active | Monitoring |

### API Backend (FastAPI on port 3000)

- 50+ endpoints for agents, memory, routing, learning, orchestration, MCP
- Real-time MCP servers (memory, learning, intelligence, orchestration)
- GGUF inference engine integration

---

## Recommended Tech Stack

### Framework: Next.js 15 (App Router) + React 19

**Why Next.js for AI Agent Platforms:**
- Server Components with streaming for real-time agent output
- API Routes as gateway to existing FastAPI backend
- WebSocket/SSE support for live agent updates
- Excellent DX with Turbopack

**Migration Path:** Keep React 19 components from `telegram-dashboard`, port to Next.js app directory structure.

### State Management

| Layer | Tool | Purpose |
|-------|------|---------|
| Server State | TanStack Query v5 | API caching, polling, mutations |
| Client State | Zustand | Agent state, UI state, sessions |
| Real-time | WebSocket + queryClient | Live MCP updates |

### UI Components: Shadcn/UI + Radix

- Beautiful, accessible components
- Dark theme by default (matches your existing UI)
- Tailwind CSS for styling
- Easy customization

**Alternative:** Keep Telegram UI components if they're working well.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    NEXT.JS FRONTEND (port 3001)               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Pages     │  │ Components  │  │   Stores    │            │
│  │ /dashboard  │  │ AgentCard   │  │useAgentStore│            │
│  │ /orchestra  │  │ MCPDebug    │  │useMCPStore  │            │
│  │ /memory     │  │ TaskGraph   │  │useTaskStore │            │
│  │ /chat       │  │ RouteViz    │  │useRouteStore│            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│         │                │                │                   │
│         └────────────────┴────────────────┘                   │
│                          │                                     │
│               ┌─────────▼─────────┐                          │
│               │ TanStack Query   │                          │
│               │ + WebSocket      │                          │
│               │ (Real-time)      │                          │
│               └─────────┬─────────┘                          │
└──────────────────────────┼────────────────────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        │       FASTAPI BACKEND (port 3000)  │
        │  ┌──────────────┐  ┌────────────┐ │
        │  │ REST API     │  │ Static     │ │
        │  │ 50+ endpoints│  │ Files     │ │
        │  └──────────────┘  └────────────┘ │
        │         │                │         │
        │  ┌──────▼──────┐  ┌─────▼─────┐  │
        │  │ MCP Servers │  │  GGUF     │  │
        │  │ (5+ running)│  │ Engine    │  │
        │  └─────────────┘  └───────────┘  │
        └───────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1) - 10h
- [ ] Initialize Next.js 15 project with App Router
- [ ] Add TypeScript (NOT optional - CRITICAL)
- [ ] Install Shadcn/UI + Tailwind
- [ ] Set up TanStack Query provider
- [ ] Configure API proxy to FastAPI backend
- [ ] Set up Vitest + React Testing Library (CRITICAL)
- [ ] Basic layout with dark theme
- [ ] Add error handling (sonner toasts + error boundaries)
- [ ] Define Zustand store schemas (state shape + actions)

### Phase 2: Core Features (Week 2) - 18h
- [ ] Add authentication (NextAuth.js or JWT middleware) - CRITICAL
- [ ] Build agent dashboard cards (Sisyphus, Hephaestus, Oracle, etc.)
- [ ] Implement Zustand stores for state
- [ ] Connect to existing API endpoints
- [ ] Add MCP status monitoring
- [ ] Task queue visualization
- [ ] Add error boundaries + retry logic

### Phase 3: Real-Time (Week 3) - 20h
- [ ] **PREREQUISITE:** Add WebSocket endpoint to FastAPI server.py - BLOCKING
- [ ] Add WebSocket/SSE for live MCP updates
- [ ] Agent activity streaming
- [ ] Task progress updates
- [ ] Memory graph real-time refresh
- [ ] Implement reconnection strategy (exponential backoff)
- [ ] Graceful fallback from WebSocket to polling

### Phase 4: Advanced UI (Week 4) - 40h
- [ ] Orchestration visualization (task flow)
- [ ] Memory graph UI (Cytoscape/D3/React Flow)
- [ ] Routing decision history
- [ ] Agent delegation chain visualization
- [ ] Handle 10,000+ node graphs efficiently
- [ ] Graph search/filter + export functionality

### Phase 5: Polish (Week 5) - 20h
- [ ] Beautiful animations
- [ ] Keyboard shortcuts (like Ctrl+K)
- [ ] Responsive design
- [ ] PWA capabilities
- [ ] Performance optimization (bundle <200KB gzipped)
- [ ] Accessibility (a11y) testing

---

## Key UI Pages to Build

### 1. Dashboard (`/dashboard`)
- Agent status cards with live indicators
- Active task count
- MCP health (green/yellow/red)
- Quick actions: spawn agent, run task

### 2. Orchestration (`/orchestration`)
- Visual task flow: user → Sisyphus → delegation → agent → result
- Real-time task tree
- Agent workload visualization
- Route decision history

### 3. MCP Debug (`/mcp`)
- List all MCP servers with PID, status
- Tool invocation logs
- Request/response inspector
- Start/stop controls

### 4. Memory (`/memory`)
- Semantic + episodic memory visualization
- Search interface
- Memory graph (nodes + edges)
- Trust scores

### 5. Chat (`/chat`)
- AI chat interface (like Cursor/Windsurf)
- Streaming responses
- Tool calling UI

---

## Real-Time Updates Strategy

### Option A: Polling (Simple - Start Here)
```typescript
const { data } = useQuery({
  queryKey: ['mcp-status'],
  queryFn: () => fetch('/api/mcps/all/status').then(r => r.json()),
  refetchInterval: 5000, // Every 5 seconds
});
```

### Option B: WebSocket (Production)
```typescript
// hooks/useAgentStream.ts
export function useAgentStream() {
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:3000/ws/stream');
    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      queryClient.setQueryData(['agent-status'], update);
    };
    return () => ws.close();
  }, []);
}
```

---

## Existing Code to Reuse

| Component | Location | Reuse? |
|-----------|----------|--------|
| `telegram-dashboard/src/*` | `/packages/telegram-dashboard/` | ✅ Yes - port to Next.js |
| `web_frontend/static/index.html` | `/packages/web_frontend/static/` | ⚠️ Migrate features |
| `server.py` API endpoints | `/packages/web_frontend/server.py` | ✅ Keep - don't rewrite |

---

## Files to Create/Modify

### New Files
- `frontend/next.config.js` - Next.js config
- `frontend/package.json` - Dependencies
- `frontend/app/layout.tsx` - Root layout
- `frontend/app/page.tsx` - Home/redirect
- `frontend/app/dashboard/page.tsx` - Dashboard
- `frontend/app/orchestration/page.tsx` - Orchestration
- `frontend/stores/*.ts` - Zustand stores
- `frontend/components/*.tsx` - UI components
- `frontend/lib/api.ts` - API client

### Modify
- `packages/web_frontend/server.py` - Add WebSocket endpoint
- `.env` - Add frontend env vars

---

## Effort Estimate

| Phase | Time | Description |
|-------|------|-------------|
| Phase 1 | 10h | Next.js + TypeScript + Shadcn + TanStack + Vitest setup |
| Phase 2 | 18h | Agent cards, Zustand stores, API connect, Auth |
| Phase 3 | 20h | WebSocket (FastAPI) + real-time updates |
| Phase 4 | 40h | Advanced visualizations (memory graph, orchestration) |
| Phase 5 | 20h | Polish, error handling, animations |
| Buffer | 12h | Contingency for unknowns |
| **Total** | **~120 hours** | Full production frontend |

---

## Next Steps

### Before Starting Phase 1 (Pre-Flight Checklist)

1. [ ] **Verify FastAPI has WebSocket** - Check if `server.py` needs WebSocket endpoint added
2. [ ] **Check API authentication** - Understand how 50+ endpoints are secured
3. [ ] **Decide on design system** - Shadcn/UI OR Telegram UI (not both)

### Implementation Timeline (Corrected)

1. **Pre-Phase 1:** Add WebSocket to FastAPI backend
2. **Phase 1 (Week 1):** Next.js + TypeScript + Shadcn + Vitest foundation (10h)
3. **Phase 2 (Week 2):** Auth + agent cards + Zustand stores (18h)
4. **Phase 3 (Week 3):** Real-time WebSocket + MCP updates (20h)
5. **Phase 4 (Week 4):** Visualizations (40h)
6. **Phase 5 (Week 5):** Polish + performance (20h)

**Total: ~120 hours** (not 76h - timeline was unrealistic)

---

---

## ⚠️ Critical Review Findings (MUST FIX BEFORE PHASE 1)

### From Metis (Plan Consultant) + Momus (Plan Critic)

---

### 🔴 BLOCKER 1: No TypeScript Strategy

**Severity:** CRITICAL

The plan recommends "industry-standard cutting-edge" but doesn't mention TypeScript. Current `telegram-dashboard` has zero TS files.

- **Required Fix:** Add TypeScript from Phase 1, not as afterthought

---

### 🔴 BLOCKER 2: No Testing Strategy

**Severity:** CRITICAL

"76 hours" plan with zero mention of:
- Unit tests (Vitest/Jest)?
- Integration tests?
- E2E tests (Playwright/Cypress)?

- **Required Fix:** Add Vitest + React Testing Library in Phase 1

---

### 🔴 BLOCKER 3: FastAPI WebSocket Missing

**Severity:** CRITICAL

The plan assumes `ws://localhost:3000/ws/stream` exists, but FastAPI has NO WebSocket endpoint.

- **Required Fix:** Add WebSocket endpoint to `server.py` BEFORE Phase 3
- **Current Status:** Backend change required - not in plan

---

### 🔴 BLOCKER 4: No Authentication Strategy

**Severity:** CRITICAL

FastAPI on port 3000 has 50+ endpoints - what authentication?
- API keys? JWT? Session tokens?
- How does Next.js proxy pass credentials?

- **Required Fix:** Add NextAuth.js or JWT middleware before Phase 2

---

### 🟠 HIGH 5: Timeline Unrealistic

| Phase | Plan | Reality |
|-------|------|---------|
| Phase 1 | 8h | 10h (Shadcn setup + TypeScript) |
| Phase 2 | 16h | 18h (API reverse-engineering) |
| Phase 3 | 12h | 20h (WebSocket + reconnection) |
| Phase 4 | 24h | 40h+ (Memory graph + viz) |
| Phase 5 | 16h | 20h (Polish) |
| **TOTAL** | **76h** | **~120h** |

---

### 🟠 HIGH 6: No Error Handling Architecture

- No error boundaries mentioned
- No fallback UI for API failures
- No retry logic for TanStack Query
- No toast/notification system (sonner)

---

### 🟠 HIGH 7: Zustand Stores Undefined

```
Missing:
├── useAgentStore - what state? actions?
├── useMCPStore - what state? actions?
├── useTaskStore - what state? actions?
├── useRouteStore - what state? actions?
└── Persistence strategy - localStorage? IndexedDB?
```

---

### 🟠 HIGH 8: MCP Integration Complexity

MCP tools are LOCAL to backend, not accessible via REST:
- Need to design MCP <-> Frontend communication channel
- 5 MCP servers each with different update patterns

---

### 🟡 MEDIUM 9: No Performance Budgets

- No bundle size targets (<200KB gzipped)
- No lazy loading strategy
- No code splitting plan

---

### 🟡 MEDIUM 10: Shadcn/UI + Telegram UI Conflict

Current `telegram-dashboard` uses `@telegram-apps/telegram-ui`. Plan suggests Shadcn/UI but also says "Keep Telegram UI if working."

- **Decision needed:** Choose ONE design system

---

## ✅ Pre-Phase 1 Checklist

Before starting implementation, complete:

- [ ] **Add TypeScript** to Next.js project (Phase 1)
- [ ] **Add Vitest + Testing Library** (Phase 1)
- [ ] **Add WebSocket endpoint** to FastAPI server.py
- [ ] **Add authentication** (NextAuth.js or JWT)
- [ ] **Define Zustand store schemas** (state shape + actions)
- [ ] **Add error handling** (sonner toasts + error boundaries)
- [ ] **Correct timeline** to ~120 hours

---

## Sources

- **Explore:** Current codebase analysis (telegram-dashboard, web_frontend, platform_layer/dashboard)
- **Librarian:** Next.js 15, React 19, TanStack Query, Shadcn/UI, AI dashboard best practices
- **Oracle:** Architecture recommendation (Next.js + React + TanStack + Zustand + Shadcn/UI)
- **Metis:** Critical gaps analysis (2026-04-12)
- **Momus:** Adversarial red-team review (2026-04-12)