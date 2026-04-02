---
description: Analyze test failures from /test output and propose fixes. Reads .agent/temp/test_output.log.
created: 2026-03-23
tags: [workflow, testing, debugging, qa]
model: default
temperature: 0.3
tools:
  read: true
  write: true
  bash: true
  search: true
---

# /fix — Test Failure Analyzer & Fixer

> **Latency Profile**: MEDIUM
> **Purpose**: "Red → Green." Diagnose test failures from `/test` output and propose targeted fixes.
> **Prerequisite**: Run `/test` first. This workflow reads `.agent/temp/test_output.log`.

## Phase 1: Load Failure Context

Read the test output log and classify the failure type:

```bash
if [ ! -f ".agent/temp/test_output.log" ]; then
  echo "❌ No test output found. Run '/test' first."
  exit 1
fi

echo "📋 Test output (last 50 lines):"
tail -n 50 .agent/temp/test_output.log
```

## Phase 2: Diagnose

Analyze the failure output and classify:

1. **Syntax Error** — Missing bracket, typo, import error → auto-fixable
2. **Logic Error** — Wrong output, assertion failure → needs reasoning
3. **Environment Error** — Missing dependency, config issue → needs setup
4. **Flaky Test** — Race condition, timing → needs investigation

For each failing test:
- Identify the exact file and line number
- Read the relevant source code
- Determine root cause
- Propose a minimal fix

## Phase 3: Apply Fix

For each diagnosed failure:

1. Show the proposed diff to the user
2. Apply the fix
3. Re-run the specific failing test to verify

```bash
echo "🔄 Re-running tests to verify fix..."
$TEST_CMD > .agent/temp/test_output.log 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo "✅ All tests pass after fix."
else
  echo "⚠️ Some tests still failing. Review .agent/temp/test_output.log"
  tail -n 20 .agent/temp/test_output.log
fi
```

## Phase 4: Log

```bash
echo "$(date +%Y-%m-%d-%H:%M),fix,$EXIT_CODE" >> .context/metrics/test_log.csv
```
