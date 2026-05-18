#!/bin/bash
# N-Xyme MIND Dashboard Runner
# Checks for rich, installs if needed, launches dashboard

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARD="$SCRIPT_DIR/dashboard.py"

echo "Starting N-Xyme MIND Dashboard..."

# Check if rich is installed, install if not
if ! python3 -c "import rich" 2>/dev/null; then
    echo "Installing rich..."
    pip install rich --break-system-packages || pip install rich
fi

# Trap Ctrl+C for clean shutdown
cleanup() {
    echo ""
    echo "Dashboard shutting down..."
    exit 0
}
trap cleanup SIGINT SIGTERM

# Launch the dashboard
exec python3 "$DASHBOARD"