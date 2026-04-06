# Masterplan: Local LLM + MCP Integration (Rosetta Stone)

## Problem

Local Ollama models (`qwen2.5-coder:7b`, `llama3.2:3b`) **cannot use your 12 MCPs** because:
- Ollama models lack native tool/function calling capability
- They weren't trained to output structured JSON tool calls
- OpenCode infrastructure expects tool-calling from the model itself

## What We Found

### Rosetta Stone Files (✅ Already Copied)
| File | Lines | Purpose |
|------|-------|---------|
| `src/tools/rosetta_stone.py` | 169 | Basic sync wrapper - parses JSON tool calls from model output |
| `src/tools/rosetta_stone_v2.py` | 250 | Enhanced async wrapper with LLM-assisted fallback parsing |

### Pipeline Integration Point
- `src/brain/pipeline.py` has placeholder for `tool_wrapper` (lines 29-38)
- Currently: `self.tool_wrapper = None` — **NOT ACTIVE**
- Need to integrate Rosetta Stone at this point

### Your MCPs (from opencode.json)
```
sequential-thinking, memory, context7, filesystem, fetch, git
athena-context, trigger-guardian, nx-mind, athena, github
unified-memory
```

## Solution Architecture

```
User Request
    ↓
OpenCode Agent (Sisyphus/Hephaestus)
    ↓
BrainPipeline.pre_execute() ← Entry point
    ↓
[NEW] RosettaStone Integration Layer
    ↓
Local Ollama Model (qwen2.5-coder:7b)
    ↓
Parse response → Extract tool call
    ↓
Execute MCP tool via Python SDK
    ↓
Return result to model → Continue conversation
```

## Implementation Plan

### Phase 1: Create Integration Layer
**File**: `src/brain/local_llm_wrapper.py` (NEW)

```python
# Wraps RosettaStoneV2 for brain.py integration
# - Converts MCP tool schemas to Rosetta format
# - Handles async execution
# - Returns tool calls in pipeline-compatible format
```

### Phase 2: Integrate into Pipeline
**Edit**: `src/brain/pipeline.py`
- Import the new wrapper
- Use in `pre_execute()` when local model is selected
- Pass MCP tool schemas to Rosetta Stone

### Phase 3: Create Tool Schema Converter
**File**: `src/brain/mcp_tool_registry.py` (NEW)
- Reads MCP config from opencode.json
- Converts MCP tool definitions to OpenAI-compatible schema
- Feeds to Rosetta Stone

### Phase 4: Test End-to-End
- Send prompt requiring MCP tool (e.g., "search memory for X")
- Verify: local model → Rosetta Stone parses → MCP executes → result returned

## File Changes Summary

### Create (NEW)
1. `src/brain/local_llm_wrapper.py` - Rosetta Stone integration
2. `src/brain/mcp_tool_registry.py` - MCP to tool schema converter

### Modify (EXISTING)
1. `src/brain/pipeline.py` - Activate tool wrapper in pre_execute()

### Already Ready
1. `src/tools/rosetta_stone.py` ✅ (copied from CATALYST)
2. `src/tools/rosetta_stone_v2.py` ✅ (copied from CATALYST)

## Testing Strategy

### Unit Test (Rosetta Stone alone)
```bash
cd src/tools
python3 rosetta_stone.py  # Should parse calculator tool call
```

### Integration Test (Pipeline + MCP)
```python
# Send: "Search memory for 'authentication'"
# Expected: 
#   1. Rosetta parses → tool_call("memory_search", {"query": "authentication"})
#   2. MCP executes → returns results
#   3. Model continues with result
```

## Risk & Mitigation

| Risk | Mitigation |
|------|------------|
| Model doesn't follow JSON format | RosettaStoneV2 has LLM translator fallback |
| MCP tools unavailable | Graceful fallback to text response |
| Performance slow | Use async, cache results |

## Success Criteria

- [ ] Local Ollama can execute at least 3 MCP tools (memory, filesystem, grep)
- [ ] Response time < 5s for simple tool calls
- [ ] Graceful fallback to text when tool fails

## Next Actions

1. **Create** `src/brain/local_llm_wrapper.py` - integration layer
2. **Create** `src/brain/mcp_tool_registry.py` - schema converter  
3. **Modify** `src/brain/pipeline.py` - activate wrapper
4. **Test** - send MCP-requiring prompt

---

*Generated: 2026-04-06*
*Based on: CATALYST's working Rosetta Stone implementation*