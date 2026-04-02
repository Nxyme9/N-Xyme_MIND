#!/usr/bin/env bash
# N-Xyme Catalyst Install Configs Script
# Copies configuration files to user directories

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../configs/opencode/plugins"
DEST_DIR="$HOME/.config/opencode/plugins"

echo "Installing OpenCode plugin configs..."

# Create destination directory if it doesn't exist
mkdir -p "$DEST_DIR"
echo "Created directory: $DEST_DIR"

# Copy all .json files from source to destination
for file in "$SOURCE_DIR"/*.json; do
    if [ -f "$file" ]; then
        cp "$file" "$DEST_DIR/"
        echo "Copied $(basename "$file") to $DEST_DIR/"
    fi
done

echo "Configuration installation complete."