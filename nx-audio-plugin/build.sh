#!/bin/bash
# Build script for N-Xyme Audio Bitwig Extension
# Requires: Java 17+, Maven

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "Building N-Xyme Audio Plugin..."

# Check Java
if ! command -v java &> /dev/null; then
    echo "ERROR: Java not found. Please install Java 17+"
    exit 1
fi

# Check Maven
if ! command -v mvn &> /dev/null; then
    echo "ERROR: Maven not found. Please install Maven"
    exit 1
fi

# Compile
echo "Compiling..."
mvn clean package -DskipTests

# Check output
if [ -f "target/N-XymeAudio.jar" ]; then
    echo "Build successful!"
    echo ""
    echo "To install to Bitwig Studio:"
    echo "  1. Copy target/N-XymeAudio.jar to ~/Bitwig Studio/Extensions/"
    echo "  2. Rename to N-XymeAudio.bwextension"
    echo "  3. Restart Bitwig Studio"
    echo ""
    echo "Or use the bundled .bwextension format:"
    echo "  mvn package -D packaging=bwextension"
else
    echo "Build failed. Check errors above."
    exit 1
fi