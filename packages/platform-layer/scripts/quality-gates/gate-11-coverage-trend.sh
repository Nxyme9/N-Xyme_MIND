#!/usr/bin/env bash
# Gate 11: Coverage Trend Check — blocks coverage regressions > 5%
set -euo pipefail

echo "Gate 11: Coverage Trend Check"

COVERAGE_FILE=".coverage-history"

# Run coverage and extract percentage
OUTPUT=$(PYTHONPATH=. pytest tests/ --cov=src --cov-report=term-missing 2>&1)
CURRENT=$(echo "$OUTPUT" | grep "^TOTAL" | awk '{print $NF}' | tr -d '%')

if [ -z "$CURRENT" ]; then
  echo "[WARN] Could not determine coverage — skipping trend check"
  exit 0
fi

PREVIOUS=$(cat "$COVERAGE_FILE" 2>/dev/null || echo "0")

echo "Current: ${CURRENT}%, Previous: ${PREVIOUS}%"

if command -v bc &>/dev/null; then
  if [ "$(echo "$CURRENT < $PREVIOUS" | bc)" -eq 1 ]; then
    REGRESSION=$(echo "$PREVIOUS - $CURRENT" | bc)
    if [ "$(echo "$REGRESSION > 5" | bc)" -eq 1 ]; then
      echo "::error::Coverage regression of ${REGRESSION}% detected"
      exit 1
    fi
    echo "[WARN] Coverage dropped by ${REGRESSION}% (threshold: 5%)"
  fi
else
  # Fallback: integer comparison
  CURRENT_INT=${CURRENT%.*}
  PREVIOUS_INT=${PREVIOUS%.*}
  if [ "$CURRENT_INT" -lt "$PREVIOUS_INT" ]; then
    REGRESSION=$((PREVIOUS_INT - CURRENT_INT))
    if [ "$REGRESSION" -gt 5 ]; then
      echo "::error::Coverage regression of ${REGRESSION}% detected"
      exit 1
    fi
    echo "[WARN] Coverage dropped by ${REGRESSION}% (threshold: 5%)"
  fi
fi

echo "$CURRENT" > "$COVERAGE_FILE"
echo "[PASS] Coverage trend OK"
