# N-Xyme_MIND - Persistent Context File

> This file provides persistent context for every AI session. Read on session start.

---

## 🎯 Current Focus

_[Update this on session start - what are you working on?]_

---

## ⚡ Rules (ADHD-Friendly - Non-Negotiable)

1. **One question per message** - Never ask multiple things at once
2. **Always show evidence** - Before claiming completion, show proof (tests pass, file exists, etc.)
3. **Save state every 30 minutes** - Use `bash bin/save-and-exit.sh` to checkpoint
4. **Energy-based scheduling** - Work in 90-min blocks, break for 20 min
5. **Sequential over parallel** - Complete one task before starting another
6. **Minimize context switching** - Finish what you started before switching

---

## 📁 Project Structure (Quick Reference)

```
N-Xyme_MIND/
├── bin/                    # 71 scripts - main entry points
│   ├── n-xyme-mind.sh      # Main entry point
│   ├── health-*.sh         # L0/L1/L2 health checks
│   └── mcp-*.sh            # MCP server management
├── packages/               # 27 Python packages (core logic)
├── configs/               # Model router, VPN configs
├── .sisyphus/             # Session state, routing DB, learning data
├── AGENTS.md               # Workspace rules (READ FIRST)
├── opencode.json           # Main config (11 agents, 14 MCPs)
└── tests/                  # Test suites (coverage at 11.6%)
```

---

## 🔧 Key Commands

| Command | Purpose |
|---------|---------|
| `bash n-xyme-mind.sh` | Start the system |
| `bash bin/health-l0-blink.sh` | Quick health check (<1s) |
| `bash bin/mcp-doctor.sh` | Diagnose MCP issues |
| `bash bin/save-and-exit.sh` | Save state and exit cleanly |
| `python3 -m pytest tests/` | Run test suite |

---

## 🚨 Known Issues (Avoid)

- **System tray** - brain-tray.py has KDE Wayland issues, use web-control.py instead
- **Port 8766** - Web control panel for service management
- **Low test coverage** - Only 11.6%, needs improvement

---

## 🧠 Session Protocol

### Start of Session
1. Read this file
2. Update "Current Focus" above
3. Check `git status` for any uncommitted work

### During Session
1. Work on one thing at a time
2. Save state every 30 min
3. Commit often (checkpoint commits)
4. Test after every meaningful change

### End of Session
1. Run `bash bin/save-and-exit.sh`
2. Review what was accomplished
3. Update "Current Focus" for next session

---

## 🔄 Delegation Quick-Reference

| Task Type | Agent | Complexity |
|-----------|-------|------------|
| "fix typo" | sisyphus-junior | L1 |
| "fix bug" | hephaestus | L2 |
| "add feature" | explore → hephaestus | L3 |
| "build system" | prometheus → hephaestus | L4 |
| "redesign" | metis → prometheus → hephaestus | L5 |

---

## 📋 Environment Variables (If Needed)

```bash
# Source before running
source /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/env.sh
```

---

*Last updated: 2026-04-10*--- Checkpoint: 2026-04-10 11:25:51 ---
