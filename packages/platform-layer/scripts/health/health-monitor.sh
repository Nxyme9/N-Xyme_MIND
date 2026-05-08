#!/usr/bin/env bash
# Health Monitor for N-Xyme MIND System
# Checks all components and auto-recovers failed services

set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; ERRORS=$((ERRORS+1)); }
warn() { echo -e "${YELLOW}!${NC} $1"; }

ERRORS=0

echo "=== N-Xyme MIND Health Monitor ==="
echo "Timestamp: $(date)"
echo ""

# Check Model Router
echo "--- Model Router ---"
if curl -sf http://127.0.0.1:8080/health > /dev/null 2>&1; then
    pass "Model Router: Healthy"
else
    fail "Model Router: Unhealthy - Restarting..."
    systemctl --user restart model-router.service
    sleep 2
    if curl -sf http://127.0.0.1:8080/health > /dev/null 2>&1; then
        pass "Model Router: Recovered"
    else
        fail "Model Router: Failed to recover"
    fi
fi

# Check SOCKS5 Proxies
echo ""
echo "--- SOCKS5 Proxies ---"
for port in 1080 1081 1082 1083 1084 1085 1086 1087; do
    if ss -tlnp | grep -q ":${port} "; then
        pass "SOCKS5 Proxy :${port}: Running"
    else
        fail "SOCKS5 Proxy :${port}: Down - Restarting..."
        systemctl --user restart socks5-proxy@${port}.service
        sleep 1
        if ss -tlnp | grep -q ":${port} "; then
            pass "SOCKS5 Proxy :${port}: Recovered"
        else
            fail "SOCKS5 Proxy :${port}: Failed to recover"
        fi
    fi
done

# Check GGUF llama-server (primary) and Ollama (fallback)
echo ""
echo "--- GGUF / Ollama ---"
if curl -sf http://localhost:8080/api/tags > /dev/null 2>&1; then
    pass "GGUF llama-server: Running on port 8080"
elif curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    warn "GGUF llama-server: Not running - using Ollama fallback on port 11434"
else
    fail "Neither GGUF (8080) nor Ollama (11434) is running"
fi

# Check Local Models (GGUF)
echo ""
echo "--- GGUF Models ---"
for model in qwen2.5-coder-7b-q4_k_m qwen2.5-0.5b-instruct-q4_k_m nomic-embed-text-v1.5-Q4_K_M.gguf; do
    if curl -sf http://localhost:8080/api/tags 2>/dev/null | grep -q "$model"; then
        pass "Model: $model (available)"
    else
        warn "Model: $model (not loaded)"
    fi
done

# Summary
echo ""
echo "==================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}All checks passed!${NC}"
else
    echo -e "${RED}$ERRORS check(s) failed${NC}"
fi
exit $ERRORS
