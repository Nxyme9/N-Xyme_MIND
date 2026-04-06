#!/usr/bin/env bash
# Review Triage Override — Python wrapper (backward compatible)
# Usage: review-triage.sh "task description" [file_paths...]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

export PYTHONPATH="$ROOT_DIR:$PYTHONPATH"
exec python3 "$ROOT_DIR/src/tools/intelligence/review_triage.py" "$@"
