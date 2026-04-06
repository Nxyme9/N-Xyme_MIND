#!/usr/bin/env bash
# Gate 9: Dependency Vulnerability Scan — blocks commits with vulnerable dependencies
set -euo pipefail

echo "Gate 9: Dependency Vulnerability Scan (pip-audit)"

if command -v pip-audit &>/dev/null; then
  pip-audit -r pyproject.toml --format=columns 2>&1
  exit $?
else
  echo "[SKIP] pip-audit not installed — pip install pip-audit"
  exit 0
fi
