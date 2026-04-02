---
description: Canonical git shorthands (sync, commit, push)
---

# Shorthand Commands

Canonical semantics for common git operations, adapted from OpenClaw's agent conventions.

## Commands

### `sync`

Stage + commit dirty tree, then `git pull --rebase`, then `git push`.

```bash
# Full form:
python3 .agent/scripts/git_commit.py
git pull --rebase origin main
git push
```

### `commit`

Scoped commit — YOUR changed files ONLY. Never stages the entire repo.

```bash
# Use the scoped committer:
python3 .agent/scripts/committer.py "feat: add doctor CLI" src/athena/cli/doctor.py

# Safety: blocks ".", node_modules, .env, credentials
# Multi-agent safe: only stages specified files
```

### `commit all`

Stage everything, but in **grouped logical chunks** (one commit per component).

```bash
# Group by component — do NOT mix unrelated changes:
python3 .agent/scripts/committer.py "feat(cli): add doctor subcommand" src/athena/cli/doctor.py src/athena/__main__.py
python3 .agent/scripts/committer.py "feat(scripts): add scoped committer" .agent/scripts/committer.py
```

### `push`

Always `git pull --rebase` FIRST, then push. Never push blind.

```bash
git pull --rebase origin main
git push
```

## Multi-Agent Safety (Protocol 413)

When multiple agents are active in the workspace:

1. **Never** use `git stash` — stashes are global, another agent might pop yours
2. **Never** use `git checkout <branch>` without coordination
3. **Prefer** worktrees for parallel work: `git worktree add ../feature-branch feature-branch`
4. **Always** use the scoped committer to avoid staging other agents' files
