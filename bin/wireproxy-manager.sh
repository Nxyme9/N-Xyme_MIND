#!/usr/bin/env bash
# WireProxy SOCKS5 proxy manager for VPN rotation
# Creates and manages 8 WireProxy instances on ports 1080-1087

set -euo pipefail

WIREPROXY_BIN="${HOME}/go/bin/wireproxy"
CONFIG_DIR="${HOME}/.config/wireproxy"
SERVICE_DIR="${HOME}/.config/systemd/user"

# VPN server list (different countries for different exit IPs)
declare -A SERVERS=(
    [1]="nl-free-101.protonvpn.net:51820"    # Netherlands
    [2]="us-free-101.protonvpn.net:51820"     # USA
    [3]="de-free-101.protonvpn.net:51820"     # Germany
    [4]="ca-free-101.protonvpn.net:51820"     # Canada
    [5]="jp-free-101.protonvpn.net:51820"     # Japan
    [6]="ro-free-101.protonvpn.net:51820"     # Romania
    [7]="no-free-101.protonvpn.net:51820"     # Norway
    [8]="se-free-101.protonvpn.net:51820"     # Sweden
)

# Country codes for naming
declare -A COUNTRIES=(
    [1]="nl" [2]="us" [3]="de" [4]="ca"
    [5]="jp" [6]="ro" [7]="no" [8]="se"
)

usage() {
    echo "Usage: $0 {setup|start|stop|status|generate-configs}"
    echo ""
    echo "Commands:"
    echo "  setup            - Create systemd service template"
    echo "  generate-configs - Generate WireProxy configs (requires WG credentials)"
    echo "  start            - Start all WireProxy instances"
    echo "  stop             - Stop all WireProxy instances"
    echo "  status           - Show status of all instances"
    exit 1
}

setup() {
    echo "Creating systemd service template..."
    cat > "${SERVICE_DIR}/wireproxy@.service" << 'SVCEOF'
[Unit]
Description=WireProxy SOCKS5 instance %i
After=network.target

[Service]
ExecStart=%h/go/bin/wireproxy -c %h/.config/wireproxy/proxy-%i.conf
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=default.target
SVCEOF
    echo "Service template created at ${SERVICE_DIR}/wireproxy@.service"
}

generate_configs() {
    echo "Generating WireProxy configs..."
    echo ""
    echo "⚠️  You need to provide your ProtonVPN WireGuard credentials."
    echo "   Get them from: https://account.protonvpn.com/account -> Downloads -> WireGuard"
    echo ""
    
    for i in "${!SERVERS[@]}"; do
        PORT=$((1079 + i))
        COUNTRY="${COUNTRIES[$i]}"
        CONF_FILE="${CONFIG_DIR}/proxy-${i}.conf"
        
        if [ -f "$CONF_FILE" ] && grep -q "PrivateKey = PLACEHOLDER" "$CONF_FILE"; then
            echo "Config $i ($COUNTRY) needs WireGuard credentials:"
            echo "  File: $CONF_FILE"
            echo "  Port: $PORT"
            echo "  Server: ${SERVERS[$i]}"
            echo ""
            echo "  Edit the file and replace:"
            echo "    PrivateKey = <your-wg-private-key>"
            echo "    PublicKey = <wg-public-key-for-${COUNTRY}>"
            echo ""
        fi
    done
}

start_all() {
    echo "Starting WireProxy instances..."
    systemctl --user daemon-reload
    
    for i in "${!SERVERS[@]}"; do
        echo "Starting proxy-$i (port $((1079 + i)), ${COUNTRIES[$i]})..."
        systemctl --user start "wireproxy@${i}" 2>/dev/null || echo "  Failed to start proxy-$i"
    done
    
    sleep 3
    status_all
}

stop_all() {
    echo "Stopping WireProxy instances..."
    for i in "${!SERVERS[@]}"; do
        systemctl --user stop "wireproxy@${i}" 2>/dev/null || true
    done
    echo "All instances stopped."
}

status_all() {
    echo "=== WireProxy Status ==="
    for i in "${!SERVERS[@]}"; do
        PORT=$((1079 + i))
        COUNTRY="${COUNTRIES[$i]}"
        STATUS=$(systemctl --user is-active "wireproxy@${i}" 2>/dev/null || echo "inactive")
        
        if [ "$STATUS" = "active" ]; then
            echo "  ✅ proxy-$i ($COUNTRY:$PORT) - active"
        else
            echo "  ❌ proxy-$i ($COUNTRY:$PORT) - $STATUS"
        fi
    done
    echo ""
    echo "=== VPN Health (Model Router) ==="
    curl -sf http://127.0.0.1:8080/vpn/health 2>/dev/null | python3 -m json.tool 2>/dev/null | head -10 || echo "  Model router not responding"
}

case "${1:-}" in
    setup) setup ;;
    generate-configs) generate_configs ;;
    start) start_all ;;
    stop) stop_all ;;
    status) status_all ;;
    *) usage ;;
esac
