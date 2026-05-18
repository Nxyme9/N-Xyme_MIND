#!/bin/bash
# =============================================================================
# kill_notifications.sh — One-shot kill ALL notification sources
# =============================================================================
# Part of the N-Xyme MIND Notification Crisis permanent fix.
# Canonical kill chain — apply in this order.
# See: data/memory/holographic-memory.json (mem_1779068874)
# =============================================================================

set -e

echo "=== N-Xyme MIND — Killing All Notification Sources ==="

# Step 1: Stop & disable systemd services
echo "[1/5] Stopping systemd services..."
systemctl --user stop --now nx-dictate.service 2>/dev/null && echo "  ✓ nx-dictate.service stopped" || echo "  - nx-dictate.service not running"
systemctl --user disable nx-dictate.service 2>/dev/null && echo "  ✓ nx-dictate.service disabled" || echo "  - nx-dictate.service already disabled"

# Step 2: Stop & disable auto-starting timers
echo "[2/5] Disabling auto-starting timers..."
systemctl --user disable --now nx-heartbeat.timer 2>/dev/null && echo "  ✓ nx-heartbeat.timer disabled" || echo "  - nx-heartbeat.timer not found"
systemctl --user disable --now nx-guardian.timer 2>/dev/null && echo "  ✓ nx-guardian.timer disabled" || echo "  - nx-guardian.timer not found"
systemctl --user disable --now nx-meta-monitor.timer 2>/dev/null && echo "  ✓ nx-meta-monitor.timer disabled" || echo "  - nx-meta-monitor.timer not found"

# Step 3: Kill Ralph loop persistence
echo "[3/5] Removing Ralph loop state..."
RALPH_STATE="data/ralph-state/active.md"
if [ -f "$RALPH_STATE" ]; then
  rm -f "$RALPH_STATE"
  echo "  ✓ Ralph loop state cleared"
else
  echo "  - No Ralph loop state found"
fi

# Step 4: Kill dictation feedback scripts
echo "[4/5] Killing dictation feedback processes..."
pkill -f feedback.py 2>/dev/null && echo "  ✓ feedback.py killed" || echo "  - No feedback.py running"
pkill -f nx_dictate 2>/dev/null && echo "  ✓ nx_dictate killed" || echo "  - No nx_dictate running"

# Step 5: Verify
echo "[5/5] Verification..."
echo ""
echo "=== Remaining active user services ==="
systemctl --user list-units --type=service --state=running --no-legend 2>/dev/null | awk '{print "  " $1}'
echo ""
echo "=== Remaining active timers ==="
systemctl --user list-timers --no-legend 2>/dev/null | awk '{print "  " $NF}'
echo ""
echo "✓ All notification sources killed."
echo "  If toasts persist, restart opencode to clear plugin event streams."
