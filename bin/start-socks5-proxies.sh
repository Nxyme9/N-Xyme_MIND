#!/bin/bash
# Start 8 SOCKS5 proxy backends for VPN IP rotation
# Each SOCKS5 proxy provides a different exit IP
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_DIR="/tmp/socks5-proxies"

mkdir -p "$PID_DIR"

echo "Starting 8 SOCKS5 proxy backends..."

# Option A: SSH-based SOCKS5 proxies (requires SSH access to proxy servers)
# Uncomment and configure if you have SSH-accessible servers:
#
# PROXY_SERVERS=(
#   "user@proxy-1.example.com"
#   "user@proxy-2.example.com"
#   "user@proxy-3.example.com"
#   "user@proxy-4.example.com"
#   "user@proxy-5.example.com"
#   "user@proxy-6.example.com"
#   "user@proxy-7.example.com"
#   "user@proxy-8.example.com"
# )
#
# for i in "${!PROXY_SERVERS[@]}"; do
#   port=$((1080 + i))
#   server="${PROXY_SERVERS[$i]}"
#   ssh -D $port -f -N -o ServerAliveInterval=30 -o ServerAliveCountMax=3 "$server"
#   echo $! > "$PID_DIR/socks5-$port.pid"
#   echo "  SOCKS5 proxy started on port $port via $server"
# done

# Option B: Use local Python SOCKS5 server (for testing)
# Each instance runs on a different port
for i in $(seq 0 7); do
  port=$((1080 + i))
  
  # Check if port is already in use
  if lsof -i :$port >/dev/null 2>&1; then
    echo "  Port $port already in use, skipping"
    continue
  fi
  
  # Start local SOCKS5 server
  nohup python3 "$SCRIPT_DIR/socks5-server.py" --port $port > "/tmp/socks5-$port.log" 2>&1 &
  echo $! > "$PID_DIR/socks5-$port.pid"
  echo "  SOCKS5 proxy started on port $port (PID: $(cat "$PID_DIR/socks5-$port.pid"))"
done

echo ""
echo "SOCKS5 proxies configured on ports 1080-1087"
echo "PID files: $PID_DIR/"
echo ""
echo "To stop all: bash $SCRIPT_DIR/stop-socks5-proxies.sh"
