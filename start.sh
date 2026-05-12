#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

show_menu() {
    echo ""
    echo "╔═══════════════════════════════════════════════╗"
    echo "║         N-Xyme_MIND Quick Start                ║"
    echo "╠═══════════════════════════════════════════════╣"
    echo "║  1. Start ALL (backend + frontend)             ║"
    echo "║  2. Backend only                               ║"
    echo "║  3. Frontend only (Next.js on port 3004)      ║"
    echo "║  4. OpenCode (full workspace)                  ║"
    echo "║  5. Status check                              ║"
    echo "║  6. Stop all services                        ║"
    echo "║  0. Exit                                      ║"
    echo "╚═══════════════════════════════════════════════╝"
    echo ""
}

start_backend() {
    echo "→ Starting backend services..."
    if [ -f "$ROOT/bin/start-backend.sh" ]; then
        bash "$ROOT/bin/start-backend.sh"
    else
        echo "Error: start-backend.sh not found"
        return 1
    fi
}

start_frontend() {
    echo "→ Starting frontend (Next.js)..."
    cd "$ROOT/frontend"
    nohup npx next dev -p 3004 > "$ROOT/logs/frontend.log" 2>&1 &
    echo "Frontend starting on http://localhost:3004"
}

start_opencode() {
    echo "→ Launching OpenCode..."
    cd "$ROOT"
    exec ~/.opencode/bin/opencode "$@"
}

check_status() {
    echo "→ Checking services..."
    echo ""
    
    echo "Backend (brain_mcp):"
    if curl -sf --max-time 2 http://localhost:8765/health 2>/dev/null; then
        echo "  ✓ Running on http://localhost:8765"
    else
        echo "  ✗ Not running"
    fi
    
    echo ""
    echo "Frontend (Next.js):"
    if curl -sf --max-time 2 http://localhost:3004 2>/dev/null; then
        echo "  ✓ Running on http://localhost:3004"
    else
        echo "  ✗ Not running"
    fi
    
    echo ""
    echo "GGUF Server:"
    for port in 8080 8088 8086; do
        if curl -sf --max-time 2 "http://localhost:$port/v1/models" 2>/dev/null; then
            echo "  ✓ Running on http://localhost:$port"
            break
        fi
    done
}

stop_all() {
    echo "→ Stopping all services..."
    pkill -f "brain_mcp" 2>/dev/null || true
    pkill -f "http_gateway" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    echo "Done."
}

if [ $# -gt 0 ]; then
    case "$1" in
        1|all)      start_backend; start_frontend ;;
        2|backend)  start_backend ;;
        3|frontend) start_frontend ;;
        4|opencode) shift; start_opencode "$@" ;;
        5|status)   check_status ;;
        6|stop)     stop_all ;;
        *)          echo "Usage: $0 [all|backend|frontend|opencode|status|stop]"; exit 1 ;;
    esac
    exit 0
fi

while true; do
    show_menu
    read -p "Select option: " choice
    
    case "$choice" in
        1) start_backend; start_frontend; break ;;
        2) start_backend; break ;;
        3) start_frontend; break ;;
        4) start_opencode; break ;;
        5) check_status ;;
        6) stop_all ;;
        0) echo "Exiting."; exit 0 ;;
        *) echo "Invalid option." ;;
    esac
done