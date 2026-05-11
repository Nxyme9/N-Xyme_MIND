---
epic_id: E-101
title: "Security Hardening"
priority: P0
stories: 3
points: 5
created: 2026-05-11
sprint: sprint-3
status: pending
bmad_agents:
  lead: Amelia (dev)
  pm: John (sprint management)
  architect: Winston (architecture review)
---

# Epic E-101: Security Hardening

**Priority:** P0 (CRITICAL) | **Stories:** 3 | **Points:** 5 | **Risk:** LOW

## Epic Goal

Harden N-Xyme MIND's security posture by addressing critical and high-priority findings from the full-stack audit.

## Rationale

- Security findings scored 72/100 (B-) after adversarial corrections
- The CRITICAL Notion token exposure must be verified and rotated if found
- The HIGH gitleaks regex issue creates false negatives, weakening the secret-scanning pipeline
- The MEDIUM CVE scanning gap leaves dependencies unmonitored

## Success Criteria

1. Notion token verified — zero matches on `grep -r "ntn_561668" .`
2. Gitleaks regex tightened — no false positives on `$PATH`/`$HOME`/`$USER`
3. CVE scanning integrated into CI — pipeline fails on known CVEs

---

## Story S-101: Verify Notion Token Exposure

**Story ID:** S-101 | **Points:** 1 | **Priority:** CRITICAL | **TDD:** Verification Only

### What
Verify whether the Notion token (`ntn_561668...`) referenced in the audit exists in `opencode.json` at line 306. Rotate if present.

### File
`/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/opencode.json` (line ~306)

### Acceptance Criteria
- AC-101.1: `grep -r "ntn_561668" .` returns zero matches
- AC-101.2: If token found, rotation completes and old token is revoked
- AC-101.3: Notion MCP server connects successfully with new token

### QA Command
```bash
grep -r "ntn_561668" . --exclude-dir=.git
grep -rn "ntn_" . --exclude-dir=.git | grep -v ".git" | grep -v "test" | grep -v "docs"
```

### Atomic Commit
```
security: verify Notion token exposure and rotate if found
```

---

## Story S-102: Fix Gitleaks Regex Over-Broad Allowlist

**Story ID:** S-102 | **Points:** 2 | **Priority:** HIGH | **TDD:** Test-First

### What
Replace overly broad gitleaks allowlist regex `'''\$[a-zA-Z_]+\$'''` with `'''\$[a-zA-Z_][a-zA-Z0-9_]{0,30}\$'''`.

### File
`/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/.gitleaks.toml`

### Root Cause
Current regex matches shell variables like `$PATH`, `$HOME`, `$USER`, creating false negatives that allow real secrets to slip through.

### Acceptance Criteria
- AC-102.1: Regex no longer matches `$PATH`, `$HOME`, `$USER`
- AC-102.2: `gitleaks detect --verbose` on test file with shell vars shows no false positives
- AC-102.3: Real secrets still caught by gitleaks' built-in rules
- AC-102.4: No new false positives introduced on full codebase scan

### QA Commands
```bash
# Should NOT flag shell variables
echo 'export PATH=$PATH:/usr/local/bin' | gitleaks detect --verbose --stdin

# Should flag real secrets
echo 'api_key="sk-1234567890abcdef"' | gitleaks detect --verbose --stdin

# Full codebase scan
gitleaks detect --verbose --source . --report-format json
```

### Atomic Commit
```
security: tighten gitleaks regex for shell variables
```

---

## Story S-103: Add Dependency CVE Scanning to CI

**Story ID:** S-103 | **Points:** 2 | **Priority:** MEDIUM | **TDD:** Test-First | **Depends:** S-102

### What
Add `pip-audit` or `safety check` to `.github/workflows/` quality gates. CI must FAIL when known CVEs are detected.

### Files
- `.github/workflows/ci.yml` (or create if missing)
- `docs/CI-QUALITY-GATES.md` (document the scan)

### Acceptance Criteria
- AC-103.1: CI pipeline includes `pip-audit` step
- AC-103.2: Step passes when no CVEs in dependencies
- AC-103.3: Step FAILS when test CVE is introduced (verify gate works)
- AC-103.4: Clear CVE report output in CI logs showing package + CVE ID
- AC-103.5: Scan completes within 60 seconds

### QA Commands
```bash
# Manual CVE scan (should pass on clean deps)
pip-audit

# Test failure on known CVE
pip install "package-with-cve==vulnerable.version"
pip-audit  # Should return non-zero exit code
```

### Implementation Notes
- Use `pip-audit` (preferred over `safety` for JSON output and SPDX support)
- Use `pip-audit --format=json --exit-code` for CI integration
- Clean up test CVE before committing

### Atomic Commit
```
security: add pip-audit CVE scanning to CI quality gates
```

---

## Quality Gates (All Stories)

| Gate | Command | Must Pass |
|------|---------|-----------|
| Typecheck | `mypy src/` | Zero errors |
| Lint | `ruff check src/` | Zero errors |
| Format | `ruff format --check src/` | Zero diffs |
| Tests | `pytest tests/ -v` | All pass |
| Secrets | `gitleaks detect --verbose` | Zero leaks |
| Pre-commit | `pre-commit run --all-files` | All hooks pass |

---

## Timeline

| Day | Activity |
|-----|----------|
| Day 1 | S-101: Verify Notion Token (CRITICAL, 1pt) |
| Day 1-2 | S-102: Fix Gitleaks Regex (HIGH, 2pts) |
| Day 2-3 | S-103: Add CVE Scanning to CI (MEDIUM, 2pts) |

**Critical Path:** S-101 → S-102 → S-103

---

## Definition of Done

All of the following must be true for this epic to be DONE:

1. `grep -r "ntn_561668" .` returns **zero matches**
2. `gitleaks detect --verbose` catches real secrets but **no false positives** on `$PATH`/`$HOME`/`$USER`
3. `pip-audit` integrated into CI and **fails on intentionally introduced test CVE**
4. All 3 atomic commits are merged with passing CI
5. Security audit score improves from **72/100 to 85+/100**