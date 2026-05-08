#!/usr/bin/env bash
# Gate 8: Security-Sensitive Path Detection — Python wrapper (backward compatible)
# Usage: gate-8-security-paths.sh "task description"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

export PYTHONPATH="$ROOT_DIR:$PYTHONPATH"
exec python3 "$ROOT_DIR/src/intelligence/security_gate.py" "$@"
