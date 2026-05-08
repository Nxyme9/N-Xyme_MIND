#!/usr/bin/env bash
# Bash environment setup — source with: source ./env.sh

# Get script directory (resolve symlinks and go up to project root)
_NX_MIND_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Core paths ──
export NX_MIND_ROOT="$_NX_MIND_SCRIPT_DIR"
export VIRTUAL_ENV="$NX_MIND_ROOT/.venv"
export PATH="$VIRTUAL_ENV/bin:$PATH"
export PYTHONPATH="$NX_MIND_ROOT/packages:$NX_MIND_ROOT/src"

# ── Ollama ──
export OLLAMA_MODELS="$NX_MIND_ROOT/.ollama/models"

# ── Model Router ──
export MODEL_ROUTER_API_KEY=""

# ── npm cache ──
export npm_config_cache="$NX_MIND_ROOT/.cache/npm"

# ── Temp & Cache (avoid /tmp which is small) ──
export TMPDIR="$NX_MIND_ROOT/.tmp"
export TEMP="$NX_MIND_ROOT/.tmp"
export TMP="$NX_MIND_ROOT/.tmp"
export PIP_CACHE_DIR="$NX_MIND_ROOT/.cache/pip"
export CARGO_HOME="$NX_MIND_ROOT/.cache/cargo"
export RUSTUP_HOME="$NX_MIND_ROOT/.cache/rustup"

# Create temp dir if missing
mkdir -p "$NX_MIND_ROOT/.tmp"
mkdir -p "$NX_MIND_ROOT/.cache/pip"
mkdir -p "$NX_MIND_ROOT/.cache/npm"
mkdir -p "$NX_MIND_ROOT/.cache/cargo"
mkdir -p "$NX_MIND_ROOT/.cache/rustup"

# ── Load .env if present ──
if [[ -f "$NX_MIND_ROOT/.env" ]]; then
    set -a
    source "$NX_MIND_ROOT/.env"
    set +a
fi

unset _NX_MIND_SCRIPT_DIR
