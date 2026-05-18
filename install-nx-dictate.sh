#!/usr/bin/env bash
set -euo pipefail

# N-Xyme Dictate installer — QoL autostart + config
SERVICE_NAME="nx-dictate"
SERVICE_SRC="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/services/nx-dictate/nx-dictate.service"
SERVICE_DST="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/nx-dictate.service"

echo "=== N-Xyme Dictate Installer ==="
echo ""

# 1. Verify venv
if [ ! -f "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/venv/bin/python" ]; then
  echo "❌ Virtual env not found at /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/venv/"
  exit 1
fi

# 2. Install edge-tts if missing
echo "📦 Checking dependencies..."
/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/venv/bin/python -c "import edge_tts" 2>/dev/null || {
  echo "   Installing edge-tts..."
  /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/venv/bin/pip install edge-tts
}
echo "   ✅ Dependencies OK"

# 3. Check CUDA
echo "🔍 Checking GPU..."
/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/venv/bin/python -c "
import torch
if torch.cuda.is_available():
    print(f'   ✅ CUDA: {torch.cuda.get_device_name(0)} ({torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB)')
else:
    print('   ⚠️  CUDA not available — will use CPU')
"

# 4. Check mic
echo "🎤 Checking microphones..."
/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/venv/bin/python -m nx_dictate --list-devices 2>/dev/null
echo ""

# 5. Check injection backend
echo "⌨️ Checking text injection..."
for cmd in ydotool wtype xdotool; do
  if which $cmd &>/dev/null; then
    echo "   ✅ $cmd available"
  fi
done

# 6. Install systemd user service
echo ""
echo "⚙️  Installing systemd user service..."
mkdir -p "$(dirname "$SERVICE_DST")"
cp "$SERVICE_SRC" "$SERVICE_DST"
systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"
echo "   ✅ Service installed: $SERVICE_DST"

# 7. Enable lingering (allows user services to run without login)
echo "🔓 Enabling linger for $USER..."
sudo loginctl enable-linger "$USER" 2>/dev/null || true
echo "   ✅ Linger enabled"

# 8. Test run (download model if needed)
echo ""
echo "🚀 Testing voice dictation (first run downloads model)..."
echo "   Press Ctrl+C after 5 seconds if you don't want to test now."
echo ""
/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/venv/bin/python -m nx_dictate --model large-v3 --backend ydotool --no-tray &
PID=$!
sleep 5
kill $PID 2>/dev/null || true

echo ""
echo "=== ✅ Installation Complete ==="
echo ""
echo "Commands:"
echo "  Start now:   python -m nx_dictate --model large-v3 --backend ydotool"
echo "  Start with Scarlett 2i2: python -m nx_dictate --device 10 --model large-v3 --backend ydotool"  
echo "  Hold-to-talk: python -m nx_dictate --hold 'right ctrl' --model large-v3 --backend ydotool"
echo "  Start via systemd: systemctl --user start nx-dictate"
echo "  Auto-start: systemctl --user enable nx-dictate"
echo "  View logs: journalctl --user -u nx-dictate -f"
echo "  List devices: python -m nx_dictate --list-devices"
