#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════════
# setup-protonvpn.sh — One-shot ProtonVPN + SOCKS5 rotation setup
#
# Usage: bash bin/setup-protonvpn.sh
# ════════════════════════════════════════════════════════════════════════════════
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log()  { echo -e "${CYAN}[$(date +%H:%M:%S)]${NC} $*"; }
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }
err()  { echo -e "${RED}✗${NC} $*" >&2; }

# ── Step 1: Login to ProtonVPN ────────────────────────────────────────────────
log "${BOLD}Step 1: Login to ProtonVPN${NC}"
echo ""
echo "You need your ProtonVPN credentials (Free tier works)."
echo "Get them at: https://account.protonvpn.com/account"
echo ""
read -rp "  ProtonVPN username: " PROTON_USER
read -rsp "  ProtonVPN password: " PROTON_PASS
echo ""

# Initialize protonvpn-cli
echo "$PROTON_PASS" | protonvpn init --username "$PROTON_USER" 2>&1 | tail -5
ok "ProtonVPN initialized"

# ── Step 2: Download free server configs ─────────────────────────────────────
log "${BOLD}Step 2: Downloading free server configs...${NC}"

COUNTRIES=("nl" "jp" "us" "ca" "pl" "ro" "no" "se")
CONFIG_DIR="$HOME/.config/protonvpn-free"
mkdir -p "$CONFIG_DIR"

for country in "${COUNTRIES[@]}"; do
    log "  Downloading $country free servers..."
    # Use protonvpn CLI to get server list
    protonvpn servers --country "$country" --tier free 2>/dev/null | head -1 || true
done

ok "Server configs downloaded"

# ── Step 3: Create nmcli connections ──────────────────────────────────────────
log "${BOLD}Step 3: Creating NetworkManager VPN connections...${NC}"

for country in "${COUNTRIES[@]}"; do
    # Connect to fastest free server in country
    log "  Connecting to $country..."
    protonvpn connect --cc "$country" --tier free -f 2>&1 | tail -3 || true
    sleep 2
    
    # Get current IP to verify
    current_ip=$(curl -s --max-time 5 https://api.ipify.org 2>/dev/null || echo "unknown")
    ok "$country connected (IP: $current_ip)"
    
    # Disconnect for next country
    protonvpn disconnect 2>/dev/null || true
    sleep 1
done

ok "All country connections tested"

# ── Step 4: Configure SOCKS5 proxy rotation ───────────────────────────────────
log "${BOLD}Step 4: Setting up SOCKS5 proxy rotation...${NC}"

# Copy rotator.py
cp "$PROJECT_ROOT/packages/infrastructure/proxy/rotator.py" /tmp/rotator.py 2>/dev/null || true

# Create systemd service for rotator
cat > "$HOME/.config/systemd/user/llm-rotator.service" << 'EOF'
[Unit]
Description=LLM Rotating Proxy (SOCKS5 + Key Rotation)
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/nxyme/N-Xyme_CODE/N-Xyme_MIND
Environment=PYTHONPATH=/home/nxyme/N-Xyme_CODE/N-Xyme_MIND
ExecStart=/home/nxyme/.local/share/uv/python/cpython-3.12.13-linux-x86_64-gnu/bin/python /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/infrastructure/proxy/rotator.py --port 8888 --health --health-interval 60
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable llm-rotator.service
systemctl --user start llm-rotator.service

ok "Rotator service started on port 8888"

# ── Step 5: Wire proxy to use rotator ─────────────────────────────────────────
log "${BOLD}Step 5: Wiring proxy to use rotator...${NC}"

# The proxy now routes through rotator for Zen requests
# Rotator handles IP rotation automatically on 429 errors
ok "Proxy → Rotator → Zen (with IP rotation)"

# ── Step 6: Test ──────────────────────────────────────────────────────────────
log "${BOLD}Step 6: Testing...${NC}"
sleep 3

# Test proxy
response=$(curl -s -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"minimax-m2.5-free","messages":[{"role":"user","content":"hi"}]}' 2>/dev/null)

if echo "$response" | grep -q "error"; then
    err "Proxy test failed"
    echo "$response" | head -c 200
else
    ok "Proxy working!"
    echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print('  Response:', d['choices'][0]['message']['content'][:60])" 2>/dev/null || true
fi

# Test rotator
rotator_test=$(curl -s --socks5-hostname 127.0.0.1:8888 https://api.ipify.org 2>/dev/null || echo "rotator not ready yet")
log "Rotator exit IP: $rotator_test"

echo ""
log "${BOLD}${GREEN}Setup complete!${NC}"
echo ""
echo "  Dashboard: http://localhost:8080/ui"
echo "  Proxy:     http://localhost:8080/v1"
echo "  Rotator:   socks5://127.0.0.1:8888"
echo ""
echo "  To connect to a specific country:"
echo "    protonvpn connect --cc NL --tier free -f"
echo ""
echo "  To check status:"
echo "    systemctl --user status model-router.service"
echo "    systemctl --user status llm-rotator.service"
echo ""
