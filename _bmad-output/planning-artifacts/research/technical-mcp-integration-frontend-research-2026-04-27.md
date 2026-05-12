# Technical Research: MCP Integration for Custom Frontends

**Research Topic**: MCP integration patterns for TUI, Web, and Desktop frontends in N-Xyme MIND ecosystem
**Date**: 2026-04-27
**Status**: Complete

## Executive Summary

This research documents the findings from auditing existing frontends and provides architectural guidance for building custom unified frontends that properly leverage ALL MCPs in the N-Xyme MIND ecosystem.

**Key Finding**: The existing frontends have partial MCP integration. A complete rebuild is recommended to achieve full MCP visibility and control.

---

## 1. MCP Landscape Analysis

### 1.1 Available MCPs

| MCP | Status | Tools | Purpose |
|-----|--------|-------|---------|
| learning_engine | ✅ OK | 9 | Q-learning, Thompson Sampling, Multi-Armed Bandits, Circuit Breakers |
| orchestration | ✅ OK | 4 | BMAD workflow orchestration, trigger management |
| intelligence | ✅ OK | 4 | Task routing, complexity scoring, agent selection |
| memory_store | ✅ OK | FAISS | Semantic search, memory recall, context injection |
| sessions | ✅ OK | 5 | Session management, pool handling |

### 1.2 MCP Access Patterns

**HTTP API (Web Backend)**:
- Base URL: `http://localhost:3000/api/`
- Endpoints: 30+ API endpoints
- Authentication: None (internal use)
- Format: JSON

**Python Direct Import**:
- Package path: `packages.orchestration.*`, `packages.learning_engine.*`
- Requires: Proper sys.path configuration

---

## 2. Frontend Audit Results

### 2.1 TUI Applications

| App | Status | Issues |
|-----|--------|--------|
| routing-dashboard.py | ✅ WORKING | None - shows 448 delegations, 99% success |
| monitoring-dashboard.py | ⚠️ SILENT | Runs but minimal output |
| platform-layer/tui/* | ❌ FAILED | Most require Textual library (not installed) |
| nx_mind_tui.py | ⚠️ PARTIAL | Import path issues (packages.nx_mcp missing) |

**Root Cause**: Textual library not installed in environment.

### 2.2 Web Frontends

| App | Status | Details |
|-----|--------|---------|
| server.py (port 3000) | ✅ WORKING | 5/5 MCPs operational, 30+ endpoints |
| dashboard.html | ✅ WORKING | React dashboard at /dashboard |
| platform-layer/dashboard/* | ✅ WORKING | Static serving works |

**Root Cause**: Fixed - added sys.path configuration to server.py

### 2.3 Desktop Applications

| App | Status | Details |
|-----|--------|---------|
| Tauri binary (release) | ✅ WORKING | Binary at src-tauri/target/release/ |
| Next.js frontend | ✅ WORKING | Runs on port 3001 (3000 busy) |
| Internal MCP services | ✅ WORKING | Brain MCP on 8765, Gateway on 8766 |

**Status**: Fully functional but runs isolated internal services.

---

## 3. Integration Patterns

### 3.1 Pattern 1: HTTP API Gateway (Recommended for Web/Desktop)

**Use Case**: Web dashboard, Tauri desktop app
**Approach**: All MCPs accessed via HTTP to localhost:3000

```
Frontend (React/Vue/Svelte)
    ↓ HTTP
localhost:3000/api/*
    ↓
MCP Clients (learning, memory, orchestration, intelligence)
```

**Advantages**:
- Language-agnostic
- Easy to debug
- Single point of entry
- Already implemented and tested

**Disadvantages**:
- Network overhead (minimal for local)
- Requires server running

### 3.2 Pattern 2: Direct Python Import (Recommended for TUI)

**Use Case**: Terminal TUI applications
**Approach**: Import MCP packages directly

```python
import sys
sys.path.insert(0, '/home/nxyme/N-Xyme_CODE/N-Xyme_MIND')

from packages.learning_engine import *
from packages.orchestration import *
```

**Advantages**:
- No server dependency
- Lower latency
- Full feature access

**Disadvantages**:
- Python-only
- Requires proper sys.path

### 3.3 Pattern 3: Hybrid (Recommended for Desktop)

**Use Case**: Tauri desktop with embedded services
**Approach**: Both HTTP API and direct import where appropriate

---

## 4. Recommended Architecture

### 4.1 Unified MCP Client Library

Create a shared `nx_mcp_client` package that provides:

```python
class NXMindClient:
    def __init__(self, mode='http'):
        if mode == 'http':
            self.learning = LearningHTTPClient(base_url='http://localhost:3000')
            self.memory = MemoryHTTPClient(base_url='http://localhost:3000')
        else:
            self.learning = LearningDirectClient()
            self.memory = MemoryDirectClient()
    
    async def route_task(self, task: str) -> dict:
        """Unified task routing across all MCPs"""
        pass
    
    async def search_memory(self, query: str) -> list:
        """Unified memory search"""
        pass
    
    async def record_outcome(self, task: str, success: bool) -> None:
        """Learning system update"""
        pass
```

### 4.2 Frontend-Specific Implementations

**TUI (Rich-based)**:
- Use direct Python import pattern
- Rich console for UI
- AsyncIO for MCP calls

**Web Dashboard**:
- Use HTTP API pattern
- React/Vue frontend
- WebSocket for real-time updates

**Desktop (Tauri)**:
- Use HTTP API to backend
- Rust backend for native features
- WebView for UI

---

## 5. Gap Analysis

### 5.1 Current Gaps

| Gap | Severity | Impact |
|-----|----------|--------|
| No unified MCP client library | HIGH | Each frontend reinventing MCP access |
| Textual not installed | MEDIUM | Cannot run most TUI apps |
| Tauri runs isolated services | MEDIUM | Duplicate MCP instances |
| No real-time updates | LOW | Poll-based only |

### 5.2 Recommended Fixes

1. **Install Textual**: `pip install textual` for TUI apps
2. **Create unified client**: Single library for all MCP access
3. **Configure Tauri**: Point to localhost:3000 instead of internal services
4. **Add WebSocket**: For real-time MCP status updates

---

## 6. Implementation Priority

### Phase 1: Foundation (Day 1)
- [ ] Install Textual library
- [ ] Create unified MCP client library
- [ ] Fix import paths in existing TUIs

### Phase 2: Web Dashboard (Day 2)
- [ ] Enhance existing dashboard at /dashboard
- [ ] Add real-time MCP status via WebSocket
- [ ] Add memory search visualization

### Phase 3: TUI (Day 3)
- [ ] Build new Rich-based TUI with unified client
- [ ] Add learning visualization
- [ ] Add memory search interface

### Phase 4: Desktop (Day 4)
- [ ] Configure Tauri to use localhost:3000
- [ ] Add native system integration
- [ ] Package for distribution

---

## 7. Conclusion

The N-Xyme MIND ecosystem has 5 operational MCPs with 30+ API endpoints. The existing frontends have partial functionality due to:

1. Missing dependencies (Textual)
2. Import path issues
3. No unified client library
4. Isolated service instances in Tauri

A systematic rebuild following the architecture above will provide full MCP integration across all three frontend types (TUI, Web, Desktop).

---

## References

- Backend: `packages/web_frontend/server.py`
- Working TUI: `packages/platform_layer/dashboard/routing-dashboard.py`
- Tauri: `nx-mind-desktop/src-tauri/`
- Learning MCP: `packages/learning_engine/`
- Memory MCP: `packages/memory_store/`