#!/usr/bin/env bash
# Create ProtonVPN FREE tier connections for all available countries
# Uses existing TLS certs (all identical) from working NL connection

CERT_DIR="/home/nxyme/.local/share/networkmanagement/certificates/nm-openvpn"
CERT_PREFIX="pvpnef8idi9w"  # All cert sets are identical, using the one from working NL

# Server IPs resolved from node-{country}-{number}.protonvpn.net
declare -A SERVERS=(
  ["NL"]="185.177.124.84:node-nl-108.protonvpn.net"
  ["JP"]="45.87.213.226:node-jp-31.protonvpn.net"
  ["CA"]="149.88.97.122:node-ca-25.protonvpn.net"
  ["PL"]="149.102.244.112:node-pl-12.protonvpn.net"
  ["RO"]="146.70.246.98:node-ro-12.protonvpn.net"
  ["NO"]="95.173.205.167:node-no-12.protonvpn.net"
)

# Additional backup servers
declare -A BACKUP_SERVERS=(
  ["NL2"]="212.8.243.7:node-nl-138.protonvpn.net"
  ["JP2"]="193.148.16.2:node-jp-32.protonvpn.net"
  ["CA2"]="149.88.97.110:node-ca-26.protonvpn.net"
  ["RO2"]="146.70.246.97:node-ro-13.protonvpn.net"
  ["NO2"]="95.173.205.165:node-no-13.protonvpn.net"
)

create_connection() {
  local name="$1"
  local server_ip="$2"
  local verify_name="$3"
  
  echo "Creating connection: $name -> $server_ip ($verify_name)"
  
  nmcli connection add \
    type vpn \
    ifname -- \
    vpn.openvpn.service-type org.freedesktop.NetworkManager.openvpn \
    vpn.data "ca=${CERT_DIR}/${CERT_PREFIX}-ca.pem,\
cert=${CERT_DIR}/${CERT_PREFIX}-cert.pem,\
cipher=AES-256-GCM,\
connection-type=tls,\
dev=tun,\
key=${CERT_DIR}/${CERT_PREFIX}-key.pem,\
mssfix=0,\
proto-tcp=yes,\
remote=${server_ip}:443\\ ${server_ip}:7770\\ ${server_ip}:8443,\
remote-cert-tls=server,\
remote-random=yes,\
reneg-seconds=0,\
tls-crypt=${CERT_DIR}/${CERT_PREFIX}-tls-crypt.pem,\
tunnel-mtu=1500,\
verify-x509-name=name:${verify_name}" \
    connection.id "$name" \
    connection.autoconnect no
    
  if [ $? -eq 0 ]; then
    echo "  ✓ Created $name"
  else
    echo "  ✗ Failed to create $name (may already exist)"
  fi
}

# Delete existing test connections (not the working NL one)
echo "Cleaning up old test connections..."
for conn in "ProtonVPN JP-FREE" "ProtonVPN US-FREE" "ProtonVPN CA-FREE" "ProtonVPN PL-FREE" "ProtonVPN RO-FREE" "ProtonVPN NO-FREE" "ProtonVPN SE-FREE"; do
  nmcli connection delete "$conn" 2>/dev/null
done

echo ""
echo "Creating primary connections..."
for country in NL JP CA PL RO NO; do
  IFS=':' read -r ip hostname <<< "${SERVERS[$country]}"
  create_connection "ProtonVPN ${country}-FREE" "$ip" "$hostname"
done

echo ""
echo "Creating backup connections..."
for key in NL2 JP2 CA2 RO2 NO2; do
  country="${key:0:2}"
  IFS=':' read -r ip hostname <<< "${BACKUP_SERVERS[$key]}"
  create_connection "ProtonVPN ${country}-FREE-BACKUP" "$ip" "$hostname"
done

echo ""
echo "=== Summary ==="
echo "Available ProtonVPN connections:"
nmcli connection show | grep -i protonvpn | awk '{print $1}'

echo ""
echo "NOTE: US servers could not be resolved. Need to find US server IPs manually."
echo "NOTE: Sweden (SE) is NOT available on ProtonVPN free tier."
