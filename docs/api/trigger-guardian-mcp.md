# Trigger Guardian MCP API Contract

## Overview
Manages trigger phrase registration, matching, and analytics for the N-Xyme nervous system.

## Connection
```json
{
  "command": ["./packages/trigger-guardian-mcp/.venv/bin/python", "-m", "trigger_guardian_mcp"]
}
```

## Tools

### `register_trigger`
Register a trigger phrase with callback action.

**Input:**
```json
{
  "phrase": "string - The trigger phrase (e.g., '/my-command')",
  "description": "string (optional)",
  "handler": "string - callback|skill|function|workflow",
  "handler_target": "string (optional)",
  "pattern_type": "string - exact|prefix|regex"
}
```

### `list_triggers`
List all registered triggers.

**Input:** `{}`

**Output:**
```json
{
  "triggers": [{"phrase": "string", "description": "string", "handler": "string"}],
  "count": "number"
}
```

### `check_trigger`
Check if input matches any registered trigger.

**Input:**
```json
{
  "input_text": "string - The input string to check"
}
```

**Output:**
```json
{
  "matched": "boolean",
  "trigger": {"phrase": "string", "handler": "string"} (if matched)
}
```

### `log_trigger_event`
Log trigger activation for analytics.

**Input:**
```json
{
  "phrase": "string",
  "input_text": "string",
  "metadata": "object (optional)"
}
```
