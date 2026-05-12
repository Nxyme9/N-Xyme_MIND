#!/bin/bash
# Quick setup for N-Xyme Audio Plugin
# Run this on your machine with Bitwig installed

echo "=== N-Xyme Audio Plugin Setup ==="
echo ""

# Check if we can build
if command -v java &> /dev/null && command -v mvn &> /dev/null; then
    echo "✓ Java and Maven found, building..."
    cd "$(dirname "$0")/nx-audio-plugin"
    ./build.sh
else
    echo "✗ Java/Maven not found"
    echo ""
    echo "To build the plugin, install:"
    echo "  - Java 17+: https://adoptium.net/"
    echo "  - Maven: https://maven.apache.org/download.cgi"
    echo ""
    echo "Then run: cd nx-audio-plugin && ./build.sh"
    echo ""
    echo "After building, copy to Bitwig:"
    echo "  cp target/N-XymeAudio.jar ~/Bitwig\\ Studio/Extensions/N-XymeAudio.bwextension"
fi