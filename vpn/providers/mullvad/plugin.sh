#!/usr/bin/env bash
# Mullvad VPN Provider Plugin
# API docs: https://api.mullvad.net/

set -euo pipefail

PROVIDER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MULLVAD_API="https://api.mullvad.net"
MULLVAD_DNS="10.64.0.1"
MULLVAD_PORT=51820

# ─── helpers ────────────────────────────────────────────────────────────────

_mullvad_cfg() {
  if [[ ! -f "$PROVIDER_DIR/config.json" ]]; then
    echo '{"error":"config.json not found"}' >&2
    return 1
  fi
  jq -r ".${1:?}" "$PROVIDER_DIR/config.json"
}

# ─── provider_info ──────────────────────────────────────────────────────────

provider_info() {
  cat <<'EOF'
{
  "name": "mullvad",
  "requires_auth": true,
  "auth_type": "account_number",
  "max_connections": 5,
  "protocol": "wireguard"
}
EOF
}

# ─── provider_authenticate ──────────────────────────────────────────────────

provider_authenticate() {
  local account_number
  account_number="$(_mullvad_cfg account_number)" || return 1

  if ! [[ "$account_number" =~ ^[0-9]+$ ]]; then
    echo '{"error":"account_number must be numeric"}' >&2
    return 1
  fi

  # Verify account with Mullvad API
  local status
  status=$(curl -sf \
    -H "Authorization: Bearer $account_number" \
    "$MULLVAD_API/public/relays/wireguard/v1/" \
    -o /dev/null -w '%{http_code}' 2>/dev/null) || true

  if [[ "$status" != "200" ]]; then
    echo '{"error":"account verification failed (bad account number or network error)"}' >&2
    return 1
  fi

  jq -n \
    --arg acct "$account_number" \
    --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{authenticated:true, account_number:$acct, authenticated_at:$ts}' \
    > "$PROVIDER_DIR/auth_state.json"

  echo "Mullvad: authenticated (account $account_number)" >&2
}

# ─── provider_list_servers ──────────────────────────────────────────────────

provider_list_servers() {
  local account_number
  account_number="$(_mullvad_cfg account_number)" || return 1

  local response
  response=$(curl -sf \
    -H "Authorization: Bearer $account_number" \
    "$MULLVAD_API/public/relays/wireguard/v1/")

  # Parse relay list — each relay has {hostname, country_code, city_code, ipv4_addr_in, ...}
  echo "$response" | jq '[
    .relays[] | {
      id:       .hostname,
      name:     .hostname,
      country:  .country_code,
      city:     .city_code,
      hostname: (.hostname + ".mullvad.net"),
      public_key: .public_key,
      ipv4:     .ipv4_addr_in,
      port:     51820
    }
  ]'
}

# ─── provider_generate_config ──────────────────────────────────────────────

provider_generate_config() {
  local server_id="${1:?server_id required (use hostname from provider_list_servers)}"

  # Load auth
  if [[ ! -f "$PROVIDER_DIR/auth_state.json" ]]; then
    echo '{"error":"not authenticated — run provider_authenticate first"}' >&2
    return 1
  fi

  local account_number
  account_number=$(jq -r '.account_number' "$PROVIDER_DIR/auth_state.json")

  # Generate a WireGuard keypair
  local private_key public_key
  private_key=$(wg genkey)
  public_key=$(echo "$private_key" | wg pubkey)

  # Register the key with Mullvad and get an IP
  local wg_response
  wg_response=$(curl -sf \
    -X POST "$MULLVAD_API/public/relays/wireguard/v1/" \
    -H "Authorization: Bearer $account_number" \
    -H "Content-Type: application/json" \
    --data "$(jq -n --arg pk "$public_key" '{public_key: $pk}')")

  local client_ipv4 client_ipv6 server_pubkey
  client_ipv4=$(echo "$wg_response" | jq -r '.ipv4_address')
  client_ipv6=$(echo "$wg_response" | jq -r '.ipv6_address')

  # Look up the server's public key from the relay list
  local relay_list
  relay_list=$(curl -sf \
    -H "Authorization: Bearer $account_number" \
    "$MULLVAD_API/public/relays/wireguard/v1/")

  server_pubkey=$(echo "$relay_list" | jq -r \
    --arg sid "$server_id" \
    '.relays[] | select(.hostname == $sid) | .public_key')

  if [[ -z "$server_pubkey" || "$server_pubkey" == "null" ]]; then
    echo "{\"error\":\"server $server_id not found\"}" >&2
    return 1
  fi

  # Look up server IP
  local server_ip
  server_ip=$(echo "$relay_list" | jq -r \
    --arg sid "$server_id" \
    '.relays[] | select(.hostname == $sid) | .ipv4_addr_in')

  # Output WireGuard config
  cat <<EOF
[Interface]
PrivateKey = $private_key
Address = $client_ipv4/32, $client_ipv6/128
DNS = $MULLVAD_DNS

[Peer]
PublicKey = $server_pubkey
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = $server_ip:$MULLVAD_PORT
EOF
}

# ─── provider_health_check ─────────────────────────────────────────────────

provider_health_check() {
  if [[ ! -f "$PROVIDER_DIR/auth_state.json" ]]; then
    return 1
  fi
  local account_number
  account_number=$(jq -r '.account_number' "$PROVIDER_DIR/auth_state.json") || return 1
  curl -sf \
    -H "Authorization: Bearer $account_number" \
    "$MULLVAD_API/public/relays/wireguard/v1/" \
    -o /dev/null
}

# ─── provider_cleanup ──────────────────────────────────────────────────────

provider_cleanup() {
  echo "Mullvad: cleanup (no-op)" >&2
  return 0
}
