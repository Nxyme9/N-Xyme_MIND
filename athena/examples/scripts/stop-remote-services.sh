#!/bin/bash
# Stop remote services script
# Stops both the Telegram bot and dashboard backend

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"

echo "Stopping remote services..."

# Stop bot if running
if [ -f "$LOG_DIR/bot.pid" ]; then
    BOT_PID=$(cat "$LOG_DIR/bot.pid")
    if kill -0 "$BOT_PID" 2>/dev/null; then
        echo "Stopping bot (PID: $BOT_PID)..."
        kill "$BOT_PID" 2>/dev/null
        sleep 1
        # Force kill if still running
        kill -9 "$BOT_PID" 2>/dev/null
    fi
    rm -f "$LOG_DIR/bot.pid"
fi

# Stop dashboard if running
if [ -f "$LOG_DIR/dashboard.pid" ]; then
    DASH_PID=$(cat "$LOG_DIR/dashboard.pid")
    if kill -0 "$DASH_PID" 2>/dev/null; then
        echo "Stopping dashboard (PID: $DASH_PID)..."
        kill "$DASH_PID" 2>/dev/null
        sleep 1
        # Force kill if still running
        kill -9 "$DASH_PID" 2>/dev/null
    fi
    rm -f "$LOG_DIR/dashboard.pid"
fi

echo "All services stopped!"
