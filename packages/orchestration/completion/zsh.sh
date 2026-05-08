#!/bin/zsh
# Zsh completion for packages.orchestration.cli
#
# INSTALLATION:
#
# Option 1: Source manually
#   source /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/orchestration/completion/zsh.sh
#
# Option 2: Add to .zshrc for persistent loading
#   echo 'source /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/orchestration/completion/zsh.sh' >> ~/.zshrc
#
# Option 3: Install system-wide (requires sudo)
#   sudo cp /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/orchestration/completion/zsh.sh /usr/share/zsh/site-functions/
#

_cli_completion() {
    local -a opts
    opts=(
        '--task:Task description to execute'
        '--target:Optimization target\(speed\|balanced\|quality\|latency\|success\)'
        '--health:Show system health check'
        '--stats:Show routing and delegation statistics'
        '--help:Show help message'
        '--completion:Output completion script\(bash\|zsh\)'
    )

    _describe 'command' opts
}

_cli_completion_target() {
    local -a targets
    targets=(
        'speed:Optimize for speed/latency'
        'balanced:Balanced optimization'
        'quality:Optimize for quality/success'
        'latency:Same as speed'
        'success:Same as quality'
    )
    _describe 'target' targets
}

_cli_completion_completion_type() {
    local -a types
    types=(
        'bash:Bash completion script'
        'zsh:Zsh completion script'
    )
    _describe 'completion type' types
}

# Register completions
compdef _cli_completion python
compdef _cli_completion python3
compdef _cli_completion -p python
compdef _cli_completion -p python3

# Completion for --task argument (no completion - freeform text)
_cli_completion_task() {
    _message 'Task description'
}

# Completion for --target argument
_cli_completion_target_val() {
    _cli_completion_target
}

# Completion for --completion argument
_cli_completion_completion_val() {
    _cli_completion_completion_type
}

# Main completion function
_cli_completion_main() {
    local curcontext="$curcontext" state line
    typeset -A opt_args

    _arguments -C '1: :->command' '*: :->option' && return

    case "$state" in
        command)
            _cli_completion
            ;;
        option)
            case "$opt_args[1]" in
                --task)
                    _cli_completion_task
                    ;;
                --target)
                    _cli_completion_target_val
                    ;;
                --completion)
                    _cli_completion_completion_val
                    ;;
                *)
                    _cli_completion
                    ;;
            esac
            ;;
    esac
}

# Override completions for python/python3 when invoking the CLI
_cli_python_complete() {
    local -a cmd
    cmd=(${(z)BUFFER})
    
    # Check if this looks like our CLI
    if [[ "$cmd[1]" == "python" ]] || [[ "$cmd[1]" == "python3" ]]; then
        # Check for packages.orchestration.cli or -m packages.orchestration.cli
        if [[ "$BUFFER" == *"packages.orchestration.cli"* ]] || [[ "$BUFFER" == *"packages.orchestration.cli"* ]]; then
            _cli_completion_main
            return
        fi
    fi
    
    # Fall back to default completion
    _normal
}

# Register for python/python3
compdef _cli_python_complete python
compdef _cli_python_complete python3