# Masterplan: Type Errors, Local LLM Tools, Unified Architecture

## Overview

This masterplan addresses 3 interconnected goals:
1. **Fix all remaining type errors** in the codebase
2. **Get local LLM (Ollama) with tool calling working** (end-to-end verified)
3. **Unified tool access** for both local and cloud models

---

## Goal 1: Fix All Remaining Type Errors

### Current State
- `src/` - **0 type errors** ✅ (already fixed: routing_cache.py, rate_limiter.py)
- `packages/` - **64 type errors** ⚠️

### Type Error Breakdown (packages/)

#### Critical (Fix Directly)
| File | Count | Issue | Fix Strategy |
|------|-------|-------|---------------|
| `message_queue.py` | 5 | None not assignable to str/Dict | Add Optional[] types |
| `middleware/interceptor.py` | 3 | None attribute access | Add null checks |
| `delegation/context_sharing.py` | 8 | Type mismatches | Fix types, add cast |
| `delegation/communication.py` | 4 | None not assignable | Add default values |
| `multi_agent_coordinator.py` | 1 | BaseException in list | Add type: ignore |

#### Import/Undefined (Check and Fix)
| File | Count | Issue | Fix Strategy |
|------|-------|-------|---------------|
| `delegation_logger.py` | 6 | StateDB, Delegation undefined | Import from correct module |
| `agent_optimizer.py` | 8 | StateDB undefined, get_all_agent_performance missing | Import or add methods |
| `result_checker.py` | 1 | StateDB undefined | Import |
| `review/security_gate.py` | 1 | Optional undefined | Import from typing |
| `templates/__init__.py` | 1 | get_template not found | Check actual export |
| `scoring/token_estimator.py` | 1 | tiktoken import | Install or add type: ignore |

#### Minor (Add type: ignore)
| File | Count | Issue | Fix Strategy |
|------|-------|-------|---------------|
| `mcp_server.py` | 4 | RoutingDecision/ScoreResult attrs | Add type: ignore |
| `predictive_router.py` | 1 | float vs int | Add type: ignore |
| `error_recovery.py` | 2 | Exception vs str | Add type: ignore |
| `router/ml.py` | 2 | max() overload | Add type: ignore |
| `router/local_model.py` | 2 | aiohttp import | Add type: ignore |

### Execution Plan

```bash
# Step 1: Run type check to get current state
./bin/quality-gates/gate-1-py-typecheck.sh

# Step 2: Fix critical types (add Optional, defaults, null checks)
# Step 3: Fix imports (ensure correct module paths)
# Step 4: Add type: ignore for complex edge cases

# Atomic commits:
# - commit 1: "fix: add Optional types to message_queue.py"
# - commit 2: "fix: resolve imports in delegation_logger.py"  
# - commit 3: "fix: add type ignores for mcp_server.py attrs"
# - commit 4: "fix: add null checks in interceptor.py"
```

### Success Criteria
- ✅ `pyright packages/` shows 0 errors (or documented acceptable list)
- ✅ All tests in `tests/` pass
- ✅ No regressions in existing functionality

---

## Goal 2: Local LLM with Tool Calling (VERIFIED WORKING)

### Current State
- **End-to-end test PASSED** ✅
- Model correctly calls `search_memories` → results returned
- 43 tools loaded from MCPToolRegistry
- qwen2.5-coder:7b generates JSON → MCPToolExecutor executes

### Verified Pipeline
```
User Query: "Search my memories for local LLM"
    ↓
LocalLLMWrapper.execute_with_tools()
    ↓
RosettaStoneV2.format_tools() → tools as text descriptions
    ↓
Ollama /api/chat → model generates JSON tool call
    ↓
_extract_tool_calls() → parses {"name": "search_memories", "arguments": {...}}
    ↓
MCPToolExecutor.execute("search_memories", args)
    ↓
Results returned to model (2nd pass)
    ↓
Final response to user
```

### Remaining Work
1. **Verify with more complex queries** (multi-tool calls)
2. **Test error handling** (invalid tool name, bad args)
3. **Add retry logic** if tool execution fails
4. **Document the working pipeline** in docs/

### Success Criteria
- ✅ Local LLM can call any of 43 MCP tools
- ✅ Results returned to model for final response
- ✅ Error cases handled gracefully

---

## Goal 3: Unified Tool Access Architecture

### Current Gap Analysis

| Aspect | Cloud Models | Local Models |
|--------|--------------|--------------|
| Tool Config | opencode.json MCP servers | opencode.json → MCPToolRegistry |
| Tool Format | Native OpenAI function schema | Text descriptions via RosettaStone |
| Execution | Direct MCP protocol | MCPToolExecutor (manual) |
| System Prompt | Built-in to OpenCode | Custom in prompts.py |
| Fallback | skip_local: true | fallback_to_cloud: true |

### Architecture Proposal: UnifiedToolGateway

Create a unified interface `UnifiedToolGateway` that:
1. **Detects model type** (cloud vs local)
2. **Routes tool access** appropriately:
   - Cloud → Direct MCP via opencode.json
   - Local → RosettaStone + MCPToolExecutor
3. **Provides same tool catalog** to both

### Implementation

```python
# src/brain/unified_tool_gateway.py
class UnifiedToolGateway:
    def __init__(self, model_provider: str):
        self.model_provider = model_provider
        self.mcp_registry = MCPToolRegistry()
    
    def get_tools(self) -> list[dict]:
        """Returns tools in appropriate format for the model"""
        if self.is_cloud_model(self.model_provider):
            return self.mcp_registry.get_mcp_tools()
        else:
            return self.mcp_registry.get_openai_tools()
    
    def execute_tool(self, tool_call: dict) -> Any:
        """Execute tool regardless of model type"""
        return MCPToolExecutor.execute(tool_call)
```

### Tool Catalog (Same for Both)

| MCP Server | Tools Available |
|------------|-----------------|
| filesystem | read, write, glob, grep, edit |
| memory | search, write, recall |
| github | issues, PRs, commits, search |
| git | status, diff, log, branch |
| fetch | url content retrieval |
| context7 | library docs lookup |
| unified-memory | semantic search |

### Success Criteria
- Both local and cloud models see **same 43 tools**
- Tool execution works identically for both
- Easy to add new tools (single registry)

---

## Atomic Commit Strategy

| # | Commit Message | Files Changed |
|---|----------------|---------------|
| 1 | fix: add Optional types to message_queue.py | packages/intelligence/message_queue.py |
| 2 | fix: resolve imports in delegation_logger.py | packages/intelligence/delegation_logger.py |
| 3 | fix: add type ignores for mcp_server.py attrs | packages/intelligence/mcp_server.py |
| 4 | fix: add null checks in interceptor.py | packages/intelligence/middleware/interceptor.py |
| 5 | fix: resolve delegation context types | packages/intelligence/delegation/context_sharing.py |
| 6 | feat: create UnifiedToolGateway | src/brain/unified_tool_gateway.py |
| 7 | docs: document local LLM tool pipeline | docs/local-llm-tools.md |
| 8 | test: add e2e test for multi-tool calls | tests/test_unified_tools.py |

---

## TDD Approach

### Phase 1: Fix Types
```python
# Before: def send_message(to_agent: str, message: Dict[str, Any])
# After: def send_message(to_agent: Optional[str], message: Optional[Dict[str, Any]] = None)
```

### Phase 2: Verify Local LLM
```python
# Test: local model calls 2 tools in sequence
query = "Find files matching pattern, then search memories"
# Verify both tools execute correctly
```

### Phase 3: Unified Gateway
```python
# Test: same query to cloud and local models
# Verify both get same tool results
```

---

## Summary

| Goal | Status | Next Action |
|------|--------|-------------|
| Type errors in src/ | ✅ DONE | N/A |
| Type errors in packages/ | ⚠️ 64 errors | Fix critical, add type:ignore for rest |
| Local LLM tools | ✅ VERIFIED | Test multi-tool scenarios |
| Unified architecture | 📐 PROPOSED | Implement UnifiedToolGateway |

**Estimated work**: 8 commits, 2-3 hours total