#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

show_menu() {
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║           N-XYME DICTATE - BLEEDING EDGE EDITION              ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "  1. Start Dictation (mouse buttons)"
    echo "  2. Start WebSocket Server"
    echo "  3. Run Benchmark"
    echo "  4. Quick Test (3 sec record)"
    echo "  5. Install Dependencies"
    echo "  6. View Logs"
    echo "  7. Enable Auto-start (systemd)"
    echo "  8. Quit"
    echo ""
}

install_deps() {
    echo "Installing dependencies..."
    for cmd in wl-copy wtype ydotool; do
        if ! command -v $cmd &> /dev/null; then
            echo "  Installing $cmd..."
            if command -v apt-get &> /dev/null; then
                sudo apt-get install -y wl-clipboard wtype xdotool || true
            elif command -v pacman &> /dev/null; then
                sudo pacman -S --noconfirm wl-clipboard wtype xdotool || true
            fi
        fi
    done
    echo "  Installing Python packages..."
    pip install faster-whisper websockets sounddevice numpy evdev 2>/dev/null || true
    echo "✓ Dependencies ready"
}

start_dictation() {
    echo "Starting N-Xyme Dictate..."
    cd "$SCRIPT_DIR"
    ./nxyme-dictate.sh
}

start_ws() {
    echo "Starting WebSocket server on port 8765..."
    cd "$SCRIPT_DIR"
    python3 server/main.py
}

run_benchmark() {
    echo "Running benchmark..."
    cd "$SCRIPT_DIR"
    python3 scripts/benchmark_dictate.py
}

quick_test() {
    echo "Quick test (3 seconds)..."
    cd "$SCRIPT_DIR"
    python3 scripts/quick_dictate_test.py
}

view_logs() {
    journalctl --user -f -u nxyme-dictate 2>/dev/null || echo "No systemd logs"
}

enable_autostart() {
    echo "Enabling auto-start..."
    mkdir -p ~/.config/systemd/user
    cp "$SCRIPT_DIR/nxyme-dictate.service" ~/.config/systemd/user/
    systemctl --user daemon-reload
    systemctl --user enable --now nxyme-dictate
    echo "✓ Auto-start enabled"
}

while true; do
    show_menu
    read -p "Select option [1-8]: " choice
    
    case $choice in
        1) start_dictation ;;
        2) start_ws ;;
        3) run_benchmark ;;
        4) quick_test ;;
        5) install_deps ;;
        6) view_logs ;;
        7) enable_autostart ;;
        8) echo "Goodbye!"; exit 0 ;;
        *) echo "Invalid option" ;;
    esac
    echo ""
done