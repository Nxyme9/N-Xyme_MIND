#!/usr/bin/env bash
# Delegation Benchmark — Python wrapper (backward compatible)
# Usage: benchmark-delegation.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

export PYTHONPATH="$ROOT_DIR:$PYTHONPATH"
exec python3 "$ROOT_DIR/src/tools/intelligence/benchmark.py" "$@"
