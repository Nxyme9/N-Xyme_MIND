#!/usr/bin/env bash
# Result Store Checker — Python wrapper (backward compatible)
# Usage: check-results.sh "task description"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

export PYTHONPATH="$ROOT_DIR:$PYTHONPATH"
exec python3 "$ROOT_DIR/src/tools/intelligence/result_checker.py" "$@"
