# SEE MASTER_SYSTEM.md FOR FULL STATUS

This file is DEPRECATED. All info consolidated to:
**`MASTER_SYSTEM.md`**

### Quick Links:
- Memory: Graphiti ✅ Running
- Compression: DISABLED ✅
- Models: Best free (mimo-v2-pro-free) ✅
- Configs: `~/.config/opencode/`
**Date**: 2026-03-30  
**Status**: PARTIALLY CONFIGURED - Several critical issues remain

## CURRENT SYSTEM STATE

### Config Files (SCATTERED - needs consolidation)
- **oh-my-opencode.json**: `/home/nxyme/.config/opencode/oh-my-opencode.json` - 11 agents with prompt_append, free zen models
- **opencode.json**: `/home/nxyme/.config/opencode/opencode.json` - 22 MCPs, OpenRouter provider with API key
- **model-router.json**: `/home/nxyme/.config/opencode/model-router.json` - 150+ models (opencode-zen + OpenRouter)
- **AGENTS.md**: `/home/nxyme/.config/opencode/AGENTS.md` - System schema, global rules
- **api-keys.json**: `/home/nxyme/.config/opencode/api-keys.json` - References secrets
- **Secrets**: `/home/nxyme/N-Xyme_MIND/secrets/api-keys.json`

### Known Issues
1. **CONFIGURATION SCATTER**: Files spread across `~/.config/opencode/` and `N-Xyme_MIND/`. User wants EVERYTHING at `/home/nxyme/N-Xyme_MIND/`
2. **GRAPHITI MCP NOT CONNECTING**: Server runs at localhost:8001 (health OK, Neo4j connected, 15 tools), but `skill_mcp` returns "MCP server graphiti not found". Root cause: `skill_mcp` only sees MCPs from loaded SKILLS, not from `opencode.json`. Need to fix MCP discovery/connection layer.
3. **VOXTYPE**: Daemon running with F9 hotkey (fixed from --no-hotkey flag). Should work now.
4. **TELEGRAM BOT**: Research complete. Node.js/Telegraf scaffold at `/home/nxyme/telegram-telegraf-bot/`. Not deployed.
5. **CONTEXT WARNINGS**: System-level (cannot disable). Hooks disabled but system monitors context window size. Only solution: keep conversations shorter.

### Graphiti MCP Details
- **Health**: OK at localhost:8001, Neo4j connected
- **Bridge**: `/home/nxyme/N-Xyme_MIND/tools/mcp-bridge/mcp-stdio-bridge.js` (184 lines, proxies stdio to HTTP)
- **Config in opencode.json**: Lines 26-34, local type, command uses bridge.js
- **Test result**: Manual bridge test SUCCESS (15 tools returned)
- **Issue**: OpenCode's MCP discovery layer can't see it. Needs investigation.

### User Frustrations (READ THIS CAREFULLY)
- Context limits causing me to STOP repeatedly - user screamed "U KEEP STOPPING"
- Compression loops wasted 12 hours - root cause was AGENTS.md saying "Use compress proactively"
- Wants EVERYTHING self-contained at N-Xyme_MIND, not scattered
- Wants Graphiti MCP working NOW
- Wants MAXIMUM PARALLEL AGENTS, not sequential work
- "I WANT THE BEST OF THE BEST FOR CODING AND REASONING ONLY!"

### Hardware
- CPU: Ryzen 7 7800X3D (8C/16T, 104MB cache)
- GPU: RTX 3080 Ti (12GB VRAM)
- RAM: 32GB DDR5
- OS: CachyOS Linux (native, no Docker/WSL)

### Models Available
- **OpenCode Zen (free)**: mimo-v2-pro-free, mimo-v2-omni-free, gpt-5-nano, kimi-k2.5-free, claude-sonnet-4, gpt-5.4, qwen3-coder, etc.
- **OpenRouter (paid)**: o3, claude-sonnet-4.6, gpt-5.4-pro, deepseek-r1, etc. (free tier exhausted)
- **Ollama (local)**: qwen3:8b

### Parallel Limits
- maxConcurrentAgents: 8
- maxConcurrentBackgroundTasks: 12
- maxConcurrentExplore: 8
- maxConcurrentLibrarian: 4
- maxConcurrentOracle: 2
- maxConcurrentDeep: 4

### Disabled Hooks
- context-window-monitor
- anthropic-context-window-limit-recovery
- preemptive-compaction

## IMMEDIATE TODO (new session)
1. **CONSOLIDATE CONFIGS**: Move everything to `/home/nxyme/N-Xyme_MIND/`
2. **FIX GRAPHITI MCP**: Make it discoverable by OpenCode's MCP layer
3. **TEST VOXTYPE**: Verify F9 hotkey works
4. **TELEGRAM BOT**: Deploy or shelve based on user preference
5. **VALIDATE ALL AGENTS**: Test that prompt_append works across all 11 agents

## CONTEXT WARNINGS (SYSTEM-LEVEL)
These CANNOT be disabled. They're baked into the model's context window monitoring. Solutions:
- Keep conversations SHORTER
- Use model with LARGER context window
- Accept warnings (informational, not breaking)
