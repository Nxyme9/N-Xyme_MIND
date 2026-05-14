# Sprint 4b — Ecosystem Hardening Master Plan

> **Generated**: 2026-05-12 | **Status**: Ready to Execute
> **Context**: Post-Sprint 3 integration (commit `89ba984`) | 11 ecosystem audits completed
> **Total estimated effort**: ~61h (6 phases over 3-4 weeks at relaxed pace)

---

## EXECUTIVE SUMMARY

Sprint 3 shipped ~15 new modules. Sprint 4b is a comprehensive hardening effort targeting the **40 critical gaps** discovered across 11 parallel ecosystem audits. The goal is to bring N-Xyme_MIND from its current ~28% health score (vs industry gold standard) to production-ready.

### Scope

| Category | Gaps | Priority |
|----------|------|----------|
| Security & Error Handling | 10 | 🟥 Critical + 🟧 High |
| CI/CD & Quality Gates | 8 | 🟧 High + 🟨 Medium |
| Testing Coverage | 6 | 🟧 High + 🟨 Medium |
| Observability & Monitoring | 5 | 🟨 Medium |
| Industry Pattern Adoption | 11 | 🟨 Medium + 🟩 Low |
| **Total** | **40** | **5 priority tiers** |

### 5 Fixes That Unlock Everything

These P0 items gate all other work:

| # | Fix | File(s) | Effort | Blocks |
|---|-----|---------|--------|--------|
| P0-1 | SQL injection fixes | `packages/memory_core/stores/relational_store.py` | 1h | 17 vulnerabilities |
| P0-2 | Git history purge | `git filter-branch` on `.env` | 1h | Live secrets in repo |
| P0-3 | MCP fix: orchestration | `packages/orchestration/` (KeyError chain) | 1h | orchestration MCP dead |
| P0-4 | CORS fix | `packages/http_gateway.py` | 0.5h | Production vulnerability |
| P0-5 | MCP fix: quality-gates binary | `bin/quality-gates/` | 0.5h | gate-5 not scanning |

---

## PHASE 0: Emergency Critical Fixes

**Effort**: ~4h | **Goal**: Remove the 5 items that block everything else

### Epic P0-E1: Security Emergency Fixes

#### Story P0-E1-S1: Fix SQL Injection in relational_store.py

**File**: `packages/memory_core/stores/relational_store.py`
**Problem**: 17 f-string SQL vulnerabilities — user input directly interpolated into SQL queries
**Fix**: Replace all `f"SELECT ... {var}"` with parameterized `cursor.execute("SELECT ... ?", (var,))`
**Validation**: Run `bandit -r packages/memory_core/` → 0 SQL injection findings
**Effort**: 1h

```python
# BEFORE (vulnerable)
cursor.execute(f"SELECT * FROM memories WHERE id = {memory_id}")

# AFTER (parameterized)
cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
```

#### Story P0-E1-S2: Purge Secrets from Git History

**Problem**: `.env` with live secrets committed to git history
**Fix**: `git filter-branch` or `git filter-repo` to remove `.env` from all commits
**Validation**: `git log --all --full-history -- .env` → no results
**Effort**: 1h

```bash
# Option A: git filter-branch
git filter-branch --force --tree-filter 'rm -f .env' --prune-empty --tag-name-filter cat -- --all

# Option B (preferred): git filter-repo
git filter-repo --path .env --invert-paths
```

#### Story P0-E1-S3: Fix CORS Configuration

**File**: `packages/http_gateway.py`
**Problem**: `allow_origins=["*"]` allows any origin in production
**Fix**: Use environment variable `ALLOWED_ORIGINS` (comma-separated), default to empty list
**Validation**: `grep -r 'allow_origins=\["\*"\]' packages/` → no results
**Effort**: 0.5h

#### Story P0-E1-S4: Fix Orchestration MCP Import Chain

**Problem**: `packages/orchestration/` has `KeyError: 'packages.infrastructure'` import cascade
**Fix**: Fix `__init__.py` import paths in `packages/orchestration/`
**Validation**: `python3 -c "from packages.orchestration import orchestration_mcp"` → success
**Effort**: 1h

#### Story P0-E1-S5: Create Quality-Gates Binary

**Problem**: gate-5 references `./.venv/bin/quality-gates-mcp` binary that doesn't exist
**Fix**: Either create the binary OR update gate-5 to use `bandit` or `semgrep`
**Validation**: `bash bin/quality-gates/gate-5-secrets.sh` → exit 0
**Effort**: 0.5h

---

## PHASE 1: Security & Error Handling Foundation

**Effort**: ~8h | **Goal**: Eliminate bare except, add exception hierarchy, fix hardcoded creds

### Epic P1-E1: Error Handling Overhaul

#### Story P1-E1-S1: Eliminate Bare Except Blocks

**Problem**: 81 bare `except:` blocks in 45 files — catches everything including KeyboardInterrupt
**Fix**: Replace with specific exception types. Document in each file.
**Priority files** (most critical first):
1. `packages/` — 45+ files
2. `src/` — 20+ files
3. `bin/` — 15+ files

**Validation**: `grep -r "except:" packages/ src/ bin/ | grep -v "except Exception" | grep -v "except ("` → 0 results
**Effort**: 3h

#### Story P1-E1-S2: Create Exception Hierarchy

**Problem**: No custom exception classes, everything uses `Exception` or `BaseException`
**Fix**: Create `packages/nxyme_core/exceptions.py` with:
- `NxError` (base)
- `NxConfigurationError`
- `NxMCPError`
- `NxAIAgentError`
- `NxValidationError`

**Validation**: `python3 -c "from packages.nxyme_core.exceptions import NxError"` → success
**Effort**: 2h

#### Story P1-E1-S3: Fix Hardcoded Credentials

**Files**:
- `frontend/src/app/api/auth/[...nextauth]/route.ts` — hardcoded `admin:admin` base64
- Any other hardcoded secrets, API keys, passwords

**Fix**: Replace with environment variable references
**Validation**: `grep -r "admin.*admin" frontend/` → no results
**Effort**: 1h

### Epic P1-E2: Security Hardening

#### Story P1-E2-S1: Add Input Validation Layer

**Files**: All user-facing endpoints in `packages/` and `frontend/`
**Fix**: Add sanitization for all external input (SQL injection prevention for remaining files)
**Validation**: OWASP ASVS Level 2 input validation
**Effort**: 2h

---

## PHASE 2: CI/CD Hardening & Quality Gates

**Effort**: ~10h | **Goal**: Bring all 11 quality gates to production-ready, fix CI blind spots

### Epic P2-E1: Quality Gate Completion

#### Story P2-E1-S1: Fix SAST to Scan All Python

**Problem**: gate-10 SAST only scans `src/` — misses `packages/` and `bin/`
**Fix**: Update `bin/quality-gates/gate-10-sast.sh` to scan `packages/ bin/ src/`
**Effort**: 0.5h

#### Story P2-E1-S2: Integrate Gitleaks into CI

**Problem**: gitleaks installed but NOT in CI pipeline
**Fix**: Add `gitleaks detect --source . --fail-on-leak` to CI workflow
**Effort**: 0.5h

#### Story P2-E1-S3: Add npm audit to CI

**Problem**: No `npm audit` in CI for frontend dependencies
**Fix**: Add `npm audit --audit-level=moderate` to CI
**Effort**: 0.5h

#### Story P2-E1-S4: Fix pip-audit

**Problem**: pip-audit broken (not installed or wrong invocation)
**Fix**: Install and configure pip-audit properly
**Effort**: 0.5h

#### Story P2-E1-S5: Add Build Matrix

**Problem**: No CI matrix for Python version / OS combinations
**Fix**: Add matrix for Python 3.11, 3.12 and Ubuntu 22.04, 24.04
**Effort**: 1h

#### Story P2-E1-S6: Remove Overlapping CI

**Problem**: Some checks run multiple times in CI
**Fix**: Deduplicate CI jobs, ensure each check runs once at optimal stage
**Effort**: 1h

### Epic P2-E2: Secrets & Dependency Management

#### Story P2-E2-S1: Add Dependency Scanning (Dependabot)

**Problem**: No automated dependency update PRs
**Fix**: Configure GitHub Dependabot for `package.json`, `requirements.txt`, `pyproject.toml`
**Effort**: 1h

#### Story P2-E2-S2: Generate SBOM

**Problem**: No Software Bill of Materials
**Fix**: Add `syft packages/` to CI, store SBOM as artifact
**Effort**: 1h

#### Story P2-E2-S3: Add CodeQL Security Scanning

**Problem**: No CodeQL in CI (industry standard)
**Fix**: Add CodeQL analysis as GitHub Actions step
**Effort**: 1h

#### Story P2-E2-S4: Add CSP Headers

**Problem**: No Content Security Policy headers
**Fix**: Add CSP middleware to http_gateway
**Effort**: 1h

---

## PHASE 3: Test Coverage Expansion

**Effort**: ~20h | **Goal**: Cover Sprint-3 modules with tests, fill empty test directories

> **Note**: This phase mirrors `docs/SPRINT4-PLAN.md` (tasks 4.1–4.7, 4.13)
> Total from SPRINT4-PLAN: ~27h for tests + CI/benchmarks

### Epic P3-E1: Sprint-3 Module Test Coverage

| Story | Module | Effort | Coverage Target |
|-------|--------|--------|-----------------|
| P3-E1-S1 | nx_trainer | 4h | Training pipeline, data loading, model orchestration |
| P3-E1-S2 | nx_dictate | 3h | Transcription, audio capture, text processing |
| P3-E1-S3 | nx-audio-* | 3h | Bridge, workflow, plugin integration tests |
| P3-E1-S4 | nxyme_core | 2h | Core framework unit tests |
| P3-E1-S5 | nx-mind-desktop | 3h | Desktop UI logic tests |
| P3-E1-S6 | nx_sms / nx_rotator | 2h | SMS gateway + rotation service tests |
| P3-E1-S7 | integration test suite | 3h | Update tests/integration/ for new module wiring |

### Epic P3-E2: Empty Test Directory Population

| Story | Directory | Status | Effort |
|-------|-----------|--------|--------|
| P3-E2-S1 | tests/e2e/ | Empty | 2h |
| P3-E2-S2 | tests/performance/ | Empty | 2h |
| P3-E2-S3 | tests/chaos/ | Empty | 1h |
| P3-E2-S4 | tests/frontend/ | 0 files | 2h |

### Epic P3-E3: Test CI Integration

| Story | Task | Effort |
|-------|------|--------|
| P3-E3-S1 | Run pytest in CI on all PRs | 2h |
| P3-E3-S2 | Add coverage reporting to CI | 1h |
| P3-E3-S3 | Add frontend tests to CI | 1h |
| P3-E3-S4 | Add package tests to CI | 1h |

---

## PHASE 4: Observability & Monitoring

**Effort**: ~8h | **Goal**: Wire the real but unconnected observability infrastructure

### Epic P4-E1: OpenTelemetry Wire-Up

**Problem**: `packages/orchestration/tracing.py` (563L) and `packages/orchestration/observability.py` (651L) exist but OTEL not installed
**Fix**:
1. Add `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp` to requirements
2. Initialize OTEL in MCP server startup
3. Add trace context propagation to agent delegation

**Validation**: OTEL traces visible in Jaeger/OTLP endpoint
**Effort**: 3h

### Epic P4-E2: Prometheus HTTP Server

**Problem**: `observability.py` has real Prometheus metrics but no HTTP server to expose them
**Fix**: Add `prometheus_client.start_http_server(9090)` to observability.py
**Validation**: `curl localhost:9090/metrics` → Prometheus metrics output
**Effort**: 1h

### Epic P4-E3: Log Aggregation Setup

**Problem**: Plain stdlib logging only, no structured log aggregation
**Fix**: Integrate structured logging (JSON format) with log aggregation tooling
**Effort**: 2h

### Epic P4-E4: Circuit Breaker Standardization

**Problem**: 8 custom circuit breakers + 34 retry variants — inconsistent patterns
**Fix**: Standardize on `tenacity` library for retries, create shared circuit breaker decorator
**Effort**: 2h

---

## PHASE 5: Industry Pattern Adoption

**Effort**: ~12h | **Goal**: Add the 11 missing industry patterns from 40-pattern audit

### Epic P5-E1: Missing Patterns

| Pattern | Status | Effort | Priority |
|---------|--------|--------|----------|
| Property-based testing | Missing | 1h | 🟩 Low |
| Mutation testing | Missing | 1h | 🟩 Low |
| Contract testing (Pact) | Missing | 2h | 🟩 Low |
| Commit lint | Missing | 1h | 🟩 Low |
| Branch naming conventions | Missing | 0.5h | 🟩 Low |
| PR templates | Missing | 0.5h | 🟨 Medium |
| .editorconfig | Missing | 0.5h | 🟨 Medium |
| API versioning strategy | Missing | 2h | 🟨 Medium |
| Feature flags | Missing | 3h | 🟨 Medium |
| Rate limiting | Partial | 2h | 🟧 High |
| RBAC/permission system | Missing | 2h | 🟧 High |

---

## SPRINT BREAKDOWN

| Sprint | Phase | Stories | Hours | Focus |
|--------|-------|---------|-------|-------|
| Sprint 4b.1 | Phase 0 | 5 | 4h | Emergency fixes |
| Sprint 4b.2 | Phase 1 | 4 | 8h | Security + error handling |
| Sprint 4b.3 | Phase 2 | 10 | 10h | CI/CD hardening |
| Sprint 4b.4 | Phase 3 | 11 | 20h | Test coverage |
| Sprint 4b.5 | Phase 4 | 4 | 8h | Observability |
| Sprint 4b.6 | Phase 5 | 11 | 12h | Industry patterns |
| **Total** | **6 phases** | **45 stories** | **62h** | |

---

## RISK ASSESSMENT

| Risk | Likelihood | Impact | Mitigation |
|------|-------------|--------|-----------|
| Git history purge corrupts repo | Low | High | Create backup branch before filter |
| SQL injection fix breaks queries | Medium | High | Run existing tests after each file |
| Breaking MCP startup during fix | Medium | Medium | Test each MCP individually with `python3 -c "import ..."` |
| Test coverage expansion finds bugs | High | Low | Good — bugs found early are cheap to fix |
| CI changes break existing pipeline | Medium | Medium | Run CI locally before merge |

---

## ROLLBACK PLAN

| Scenario | Rollback Action |
|----------|-----------------|
| Phase 0 fixes break MCPs | `git checkout HEAD~1 -- packages/` (revert to 89ba984) |
| Phase 1 changes introduce new errors | Revert specific files, keep SQL injection fixes |
| Phase 2 CI changes fail | Disable CI jobs temporarily, revert to working CI |
| Phase 3 test changes break tests | Skip test CI, revert test files |
| Phase 4 observability causes performance issues | Disable OTEL/Prometheus, revert to stdlib logging |

---

## SUCCESS CRITERIA

After all phases complete:

- [ ] `bandit -r packages/ src/` → 0 high/critical findings
- [ ] `git log --all --full-history -- .env` → no results (secrets purged)
- [ ] `grep -r "except:" packages/ src/` → 0 bare except blocks
- [ ] All 11 quality gates pass in CI
- [ ] `pytest --cov=packages/` → >70% coverage (currently ~10%)
- [ ] `curl localhost:9090/metrics` → Prometheus metrics output
- [ ] OTEL traces visible in tracing backend
- [ ] Health score: 28% → 75%+ (vs industry gold standard)

---

## EXECUTION ORDER

```
Phase 0 (4h) → Phase 1 (8h) → Phase 2 (10h) → Phase 3 (20h) → Phase 4 (8h) → Phase 5 (12h)
     ↓              ↓              ↓              ↓              ↓              ↓
  SQL inj +     Exception      SAST +        nx_trainer    OTEL +        PR templates
  secrets +      hierarchy +   gitleaks +    tests +       Prometheus    + RBAC +
  MCP fixes     hardcoded      npm audit     E2E empty     + circuit     feature flags
                 creds          + SBOM        dirs filled   breakers
```

### Immediate Next Step (Phase 0)

Delegate to Hephaestus:
1. Fix SQL injection in `relational_store.py` (17 locations)
2. Fix CORS in `http_gateway.py`
3. Fix orchestration MCP import chain

After Phase 0 complete → run `bmad-sprint-planning` to formalize remaining phases.

---

*Master Plan v2.0 | N-Xyme_MIND | 2026-05-12 | 40 gaps, 45 stories, 62h*
