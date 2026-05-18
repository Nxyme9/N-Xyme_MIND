---
name: bmad-session-digest
description: "Session log parser and digest generator — summarizes opencode sessions into concise markdown"
---

## What I am

Session Digest plugin parses opencode session logs and generates concise digests/summaries of what happened in each session. It helps the user quickly understand what was accomplished without reading entire logs.

## How to use

```bash
# Generate digests for all sessions
just digest

# Generate digest for the latest session only
just digest-latest

# Generate digest for a specific session
python3 plugins/session-digest/generator.py --session <session-id>

# Parse logs to JSON (intermediate step)
python3 plugins/session-digest/parser.py --pretty

# View digest output to stdout
python3 plugins/session-digest/generator.py --latest --stdout
```

## Plugin Commands

When loaded as an OpenCode plugin:

| Command | Description |
|---------|-------------|
| `/digest` | Generate and display the latest session digest |
| `/digest-last` | Show the most recently saved digest |
| `/digest-list` | List all available digests |
| `/digest <session-id>` | Generate digest for a specific session |

## Plugin Hooks

- `session.end` — Auto-generates a digest when a session ends
- `session.start` — Loads the previous session's digest for context
- `experimental.chat.messages.transform` — Injects digest summary as system context on new session start

## Output Format

Each digest is a markdown file saved to `data/sessions/digests/{date}-{session-id}.md` containing:

| Section | Content |
|---------|---------|
| Header | Session ID, start/end time, duration |
| Summary | Event counts, prompts, tool calls, files, errors, subagents |
| Tools Used | List of tools with call counts |
| Files Modified | Files changed with operation type |
| Errors Encountered | Error messages with timestamps |
| Subagent Tasks | Spawned agents with status |
| Key Decisions | Detected decision points from conversation |
| Recent Prompts | Last 5 user prompts |

## Files

- `parser.py` — Session log parser (Python)
- `generator.py` — Digest generator (Python)
- `plugin.js` — OpenCode plugin (Node.js)
- `data/sessions/digests/*.md` — Generated digest files

## Log Format

Parses opencode JSON-L logs from `~/.local/share/opencode/log/*.log`:

| Event Type | Extracted Data |
|------------|----------------|
| `session.prompt` | User messages |
| `message.part.delta` | Assistant responses |
| `tool.registry` | Tool calls with inputs |
| `permission` | Permission checks |
| `error` | Error messages and stack traces |
| `agent.spawn` | Subagent task spawns |
| `session.start/end` | Session timing |

## Parser CLI Options

```bash
python3 plugins/session-digest/parser.py [options]

--log-dir DIR    Custom log directory
--file FILE      Parse a single log file
--session ID     Filter by session ID
--pretty         Pretty-print JSON output
--output FILE    Write to file instead of stdout
```

## Generator CLI Options

```bash
python3 plugins/session-digest/generator.py [options]

--log-dir DIR/FILE  Log directory or single log file
--session ID        Generate digest for specific session
--latest            Generate digest for latest session only
--output-dir DIR    Custom output directory
--stdout            Print digest to stdout instead of saving
```
