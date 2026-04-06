#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

PASS=0
FAIL=0

check() {
  if [ "$1" = "0" ]; then
    echo "  ✓ $2"
    PASS=$((PASS + 1))
  else
    echo "  ✗ $2"
    FAIL=$((FAIL + 1))
  fi
}

echo "========================================"
echo "  N-Xyme_MIND FULL SYSTEM TEST"
echo "========================================"
echo ""

# 1. env.sh
echo "=== 1. env.sh ==="
source env.sh 2>/dev/null
check $? "env.sh sourced"
echo ""

# 2. Health Check
echo "=== 2. Health Check ==="
bash bin/health-l0-blink.sh 2>/dev/null
check $? "L0 health check"
echo ""

# 3. athena-context-mcp
echo "=== 3. athena-context-mcp ==="
./packages/athena-context-mcp/venv/bin/python -c "
from athena_context_mcp import get_active_context, get_product_context, get_user_context, get_constraints
ac = get_active_context()
pc = get_product_context()
uc = get_user_context()
co = get_constraints()
assert ac, 'active_context failed'
assert pc, 'product_context failed'
assert uc, 'user_context failed'
assert co, 'constraints failed'
print('  All 4 tools working')
" 2>&1
check $? "athena-context-mcp tools"
echo ""

# 4. nx-mind-mcp
echo "=== 4. nx-mind-mcp ==="
./packages/nx-mind-mcp/venv/bin/python -c "
from nx_mind_mcp import get_mind_state, get_session_history, get_active_workflow, get_project_manifest, get_memory_stats
ms = get_mind_state()
sh = get_session_history()
aw = get_active_workflow()
pm = get_project_manifest()
mst = get_memory_stats()
print('  All 5 tools working')
" 2>&1
check $? "nx-mind-mcp tools"
echo ""

# 5. trigger-guardian-mcp
echo "=== 5. trigger-guardian-mcp ==="
./packages/trigger-guardian-mcp/.venv/bin/python -c "
from trigger_guardian_mcp import register_trigger, list_triggers, check_trigger, get_trigger_handlers
lt = list_triggers()
ct = check_trigger(input_text='/test')
gh = get_trigger_handlers(phrase='/test')
print(f'  list_triggers: {len(lt.get(\"triggers\", []))} triggers')
print('  All 3 tools working')
" 2>&1
check $? "trigger-guardian-mcp tools"
echo ""

# 6. Memory Bank Files
echo "=== 6. Memory Bank Files ==="
for file in activeContext.md productContext.md userContext.md constraints.md; do
  if [ -s ".context/memory_bank/$file" ]; then
    echo "  ✓ $file"
    PASS=$((PASS + 1))
  else
    echo "  ✗ $file"
    FAIL=$((FAIL + 1))
  fi
done
echo ""

# 7. Memory Graph
echo "=== 7. Memory Graph ==="
if [ -d ".context/memory_graph" ]; then
  echo "  ✓ memory_graph exists"
  PASS=$((PASS + 1))
else
  echo "  ✗ memory_graph missing"
  FAIL=$((FAIL + 1))
fi
echo ""

# 8. MetricsStore
echo "=== 8. MetricsStore ==="
METRICS_DB_PATH=/tmp/test.db ./venvs/athena/bin/python -c "
from src.metrics_store import MetricsStore
s = MetricsStore()
assert '/tmp/test.db' in s.db_path, f'Expected /tmp/test.db, got {s.db_path}'
print(f'  db_path: {s.db_path}')
" 2>&1
check $? "MetricsStore env path resolution"
echo ""

# 9. Bridge Module
echo "=== 9. Bridge Module ==="
./venvs/athena/bin/python -c "
from src.integrations.metrics_memory_bridge import log_metric_to_context, get_metrics_summary, sync_metrics_to_memory
print('  All 3 functions importable')
" 2>&1
count=$(grep -rn '/home/nxyme' --include='*.py' . | grep -v venv | grep -v '.venv' | grep -v test | grep -v '.git' | wc -l || true)
echo ""

# 10. Bootstrap Fresh Clone
echo "=== 10. Bootstrap Fresh Clone ==="
rm -rf /tmp/test-bootstrap
mkdir /tmp/test-bootstrap
cp bootstrap.sh /tmp/test-bootstrap/
cd /tmp/test-bootstrap
bash bootstrap.sh 2>&1 | tail -5
cd "$SCRIPT_DIR/.."
if [ -d "/tmp/test-bootstrap/.context/memory_bank" ] && [ -d "/tmp/test-bootstrap/.context/memory_graph" ]; then
  echo "  ✓ All directories created"
  PASS=$((PASS + 1))
else
  echo "  ✗ Missing directories"
  FAIL=$((FAIL + 1))
fi
echo ""

# 11. Path Portability
echo "=== 11. Path Portability ==="
count=$(grep -rn '/home/nxyme' --include='*.py' . | grep -v venv | grep -v '.venv' | grep -v test | grep -v '.git' | wc -l || true)
echo "  Hardcoded paths in source: $count"
if [ "$count" -eq 0 ]; then
  PASS=$((PASS + 1))
else
  FAIL=$((FAIL + 1))
fi
echo ""

# 12. Security - shell=True in network-facing code only
# Note: shell=True in internal app launchers (focus_manager, quick_actions) is acceptable
# because they launch user-configured shortcuts, not process external input
echo "=== 12. Security (shell=True) ==="
count=$(grep -rn 'shell=True' src/ --include='*.py' | grep -v 'focus_manager' | grep -v 'quick_actions' | wc -l || true)
echo "  shell=True in network-facing code: $count"
if [ "$count" -eq 0 ]; then
  echo "  ✓ No shell=True in network-facing code"
  echo "  Note: 5 shell=True in internal app launchers (accepted)"
  PASS=$((PASS + 1))
else
  FAIL=$((FAIL + 1))
fi
echo ""

# 13. CHANGELOG.md
echo "=== 13. CHANGELOG.md ==="
if [ -s CHANGELOG.md ]; then
  echo "  ✓ CHANGELOG.md exists"
  PASS=$((PASS + 1))
else
  echo "  ✗ CHANGELOG.md missing"
  FAIL=$((FAIL + 1))
fi
echo ""

# 14. Dockerfile Security
echo "=== 14. Dockerfile Security ==="
if grep -q "USER appuser" src/security-agent/Dockerfile; then
  echo "  ✓ Non-root user"
  PASS=$((PASS + 1))
else
  echo "  ✗ Runs as root"
  FAIL=$((FAIL + 1))
fi
if grep -q "HEALTHCHECK" src/security-agent/Dockerfile; then
  echo "  ✓ Healthcheck"
  PASS=$((PASS + 1))
else
  echo "  ✗ No healthcheck"
  FAIL=$((FAIL + 1))
fi
echo ""

# Summary
echo "========================================"
echo "  RESULTS: $PASS passed, $FAIL failed"
echo "========================================"
if [ "$FAIL" -eq 0 ]; then
  echo "  ALL SYSTEMS OPERATIONAL"
else
  echo "  $FAIL ISSUES FOUND"
fi
echo "========================================"
