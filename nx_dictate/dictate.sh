#!/bin/bash
# N-Xyme Dictate - Quick Start Script
# Hold mouse side button → record → release → types text

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/.venv/bin/python3"

# Kill any existing instances
pkill -f "nx_dictate" 2>/dev/null
sleep 0.5

# Start with realtime mode (types on release, not during speech!)
exec $VENV -m nx_dictate.__main__ --model tiny --realtime "$@"