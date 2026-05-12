#!/usr/bin/env bash
# Provider Plugin Template
# Every provider MUST implement these functions.
# Copy this directory, rename, and fill in the implementations.

set -euo pipefail

PROVIDER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ─── provider_info ──────────────────────────────────────────────────────────
# Returns JSON with provider metadata.
# Required fields: name, requires_auth, auth_type, max_connections, protocol
provider_info() {
  cat <<'EOF'
{
  "name": "template",
  "requires_auth": true,
  "auth_type": "none",
  "max_connections": 1,
  "protocol": "wireguard"
}
EOF
}

# ─── provider_authenticate ──────────────────────────────────────────────────
# Authenticate with the provider.
# Reads credentials from $PROVIDER_DIR/config.json
# Writes auth state to $PROVIDER_DIR/auth_state.json
# Returns 0 on success, 1 on failure.
provider_authenticate() {
  echo '{"error": "provider_authenticate not implemented"}' >&2
  return 1
}

# ─── provider_list_servers ──────────────────────────────────────────────────
# Returns a JSON array of available servers.
# Each server object MUST have at least: id, name, country, city
provider_list_servers() {
  echo '[]'
}

# ─── provider_generate_config ──────────────────────────────────────────────
# Generates a WireGuard config for the given server_id.
# Writes config to stdout.
# Returns 0 on success, 1 on failure.
provider_generate_config() {
  local server_id="${1:?server_id required}"
  echo '{"error": "provider_generate_config not implemented"}' >&2
  return 1
}

# ─── provider_health_check ─────────────────────────────────────────────────
# Checks if the provider is healthy and authenticated.
# Returns 0 if healthy, 1 if not.
provider_health_check() {
  if [[ -f "$PROVIDER_DIR/auth_state.json" ]]; then
    return 0
  fi
  return 1
}

# ─── provider_cleanup ──────────────────────────────────────────────────────
# Optional cleanup on shutdown. Remove temp files, revoke tokens, etc.
provider_cleanup() {
  return 0
}
