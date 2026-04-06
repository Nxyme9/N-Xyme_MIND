#!/usr/bin/env bash
# bin/ensure-ollama.sh — Start Ollama, wait for readiness, pull embedding model if missing
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OLLAMA_URL="http://localhost:11434"
EMBED_MODEL="${OLLAMA_EMBED_MODEL:-nomic-embed-text}"
MAX_WAIT=30
POLL_INTERVAL=2

# ── Colors ──
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[ollama]${NC} $*"; }
warn()  { echo -e "${YELLOW}[ollama]${NC} $*"; }
error() { echo -e "${RED}[ollama]${NC} $*"; }

# ── 1. Check if Ollama binary exists ──
if ! command -v ollama &>/dev/null; then
    error "ollama binary not found in PATH"
    echo "Install: curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
fi

# ── 2. Start Ollama if not running ──
if curl -sf --max-time 2 "$OLLAMA_URL/api/tags" &>/dev/null; then
    info "Ollama is already running"
else
    warn "Ollama not running — starting..."
    ollama serve &>/dev/null &
    OLLAMA_PID=$!
    disown $OLLAMA_PID 2>/dev/null || true
fi

# ── 3. Wait for Ollama to be ready ──
info "Waiting for Ollama to be ready (max ${MAX_WAIT}s)..."
elapsed=0
while [ $elapsed -lt $MAX_WAIT ]; do
    if curl -sf --max-time 2 "$OLLAMA_URL/api/tags" &>/dev/null; then
        info "Ollama is ready (${elapsed}s)"
        break
    fi
    sleep $POLL_INTERVAL
    elapsed=$((elapsed + POLL_INTERVAL))
done

if [ $elapsed -ge $MAX_WAIT ]; then
    error "Ollama did not become ready within ${MAX_WAIT}s"
    exit 1
fi

# ── 4. Pull embedding model if missing ──
if ollama list 2>/dev/null | grep -q "$EMBED_MODEL"; then
    info "Embedding model '$EMBED_MODEL' already present"
else
    warn "Embedding model '$EMBED_MODEL' not found — pulling..."
    ollama pull "$EMBED_MODEL"
    info "Embedding model '$EMBED_MODEL' pulled successfully"
fi

# ── 5. Verify model is loaded ──
if ollama list 2>/dev/null | grep -q "$EMBED_MODEL"; then
    info "Ollama ready with model '$EMBED_MODEL'"
    exit 0
else
    error "Model '$EMBED_MODEL' failed to pull"
    exit 1
fi
