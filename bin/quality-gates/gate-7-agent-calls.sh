#!/bin/bash
# Gate 7: Validate agent task() calls in code
# Prevents missing load_skills, run_in_background, invalid subagent_type

set -e

echo "🔍 Gate 7: Validating agent task() calls..."

# Find all Python files with task() calls (exclude venvs, node_modules, and validator)
FILES=$(find . -name "*.py" \
    -not -path "./venv/*" \
    -not -path "./.venv/*" \
    -not -path "./node_modules/*" \
    -not -path "./venvs/*" \
    -not -path "./packages/*/venv/*" \
    -not -path "./packages/*/.venv/*" \
    -not -path "./bin/validate-agent-call.py" \
    2>/dev/null || true)

ERRORS=0

for file in $FILES; do
    # Only check files that have actual agent task() delegation calls
    # Match task( with subagent_type= or category= (agent delegation pattern)
    # Exclude: task = ..., task(), self.task, _task, generate_task, etc.
    if grep -nE '^[[:space:]]*task\((subagent_type|category)=' "$file" > /dev/null 2>&1; then
        # Check for task() calls missing load_skills
        if grep -nE '^[[:space:]]*task\((subagent_type|category)=' "$file" | grep -v "load_skills" > /dev/null 2>&1; then
            echo "❌ $file: task() call missing load_skills parameter"
            ERRORS=$((ERRORS + 1))
        fi

        # Check for task() calls missing run_in_background
        if grep -nE '^[[:space:]]*task\((subagent_type|category)=' "$file" | grep -v "run_in_background" > /dev/null 2>&1; then
            echo "❌ $file: task() call missing run_in_background parameter"
            ERRORS=$((ERRORS + 1))
        fi
    fi
done

if [ $ERRORS -gt 0 ]; then
    echo "❌ Gate 7 FAILED: $ERRORS agent call errors found"
    exit 1
fi

echo "✅ Gate 7 PASSED: All agent task() calls valid"
exit 0
