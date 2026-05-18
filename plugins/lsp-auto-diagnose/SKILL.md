---
name: bmad-lsp-diagnose
description: "LSP server health monitoring — detect dead/stalled servers, auto-restart, diagnose failures"
---

## What I am

Background LSP health monitor. Runs as a daemon checking pyright, rust-analyzer, typescript-language-server, and bash-language-server. Auto-restarts dead servers and sends desktop notifications.

## How to use

```bash
# Check LSP status (table format)
just lsp-status

# Run full diagnosis (JSON output)
just lsp-diagnose

# Start background monitor
just lsp-monitor
```

Or directly:

```bash
python3 plugins/lsp-auto-diagnose/diagnose.py status
python3 plugins/lsp-auto-diagnose/diagnose.py check
python3 plugins/lsp-auto-diagnose/diagnose.py daemon
```

## Health Categories

| Status | Meaning | Action |
|--------|---------|--------|
| healthy | Responding normally | None |
| stalled | CPU >= 90% | Kill + restart |
| dead | No process found | Restart |
| misconfigured | Bad config/missing binary | Log + notify |

## Rate Limits

- Max 3 restarts per 5 minutes per server
- Health check interval: 60s
- Notification on every restart

## Monitored Servers

| Server | Language | Restart Command |
|--------|----------|-----------------|
| pyright | Python | `pyright-langserver --stdio` |
| rust-analyzer | Rust | `rust-analyzer` |
| typescript-language-server | TypeScript/JS | `typescript-language-server --stdio` |
| bash-language-server | Bash/Shell | `bash-language-server start` |

## Plugin Hooks

The OpenCode plugin (`plugin.js`) hooks into:

- `tool.execute.after` — Checks LSP health after write/edit/bash tool calls
- `session.start` — Starts periodic 60s health checks
- `session.end` — Stops periodic checks

## Files

- `diagnose.py` — Health check engine (Python)
- `plugin.js` — OpenCode plugin (Node.js)
- `data/lsp-diagnose/health.jsonl` — Health check log (one JSON per line)
- `data/lsp-diagnose/restarts.jsonl` — Restart action log (one JSON per line)

## Diagnosis Output Format

Each health check returns a JSON object:

```json
{
  "server": "pyright",
  "status": "healthy",
  "pids": [12345],
  "cpu": 2.5,
  "timestamp": "2026-05-17T10:30:00.000Z"
}
```

Restart actions:

```json
{
  "server": "pyright",
  "action": "restarted",
  "killed_pids": [12345],
  "timestamp": "2026-05-17T10:30:00.000Z"
}
```

Or when rate-limited:

```json
{
  "server": "pyright",
  "action": "skipped",
  "reason": "rate_limited",
  "timestamp": "2026-05-17T10:30:00.000Z"
}
```
