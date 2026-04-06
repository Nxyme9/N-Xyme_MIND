#!/usr/bin/env bash
# Gate 10: Static Application Security Testing — detects security anti-patterns
set -euo pipefail

echo "Gate 10: SAST (bandit)"

if command -v bandit &>/dev/null; then
  bandit -r src/ -f txt -ll --skip B101 2>&1
  exit $?
else
  echo "[SKIP] bandit not installed — pip install bandit"
  exit 0
fi
