# trigger-guardian-mcp
# Trigger phrase monitoring and routing MCP server

A Python MCP server that monitors and routes based on trigger phrases (e.g., `/start-work`, `/handoff`, slash commands). Enables workflow initiation and agent handoff detection.

## Tools

| Tool | Description |
|------|-------------|
| `register_trigger` | Registers a trigger phrase with callback action |
| `list_triggers` | Lists all registered triggers |
| `check_trigger` | Checks if input matches any registered trigger |
| `get_trigger_handlers` | Returns handlers for a matched trigger |
| `log_trigger_event` | Logs trigger activation for analytics |
| `clear_triggers` | Clears all registered triggers |

## Installation

```bash
pip install -e .
```

## Usage

### stdio mode (for OpenCode/Claude Desktop)
```bash
python -m trigger_guardian_mcp
```

### SSE mode (for remote access)
```bash
python -m trigger_guardian_mcp --sse --port 8767
```

## Built-in Triggers

The server comes with these default triggers:

| Phrase | Handler | Description |
|--------|---------|-------------|
| `/start-work` | skill:start-work | Start a new work session |
| `/handoff` | skill:handoff | Hand off to another agent/session |
| `/git-master` | skill:git-master | Git operations with master workflow |
| `/refactor` | skill:refactor | Intelligent refactoring command |
| `/playwright` | skill:playwright | Browser automation with Playwright |
| `/dev-browser` | skill:dev-browser | Persistent browser automation |

## Pattern Types

- `exact`: Match the trigger phrase exactly
- `prefix`: Match if input starts with the trigger phrase
- `regex`: Match using a regular expression pattern

## Integration

Add to your OpenCode MCP configuration:

```json
{
  "mcpServers": {
    "trigger-guardian": {
      "command": "python",
      "args": ["-m", "trigger_guardian_mcp"],
      "env": {
        "PYTHONPATH": "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/trigger-guardian-mcp"
      }
    }
  }
}
```