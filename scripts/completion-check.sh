#!/usr/bin/env bash
# scripts/completion-check.sh
# Run this BEFORE ending any response

echo "============================================================"
echo "COMPLETION CHECK - The 11/10 Drive"
echo "============================================================"
echo ""

# 1. Count incomplete tasks
INCOMPLETE=$(grep -r "\- \[ \]" .sisyphus/plans/*.md 2>/dev/null | wc -l)
COMPLETED=$(grep -r "\- \[x\]" .sisyphus/plans/*.md 2>/dev/null | wc -l)
TOTAL=$((INCOMPLETE + COMPLETED))

echo "[TASK STATUS]"
echo "  Incomplete: $INCOMPLETE"
echo "  Completed:  $COMPLETED"
echo "  Total:      $TOTAL"

if [ $TOTAL -gt 0 ]; then
    PERCENT=$((COMPLETED * 100 / TOTAL))
    echo "  Progress:   $PERCENT%"
    
    # Visual bar
    BARS=$((PERCENT / 5))
    EMPTY=$((20 - BARS))
    printf "  ["
    for i in $(seq 1 $BARS); do printf "#"; done
    for i in $(seq 1 $EMPTY); do printf "."; done
    printf "] $PERCENT%%\n"
fi

echo ""

# 2. Check for syntax errors
echo "[SYNTAX CHECK]"
ERRORS=$(python -m py_compile jarvis/*.py 2>&1 | grep -i error | wc -l)
if [ $ERRORS -gt 0 ]; then
    echo "  [FAIL] $ERRORS syntax errors found"
    python -m py_compile jarvis/*.py 2>&1 | grep -i error | head -5
else
    echo "  [OK] No syntax errors"
fi

echo ""

# 3. Check imports
echo "[IMPORT CHECK]"
python -c "
import sys
sys.path.insert(0, '.')
modules = ['jarvis.config.graphiti_config', 'jarvis.engine.brain', 'jarvis.api.server']
failed = []
for m in modules:
    try:
        __import__(m)
    except Exception as e:
        failed.append((m, str(e)))
if failed:
    print(f'  [FAIL] {len(failed)} import errors:')
    for m, e in failed:
        print(f'    - {m}: {e}')
else:
    print('  [OK] All core imports work')
" 2>&1

echo ""

# 4. Git status
echo "[GIT STATUS]"
MODIFIED=$(git status --short 2>/dev/null | wc -l)
echo "  Modified files: $MODIFIED"

echo ""

# 5. VERDICT
echo "============================================================"
if [ $INCOMPLETE -eq 0 ]; then
    echo "[SUCCESS] VERDICT: ALL TASKS COMPLETE"
    echo "[NEXT] Apply 11/10 rule - how can you make it BETTER?"
else
    echo "[FAIL] VERDICT: $INCOMPLETE TASKS REMAINING"
    echo "[ACTION] KEEP WORKING - DO NOT STOP"
    echo ""
    echo "Incomplete tasks:"
    grep -r "\- \[ \]" .sisyphus/plans/*.md 2>/dev/null | head -10
    echo ""
    echo "YOU CANNOT STOP UNTIL ALL TASKS ARE COMPLETE"
    exit 1
fi
echo "============================================================"
