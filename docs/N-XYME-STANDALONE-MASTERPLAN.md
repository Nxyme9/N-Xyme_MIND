# N-Xyme MIND — Standalone AI Coding Ecosystem
## Masterplan: Building Our Own OpenCode-Based System

---

## Executive Summary

Build a fully standalone, self-hosted AI coding ecosystem based on anomalyco/opencode with custom agent configurations (N-Xyme branding). All open source, no proprietary lock-in.

---

## Source Repos

| Repo | Stars | Purpose | License |
|------|-------|---------|---------|
| **anomalyco/opencode** | 137k | Main AI coding agent (core) | MIT |
| **code-yeongyu/oh-my-openagent** | 48k | Agent orchestration plugin | MIT |
| **ollama/ollama** | 120k+ | Local LLM runtime | MIT |
| **langchain-ai/langchain** | 100k+ | Agent framework | MIT |
| **langfuse/langfuse** | 12k+ | LLM observability | MIT |
| **Codium-ai/pr-agent** | 7k+ | PR automation | MIT |

---

## Architecture Options

### Option A: Fork + Customize (RECOMMENDED)
1. Fork `anomalyco/opencode` 
2. Add oh-my-openagent as plugin
3. Customize branding to N-Xyme
4. Add custom MCPs from N-Xyme_MIND

### Option B: Build on OpenCode (No Fork)
1. Use anomalyco/opencode as base binary
2. Configure custom agents in oh-my-opencode.json
3. Add custom MCPs (Python stdio)
4. Standalone entry point script

### Option C: From Scratch (LONG TERM)
1. Use LangGraph for agent orchestration
2. Ollama for local LLM
3. Custom Python MCPs
4. Build custom TUI

---

## Components to Port/Integrate

### From N-Xyme_MIND (Current)
- [x] athena-context-mcp — Context injection
- [x] trigger-guardian-mcp — Trigger phrase monitoring  
- [x] nx-mind-mcp — MIND state management
- [x] trigger_engine.py — Action handlers
- [x] vpn/rotator.py — VPN rotation
- [x] memory/connectors.py — 4 working connectors

### From oh-my-openagent (Plugin)
- [ ] Sisyphus agent (orchestrator)
- [ ] Hephaestus agent (implementation)
- [ ] Prometheus agent (planning)
- [ ] Oracle agent (architecture)
- [ ] Ultrawork mode
- [ ] Ralph Loop
- [ ] Hashline edit tool
- [ ] Background agents

### From External (New)
- [ ] Langfuse (observability)
- [ ] PR-Agent (code review)
- [ ] Custom memory (replace quivr)

---

## Implementation Phases

### Phase 1: Foundation
- [ ] Fork or clone anomalyco/opencode
- [ ] Set up build environment (Bun)
- [ ] Test base binary runs
- [ ] Add oh-my-openagent plugin

### Phase 2: Agent Configuration
- [ ] Define N-Xyme agent profiles
- [ ] Configure model routing
- [ ] Set up categories (deep, quick, ultrabrain, etc.)
- [ ] Test delegation

### Phase 3: Custom MCPs
- [ ] Port athena-context-mcp
- [ ] Port trigger-guardian-mcp
- [ ] Port nx-mind-mcp
- [ ] Configure in opencode.json

### Phase 4: Memory System
- [ ] Set up vector DB (optional: qdrant, chroma)
- [ ] Integrate with existing connectors
- [ ] Add observability (Langfuse)

### Phase 5: Branding & Packaging
- [ ] Rename to N-Xyme
- [ ] Custom entry point script
- [ ] Build standalone binary
- [ ] Create installer

---

## Key Files to Modify

### In anomalyco/opencode
```
packages/opencode/src/        # Core logic
packages/ai/                 # AI providers
packages/sdk/                # Client SDK
```

### Configuration
```
~/.config/opencode/opencode.json     # Main config
~/.config/opencode/oh-my-opencode.json  # Agent config
opencode.json                        # Project MCPs
```

---

## Estimated Timeline

| Phase | Effort | Duration |
|-------|--------|----------|
| Phase 1 | Medium | 1-2 days |
| Phase 2 | Low | 1 day |
| Phase 3 | Medium | 2-3 days |
| Phase 4 | High | 3-5 days |
| Phase 5 | Medium | 2-3 days |

**Total: ~2 weeks for full standalone**

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| OpenCode API changes | Pin to specific version |
| Build complexity | Use pre-built binaries |
| MCP compatibility | Use stdio mode |
| Model routing bugs | Use category, not subagent_type |

---

## Next Steps

1. Choose architecture option (A recommended)
2. Clone/fork repos
3. Set up build environment
4. Begin Phase 1

---

*Generated: 2026-04-04*
*Purpose: Standalone N-Xyme AI coding ecosystem*
