#!/bin/bash
# Start Telegram Bot with auto-restart

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Load .env if exists
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

LOG_FILE="/tmp/telegram-bot-$(date +%Y%m%d-%H%M%S).log"

echo "Starting N-Xyme MIND Telegram Bot..."
echo "Log file: $LOG_FILE"

# Run with auto-restart on crash
while true; do
    python3 telegram-bot.py 2>&1 | tee -a "$LOG_FILE"
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -ne 0 ]; then
        echo "[$(date)] Bot crashed with exit code $EXIT_CODE. Restarting in 5 seconds..." >> "$LOG_FILE"
        sleep 5
    else
        echo "[$(date)] Bot exited normally" >> "$LOG_FILE"
        break
    fi
done
