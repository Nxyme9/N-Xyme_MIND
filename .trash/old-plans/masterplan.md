# Masterplan: Fix Model Feedback Loop, TUI Integration & Prompt Engineering

## Executive Summary

This masterplan addresses three critical issues preventing local Ollama models (qwen2.5-coder:7b, llama3.2:3b) from being fully functional with OpenCode custom MCPs:

1. **Model Feedback Loop** - Model returns `{"name": "_none", "arguments": {}}` after tool execution
2. **OpenCode TUI Integration** - BrainPipeline not connected to actual UI for execution
3. **Prompt Engineering** - Need better instructions for quality responses after tool results

---

## Problem Analysis

### Issue 1: Model Feedback Loop
**Symptom**: After executing MCP tools, the model returns `{"name": "_none", "arguments": {}}` instead of natural language.

**Root Cause**:
- The model receives tool execution results but doesn't have proper instructions to convert results to response
- No second-pass generation after tool execution results are fed back
- System prompt lacks clear guidelines for "after tool execution" behavior

### Issue 2: OpenCode TUI Integration
**Symptom**: BrainPipeline exists but isn't connected to TUI for actual execution.

**Root Cause**:
- TUI uses its own message handling flow
- No bridge between TUI message input and BrainPipeline/local_llm_wrapper
- Tools are defined but not hooked into the actual execution path in TUI

### Issue 3: Prompt Engineering
**Symptom**: Model generates poor responses after tool results.

**Root Cause**:
- System prompt doesn't include "you have access to tools" instruction
- No example of "tool result → natural response" in few-shot context
- Model confused about what to do after receiving JSON tool results

---

## Solution Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INPUT                               │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  OPENCODE TUI (src/tui/)                                        │
│  - Message input handling                                       │
│  - Tool call parsing                                           │
│  - Result display                                               │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  BRIDGE: TUI → BrainPipeline (NEW)                             │
│  - Hook local_llm_wrapper into TUI message flow               │
│  - Pass tools to wrapper                                       │
│  - Handle tool execution loop                                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        ▼                                           ▼
┌──────────────────────┐                 ┌──────────────────────────┐
│ LOCAL_LLM_WRAPPER    │                 │ TOOL EXECUTION LOOP      │
│ - Rosetta Stone     │                 │ - Parse tool call       │
│ - Tool schema norm  │                 │ - Execute MCP tool      │
│ - Execute MCP=True  │                 │ - Feed result back      │
└────────┬─────────────┘                 │ - Generate response     │
         │                               └───────────┬──────────────┘
         ▼                                           │
┌──────────────────────┐                               │
│ ROSETTA STONE V2     │◄─────────────────────────────┘
│ - Tool parsing       │
│ - Model calling      │
└──────────────────────┘
         │
         ▼
┌──────────────────────┐
│ OLLAMA (local)       │
│ - qwen2.5-coder:7b   │
│ - llama3.2:3b        │
└──────────────────────┘
```

---

## Phase 1: Fix Model Feedback Loop (Priority: HIGH)

### Task 1.1: Implement Second-Pass Generation (CRITICAL FIX)
**File**: `src/brain/local_llm_wrapper.py`

**Problem**: Model executes tools but doesn't generate response after results.

**Root Cause Found**: Tool execution results are NOT fed back to model. After `MCPToolExecutor` runs, results sit in `executed` field but model never receives them for second-pass generation.

**Solution**: After tool execution, append results as `tool` role message and re-call model:

```python
async def execute_with_tools(...):
    # Pass 1: Get tool call
    result = await self.rosetta.chat_with_tools_async(...)
    
    if has_tool_calls:
        executed_results = await self._execute_mcp_tools(calls)
        
        # CRITICAL FIX: Pass 2 - Feed results back to model
        messages_with_tool_result = messages + [
            {"role": "assistant", "content": f'I will call {tool_name}'},
            {"role": "tool", "content": json.dumps(executed_results), "tool_call_id": "call_1"}
        ]
        
        # Generate final response
        final_response = await self.rosetta.chat_async(messages_with_tool_result)
        return {"type": "text", "content": final_response}
```

**Verification**:
- [ ] Model calls tool correctly
- [ ] Tool executes and returns results  
- [ ] Results fed back to model (second pass)
- [ ] Model generates natural language response (not `_none`)

---

## Research Findings (from explore/librarian/oracle)

### TUI Architecture (Explore)
- TUI is in `src/ui/tui/` (NOT `src/tui/`)
- Entry point: `ultimate_dashboard.py` - Textual-based app with modal screens
- Message flow: `on_input_submitted()` in modal screens (SearchScreen, ConfigEditorScreen)
- API client: `api_client.py` connects to Catalyst REST API at localhost:8100
- Tool execution integration: Add new modal + API endpoint

### Tool Execution Patterns (Explore)
- 3-layer pipeline: RosettaStoneV2 (parsing) → LocalLLMWrapper (execution) → MCPToolExecutor (handlers)
- Current bug: Tool results in `executed` field but NOT fed back to model for second-pass
- Agent loops in `src/orchestration/reflexion_agent.py` show full flow

### MCP Best Practices (Librarian)
- Standard pattern: Execute tool → format as `role: "tool"` message → append to conversation → re-call LLM
- Key: Message format must include `tool_call_id` to link result to call
- Best practice: Use LangChain-like AgentExecutor pattern for multi-turn tool calling

### OpenCode Integration Patterns (Librarian)
- Architecture: User Input → Context Building → LLM Request → Streaming Response → Tool Execution → Tool Results → Continue
- Event types: `content_delta`, `thinking_delta`, `tool_use_start/delta/stop`
- TUI uses Bubble Tea framework (Go) but Python version uses Textual

### Oracle Architectural Guidance
- Create NEW execution path (don't modify existing TUI or BrainPipeline)
- Add `/brain/execute` REST endpoint that calls LocalLLMWrapper
- Fix: Append tool results as `tool` role message back to messages, then re-call model
- This matches standard MCP pattern from production repos

---

### Task 1.2: Create Better System Prompt
**File**: `src/brain/prompts.py` (NEW)

**Solution**: Create optimized system prompt for tool-use scenarios.

```python
TOOL_USE_SYSTEM_PROMPT = """You are an AI assistant with access to tools.

AVAILABLE TOOLS:
{tools_description}

INSTRUCTIONS:
1. When you need to use a tool, respond with a tool call in this format:
   {"name": "tool_name", "arguments": {"arg1": "value1"}}
2. After receiving tool results, provide a natural language response to the user
3. Don't just repeat the tool output - summarize and explain the results

EXAMPLES:
User: "List files in src directory"
You: {"name": "list_directory", "arguments": {"path": "src"}}
[Tool Result: {"files": ["a.py", "b.py"]}]
You: "Found 2 files in src: a.py and b.py"

Remember: After tool execution, ALWAYS provide a helpful response, not another tool call.
"""
```

### Task 1.3: Test Feedback Loop
**File**: `tests/test_feedback_loop.py` (NEW)

**Verification**:
- [ ] Model calls tool correctly
- [ ] Tool executes and returns results
- [ ] Model generates natural language response (not another tool call)
- [ ] Response addresses user's original question

---

## Phase 2: OpenCode TUI Integration (Priority: HIGH)

### Task 2.1: Map TUI Architecture
**Files to examine**:
- `src/tui/*.py` - Find entry points
- `src/tui/handlers/` - Message handlers
- `src/mcp_server.py` - MCP server for tool definitions

**Goal**: Understand how TUI currently processes messages and where to inject BrainPipeline.

### Task 2.2: Create TUI Bridge
**File**: `src/tui/bridge.py` (NEW)

**Solution**: Bridge TUI to BrainPipeline with tool execution.

```python
class TUIBrainBridge:
    """Bridge OpenCode TUI to BrainPipeline for tool execution."""
    
    def __init__(self):
        self.pipeline = BrainPipeline()
        self.llm_wrapper = LocalLLMWrapper()
    
    async def process_message(self, user_message: str) -> str:
        """Process user message with tool execution support."""
        
        # Get available tools from registry
        tools = get_tools()
        
        # Build messages
        messages = [{"role": "user", "content": user_message}]
        
        # Execute with tools (includes feedback loop)
        result = await self.llm_wrapper.execute_with_tools(messages, tools)
        
        return result.get("content", str(result))
```

### Task 2.3: Hook into TUI Message Flow
**Files**: `src/tui/main.py`, `src/tui/handlers/message.py`

**Solution**: Replace or augment existing message handling.

```python
# In message handler
async def handle_user_message(message: str):
    bridge = TUIBrainBridge()
    
    # Check if message might need tools
    if should_use_tools(message):
        response = await bridge.process_message(message)
    else:
        response = await regular_llm_response(message)
    
    return response
```

### Task 2.4: Test TUI Integration
**Verification**:
- [ ] TUI launches without errors
- [ ] Message input triggers BrainPipeline
- [ ] Tool definitions passed to model
- [ ] Execution results displayed in TUI

---

## Phase 3: Prompt Engineering (Priority: MEDIUM)

### Task 3.1: Create Tool-Use Prompt Library
**File**: `src/brain/prompts.py`

**Prompts needed**:
1. `SYSTEM_WITH_TOOLS` - Base system prompt with tools
2. `TOOL_RESULT_SUMMARY` - How to summarize tool results
3. `ERROR_RECOVERY` - How to handle tool failures
4. `MULTI_TOOL` - Handling multiple tool calls in sequence

### Task 3.2: Optimize for llama3.2:3b
**Observation**: llama3.2:3b performs better than qwen2.5-coder:7b for tool calling.

**Solution**: Create model-specific prompts.

```python
PROMPTS = {
    "llama3.2:3b": {
        "system": LLAMA_SYSTEM_PROMPT,  # More explicit formatting
        "tool_call_format": "Use function calling format",
    },
    "qwen2.5-coder:7b": {
        "system": QWEN_SYSTEM_PROMPT,  # Different formatting
        "tool_call_format": "JSON object with name/arguments",
    }
}
```

### Task 3.3: Add Few-Shot Examples
**Solution**: Include 2-3 examples of tool use in system prompt.

```python
FEW_SHOT_EXAMPLES = [
    {
        "user": "What's in the src directory?",
        "assistant": {"name": "list_directory", "arguments": {"path": "src"}},
        "tool_result": '{"entries": ["brain", "tui", "tools"]}',
        "response": "The src directory contains three main folders: brain, tui, and tools."
    }
]
```

### Task 3.4: Test Prompt Variations
**File**: `tests/test_prompts.py` (NEW)

**Metrics to track**:
- Tool call accuracy (% of correct tool names)
- Argument accuracy (% of correct arguments)
- Response quality (natural language after results)
- Failure recovery (how model handles errors)

---

## Implementation Order

```
PHASE 1: Model Feedback Loop (Week 1)
├── Task 1.1: Second-pass generation
├── Task 1.2: Better system prompt
├── Task 1.3: Test feedback loop
└── → DELIVERABLE: Model generates response after tool execution

PHASE 2: TUI Integration (Week 2)
├── Task 2.1: Map TUI architecture
├── Task 2.2: Create TUI bridge
├── Task 2.3: Hook into TUI
└── → DELIVERABLE: TUI uses BrainPipeline for tool execution

PHASE 3: Prompt Engineering (Week 3)
├── Task 3.1: Prompt library
├── Task 3.2: Model-specific optimization
├── Task 3.3: Few-shot examples
└── → DELIVERABLE: High-quality responses after tool results
```

---

## Dependencies & Prerequisites

### External Dependencies
- Ollama running locally with models loaded
- OpenCode TUI functional

### Internal Dependencies
- [x] `src/brain/local_llm_wrapper.py` - EXISTS
- [x] `src/brain/mcp_tool_executor.py` - EXISTS
- [x] `src/brain/mcp_tool_registry.py` - EXISTS
- [x] `src/brain/pipeline.py` - EXISTS

### New Files Needed
- `src/brain/prompts.py` - Prompt library
- `src/tui/bridge.py` - TUI-BrainPipeline bridge
- `tests/test_feedback_loop.py` - Feedback loop tests
- `tests/test_prompts.py` - Prompt variation tests

---

## Testing Strategy

### Unit Tests
- `test_second_pass_generation` - Verify feedback loop works
- `test_tool_call_parsing` - Verify correct tool/args extraction
- `test_prompt_variations` - Compare prompt effectiveness

### Integration Tests
- `test_tui_bridge` - TUI → BrainPipeline → response
- `test_full_agent_loop` - User message → tool → response

### Benchmark Tests
- Tool call accuracy (llama3.2:3b vs qwen2.5-coder:7b)
- Response quality (1-5 scale on helpfulness)
- Latency (tool execution + model response)

---

## Success Criteria

| Issue | Success Metric | Target |
|-------|---------------|--------|
| Feedback Loop | Model generates response after tool execution | 100% of tool calls get response |
| TUI Integration | TUI processes messages through BrainPipeline | TUI functional with tool execution |
| Prompt Engineering | Response quality score | ≥4/5 on helpfulness |

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| qwen2.5-coder poor tool calling | HIGH | Switch to llama3.2:3b as default |
| TUI architecture complex | MEDIUM | Spend time mapping before implementation |
| Model returns `_none` | HIGH | Add explicit format instructions in prompt |

---

## Open Questions

1. **Model selection**: Should we prioritize llama3.2:3b (better tool calling) over qwen2.5-coder:7b?
2. **TUI scope**: Should we modify existing TUI or create new tool-execution mode?
3. **Fallback strategy**: What should happen if tool execution fails?

---

## Next Steps

1. **Start Phase 1** - Implement second-pass generation in `local_llm_wrapper.py`
2. **Create prompts.py** - Build prompt library with few-shot examples
3. **Test feedback loop** - Verify model generates response after tool execution
4. **Map TUI** - Understand TUI message flow before bridge implementation