#!/usr/bin/env bash
# Create ProtonVPN FREE tier connections by importing .ovpn files
# Uses existing TLS certs from working NL connection

CERT_DIR="/home/nxyme/.local/share/networkmanagement/certificates/nm-openvpn"
CERT_PREFIX="pvpnef8idi9w"
OVPN_DIR="/tmp/protonvpn-configs"

mkdir -p "$OVPN_DIR"

# Read CA cert and TLS-crypt key
CA_CERT=$(cat "${CERT_DIR}/${CERT_PREFIX}-ca.pem")
TLS_CRYPT=$(cat "${CERT_DIR}/${CERT_PREFIX}-tls-crypt.pem")

# Server list: country|ip|hostname
SERVERS=(
  "NL|185.177.124.84|node-nl-108.protonvpn.net"
  "JP|45.87.213.226|node-jp-31.protonvpn.net"
  "CA|149.88.97.122|node-ca-25.protonvpn.net"
  "PL|149.102.244.112|node-pl-12.protonvpn.net"
  "RO|146.70.246.98|node-ro-12.protonvpn.net"
  "NO|95.173.205.167|node-no-12.protonvpn.net"
  # Backup servers
  "NL-2|212.8.243.7|node-nl-138.protonvpn.net"
  "JP-2|193.148.16.2|node-jp-32.protonvpn.net"
  "CA-2|149.88.97.110|node-ca-26.protonvpn.net"
  "RO-2|146.70.246.97|node-ro-13.protonvpn.net"
  "NO-2|95.173.205.165|node-no-13.protonvpn.net"
)

create_ovpn() {
  local country="$1"
  local ip="$2"
  local hostname="$3"
  local config_name="ProtonVPN-${country}-FREE"
  local ovpn_file="${OVPN_DIR}/${config_name}.ovpn"
  
  cat > "$ovpn_file" << EOF
client
dev tun
proto tcp
remote ${ip} 443
remote ${ip} 7770
remote ${ip} 8443
remote-random
resolv-retry infinite
nobind
tun-mtu 1500
mssfix 0
cipher AES-256-GCM
auth SHA512
comp-lzo no
verb 3
persist-key
persist-tun
remote-cert-tls server
verify-x509-name ${hostname} name
reneg-sec 0
auth-nocache
script-security 2

<ca>
${CA_CERT}
</ca>

<cert>
$(cat "${CERT_DIR}/${CERT_PREFIX}-cert.pem")
</cert>

<key>
$(cat "${CERT_DIR}/${CERT_PREFIX}-key.pem")
</key>

key-direction 1
<tls-auth>
${TLS_CRYPT}
</tls-auth>
EOF

  echo "$ovpn_file"
}

echo "=== Creating .ovpn configs ==="
for server in "${SERVERS[@]}"; do
  IFS='|' read -r country ip hostname <<< "$server"
  ovpn_file=$(create_ovpn "$country" "$ip" "$hostname")
  echo "Created: $ovpn_file"
done

echo ""
echo "=== Importing into NetworkManager ==="
for ovpn_file in "${OVPN_DIR}"/*.ovpn; do
  config_name=$(basename "$ovpn_file" .ovpn)
  echo "Importing: $config_name"
  
  # Delete if exists
  nmcli connection delete "$config_name" 2>/dev/null
  
  # Import
  nmcli connection import type openvpn file "$ovpn_file"
  
  if [ $? -eq 0 ]; then
    echo "  ✓ Imported $config_name"
  else
    echo "  ✗ Failed to import $config_name"
  fi
done

echo ""
echo "=== Summary ==="
echo "ProtonVPN connections:"
nmcli connection show | grep -i protonvpn
