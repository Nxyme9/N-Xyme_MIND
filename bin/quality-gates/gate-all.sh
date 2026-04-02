#!/usr/bin/env bash
set -euo pipefail
echo "Running all quality gates..."

./bin/quality-gates/gate-1-typecheck.sh || exit 1
./bin/quality-gates/gate-1-py-typecheck.sh || exit 1
./bin/quality-gates/gate-2-lint.sh || exit 1
./bin/quality-gates/gate-2-py-lint.sh || exit 1
./bin/quality-gates/gate-3-format.sh || exit 1
./bin/quality-gates/gate-4-test.sh || exit 1
./bin/quality-gates/gate-5-secrets.sh || exit 1
./bin/quality-gates/gate-6-placeholders.sh  # warning only

echo "All gates passed!"
exit 0
