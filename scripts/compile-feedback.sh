#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# compile-feedback.sh — Mojo compile wrapper that captures structured feedback
#
# Usage:
#   ./scripts/compile-feedback.sh <source.mojo> [output_binary]
#
# Output: JSON with:
#   { "success": bool, "source": str, "binary": str,
#     "errors": [str], "warnings": [str],
#     "duration_ms": int, "agent": str, "task": str }
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

SOURCE="$1"
BINARY="${2:-/dev/null}"
AGENT="${3:-unknown}"
TASK="${4:-compile}"

if [ ! -f "$SOURCE" ]; then
  echo "{\"success\":false,\"source\":\"$SOURCE\",\"error\":\"file not found\",\"agent\":\"$AGENT\",\"task\":\"$TASK\",\"duration_ms\":0}"
  exit 0
fi

# Check that mojo is available
MOJO="${MOJO:-$HOME/.local/bin/mojo}"
if [ ! -x "$MOJO" ]; then
  echo "{\"success\":false,\"source\":\"$SOURCE\",\"error\":\"mojo not found at $MOJO\",\"agent\":\"$AGENT\",\"task\":\"$TASK\",\"duration_ms\":0}"
  exit 0
fi

START_MS=$(date +%s%3N)

# Capture stderr for errors/warnings
ERR_LOG=$(mktemp /tmp/compile-err-XXXXXX.log)
OUT_LOG=$(mktemp /tmp/compile-out-XXXXXX.log)
EXIT_CODE=0

if [ "$BINARY" = "/dev/null" ]; then
  # Just syntax check — only compile, don't produce binary
  "$MOJO" build "$SOURCE" -o /dev/null > "$OUT_LOG" 2> "$ERR_LOG" || EXIT_CODE=$?
else
  "$MOJO" build "$SOURCE" -o "$BINARY" > "$OUT_LOG" 2> "$ERR_LOG" || EXIT_CODE=$?
fi

END_MS=$(date +%s%3N)
DURATION_MS=$(( END_MS - START_MS ))

# Parse errors and warnings from stderr
ERRORS=()
WARNINGS=()
while IFS= read -r line; do
  if [[ "$line" == *"error:"* ]]; then
    ERRORS+=("$line")
  elif [[ "$line" == *"warning:"* ]]; then
    WARNINGS+=("$line")
  fi
done < "$ERR_LOG"

# Build JSON safely using Python for proper escaping
python3 -c "
import json, sys
result = {
    'success': $EXIT_CODE == 0,
    'source': '$SOURCE',
    'binary': '$BINARY' if '$BINARY' != '/dev/null' else '',
    'errors': $(python3 -c "import json; print(json.dumps($(printf '%s\n' "${ERRORS[@]}" | python3 -c 'import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))' 2>/dev/null || echo '[]')))"),
    'warnings': $(python3 -c "import json; print(json.dumps($(printf '%s\n' "${WARNINGS[@]}" | python3 -c 'import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))' 2>/dev/null || echo '[]')))"),
    'duration_ms': $DURATION_MS,
    'agent': '$AGENT',
    'task': '$TASK',
    'exit_code': $EXIT_CODE
}
print(json.dumps(result))
"

rm -f "$ERR_LOG" "$OUT_LOG"
exit 0
