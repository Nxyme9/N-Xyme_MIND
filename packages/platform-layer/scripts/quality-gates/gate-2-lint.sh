#!/usr/bin/env bash
echo "🔍 Gate 2: Lint"
if [ -f ".eslintrc.js" ] || [ -f ".eslintrc.json" ] || [ -f "eslint.config.js" ]; then
  npx eslint . --max-warnings 0 2>&1
  exit $?
elif [ -f "biome.json" ]; then
  npx biome check . 2>&1
  exit $?
else
  echo "⚠️  No linter config found — skipping"
  exit 0
fi
