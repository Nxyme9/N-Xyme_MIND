# Wake Up — Session Briefing

> **Last updated:** 2026-04-02T01:15:00Z
> **Last agent:** Prometheus
> **Session type:** Post-CachyOS reinstall recovery
> **Status:** Drives fixed, MCPs partially fixed, agents need auth

---

## AGENT SWITCH TRIGGER

If you are reading this and you are NOT the agent listed above, READ THIS FIRST:
1. You are inheriting context from a DIFFERENT agent
2. Read the "What Happened" and "What's Next" sections below
3. Check `.sisyphus/session-state.json` for current task state
4. Continue from "What's Next" — do NOT restart from scratch

---

## Critical State

- **System**: CachyOS (Arch-based), freshly reinstalled
- **Python**: 3.14 — venv broken (pip shebangs corrupted, pydantic.v1 incompatible)
- **Ollama**: Running, pulling qwen2.5:3b
- **Node.js**: v25.8.2 installed
- **uv**: 0.11.2 installed

## What Happened

1. User reinstalled CachyOS, barely recovered data
2. Fixed 5 drives (fstab entries, auto-mount on boot)
3. Fixed 6/8 MCP servers (npx/uvx instead of broken Python)
4. Fixed opencode.json paths (nxyme → n-xyme relative)
5. Fixed agent models (all → mimo-v2-pro-free)
6. Fixed explore/librarian bash permissions
7. Fixed opencode startup (disabled broken MCPs, fixed context7 config)
8. Fixed fish PATH for opencode

## What's Still Broken

1. **Subagents broken** — "Missing Authentication header" — user MUST run: `opencode providers login`
2. **athena MCP disabled** — no npm alternative, Python venv broken
3. **Backup .img.zst** — 183GB, needs decompression (user had 5-hour loop before)
4. **Game not installed** — ISO mounted at /mnt/game-iso, needs `wine setup.exe`

## What's Next

1. User runs `opencode providers login` to fix subagent auth
2. User runs `wine setup.exe` to install game
3. Later: decompress .img.zst for full backup recovery
4. Later: fix athena MCP or find alternative

---

## Compression Guard
- DO NOT TOUCH compression settings
- All compression hooks are DISABLED for a reason
- DO NOT re-enable, modify, or suggest compression improvements
