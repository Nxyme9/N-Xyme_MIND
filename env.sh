#!/usr/bin/env bash
# Source this file: source ./env.sh
export NX_MIND_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Python venv
export VIRTUAL_ENV="$NX_MIND_ROOT/venvs/athena"
export PATH="$VIRTUAL_ENV/bin:$PATH"
export PYTHONPATH="$NX_MIND_ROOT/athena/src:$NX_MIND_ROOT/src"

# Ollama
export OLLAMA_MODELS="$NX_MIND_ROOT/.ollama/models"

# npm cache (local)
export npm_config_cache="$NX_MIND_ROOT/.cache/npm"

# Load API keys
[ -f "$NX_MIND_ROOT/.env" ] && set -a && source "$NX_MIND_ROOT/.env" && set +a
