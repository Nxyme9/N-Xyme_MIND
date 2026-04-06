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
./bin/quality-gates/gate-7-agent-calls.sh || exit 1

./bin/quality-gates/gate-8-security-paths.sh || exit 1
./bin/quality-gates/gate-9-deps.sh || exit 1
./bin/quality-gates/gate-10-sast.sh || exit 1
./bin/quality-gates/gate-11-coverage-trend.sh || exit 1

echo "All gates passed!"
exit 0
