#!/usr/bin/env bash
# ProtonVPN Provider Plugin
# No programmatic API — uses pre-downloaded .conf files or protonvpn-wg-confgen CLI.

set -euo pipefail

PROVIDER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIGS_DIR="$PROVIDER_DIR/configs"

# ─── provider_info ──────────────────────────────────────────────────────────

provider_info() {
  cat <<'EOF'
{
  "name": "protonvpn",
  "requires_auth": false,
  "auth_type": "config_file",
  "max_connections": 10,
  "protocol": "wireguard"
}
EOF
}

# ─── provider_authenticate ──────────────────────────────────────────────────

provider_authenticate() {
  # Check for config files or CLI tool
  if [[ -d "$CONFIGS_DIR" ]] && compgen -G "$CONFIGS_DIR/*.conf" > /dev/null; then
    jq -n '{authenticated:true, mode:"config_files", count:0}' \
      > "$PROVIDER_DIR/auth_state.json"
    echo "ProtonVPN: found config files in configs/" >&2
    return 0
  fi

  if command -v protonvpn-wg-confgen &>/dev/null; then
    jq -n '{authenticated:true, mode:"cli"}' \
      > "$PROVIDER_DIR/auth_state.json"
    echo "ProtonVPN: protonvpn-wg-confgen available" >&2
    return 0
  fi

  echo '{"error":"no .conf files in configs/ and protonvpn-wg-confgen not found"}' >&2
  return 1
}

# ─── provider_list_servers ──────────────────────────────────────────────────

provider_list_servers() {
  local servers="[]"

  if [[ -d "$CONFIGS_DIR" ]]; then
    servers=$(for f in "$CONFIGS_DIR"/*.conf; do
      [[ -f "$f" ]] || continue
      local name
      name=$(basename "$f" .conf)
      local country city
      country=$(grep -m1 '^# Country:' "$f" 2>/dev/null | sed 's/^# Country: *//' || echo "XX")
      city=$(grep -m1 '^# City:' "$f" 2>/dev/null | sed 's/^# City: *//' || echo "$name")

      jq -n \
        --arg id "$name" \
        --arg nm "$name" \
        --arg co "$country" \
        --arg ci "$city" \
        '{id:$id, name:$nm, country:$co, city:$ci}'
    done | jq -s '.')
  fi

  echo "$servers"
}

# ─── provider_generate_config ──────────────────────────────────────────────

provider_generate_config() {
  local server_id="${1:?server_id required}"

  if [[ -f "$CONFIGS_DIR/${server_id}.conf" ]]; then
    cat "$CONFIGS_DIR/${server_id}.conf"
    return 0
  fi

  echo "{\"error\":\"config ${server_id}.conf not found in configs/\"}" >&2
  return 1
}

# ─── provider_health_check ─────────────────────────────────────────────────

provider_health_check() {
  if [[ -d "$CONFIGS_DIR" ]] && compgen -G "$CONFIGS_DIR/*.conf" > /dev/null; then
    return 0
  fi
  if command -v protonvpn-wg-confgen &>/dev/null; then
    return 0
  fi
  return 1
}

# ─── provider_cleanup ──────────────────────────────────────────────────────

provider_cleanup() {
  return 0
}
