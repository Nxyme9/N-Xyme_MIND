#!/usr/bin/env bash
# =============================================================================
# mcp-bulletproof.sh — Bulletproof MCP lifecycle manager
# =============================================================================
# Problem: OpenCode manages MCPs via stdio. When OpenCode dies, MCPs become
#          zombies → MCPO connection errors (32000) and timeouts (32001).
# Solution: Run brain_mcp as session leader (immune to terminal death),
#           supervised by this daemon with auto-restart.
# =============================================================================

set -uo pipefail

readonly ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly VENV_PY="$ROOT/.venv/bin/python"
readonly PID_DIR="$ROOT/.sisyphus/mcp_pids"
readonly LOG_FILE="$PID_DIR/brain_mcp.log"
readonly STDOUT_FILE="$PID_DIR/brain_mcp.stdout"
readonly STDERR_FILE="$PID_DIR/brain_mcp.stderr"
readonly STATE_FILE="$PID_DIR/brain_mcp.state.json"
readonly HEALTH_TIMEOUT=5
readonly CHECK_INTERVAL=30
readonly MAX_RESTART_DELAY=300

# Exponential backoff state
RESTART_DELAY=30
MAX_RESTARTS=50
RESTART_COUNT=0

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

# ── Helpers ──────────────────────────────────────────────────────────────────

log()  { echo -e "$(date '+%Y-%m-%d %H:%M:%S') [MCP-SUP] $*" | tee -a "$LOG_FILE" >&2; }
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*" | tee -a "$LOG_FILE" >&2; }
err()  { echo -e "${RED}✗${NC} $*" | tee -a "$LOG_FILE" >&2 >&2; }

mkdir -p "$PID_DIR"

# ── State Management ─────────────────────────────────────────────────────────

read_state() {
    if [[ -f "$STATE_FILE" ]]; then
        <"$STATE_FILE" "$VENV_PY" -c "import json,sys; d=json.load(sys.stdin); print(d.get('pid',''), d.get('status','unknown'), d.get('restart_count',0))" 2>/dev/null
    fi
}

write_state() {
    local pid="$1"; local status="$2"; local started_at="${3:-$(date -Iseconds)}"
    local restart_count="${4:-0}"; local last_error="${5:-null}"

    # Write via Python for safe JSON
    "$VENV_PY" -c "
import json, sys
state = {
    'pid': $pid,
    'started_at': '$started_at',
    'restart_count': $restart_count,
    'last_restart_at': $([ "$status" = "running" ] && echo "null" || echo "'$(date -Iseconds)'"),
    'last_error': $last_error,
    'status': '$status'
}
with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)
" 2>/dev/null || true
}

# ── Zombie Detection ────────────────────────────────────────────────────────

find_orphaned_mcp_processes() {
    # Find all MCP-related Python processes
    ps aux 2>/dev/null | grep -E 'packages\.(brain_mcp|learning_engine|intelligence|orchestration|trigger_guardian|catalyst_orchestrator|nx_mind|memory_core|session_pool)' \
        | grep -v grep | awk '{print $2}' | while read pid; do
        # Check if parent is alive
        ppid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
        if [[ -n "$ppid" ]]; then
            if ! ps -p "$ppid" 2>/dev/null | grep -qE 'opencode|npm exec|bash'; then
                echo "$pid"
            fi
        fi
    done
}

cleanup_zombies() {
    log "Checking for orphaned MCP processes..."
    local zombies
    zombies=$(find_orphaned_mcp_processes)
    if [[ -n "$zombies" ]]; then
        warn "Found orphaned MCP processes: $zombies"
        echo "$zombies" | while read pid; do
            log "Killing orphaned process $pid..."
            kill "$pid" 2>/dev/null
        done
        sleep 1
        # Force kill any that are still alive
        echo "$zombies" | while read pid; do
            kill -9 "$pid" 2>/dev/null && log "Force-killed $pid" || true
        done
        log "Zombie cleanup complete"
    else
        log "No orphaned MCP processes found"
    fi
}

# ── Brain MCP Lifecycle ─────────────────────────────────────────────────────

is_process_alive() {
    local pid="$1"
    [[ -d "/proc/$pid" ]] 2>/dev/null
}

is_port_listening() {
    ss -tlnp 2>/dev/null | grep -q ':8765'
}

wait_for_port() {
    local timeout="$1"
    local elapsed=0
    while [[ $elapsed -lt $timeout ]]; do
        if is_port_listening; then
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    return 1
}

start_brain_mcp() {
    log "Starting brain_mcp (HTTP mode on port 8765)..."

    cleanup_zombies

    if is_port_listening; then
        warn "Port 8765 already in use — checking if old process"
        local old_pid
        old_pid=$(ss -tlnp 2>/dev/null | grep ':8765' | grep -oP 'pid=\K[0-9]+' | head -1)
        if [[ -n "$old_pid" ]] && is_process_alive "$old_pid"; then
            log "Old brain_mcp still running on PID $old_pid — stopping first"
            kill "$old_pid" 2>/dev/null
            sleep 2
        fi
    fi

    export PYTHONPATH="$ROOT:$ROOT/packages"

    setsid env PYTHONPATH="$PYTHONPATH" \
        "$VENV_PY" -m packages.brain_mcp --http --port 8765 \
        >> "$STDOUT_FILE" \
        2>> "$STDERR_FILE" \
        < /dev/null &
    local pid=$!

    log "brain_mcp started with PID $pid"

    if wait_for_port 10; then
        write_state "$pid" "running" "$(date -Iseconds)" "$RESTART_COUNT"
        ok "brain_mcp is running (PID $pid, port 8765)"
        RESTART_DELAY=30
        return 0
    else
        local last_lines
        last_lines=$(tail -10 "$STDERR_FILE" 2>/dev/null || echo "no stderr")
        write_state "0" "dead" "" "$RESTART_COUNT" "\"Startup failed: $last_lines\""
        err "brain_mcp failed to start. Last stderr: $last_lines"
        return 1
    fi
}

stop_brain_mcp() {
    local pid
    pid=$(read_state | awk '{print $1}')

    if [[ -z "$pid" ]] || [[ "$pid" = "None" ]]; then
        log "No brain_mcp PID found in state"
        return 0
    fi

    if is_process_alive "$pid"; then
        log "Stopping brain_mcp (PID $pid)..."
        kill "$pid" 2>/dev/null
        sleep 2
        if is_process_alive "$pid"; then
            kill -9 "$pid" 2>/dev/null && log "Force-killed PID $pid" || true
        fi
        ok "brain_mcp stopped"
    else
        log "brain_mcp (PID $pid) already dead"
    fi

    write_state "0" "dead" "" "$RESTART_COUNT"
}

# ── Health Check ─────────────────────────────────────────────────────────────

check_health() {
    local pid
    pid=$(read_state | awk '{print $1}')

    if [[ -z "$pid" ]] || [[ "$pid" = "None" ]] || ! is_process_alive "$pid"; then
        echo "DEAD — process not running"
        return 1
    fi

    if is_port_listening; then
        local resp
        resp=$(curl -s --max-time "$HEALTH_TIMEOUT" http://localhost:8765/health 2>/dev/null)
        if [[ -n "$resp" ]]; then
            ok "brain_mcp (PID $pid) is healthy — HTTP responding"
            return 0
        fi
    fi

    err "brain_mcp (PID $pid) is not responding on port 8765"
    return 1
}

# ── Restart Logic ───────────────────────────────────────────────────────────

restart_with_backoff() {
    local last_error="${1:-"unknown"}"
    RESTART_COUNT=$((RESTART_COUNT + 1))

    if [[ $RESTART_COUNT -gt $MAX_RESTARTS ]]; then
        err "Max restarts ($MAX_RESTARTS) reached. Manual intervention required."
        write_state "0" "dead" "" "$RESTART_COUNT" "\"Max restarts exceeded\""
        exit 1
    fi

    warn "Restart $RESTART_COUNT in ${RESTART_DELAY}s... (last error: $last_error)"

    sleep "$RESTART_DELAY"

    # Exponential backoff
    RESTART_DELAY=$((RESTART_DELAY * 2))
    [[ $RESTART_DELAY -gt $MAX_RESTART_DELAY ]] && RESTART_DELAY=$MAX_RESTART_DELAY

    start_brain_mcp
}

# ── Supervisor Loop ─────────────────────────────────────────────────────────

run_supervisor() {
    log "=== MCP Bulletproof Supervisor Started ==="
    log "PID: $$ | PID_FILE: $PID_DIR/brain_mcp.pid"

    # Write our supervisor PID
    echo "$$" > "$PID_DIR/brain_mcp.supervisor.pid"

    # Initial cleanup
    cleanup_zombies

    # Start brain_mcp
    if ! start_brain_mcp; then
        restart_with_backoff "initial_start_failed"
    fi

    # ── Main supervision loop ──
    while true; do
        sleep "$CHECK_INTERVAL"

        local pid
        pid=$(read_state | awk '{print $1}')

        if [[ -z "$pid" ]] || [[ "$pid" = "None" ]]; then
            log "No PID in state — restarting"
            start_brain_mcp || restart_with_backoff "no_pid_in_state"
            continue
        fi

        if ! is_process_alive "$pid"; then
            err "brain_mcp (PID $pid) is dead"
            start_brain_mcp || restart_with_backoff "process_dead"
            continue
        fi

        # Process alive — update state
        local current_status
        current_status=$(read_state | awk '{print $2}')
        write_state "$pid" "$current_status" "" "$RESTART_COUNT"
        log "brain_mcp (PID $pid) alive — OK"
    done
}

# ── CLI ─────────────────────────────────────────────────────────────────────

cmd_start() {
    # Check if already running
    local pid
    pid=$(read_state | awk '{print $1}')
    if [[ -n "$pid" ]] && [[ "$pid" != "None" ]] && is_process_alive "$pid" 2>/dev/null; then
        ok "brain_mcp already running (PID $pid)"
        return 0
    fi

    cleanup_zombies
    start_brain_mcp
}

cmd_stop() {
    stop_brain_mcp
}

cmd_status() {
    echo ""
    echo "━━━ MCP Bulletproof Status ━━━"
    echo "State file: $STATE_FILE"
    echo ""

    if [[ -f "$STATE_FILE" ]]; then
        cat "$STATE_FILE"
        echo ""
    fi

    local pid
    pid=$(read_state | awk '{print $1}')

    if [[ -n "$pid" ]] && [[ "$pid" != "None" ]] && is_process_alive "$pid" 2>/dev/null; then
        local uptime
        uptime=$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ')
        ok "brain_mcp running — PID $pid — uptime: $uptime"
    else
        err "brain_mcp is NOT running"
    fi

    echo ""
    echo "━━━ Recent Log (last 10 lines) ━━━"
    tail -10 "$LOG_FILE" 2>/dev/null || echo "(no log)"
    echo ""

    echo "━━━ Supervisor PID ━━━"
    if [[ -f "$PID_DIR/brain_mcp.supervisor.pid" ]]; then
        local sup_pid
        sup_pid=$(cat "$PID_DIR/brain_mcp.supervisor.pid")
        if is_process_alive "$sup_pid" 2>/dev/null; then
            ok "Supervisor running (PID $sup_pid)"
        else
            err "Supervisor not running (stale PID $sup_pid)"
        fi
    else
        warn "No supervisor PID file"
    fi
}

cmd_health() {
    cmd_status
    echo ""
    echo "━━━ Health Check ━━━"
    check_health || true
}

cmd_cleanup() {
    log "Running zombie cleanup only (no start)..."
    cleanup_zombies
    ok "Cleanup complete"
}

cmd_restart() {
    cmd_stop
    sleep 2
    cmd_start
}

cmd_daemon() {
    # Daemonize: fork and exit
    run_supervisor &
    local sup_pid=$!
    echo "$sup_pid" > "$PID_DIR/brain_mcp.supervisor.pid"
    disown "$sup_pid" 2>/dev/null
    ok "Supervisor daemonized (PID $sup_pid)"
}

# ── Main ───────────────────────────────────────────────────────────────────

ACTION="${1:-}"

case "$ACTION" in
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    status)  cmd_status ;;
    health)  cmd_health ;;
    cleanup) cmd_cleanup ;;
    restart) cmd_restart ;;
    daemon)  cmd_daemon ;;
    supervisor|run)
                cleanup_zombies
                run_supervisor ;;
    *)
        echo "Usage: $0 {start|stop|status|health|cleanup|restart|daemon|supervisor}"
        echo ""
        echo "  start    — Start brain_mcp (one-shot, no supervision)"
        echo "  stop     — Stop brain_mcp"
        echo "  status   — Show PID, state, uptime, recent log"
        echo "  health   — Full status + health check"
        echo "  cleanup  — Kill orphaned MCP processes only"
        echo "  restart  — Stop + start"
        echo "  daemon   — Fork and run as daemon with auto-restart"
        echo "  supervisor|run — Run supervisor loop (blocks)"
        echo ""
        echo "Recommended: $0 daemon (starts with auto-restart supervision)"
        exit 1
        ;;
esac
