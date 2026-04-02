#!/usr/bin/env bash
# launch_athena.sh
# ============================================================================
# Purpose: Launch the Active OS Daemon (Athena Sidecar/Watcher)
# Usage:   ./launch_athena.sh [--background]
# ============================================================================

set -e

# Resolve Repo Root using .athena_root marker
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REPO_ROOT="$SCRIPT_DIR"
while [ ! -f "$REPO_ROOT/.athena_root" ] && [ "$REPO_ROOT" != "/" ]; do
    REPO_ROOT="$(dirname "$REPO_ROOT")"
done
if [ ! -f "$REPO_ROOT/.athena_root" ]; then
    # Fallback: assume script is at scripts/ inside repo root
    REPO_ROOT="$(dirname "$SCRIPT_DIR")"
fi

# Locate Daemon Script (within this repo's src/)
DAEMON_SCRIPT="$REPO_ROOT/src/athena/core/athenad.py"

if [[ ! -f "$DAEMON_SCRIPT" ]]; then
    echo "❌ Error: Daemon script not found at $DAEMON_SCRIPT"
    exit 1
fi

echo "🚀 Launching Athena Daemon..."
echo "   Target: $DAEMON_SCRIPT"

if [[ "$1" == "--background" ]]; then
    # Guard: Prevent duplicate daemons
    PID_FILE="$REPO_ROOT/.athenad.pid"
    if [[ -f "$PID_FILE" ]]; then
        OLD_PID=$(cat "$PID_FILE")
        if kill -0 "$OLD_PID" 2>/dev/null; then
            echo "⚠️  Daemon already running (PID: $OLD_PID). Use --stop first."
            exit 0
        else
            echo "🧹 Stale PID file found. Cleaning up..."
            rm "$PID_FILE"
        fi
    fi

    # Run in background and detach
    nohup python3 "$DAEMON_SCRIPT" > "$REPO_ROOT/athenad.log" 2>&1 &
    PID=$!
    echo "✅ Athena Daemon started in background."
    echo "   PID: $PID"
    echo "   Log: $REPO_ROOT/athenad.log"
    
    echo "$PID" > "$REPO_ROOT/.athenad.pid"
elif [[ "$1" == "--stop" ]]; then
    # Stop the daemon
    PID_FILE="$REPO_ROOT/.athenad.pid"
    if [[ -f "$PID_FILE" ]]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "🛑 Stopping Athena Daemon (PID: $PID)..."
            kill "$PID"
            rm "$PID_FILE"
            echo "✅ Daemon stopped."
        else
            echo "⚠️  Daemon process $PID not found. Cleaning up pidfile."
            rm "$PID_FILE"
        fi
    else
        echo "⚠️  No .athenad.pid found. Is the daemon running?"
    fi
else
    # Run in foreground
    python3 "$DAEMON_SCRIPT"
fi
