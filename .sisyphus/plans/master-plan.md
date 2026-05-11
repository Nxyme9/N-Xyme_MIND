# N-Xyme_MIND Master Plan - Complete System Inventory

> Generated: 2026-04-16
> Purpose: Gap analysis between frontend orchestration UI and actual system implementation
> Status: COMPLETE - 3 exploration agents synthesized

---

## Executive Summary

The frontend orchestration page (`/frontend/src/app/orchestration/page.tsx`) is a **v1 prototype** with:
- Hardcoded agent configs (line 123-131)
- Mock API endpoints that may not connect to real system
- No connection to actual MCP servers or Q-Learning routing

**Total System Components:**
- ~133 API endpoints across 8 layers
- 17 MCP servers configured
- 12 brain namespaces
- 10 orchestration agents
- Q-Learning routing with full outcome logging

---

## Part 1: All MCPs (17 Configured)

### Configuration Files
| File | MCP Count |
|------|-----------|
| `/opencode.json` (project root) | 17 MCPs |
| `/.opencode/opencode.json` (workspace) | 14 MCPs |

### MCP Inventory

| # | MCP Name | Connects To | Tools/Commands | Config Location |
|---|----------|-------------|----------------|-----------------|
| 1 | **nx-brain** | Brain MCP (internal) | 60+ tools across 12 namespaces | opencode.json:189-192 |
| 2 | **nx-context** | Context Store | 10 context operations | opencode.json:229-233 |
| 3 | **nx-memory** | Memory Store | 7 memory operations | opencode.json:234-238 |
| 4 | **nx-learning** | Learning Engine | 10 Q-Learning operations | opencode.json:244-248 |
| 5 | **nx-intelligence** | Intelligence Layer | 4 routing operations | opencode.json:239-243 |
| 6 | **nx-delegate** | N-Xyme Delegate | 4 delegation operations | opencode.json:249-253 |
| 7 | **nx-quality** | Quality Gates | 12 quality gates | opencode.json:199-203 |
| 8 | **nx-pipeline** | Orchestration | 4 session operations | opencode.json:209-213 |
| 9 | **nx-triggers** | Trigger Guardian | 6 trigger operations | opencode.json:224--brain228 |
| 10 | **nx-session** | Session Pool MCP | 4 session pool ops | opencode.json:194-198 |
| 11 | **sequential-thinking** | NPM package | Sequential reasoning | opencode.json:185-188 |
| 12 | **context7** | NPM package | Documentation lookup | opencode.json:305-313 |
| 13 | **fetch** | NPM package | Web fetching, search | opencode.json:314-322 |
| 14 | **github** | NPM package | GitHub integration | opencode.json:219-231 |
| 15 | **notion** | NPM package | Notion integration | opencode.json:214-222 |
| 16 | **sqlite** | SQLite MCP | 4 DB operations | opencode.json:323-334 |
| 17 | **playwright** | Playwright MCP | 5 browser operations | opencode.json:335-344 |

### nx-brain Namespaces (12)

| Namespace | Tools | Purpose |
|-----------|-------|---------|
| **memory** | 7 | Cross-session semantic memory |
| **session** | 4 | ML-native session management |
| **fingerprint** | 12 | User patterns & context injection |
| **learning** | 5 | Q-Learning routing integration |
| **mind** | 8 | Project state tracking |
| **context** | 10 | Context management |
| **intelligence** | 4 | Complexity scoring |
| **trigger** | 5 | Pattern-based triggers |
| **tunnel** | 12 | API tunneling |
| **catalyst** | 4 | Flow state detection |
| **sqlite** | 3 | Direct DB access |
| **browser** | 6 | Browser automation |

---

## Part 2: All API Endpoints (~133 Total)

### Layer 1: Frontend API Routes (Next.js - Port 3000) - 18 endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `/api/health` | GET | Frontend health check |
| `/api/backend/health` | GET | Backend health status |
| `/api/backend/mcp` | GET/POST/PUT/DELETE | MCP connection management |
| `/api/backend/agents` | GET | List registered agents |
| `/api/backend/api-keys` | GET/POST | API key management |
| `/api/backend/settings` | GET/POST | User settings |
| `/api/backend/system-stats` | GET | System stats |
| `/api/memory/write` | POST | Write memory |
| `/api/memory/search` | GET | Search memory |
| `/api/memory/recall` | GET | Recall session |
| `/api/memory/stats` | GET | Memory statistics |
| `/api/memory/unified/search` | GET | Unified search |
| `/api/orchestration/chain` | GET/POST | Workflow chain |
| `/api/orchestration/session` | GET | Session pool stats |
| `/api/orchestration/status/[taskId]` | GET | Task status |
| `/api/orchestration/tools` | GET | Available tools |
| `/api/orchestration/workflows` | GET | BMAD workflows |
| `/api/auth/[...nextauth]` | GET/POST | Authentication |

### Layer 2: HTTP Gateway (FastAPI - Port 8766) - 18 endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `/` | GET | Gateway root |
| `/tools_list` | GET | All agents/tools |
| `/api/registry/agents` | GET | Registry agents |
| `/memory_get` | POST | Search memories |
| `/memory_write` | POST | Write memory |
| `/memory_stats` | GET | Memory stats |
| `/recall_session` | POST | Recall session |
| `/find_context` | POST | Find context |
| `/system_health_check` | GET | Health check |
| `/orchestration_spawn` | POST | Spawn task |
| `/orchestration_task_status/{task_id}` | GET | Task status |
| `/orchestration_orchestrate` | POST | Run BMAD workflow |
| `/orchestration_workflows` | GET | List workflows |
| `/orchestration_detect_state` | POST | Detect FLOW/FRICTION |
| `/route_task` | POST | Route task |
| `/learning_record_outcome` | POST | Record outcome |
| `/learning_recommendations/{task}` | GET | Agent recommendations |
| `/session_pool_stats` | GET | Session pool |

### Layer 3: Web Frontend Server (FastAPI - Port 8000) - 42 endpoints

**Memory (10):** `/api/memory/{search,stats,write,recall,context,router-search,comprehensive-stats,unified/search}`

**Learning (9):** `/api/routing/{route,stats}`, `/api/learning/{record,status,retrain,recommendations,log,progress,rate-message}`

**Intelligence (4):** `/api/intelligence/{route,score,agents,history}`

**Orchestration (7):** `/api/orchestration/{spawn,status,tools}`, `/api/tools/execute`, `/api/skills/execute`, `/api/orchestration/session`

**Sessions (3):** `/api/sessions/{list,,}`

**Settings (2):** `/api/settings`

**Models (4):** `/api/models/{local,ollama,load,status}`

**Agents (6):** `/api/agents`, `/api/registry/{agents,agent-status,tools,skills,mcps}`

**Other:** Health, WebSocket, Chat proxy

### Layer 4: Frankenstein Engine (FastAPI - Port 8080) - 10 endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `/` | GET | Server info |
| `/health` | GET | Health check |
| `/v1/models` | GET | List models |
| `/v1/chat/completions` | POST | Chat completions |
| `/v1/completions` | POST | Text completions |
| `/v1/embeddings` | POST | Embeddings |
| `/slots` | GET | Slot status |
| `/slots/{slot_id}` | GET | Slot details |
| `/slots/{slot_id}/cancel` | POST | Cancel slot |
| `/metrics` | GET | Server metrics |

### Layer 5: Brain API (Python - Port 8081) - 5 endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `/health` | GET | Health check |
| `/status` | GET | Brain status |
| `/think` | POST | Brain think |
| `/embed` | POST | Generate embeddings |
| `/rosetta` | POST | Translate to actions |

### Layer 6: Infrastructure Proxy (FastAPI - Port 8080) - 6 endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `/health` | GET | Health check |
| `/v1/chat/completions` | POST | Chat completions |
| `/v1/models` | GET | List models |
| `/dashboard` | GET | Dashboard data |
| `/v1/feedback` | POST | Submit feedback |
| `/v1/feedback/rankings` | GET | Model rankings |

### Layer 7: Agent Framework (FastAPI - Port 8002) - 9 endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `/health` | GET | Health check |
| `/agents` | GET | List agents |
| `/agents/{name}` | GET | Agent config |
| `/route` | POST | Route task |
| `/status` | GET | Task statuses |
| `/tasks/{task_id}` | GET | Task status |
| `/tasks/{task_id}/cancel` | POST | Cancel task |
| `/permissions/check` | POST | Check permission |
| `/permissions/evaluate` | POST | Evaluate command |

### Layer 8: MCP Servers (stdio/SSE) - 25+ tools

**Memory MCP:** 9 tools (search, stats, recall, find_context, memory_search, memory_write, etc.)

**Orchestration MCP:** 4 tools (spawn, task_status, orchestrate, detect_state)

**Delegate MCP:** 4 tools (nx_delegate, nx_delegate_with_id, record_outcome, health_check)

**Learning MCP:** 10 tools (record_outcome, route_task, execute_hybrid, status, retrain, etc.)

**Intelligence MCP:** 4 tools (route, score_complexity, available_agents, get_routing_history)

---

## Part 3: All Settings

### Frontend Settings (in orchestration page.tsx)

**Agent Config (lines 123-131):**
```typescript
const DEFAULT_AGENTS: AgentConfig[] = [
  { id: "hephaestus", name: "Hephaestus", role: "Implementation", ... },
  { id: "oracle", name: "Oracle", role: "Architecture Review", ... },
  { id: "explore", name: "Explore", role: "Codebase Search", ... },
  { id: "librarian", name: "Librarian", role: "External Research", ... },
  { id: "prometheus", name: "Prometheus", role: "Plan Builder", ... },
  { id: "momus", name: "Momus", role: "Adversarial Review", ... },
  { id: "atlas", name: "Atlas", role: "Plan Executor", ... },
]
```

**Node Styles (lines 139-200):**
- source, orchestrator, agent, router, splitter, aggregator, llm, tool

**Color Options:** #ef4444, #f97316, #f59e0b, #22c55e, #3b82f6, #8b5cf6

### Backend Settings

**Q-Learning Routing (`nx_routing.py`):**
```
Agent Pool Sizes: {"hephaestus": 3, "explore": 2, "oracle": 1, ...}
Q-Table: Agent × Complexity (L1-L5)
Epsilon-greedy: 10% exploration
```

**WorkerPool (`pool.py`):**
- Default timeout: 300s
- Max retries: 3
- Heartbeat monitoring enabled

**Catalyst State Machine (`catalyst.py`):**
- FLOW: reaction_time < 3000ms, message_length < 500
- FRICTION: reaction_time > 8000ms, message_length > 1000
- ADAPT: Transitional state

**Fractal Delegation:**
- Max depth: 3
- Max parallel agents: 8

---

## Part 4: Orchestration Components

### Agent Types (10)

| Agent | Role | Pool Size | Default Model |
|-------|------|-----------|---------------|
| hephaestus | Implementation | 3 | GPT-4o |
| oracle | Architecture Review | 1 | Claude 3.5 Sonnet |
| explore | Codebase Search | 2 | GPT-4o |
| librarian | External Research | 1 | Claude 3.5 Sonnet |
| prometheus | Plan Builder | 1 | GPT-4o |
| momus | Adversarial Review | 1 | Gemini 1.5 Pro |
| atlas | Plan Executor | 1 | GPT-4o |
| sisyphus | Master Orchestrator | 1 | minimax-m2.5-free |
| catalyst | Flow State Orchestrator | 1 | minimax-m2.5-free |
| metis | Pre-planning | 1 | - |

### Orchestration Flow

```
User Input
    ↓
Catalyst (UserStateDetector) → FLOW/FRICTION/ADAPT
    ↓
nx_delegate() → UnifiedDelegationRouter
    ↓
nx_routing.route_task() → Q-Learning (L1-L5 complexity)
    ↓
spawn() → fast_inject_context() (500 token budget)
    ↓
WorkerPool.submit_task() → AgentWorker
    ↓
record_outcome() → Q-Learning update
    ↓
brain_mcp.memory_store → semantic storage
```

### Key Files

| Component | File Path |
|-----------|-----------|
| Spawn Entry | `packages/orchestration/spawn.py` |
| Worker Pool | `packages/orchestration/agents/pool.py` |
| Agent Worker | `packages/orchestration/agents/worker.py` |
| Agent Registry | `packages/orchestration/agents/registry.py` |
| Catalyst | `packages/orchestration/catalyst.py` |
| Q-Learning Routing | `packages/nx_routing.py` |
| Delegate | `packages/nx_delegate/nx_delegate.py` |
| Brain MCP | `packages/brain_mcp/__init__.py` |

---

## Part 5: Gap Analysis

### Frontend vs Reality

| Component | Frontend Has | Reality | Gap |
|-----------|-------------|---------|-----|
| **Agent Config** | Hardcoded 7 agents (line 123-131) | 10+ agents in registry | Static vs Dynamic |
| **API Calls** | `/api/orchestration/spawn` | Calls spawn.py but timeout may fail | May not connect |
| **Workflows** | `/api/orchestration/workflows` | Loads from `_bmad/catalyst/workflows/` | Path must exist |
| **Memory** | `/api/memory/*` | Uses memory_store but 7 sources | Not all sources used |
| **Session** | `/api/orchestration/session` | Uses WorkerPool | Should work |
| **Learning** | No frontend connection | Q-Learning in nx_routing.py | NOT HOOKED |
| **Fingerprint** | No frontend connection | 500 token context injection | NOT HOOKED |
| **Catalyst State** | No frontend display | FLOW/FRICTION detection | NOT HOOKED |

### What Works

- ✅ Health checks (frontend → backend)
- ✅ Session pool stats
- ✅ MCP listing
- ✅ Task status polling
- ✅ Memory search/write (basic)

### What Needs Fixing

1. **Agent Registry Sync** - Frontend hardcodes, should fetch from registry
2. **Q-Learning Integration** - No frontend shows routing decisions
3. **Fingerprint Context** - No UI for user preference injection
4. **Catalyst State Display** - No FLOW/FRICTION indicator in UI
5. **Workflow Execution** - Chain DAG exists but may not trigger real agents
6. **Outcome Logging** - No visibility into learning system

---

## Part 6: Action Items

### High Priority

1. **Hook Agent Registry**
   - Fetch agents from `packages/orchestration/agents/registry.py`
   - Replace hardcoded DEFAULT_AGENTS with dynamic list

2. **Add Q-Learning Display**
   - Show routing decisions in UI
   - Display confidence scores
   - Show L1-L5 complexity indicator

3. **Connect Catalyst State**
   - Add FLOW/FRICTION indicator to header
   - Show current state with color coding

4. **Fix Memory Integration**
   - Use all 7 memory sources
   - Add unified search endpoint

### Medium Priority

5. **Workflow Execution Fix**
   - Verify `_bmad/catalyst/workflows/` path
   - Test actual agent spawning

6. **Outcome Logging UI**
   - Show success/failure rates
   - Display learning progress

7. **Session Fingerprint**
   - Add user preference display
   - Show injected context tokens

### Low Priority

8. **Model Selection**
   - Connect to model registry
   - Show available GGUF models

9. **Quality Gates Integration**
   - Display gate status in UI
   - Show test results

---

## Conclusion

The frontend orchestration page is a **v1 prototype** that needs modernization to connect to the real N-Xyme_MIND system. The backend has full Q-Learning routing, session management, memory, and catalyst state detection - but the frontend doesn't utilize most of these capabilities.

**Next Steps:**
1. Start with high priority fixes (Agent Registry, Q-Learning Display, Catalyst State)
2. Verify backend endpoints are actually running
3. Add integration tests to confirm connectivity
4. Iterate on medium/low priority items

---

*Document generated from 3 parallel exploration agents*
*Total findings: 133 endpoints, 17 MCPs, 12 brain namespaces, 10 agents*