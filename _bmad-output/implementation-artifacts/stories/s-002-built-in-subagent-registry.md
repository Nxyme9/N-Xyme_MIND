# Story S-002: Built-in Subagent Registry

## Status: DONE
## Epic: Epic 1 - AgentTool Core Infrastructure

### Implementation
- AgentTool class includes get_registry() method
- Registry stores subagent configs in memory
- Pre-configured agents: explore, plan, oracle, general

### Verification
```
python3 -c "from nxyme_core.agent_tool import AgentTool; t = AgentTool(); print(t.get_registry())"
```