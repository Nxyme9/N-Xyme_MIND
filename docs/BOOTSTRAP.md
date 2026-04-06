# Bootstrap Guide

## Quick Start (Existing Machine)

```bash
cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
source env.sh
bash n-xyme-mind.sh
```

## Fresh Machine Setup

```bash
git clone https://github.com/Nxyme9/N-Xyme_MIND_v0.1.git
cd N-Xyme_MIND_v0.1
bash bootstrap.sh
```

## What bootstrap.sh Does

1. Detects OS (Arch/Debian/Fedora/RHEL)
2. Installs system deps (node, npm, curl)
3. Installs uv (Python package manager)
4. Installs OMO globally
5. Installs MCP packages globally
6. Creates Python venv
7. Installs Python deps
8. Fixes shebangs
9. Fixes hardcoded paths
10. Creates required directories
11. Runs health check

## Prerequisites

- Linux (Arch, Debian, Fedora, or RHEL)
- Python 3.10+
- Internet connection (for first run only)

## Manual Setup (if bootstrap fails)

```bash
# 1. Install Node.js
sudo pacman -S nodejs npm  # Arch
sudo apt install nodejs npm  # Debian
sudo dnf install nodejs npm  # Fedora

# 2. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install OMO
sudo npm install -g oh-my-opencode@3.14.0

# 4. Install MCPs
sudo npm install -g @modelcontextprotocol/server-sequential-thinking
sudo npm install -g @modelcontextprotocol/server-memory
sudo npm install -g @upstash/context7-mcp
sudo npm install -g mcp-server-filesystem

# 5. Create venv
uv venv venvs/athena --python python3
uv pip install -e athena --python venvs/athena/bin/python

# 6. Launch
source env.sh
bash n-xyme-mind.sh
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "node not found" | Install Node.js, restart terminal |
| "npx not found" | Install npm, restart terminal |
| "uv not found" | Run uv install script, source ~/.bashrc |
| "MCP disconnected" | Check binary: `which mcp-server-sequential-thinking` |
| "athena import error" | Reinstall: `uv pip install -e athena --python venvs/athena/bin/python` |
| "Ollama not running" | Start: `ollama serve &` |
