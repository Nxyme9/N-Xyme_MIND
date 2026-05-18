---
config_ref: /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/docs/opencode-schema-reference.md
nx_config: /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/config/nx_agents.json
opencode_config: /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/opencode.json
mcp_server: /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/services/opencode-admin-mcp/src/server.py
---

# BMad OpenCode Schema — Config Editing Workflow

**Goal:** Safely edit, validate, and maintain OpenCode configuration.

## Valid Root Keys (opencode.json)

| Key | Type | Description |
|-----|------|-------------|
| `$schema` | string | JSON Schema URL (optional) |
| `model` | string | Default model ID |
| `skills` | object | skills.paths array of scan dirs |
| `compaction` | object | Auto-compaction settings |
| `plugin` | array | Plugin paths or npm packages |
| `mcp` | object | MCP server definitions |
| `permission` | string/object | Default tool permission |
| `agent` | object | Named agent definitions |
| `provider` | object | Provider + model limits |
| `instructions` | array | Global system instructions |

## Key Facts

- Config precedence (highest→lowest): `OPENCODE_CONFIG_CONTENT` (#6) > `opencode.json` (#4) > `~/.config/opencode/opencode.json` (#2)
- `bins/nx` injects config via `OPENCODE_CONFIG_CONTENT` env var (priority #6)
- Custom keys cause `Unrecognized keys:` error on startup — keep them in `config/nx_agents.json`
- `SKILL.md` needs YAML frontmatter with `name` and `description`; dir name must match `name`
- Plugins use `.disabled` extension to deactivate
- Permission format: `"allow"` (all), `"deny"` (none), or `{"tool_name": "allow|deny", ...}`

## Workflow Steps

### Step 1: Diagnose

If opencode fails to start, check the error message for:
- `Unrecognized keys:` — move those keys to `config/nx_agents.json`
- `ENOENT` — file path doesn't exist
- `JSON parse error` — syntax issue, validate with `python3 -m json.tool`

### Step 2: Validate

Run the opencode-admin-mcp `validate_config` tool against `opencode.json`:
- Checks all keys against allowed list
- Verifies agent definitions have required fields
- Ensures MCP server scripts exist on disk

### Step 3: Edit

Use the MCP tools for safe edits:
- `edit_config` — change a specific key in opencode.json
- `add_agent` — add a new agent definition
- `remove_key` — remove a key from any config
- `sync_nx_config` — sync a key between opencode.json and nx_agents.json

### Step 4: Verify

After any edit:
1. Validate JSON syntax: `python3 -m json.tool opencode.json`
2. Run `opencode --dry-run` or check that startup no longer errors
3. For agent changes, verify `bins/nx` still validates: `bins/nx`

## Restricting Root Permissions

To remove bash from the default root agent:

```json
{
  "permission": {
    "bash": "deny",
    "write": "allow",
    "edit": "allow",
    "read": "allow",
    "glob": "allow",
    "grep": "allow"
  }
}
```

Individual agents inherit root defaults but can be further restricted via `agents/{name}/tools/tools.json`.
