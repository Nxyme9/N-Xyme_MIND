#!/usr/bin/env bash
# Branch guard — blocks direct commits to main/master
BRANCH=$(git branch --show-current 2>/dev/null)
if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
  echo "ERROR: Direct commits to $BRANCH are blocked."
  echo "Create a feature branch: git checkout -b feature/your-change"
  echo "Or use: git commit --no-verify to bypass (not recommended)"
  exit 1
fi
