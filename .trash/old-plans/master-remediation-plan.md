# N-Xyme MIND — Master Remediation Plan (v2)

> **Generated**: 2026-04-06
> **Audit Score**: B- (81.5%) → **Target**: A (95%+)
> **Scope**: ALL 14 issues from full system audit — 7 dimensions
> **Philosophy**: Pragmatic for personal workspace. No enterprise bloat. No feature removal.
> **Timeline**: 4 waves, ~4 weeks

---

## Wave 0 — Foundation Cleanup (Day 1, ~2 hours)

**Goal**: Zero-risk cleanup. Dead code, typos, stale artifacts.

### 0.1 Remove stale `mcp/` directory
- **Action**: `rm -rf mcp/` (empty, 0 entries)
- **Risk**: None
- **Verify**: `ls mcp/` → "No such file or directory"

### 0.2 Fix `.env.example` typo
- **File**: `.env.example` line 17
- **Action**: `CEREBRAS_API_KEY=cYOUR_API_KEY_HERE` → `CEREBRAS_API_KEY=YOUR_API_KEY_HERE`
- **Risk**: None
- **Verify**: `grep CEREBRAS .env.example`

### 0.3 Fix dead code in `gate-all.sh`
- **File**: `bin/quality-gates/gate-all.sh` lines 15-19
- **Action**: Remove unreachable duplicate `echo`/`exit` after first `exit 0`
- **Risk**: None
- **Verify**: `bash -n bin/quality-gates/gate-all.sh`

### 0.4 Fix `gate-4-test.sh` — only checks JS frameworks, skips Python
- **File**: `bin/quality-gates/gate-4-test.sh`
- **Current**: Only checks vitest/jest, exits 0 for Python projects
- **Action**: Add pytest fallback before the final `else`:
  ```bash
  elif [ -f "pyproject.toml" ] || [ -f "pytest.ini" ] || [ -d "tests/" ]; then
    PYTHONPATH=. pytest tests/ -v 2>&1
    exit $?
  ```
- **Risk**: Low (may reveal failing tests)
- **Verify**: `bash bin/quality-gates/gate-4-test.sh`

**Success Criteria**:
- [ ] `mcp/` directory removed
- [ ] `.env.example` typo fixed
- [ ] `gate-all.sh` dead code removed
- [ ] `gate-4-test.sh` runs pytest
- [ ] All quality gates still pass

---

## Wave 1 — Security Hardening (Day 1-2, ~4 hours)

**Goal**: Close ALL security gaps. Add dependency scanning, SAST, rate limiting.

### 1.1 Add `pip-audit` dependency vulnerability scanning
- **New file**: `bin/quality-gates/gate-9-deps.sh`
- **CI change**: `.github/workflows/quality-gate.yml` — add `dependencies` job
- **Action**:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  echo "Gate 9: Dependency Vulnerability Scan (pip-audit)"
  if command -v pip-audit &>/dev/null; then
    pip-audit -r pyproject.toml --format=columns 2>&1
  else
    echo "[SKIP] pip-audit not installed — pip install pip-audit"
    exit 0
  fi
  ```
- **Risk**: Low (read-only scan)
- **Verify**: `bash bin/quality-gates/gate-9-deps.sh`

### 1.2 Add `bandit` SAST (Static Application Security Testing)
- **New file**: `bin/quality-gates/gate-10-sast.sh`
- **CI change**: `.github/workflows/quality-gate.yml` — add `sast` job
- **Action**:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  echo "Gate 10: SAST (bandit)"
  if command -v bandit &>/dev/null; then
    bandit -r src/ -f txt -ll --skip B101 2>&1
  else
    echo "[SKIP] bandit not installed — pip install bandit"
    exit 0
  fi
  ```
- **Risk**: Low (read-only analysis)
- **Verify**: `bash bin/quality-gates/gate-10-sast.sh`

### 1.3 Add rate limiting to model router
- **File**: `bin/model-router.py` (or the HTTP server that runs on :8080)
- **Action**: Add token-bucket rate limiter on `/route` endpoint
  - Check if `src/rate_limiter.py` already exists — reuse it
  - If not, add simple middleware: 100 req/min per IP
  - Make configurable: `MODEL_ROUTER_RATE_LIMIT=100`
- **Risk**: Medium (could break high-throughput usage)
- **Mitigation**: Configurable via env var, default high (100/min)
- **Verify**: Rapid-fire 101 requests → 429 on 101st

### 1.4 Update `gate-all.sh` to include new gates
- **File**: `bin/quality-gates/gate-all.sh`
- **Action**: Add before final `echo "All gates passed!"`:
  ```bash
  ./bin/quality-gates/gate-8-security-paths.sh || exit 1
  ./bin/quality-gates/gate-9-deps.sh || exit 1
  ./bin/quality-gates/gate-10-sast.sh || exit 1
  ```
- **Risk**: None
- **Verify**: `bash bin/quality-gates/gate-all.sh`

### 1.5 Update CI `summary` job dependencies
- **File**: `.github/workflows/quality-gate.yml` line 119
- **Action**: Update `needs:` to include `dependencies`, `sast`
- **Risk**: None
- **Verify**: CI runs all jobs

**Success Criteria**:
- [ ] `gate-9-deps.sh` created and passes
- [ ] `gate-10-sast.sh` created and passes
- [ ] CI workflow includes `dependencies` and `sast` jobs
- [ ] Model router rate limiter active
- [ ] `gate-all.sh` includes gates 8, 9, 10

---

## Wave 2 — Testing Overhaul (Day 2-5, ~12 hours)

**Goal**: Raise coverage 14% → 40% (sprint) → 60% (target). Add E2E + perf tests.

### 2.1 Raise coverage threshold: 14% → 40%
- **File**: `.github/workflows/quality-gate.yml` (coverage job)
- **Action**: Change `--cov-fail-under=14` to `--cov-fail-under=40`
- **Risk**: Medium (CI will fail if coverage < 40%)
- **Mitigation**: Run `pytest --cov=src` locally first to check current baseline
- **Verify**: CI coverage job passes

### 2.2 Add E2E tests for core routing flows
- **New file**: `tests/e2e/test_routing_e2e.py`
- **Test cases**:
  1. Simple task → routes to correct agent
  2. Complex task → triggers multi-agent chain
  3. Security-sensitive path → forces Oracle review
  4. Fallback chain → degrades gracefully when primary fails
  5. Rate limit → returns 429 after threshold
- **Risk**: Low (new tests only)
- **Verify**: `pytest tests/e2e/ -v`

### 2.3 Add performance regression tests
- **New file**: `tests/perf/test_benchmarks.py`
- **Action**: Load `benchmark-results.json`, assert no regression > 20%
  ```python
  def test_model_routing_no_regression():
      baseline_ms = 0.6945
      current_ms = measure_model_routing()
      assert current_ms < baseline_ms * 1.2
  ```
- **Risk**: Low
- **Verify**: `pytest tests/perf/ -v`

### 2.4 Write unit tests for uncovered critical modules
- **Priority modules** (highest impact, lowest coverage):
  1. `src/model_router/` — routing logic
  2. `src/security/` — security gates
  3. `src/health_monitor.py` — auto-recovery
  4. `src/circuit_breaker.py` — failure handling
  5. `src/memory_router.py` — memory operations
- **Action**: Write unit tests for each module's public API
- **Risk**: Low
- **Verify**: `pytest tests/unit/ -v --cov=src --cov-report=term-missing`

### 2.5 Fix test gate to actually run Python tests
- **Already done in Wave 0.4**
- **Verify**: `bash bin/quality-gates/gate-4-test.sh` runs pytest

**Success Criteria**:
- [ ] Coverage threshold raised to 40% (CI passing)
- [ ] E2E test suite exists with 5+ routing flow tests
- [ ] Performance regression tests exist
- [ ] Critical modules have unit test coverage
- [ ] `pytest tests/ -v` passes with 0 failures

---

## Wave 3 — Code Quality (Day 3-4, ~6 hours)

**Goal**: Make Pyright blocking. Enforce type hints. Clean quality gates.

### 3.1 Fix Pyright gate — remove `|| true`
- **File**: `.github/workflows/quality-gate.yml` line 115
- **Current**: `uv run pyright src/ --outputjson || true`
- **Action**: Remove `|| true`, make it blocking
- **Risk**: HIGH (will fail CI if type errors exist)
- **Mitigation**:
  1. Run `pyright src/` locally first
  2. Fix all type errors BEFORE removing `|| true`
  3. If too many errors, add `pyrightconfig.json` with gradual strictness

### 3.2 Add `pyrightconfig.json` for gradual type enforcement
- **New file**: `pyrightconfig.json`
- **Action**:
  ```json
  {
    "include": ["src/"],
    "typeCheckingMode": "basic",
    "reportMissingTypeStubs": false,
    "reportUnknownParameterType": "warning",
    "reportUnknownVariableType": "warning",
    "reportUnknownMemberType": "warning"
  }
  ```
- **Risk**: Low (warnings only initially)
- **Verify**: `pyright src/` shows warnings, not errors

### 3.3 Add type hints to uncovered critical modules
- **Modules**: Same as Wave 2.4 priority list
- **Action**: Add type hints to all public functions/classes
- **Risk**: Low (additive only)
- **Verify**: `pyright src/model_router/` → 0 errors

### 3.4 Update `gate-all.sh` to include all gates
- **Already done in Wave 1.4**

**Success Criteria**:
- [ ] Pyright gate blocking (no `|| true`)
- [ ] `pyrightconfig.json` exists with gradual strictness
- [ ] Critical modules have type hints
- [ ] `bash bin/quality-gates/gate-all.sh` passes

---

## Wave 4 — CI/CD Hardening (Day 4-5, ~4 hours)

**Goal**: Add dependency caching, branch protection, release automation.

### 4.1 Add Python dependency caching to CI
- **File**: `.github/workflows/quality-gate.yml`
- **Action**: Add uv package cache (not just binary):
  ```yaml
  - name: Cache uv packages
    uses: actions/cache@v4
    with:
      path: ~/.cache/uv
      key: uv-packages-${{ runner.os }}-${{ hashFiles('**/pyproject.toml') }}
      restore-keys: |
        uv-packages-${{ runner.os }}-
  ```
- **Risk**: None
- **Verify**: Second CI run is faster

### 4.2 Create branch protection documentation
- **New file**: `.github/BRANCH-PROTECTION.md`
- **Action**: Document required status checks for GitHub Settings → Branches:
  - typecheck, lint, format, test, coverage, secrets, placeholders, pyright, dependencies, sast
- **Risk**: None (documentation only)
- **Verify**: Manual setup in GitHub

### 4.3 Add release automation workflow
- **New file**: `.github/workflows/release.yml`
- **Action**: On tag push → create GitHub release with changelog
  ```yaml
  name: Release
  on:
    push:
      tags: ['v*']
  jobs:
    release:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - name: Create Release
          uses: softprops/action-gh-release@v1
          with:
            body_path: CHANGELOG.md
  ```
- **Risk**: Low
- **Verify**: Push tag → release created

### 4.4 Add `gate-11-coverage-trend.sh`
- **New file**: `bin/quality-gates/gate-11-coverage-trend.sh`
- **Action**: Track coverage trend, fail if regression > 5%
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  echo "Gate 11: Coverage Trend Check"
  CURRENT=$(PYTHONPATH=. pytest tests/ --cov=src --cov-report=term-missing 2>&1 | grep TOTAL | awk '{print $NF}' | tr -d '%')
  PREVIOUS=$(cat .coverage-history 2>/dev/null || echo "0")
  echo "Current: ${CURRENT}%, Previous: ${PREVIOUS}%"
  if [ "$(echo "$CURRENT < $PREVIOUS" | bc)" -eq 1 ]; then
    REGRESSION=$(echo "$PREVIOUS - $CURRENT" | bc)
    if [ "$(echo "$REGRESSION > 5" | bc)" -eq 1 ]; then
      echo "::error::Coverage regression of ${REGRESSION}% detected"
      exit 1
    fi
  fi
  echo "$CURRENT" > .coverage-history
  echo "[PASS] Coverage trend OK"
  ```
- **Risk**: Medium (may fail on legitimate refactors)
- **Mitigation**: Warning-only for first month

**Success Criteria**:
- [ ] CI dependency caching active
- [ ] Branch protection documented
- [ ] Release workflow exists
- [ ] Coverage trend gate exists
- [ ] CI pipeline runs all 11 gates

---

## Wave 5 — Architecture Modularization (Day 5-10, ~20 hours)

**Goal**: Split monolithic `src/` (194 files) into logical modules. HIGHEST RISK.

### 5.1 Define module boundaries
- **Proposed structure**:
  ```
  src/
  ├── orchestration/        # Agent coordination, routing, delegation
  ├── memory/               # Memory management, embeddings, graph
  ├── security/             # Security gates, encryption, secrets
  ├── health/               # Health checks, monitoring, recovery
  ├── audio/                # Audio processing (separate domain)
  ├── video/                # Video processing
  ├── ui/                   # UI, TUI, themes, dashboards
  ├── infrastructure/       # Config, logging, caching, networking
  └── tools/                # MCP tools, utilities, middleware
  ```
- **Risk**: HIGH (breaking changes if imports aren't updated)
- **Mitigation**:
  1. Create new module directories alongside existing files
  2. Move files one module at a time
  3. Update ALL imports after each move
  4. Run full test suite after each module move
  5. Keep `src/__init__.py` with re-exports for backward compatibility

### 5.2 Migration strategy (per module)
For each module:
1. Create directory: `mkdir -p src/orchestration`
2. Add `__init__.py` with re-exports
3. Move files: `mv src/model_router src/orchestration/`
4. Update imports: `grep -rl "from src.model_router" src/ | xargs sed -i 's/from src.model_router/from src.orchestration.model_router/g'`
5. Run tests: `pytest tests/ -v`
6. If tests pass → commit. If fail → revert and fix.

### 5.3 Update all quality gates for new structure
- **Files**: All `bin/quality-gates/gate-*.sh`
- **Action**: Update paths from `src/` to new module paths
- **Risk**: Medium
- **Verify**: `bash bin/quality-gates/gate-all.sh` passes

### 5.4 Update CI/CD for new structure
- **Files**: `.github/workflows/*.yml`
- **Action**: Update paths in typecheck, lint, coverage jobs
- **Risk**: Low
- **Verify**: CI passes

### 5.5 Update `opencode.json` and `AGENTS.md`
- **Files**: `opencode.json`, `AGENTS.md`
- **Action**: Update any hardcoded paths to new module structure
- **Risk**: Low
- **Verify**: OpenCode agents can still find and use code

**Success Criteria**:
- [ ] `src/` reorganized into 8+ logical modules
- [ ] All imports updated and working
- [ ] All tests pass (100% of pre-migration tests)
- [ ] All quality gates pass
- [ ] CI/CD pipeline passes
- [ ] OpenCode agents still functional

---

## Wave 6 — Operations Excellence (Day 8-12, ~8 hours)

**Goal**: Add alerting, runbooks, benchmark memory tracking, mutation testing, API docs.

### 6.1 Implement memory tracking in benchmarks
- **File**: `bin/benchmark-models.py`
- **Action**: Add `tracemalloc` to measure memory delta
  ```python
  import tracemalloc
  tracemalloc.start()
  # ... run benchmark ...
  current, peak = tracemalloc.get_traced_memory()
  tracemalloc.stop()
  result["memory"] = {"current_bytes": current, "peak_bytes": peak}
  ```
- **Risk**: Low
- **Verify**: `python3 bin/benchmark-models.py` shows memory stats (not 0 bytes)

### 6.2 Add alerting integration
- **File**: `src/notification_service.py` (enhance existing)
- **Action**: Add webhook-based alerting (Slack/Discord generic webhook)
  - Configurable via `.env`: `ALERT_WEBHOOK_URL=`, `ALERT_CHANNEL=slack`
  - Trigger on: critical health failures, security gate failures, coverage regressions
- **Risk**: Low (opt-in via env var)
- **Verify**: Set webhook URL → trigger alert → received

### 6.3 Create runbooks
- **New directory**: `docs/runbooks/`
- **Runbooks**:
  1. `agent-routing-failure.md`
  2. `mcp-server-down.md`
  3. `secret-leak-response.md`
  4. `coverage-regression.md`
  5. `model-router-outage.md`
- **Risk**: None
- **Verify**: `ls docs/runbooks/` shows 5 files

### 6.4 Add mutation testing
- **New file**: `bin/mutation-test.sh`
- **Action**: Use `mutmut` for Python mutation testing
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  echo "Mutation Testing"
  if command -v mutmut &>/dev/null; then
    mutmut run --paths-to-mutate src/model_router/
    mutmut results
  else
    echo "[SKIP] mutmut not installed"
    exit 0
  fi
  ```
- **Risk**: Low
- **Verify**: `bash bin/mutation-test.sh`

### 6.5 Document MCP API contracts
- **New directory**: `docs/api/`
- **Files**:
  - `docs/api/athena-mcp.md`
  - `docs/api/unified-memory-mcp.md`
  - `docs/api/trigger-guardian-mcp.md`
  - `docs/api/nx-mind-mcp.md`
- **Risk**: None
- **Verify**: `ls docs/api/` shows 4+ files

**Success Criteria**:
- [ ] Benchmarks show memory stats (not 0 bytes)
- [ ] Alerting webhook configurable and functional
- [ ] 5 runbooks created in `docs/runbooks/`
- [ ] Mutation testing script exists
- [ ] MCP API contracts documented

---

## Dependency Graph

```
Wave 0 (Foundation) ──────────────────────────────────────────┐
    ↓                                                          │
Wave 1 (Security) ────→ Wave 3 (Code Quality)                 │
    ↓                        ↓                                 │
Wave 2 (Testing) ────→ Wave 4 (CI/CD)                         │
    ↓                        ↓                                 │
Wave 5 (Architecture) ──→ Wave 6 (Operations) ←───────────────┘
```

**Parallelizable**:
- Wave 0 + Wave 1 can run in parallel (independent)
- Wave 2 + Wave 3 can run in parallel (independent)
- Wave 6 can start as soon as Wave 5 module boundaries are defined

**Sequential dependencies**:
- Wave 5 MUST wait for Wave 2 (tests must pass before restructuring)
- Wave 4 MUST wait for Wave 1 (new gates must exist before CI uses them)
- Wave 6 SHOULD wait for Wave 5 (runbooks reference final module structure)

---

## Timeline

| Week | Waves | Effort | Milestone |
|------|-------|--------|-----------|
| **Week 1** | 0, 1, 2 (partial) | ~18 hours | Security hardened, tests running |
| **Week 2** | 2 (complete), 3 | ~18 hours | Coverage at 40%, Pyright blocking |
| **Week 3** | 4, 5 (partial) | ~24 hours | CI/CD hardened, modules started |
| **Week 4** | 5 (complete), 6 | ~28 hours | Architecture clean, ops excellent |

**Total Estimated Effort**: ~88 hours (~11 working days)
**Target Completion**: 4 weeks from start

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Wave 5 breaks imports | HIGH | HIGH | Move one module at a time, test after each |
| Pyright reveals 100+ type errors | MEDIUM | MEDIUM | Use `pyrightconfig.json` gradual strictness |
| Coverage threshold causes CI failures | MEDIUM | LOW | Two-step approach (14% → 40% → 60%) |
| Model router rate limiter breaks usage | LOW | MEDIUM | Configurable via env var, start high |
| Benchmark memory tracking adds overhead | LOW | LOW | Only enabled during benchmark runs |

---

## Final Success Criteria (ALL must be met)

- [ ] **Security**: 11/11 quality gates passing (including deps + SAST + coverage trend)
- [ ] **Testing**: Coverage ≥ 40% (target 60%), E2E tests exist, perf tests exist
- [ ] **Code Quality**: Pyright blocking, type hints on critical modules
- [ ] **CI/CD**: 11 gates running, dependency caching active, release workflow exists
- [ ] **Architecture**: `src/` modularized into 8+ logical directories
- [ ] **Performance**: Benchmarks show memory stats, no regression > 20%
- [ ] **Operations**: Alerting configured, 5 runbooks, MCP APIs documented
- [ ] **Overall Score**: A (95%+)

---

## File Change Summary

| File | Wave | Change |
|------|------|--------|
| `mcp/` | 0 | DELETE directory |
| `.env.example` | 0 | EDIT typo |
| `bin/quality-gates/gate-all.sh` | 0, 1, 3 | EDIT dead code + new gates |
| `bin/quality-gates/gate-4-test.sh` | 0 | EDIT add pytest |
| `bin/quality-gates/gate-9-deps.sh` | 1 | CREATE |
| `bin/quality-gates/gate-10-sast.sh` | 1 | CREATE |
| `bin/quality-gates/gate-11-coverage-trend.sh` | 4 | CREATE |
| `bin/model-router.py` | 1 | EDIT rate limiting |
| `.github/workflows/quality-gate.yml` | 1, 2, 3, 4 | EDIT new jobs + caching |
| `.github/workflows/release.yml` | 4 | CREATE |
| `.github/BRANCH-PROTECTION.md` | 4 | CREATE |
| `tests/e2e/test_routing_e2e.py` | 2 | CREATE |
| `tests/perf/test_benchmarks.py` | 2 | CREATE |
| `tests/unit/test_*.py` | 2 | CREATE 5+ files |
| `pyrightconfig.json` | 3 | CREATE |
| `src/orchestration/` | 5 | CREATE + move files |
| `src/memory/` | 5 | CREATE + move files |
| `src/security/` | 5 | CREATE + move files |
| `src/health/` | 5 | CREATE + move files |
| `src/audio/` | 5 | CREATE + move files |
| `src/video/` | 5 | CREATE + move files |
| `src/ui/` | 5 | CREATE + move files |
| `src/infrastructure/` | 5 | CREATE + move files |
| `src/tools/` | 5 | CREATE + move files |
| `bin/benchmark-models.py` | 6 | EDIT memory tracking |
| `src/notification_service.py` | 6 | CREATE/EDIT |
| `docs/runbooks/*.md` | 6 | CREATE 5 files |
| `bin/mutation-test.sh` | 6 | CREATE |
| `docs/api/*.md` | 6 | CREATE 4+ files |

**Total**: ~35 files created/modified, 1 directory deleted

---

## Immediate Next Steps (Start Wave 0 Now)

1. [ ] Remove `mcp/` directory
2. [ ] Fix `.env.example` typo
3. [ ] Fix `gate-all.sh` dead code
4. [ ] Fix `gate-4-test.sh` to run pytest
5. [ ] Run `bash bin/quality-gates/gate-all.sh` to verify all gates pass
