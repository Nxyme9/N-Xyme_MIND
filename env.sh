#!/usr/bin/env bash
# Bash environment setup — source with: source ./env.sh

# Get script directory
_NX_MIND_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Core paths ──
export NX_MIND_ROOT="$_NX_MIND_SCRIPT_DIR"
export VIRTUAL_ENV="$NX_MIND_ROOT/venvs/athena"
export PATH="$VIRTUAL_ENV/bin:$PATH"
export PYTHONPATH="$NX_MIND_ROOT/athena/src:$NX_MIND_ROOT/src"

# ── Ollama ──
export OLLAMA_MODELS="$NX_MIND_ROOT/.ollama/models"

# ── Model Router ──
export MODEL_ROUTER_API_KEY=""

# ── npm cache ──
export npm_config_cache="$NX_MIND_ROOT/.cache/npm"

# ── Load .env if present ──
if [[ -f "$NX_MIND_ROOT/.env" ]]; then
    set -a
    source "$NX_MIND_ROOT/.env"
    set +a
fi

unset _NX_MIND_SCRIPT_DIR
