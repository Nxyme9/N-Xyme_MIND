#!/usr/bin/env bash
# momentum-detector.sh - Detect and protect flow state
# ADHD-friendly: Protects hyperfocus states from interruptions

set -e

WORKDIR="${WORKDIR:-/home/nxyme/N-Xyme_CODE/N-Xyme_MIND}"
LOG_FILE="$WORKDIR/.sisyphus/session-log.jsonl"

# Config
TOOL_CALL_WINDOW=20          # Consider last N tool calls
FAILURE_THRESHOLD=0.3        # Low failure rate = in flow
RAPID_CALL_THRESHOLD=10      # Tool calls per minute = rapid
INTERRUPT_COOLDOWN=300       # 5 min between warnings

function get_recent_tool_calls() {
    # Get recent tool calls from session log
    if [ -f "$LOG_FILE" ]; then
        tail -n "$TOOL_CALL_WINDOW" "$LOG_FILE" 2>/dev/null | grep -c '"tool"' || echo "0"
    else
        echo "0"
    fi
}

function get_failure_rate() {
    # Calculate failure rate from recent calls
    if [ -f "$LOG_FILE" ]; then
        total=$(tail -n "$TOOL_CALL_WINDOW" "$LOG_FILE" 2>/dev/null | grep -c '"tool"' || echo "1")
        failures=$(tail -n "$TOOL_CALL_WINDOW" "$LOG_FILE" 2>/dev/null | grep -c '"error"' || echo "0")
        if [ "$total" -eq 0 ]; then
            echo "0"
        else
            # Return as percentage
            echo $((failures * 100 / total))
        fi
    else
        echo "0"
    fi
}

function detect_momentum() {
    # Check if user is in "flow state"
    local tool_calls=$(get_recent_tool_calls)
    local failure_rate=$(get_failure_rate)
    
    # Simple heuristics
    if [ "$tool_calls" -ge "$RAPID_CALL_THRESHOLD" ] && [ "$failure_rate" -lt "$((FAILURE_THRESHOLD * 100))" ]; then
        echo "flow"
    elif [ "$failure_rate" -gt 50 ]; then
        echo "struggling"
    else
        echo "normal"
    fi
}

function main() {
    local mode="${1:-check}"
    
    case "$mode" in
        check)
            local state=$(detect_momentum)
            case "$state" in
                flow)
                    echo "🔥 FLOW STATE DETECTED - Minimizing interruptions"
                    echo "   You're in the zone! Keep going."
                    # Could set env var to reduce interrupts
                    export NXYME_FLOW_MODE=1
                    ;;
                struggling)
                    echo "🧠 Taking a break might help"
                    echo "   You've hit some blockers. Consider:"
                    echo "   - Running: bash bin/error-translator.py"
                    echo "   - Consulting Oracle: task with subagent_type=oracle"
                    ;;
                *)
                    echo "✅ Normal workflow"
                    ;;
            esac
            ;;
        watch)
            echo "Watching for flow state... (Ctrl+C to exit)"
            while true; do
                local state=$(detect_momentum)
                if [ "$state" = "flow" ]; then
                    echo "🔥 You're in FLOW! Keep going!"
                fi
                sleep 60
            done
            ;;
        *)
            echo "Usage: $0 [check|watch]"
            ;;
    esac
}

main "$@"
