#!/usr/bin/env fish
# N-Xyme Dictate Launcher for Fish shell

set -gx PATH "$HOME/N-Xyme_CODE/N-Xyme_MIND/.venv/bin" $PATH
set -gx PYTHONPATH "$HOME/N-Xyme_CODE/N-Xyme_MIND"

python -m nx_dictate --device 1 $argv