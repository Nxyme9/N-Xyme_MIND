#!/usr/bin/env bash
# Mutation Testing — verifies test effectiveness
set -euo pipefail

echo "Mutation Testing (mutmut)"

if command -v mutmut &>/dev/null; then
  echo "Running mutation tests on src/model_router/..."
  mutmut run --paths-to-mutate src/model_router/ 2>&1
  echo ""
  echo "Mutation test results:"
  mutmut results 2>&1
else
  echo "[SKIP] mutmut not installed — pip install mutmut"
  exit 0
fi
