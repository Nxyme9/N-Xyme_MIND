# MCP & Tool Naming Convention

## Current State (Confusing)

| Current Name | Problem |
|-------------|---------|
| `brain_mcp` | "brain" is vague - what does it do? |
| `memory_store` | "store" implies database, but it's an MCP |
| `nx_mind_mcp` | "nx" prefix inconsistent |
| `trigger_guardian_mcp` | Too long, unclear |
| `learning_engine` | "engine" - sounds like code, not MCP |

---

## Proposed Naming Schema

### MCP Server Names

Format: `{domain}-{type}-mcp`

| Domain | Type | New Name | Description |
|--------|------|----------|--------------|
| **context** | core | `context-core-mcp` | Active/product/user/context |
| **memory** | core | `memory-core-mcp` | Vector/graph/relational storage |
| **learning** | engine | `learning-engine-mcp` | Q-Learning routing |
| **session** | state | `session-state-mcp` | Session pool & state |
| **trigger** | guard | `trigger-guard-mcp` | Command triggers |
| **intelligence** | code | `intelligence-code-mcp` | Code quality |
| **http** | gateway | `http-gateway-mcp` | REST API |

### Tool Namespaces

Format: `{domain}.{function}`

| Current | New | Example |
|---------|-----|---------|
| `brain_mcp.memory.search` | `memory.search` | `memory.search(query="...")` |
| `brain_mcp.context.get_active` | `context.get_active` | `context.get_active()` |
| `brain_mcp.learning.route` | `learning.route_task` | `learning.route_task(task="...")` |
| `brain_mcp.fingerprint.inject` | `context.inject` | `context.inject(agent="...")` |

---

## Migration Table

| Old Name | New Name | Status |
|----------|----------|--------|
| `brain_mcp` | `context-core-mcp` | Rename |
| `memory_store` | `memory-core-mcp` | Rename |
| `learning_engine` | `learning-engine-mcp` | Keep (already good) |
| `nx_mind_mcp` | `session-state-mcp` | Rename |
| `trigger_guardian_mcp` | `trigger-guard-mcp` | Rename |
| `intelligence` package | `intelligence-code-mcp` | Rename |

---

## Implementation

**Step 1**: Rename packages (folder names)
```
brain_mcp/ → context_core_mcp/
memory_store/ → memory_core_mcp/
nx_mind_mcp/ → session_state_mcp/
trigger_guardian_mcp/ → trigger_guard_mcp/
```

**Step 2**: Update imports in code

**Step 3**: Update opencode.json MCP config

**Step 4**: Test all tools still work

---

## Why This Helps

- **clear**: `memory-core-mcp` = "the core memory system as MCP"
- **consistent**: All follow `{domain}-{type}-mcp` pattern  
- **discoverable**: Can guess tool names from package names
- **debuggable**: Easy to know which MCP is which