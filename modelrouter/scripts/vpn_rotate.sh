#!/usr/bin/env bash
# VPN Rotation Script for ProtonVPN Free Tier
# Usage: ./vpn_rotate.sh [country]
# Countries: NL, JP, US, CA, PL, RO, NO (auto if no arg)

# Don't exit on error - we handle failures gracefully
set +e

# VPN connections by country
declare -A VPN_CONNECTIONS=(
    ["NL"]="ProtonVPN-NL-FREE"
    ["JP"]="ProtonVPN-JP-FREE"
    ["US"]="ProtonVPN-US-FREE"
    ["CA"]="ProtonVPN-CA-FREE"
    ["PL"]="ProtonVPN-PL-FREE"
    ["RO"]="ProtonVPN-RO-FREE"
    ["NO"]="ProtonVPN-NO-FREE"
)

PM2_APP="socks5-vpn"

# Get all active VPN connections
get_active_vpns() {
    nmcli connection show --active | grep -i "protonvpn" | awk '{print $1}' || echo ""
}

# Disconnect ALL VPN connections
disconnect_all_vpn() {
    local vpns=$(get_active_vpns)
    if [ -n "$vpns" ]; then
        echo "Disconnecting VPNs: $vpns"
        for vpn in $vpns; do
            echo "  Down: $vpn"
            nmcli connection down id "$vpn" 2>/dev/null || true
        done
        # Wait for tun0 to disappear
        echo "Waiting for tun0 to disappear..."
        for i in {1..10}; do
            if ! ip link show tun0 &>/dev/null; then
                echo "  tun0 removed"
                return 0
            fi
            sleep 1
        done
    fi
    return 0
}

# Connect to country
connect_vpn() {
    local country=$1
    local conn_name=${VPN_CONNECTIONS[$country]}
    
    if [ -z "$conn_name" ]; then
        echo "Unknown country: $country"
        echo "Available: ${!VPN_CONNECTIONS[@]}"
        exit 1
    fi
    
    echo "Connecting to $country ($conn_name)..."
    nmcli connection up id "$conn_name" 2>&1
    
    # Wait for tun0 with longer timeout
    echo "Waiting for tun0 to appear..."
    for i in {1..20}; do
        if ip link show tun0 &>/dev/null; then
            # Verify it's actually UP
            if ip link show tun0 | grep -q "UP"; then
                break
            fi
        fi
        echo "  Attempt $i/20..."
        sleep 1
    done
    
    if ip link show tun0 &>/dev/null; then
        local vpn_ip=$(curl --interface tun0 --connect-timeout 10 -s http://ifconfig.me 2>/dev/null || echo "unknown")
        echo "Connected! VPN IP: $vpn_ip"
        return 0
    else
        echo "ERROR: tun0 not found after connection"
        return 1
    fi
}

# Restart SOCKS proxy
restart_proxy() {
    echo "Restarting SOCKS proxy..."
    # Kill stale processes first to free port
    pkill -f "socks5_vpn.py" 2>/dev/null || true
    sleep 1
    
    # Use pm2 restart but don't wait for it
    pm2 restart $PM2_APP 2>&1 || true
    
    # Wait for proxy to be ready
    echo "Waiting for proxy..."
    for i in {1..10}; do
        if ss -tlnp 2>/dev/null | grep -q ":1080"; then
            break
        fi
        sleep 1
    done
    
    # Quick test with timeout
    local proxy_ip=$(timeout 10 curl -s --socks5 127.0.0.1:1080 --connect-timeout 5 http://ifconfig.me 2>/dev/null || echo "failed")
    
    if [ "$proxy_ip" != "failed" ] && [ -n "$proxy_ip" ]; then
        echo "Proxy working! IP through proxy: $proxy_ip"
        return 0
    else
        echo "Warning: Proxy may not be working (got: $proxy_ip)"
        return 1
    fi
}

# Auto-rotate to random country
auto_rotate() {
    local countries=(${!VPN_CONNECTIONS[@]})
    local current=$(get_active_vpns | head -1)
    local new_country
    
    # Pick a different country
    local attempts=0
    while [ $attempts -lt 10 ]; do
        new_country=${countries[$RANDOM % ${#countries[@]}]}
        if [[ "$current" != *"$new_country"* ]]; then
            break
        fi
        attempts=$((attempts + 1))
    done
    
    echo "Auto-rotating to: $new_country"
    connect_vpn "$new_country"
}

# Main
main() {
    local country=${1^^}  # Uppercase
    
    echo "=== VPN Rotation ==="
    
    # Step 1: Disconnect all VPNs
    disconnect_all_vpn
    
    # Small pause
    sleep 2
    
    # Step 2: Connect to new VPN
    if [ -z "$country" ]; then
        auto_rotate
    else
        connect_vpn "$country"
    fi
    
    # Step 3: Restart proxy
    restart_proxy
    
    echo "=== Complete ==="
    echo "Direct IP: $(curl -s --connect-timeout 5 http://ifconfig.me 2>/dev/null || echo 'N/A')"
}

main "$@"
