#!/usr/bin/env bash
# Gate 5: Secret scanning — blocks commits with leaked secrets
echo "Gate 5: Secret Scan"
PATTERNS='ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36}|ghu_[a-zA-Z0-9]{36}|ghs_[a-zA-Z0-9]{36}|sk-[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16}|sk-or-v1-[a-zA-Z0-9]{32,}'
MATCHES=$(rg -n "$PATTERNS" \
  --include='*.py' --include='*.ts' --include='*.js' --include='*.json' \
  --include='*.md' --include='*.yaml' --include='*.yml' --include='*.sh' \
  --glob='!.opencode/**' --glob='!node_modules/**' --glob='!.venv/**' \
  . 2>/dev/null)
if [ -n "$MATCHES" ]; then
  echo "::error::Potential secrets found!"
  echo "$MATCHES"
  exit 1
else
  echo "[PASS] No secrets detected"
  exit 0
fi
