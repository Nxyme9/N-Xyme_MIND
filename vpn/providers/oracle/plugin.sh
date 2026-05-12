#!/usr/bin/env bash
# Oracle Cloud Provider Plugin
# Starts SSH -D SOCKS5 tunnels to Oracle Cloud VMs.

set -euo pipefail

PROVIDER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$PROVIDER_DIR/.pids"

# ─── provider_info ──────────────────────────────────────────────────────────

provider_info() {
  cat <<'EOF'
{
  "name": "oracle",
  "requires_auth": false,
  "auth_type": "ssh_key",
  "max_connections": 0,
  "protocol": "ssh_socks5"
}
EOF
}

# ─── provider_authenticate ──────────────────────────────────────────────────

provider_authenticate() {
  echo '{"authenticated":true}' > "$PROVIDER_DIR/auth_state.json"
  return 0
}

# ─── provider_list_servers ──────────────────────────────────────────────────

provider_list_servers() {
  if [[ ! -f "$PROVIDER_DIR/config.json" ]]; then
    echo '[]'
    return 0
  fi

  jq '[.vms[] | {
    id: .name,
    name: .name,
    country: "XX",
    city: "unknown",
    ssh_host: .host,
    ssh_user: .user,
    ssh_key: .key,
    socks_port: .socks_port
  }]' "$PROVIDER_DIR/config.json"
}

# ─── provider_generate_config ──────────────────────────────────────────────

provider_generate_config() {
  local server_id="${1:?server_id required}"

  if [[ ! -f "$PROVIDER_DIR/config.json" ]]; then
    echo '{"error":"config.json not found"}' >&2
    return 1
  fi

  local vm
  vm=$(jq -r --arg sid "$server_id" '.vms[] | select(.name == $sid)' "$PROVIDER_DIR/config.json")

  if [[ -z "$vm" ]]; then
    echo "{\"error\":\"VM $server_id not found in config.json\"}" >&2
    return 1
  fi

  local host user key socks_port
  host=$(echo "$vm" | jq -r '.host')
  user=$(echo "$vm" | jq -r '.user')
  key=$(echo "$vm" | jq -r '.key')
  socks_port=$(echo "$vm" | jq -r '.socks_port // 1080')

  mkdir -p "$PID_DIR"

  # Start SSH SOCKS5 tunnel in background
  ssh -f -N -D "127.0.0.1:$socks_port" \
    -o StrictHostKeyChecking=no \
    -o ServerAliveInterval=60 \
    -o ServerAliveCountMax=3 \
    -i "$key" \
    "${user}@${host}" &

  local pid=$!
  echo "$pid" > "$PID_DIR/${server_id}.pid"

  cat <<EOF
[Oracle SOCKS5 Tunnel]
Host = $host
User = $user
SOCKS5 = 127.0.0.1:$socks_port
PID = $pid
EOF
}

# ─── provider_health_check ─────────────────────────────────────────────────

provider_health_check() {
  if [[ -d "$PID_DIR" ]]; then
    for pidfile in "$PID_DIR"/*.pid; do
      [[ -f "$pidfile" ]] || continue
      local pid
      pid=$(cat "$pidfile")
      if kill -0 "$pid" 2>/dev/null; then
        return 0
      fi
    done
  fi
  return 1
}

# ─── provider_cleanup ──────────────────────────────────────────────────────

provider_cleanup() {
  if [[ -d "$PID_DIR" ]]; then
    for pidfile in "$PID_DIR"/*.pid; do
      [[ -f "$pidfile" ]] || continue
      local pid
      pid=$(cat "$pidfile")
      kill "$pid" 2>/dev/null || true
      rm -f "$pidfile"
    done
  fi
  return 0
}
