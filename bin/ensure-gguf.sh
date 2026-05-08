#!/usr/bin/env bash
# bin/ensure-gguf.sh — Check GGUF llama-server on port 8088
set -euo pipefail

GGUF_URL="http://localhost:8088"
MAX_WAIT=30
POLL_INTERVAL=2

# ── Colors ──
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[gguf]${NC} $*"; }
warn()  { echo -e "${YELLOW}[gguf]${NC} $*"; }
error() { echo -e "${RED}[gguf]${NC} $*"; }

# ── 1. Check if GGUF llama-server is running on port 8088 ──
if curl -sf --max-time 2 "$GGUF_URL/v1/models" &>/dev/null; then
    info "GGUF llama-server is running on port 8088"
    exit 0
fi

# ── 2. Not running — report error ──
error "GGUF llama-server not running on port 8088"
echo ""
echo "To start GGUF llama-server:"
echo "  llama-server -m models/qwen2.5-0.5b-instruct-q4_k_m.gguf --port 8088"
exit 1