# N-Xyme_MIND — Architecture

## System Overview

```
OpenCode TUI → OMO Plugin → Agent Layer → MCP Layer → Tools
```

## Config Separation (CRITICAL)

| File | Purpose | Who Reads It |
|------|---------|-------------|
| `~/.config/opencode/opencode.json` | Global base config | OpenCode (always) |
| `~/.config/opencode/oh-my-opencode.json` | Global agent models | OMO plugin (always) |
| `$PROJECT/opencode.json` | Project MCP overrides | OpenCode (if present) |
| `$PROJECT/AGENTS.md` | Workspace rules | OpenCode (on first read) |

**Rule**: Global config = base. Project config = overrides. Never mix agent definitions into opencode.json.

## MCP Communication

All MCPs use local stdio transport. No network dependencies for MCP protocol.

## Agent Delegation

```
Sisyphus (orchestrator)
├── Hephaestus (implementation)
├── Oracle (architecture review)
├── Prometheus (planning)
├── Metis (gap analysis)
├── Momus (adversarial review)
├── Atlas (executor)
├── Explore (codebase search)
├── Librarian (external research)
├── Sisyphus-junior (light tasks)
└── Multimodal-looker (vision)
```
