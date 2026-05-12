---
stepsCompleted: [1]
inputDocuments:
  - "_bmad-output/planning-artifacts/prd-n-xyme-dashboard.md"
  - "_bmad-output/planning-artifacts/research/technical-mcp-integration-frontend-research-2026-04-27.md"
workflowType: 'architecture'
project_name: 'N-Xyme Custom Frontends'
user_name: 'N-Xyme'
date: '2026-04-27'
---

# Architecture Decision Document

**Project:** N-Xyme MIND Custom Frontends (TUI, Web, Desktop)
**Author:** Sisyphus (Ralph Loop)
**Date:** 2026-04-27

---

## Step 1: Project Context

### Input Documents
- PRD: `prd-n-xyme-dashboard.md` - Unified dashboard requirements
- Research: `technical-mcp-integration-frontend-research-2026-04-27.md` - MCP integration patterns

### System Overview
- **MCPs**: learning_engine, orchestration, intelligence, memory_store, sessions (5/5 operational)
- **Backend**: FastAPI on port 3000 with 30+ endpoints
- **Goal**: Build custom TUI, Web, and Desktop frontends with full MCP integration

---

## Step 2: Architecture Decisions

### Decision 1: Unified MCP Client Library

**Pattern**: Create `packages/nx_mcp_client/` that provides unified interface

```python
class NXMindClient:
    def __init__(self, mode='http'):
        self.mode = mode
        if mode == 'http':
            self.base_url = 'http://localhost:3000/api'
    
    async def route_task(self, task: str) -> dict:
        """Route to best agent via intelligence MCP"""
        pass
    
    async def search_memory(self, query: str) -> list:
        """Semantic search via memory_store MCP"""
        pass
    
    async def record_outcome(self, task: str, success: bool, latency_ms: int) -> None:
        """Record for learning via learning_engine MCP"""
        pass
    
    async def get_learning_stats(self) -> dict:
        """Get Q-learning statistics"""
        pass
    
    async def get_mcp_status(self) -> dict:
        """Get all MCP status"""
        pass
```

### Decision 2: TUI Architecture

**Framework**: Rich (not Textual - not installed)
**Pattern**: Direct Python import
**File**: `nx_mind_unified_tui.py`

Components:
- `MCPClient` - direct import of MCP packages
- `RichConsoleUI` - Rich-based interactive UI
- `TaskRouter` - intelligence MCP integration
- `MemorySearch` - memory_store MCP integration
- `LearningDashboard` - learning visualization

### Decision 3: Web Dashboard Architecture

**Framework**: React (existing) + enhancements
**Pattern**: HTTP API via localhost:3000
**File**: Enhance `packages/web_frontend/static/dashboard.html`

Enhancements:
- WebSocket for real-time MCP status
- Memory search visualization
- Learning stats charts (extend existing Chart.js)
- Agent performance metrics

### Decision 4: Desktop Architecture

**Framework**: Tauri (existing binary)
**Pattern**: HTTP API to localhost:3000 (not internal services)
**Config**: Modify `src-tauri/tauri.conf.json`

Changes:
- Remove internal MCP services
- Point to localhost:3000 for all MCP access
- Add system tray integration
- Native window controls

---

## Step 3: Component Architecture

### Shared Components

| Component | Location | Purpose |
|-----------|----------|---------|
| nx_mcp_client | packages/nx_mcp_client/ | Unified MCP interface |
| mcp_types | packages/nx_mcp_client/types.py | Type definitions |

### TUI-Specific

| Component | Location | Purpose |
|-----------|----------|---------|
| rich_ui | nx_mind_unified_tui.py | Main TUI app |
| dashboard_panel | components/dashboard.py | Rich-based dashboard |
| memory_panel | components/memory.py | Memory search interface |

### Web-Specific

| Component | Location | Purpose |
|-----------|----------|---------|
| dashboard.html | packages/web_frontend/static/ | Main dashboard (extend) |
| mcp-status.js | static/js/ | Real-time MCP status |
| memory-viz.js | static/js/ | Memory visualization |

### Desktop-Specific

| Component | Location | Purpose |
|-----------|----------|---------|
| tauri.conf.json | src-tauri/ | Config update |
| main.rs | src-tauri/src/ | Native integration |

---

## Step 4: Implementation Priority

### Phase 1: Foundation (Day 1)
1. [ ] Create `packages/nx_mcp_client/` with unified client
2. [ ] Fix server.py import path (DONE)
3. [ ] Install Rich if needed

### Phase 2: TUI (Day 2)
1. [ ] Build `nx_mind_unified_tui.py` with Rich
2. [ ] Integrate all MCPs via client library
3. [ ] Test and iterate

### Phase 3: Web Enhancement (Day 3)
1. [ ] Add WebSocket for real-time updates
2. [ ] Enhance memory visualization
3. [ ] Add learning stats charts

### Phase 4: Desktop (Day 4)
1. [ ] Modify Tauri config for localhost:3000
2. [ ] Remove internal services
3. [ ] Test full integration

---

## Step 5: Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Server not running | Add startup check and auto-start |
| MCP timeout | Add retry with exponential backoff |
| Memory MCP degraded | Fallback to file-based session memory |
| Import path issues | Use absolute paths, verify on startup |

---

## Next Steps

Proceed to implementation with `bmad-quick-dev` for each component.

[C] Continue to implementation planning