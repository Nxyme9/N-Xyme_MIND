#!/bin/bash
# Stop all SOCKS5 proxy backends
set -e

PID_DIR="/tmp/socks5-proxies"

if [ ! -d "$PID_DIR" ]; then
    echo "No SOCKS5 proxies running (no PID directory)"
    exit 0
fi

echo "Stopping SOCKS5 proxies..."

for pid_file in "$PID_DIR"/socks5-*.pid; do
    if [ -f "$pid_file" ]; then
        PID=$(cat "$pid_file")
        PORT=$(basename "$pid_file" | sed 's/socks5-//;s/.pid//')
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            echo "  Stopped SOCKS5 on port $PORT (PID: $PID)"
        else
            echo "  SOCKS5 on port $PORT not running (stale PID: $PID)"
        fi
        rm -f "$pid_file"
    fi
done

# Also kill any remaining python SOCKS5 servers on those ports
for port in $(seq 1080 1087); do
    if lsof -i :$port >/dev/null 2>&1; then
        fuser -k $port/tcp 2>/dev/null || true
        echo "  Killed process on port $port"
    fi
done

echo "All SOCKS5 proxies stopped"
