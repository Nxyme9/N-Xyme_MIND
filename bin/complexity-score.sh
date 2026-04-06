#!/usr/bin/env bash
# Complexity Scorer — Python wrapper (backward compatible)
# Usage: complexity-score.sh "task description"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

exec python3 "$ROOT_DIR/src/tools/intelligence/complexity_scorer.py" "$@"
