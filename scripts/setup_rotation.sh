#!/usr/bin/env bash
# OpenCode Auto-Rotation Setup
# Run this to enable automatic key rotation for OpenCode

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER="$SCRIPT_DIR/opencode_wrapper.py"
ROTATOR="$SCRIPT_DIR/key_rotator_v3.py"

# Create shell function for opencode
opencode_wrapper() {
    python3 "$WRAPPER" "$@"
}

# Export for subshells
export -f opencode_wrapper 2>/dev/null || true

# Show status
echo "=========================================="
echo "🟢 OPENCODE AUTO-ROTATION ENABLED"
echo "=========================================="
echo ""
echo "Commands:"
echo "  opencode [args]     # Auto-rotates on rate limits"
echo "  python $ROTATOR status     # Show key/model status"
echo "  python $ROTATOR health    # Health check"
echo "  python $ROTATOR test      # Test rotation"
echo ""
echo "Current state:"
python3 "$ROTATOR" status | head -20
echo ""
echo "To use in current shell, run:"
echo "  alias opencode='python3 $WRAPPER'"
echo ""
echo "Or add to ~/.bashrc for persistence:"
echo "  echo \"alias opencode='python3 $WRAPPER'\" >> ~/.bashrc"
echo "=========================================="
