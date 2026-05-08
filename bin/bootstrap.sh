#!/usr/bin/env bash
# bootstrap.sh — One-command setup for N-Xyme_MIND on ANY Linux machine
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=== N-Xyme_MIND Bootstrap ==="

# 1. Detect OS
if [ -f /etc/arch-release ]; then
    DISTRO="arch"
elif [ -f /etc/fedora-release ]; then
    DISTRO="fedora"
elif [ -f /etc/redhat-release ]; then
    DISTRO="rhel"
elif [ -f /etc/debian_version ]; then
    DISTRO="debian"
else
    echo "Unsupported distro. Manual setup required."
    exit 1
fi
echo "Detected: $DISTRO"

# 2. Install system deps
install_if_missing() {
    if ! command -v "$1" &>/dev/null; then
        echo "Installing $1..."
        case "$DISTRO" in
            arch)   sudo pacman -S --noconfirm "$2" ;;
            debian) sudo apt install -y "$3" ;;
            fedora) sudo dnf install -y "$4" ;;
            rhel)   sudo yum install -y "$4" ;;
        esac
    else
        echo "$1 already installed: $(command -v $1)"
    fi
}

install_if_missing node nodejs nodejs nodejs
install_if_missing npm npm npm npm
install_if_missing curl curl curl curl

# 3. Install uv
if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# 4. Install OMO
if ! npm ls -g oh-my-opencode &>/dev/null; then
    echo "Installing OMO..."
    sudo npm install -g oh-my-opencode@3.14.0
fi

# 5. Install MCP packages
echo "Installing MCP packages..."
sudo npm install -g @modelcontextprotocol/server-sequential-thinking @modelcontextprotocol/server-memory @upstash/context7-mcp mcp-server-filesystem

# 6. Create Python venv
echo "Creating Python venv..."
uv venv "$ROOT/.venv" --python python3
uv pip install . --python "$ROOT/.venv/bin/python"
uv pip install sentence-transformers --python "$ROOT/.venv/bin/python"

# 7. Fix shebangs
echo "Fixing shebangs..."
find "$ROOT" -name "*.py" -exec sed -i '1s|^#!/usr/bin/python.*|#!/usr/bin/env python3|' {} \;
find "$ROOT" -name "*.sh" -exec sed -i '1s|^#!/bin/bash|#!/usr/bin/env bash|' {} \;

# 8. Fix hardcoded paths
echo "Fixing paths..."
find "$ROOT" -name "*.py" -exec sed -i 's|/home/nxyme/nx_openmore|.|g' {} \;
find "$ROOT" -name "*.yaml" -exec sed -i 's|/home/nxyme/nx_openmore|.|g' {} \;

# 9. Create required directories
mkdir -p "$ROOT/.opencode/data" "$ROOT/.ollama/models" "$ROOT/.cache"

# 10. Sync config
cp "$ROOT/opencode.json" "$ROOT/.opencode/opencode.json"

# 11. Health check
echo "Running health checks..."
bash "$ROOT/bin/health-l0-blink.sh"

echo ""
echo "=== Bootstrap complete! ==="
echo "Run: source env.sh && bash n-xyme-mind.sh"
