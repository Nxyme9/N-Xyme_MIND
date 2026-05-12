#!/usr/bin/env bash
# Windscribe Provider Plugin
# Manual config files only.

set -euo pipefail

PROVIDER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIGS_DIR="$PROVIDER_DIR/configs"

provider_info() {
  cat <<'EOF'
{"name":"windscribe","requires_auth":false,"auth_type":"config_file","max_connections":0,"protocol":"wireguard"}
EOF
}

provider_authenticate() {
  echo '{"authenticated":true}' > "$PROVIDER_DIR/auth_state.json"
  return 0
}

provider_list_servers() {
  [[ -d "$CONFIGS_DIR" ]] || { echo '[]'; return 0; }
  for f in "$CONFIGS_DIR"/*.conf; do
    [[ -f "$f" ]] || continue
    jq -n --arg id "$(basename "$f" .conf)" '{id:$id, name:$id, country:"XX", city:"unknown"}'
  done | jq -s '.'
}

provider_generate_config() {
  local server_id="${1:?server_id required}"
  if [[ -f "$CONFIGS_DIR/${server_id}.conf" ]]; then
    cat "$CONFIGS_DIR/${server_id}.conf"
    return 0
  fi
  echo "{\"error\":\"${server_id}.conf not found\"}" >&2
  return 1
}

provider_health_check() {
  [[ -d "$CONFIGS_DIR" ]] && compgen -G "$CONFIGS_DIR/*.conf" > /dev/null
}

provider_cleanup() { return 0; }
