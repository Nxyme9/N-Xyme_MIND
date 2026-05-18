#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# build-agent.sh — Compile a per-agent Mojo binary with baked-in identity
#
# Usage:
#   ./scripts/build-agent.sh <agent_name> [output_binary]
#
# Builds a compiled agent binary with the agent's name baked in at compile time.
# The binary reads compile patterns from memory on startup.
#
# Examples:
#   ./scripts/build-agent.sh "Hephaestus - Builder" bins/hephaestus-agent
#   ./scripts/build-agent.sh "Catalyst" bins/catalyst-agent
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

AGENT_NAME="$1"
OUTPUT="${2:-bins/$(echo "$AGENT_NAME" | tr '[:upper:]' '[:lower:]' | tr -s ' ' '-' | tr -s '_' '-')-agent}"
MOJO="${MOJO:-$HOME/.local/bin/mojo}"
TEMPLATE="agents/templates/compiled-agent.mojo"
BUILD_DIR="$(dirname "$TEMPLATE")/build"

mkdir -p "$BUILD_DIR"

# Sanitize agent name for use in Mojo source
# Remove special chars, keep alphanumeric + spaces + hyphens
SANITIZED=$(echo "$AGENT_NAME" | sed 's/[^a-zA-Z0-9 _-]//g')

# Generate a build file with the agent name hardcoded
BUILD_FILE="$BUILD_DIR/$(echo "$AGENT_NAME" | tr -s ' ' '_' | tr -s '-' '_').mojo"

# Copy template and replace the comptime default
sed "s/comptime AGENT_NAME: String = \"unknown-agent\"/comptime AGENT_NAME: String = \"$SANITIZED\"/" \
  "$TEMPLATE" > "$BUILD_FILE"

echo "Building agent: $SANITIZED → $OUTPUT"

# Compile with feedback
START_MS=$(date +%s%3N)
if "$MOJO" build "$BUILD_FILE" -o "$OUTPUT" 2>&1; then
  END_MS=$(date +%s%3N)
  DURATION_MS=$(( END_MS - START_MS ))
  
  # Store compile feedback
  FEEDBACK=$(cat << JSONEOF
{"success":true,"source":"$TEMPLATE","binary":"$OUTPUT","errors":[],"warnings":[],"duration_ms":$DURATION_MS,"agent":"$SANITIZED","task":"build-agent"}
JSONEOF
  )
  echo "$FEEDBACK" | python3 "$(dirname "$0")/compile-pattern-memory.py" store > /dev/null 2>&1 || true
  
  echo "✅ Built $SANITIZED in ${DURATION_MS}ms"
  echo "   Binary: $OUTPUT"
  echo "   Size: $(stat -c%s "$OUTPUT") bytes"
else
  echo "❌ Build FAILED for $SANITIZED"
  exit 1
fi
