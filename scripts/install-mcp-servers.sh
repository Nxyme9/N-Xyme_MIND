#!/usr/bin/env bash
# N-Xyme Catalyst MCP Servers Installation Script
# Installs all MCP servers from the packages directory

set -e

echo "Installing MCP Servers..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGES_DIR="$SCRIPT_DIR/../packages/mcp-servers"

# Check if packages directory exists
if [ ! -d "$PACKAGES_DIR" ]; then
    echo "Error: Packages directory not found at $PACKAGES_DIR"
    exit 1
fi

# Install local tools MCP servers
echo "Installing local tools MCP servers..."
for server in ollama-mcp github-mcp git-mcp sqlite-mcp; do
    SERVER_DIR="$PACKAGES_DIR/local-tools/$server"
    if [ -d "$SERVER_DIR" ]; then
        echo "Installing $server..."
        cd "$SERVER_DIR"
        if [ -f "package.json" ]; then
            npm install
        elif [ -f "requirements.txt" ]; then
            pip install -r requirements.txt
        fi
        cd - > /dev/null
    else
        echo "Warning: $server directory not found"
    fi
done

# Install web tools MCP servers
echo "Installing web tools MCP servers..."
for server in playwright-mcp puppeteer-mcp fetch-mcp brave-search-mcp exa-mcp; do
    SERVER_DIR="$PACKAGES_DIR/web-tools/$server"
    if [ -d "$SERVER_DIR" ]; then
        echo "Installing $server..."
        cd "$SERVER_DIR"
        if [ -f "package.json" ]; then
            npm install
        elif [ -f "requirements.txt" ]; then
            pip install -r requirements.txt
        fi
        cd - > /dev/null
    else
        echo "Warning: $server directory not found"
    fi
done

# Install utility tools MCP servers
echo "Installing utility tools MCP servers..."
for server in context7-mcp grep-app-mcp obsidian-mcp shadcn-mcp; do
    SERVER_DIR="$PACKAGES_DIR/utility-tools/$server"
    if [ -d "$SERVER_DIR" ]; then
        echo "Installing $server..."
        cd "$SERVER_DIR"
        if [ -f "package.json" ]; then
            npm install
        elif [ -f "requirements.txt" ]; then
            pip install -r requirements.txt
        fi
        cd - > /dev/null
    else
        echo "Warning: $server directory not found"
    fi
done

echo "MCP servers installation complete!"
echo "Start services with: docker-compose up -d"