#!/bin/bash
# Quick launcher for brain-tray - just double-click this

cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/bin

# Kill any existing
pkill -f brain-tray.py 2>/dev/null

# Clean lock
rm -f logs/brain-tray.lock

# Start with full environment
export QT_QPA_PLATFORM=xcb
export XDG_CURRENT_DESKTOP=KDE
export KDE_FULL_SESSION=true

# Run and log
python3 brain-tray.py > logs/tray-launch.log 2>&1 &

echo "Started! Check logs/tray-launch.log"