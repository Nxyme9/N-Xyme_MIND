#!/usr/bin/env bash
echo "🔍 Gate 3: Format"
if [ -f ".prettierrc" ] || [ -f ".prettierrc.json" ]; then
  npx prettier --check . 2>&1
  exit $?
else
  echo "⚠️  No prettier config found — skipping"
  exit 0
fi
