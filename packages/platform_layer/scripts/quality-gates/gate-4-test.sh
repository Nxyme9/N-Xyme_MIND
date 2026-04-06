#!/usr/bin/env bash
echo "🔍 Gate 4: Tests"
if [ -f "vitest.config.ts" ] || [ -f "vitest.config.js" ]; then
  npx vitest run 2>&1
  exit $?
elif [ -f "jest.config.js" ] || [ -f "jest.config.ts" ]; then
  npx jest --passWithNoTests 2>&1
  exit $?
elif [ -f "pyproject.toml" ] || [ -f "pytest.ini" ] || [ -d "tests/" ]; then
  PYTHONPATH=. pytest tests/ -v 2>&1
  exit $?
else
  echo "⚠️  No test config found — skipping"
  exit 0
fi
