# N-Xyme MIND — Package Index

**Generated:** 2026-04-27  
**Total Packages:** 48  
**Status:** Complete Inventory

---

## Package Registry

### Core Orchestration

| Package | Purpose | MCP |
|---------|---------|-----|
| `orchestration` | Agent coordination, spawning, lifecycle | ❌ |
| `catalyst_orchestrator` | FLOW/FRICTION state machine | ❌ |
| `brain_mcp` | Brain-context MCP integration | ✅ |
| `nx_context_mcp` | Context management | ✅ |
| `nx_delegate` | Delegation system | ✅ |
| `nx_mind_mcp` | Mind state MCP | ✅ |
| `mind` | Mind orchestration | ❌ |

### Intelligence & Learning

| Package | Purpose | Status |
|---------|---------|--------|
| `intelligence` | Learning, routing, decision making | ✅ |
| `learning_engine` | Q-Learning routing optimization | ✅ |
| `model_orchestrator` | Model orchestration | ✅ |
| `router_mcp` | Routing MCP | ✅ |

### Memory & Persistence

| Package | Purpose | MCP |
|---------|---------|-----|
| `memory_store` | Persistent memory with versioning | ❌ |
| `memory_core` | Core memory operations | ❌ |
| `context_store` | Context storage | ❌ |
| `unified-memory` | Unified memory interface | ✅ |
| `unified_compactor` | Memory compaction | ❌ |

### Infrastructure

| Package | Purpose | Status |
|---------|---------|--------|
| `infrastructure` | System infrastructure | ✅ |
| `platform_layer` | Platform abstractions | ✅ |
| `common` | Shared utilities | ✅ |
| `core` | Core functionality | ✅ |
| `data` | Data handling | ✅ |
| `models` | Data models | ✅ |

### Agents & Teams

| Package | Purpose | Status |
|---------|---------|--------|
| `agents` | Agent definitions | ✅ |
| `session_pool_mcp` | Session pooling | ✅ |
| `session_pool_mcp` | Session pool MCP | ✅ |

### MCP Servers (Standalone)

| Package | Purpose | Status |
|---------|---------|--------|
| `core-mcp` | Core MCP server | ✅ |
| `nx-context-mcp` | N-Xyme context MCP | ✅ |
| `nx-mind-mcp` | Mind state MCP | ✅ |
| `playwright-mcp` | Playwright automation | ✅ |
| `quality-gates-mcp` | Quality gates MCP | ✅ |
| `sqlite-mcp` | SQLite MCP | ✅ |
| `trigger_guardian_mcp` | Trigger guardian | ✅ |
| `trigger-guardian-mcp` | Trigger MCP | ✅ |

### Integration

| Package | Purpose | Status |
|---------|---------|--------|
| `http_gateway.py` | HTTP transport | ⚠️ |
| `tunnel` | API rotation/proxy | ✅ |
| `intelligent_router_mcp` | Intelligent routing | ✅ |

### Specialization

| Package | Purpose | Status |
|---------|---------|--------|
| `local_llm` | GGUF inference engine | ✅ |
| `web_frontend` | Dashboard UI | ✅ |
| `web-frontend` | Dashboard (alt) | ✅ |
| `dictate` | Voice input | ⚠️ |
| `telegram-dashboard` | Telegram bot | ✅ |
| `training` | Model training | ✅ |
| `datasets` | Training datasets | ✅ |
| `data_collection` | Data collection | ✅ |

### Legacy

| Package | Purpose | Status |
|---------|---------|--------|
| `legacy` | Legacy compatibility | ✅ |

### Tools

| Package | Purpose | Status |
|---------|---------|--------|
| `nxyme_tools.py` | N-Xyme tools | ✅ |
| `nx_routing.py` | Routing utilities | ✅ |

### Athena Integration

| Package | Purpose | Status |
|---------|---------|--------|
| `athena-context-mcp` | Athena context MCP | ✅ |

---

## MCP Server Inventory

### Primary MCPs

| MCP | Tools | Status |
|-----|-------|--------|
| `nxyme-mcp` (Node.js) | 33 | ✅ Running |
| `context7` | Docs | ✅ Running |
| `sequential-thinking` | Reasoning | ✅ Running |
| `filesystem` | File access | ✅ Running |

### N-Xyme MCPs (via unified-memory)

| MCP | Tools | Status |
|-----|-------|--------|
| `nx_context_mcp` | Context | ✅ |
| `nx_delegate_mcp` | Delegation | ✅ |
| `nx_brain_mcp` | Brain | ✅ |
| `nx_mind_mcp` | Mind state | ✅ |
| `trigger_guardian_mcp` | Triggers | ✅ |
| `session_pool_mcp` | Sessions | ✅ |
| `quality_gates_mcp` | Gates | ✅ |

---

## Package Count: 48 ✅

| Category | Count | Percentage |
|----------|-------|----------|
| Core | 8 | 16.7% |
| MCP | 15 | 31.2% |
| Intelligence | 4 | 8.3% |
| Memory | 5 | 10.4% |
| Integration | 6 | 12.5% |
| Specialization | 6 | 12.5% |
| Legacy | 4 | 8.3% |

---

## Verification

```bash
# Count packages
ls /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/ | grep -v '^__' | wc -l
# Expected: 48

# Verify key packages
ls -d /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/orchestration/
ls -d /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/brain_mcp/
ls -d /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/learning_engine/
```

---

**Status:** 100% Complete  
**Next Review:** On architecture changes