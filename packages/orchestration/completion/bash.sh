#!/bin/bash
# Bash completion for packages.orchestration.cli
# 
# INSTALLATION:
# 
# Option 1: Source manually
#   source /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/orchestration/completion/bash.sh
#
# Option 2: Add to .bashrc for persistent loading
#   echo 'source /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/orchestration/completion/bash.sh' >> ~/.bashrc
#
# Option 3: Install system-wide (requires sudo)
#   sudo cp /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/orchestration/completion/bash.sh /etc/bash_completion.d/
#

_cli_completion() {
    local cur prev words cword
    _init_completion || return

    # Main options
    if [[ "$cword" -eq 1 ]]; then
        COMPREPLY=($(compgen -W "--task --target --health --stats --help --completion" -- "$cur"))
        return
    fi

    # Previous option
    prev="${words[cword-1]}"

    case "$prev" in
        --task)
            # No completion for task arguments (free-form text)
            return
            ;;
        --target)
            COMPREPLY=($(compgen -W "speed balanced quality latency success" -- "$cur"))
            return
            ;;
        --completion)
            COMPREPLY=($(compgen -W "bash zsh" -- "$cur"))
            return
            ;;
    esac

    # Handle option=value format
    if [[ "$cur" == --*=* ]]; then
        local opt="${cur%%=*}"
        case "$opt" in
            --target)
                COMPREPLY=($(compgen -W "speed balanced quality latency success" -P "${cur%%=*}=" -- "${cur#*=}"))
                return
                ;;
            --completion)
                COMPREPLY=($(compgen -W "bash zsh" -P "${cur%%=*}=" -- "${cur#*=}"))
                return
                ;;
        esac
    fi
}

complete -F _cli_completion python
complete -F _cli_completion python3
complete -F _cli_completion -o nospace python
complete -F _cli_completion -o nospace python3