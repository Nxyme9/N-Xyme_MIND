#!/usr/bin/env bash
# Delegation Logger — Python wrapper (backward compatible)
# Usage: delegation-log.sh log "task_id" "agent" "level" "status" [tokens]
#        delegation-log.sh show [count]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

export PYTHONPATH="$ROOT_DIR:$PYTHONPATH"

ACTION="${1:-show}"

if [ "$ACTION" = "log" ]; then
  shift
  exec python3 "$ROOT_DIR/src/tools/intelligence/delegation_logger.py" log "$@"
elif [ "$ACTION" = "show" ]; then
  shift
  exec python3 "$ROOT_DIR/src/tools/intelligence/delegation_logger.py" show "$@"
else
  exec python3 "$ROOT_DIR/src/tools/intelligence/delegation_logger.py" "$@"
fi
