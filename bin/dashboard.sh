#!/usr/bin/env bash
# N-Xyme MIND Dashboard Launcher
# Usage: ./bin/dashboard.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Use the athena venv which has textual installed
PYTHON="$ROOT_DIR/venvs/athena/bin/python3"

# Check if textual is installed
if ! "$PYTHON" -c "import textual" 2>/dev/null; then
    echo "Installing textual..."
    "$PYTHON" -m pip install textual -q
fi

# Run the dashboard v2
cd "$ROOT_DIR"
PYTHONPATH=. "$PYTHON" -m packages.platform_layer.tui.dashboard_v2
