#!/usr/bin/env bash
# Gate 6: Placeholder detection — warns on TODO/FIXME/placeholder values
echo "Gate 6: Placeholder Scan"
MATCHES=$(rg -n 'example\.com|CHANGEME|your-.*-here|xxx|placeholder|REPLACE_ME' \
  --include='*.py' --include='*.ts' --include='*.js' \
  --glob='!node_modules/**' --glob='!.opencode/**' --glob='!.venv/**' \
  --glob='!athena/.venv/**' \
  src/ athena/src/ jarvis-new/src/ 2>/dev/null)
if [ -n "$MATCHES" ]; then
  echo "::error::Placeholder values found — commit blocked"
  echo "$MATCHES"
  exit 1  # Block commit
else
  echo "[PASS] No placeholders detected"
  exit 0
fi
