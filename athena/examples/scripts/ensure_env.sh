#!/usr/bin/env bash
# ensure_env.sh — Zero-Dependency Environment Validator
# ======================================================
# Called by boot.py to verify the runtime environment.
# Returns 0 if healthy, non-zero if repairs needed.
#
# Supports both venv AND system-level Python installations.
# If deps exist in system Python, venv is optional.
#
# Usage:
#   ./ensure_env.sh         # Check only
#   ./ensure_env.sh --fix   # Attempt auto-repair

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
VENV_PATH="${PROJECT_ROOT}/.venv"
PYTHON_MIN="3.10"

echo "🔍 Athena Environment Check"
echo "─────────────────────────────────────"

# Check 1: Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [[ "$(printf '%s\n' "$PYTHON_MIN" "$PYTHON_VERSION" | sort -V | head -n1)" != "$PYTHON_MIN" ]]; then
    echo "❌ Python $PYTHON_MIN+ required (found $PYTHON_VERSION)"
    exit 1
fi
echo "✅ Python $PYTHON_VERSION"

# Check 2: Virtual environment (optional if system Python has deps)
if [ -d "$VENV_PATH" ]; then
    echo "✅ Virtual environment exists"
    source "$VENV_PATH/bin/activate" 2>/dev/null || true
else
    echo "ℹ️  No .venv found — using system Python"
fi

# Check 3: Core dependencies (check active Python, venv or system)
if ! python3 -c "from supabase import create_client" 2>/dev/null; then
    echo "⚠️ Supabase SDK not installed"
    if [ "$1" == "--fix" ]; then
        pip install -q supabase
        echo "✅ Supabase installed"
    else
        exit 3
    fi
else
    echo "✅ Core dependencies verified"
fi

# Check 4: .env file
if [ ! -f "${PROJECT_ROOT}/.env" ]; then
    echo "⚠️ .env file missing"
    if [ "$1" == "--fix" ] && [ -f "${PROJECT_ROOT}/.env.example" ]; then
        cp "${PROJECT_ROOT}/.env.example" "${PROJECT_ROOT}/.env"
        echo "✅ Created .env from example (configure API keys!)"
    else
        exit 4
    fi
else
    echo "✅ .env file present"
fi

echo "─────────────────────────────────────"
echo "✅ Environment healthy"
exit 0
