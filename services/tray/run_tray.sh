#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# run_tray.sh — Launch N-Xyme MIND System Tray in background.
#
# Usage:
#   bash run_tray.sh [--debug]    # Launch with debug logging
#   bash run_tray.sh --fg        # Launch in foreground (for testing)
#   bash run_tray.sh --kill      # Kill existing tray process
#   bash run_tray.sh --status    # Check if tray is running
# ──────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAY_PY="${SCRIPT_DIR}/nx_tray.py"
PID_FILE="${SCRIPT_DIR}/.tray.pid"
LOG_FILE="${SCRIPT_DIR}/run_tray.log"

# Color helpers
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ── Ensure dependencies ─────────────────────────────────────────────────

ensure_python_deps() {
    # Check if PyQt6 is available
    if ! python3 -c "from PyQt6.QtWidgets import QApplication" 2>/dev/null; then
        warn "PyQt6 not found — attempting install…"
        pip3 install PyQt6 2>&1 | tail -1
        if ! python3 -c "from PyQt6.QtWidgets import QApplication" 2>/dev/null; then
            error "PyQt6 installation failed. Try: pip3 install PyQt6"
            exit 1
        fi
        info "PyQt6 installed successfully"
    fi
}

# ── PID management ──────────────────────────────────────────────────────

save_pid() {
    echo "$1" > "$PID_FILE"
}

read_pid() {
    if [[ -f "$PID_FILE" ]]; then
        cat "$PID_FILE"
    else
        echo ""
    fi
}

is_running() {
    local pid
    pid="$(read_pid)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        return 0
    fi
    # Also check by process name
    if pgrep -f "nx_tray.py" | grep -v "$$" > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

# ── Commands ────────────────────────────────────────────────────────────

cmd_status() {
    if is_running; then
        local pid
        pid="$(read_pid)"
        if [[ -z "$pid" ]] || ! kill -0 "$pid" 2>/dev/null; then
            pid="$(pgrep -f "nx_tray.py" | head -1)"
        fi
        info "N-Xyme Tray is RUNNING (PID ${pid})"
        echo ""
        echo "  Log file:  ${LOG_FILE}"
        echo "  Tray app:  ${TRAY_PY}"
        echo ""
        echo "  Quick commands:"
        echo "    bash run_tray.sh --kill    # Stop tray"
        echo "    bash run_tray.sh --fg      # Run in foreground"
        exit 0
    else
        warn "N-Xyme Tray is NOT running"
        exit 1
    fi
}

cmd_kill() {
    if is_running; then
        local pid
        pid="$(read_pid)"
        if [[ -z "$pid" ]] || ! kill -0 "$pid" 2>/dev/null; then
            pid="$(pgrep -f "nx_tray.py" | head -1)"
        fi
        info "Stopping N-Xyme Tray (PID ${pid})…"
        kill "$pid" 2>/dev/null || true
        # Wait up to 3 seconds
        for i in 1 2 3; do
            if ! kill -0 "$pid" 2>/dev/null; then
                break
            fi
            sleep 1
        done
        # Force if still alive
        if kill -0 "$pid" 2>/dev/null; then
            warn "Force killing PID ${pid}…"
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
        info "Tray stopped"
    else
        warn "No running tray found"
    fi
}

cmd_foreground() {
    ensure_python_deps
    info "Starting N-Xyme Tray in FOREGROUND (Ctrl+C to stop)…"
    exec python3 "$TRAY_PY" --debug
}

cmd_background() {
    ensure_python_deps

    # Kill existing instance first
    if is_running; then
        warn "Tray already running — stopping first…"
        cmd_kill
        sleep 1
    fi

    info "Starting N-Xyme Tray in BACKGROUND…"

    # Start with daemon flag — it forks itself
    nohup python3 "$TRAY_PY" --daemon > "$LOG_FILE" 2>&1 &
    local pid=$!
    save_pid "$pid"
    disown "$pid"

    # Verify it started
    sleep 2
    if kill -0 "$pid" 2>/dev/null; then
        info "N-Xyme Tray started (PID ${pid})"
        info "Log: ${LOG_FILE}"
        echo ""
        echo "Use: bash run_tray.sh --status   # Check status"
        echo "     bash run_tray.sh --kill     # Stop tray"
        echo "     tail -f ${LOG_FILE}         # Follow logs"
    else
        error "Tray failed to start — check log:"
        tail -5 "$LOG_FILE" 2>/dev/null || true
        exit 1
    fi
}

# ── Main dispatch ───────────────────────────────────────────────────────

case "${1:-}" in
    --status|-s)
        cmd_status
        ;;
    --kill|-k)
        cmd_kill
        ;;
    --fg|--foreground|-f)
        cmd_foreground
        ;;
    --debug|-d)
        # Background with debug logging
        ensure_python_deps
        nohup python3 "$TRAY_PY" --daemon --debug > "$LOG_FILE" 2>&1 &
        local pid=$!
        save_pid "$pid"
        disown "$pid"
        sleep 2
        info "N-Xyme Tray started with debug (PID ${pid})"
        info "Log: ${LOG_FILE}"
        ;;
    --help|-h)
        echo "N-Xyme MIND System Tray — Launcher"
        echo ""
        echo "Usage: bash run_tray.sh [OPTION]"
        echo ""
        echo "Options:"
        echo "  (no args)    Start tray in background (default)"
        echo "  --fg         Start in foreground (testing)"
        echo "  --debug      Start with debug logging"
        echo "  --status     Check if tray is running"
        echo "  --kill       Stop the tray"
        echo "  --help       Show this help"
        ;;
    "")
        cmd_background
        ;;
    *)
        error "Unknown option: $1"
        echo "Try: bash run_tray.sh --help"
        exit 1
        ;;
esac
