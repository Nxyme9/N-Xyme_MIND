# Root Configuration

## Configuration Files

### opencode.json

Main OpenCode configuration file defining:
- Model selection (minimax-m2.5-free)
- Agent configurations with permissions
- MCP server definitions
- Provider configurations (openrouter, xai, deepseek, ollama, lmstudio, gguf, opencode)
- Permission rules for read, edit, bash

### oh-my-openagent.json

Agent definitions and behavioral rules:
- 12 agents: sisyphus, catalyst, prometheus, oracle, metis, momus, hephaestus, atlas, explore, librarian, sisyphus-junior, multimodal-looker
- 9 categories: visual-engineering, ultrabrain, deep, artistry, quick, unspecified-low, unspecified-high, routing, writing
- Experimental features: aggressive_truncation, truncate_all_tool_outputs, dynamic_context_pruning
- Disabled hooks list

### triggers.json

Unified trigger configuration for Catalyst nervous system:
- Action registry: restart_service, throttle_ollama, force_gc, alert, quarantine, clean_stale, clear_lock, rotate_vpn, rotate_api_key, etc.
- Trigger categories: gpu, pm2, service, database, sessions, rate_limit, config, graphiti, ollama, system, velocity, consciousness, memory

### AGENTS.md

Workspace agent instructions including:
- Dissection mode principles
- Agent switch detection
- System map with agent roles
- Delegation routing matrix
- Quality gates
- Anti-patterns

## Scripts

### bootstrap.sh

Located in `bin/bootstrap.sh` - supports Arch/Debian/Fedora/RHEL for fresh machine setup.

## Notes

- Configuration follows OpenCode schema (https://opencode.ai/config.json)
- Agent permissions define what each agent can do
- MCP servers connect to various services (memory, learning, context, etc.)
- Providers configured with model limits and API endpoints