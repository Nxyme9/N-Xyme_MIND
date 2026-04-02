#!/usr/bin/env bash
# N-Xyme Catalyst WSL Setup Script
# Sets up OpenCode wrapper and WSL integration

set -e

echo "Setting up N-Xyme Catalyst in WSL..."

# Check if running in WSL
if ! grep -qEi "(microsoft|wsl)" /proc/version &>/dev/null; then
    echo "Warning: This script is intended for WSL environments."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install dependencies
echo "Installing dependencies..."
sudo apt-get update
sudo apt-get install -y docker.io docker-compose python3 python3-pip nodejs npm

# Add user to docker group
sudo usermod -aG docker $USER

# Install OpenCode
echo "Installing OpenCode..."
curl -fsSL https://opencode.ai/install.sh | bash

# Setup OpenCode wrappers
echo "Setting up OpenCode wrappers..."
mkdir -p ~/.config/opencode

# Create OpenCode config directory
mkdir -p ~/.config/opencode/plugins
mkdir -p ~/.config/opencode/agents

# Copy configs from repository
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR/.."

# Copy plugin configs
cp "$REPO_ROOT/configs/opencode/plugins/"* ~/.config/opencode/plugins/

# Copy agent configs
cp "$REPO_ROOT/configs/opencode/agents/"* ~/.config/opencode/agents/

# Copy main config
cp "$REPO_ROOT/configs/opencode/opencode.json" ~/.config/opencode/
cp "$REPO_ROOT/configs/opencode/permissions.json" ~/.config/opencode/

echo "Setup complete!"
echo "Please restart your terminal or run: source ~/.bashrc"