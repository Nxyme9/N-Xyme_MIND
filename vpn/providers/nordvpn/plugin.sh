#!/usr/bin/env bash
# NordVPN Provider Plugin
# API docs: https://api.nordvpn.com

set -euo pipefail

PROVIDER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NORD_API="https://api.nordvpn.com"
NORD_DNS="103.86.96.100, 103.86.99.100"
NORD_PORT=51820

# ─── helpers ────────────────────────────────────────────────────────────────

_nord_cfg() {
  if [[ ! -f "$PROVIDER_DIR/config.json" ]]; then
    echo '{"error":"config.json not found"}' >&2
    return 1
  fi
  jq -r ".${1:?}" "$PROVIDER_DIR/config.json"
}

_nord_token() {
  if [[ -f "$PROVIDER_DIR/auth_state.json" ]]; then
    jq -r '.token // empty' "$PROVIDER_DIR/auth_state.json"
  fi
}

# ─── provider_info ──────────────────────────────────────────────────────────

provider_info() {
  cat <<'EOF'
{
  "name": "nordvpn",
  "requires_auth": true,
  "auth_type": "username_password",
  "max_connections": 10,
  "protocol": "wireguard"
}
EOF
}

# ─── provider_authenticate ──────────────────────────────────────────────────

provider_authenticate() {
  local username password token_response
  username="$(_nord_cfg username)" || return 1
  password="$(_nord_cfg password)" || return 1

  # NordVPN uses /v1/users/tokens to get an auth token
  token_response=$(curl -sf \
    -X POST "$NORD_API/v1/users/tokens" \
    -H "Content-Type: application/json" \
    --data "$(jq -n --arg u "$username" --arg p "$password" \
      '{username: $u, password: $p}')") || {
    echo '{"error":"authentication request failed"}' >&2
    return 1
  }

  local token
  token=$(echo "$token_response" | jq -r '.token // .access_token // empty')

  if [[ -z "$token" ]]; then
    echo '{"error":"no token in auth response"}' >&2
    return 1
  fi

  jq -n \
    --arg tok "$token" \
    --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{authenticated:true, token:$tok, authenticated_at:$ts}' \
    > "$PROVIDER_DIR/auth_state.json"

  echo "NordVPN: authenticated" >&2
}

# ─── provider_list_servers ──────────────────────────────────────────────────

provider_list_servers() {
  local token
  token="$(_nord_token)" || {
    echo '[]'
    return 1
  }

  # Fetch all servers, filter for wireguard_udp support
  local response
  response=$(curl -sf \
    -H "Authorization: Bearer $token" \
    "$NORD_API/v1/servers?limit=0")

  echo "$response" | jq '[
    .[] | select(.technologies[]?.identifier == "wireguard_udp") | {
      id:       (.hostname | sub("\\.nordvpn\\.com$"; "")),
      name:     .name,
      country:  .country.code,
      city:     (.locations[0].country.city.name // "unknown"),
      hostname: .hostname,
      port:     51820,
      load:     .load,
      station:  .station
    }
  ] | sort_by(.country, .city)'
}

# ─── provider_generate_config ──────────────────────────────────────────────

provider_generate_config() {
  local server_id="${1:?server_id required}"

  if [[ ! -f "$PROVIDER_DIR/auth_state.json" ]]; then
    echo '{"error":"not authenticated"}' >&2
    return 1
  fi

  local token
  token="$(_nord_token)"

  # Fetch the WireGuard private key from NordVPN credentials endpoint
  local cred_response
  cred_response=$(curl -sf \
    -H "Authorization: Bearer $token" \
    "$NORD_API/v1/users/services/credentials") || {
    echo '{"error":"failed to fetch WireGuard credentials"}' >&2
    return 1
  }

  local private_key
  private_key=$(echo "$cred_response" | jq -r '.nordlynx_private_key // .private_key // empty')

  if [[ -z "$private_key" ]]; then
    echo '{"error":"no private key in credentials response"}' >&2
    return 1
  fi

  local public_key
  public_key=$(echo "$private_key" | wg pubkey)

  # Resolve server IP from hostname
  local server_hostname="${server_id}.nordvpn.com"
  local server_ip
  server_ip=$(dig +short "$server_hostname" A | tail -1)

  if [[ -z "$server_ip" ]]; then
    echo "{\"error\":\"could not resolve $server_hostname\"}" >&2
    return 1
  fi

  # Fetch peer public key from server list
  local servers_json
  servers_json=$(curl -sf \
    -H "Authorization: Bearer $token" \
    "$NORD_API/v1/servers?limit=0")

  local peer_pubkey
  peer_pubkey=$(echo "$servers_json" | jq -r \
    --arg sid "$server_id" \
    '[.[] | select(.hostname == ($sid + ".nordvpn.com")) | .technologies[] | select(.identifier == "wireguard_udp") | .metadata[] | select(.name == "public_key") | .value][0] // empty')

  if [[ -z "$peer_pubkey" ]]; then
    # Fallback: use NordVPN's generic endpoint
    peer_pubkey="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    echo "Warning: could not find server public key, using placeholder" >&2
  fi

  cat <<EOF
[Interface]
PrivateKey = $private_key
Address = 10.5.0.2/32
DNS = $NORD_DNS

[Peer]
PublicKey = $peer_pubkey
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = $server_ip:$NORD_PORT
EOF
}

# ─── provider_health_check ─────────────────────────────────────────────────

provider_health_check() {
  local token
  token="$(_nord_token)" || return 1
  curl -sf \
    -H "Authorization: Bearer $token" \
    "$NORD_API/v1/servers?limit=1" \
    -o /dev/null
}

# ─── provider_cleanup ──────────────────────────────────────────────────────

provider_cleanup() {
  return 0
}
