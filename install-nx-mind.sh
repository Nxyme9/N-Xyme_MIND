#!/bin/bash
# N-Xyme MIND - Proper Installation Script
# Industry standard - no symlinks, proper PATH

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/nx-mind/bin"

echo "🚀 Installing N-Xyme MIND..."

# Create installation directory
mkdir -p "$INSTALL_DIR"

# Copy the main script (NOT symlink - actual file)
cp "$SCRIPT_DIR/nx_mind.py" "$INSTALL_DIR/nx_mind.py"
chmod +x "$INSTALL_DIR/nx_mind.py"

# Create executable wrapper with proper PYTHONPATH
cat > "$INSTALL_DIR/nx-mind" << 'EOF'
#!/bin/bash
# N-Xyme MIND Launcher
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# Go back to actual project directory to find packages
PROJECT_DIR="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
cd "$PROJECT_DIR"
PYTHONPATH="$PROJECT_DIR" exec python3 "$SCRIPT_DIR/nx_mind.py" "$@"
EOF
chmod +x "$INSTALL_DIR/nx-mind"

# Add to PATH in shell rc
SHELL_RC=""
if [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
elif [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
fi

# Check if already in PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo "" >> "$SHELL_RC"
    echo "# N-Xyme MIND" >> "$SHELL_RC"
    echo "export PATH=\"\$HOME/.local/nx-mind/bin:\$PATH\"" >> "$SHELL_RC"
    echo "✅ Added to PATH in $SHELL_RC"
    echo "   Run: source $SHELL_RC"
fi

echo ""
echo "✅ N-Xyme MIND installed to: $INSTALL_DIR"
echo ""
echo "Usage:"
echo "  nx-mind \"task description\""
echo "  nx-mind --interactive"
echo "  nx-mind --help"
echo ""
echo "To use now, run:"
echo "  export PATH=\"\$HOME/.local/nx-mind/bin:\$PATH\""
echo "  nx-mind \"hello world\""