#!/usr/bin/env bash
# Surfshark VPN Provider Plugin
# API: https://api.surfshark.com

set -euo pipefail

PROVIDER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SURFSHARK_API="https://api.surfshark.com"

# ─── helpers ────────────────────────────────────────────────────────────────

_ss_cfg() {
  if [[ ! -f "$PROVIDER_DIR/config.json" ]]; then
    echo '{"error":"config.json not found"}' >&2
    return 1
  fi
  jq -r ".${1:?}" "$PROVIDER_DIR/config.json"
}

_ss_token() {
  if [[ -f "$PROVIDER_DIR/auth_state.json" ]]; then
    jq -r '.token // empty' "$PROVIDER_DIR/auth_state.json"
  fi
}

# ─── provider_info ──────────────────────────────────────────────────────────

provider_info() {
  cat <<'EOF'
{
  "name": "surfshark",
  "requires_auth": true,
  "auth_type": "username_password",
  "max_connections": 0,
  "protocol": "wireguard"
}
EOF
}

# ─── provider_authenticate ──────────────────────────────────────────────────

provider_authenticate() {
  local username password
  username="$(_ss_cfg username)" || return 1
  password="$(_ss_cfg password)" || return 1

  local token_response
  token_response=$(curl -sf \
    -X POST "$SURFSHARK_API/v1/auth/login" \
    -H "Content-Type: application/json" \
    --data "$(jq -n --arg u "$username" --arg p "$password" \
      '{username: $u, password: $p}')") || {
    echo '{"error":"login request failed"}' >&2
    return 1
  }

  local token
  token=$(echo "$token_response" | jq -r '.token // .accessToken // empty')

  if [[ -z "$token" ]]; then
    echo '{"error":"no token in login response"}' >&2
    return 1
  fi

  jq -n \
    --arg tok "$token" \
    --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{authenticated:true, token:$tok, authenticated_at:$ts}' \
    > "$PROVIDER_DIR/auth_state.json"

  echo "Surfshark: authenticated" >&2
}

# ─── provider_list_servers ──────────────────────────────────────────────────

provider_list_servers() {
  local token
  token="$(_ss_token)" || {
    echo '[]'
    return 1
  }

  local response
  response=$(curl -sf \
    -H "Authorization: Bearer $token" \
    "$SURFSHARK_API/v1/server")

  echo "$response" | jq '[
    .data // .[] | {
      id:       .id,
      name:     (.friendlyName // .hostname),
      country:  (.country // "XX"),
      city:     (.location // .city // "unknown"),
      hostname: .hostname,
      port:     51820
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
  token="$(_ss_token)"

  local gen_response
  gen_response=$(curl -sf \
    -X POST "$SURFSHARK_API/v1/server/generateWireguard" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    --data "$(jq -n --arg sid "$server_id" '{deviceId: $sid}')") || {
    echo '{"error":"config generation failed"}' >&2
    return 1
  }

  echo "$gen_response" | jq -r '
    "[Interface]\n" +
    "PrivateKey = " + .privateKey + "\n" +
    "Address = " + (.address // "10.14.0.2/32") + "\n" +
    "DNS = " + (.dns // "162.252.172.57, 149.154.159.92") + "\n\n" +
    "[Peer]\n" +
    "PublicKey = " + .publicKey + "\n" +
    "AllowedIPs = 0.0.0.0/0, ::/0\n" +
    "Endpoint = " + .endpoint
  '
}

# ─── provider_health_check ─────────────────────────────────────────────────

provider_health_check() {
  local token
  token="$(_ss_token)" || return 1
  curl -sf \
    -H "Authorization: Bearer $token" \
    "$SURFSHARK_API/v1/server" \
    -o /dev/null
}

# ─── provider_cleanup ──────────────────────────────────────────────────────

provider_cleanup() {
  return 0
}
