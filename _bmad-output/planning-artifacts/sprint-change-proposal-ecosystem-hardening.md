# Sprint Change Proposal: Sprint 4b — Ecosystem Hardening

> **Generated**: 2026-05-12 | **Scope**: Major | **Change Trigger**: Post-Sprint 3 integration audit

---

## SECTION 1: ISSUE SUMMARY

**Problem Statement**: Sprint 3 shipped ~15 new modules, but 11 parallel ecosystem audits revealed **40 critical gaps** across security, testing, CI/CD, observability, and industry patterns. The N-Xyme_MIND health score is ~28% vs industry gold standard.

**Triggering Evidence**:
- 17 SQL injection vulnerabilities in `relational_store.py`
- Live secrets in git history (`.env`)
- 81 bare `except:` blocks catching everything
- CORS `allow_origins=["*"]` in production gateway
- 8 dead MCPs (orchestration, quality-gates, nx-context, etc.)
- Zero frontend tests in CI, empty E2E/perf/chaos test directories
- 53 benchmark scripts with ZERO CI integration
- gitleaks installed but NOT used in CI
- Real OpenTelemetry code (563L tracing + 651L observability) but NOT installed as deps
- 26 of 40 industry patterns missing

**Context**: This is a **major course correction** — the existing `docs/SPRINT4-PLAN.md` (84L, 40.5h) only covers test coverage. It does not address security, CI/CD, observability, or industry patterns. A comprehensive multi-phase plan is needed.

---

## SECTION 2: IMPACT ANALYSIS

### Epic Impact

| Epic | Status | Changes Needed |
|------|--------|---------------|
| Sprint 4 (test coverage) | In progress | Expand from 15 tasks to 26 (add security + CI stories) |
| Sprint 3 (integration) | Complete | No changes — this change builds on Sprint 3 |
| Future sprints | Not started | Must wait for Phase 0–5 completion |

### Artifact Impact

| Artifact | Current State | Changes Needed |
|----------|---------------|---------------|
| `docs/SPRINT4-PLAN.md` | 84L, 15 tasks, ~40.5h | Superseded by `.sisyphus/plans/sprint-4b-ecosystem-hardening-master-plan.md` |
| `opencode.json` | MCP config (15 MCPs, most dead) | Phase 0 MCP fixes |
| `bin/quality-gates/` | 11 gates, 3 broken | Phase 2 CI hardening |
| `tests/` | ~40 test files, 3 empty dirs | Phase 3 test expansion |
| `.sisyphus/` | 4 audit docs, no unified plan | New master plan document |

### Technical Impact

- **Breaking**: Phase 0 SQL injection fix changes query execution in `relational_store.py`
- **Breaking**: Phase 0 MCP fixes may change import behavior
- **Non-breaking**: Phase 1–5 are additive improvements

---

## SECTION 3: RECOMMENDED APPROACH

**Selected**: Direct Adjustment (Option 1) with phased execution

**Rationale**:
- No rollback needed — no completed sprint work is being undone
- MVP is not affected — this is hardening, not feature change
- Scope is large but well-understood — 40 gaps across 6 phases
- Each phase is independent enough to execute in sequence
- Risk is manageable with rollback plan per phase

**Effort Estimate**: ~62h total across 6 phases (~3-4 weeks at relaxed pace)

**Risk Assessment**: Medium — largest risk is Phase 0 SQL injection fix (could break queries) and git history purge (could corrupt repo). Both have rollback plans.

---

## SECTION 4: DETAILED CHANGE PROPOSALS

### Change: Replace Sprint 4 Plan with Comprehensive Master Plan

**Scope**: `docs/SPRINT4-PLAN.md` → `.sisyphus/plans/sprint-4b-ecosystem-hardening-master-plan.md`

| Aspect | Old Plan | New Plan |
|--------|----------|----------|
| Tasks | 15 | 45 |
| Phases | 1 | 6 |
| Scope | Tests only | Tests + Security + CI + Observability + Patterns |
| Estimate | 40.5h | 62h |
| Priority | Tests | Security (SQL inj, secrets, CORS) first |

### Change: Add 5 Emergency Phase 0 Fixes

**New Phase 0 (4h)** — blocks all other phases:
1. SQL injection fix (`relational_store.py` × 17)
2. Git history purge (`.env` secrets)
3. MCP: orchestration fix (import chain)
4. MCP: quality-gates binary
5. CORS fix (`http_gateway.py`)

### Change: Add Phase 1 Security + Error Handling (8h)

**New Phase 1**:
- Eliminate 81 bare except blocks
- Create exception hierarchy (`NxError` base class)
- Fix hardcoded credentials (NextAuth admin)
- Add input validation layer

### Change: Add Phase 2 CI/CD Hardening (10h)

**New Phase 2**:
- Fix SAST to scan `packages/` + `bin/` (currently only `src/`)
- Integrate gitleaks into CI
- Add npm audit to CI
- Add Dependabot
- Add SBOM generation
- Add CodeQL
- Add CSP headers
- Add build matrix

### Change: Add Phase 4 Observability (8h)

**New Phase 4** (Phase 3 = tests):
- Install OpenTelemetry deps, wire tracing + observability
- Add Prometheus HTTP server
- Add log aggregation
- Standardize circuit breakers + retries

### Change: Add Phase 5 Industry Patterns (12h)

**New Phase 5**:
- Add PR templates, .editorconfig
- Add property/mutation/contract testing
- Add API versioning, feature flags, RBAC
- Add rate limiting

---

## SECTION 5: IMPLEMENTATION HANDOFF

**Scope Classification**: Major — requires PM + Architect coordination

### Handoff Plan

| Phase | Executor | Handoff |
|-------|----------|---------|
| Phase 0 | Hephaestus (delegate) | SQL inj + CORS + MCP fixes |
| Phase 1 | Hephaestus + Oracle review | Error handling + credentials |
| Phase 2 | Hephaestus | CI fixes + quality gates |
| Phase 3 | Hephaestus | Test coverage (from existing SPRINT4-PLAN) |
| Phase 4 | Hephaestus + Oracle review | OTEL + Prometheus |
| Phase 5 | Hephaestus | Industry patterns |

### Success Criteria

- [ ] 17 SQL injections → 0
- [ ] `.env` secrets → purged from history
- [ ] 81 bare except → 0
- [ ] 11 quality gates → all pass
- [ ] Health score → 28% → 75%+
- [ ] OTEL traces → visible in backend
- [ ] Prometheus metrics → `/metrics` endpoint

### Next Steps

1. **Approve** this proposal
2. **Delegate** Phase 0 to Hephaestus immediately
3. **Run** `bmad-sprint-planning` to formalize sprint plans
4. **Execute** phase by phase, oldest phase first

---

*Change Proposal | Sprint 4b | 2026-05-12 | Major scope | PM + Architect handoff*
