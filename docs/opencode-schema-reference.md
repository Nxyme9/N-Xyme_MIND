# OpenCode Configuration Schema — Complete Reference

> Source: [opencode.ai/docs](https://opencode.ai/docs/config/) + schema research (May 2026)

## Config Precedence (lowest → highest)

| # | Source | Path |
|---|--------|------|
| 1 | Remote config | `.well-known/opencode` |
| 2 | Global config | `~/.config/opencode/opencode.json` |
| 3 | Custom path | `OPENCODE_CONFIG` env var |
| 4 | Project config | `opencode.json` in project root |
| 5 | `.opencode/` dirs | `.opencode/opencode.json` or `~/.config/opencode/opencode.json` |
| **6** | **Inline config** | **`OPENCODE_CONFIG_CONTENT` env var (what `bins/nx` uses)** |
| 7 | Managed (file) | `/etc/opencode/` or platform equivalent |
| 8 | Managed (MDM) | `.mobileconfig` — not user-overridable |

Configs are **merged** (non-conflicting keys preserved). Later sources override earlier ones.

## How `bins/nx` Works (Our Setup)

```
bins/nx
  ├── sync-agents.js  → agents/{name}/agent.js  →  .opencode/agents/{name}.md
  └── OPENCODE_CONFIG_CONTENT = cat config/nx_agents.json
       └── Priority #6 — overrides root opencode.json
```

`config/nx_agents.json` is the **single source of truth**. It includes `mcp.nx` which tells OpenCode to manage `bins/nx_agents` as a persistent native MCP server.

## Plugins

- `.opencode/plugins/*.js` or `.ts` — auto-loaded at startup
- OR `opencode.json` → `"plugin": ["npm-package-name"]`
- Plugin API: `@opencode-ai/plugin` v^1.14.48
- Exports named `Plugin` async function returning hooks/tools
- `.disabled` extension = plugin won't load

## Skills Discovery

OpenCode scans for `SKILL.md` (all caps, not `skill.md`) in:
- `.opencode/skills/*/SKILL.md`
- `~/.config/opencode/skills/*/SKILL.md`
- `.claude/skills/*/SKILL.md`
- `.agents/skills/*/SKILL.md`
- **`skills.paths` in config** → each path is scanned for `*/SKILL.md`

**SKILL.md must have frontmatter:**
```yaml
---
name: my-skill        # required: lowercase + hyphens, 1-64 chars
description: "..."    # required: 1-1024 chars
---
```

Skill directory name must match `name` field. Without both, the skill is invisible.

## MCP Configuration

```json
{
  "mcp": {
    "nx": {
      "type": "local",
      "command": ["path/to/binary"],
      "enabled": true,
      "timeout": 30000
    }
  }
}
```

- **Local**: persistent subprocess with stdin/stdout JSON-RPC
- **Remote**: HTTP URL with optional OAuth
- OpenCode manages lifecycle — no plugin needed for MCP tools

## Key Files in N-Xyme

| File | Role |
|------|------|
| `opencode.json` | Root config (mostly overridden by OPENCODE_CONFIG_CONTENT) |
| `config/nx_agents.json` | Single source of truth — our REAL config |
| `bins/nx` | Launcher — injects config, syncs agents, launches opencode |
| `bins/nx_agents` | Rust MCP server (persistent process via native MCP) |
| `scripts/sync-agents.js` | Generates `.opencode/agents/*.md` from `agents/*/agent.js` |
| `.opencode/plugins/` | Plugin directory (`.js` loaded, `.disabled` skipped) |
| `agents/*/agent.js` | Single source of truth for agent definitions |

## Common Pitfalls

1. **Plugin vs Native MCP conflict** — having both a plugin AND `mcp` config for the same binary registers duplicate tools. Use one or the other.
2. **SKILL.md must be CAPS** — `skill.md` won't work, only `SKILL.md`.
3. **Skills need matching name/dir** — directory name must equal `name` field in frontmatter.
4. **`OPENCODE_CONFIG_CONTENT` > `opencode.json`** — inline JSON env var overrides file config.
5. **Plugins reload on restart** — renaming to `.disabled` is the safe way to deactivate.
