# N-Xyme MIND: Unified Personal AI System Plan

## Vision
Replace OpenCode + OMO + BMAD with a single `nx-mind` command that does EVERYTHING better with total control.

## Current State Analysis

### What We Have (N-Xyme_MIND)
```
packages/
├── nx_mcp/              # ✅ nx_delegate (working)
├── orchestration/       # ✅ weighted_injector
├── learning_engine/    # ✅ SICA, RL, multi_reward_router
├── data_collection/   # ✅ trajectory_collector
├── memory_core/       # Memory system
├── intelligence/      # Router system
└── nx_brain_mcp/      # Brain functionality
```

### What We Need to Keep (FRANKENSTEIN)
| Source | Keep | Why |
|--------|------|-----|
| **OpenCode** | CLI entry, MCP config, TUI | Proven entry point |
| **OMO** | Agent definitions, hook system, categories | 11 agents, working patterns |
| **Anthropic** | Tool system, state management, session handling | 804K LOC of production code |
| **N-Xyme** | Learning, routing, memory | Our custom innovations |

---

## Architecture: N-Xyme MIND

```
┌─────────────────────────────────────────────────────────────┐
│                    N-XYME MIND ENTRY POINT                  │
│                     nx-mind [command]                       │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   CLI LAYER   │   │   MCP SERVERS   │   │   TOOL SYSTEM   │
│ (Go/TypeScript│   │   (Python/Py)    │   │  (Anthropic-    │
│  from OpenCode│   │   from N-Xyme   │   │   inspired)     │
└───────────────┘   └─────────────────┘   └─────────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION ENGINE                     │
│              (Hook-based like OMO + Learning)               │
│  • agent_manager   • hook_system   • task_delegate          │
│  • weighted_injector (our) • trajectory (our)               │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   12 AGENTS   │   │  LEARNING ENGINE │   │   MEMORY BANK   │
│ (from OMO)    │   │  (SICA+RL+N-gram)│   │  (semantic+     │
│ • Sisyphus    │   │  (from N-Xyme)  │   │   episodic)     │
│ • Hephaestus  │   │                  │   │  (from N-Xyme)  │
│ • Oracle      │   │                  │   │                  │
│ • etc.        │   │                  │   │                  │
└───────────────┘   └─────────────────┘   └─────────────────┘
```

---

## Implementation Plan

### Phase 1: Entry Point (Week 1)
- [ ] Create `nx-mind` CLI in Go (like OpenCode main.go)
- [ ] Integrate with existing N-Xyme packages via subprocess or binding
- [ ] Basic command: `nx-mind "task description"`

### Phase 2: Agent System (Week 2)
- [ ] Port 12 OMO agents to Python (clean implementations)
- [ ] Create hook system (like OMO's 55 hooks)
- [ ] Categories: quick, deep, visual, routing, writing

### Phase 3: Learning Integration (Week 3)
- [ ] Connect nx_delegate as primary routing
- [ ] Integrate weighted_injector
- [ ] Connect trajectory_collector
- [ ] SICA + RL loop

### Phase 4: Memory & Context (Week 4)
- [ ] Semantic memory (existing)
- [ ] Episodic memory (existing)
- [ ] Session context (from Anthropic)
- [ ] Long-term learning

### Phase 5: Tool System (Week 5)
- [ ] File operations (from Anthropic)
- [ ] Bash/Shell (from OpenCode)
- [ ] MCP integration (from OpenCode)
- [ ] Custom tools from N-Xyme

---

## Key Files to Create

```
nx-mind/
├── cmd/
│   └── main.go           # Entry point
├── src/
│   ├── agents/           # 12 ported agents
│   ├── orchestration/    # Hook + task system
│   ├── tools/            # Tool definitions
│   ├── memory/           # Context management
│   └── learning/         # Our innovations
├── packages/             # Python integration
│   ├── nx_mcp/          # Our delegate
│   ├── learning_engine/ # SICA + RL
│   └── memory_core/     # Our memory
└── scripts/
    └── nx-mind.sh       # Terminal launcher
```

---

## Commands

```bash
# Basic usage
nx-mind "implement JWT auth"

# With mode
nx-mind "fix the bug" --mode=fast
nx-mind "design UI" --mode=visual

# Interactive
nx-mind --interactive

# Agent selection
nx-mind "refactor" --agent=hephaestus
```

---

## Why This Beats Everything Else

| Feature | OpenCode | OMO | BMAD | N-Xyme MIND |
|---------|----------|-----|------|-------------|
| Entry point | ✅ | ❌ | ❌ | ✅ Our CLI |
| Learning | ❌ | ❌ | ❌ | ✅ SICA+RL |
| Memory | ❌ | ❌ | ❌ | ✅ Full |
| Agents | ❌ | ✅ | ❌ | ✅ Ported |
| Hooks | ❌ | ✅ | ❌ | ✅ Enhanced |
| Total control | ❌ | ❌ | ❌ | ✅ 100% |

---

## Next Steps

1. **Approve this plan** 
2. **Start Phase 1**: Create Go entry point
3. **Iterate**: Each phase builds on previous

**Shall I start implementing Phase 1?**