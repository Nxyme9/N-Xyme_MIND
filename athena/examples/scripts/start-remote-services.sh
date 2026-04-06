#!/bin/bash
# Start remote services script
# Launches both the Telegram bot and dashboard backend in the background

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

echo "Starting remote services..."

# Start the PTB bot in background
echo "Launching Telegram bot..."
python3 "$SCRIPT_DIR/bot/main.py" > "$LOG_DIR/bot.log" 2>&1 &
BOT_PID=$!
echo "Bot started with PID: $BOT_PID"

# Start the dashboard backend in background
echo "Launching dashboard backend..."
python3 "$SCRIPT_DIR/dashboard/backend/main.py" > "$LOG_DIR/dashboard.log" 2>&1 &
DASH_PID=$!
echo "Dashboard started with PID: $DASH_PID"

# Save PIDs to file for stop script
echo "$BOT_PID" > "$LOG_DIR/bot.pid"
echo "$DASH_PID" > "$LOG_DIR/dashboard.pid"

echo "All services started successfully!"
echo "  - Bot: PID $BOT_PID"
echo "  - Dashboard: PID $DASH_PID"
echo "Logs available at: $LOG_DIR"
