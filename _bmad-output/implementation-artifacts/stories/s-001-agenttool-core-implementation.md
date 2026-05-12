# Story S-001: AgentTool Core Implementation

## Status: DONE
## Epic: Epic 1 - AgentTool Core Infrastructure
## Priority: P0

### Implementation
- Created `nxyme_core/agent_tool.py` (287 lines)
- AgentTool class with spawn_subagent method
- SubagentConfig and Subagent dataclasses
- SubagentState enum for lifecycle

### Verification
```
python3 -c "from nxyme_core.agent_tool import AgentTool; t = AgentTool(); print('OK')"
```
Result: OK

### CLI Access
```
python3 -m nxyme_core.cli agent spawn --agent-type explore --prompt "test"
```