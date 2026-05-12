#!/bin/bash
###############################################################################
# ADHD Dolphin Service Menu - Right-click to run any script
# Installs into ~/.local/share/kio_desktop/ for Dolphin context menu
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MENU_DIR="$HOME/.local/share/kio_desktop"

install_service_menu() {
    log "Installing Dolphin context menu..."
    
    mkdir -p "$MENU_DIR"
    
    cat > "$MENU_DIR/adhd-scripts.desktop" << 'EOF'
[Desktop Entry]
Type=Service
Name=🧠 ADHD Scripts
Icon=utilities-system-monitor
MimeType=application/x-desktop;text/plain
X-KDE-Priority=TopLevel
X-KDE-SortOrder=1

[Desktop Entry]
Type=Path
Actions=adhd-task;adhd-pomodoro;adhd-notes;adhd-focus;adhd-presets;adhd-session

Name=🧠 ADHD Scripts

[Desktop Entry]
Name=📋 Task Launcher (Max 3)
Exec=/home/nxyme/.local/bin/adhd-task-launcher.sh
Icon=task
X-KDE-Submenu=🧠 ADHD Scripts

[Desktop Entry]
Name=🍅 Pomodoro Timer
Exec=/home/nxyme/.local/bin/adhd-pomodoro.sh
Icon=clock
X-KDE-Submenu=🧠 ADHD Scripts

[Desktop Entry]
Name=📝 Quick Notes
Exec=/home/nxyme/.local/bin/adhd-quick-note.sh
Icon=text-plain
X-KDE-Submenu=🧠 ADHD Scripts

[Desktop Entry]
Name=🎯 Toggle Focus Mode
Exec=/home/nxyme/.local/bin/adhd-focus.sh toggle
Icon=focusmode
X-KDE-Submenu=🧠 ADHD Scripts

[Desktop Entry]
Name=⚡ System Presets
Exec=/home/nxyme/.local/bin/adhd-presets.sh
Icon=preferences-system
X-KDE-Submenu=🧠 ADHD Scripts

[Desktop Entry]
Name=💾 Save Session
Exec=/home/nxyme/.local/bin/adhd-session-save.sh
Icon=document-save
X-KDE-Submenu=🧠 ADHD Scripts

[Desktop Entry]
Name=🔒 Focus Hide All
Exec=/home/nxyme/.local/bin/adhd-focus-hide.sh
Icon=lock
X-KDE-Submenu=🧠 ADHD Scripts

[Desktop Entry]
Name=🚀 Quick Launch
Exec=/home/nxyme/.local/bin/adhd-app-launcher.sh
Icon=launcher
X-KDE-Submenu=🧠 ADHD Scripts

[Desktop Entry]
Name=🔔 Break Reminder
Exec=/home/nxyme/.local/bin/adhd-break-reminder.sh start
Icon=bell
X-KDE-Submenu=🧠 ADHD Scripts

[Desktop Entry]
Name=🎉 Celebrate
Exec=/home/nxyme/.local/bin/adhd-celebrate.sh
Icon=trophy
X-KDE-Submenu=🧠 ADHD Scripts

[Desktop Entry]
Name=⚡ Energy Mode
Exec=/home/nxyme/.local/bin/adhd-energy-mode.sh
Icon=energy
X-KDE-Submenu=🧠 ADHD Scripts

[Desktop Entry]
Name=🔥 Daily Check-in
Exec=/home/nxyme/.local/bin/adhd-accountability.sh
Icon=football-green
X-KDE-Submenu=🧠 ADHD Scripts
EOF

    kbuildsycoca5 2>/dev/null || true
    
    log_success "Dolphin context menu installed!"
    log "Right-click anywhere in Dolphin to see '🧠 ADHD Scripts'"
}

remove_service_menu() {
    rm -f "$MENU_DIR/adhd-scripts.desktop"
    kbuildsycoca5 2>/dev/null || true
    log_success "Service menu removed"
}

case "$1" in
    install)
        install_service_menu
        ;;
    remove)
        remove_service_menu
        ;;
    *)
        install_service_menu
        ;;
esac