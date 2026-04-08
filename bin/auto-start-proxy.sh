#!/bin/bash
# Auto-start N-Xyme Router Proxy on login
# Add to ~/.bashrc or ~/.profile: source /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/bin/auto-start-proxy.sh

PROXY_PID_FILE="/tmp/router-proxy.pid"
PROXY_LOG="/tmp/router-proxy.log"
PROJECT_DIR="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"

# Check if proxy is already running
if [ -f "$PROXY_PID_FILE" ] && kill -0 "$(cat "$PROXY_PID_FILE")" 2>/dev/null; then
    # Verify it's actually our proxy
    if curl -s --max-time 2 http://localhost:8080/health >/dev/null 2>&1; then
        echo "N-Xyme Proxy already running (PID: $(cat "$PROXY_PID_FILE"))"
        return 0
    fi
fi

# Check if port 8080 is in use by another process
if lsof -i :8080 >/dev/null 2>&1; then
    # Try to kill any existing proxy
    pkill -f "openai_proxy" 2>/dev/null || true
    sleep 1
fi

cd "$PROJECT_DIR"

# Use uv run or directly invoke venv python
if command -v uv &>/dev/null && [ -f "$PROJECT_DIR/pyproject.toml" ]; then
    # Use uv to run (handles dependencies automatically)
    PYTHON_CMD="uv run --no-sync"
else
    # Fallback to venv python
    PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
    if [ ! -f "$PYTHON_BIN" ]; then
        PYTHON_BIN="python3"
    fi
    PYTHON_CMD="$PYTHON_BIN"
fi

export PYTHONPATH="$PROJECT_DIR"

# Load API keys from .env if exists
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# Export the 5 OpenRouter keys
export OPENROUTER_API_KEY_1="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"
export OPENROUTER_API_KEY_2="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"
export OPENROUTER_API_KEY_3="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"
export OPENROUTER_API_KEY_4="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"
export OPENROUTER_API_KEY_5="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"

# Start proxy in background
if [[ "$PYTHON_CMD" == "uv run"* ]]; then
    nohup $PYTHON_CMD -m packages.infrastructure.proxy.openai_proxy > "$PROXY_LOG" 2>&1 &
else
    nohup "$PYTHON_CMD" -m packages.infrastructure.proxy.openai_proxy > "$PROXY_LOG" 2>&1 &
fi
echo $! > "$PROXY_PID_FILE"

# Wait and verify
sleep 3
if curl -s --max-time 5 http://localhost:8080/health >/dev/null 2>&1; then
    echo "N-Xyme Proxy started successfully (PID: $(cat "$PROXY_PID_FILE"))"
else
    echo "WARNING: Proxy may not have started correctly. Check $PROXY_LOG"
    cat "$PROXY_LOG" | tail -10
fi
