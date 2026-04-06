# Custom MCP Server Design for N-Xyme_MIND

This document outlines the design for custom MCP servers to extend N-Xyme_MIND's capabilities beyond the current global MCPs. These servers address framework-specific integration needs identified in the Athena/BMAD ecosystem.

---

## 1. Recommended Custom MCP Servers

| Server | Purpose | Priority |
|--------|---------|----------|
| **athena-context-mcp** | Context injection from Athena memory bank | High |
| **nx-mind-mcp** | MIND state management and session continuity | High |
| **trigger-guardian-mcp** | Trigger phrase monitoring and routing | Medium |

---

## 2. athena-context-mcp

### Purpose
Injects context from the Athena framework's memory bank into OpenCode sessions. Provides access to `activeContext.md`, `productContext.md`, `userContext.md`, and constraints defined in `athena.yaml`.

### Tools

| Tool | Description |
|------|-------------|
| `get_active_context` | Returns current active context from `.context/memory_bank/activeContext.md` |
| `get_product_context` | Returns product context (identity/soul) from `.context/memory_bank/productContext.md` |
| `get_user_context` | Returns user context from `.context/memory_bank/userContext.md` |
| `get_constraints` | Returns behavioral constraints from `.context/memory_bank/constraints.md` |
| `get_bmad_agents` | Lists available BMAD agents from `_bmad/_config/agents/` |
| `get_bmad_workflows` | Lists BMAD workflows by phase from `_bmad/bmm/workflows/` |
| `inject_context` | Writes context into session for prompt injection |

### Architecture

```
athena-context-mcp/
├── index.js                 # MCP server entry point
├── tools/
│   ├── contextTools.js      # Context reading tools
│   └── bmadTools.js         # BMAD discovery tools
├── config/
│   └── defaults.yaml        # Default paths (athena.yaml reference)
└── package.json
```

**Data Flow:**
1. Load paths from `athena.yaml` (identity.*, constraints.*)
2. Read markdown files from `.context/memory_bank/`
3. Parse frontmatter and content for injection
4. Return structured JSON to OpenCode

### Implementation Notes

- Use `athena.yaml` to locate memory bank (supports override via `extends`)
- Cache context on startup; invalidate on file change detection
- Support hot-reload via filesystem watcher

---

## 3. nx-mind-mcp

### Purpose
Manages MIND state across sessions—tracks project progress, active workflows, session history, and cross-session continuity. Acts as the persistent "brain" layer for N-Xyme_MIND.

### Tools

| Tool | Description |
|------|-------------|
| `get_mind_state` | Returns current MIND state (project, phase, active tasks) |
| `update_mind_state` | Updates MIND state with new information |
| `get_session_history` | Returns history of past sessions with summaries |
| `get_active_workflow` | Returns currently active BMAD workflow and step |
| `set_context` | Sets project context for current session |
| `sync_to_memory` | Syncs MIND state to memory MCP (entities/relations) |
| `get_project_manifest` | Returns project metadata and progress |

### Architecture

```
nx-mind-mcp/
├── index.js                 # MCP server entry point
├── mind/
│   ├── state.js             # State management (in-memory + file persist)
│   ├── manifest.js          # Project manifest tracking
│   └── history.js           # Session history store
├── storage/
│   └── mind-state.json     # Persisted state file (in .context/)
├── config/
│   └── mind.yaml            # MIND configuration
└── package.json
```

**Data Flow:**
1. Initialize state from `.context/mind-state.json` or create new
2. Track active workflow from `_bmad/bmm/workflows/` discovery
3. On session end, sync state to memory MCP as entities
4. On session start, hydrate state for context injection

### Implementation Notes

- State file: `.context/mind-state.json`
- Support multi-project via `mind.yaml` project selector
- Integrate with existing memory MCP (add relations, not replace)

---

## 4. trigger-guardian-mcp

### Purpose
Monitors and routes based on trigger phrases (e.g., `/start-work`, `/handoff`, slash commands). Enables workflow initiation and agent handoff detection.

### Tools

| Tool | Description |
|------|-------------|
| `register_trigger` | Registers a trigger phrase with callback action |
| `list_triggers` | Lists all registered triggers |
| `check_trigger` | Checks if input matches any registered trigger |
| `get_trigger_handlers` | Returns handlers for a matched trigger |
| `log_trigger_event` | Logs trigger activation for analytics |
| `clear_triggers` | Clears all registered triggers |

### Architecture

```
trigger-guardian-mcp/
├── index.js                 # MCP server entry point
├── guardian/
│   ├── registry.js          # Trigger registry (in-memory)
│   ├── matcher.js           # Phrase matching (exact + fuzzy)
│   └── handlers.js          # Built-in trigger handlers
├── config/
│   └── triggers.yaml        # Default trigger definitions
└── package.json
```

**Data Flow:**
1. Load default triggers from `triggers.yaml`
2. On `check_trigger(input)`, run against registry
3. Return matched trigger + handler metadata
4. Log activation for analytics

### Implementation Notes

- Built-in triggers: `/start-work`, `/handoff`, `/git-master`, `/refactor`, `/playwright`, `/dev-browser`
- Support regex patterns for advanced matching
- Integrate with skill system for handler lookup

---

## 5. Implementation Priority

| Phase | Server | Effort | Notes |
|-------|--------|--------|-------|
| **1** | athena-context-mcp | Short | Light wrapper around existing file reads |
| **2** | nx-mind-mcp | Medium | Requires state design + memory integration |
| **3** | trigger-guardian-mcp | Short | Simple registry + matching logic |

### Phase 1: athena-context-mcp (Quick Win)

- Reuses existing file access patterns
- No new storage requirements
- High value: enables context injection from Athena

### Phase 2: nx-mind-mCP (Core Feature)

- Requires state schema design
- Needs memory MCP integration strategy
- Critical for session continuity

### Phase 3: trigger-guardian-mcp (Enhancement)

- Standalone pattern matching
- Low dependency on other components
- Enables workflow automation

---

## 6. Integration with Current MCPs

| Custom MCP | Uses Existing MCP | Integration Point |
|------------|-------------------|-------------------|
| athena-context-mcp | filesystem | Scoped reads to `.context/` |
| nx-mind-mcp | memory | Creates entities for project state |
| trigger-guardian-mcp | — | Independent, no dependencies |

---

## 7. Open Questions

1. **athena-context-mcp**: Should it parse `athena.yaml` dynamically or use hardcoded defaults?
2. **nx-mind-mcp**: State schema—flat JSON vs. hierarchical structure?
3. **trigger-guardian-mcp**: Trigger matching—exact match only or fuzzy/threshold-based?

---

## 8. Future Considerations

- **athena-bridge-mcp**: Full integration with `athena_bridge.py` for BMAD-to-task conversion
- **bmad-executor-mcp**: Direct BMAD workflow execution from OpenCode
- **catalyst-chain-mcp**: Integration with `_bmad/catalyst/` workflows
