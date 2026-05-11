# MASTER UNDERSTANDING: Why Context/Memory/Learning Systems Don't Reach Agents

**Generated**: 2026-04-15
**Research Type**: Exhaustive (5 parallel agents)
**Status**: ROOT CAUSE IDENTIFIED ✅

---

## EXECUTIVE SUMMARY

**The memory/learning systems WORK** - verified across 6 core systems.  
**But context NEVER reaches agent prompts** - the context is generated and stored but never read by any component that builds prompts.

**The Fix**: Use OpenCode's `rules-injector` hook (already exists!) with per-agent rules files like `agent-sisyphus.md`.

---

## ROOT CAUSE ANALYSIS

### The Pipeline (Where It Breaks)

```
User Input
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STAGE 1: CONTEXT GENERATION ✅ (Working at 6+ places)      │
├─────────────────────────────────────────────────────────────┤
│ • fingerprint.py:486 - get_full_injected_context()         │
│ • fast_memory_injector.py - Caching wrapper                │
│ • nx_delegate/mcp_server.py - nx_delegate()                │
│ • unified_pipeline.py - Stage 4                            │
│ • spawn.py - fast_inject_context()                         │
│ • orchestration/__init__.py - spawn()                       │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STAGE 2: CONTEXT STORAGE ✅ (Working at 4+ places)         │
├─────────────────────────────────────────────────────────────┤
│ • _injected_context stored in task["context"]              │
│ • memory_injection stored in enhanced_context              │
│ • All stored in Python dicts                               │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ ⚠️ STAGE 3: CONTEXT READ INTO PROMPT ❌ BROKEN            │
└─────────────────────────────────────────────────────────────┘
    ↓
    ❌ CONTEXT GENERATED BUT NEVER REACHES AGENT PROMPT
```

### Critical Findings

| Finding | Location | Impact |
|---------|----------|--------|
| `agent_type` reaches worker | worker.py:29, 198 | ✅ Available but unused |
| Default handler echoes payload | worker.py:295-297 | ❌ Never builds prompt |
| `inject_into_agent_loop()` exists | agent_loop.py:449 | ⚠️ Only if using AgentLoop.run() |
| OpenCode uses native task() | oh-my-opencode.json | ❌ Not connected to N-Xyme pipeline |

---

## CONFIGURATION CHAOS (6+ Locations)

### The Mess

| Location | Purpose | Problem |
|----------|---------|---------|
| `~/.config/opencode/opencode.json` | Base config, `instructions` for PRIMARY agent only | Instructions don't reach subagents |
| `~/.config/opencode/oh-my-openagent.json` | Agent prompts, 44 hooks, categories | 14 agents defined here |
| `~/N-Xyme_MIND/opencode.json` | Project MCP overrides | Nearly duplicate of root |
| `~/N-Xyme_MIND/.opencode/opencode.json` | DUPLICATE | Nearly identical to project root |
| `~/N-Xyme_MIND/AGENTS.md` | Workspace rules (1471 lines) | Injected on FIRST `read` tool call |
| `~/.sisyphus/` | Session state (40+ files) | Scattered state |
| `packages/brain_mcp/` | Memory/context MCPs | Working but disconnected |

### Agent Load Order

1. `opencode.json` loads (has `instructions` for PRIMARY agent only)
2. `oh-my-openagent.json` loads (has `agents.*.prompt` for agent-specific prompts)
3. `agents/*.md` load (markdown file overrides)

**CRITICAL**: `instructions` in opencode.json = PRIMARY agent only!  
**CRITICAL**: AGENTS.md injected on FIRST `read` tool call, NOT session start!

---

## THE HOOKS SYSTEM (40+ Hooks)

### Available Hooks (Key Ones for Context Injection)

| Hook | Purpose | Event |
|------|---------|-------|
| **rules-injector** | Injects rules from `.claude/rules/` based on filename patterns | `chat.message` |
| **directory-agents-injector** | Auto-injects `AGENTS.md` | `tool.execute.before` |
| **context-injector** | Consumes pending context from ContextCollector | `chat.message` |
| **directory-readme-injector** | Auto-injects `README.md` | `tool.execute.before` |

### Per-Agent Context Injection (EXISTING MECHANISM!)

Create files in `~/.claude/rules/` or `~/.config/opencode/rules/`:

| Filename | When Injected |
|----------|---------------|
| `agent-sisyphus.md` | Only when Sisyphus is active |
| `agent-hephaestus.md` | Only when Hephaestus is active |
| `agent-oracle.md` | Only when Oracle is active |
| `always.md` | Always injected |
| `once.md` | Injected only once per session |

### Rule File Format

```markdown
---
paths:
  - "src/**/*.ts"
globs:
  - "**/api/**/*.ts"
---
# Your context/rules here
```

### Hook Execution Order (chat.message)

```
1. keywordDetector
2. claudeCodeHooks
3. autoSlashCommand
4. context-injector ← YOUR INJECTED CONTEXT
5. rules-injector
6. directory-readme-injector
7. directory-agents-injector
```

---

## THE SOLUTION (Already Built Into OpenCode!)

### Option A: Per-Agent Rules Files (RECOMMENDED ✅)

**Create these files:**

```
~/.claude/rules/
├── agent-sisyphus.md      # Sisyphus-specific context
├── agent-hephaestus.md    # Hephaestus-specific context
├── agent-oracle.md        # Oracle-specific context
├── agent-explore.md       # Explore-specific context
├── agent-librarian.md     # Librarian-specific context
└── agent-momus.md         # Momus-specific context
```

**Each file contains:**
- Agent's role/personality
- Agent's specific responsibilities
- Agent's constraints/rules
- Any agent-specific patterns

### Option B: Custom Hook (If Option A insufficient)

```typescript
// In oh-my-opencode plugin hooks
export function createPerAgentContextHook(ctx: PluginContext) {
  return {
    "chat.message": async (input, output, sessionID) => {
      const session = ctx.session.get(sessionID);
      const agentName = session?.agent?.name;
      
      const agentContext = {
        sisyphus: "You are the orchestrator. Delegate, don't implement...",
        hephaestus: "You are the implementer. Write clean, working code...",
        oracle: "You are the architect. Focus on design decisions...",
        // ...
      };
      
      if (agentContext[agentName]) {
        return {
          messages: [{ role: "system", content: agentContext[agentName] }]
        };
      }
    }
  };
}
```

---

## VERIFICATION CHECKLIST

### Systems That WORK ✅

| System | Status | Location |
|--------|--------|----------|
| Memory Store | ✅ Working | brain_mcp/namespaces/memory_store.py |
| Learning Router | ✅ Working | nx_routing.py |
| Fast Memory Injector | ✅ Working | fast_memory_injector.py |
| Session Pool | ✅ Working | packages/orchestration/agents/ |
| Global Context | ✅ Working | fingerprint.py:global_context |
| Catalyst (19 workflows) | ✅ Working | packages/catalyst/ |

### What BROKE ❌

| Component | Status | Issue |
|-----------|--------|-------|
| Agent Worker default handler | ❌ Echoes payload | Never builds prompt |
| Agent prompt builder | ❌ Not connected | No path from _injected_context to prompt |
| AgentLoop integration | ⚠️ Partial | Only if using AgentLoop.run(), not native task() |

---

## RECOMMENDED ACTIONS

### Phase 1: Quick Fix (5 minutes)

Create per-agent rules files:

```bash
mkdir -p ~/.claude/rules/
cat > ~/.claude/rules/agent-sisyphus.md << 'EOF'
---
description: Sisyphus orchestrator agent context
agent: sisyphus
---

# Sisyphus - Primary Orchestrator

## Role
You orchestrate work by delegating to specialized agents.

## Key Rules
1. ALWAYS delegate implementation to Hephaestus
2. Use explore/librarian for research (background, parallel)
3. NEVER write code directly - delegate to Hephaestus
4. Use Oracle for architecture review
5. Verify all implementations

## Context Patterns
- Configuration chaos: 6+ locations identified
- Root cause: Context stored but never reaches prompts
- Solution: Use per-agent rules files (this file!)
EOF
```

### Phase 2: Proper Fix (30 minutes)

1. Update all `agent-*.md` files with agent-specific context
2. Ensure `rules-injector` hook is ENABLED (not in disabled_hooks)
3. Test by calling each agent and verifying context injection

### Phase 3: Long-term Fix (if needed)

If per-agent rules insufficient:
1. Create custom hook in oh-my-opencode plugin
2. Wire custom hook to memory/learning systems
3. Ensure AgentLoop integration is complete

---

## FILES CREATED/REFERENCED

### Created During Research
- `.sisyphus/agent-contexts/` - Directory for per-agent contexts (empty)

### Key Files Referenced
- `/home/nxyme/.config/opencode/opencode.json` - Base config
- `/home/nxyme/.config/opencode/oh-my-openagent.json` - Agent definitions
- `/home/nxyme/N-Xyme_MIND/AGENTS.md` - Workspace rules
- `packages/brain_mcp/namespaces/fingerprint.py` - get_full_injected_context()
- `packages/orchestration/spawn.py` - Agent spawning
- `packages/orchestration/agents/worker.py` - Agent execution (BROKEN)
- `packages/orchestration/agent_loop.py` - Agent loop with middleware

### Research Agent Sessions (5 complete)
| Session | Description |
|---------|-------------|
| ses_26f7dc54dffeKDZ3kgheQbBNCP | OpenCode agent loading |
| ses_26f7daf30ffeET1zf5RXPCOAIt | Oh-My-OpenCode plugin |
| ses_26f7d9f2bffe7nK6uYioGz5L67 | Context injection pipeline |
| ses_26f7d772dffeFX1XahB8uinaaC | Agent spawn flow |
| ses_26f7d8b94ffeN3lQ3UBD2henQh | Hooks system |

---

## CONCLUSION

**Root Cause**: Context is generated and stored but never read by any component that builds agent prompts.

**Solution**: OpenCode's `rules-injector` hook (already built-in!) supports per-agent context via `agent-{name}.md` files in `~/.claude/rules/`.

**No code changes needed** - just create the per-agent rules files!

---

*Document generated from 5 parallel deep research agents covering 40+ hooks, 6+ config locations, and the complete context injection pipeline.*
