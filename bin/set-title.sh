#!/usr/bin/env bash
# set-title.sh - Set terminal title to show current task
# ADHD-friendly: Visible progress breadcrumbs in title bar

# Usage: source this script, then call set_title "your task"
# Example: source bin/set-title.sh && set_title "Fixing auth bug"

function set_title {
    local title="$1"
    local icon="🧠"
    printf "\033]0;$icon N-Xyme: %s\007" "$title"
}

function clear_title {
    printf "\033]0;N-Xyme_MIND\007"
}

# Auto-set on prompt (optional - uncomment to enable)
# function prompt_hook {
#     local last_cmd=$(history 2>/dev/null | tail -1 | sed 's/^[0-9 ]*//')
#     if [[ -n "$last_cmd" ]]; then
#         set_title "$last_cmd"
#     fi
# }

# Export for use in scripts
export -f set_title 2>/dev/null || true
export -f clear_title 2>/dev/null || true

echo "✅ Title tracking enabled. Use: set_title 'Your task'"
echo "   To clear: clear_title"