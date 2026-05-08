#!/bin/bash
# N-Xyme Dictate Launcher
# Use this instead of activating venv manually

export PATH="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/.venv/bin:$PATH"
export PYTHONPATH="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"

exec python -m nx_dictate --device 1 "$@"