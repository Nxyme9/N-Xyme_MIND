#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source environment
source "$ROOT/env.sh"

# L0 health check (<1s)
if ! bash "$ROOT/bin/health-l0-blink.sh" 2>/dev/null; then
    echo "Health check failed. Run: bash $ROOT/bin/health-l0-blink.sh"
    exit 1
fi

# Sync canonical config to .opencode/
cp "$ROOT/opencode.json" "$ROOT/.opencode/opencode.json" 2>/dev/null || true

# Load .env if exists
[ -f "$ROOT/.env" ] && set -a && source "$ROOT/.env" && set +a

# Start remote services in background (telegram bot + dashboard)
mkdir -p "$ROOT/logs"
echo "Starting remote services..."
nohup bash "$ROOT/athena/examples/scripts/start-remote-services.sh" > "$ROOT/logs/remote-services.log" 2>&1 &
REMOTE_PID=$!
echo "Remote services started (PID: $REMOTE_PID)"

# Launch OpenCode
cd "$ROOT"
exec ~/.opencode/bin/opencode "$@"
