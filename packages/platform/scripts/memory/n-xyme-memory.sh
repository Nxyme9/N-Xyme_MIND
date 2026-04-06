#!/usr/bin/env bash
# N-Xyme Memory Daemon - Management Script
# Usage: ./bin/n-xyme-memory.sh {start|stop|status|restart|logs|health|install|uninstall}

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$ROOT_DIR/context/memory/daemon.pid"
STATUS_FILE="$ROOT_DIR/context/memory/daemon-status.json"
LOG_FILE="$ROOT_DIR/context/memory/daemon.log"
SERVICE_FILE="$SCRIPT_DIR/n-xyme-memory.service"
PYTHON="$ROOT_DIR/.venv/bin/python3"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info() { echo -e "${BLUE}[INFO]${NC} $*"; }
ok() { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    fi
}

is_running() {
    local pid
    pid=$(get_pid)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        return 0
    fi
    return 1
}

do_start() {
    if is_running; then
        warn "Daemon already running (PID: $(get_pid))"
        return 0
    fi

    info "Starting N-Xyme Memory Daemon..."
    cd "$ROOT_DIR"
    nohup "$PYTHON" -m src.memory.daemon > /dev/null 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_FILE"

    # Wait for startup
    sleep 2
    if is_running; then
        ok "Daemon started (PID: $pid)"
    else
        error "Daemon failed to start. Check logs: $LOG_FILE"
        return 1
    fi
}

do_stop() {
    if ! is_running; then
        warn "Daemon is not running"
        rm -f "$PID_FILE"
        return 0
    fi

    local pid
    pid=$(get_pid)
    info "Stopping daemon (PID: $pid)..."
    kill "$pid" 2>/dev/null || true

    # Wait for graceful shutdown
    local count=0
    while kill -0 "$pid" 2>/dev/null && [ $count -lt 10 ]; do
        sleep 1
        count=$((count + 1))
    done

    if kill -0 "$pid" 2>/dev/null; then
        warn "Daemon didn't stop gracefully, forcing..."
        kill -9 "$pid" 2>/dev/null || true
    fi

    rm -f "$PID_FILE"
    ok "Daemon stopped"
}

do_status() {
    if is_running; then
        local pid
        pid=$(get_pid)
        ok "Daemon is running (PID: $pid)"

        # Show uptime
        local start_time
        start_time=$(ps -o lstart= -p "$pid" 2>/dev/null || echo "unknown")
        if [ "$start_time" != "unknown" ]; then
            info "Started: $start_time"
        fi
    else
        warn "Daemon is not running"
    fi

    # Show status file
    if [ -f "$STATUS_FILE" ]; then
        echo ""
        info "Status file ($STATUS_FILE):"
        python3 -c "
import json
with open('$STATUS_FILE') as f:
    data = json.load(f)
for key, value in data.items():
    if isinstance(value, dict):
        print(f'  {key}:')
        for k, v in value.items():
            print(f'    {k}: {v}')
    else:
        print(f'  {key}: {value}')
" 2>/dev/null || cat "$STATUS_FILE"
    fi
}

do_restart() {
    do_stop
    sleep 1
    do_start
}

do_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -50 "$LOG_FILE"
    else
        warn "No log file found: $LOG_FILE"
    fi
}

do_health() {
    if ! is_running; then
        error "Daemon is not running"
        return 1
    fi

    info "Running health check..."
    cd "$ROOT_DIR"
    "$PYTHON" -c "
import sys
sys.path.insert(0, '.')
from src.memory.health_monitor import HealthMonitor
m = HealthMonitor('context/memory/file_registry.db', 'context/memory/file_chroma')
h = m.check_all()
score = m.get_health_score()
alerts = m.get_alerts()

print(f'Health Score: {score:.2f}/1.00')
print()
for check_name, check_data in h.get('checks', {}).items():
    status = check_data.get('status', 'unknown')
    if status == 'healthy':
        print(f'  ✅ {check_name}')
    elif status == 'warning':
        print(f'  ⚠️  {check_name}')
    else:
        print(f'  ❌ {check_name}')
    if 'details' in check_data:
        for k, v in check_data['details'].items():
            print(f'      {k}: {v}')

if alerts:
    print()
    print(f'Alerts ({len(alerts)}):')
    for alert in alerts:
        print(f'  ⚠️  {alert}')
else:
    print()
    print('No alerts')
" 2>&1
}

do_install() {
    info "Installing systemd service..."
    if [ "$(id -u)" -ne 0 ]; then
        error "This command requires root. Run with sudo:"
        echo "  sudo $0 install"
        return 1
    fi

    cp "$SERVICE_FILE" /etc/systemd/system/n-xyme-memory.service
    systemctl daemon-reload
    systemctl enable n-xyme-memory.service
    ok "Service installed and enabled"
    info "Start with: systemctl start n-xyme-memory"
}

do_uninstall() {
    info "Uninstalling systemd service..."
    if [ "$(id -u)" -ne 0 ]; then
        error "This command requires root. Run with sudo:"
        echo "  sudo $0 uninstall"
        return 1
    fi

    systemctl stop n-xyme-memory.service 2>/dev/null || true
    systemctl disable n-xyme-memory.service 2>/dev/null || true
    rm -f /etc/systemd/system/n-xyme-memory.service
    systemctl daemon-reload
    ok "Service uninstalled"
}

# Main
case "${1:-status}" in
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    status)
        do_status
        ;;
    restart)
        do_restart
        ;;
    logs)
        do_logs
        ;;
    health)
        do_health
        ;;
    install)
        do_install
        ;;
    uninstall)
        do_uninstall
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart|logs|health|install|uninstall}"
        echo ""
        echo "Commands:"
        echo "  start     - Start the memory daemon"
        echo "  stop      - Stop the memory daemon"
        echo "  status    - Show daemon status"
        echo "  restart   - Restart the daemon"
        echo "  logs      - Show recent logs"
        echo "  health    - Run health check"
        echo "  install   - Install as systemd service (requires sudo)"
        echo "  uninstall - Remove systemd service (requires sudo)"
        exit 1
        ;;
esac
