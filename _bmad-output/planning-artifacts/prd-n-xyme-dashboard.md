---
title: N-Xyme Dashboard - Unified Frontend
version: 1.0.0
date: 2026-04-27
author: N-Xyme MIND System
type: product-requirements
status: draft
---

# N-Xyme Dashboard - Unified Frontend PRD

## 1. Executive Summary

**Problem:** OpenCode frontend doesn't leverage our custom MCP infrastructure (learning, memory, routing, orchestration). Memory injection is broken, tool calling glitches during compaction, and we have 45+ unused MCP tools.

**Solution:** Build a unified N-Xyme Dashboard that exposes ALL our MCP capabilities through a proper web interface with real-time system monitoring, chat with full tool access, and ML lifecycle management.

**Target Users:** Developers, ML engineers, system administrators managing N-Xyme MIND ecosystem.

---

## 2. Current Ecosystem Analysis

### 2.1 What We Have (12 MCP Servers, 45+ Tools)

| MCP Server | Tools | Status | Purpose |
|------------|-------|--------|---------|
| learning_engine | 9 | Partial | Q-learning routing, outcome logging, stats |
| catalyst_orchestrator | 6 | Partial | BMAD workflow orchestration |
| session-pool-mcp | 5 | Partial | Session pooling/management |
| orchestration | 4 | Partial | General orchestration |
| intelligence | 4 | Partial | Routing, complexity scoring |
| nx_delegate | 4 | Partial | Task delegation with memory injection |
| dictate | 4 | Working | PRD generation |
| context_store | ? | Unknown | Context management |
| trigger_guardian | ? | Unknown | Command triggers |
| quality-gates | ? | Unknown | Code quality gates |
| memory_core | ? | Unknown | Unified memory |
| memory_store | ? | Unknown | Semantic memory |

### 2.2 Existing Frontend (Underutilized)

- **Location:** `/packages/web_frontend/`
- **Tech:** FastAPI on port 3000, vanilla JS frontend
- **Files:** 
  - `index.html` (3279 lines) - Basic dashboard
  - `trainer.html` (656 lines) - LLM trainer UI
- **Issues:** Doesn't integrate most MCPs, no learning visualization, limited chat

### 2.3 What's Missing

1. ❌ **Memory/Learning Dashboard** - No visualization of Q-learning stats, routing history
2. ❌ **Full MCP Integration** - Only ~40% of MCP tools exposed to frontend
3. ❌ **Proper Chat Interface** - Can't use our custom delegation + memory injection
4. ❌ **System Health Monitor** - No unified view of all services
5. ❌ **Model Router UI** - Can't see/control routing decisions
6. ❌ **Session Management UI** - Can't view/manage pooled sessions
7. ❌ **Trigger Dashboard** - Can't see/manage command triggers

---

## 3. Product Requirements

### 3.1 Core Features (Must Have)

#### F1: Unified Dashboard Home
- System status overview (all MCPs, services, health)
- Quick stats: active sessions, routing decisions, memory usage
- One-click access to all subsystems

#### F2: Learning Engine Visualization
- Real-time Q-learning routing stats
- Agent performance metrics (success rate, latency)
- Routing history with filtering
- Weight visualization

#### F3: Memory System Dashboard
- Memory source status (Graphiti, Hindsight, SQLite stores)
- Search interface for memories
- Context injection visualization
- Memory stats (episodic, semantic, procedural counts)

#### F4: Chat Interface with Full Tool Access
- Chat UI that uses nx_delegate for routing
- Memory injection during chat (context-aware)
- Tool call results display
- Session context management

#### F5: Session Pool Management
- Active session list with status
- Session utilization metrics
- Pool health and sizing controls
- Session return/cleanup controls

#### F6: Model Router Dashboard
- Current model selection and stats
- Provider health (OpenRouter, Ollama, etc.)
- Routing decision logs
- Manual model override controls

#### F7: Trigger System UI
- Registered triggers list
- Trigger activation logs
- Add/edit/remove triggers
- Handler status

#### F8: Quality Gates Dashboard
- Gate status for current project
- Test results visualization
- Coverage trends
- Lint/type check status

### 3.2 Technical Requirements

#### T1: Backend Stack
- FastAPI (existing) - expand with all MCP endpoints
- Add SSE for real-time updates
- Proper error handling and logging

#### T2: Frontend Stack
- React or Vue (modern, maintainable)
- Real-time updates via WebSocket/SSE
- Responsive design
- Dark theme (existing style)

#### T3: MCP Integration
- All MCP tools accessible via HTTP API
- Unified tool calling interface
- Error propagation from MCP to UI

#### T4: Performance
- <100ms response for dashboard data
- WebSocket for real-time updates
- Lazy loading for heavy data

---

## 4. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     N-Xyme Dashboard                        │
│                     (Port 3000/UI)                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │  Dashboard  │ │    Chat     │ │   Admin    │            │
│  │    Home     │ │  Interface  │ │    Panel   │            │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘            │
│         │               │               │                    │
│         └───────────────┼───────────────┘                    │
│                         │                                    │
│              ┌──────────┴──────────┐                        │
│              │   API Gateway        │                        │
│              │   (FastAPI)          │                        │
│              └──────────┬──────────┘                        │
│                         │                                    │
│    ┌────────────────────┼────────────────────┐              │
│    │                    │                    │              │
│    ▼                    ▼                    ▼              │
│ ┌────────┐        ┌──────────┐       ┌──────────┐          │
│ │Learning│        │ Memory   │       │ Router   │          │
│ │Engine │        │ Systems  │       │/Delegate │          │
│ │  MCP  │        │   MCP    │       │   MCP    │          │
│ └────────┘        └──────────┘       └──────────┘          │
│                                                                 │
│ ┌────────┐        ┌──────────┐       ┌──────────┐          │
│ │Session │        │Context   │       │Quality   │          │
│ │ Pool   │        │ Store    │       │ Gates    │          │
│ │  MCP   │        │   MCP    │       │   MCP    │          │
│ └────────┘        └──────────┘       └──────────┘          │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. API Endpoints Required

### 5.1 System
- `GET /api/health` - Full system health
- `GET /api/mcps` - List all MCPs and their status

### 5.2 Learning
- `GET /api/learning/stats` - Q-learning stats
- `GET /api/learning/routing-history` - Routing decisions
- `GET /api/learning/agent-performance` - Per-agent metrics
- `POST /api/learning/record-outcome` - Log outcome

### 5.3 Memory
- `GET /api/memory/stats` - Memory source stats
- `POST /api/memory/search` - Search memories
- `GET /api/memory/recall-session` - Session recall
- `POST /api/memory/inject` - Inject context

### 5.4 Chat
- `POST /api/chat/completions` - Chat with full MCP access
- `GET /api/chat/sessions` - List chat sessions

### 5.5 Sessions
- `GET /api/sessions` - List pooled sessions
- `POST /api/sessions/return` - Return session to pool

### 5.6 Routing
- `GET /api/routing/models` - Available models
- `POST /api/routing/route` - Manual routing
- `GET /api/routing/history` - Routing logs

### 5.7 Triggers
- `GET /api/triggers` - List triggers
- `POST /api/triggers/register` - Add trigger
- `GET /api/triggers/logs` - Trigger history

---

## 6. UI Components

### 6.1 Navigation
- Left sidebar with all sections
- Collapsible for compact view
- Active section highlighting

### 6.2 Dashboard Home
- 4-column stat cards (Sessions, MCPs, Routing, Memory)
- System health indicators (green/yellow/red)
- Quick action buttons

### 6.3 Learning Panel
- Charts: Routing success rate, agent latency
- Table: Recent routing decisions
- Controls: Adjust learning weights

### 6.4 Memory Panel
- Source toggles (Graphiti, Hindsight, SQLite)
- Search bar with filters
- Memory entry viewer

### 6.5 Chat Panel
- Message thread (like Slack/Discord)
- Tool call expansion panels
- Context indicator (what's injected)

### 6.6 Admin Panel
- MCP health grid
- Log viewer
- Configuration editor

---

## 7. Milestones

### M1: Foundation (Week 1)
- [ ] Expand FastAPI with all MCP endpoints
- [ ] Create basic React app structure
- [ ] Connect to learning_engine MCP
- [ ] Basic health dashboard

### M2: Core Features (Week 2)
- [ ] Learning visualization
- [ ] Memory dashboard
- [ ] Session pool UI
- [ ] Model router UI

### M3: Chat Integration (Week 3)
- [ ] Full chat interface
- [ ] nx_delegate integration
- [ ] Memory injection in chat
- [ ] Tool call display

### M4: Polish (Week 4)
- [ ] Trigger dashboard
- [ ] Quality gates panel
- [ ] Real-time updates (WebSocket)
- [ ] Performance optimization

---

## 8. Success Metrics

- ✅ All 12 MCPs accessible via dashboard
- ✅ Learning stats display within 100ms
- ✅ Chat with memory injection working
- ✅ Real-time updates via WebSocket
- ✅ Mobile-responsive

---

## 9. Open Questions

1. **Frontend framework:** React or Vue? (Vue may integrate faster with existing vanilla JS)
2. **Real-time:** WebSocket or SSE? (SSE simpler for one-way updates)
3. **Deployment:** Local only or cloud-ready? (Start local)
4. **Authentication:** Needed? (For now, localhost only)

---

## 10. Dependencies

- FastAPI (existing)
- All MCP servers in `/packages/*/mcp_server.py`
- React/Vue for frontend
- Chart.js or similar for visualizations
- WebSocket library

---

## Appendix A: MCP Tool Reference

### learning_engine (9 tools)
- record_outcome, route_task, status, get_recommendations
- learning_stats, log_outcome, get_outcomes, get_capabilities, health_check

### catalyst_orchestrator (6 tools)
- orchestrate, detect_state, list_workflows, get_orchestrator_status
- (2 more - need audit)

### session-pool-mcp (5 tools)
- session_get, session_return, session_list, session_warm, get_session

### orchestration (4 tools)
- spawn, task_status, tools_list, get_session_state

### intelligence (4 tools)
- route, score_complexity, available_agents, get_routing_history

### nx_delegate (4 tools)
- nx_delegate, nx_delegate_with_id, record_outcome, health_check

### dictate (4 tools)
- create_prd, create_architecture, create_epics, create_sprint

---