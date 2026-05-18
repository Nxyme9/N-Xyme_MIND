#!/usr/bin/env bash
set -euo pipefail

echo "=== N-Xyme MIND Setup ==="

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3.14+ required"
    exit 1
fi

# 2. Create venv
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

# 3. Install deps
pip install --upgrade pip
pip install numpy torch transformers sentence-transformers sounddevice pywhispercpp silero-vad pynvml

# 4. Check Mojo
if ! command -v mojo &> /dev/null; then
    echo "WARNING: Mojo not found. Install from https://modular.com/mojo"
    echo "Then run: mojo build services/mojo/src/main.mojo -o bins/nx-engine"
else
    echo "Mojo $(mojo --version) found"
fi

# 5. Create bins dir
mkdir -p bins

echo "=== Setup complete ==="
echo "Run: source .venv/bin/activate"