# Sprint 4 — Integration Hardening & Test Coverage

> **Generated**: 2026-05-12 | **Status**: Ready to Execute
> **Context**: Post-Sprint 3 integration (commit `89ba984`)

---

## Sprint 4 Overview

Sprint 3 shipped ~15 new modules (nx_trainer, nx_dictate, nx-audio, nx-mind-desktop, nxyme_core, nx_sms, etc.). Sprint 4 focuses on **hardening**: covering these new modules with tests, fixing bugs discovered during real use, and closing integration gaps the old plan didn't address.

---

## Old Sprint 4 Plan — Audit

| Task | Status | Action |
|------|--------|--------|
| CATALYST Integration | ✅ Done (docs + workflows + MCP tools) | Close |
| VPN Rotator Automation | ✅ Done (bin/vpn-rotate + rotator.py) | Close |
| Trigger Engine Automation | ❌ Not done (src/trigger_engine.py missing) | Re-prioritize to Low |
| BMAD Workflow Integration | ✅ Mostly done (workflows exist, orchestration active) | Close |
| Integration Tests | ⚠️ Partially done (5 old test files, pre-Sprint-3) | Fold into new plan |

---

## Refreshed Sprint 4 Priorities

### HIGH PRIORITY — Test Coverage

Rationale: 40+ packages, only 2 have test directories. New Sprint-3 modules have zero tests.

| # | Task | Effort | Details |
|---|------|--------|---------|
| 4.1 | **nx_trainer tests** | 4h | Test training pipeline, data loading, model orchestration |
| 4.2 | **nx_dictate tests** | 3h | Test transcription, audio capture, text processing |
| 4.3 | **nx-audio-* tests** | 3h | Bridge, workflow, plugin integration tests |
| 4.4 | **nxyme_core tests** | 2h | Core framework unit tests |
| 4.5 | **nx-mind-desktop tests** | 3h | Desktop UI logic tests |
| 4.6 | **nx_sms / nx_rotator tests** | 2h | SMS gateway + rotation service tests |
| 4.7 | **Refresh integration test suite** | 3h | Update tests/integration/ to cover new module wiring |

**Total: ~20h**

### MEDIUM PRIORITY — Bug Bash & Hardening

| # | Task | Effort | Details |
|---|------|--------|---------|
| 4.8 | **Bug bash on Sprint 3 modules** | 4h | Run each new module, log and fix issues |
| 4.9 | **MCP tool surfaces audit** | 3h | Verify all new modules expose correct MCP tools |
| 4.10 | **Session persistence check** | 2h | Verify session state survives across restarts for new modules |
| 4.11 | **Documentation for new modules** | 4h | README per module, update docs/ index |
| 4.12 | **update activeContext.md** | 0.5h | Refresh stale context file with current module inventory |

**Total: ~13.5h**

### LOW PRIORITY — CI & Benchmarks

| # | Task | Effort | Details |
|---|------|--------|---------|
| 4.13 | **CI pipeline for test execution** | 3h | GitHub Actions or local CI for test runners |
| 4.14 | **Benchmark suite expansion** | 2h | Add benchmarks for new module performance |
| 4.15 | **Trigger engine revival** | 2h | Wire triggers.json to health scripts if still needed |

**Total: ~7h**

---

## Execution Order

| Order | Task | Hours | Dependency |
|-------|------|-------|------------|
| 1 | 4.12 Update activeContext.md | 0.5 | None |
| 2 | 4.1–4.7 Test coverage (parallel per module) | 20 | None |
| 3 | 4.8 Bug bash | 4 | 4.1–4.7 (fix bugs found during testing) |
| 4 | 4.9 MCP surface audit | 3 | 4.8 |
| 5 | 4.10 Session persistence | 2 | 4.8 |
| 6 | 4.11 Docs | 4 | 4.8 (docs reflect fixed state) |
| 7 | 4.13–4.15 CI/Benchmarks/Trigger | 7 | Everything above |

**Estimated Total**: ~40.5h (relaxed pace, ~2 weeks)

---

*Sprint 4 Plan v2.0 | N-Xyme_MIND | 2026-05-12*
