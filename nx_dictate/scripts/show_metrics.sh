#!/bin/bash
# Print dictation metrics summary

echo "=== N-Xyme Dictation Metrics ==="
echo ""

if systemctl --user is-active nxyme-dictate.service >/dev/null 2>&1; then
    echo "Service: RUNNING"
    
    LOG_FILE=$(mktemp)
    journalctl --user -u nxyme-dictate.service --since "1 hour ago" --no-pager > "$LOG_FILE"
    
    TRANSCRIPTIONS=$(grep -c "Transcribed:" "$LOG_FILE" 2>/dev/null || echo "0")
    ERRORS=$(grep -c "error\|Error\|ERROR" "$LOG_FILE" 2>/dev/null || echo "0")
    RESTARTS=$(grep -c "Started nxyme-dictate" "$LOG_FILE" 2>/dev/null || echo "0")
    
    echo "Transcriptiones (last hour): $TRANSCRIPTIONS"
    echo "Errors: $ERRORS"
    echo "Restarts: $RESTARTS"
    
    rm -f "$LOG_FILE"
else
    echo "Service: STOPPED"
fi

echo ""
echo "=== Test Suite ==="
cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
PYTHONPATH=. python3 -m pytest nx-dictate/tests/ -v --tb=no -q 2>&1 | tail -3