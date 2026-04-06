# Branch Protection Rules

Configure these required status checks in **GitHub Settings → Branches → Add rule**:

## Branch: `main`

### Required status checks (all must pass):
- `typecheck` — Python type checking (pyright)
- `lint` — Python linting (ruff)
- `format` — Code formatting check
- `test` — Test suite execution (pytest)
- `coverage` — Coverage threshold (min 40%)
- `secrets` — Secret scanning (gate-5)
- `placeholders` — Placeholder detection (gate-6)
- `pyright` — Strict type checking
- `dependencies` — Dependency vulnerability scan (pip-audit)
- `sast` — Static application security testing (bandit)
- `coverage-trend` — Coverage regression check (max 5% drop)

### Additional settings:
- [x] Require branches to be up to date before merging
- [x] Require pull request reviews before merging (min 1)
- [x] Dismiss stale pull request approvals when new commits are pushed
- [x] Require review from Code Owners
- [x] Include administrators
- [x] Restrict who can push to matching branches

### Allowed merge methods:
- [x] Squash merge
- [ ] Rebase and merge
- [ ] Merge commit
