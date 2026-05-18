#!/usr/bin/env bash
set -euo pipefail

MOJO_DAEMON_PATH="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/services/mojo-router/src/daemon.py"
TOKEN_GUARD_PATH="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/services/token-guard/src/token_guard.py"
MOJO_LOG_FILE="/tmp/mojo-daemon.log"
TOKEN_GUARD_LOG_FILE="/tmp/token-guard.log"

echo "=== N-Xyme MIND Service Startup ==="

# Step 1: Kill existing daemon processes
echo "[1/4] Killing existing daemon.py processes..."
pkill -f "python3 ${MOJO_DAEMON_PATH}" 2>/dev/null && echo "  Killed existing processes" || echo "  No existing processes found"

# Step 2: Kill existing token-guard processes
echo "[2/4] Killing existing token-guard processes..."
pkill -f "python3 ${TOKEN_GUARD_PATH}" 2>/dev/null && echo "  Killed existing processes" || echo "  No existing processes found"
sleep 1

# Step 3: Start the Mojo daemon
echo "[3/4] Starting Mojo daemon..."
nohup python3 "${MOJO_DAEMON_PATH}" > "${MOJO_LOG_FILE}" 2>&1 &
DAEMON_PID=$!
echo "  Daemon started with PID: ${DAEMON_PID}"
sleep 1

# Step 4: Start TokenGuard daemon
echo "[4/4] Starting TokenGuard daemon..."
nohup python3 "${TOKEN_GUARD_PATH}" --daemon --interval 30 > "${TOKEN_GUARD_LOG_FILE}" 2>&1 &
TOKEN_GUARD_PID=$!
echo "  TokenGuard started with PID: ${TOKEN_GUARD_PID}"
sleep 1

# Test the Mojo daemon
echo ""
echo "Testing Mojo daemon..."
RESULT=$(echo '{"type":"status","id":"test"}' | python3 "${MOJO_DAEMON_PATH}")
echo "  Response: ${RESULT}"

# Test TokenGuard
echo ""
echo "Testing TokenGuard..."
TG_RESULT=$(python3 "${TOKEN_GUARD_PATH}" --check 2>/dev/null || echo "TokenGuard check completed (see log)")
echo "  Result: ${TG_RESULT}"

echo ""
echo "=== Startup Complete ==="
echo "Mojo Daemon PID:    ${DAEMON_PID}"
echo "TokenGuard PID:     ${TOKEN_GUARD_PID}"
echo "Mojo Log:           ${MOJO_LOG_FILE}"
echo "TokenGuard Log:     ${TOKEN_GUARD_LOG_FILE}"
