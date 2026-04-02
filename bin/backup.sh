#!/usr/bin/env bash
# bin/backup.sh — Automated workspace backup
# Commits and pushes all changes to protect against data loss

set -e
WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$WORKSPACE"

echo "Backup: $(date -Iseconds)"

# Check for changes
CHANGES=$(git status --porcelain 2>/dev/null | wc -l)
if [ "$CHANGES" -eq 0 ]; then
  echo "[OK] No changes to backup"
  exit 0
fi

echo "[INFO] Found $CHANGES changed files"

# Stage all tracked + untracked (respecting .gitignore)
git add -A

# Create backup commit
TIMESTAMP=$(date -Iseconds)
git commit -m "auto-backup: $TIMESTAMP" --no-verify || echo "[WARN] Nothing to commit"

# Push if remote exists
if git remote get-url origin &>/dev/null; then
  BRANCH=$(git branch --show-current 2>/dev/null || echo "master")
  timeout 30 git push origin "$BRANCH" 2>/dev/null || echo "[WARN] Push failed — will retry next backup"
fi

echo "[OK] Backup complete: $CHANGES files committed"
