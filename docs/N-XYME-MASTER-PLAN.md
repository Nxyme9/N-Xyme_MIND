# N-Xyme System Master Plan

## Executive Summary

This document maps the complete N-Xyme system architecture - all MCP servers, API endpoints, configurations, and the connections between frontend and backend.

---

## 1. MCP Servers Configuration

### OpenCode MCP Configuration (`.opencode/opencode.json`)

The system defines **15 MCP servers**:

| MCP Name | Command | Package |
|----------|---------|---------|
| `sequential-thinking` | `npx -y @modelcontextprotocol/server-sequential-thinking` | npm |
| `nx-brain` | `../.venv/bin/python -m packages.brain_mcp` | packages/brain_mcp |
| `nx-session` | `python3 -m mcp_server` | packages/session_pool_mcp |
| `nx-quality` | `../.venv/bin/quality-gates-mcp` | packages/quality-gates-mcp |
| `telegram` | `../.venv/bin/telegram-mcp-wrapper` | packages/telegram-dashboard |
| `nx-pipeline` | `../.venv/bin/python -m packages.orchestration.mcp_server` | packages/orchestration |
| `notion` | `npx -y @notionhq/notion-mcp-server` | npm |
| `github` | `npx -y @beautyfree/modelcontextprotocol-server-github` | npm |
| `nx-triggers` | `../.venv/bin/python -m packages.trigger_guardian_mcp.trigger_guardian_mcp` | packages/trigger_guardian_mcp |
| `nx-context` | `../.venv/bin/python -m packages.context_store` | packages/context_store |
| `nx-memory` | `../.venv/bin/python -m packages.memory_store.mcp_server` | packages/memory_store |
| `nx-intelligence` | `../.venv/bin/python -m packages.intelligence.mcp_server` | packages/intelligence |
| `nx-learning` | `../.venv/bin/python -m packages.learning_engine.mcp_server` | packages/learning_engine |
| `nx-delegate` | `../.venv/bin/python -m packages.nx_delegate.mcp_server` | packages/nx_delegate |

### Python MCP Server Files (13 files)

| File | Package | Purpose |
|------|---------|---------|
| `packages/learning_engine/mcp_server.py` | learning_engine | Q-Learning routing |
| `packages/dictate/mcp_server.py` | dictate | Dictation MCP |
| `packages/nx_delegate/mcp_server.py` | nx_delegate | Task delegation |
| `packages/memory_store/mcp_server.py` | memory_store | Persistent memory |
| `packages/session_pool_mcp/mcp_server.py` | session_pool_mcp | Session management |
| `packages/intelligence/mcp_server.py` | intelligence | AI intelligence layer |
| `packages/orchestration/mcp_pipeline.py` | orchestration | Pipeline MCP |
| `packages/orchestration/mcp_server.py` | orchestration | Agent spawning |
| `packages/catalyst_orchestrator/mcp_server.py` | catalyst_orchestrator | CATALYST state machine |
| `packages/infrastructure/proxy/mcp_server.py` | infrastructure | Proxy MCP |

---

## 2. HTTP Gateway (Port 8766)

The `http_gateway.py` wraps MCP tools as REST endpoints.

### Endpoints

| Method | Endpoint | Handler | Backend Call |
|--------|----------|---------|--------------|
| GET | `/` | `root()` | - |
| GET | `/tools_list` | `tools_list()` | `_call_all_capabilities()` |
| GET | `/api/registry/agents` | `registry_agents()` | `_call_all_capabilities()` |
| POST | `/memory_get` | `memory_get()` | `_call_memory_search()` |
| POST | `/memory_write` | `memory_write()` | `_call_memory_write()` |
| GET | `/memory_stats` | `memory_stats()` | `_call_memory_stats()` |
| POST | `/recall_session` | `recall_session()` | `_call_recall_session()` |
| POST | `/find_context` | `find_context()` | `_call_find_context()` |
| GET | `/system_health_check` | `system_health_check()` | `_call_health_check()` |
| POST | `/route_task` | `route_task()` | `_call_learning_route_task()` |
| POST | `/orchestration_spawn` | `orchestration_spawn()` | `_call_orchestration_spawn()` |
| GET | `/orchestration_task_status/{task_id}` | `orchestration_task_status()` | `_call_orchestration_task_status()` |
| POST | `/orchestration_orchestrate` | `orchestration_orchestrate()` | `_call_orchestration_orchestrate()` |
| GET | `/orchestration_workflows` | `orchestration_workflows()` | `_call_orchestration_list_workflows()` |
| POST | `/orchestration_detect_state` | `orchestration_detect_state()` | `_call_orchestration_detect_state()` |
| POST | `/learning_record_outcome` | `learning_record_outcome()` | `_call_learning_record_outcome()` |
| GET | `/learning_recommendations/{task_description}` | `learning_recommendations()` | `_call_learning_get_recommendations()` |

---

## 3. Frontend API Routes (Next.js - Port 3000)

### 18 API Routes

| Category | Endpoint | Methods | Backend Proxy |
|----------|----------|---------|---------------|
| **Health** ||||
| | `/api/health` | GET | Internal |
| **Auth** ||||
| | `/api/auth/[...nextauth]` | GET, POST | NextAuth.js |
| **Memory** ||||
| | `/api/memory/context` | GET | http_gateway (8766) |
| | `/api/memory/recall` | GET | http_gateway (8766) |
| | `/api/memory/search` | GET | http_gateway (8766) |
| | `/api/memory/stats` | GET | http_gateway (8766) |
| | `/api/memory/unified/search` | GET | http_gateway (8766) |
| | `/api/memory/write` | POST | http_gateway (8766) |
| **Orchestration** ||||
| | `/api/orchestration/session` | GET | http_gateway (8766) |
| | `/api/orchestration/status/[taskId]` | GET | http_gateway (8766) |
| | `/api/orchestration/tools` | GET | http_gateway (8766) |
| | `/api/orchestration/workflows` | GET | http_gateway (8766) |
| **Backend** ||||
| | `/api/backend/agents` | GET | http_gateway (8766) |
| | `/api/backend/api-keys` | GET, POST | Internal |
| | `/api/backend/health` | GET | http_gateway (8766) |
| | `/api/backend/mcp` | GET | Internal |
| | `/api/backend/settings` | GET, POST | Internal |
| | `/api/backend/system-stats` | GET | Internal |

---

## 4. Frontend Hooks → Backend Connections

### Key Hooks and Their API Calls

| Hook File | API Endpoint | Backend Service |
|-----------|--------------|-----------------|
| `useOrchestration.ts` | `/api/orchestration/*` | http_gateway (8766) |
| `useMemory.ts` | `/api/memory/*` | http_gateway (8766) |
| `useAgentPolling.ts` | `/api/backend/agents` | http_gateway (8766) |
| `useSystemStatus.ts` | `/api/backend/health`, `/api/backend/system-stats` | http_gateway (8766) |
| `useChat.ts` | `/api/health` | Internal |

---

## 5. Configuration Files

### Environment Files

| File | Purpose |
|------|---------|
| `.env` | Main environment variables |
| `.env.example` | Template |
| `frontend/.env.local` | Frontend-specific |

### Frontend Config

| File | Purpose |
|------|---------|
| `frontend/src/lib/config.ts` | Centralizes backend URLs |

```typescript
// config.ts structure
config = {
  backend: {
    brainMcp: "http://localhost:8765",
    httpGateway: "http://localhost:8766",
    orchestration: "http://localhost:8766",
    modelRouter: "http://localhost:8000",
  }
}
```

### JSON Configs (`configs/`)

| File | Purpose |
|------|---------|
| `model_router.json` | Model routing |
| `tunnel_config.json` | Tunnel configuration |
| `tools_registry.json` | Tools registry |
| `proxies.json` | Proxy configuration |
| `keys.json` | API keys |
| `agent_budgets.json` | Agent budgets |

### OpenCode Config

| File | Purpose |
|------|---------|
| `.opencode/opencode.json` | Agent definitions, MCP servers, providers |

---

## 6. Provider Configuration

### Enabled Providers

| Provider | Base URL | Key Models |
|----------|----------|------------|
| `opencode` | - | minimax-m2.5-free |
| `openrouter` | openrouter.ai/api/v1 | nvidia/nemotron-3-super-120b-a12b:free |
| `anthropic` | api.anthropic.com | - |
| `google` | generativelanguage.googleapis.com | - |
| `deepseek` | api.deepseek.com | deepseek-r1 |
| `xai` | api.x.ai | grok-3-beta |
| `cohere` | api.cohere.ai | - |
| `gguf` | localhost:8088 | qwen2.5-coder-7b-q4_k_m |

### Agent Definitions (9 agents)

| Agent | Model | Role |
|-------|-------|------|
| `sisyphus` | nvidia/nemotron-3-super-120b-a12b:free | Primary orchestrator |
| `hephaestus` | qwen/qwen3-coder:free | Implementation |
| `prometheus` | nvidia/nemotron-3-super-120b-a12b:free | Plan builder |
| `atlas` | qwen/qwen3-coder:free | Plan executor |
| `oracle` | nvidia/nemotron-3-super-120b-a12b:free | Architecture reviewer (read-only) |
| `momus` | nvidia/nemotron-3-super-120b-a12b:free | Red-team reviewer (read-only) |
| `metis` | nvidia/nemotron-3-super-120b-a12b:free | Pre-planning consultant (read-only) |
| `explore` | qwen/qwen3-coder:free | Codebase search |
| `librarian` | deepseek/deepseek-r1:free | External research |

---

## 7. Port Mapping

| Port | Service | Purpose |
|------|---------|---------|
| 3000 | Next.js frontend | UI |
| 8765 | brain_mcp (MCP server) | Raw MCP tools |
| 8766 | http_gateway | REST API proxy |
| 8000 | model_router | LLM routing |
| 8088 | llama-server | Local GGUF inference |

---

## 8. Known Issues / Missing Connections

### Issues Found
1. ~~session_pool_stats returns 404~~ - FIXED - Added endpoint to http_gateway
2. ~~API response format mismatch~~ - FIXED - Memory page data mapping aligned
3. Multiple MCP definitions - Both `session_pool_mcp` and `session-pool-mcp` exist (minor)
4. ~~Frontend hooks using localhost:8000~~ - FIXED - Now use relative /api/* endpoints

### FIXED Issues
- `/api/orchestration/session` - NOW WORKS - proxies to http_gateway/session_pool_stats
- session_pool_stats endpoint added to http_gateway.py
- Frontend error messages improved for debugging

---

## 9. Orchestration Package Structure

### Key Files (100+ files in packages/orchestration/)

| File | Purpose |
|------|---------|
| `mcp_server.py` | MCP tool definitions (spawn, task_status, orchestrate) |
| `catalyst.py` | FLOW/FRICTION state machine |
| `spawn.py` | Agent spawning logic |
| `agents/registry.py` | Agent registry |
| `tasks/dispatcher.py` | Task dispatcher |
| `workers/*` | Worker pool |
| `sessions/manager.py` | Session management |

---

## 10. Action Items

### High Priority

1. **Add session_pool_stats to http_gateway** - Create endpoint to proxy to brain_mcp
2. **Verify all frontend hooks** - Ensure they point to `/api/*` not `localhost:8766`
3. **Fix memory page data mapping** - Align API response format with frontend expectations
4. **Document frontend-backend contract** - Create swagger/openapi spec

### Medium Priority

1. **Remove duplicate MCP definitions** - Consolidate session_pool_mcp / session-pool-mcp
2. **Add health checks for all services** - Ensure ports 3000, 8765, 8766, 8000, 8088 are monitored
3. **Update orchestration hooks** - Verify useOrchestration calls correct endpoints

### Low Priority

1. **Create API documentation** - Generate OpenAPI spec from http_gateway
2. **Add monitoring dashboards** - Show connection status between all services

---

## Appendix: File Paths Reference

### Frontend
- `frontend/src/lib/config.ts`
- `frontend/src/hooks/useOrchestration.ts`
- `frontend/src/hooks/useMemory.ts`
- `frontend/src/app/api/*/route.ts`

### Backend
- `packages/http_gateway.py`
- `packages/brain_mcp/`
- `packages/orchestration/mcp_server.py`
- `packages/memory_store/mcp_server.py`
- `packages/learning_engine/mcp_server.py`

### Config
- `.opencode/opencode.json`
- `frontend/src/lib/config.ts`
- `configs/*.json`
- `.env`, `.env.example`

---

*Generated: 2026-04-16*
*Version: 1.0*