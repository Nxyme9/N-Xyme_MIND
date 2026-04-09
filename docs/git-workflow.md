# Git Workflow - N-Xyme_MIND

## Branch Strategy

### Branch Types
- `master` - Production-ready code only
- `feature/*` - New features (e.g., feature/add-auth)
- `fix/*` - Bug fixes (e.g., fix/sql-injection)
- `refactor/*` - Code refactoring (e.g., refactor/self-healer)
- `sprint/*` - Sprint branches (e.g., sprint/security-audit)

### Workflow
1. Create branch from master: `git checkout -b feature/my-feature`
2. Make commits following conventional commits
3. Push and create PR: `git push -u origin feature/my-feature`
4. PR requires: CI passing, 1 review, no conflicts
5. Merge via squash or rebase

### Naming
- lowercase, hyphens only
- issue-ticket format: `feature/123-add-jwt-auth`

### Protection
- master requires PR + status checks
- Never force push to master

## Conventional Commits

This project follows [Conventional Commits](https://www.conventionalcommits.org/) specification.

### Format
```
<type>(<scope>): <description>

[optional body]
[optional footer]
```

### Types
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation only
- `style` - Formatting, no code change
- `refactor` - Code restructuring
- `perf` - Performance improvement
- `test` - Adding/updating tests
- `chore` - Maintenance, tooling
- `ci` - CI configuration

### Examples
```
feat(auth): add JWT authentication middleware
fix(memory): resolve memory leak in unified-memory MCP
docs(api): update Athena MCP documentation
refactor(routing): simplify agent delegation logic
```

### Git Hook Setup

To enable commit message validation, create `.git/hooks/commit-msg`:

```bash
#!/bin/bash
# Conventional commits validator
commit_regex='^(feat|fix|docs|style|refactor|perf|test|chore|ci)(\([[:alnum:]_-]*\))?: .+'
if ! grep -qE "$commit_regex" "$1"; then
  echo "Invalid commit message format."
  echo "Expected: <type>(<scope>): <description>"
  echo "Types: feat, fix, docs, style, refactor, perf, test, chore, ci"
  exit 1
fi
```

Make executable: `chmod +x .git/hooks/commit-msg`