# N-Xyme MIND v1.0 — Layer 6: MCP Servers Implementation Plan

## Context

**Servers to implement**:
1. athena-context-mcp — 7 tools — Context injection
2. nx-mind-mcp — 7 tools — MIND state management
3. trigger-guardian-mcp — 6 tools — Trigger phrase routing
4. memory-mcp — NEW: Full memory operations
5. eval-harness-mcp — NEW: Quality gates + regression detection

**Critical Gaps**:
- Authentication layer (mcp-auth or JWT/OAuth 2.1)
- Rate limiting (token bucket per tool/client)
- Tool discovery (.well-known/mcp-server.json — SEP-2127)
- Schema validation (input/output validation on tools)
- Testing harness (mcp-jest integration or pytest plugin)
- Error code standardization (N-Xyme specific -32000 range)

**Repos to Study**:
- modelcontextprotocol/python-sdk — Official Python SDK
- prmichaelsen/mcp-auth — Multi-tenant auth
- josharsh/mcp-jest (16⭐) — MCP testing
- Puliczek/awesome-mcp-security (672⭐) — Security list

---

## 1. Server-by-Server Breakdown

### 1.1 athena-context-mcp (7 tools)

**Tools**:
1. `get_context` — Retrieve context for current session
2. `set_context` — Store context data
3. `get_memory` — Query memory system
4. `search_context` — Search across context
5. `get_skill` — Retrieve skill definition
6. `list_skills` — List available skills
7. `get_governance` — Get governance rules

**Schema**: Each tool has JSON Schema input/output validation

### 1.2 nx-mind-mcp (7 tools)

**Tools**:
1. `get_mind_state` — Get current MIND state
2. `set_mind_state` — Update MIND state
3. `get_session` — Get session data
4. `list_sessions` — List all sessions
5. `get_config` — Get configuration
6. `set_config` — Update configuration
7. `get_health` — Get health status

### 1.3 trigger-guardian-mcp (6 tools)

**Tools**:
1. `register_trigger` — Register trigger phrase
2. `unregister_trigger` — Remove trigger
3. `list_triggers` — List all triggers
4. `check_trigger` — Check if input matches trigger
5. `get_trigger_route` — Get route for trigger
6. `fire_trigger` — Manually fire trigger

### 1.4 memory-mcp (NEW)

**Tools**:
1. `memory_store` — Store memory with scope
2. `memory_retrieve` — Retrieve memory by key
3. `memory_search` — Hybrid search with reranking
4. `memory_get_history` — Get revision history
5. `memory_create_branch` — Create memory branch
6. `memory_merge_branch` — Merge branch
7. `memory_rollback` — Rollback to revision
8. `memory_get_user_memory` — Get user-scoped memories
9. `memory_get_session_memory` — Get session-scoped memories
10. `memory_conflict_check` — Check for conflicts

### 1.5 eval-harness-mcp (NEW)

**Tools**:
1. `eval_run` — Run evaluation suite
2. `eval_get_results` — Get evaluation results
3. `eval_compare` — Compare two evaluations
4. `eval_get_metrics` — Get specific metrics
5. `eval_regression_check` — Check for regressions
6. `eval_get_history` — Get evaluation history

---

## 2. MCP Protocol Implementation

**Base Server Class**:
```python
class NXymeMCPServer:
    """Base class for all N-Xyme MCP servers."""
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.prompts: Dict[str, MCPPrompt] = {}
        self.auth: Optional[AuthLayer] = None
        self.rate_limiter: Optional[RateLimiter] = None
    
    def register_tool(self, tool: MCPTool) -> None
    async def handle_request(self, request: Dict) -> Dict
    async def handle_tool_call(self, name: str, args: Dict) -> Dict
    def get_capabilities(self) -> Dict
    def get_tool_schemas(self) -> List[Dict]
```

**Authentication Layer**:
```python
class AuthLayer:
    """JWT/OAuth 2.1 authentication for MCP servers."""
    def validate_token(self, token: str) -> bool
    def get_permissions(self, token: str) -> List[str]
    def check_access(self, token: str, resource: str) -> bool
```

**Rate Limiter**:
```python
class RateLimiter:
    """Token bucket rate limiter per tool/client."""
    def __init__(self, tokens_per_second: float, max_tokens: int)
    def consume(self, client_id: str, tool_name: str) -> bool
    def get_remaining(self, client_id: str, tool_name: str) -> int
```

---

## 3. Dependencies

```
athena-context-mcp ──┬──► memory-mcp (uses memory operations)
                     │
nx-mind-mcp ─────────┤
                     │
trigger-guardian-mcp ┤
                     │
memory-mcp ──────────┤──► Layer 2 (Memory System)
                     │
eval-harness-mcp ────┘──► Layer 8 (Testing)
```

---

## 4. Implementation Order

| Wave | Task | Depends On |
|------|------|------------|
| 1 | memory-mcp | Layer 2 (Memory System) |
| 1 | athena-context-mcp | None |
| 2 | nx-mind-mcp | memory-mcp |
| 2 | trigger-guardian-mcp | None |
| 3 | eval-harness-mcp | Layer 8 (Testing) |

---

## 5. Test Strategy

- **Each server**: Tool schema validation, input/output validation, error handling
- **Auth layer**: Token validation, permission checking, access control
- **Rate limiter**: Token bucket algorithm, per-client tracking
- **Integration**: Cross-server communication, error propagation

---

## 6. Success Criteria

| Server | Criteria |
|--------|----------|
| athena-context-mcp | All 7 tools respond correctly |
| nx-mind-mcp | All 7 tools respond correctly |
| trigger-guardian-mcp | All 6 tools respond correctly |
| memory-mcp | All 10 tools respond correctly, integrates with Layer 2 |
| eval-harness-mcp | All 6 tools respond correctly |
| Auth layer | JWT validation works, permissions enforced |
| Rate limiter | Token bucket works, per-client tracking accurate |
