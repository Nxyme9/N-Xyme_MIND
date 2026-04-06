# Coverage Regression Runbook

## Symptoms
- CI coverage job fails
- Gate 11 (coverage trend) reports regression > 5%
- Coverage dropped below threshold (40%)

## Diagnosis Steps

### 1. Check current coverage
```bash
PYTHONPATH=. pytest tests/ --cov=src --cov-report=term-missing
```

### 2. Identify which modules lost coverage
```bash
PYTHONPATH=. pytest tests/ --cov=src --cov-report=term-missing | grep -E "^[a-z]" | sort
```

### 3. Check recent changes
```bash
git diff HEAD~5 --stat src/
git log --oneline -10
```

### 4. Compare with history
```bash
cat .coverage-history
```

## Resolution

### If regression is from legitimate refactoring:
1. Document the reason in PR description
2. Update `.coverage-history` with new baseline
3. Add tests for any uncovered new code

### If regression is from deleted tests:
```bash
git diff HEAD~5 -- tests/
# Restore accidentally deleted tests
git checkout HEAD~5 -- tests/
```

### If regression is from new untested code:
1. Identify uncovered files:
   ```bash
   PYTHONPATH=. pytest tests/ --cov=src --cov-report=html
   # Open htmlcov/index.html
   ```
2. Write tests for critical paths
3. Re-run coverage check

### If threshold is too aggressive:
1. Temporarily lower threshold in CI:
   ```yaml
   # .github/workflows/quality-gate.yml
   --cov-fail-under=35  # temporary
   ```
2. Create ticket to raise it back

## Prevention
- Write tests alongside new code (TDD)
- Run coverage locally before pushing
- Monitor coverage trends weekly
- Set up coverage alerts in CI
