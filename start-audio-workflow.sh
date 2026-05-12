#!/usr/bin/env bash
# N-Xyme Audio Workflow - Unified Starter
# Starts Bitwig OSC client + Workflow Engine + optional MCP server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUDIO_BRIDGE="$SCRIPT_DIR/nx-audio-bridge"
AUDIO_WORKFLOW="$SCRIPT_DIR/nx-audio-workflow"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  N-Xyme Audio Workflow - Hybrid Bitwig/Ableton System${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Check if Bitwig OSC is enabled
echo -e "${YELLOW}⚠️  BEFORE RUNNING: Enable OSC in Bitwig Studio${NC}"
echo "   1. Open Bitwig → Settings → Controllers/Remote"
echo "   2. Enable OSC and set port to 8000"
echo ""

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Stopping services...${NC}"
    pkill -f "bitwig_client.py" 2>/dev/null || true
    pkill -f "workflow_engine.py" 2>/dev/null || true
    pkill -f "mcp_server.py" 2>/dev/null || true
    echo -e "${GREEN}Done.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Parse arguments
MODE="${1:-full}"

case "$MODE" in
    client)
        echo -e "${GREEN}Starting Bitwig OSC client...${NC}"
        cd "$AUDIO_BRIDGE"
        python3 bitwig_client.py
        ;;
    workflow)
        echo -e "${GREEN}Starting Workflow Engine...${NC}"
        cd "$AUDIO_WORKFLOW"
        python3 workflow_engine.py
        ;;
    mcp)
        echo -e "${GREEN}Starting MCP Server...${NC}"
        cd "$AUDIO_BRIDGE"
        python3 mcp_server.py
        ;;
    full|all)
        echo -e "${GREEN}Starting FULL stack (all 3 services)...${NC}"
        echo ""
        
        # Start Bitwig client in background
        echo -e "${BLUE}[1/3]${NC} Bitwig OSC Client"
        cd "$AUDIO_BRIDGE" && python3 bitwig_client.py &
        CLIENT_PID=$!
        sleep 1
        
        # Start workflow engine in background  
        echo -e "${BLUE}[2/3]${NC} Workflow Engine"
        cd "$AUDIO_WORKFLOW" && python3 workflow_engine.py &
        WORKFLOW_PID=$!
        sleep 1
        
        # Start MCP server in background
        echo -e "${BLUE}[3/3]${NC} MCP Server (optional AI commands)"
        cd "$AUDIO_BRIDGE" && python3 mcp_server.py &
        MCP_PID=$!
        
        echo ""
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  All services running!${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
        echo ""
        echo "Services:"
        echo "  • Bitwig OSC Client  → sends commands to Bitwig"
        echo "  • Workflow Engine   → parses your natural language"
        echo "  • MCP Server        → AI-powered voice commands"
        echo ""
        echo "Try these commands:"
        echo "  → create ableton session style template"
        echo "  → create push style workflow"
        echo "  → create hybrid track layering"
        echo ""
        echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
        
        wait
        ;;
    *)
        echo "Usage: $0 [client|workflow|mcp|full]"
        echo ""
        echo "Modes:"
        echo "  client    - Start only Bitwig OSC client"
        echo "  workflow  - Start only workflow engine"  
        echo "  mcp       - Start only MCP server"
        echo "  full      - Start all 3 services (default)"
        exit 1
        ;;
esac