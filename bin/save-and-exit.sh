#!/usr/bin/env bash
# save-and-exit.sh - Save session state and exit cleanly
# ADHD-friendly: Quick checkpoint without thinking

set -e

WORKDIR="${WORKDIR:-/home/nxyme/N-Xyme_CODE/N-Xyme_MIND}"
SESSION_STATE="$WORKDIR/.sisyphus/session-state.json"
CONTEXT_FILE="$WORKDIR/N-Xyme.md"
LOG_FILE="$WORKDIR/.sisyphus/session-log.jsonl"

# Get current timestamp
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

echo "💾 Saving session state..."

# 1. Save session state if it exists
if [ -f "$SESSION_STATE" ]; then
    # Add checkpoint entry to log
    echo "{\"timestamp\": \"$TIMESTAMP\", \"action\": \"checkpoint\", \"status\": \"saved\"}" >> "$LOG_FILE" 2>/dev/null || true
fi

# 2. Save current git status as a quick snapshot
cd "$WORKDIR"
git status --short > /tmp/nxyme-git-status-$(date +%s).txt 2>/dev/null || true

# 3. Update N-Xyme.md with current focus if it exists
if [ -f "$CONTEXT_FILE" ]; then
    # Create a quick save marker
    echo ""
    echo "--- Checkpoint: $TIMESTAMP ---" >> "$CONTEXT_FILE"
fi

# 4. Kill any hanging background processes cleanly
pkill -f "python3.*8766" 2>/dev/null || true

echo "✅ Session saved at $TIMESTAMP"
echo ""
echo "📝 To resume next time:"
echo "   1. Run: bash n-xyme-mind.sh"
echo "   2. Read N-Xyme.md for context"
echo "   3. Continue from where you left off"
echo ""
echo "Ready to exit. Press Enter to close..."
read -r

exit 0