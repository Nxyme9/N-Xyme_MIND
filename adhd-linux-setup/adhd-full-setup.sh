#!/bin/bash
###############################################################################
# ADHD Full System Adaptation - 100% Frictionless Workflow
# 
# Adapts EVERYTHING: KDE, Dolphin, Terminal, Browser, Fonts, Notifications
# ONE-CLICK REVERSIBLE
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/adhd-full-backup"
LOG_FILE="$SCRIPT_DIR/adhd-full-setup.log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date)]${NC} $1" | tee -a "$LOG_FILE"; }
log_success() { echo -e "${GREEN}✓${NC} $1" | tee -a "$LOG_FILE"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1" | tee -a "$LOG_FILE"; }

backup_config() {
    log "Creating full system backup..."
    mkdir -p "$BACKUP_DIR/config"
    cp -r "$HOME/.config/kdeglobals" "$BACKUP_DIR/config/" 2>/dev/null || true
    cp -r "$HOME/.config/kwinrc" "$BACKUP_DIR/config/" 2>/dev/null || true
    cp -r "$HOME/.config/dolphinrc" "$BACKUP_DIR/config/" 2>/dev/null || true
    cp -r "$HOME/.config/plasmanotifyrc" "$BACKUP_DIR/config/" 2>/dev/null || true
    cp -r "$HOME/.config/alacritty" "$BACKUP_DIR/config/" 2>/dev/null || true
    cp -r "$HOME/.config/kcminputrc" "$BACKUP_DIR/config/" 2>/dev/null || true
    cp -r "$HOME/.config/katerc" "$BACKUP_DIR/config/" 2>/dev/null || true
    echo "$(date)" > "$BACKUP_DIR/backup-timestamp.txt"
    log_success "Backup complete: $BACKUP_DIR"
}

restore_config() {
    log "Restoring from backup..."
    [ ! -d "$BACKUP_DIR" ] && log_error "No backup found!" && exit 1
    cp -r "$BACKUP_DIR/config/"* "$HOME/.config/" 2>/dev/null || true
    log_success "Restore complete!"
}

install_adaptations() {
    log "=========================================="
    log "🚀 INSTALLING 100% ADHD ADAPTATIONS"
    log "=========================================="
    
    ###########################################################################
    # 1. FONTS - Increase for ADHD readability
    ###########################################################################
    log ""
    log "=== 1. Font Adaptations ==="
    
    mkdir -p "$HOME/.config/fontconfig"
    
    cat > "$HOME/.config/fontconfig/fonts.conf" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <match target="font">
    <edit name="antialias" mode="assign"><bool>true</bool></edit>
    <edit name="hinting" mode="assign"><bool>true</bool></edit>
    <edit name="rgba" mode="assign"><const>rgb</const></edit>
    <edit name="lcdfilter" mode="assign"><const>lcddefault</const></edit>
  </match>
  <match target="font" name="Noto Sans">
    <edit name="pixelsize" mode="assign"><double>12</double></edit>
    <edit name="weight" mode="assign"><int>80</int></edit>
  </match>
</fontconfig>
EOF
    
    kwriteconfig5 --file kdeglobals --group General --key "font" "Noto Sans,12,-1,5,50,0,0,0,0,0"
    kwriteconfig5 --file kdeglobals --group General --key "menuFont" "Noto Sans,11,-1,5,50,0,0,0,0,0"
    kwriteconfig5 --file kdeglobals --group General --key "toolBarFont" "Noto Sans,10,-1,5,50,0,0,0,0,0"
    
    kcminputrc_update() {
        kwriteconfig5 --file kcminputrc --group Mouse --key cursorSize 42
    }
    kcminputrc_update
    
    log_success "Fonts: Increased to 12pt, cursor to 42px"
    
    ###########################################################################
    # 2. DOLPHIN - Simplify for ADHD
    ###########################################################################
    log ""
    log "=== 2. Dolphin (File Manager) Adaptations ==="
    
    mkdir -p "$HOME/.config"
    
    cat > "$HOME/.config/dolphinrc" << 'EOF'
[General]
Version=202
LockPanels=true

[KFileDialog Settings]
Places Icons Auto-resize=false
Places Icons Static Size=24
Breadcrumb Navigation=true
Show hidden files=false
Sort by=Name
Sort directories first=true
View Style=DetailView
DetailViewIconSize=24

[MainWindow]
MenuBar=Disabled
ShowStatusBar=true

[PreviewSettings]
Plugins=none

[Search]
Location=Everywhere

[CompactMode]
PreviewSize=22

[Trash]
ConfirmDelete=true
EOF

    mkdir -p "$HOME/.config/kdeeventsrc"
    echo "[Dolphin]
DeletedFilesStrategy=moveToTrash" > "$HOME/.config/kdeeventsrc/dolphinrc"
    
    log_success "Dolphin: Simplified, confirm delete, larger icons"
    
    ###########################################################################
    # 3. TERMINAL (Alacritty) - Reduce visual noise
    ###########################################################################
    log ""
    log "=== 3. Terminal Adaptations ==="
    
    cat > "$HOME/.config/alacritty/alacritty.toml" << 'EOF'
[env]
TERM = "xterm-256color"
WINIT_X11_SCALE_FACTOR = "1"

[window]
dynamic_padding = true
decorations = "full"
title = "Alacritty@ADHD"
opacity = 0.95
decorations_theme_variant = "Dark"

[window.dimensions]
columns = 100
lines = 35

[window.class]
instance = "Alacritty"
general = "Alacritty"

[scrolling]
history = 10000
multiplier = 5

[font]
size = 12.0

[colors]
draw_bold_text_with_bright_colors = true

[colors.primary]
background = "0x1E1E2E"
foreground = "0xCDD6F4"

[colors.normal]
black = "0x45475A"
red = "0xF38BA8"
green = "0xA6E3A1"
yellow = "0xF9E2AF"
blue = "0x89B4FA"
magenta = "0xF5C2E7"
cyan = "0x94E2D5"
white = "0xBAC2DE"

[colors.bright]
black = "0x585B70"
red = "0xF38BA8"
green = "0xA6E3A1"
yellow = "0xF9E2AF"
blue = "0x89B4FA"
magenta = "0xF5C2E7"
cyan = "0x94E2D5"
white = "0xA6ADC8"

[cursor]
style.block.blinking = "On"
style.block.shape = "Block"

[terminal]
shell.program = /usr/bin/fish
EOF

    log_success "Terminal: 12pt font, 95% opacity, more scrollback"
    
    ###########################################################################
    # 4. KATE - Text editor adaptations
    ###########################################################################
    log ""
    log "=== 4. Kate Editor Adaptations ==="
    
    cat > "$HOME/.config/katerc" << 'EOF'
[Basic]
Auto-Save=1
Auto-Save Interval=2
Font=Noto Sans Mono,11
Line Height=1.3

[Editor]
Bracket Matching=true
Word Wrap Marker=1
Show Tab Bar=true
Show Line Numbers=true
Dynamic Word Wrap=false

[Notifications]
DoNotShowAgain=showEditToolbar:toolbarStyle,showScrollbars:viewInterfaceScrollbars
EOF

    log_success "Kate: Auto-save every 2 min, larger font"
    
    ###########################################################################
    # 5. NOTIFICATIONS - Reduce to essentials
    ###########################################################################
    log ""
    log "=== 5. Notification Adaptations ==="
    
    cat > "$HOME/.config/plasmanotifyrc" << 'EOF'
[Applications][heroic]
Seen=true

[Notifications]
DoNotDisturb=false
DoNotDisturbWhenFullScreen=true
ExecuteDelay=8000
GroupingStrategy=category
HistoryLimit=3
MaxItems=2
NotificationFilter=true
PopupPosition=TopCenter
ShowNextToMouse=false
Sound=true
Volume=40
X-KDE-NextToMouse=false
EOF

    log_success "Notifications: Max 2, 8s delay, TopCenter, quieter"
    
    ###########################################################################
    # 6. WINDOW MANAGER (KWin) - Simplify
    ###########################################################################
    log ""
    log "=== 6. KWin Adaptations ==="
    
    kwriteconfig5 --file kwinrc --group NightColor --key Active true
    kwriteconfig5 --file kwinrc --group NightColor --key NightTemperature 1600
    
    kwriteconfig5 --file kwinrc --group Windows --key AltTabSwitchApplications false
    kwriteconfig5 --file kwinrc --group Windows --key ClickRaise false
    
    kwriteconfig5 --file kwinrc --group Effect --key Blur true
    kwriteconfig5 --file kwinrc --group Effect --key Translucency false
    
    kwriteconfig5 --file kwinrc --group TabBox --key DesktopSwitching false
    kwriteconfig5 --file kwinrc --group TabBox --key HiddenPreviews true
    
    qdbus org.kde.KWin /KWin org.kde.KWin.reconfigure 2>/dev/null || true
    
    log_success "KWin: Night Color 1600K, simpler window switching"
    
    ###########################################################################
    # 7. PLASMA - Desktop adaptations
    ###########################################################################
    log ""
    log "=== 7. Plasma Desktop Adaptations ==="
    
    kwriteconfig5 --file kdeglobals --group KDE --key AnimationDurationFactor 0.15
    
    kwriteconfig5 --file kdeglobals --group Feedback --key AnimationDurationFactor 0.3
    kwriteconfig5 --file kdeglobals --group Feedback --key EffectEnabled true
    kwriteconfig5 --file kdeglobals --group Feedback --key Intensity 0.4
    
    kwriteconfig5 --file kdeglobals --group General --key ShowDeleteCommand false
    
    kwriteconfig5 --file kdeglobals --group "Colors:Selection" --key BackgroundNormal "71,173,214"
    kwriteconfig5 --file kdeglobals --group "Colors:Selection" --key ForegroundNormal "10,11,12"
    
    kwriteconfig5 --file kdeglobals --group "Colors:View" --key BackgroundNormal "22,25,37"
    kwriteconfig5 --file kdeglobals --group "Colors:View" --key ForegroundNormal "200,210,220"
    
    kwriteconfig5 --file kdeglobals --group "Colors:Window" --key BackgroundNormal "24,27,40"
    
    log_success "Plasma: Faster animations, higher contrast"
    
    ###########################################################################
    # 8. KEYBOARD - Optimize for 60% keyboard
    ###########################################################################
    log ""
    log "=== 8. Keyboard Adaptations ==="
    
    mkdir -p "$HOME/.config/autostart"
    
    cat > "$HOME/.config/autostart/adhd-keyboard-optimize.desktop" << 'EOF'
[Desktop Entry]
Comment=Keyboard optimization for ADHD workflow
Exec=/home/nxyme/.local/bin/adhd-keyboard-helper.sh
Icon=input-keyboard
Name=⌨️ Keyboard Helper
Type=Application
X-KDE-AutostartEnabled=true
EOF

    mkdir -p "$HOME/.local/bin"
    
    cat > "$HOME/.local/bin/adhd-keyboard-helper.sh" << 'EOF'
#!/bin/bash
xinput set-prop "9610:00073A74" "libinput Accel Speed" 0.3
xset r rate 250 40
EOF
    chmod +x "$HOME/.local/bin/adhd-keyboard-helper.sh"
    
    log_success "Keyboard: Faster repeat, mouse sensitivity"
    
    ###########################################################################
    # 9. MOUSE/POINTER - Larger for ADHD
    ###########################################################################
    log ""
    log "=== 9. Mouse/Pointer Adaptations ==="
    
    kwriteconfig5 --file kcminputrc --group Mouse --key cursorSize 48
    kwriteconfig5 --file kcminputrc --group Mouse --key doubleClickInterval 500
    kwriteconfig5 --file kcminputrc --group Mouse --key dragStartTime 400
    
    kwriteconfig5 --file kcminputrc --group "Libinput[9610][73][BY Tech Gaming Keyboard Mouse]" --key ScrollFactor 30
    kwriteconfig5 --file kcminputrc --group "Libinput[9610][73][BY Tech Gaming Keyboard Mouse]" --key AccelSpeed 0.4
    
    log_success "Mouse: 48px cursor, faster scroll, more responsive"
    
    ###########################################################################
    # 10. BRAVE BROWSER - ADHD optimizations
    ###########################################################################
    log ""
    log "=== 10. Browser (Brave) Adaptations ==="
    
    mkdir -p "$HOME/.config/BraveSoftware/Brave-Browser/default"
    
    cat > "$HOME/.config/BraveSoftware/Brave-Browser/default/Preferences.json.adhd" << 'EOF'
{
  "extensions": {
    "aomdlcjeipbnmcokehhlfjacdffnpkij": {}
  },
  "browser": {
    "clear_lose_for_testing": false,
    "download": {
      "open_pdf_in_system_reader": true,
      "prompt_for_download": true
    },
    "enable_spellchecking": true,
    "show_home_button": true,
    "tab_shortcuts_enabled": true
  },
  "profile": {
    "default_content_setting_values": {
      "notifications": 2
    }
  }
}
EOF

    cat > "$HOME/.local/bin/adhd-browser-reset.sh" << 'EOF'
#!/bin/bash
# Reduce browser cognitive load - simpler UI
xdotool key ctrl+shift+b 2>/dev/null || true
echo "Browser configured for reduced distractions"
EOF
    chmod +x "$HOME/.local/bin/adhd-browser-reset.sh"
    
    log_success "Browser: Simplified preferences ready"
    
    ###########################################################################
    # 11. AUTOSTART ADHD TOOLS
    ###########################################################################
    log ""
    log "=== 11. Auto-start ADHD Tools ==="
    
    mkdir -p "$HOME/.config/autostart"
    
    # ADHD Dashboard
    cat > "$HOME/.config/autostart/adhd-dashboard.desktop" << 'EOF'
[Desktop Entry]
Comment=ADHD Control Dashboard
Exec=/home/nxyme/.local/bin/adhd-dashboard.sh
Icon=utilities-system-monitor
Name=🧠 ADHD Control Center
Type=Application
X-KDE-AutostartEnabled=true
Categories=Utility;Accessibility;
EOF

    # Session saver
    [ -f "$HOME/.local/bin/adhd-session-save.sh" ] && cat > "$HOME/.config/autostart/adhd-session-save.desktop" << 'EOF'
[Desktop Entry]
Comment=Session auto-save
Exec=/home/nxyme/.local/bin/adhd-session-save.sh
Icon=document-save
Name=💾 Session Saver
Type=Application
X-KDE-AutostartEnabled=true
Categories=Utility;
EOF

    log_success "Auto-start: ADHD tools on login"
    
    ###########################################################################
    # 12. DESKTOP SHORTCUTS
    ###########################################################################
    log ""
    log "=== 12. Creating Desktop Shortcuts ==="
    
    mkdir -p "$HOME/Desktop"
    
    cat > "$HOME/Desktop/ADHD-Control.desktop" << 'EOF'
[Desktop Entry]
Comment=Open ADHD Dashboard
Exec=/home/nxyme/.local/bin/adhd-dashboard.sh
Icon=utilities-system-monitor
Name=🧠 ADHD Control Center
Type=Application
EOF

    cat > "$HOME/Desktop/Open-Files.desktop" << 'EOF'
[Desktop Entry]
Comment=Open Dolphin File Manager
Exec=dolphin
Icon=system-file-manager
Name=📁 File Manager
Type=Application
EOF

    cat > "$HOME/Desktop/Open-Terminal.desktop" << 'EOF'
[Desktop Entry]
Comment=Open Terminal
Exec=alacritty
Icon=utilities-terminal
Name=💻 Terminal
Type=Application
EOF

    log_success "Desktop shortcuts created"
    
    ###########################################################################
    # 13. KRUNNER - Faster app launching (critical for 60% keyboard)
    ###########################################################################
    log ""
    log "=== 13. KRunner Optimizations ==="
    
    kwriteconfig5 --file krunnerrc --group "General" --key "HistoryLength" 20
    kwriteconfig5 --file krunnerrc --group "General" --key "ShowRunningOnSingleClick" true
    kwriteconfig5 --file krunnerrc --group "General" --key "MaxItems" 15
    
    kwriteconfig5 --file krunnerrc --group "Plugin Priorities" --key "app" 1
    kwriteconfig5 --file krunnerrc --group "Plugin Priorities" --key "services" 1
    kwriteconfig5 --file krunnerrc --group "Plugin Priorities" --key "calculator" 1
    kwriteconfig5 --file krunnerrc --group "Plugin Priorities" --key "recentfiles" 1
    
    mkdir -p "$HOME/.local/bin"
    
    cat > "$HOME/.local/bin/adhd-krunner-boost.sh" << 'EOF'
#!/bin/bash
qdbus org.kde.krunner /App activate 2>/dev/null
xdotool key Super+Alt+Space 2>/dev/null || true
EOF
    chmod +x "$HOME/.local/bin/adhd-krunner-boost.sh"
    
    log_success "KRunner: More relevant results, faster access (Alt+Space)"
    
    ###########################################################################
    # 14. WORKSPACE - Simplify to 1 desktop
    ###########################################################################
    log ""
    log "=== 14. Workspace Simplification ==="
    
    kwriteconfig5 --file kwinrc --group Desktops --key Number 1
    kwriteconfig5 --file kwinrc --group Desktops --key Rows 1
    
    kwriteconfig5 --file kwinrc --group "Window Desktops" --key "AllDesktops" 1
    
    kwriteconfig5 --file kwinrc --group "Script-Activitymanager" --key "FocusFollowsMouse" true
    
    log_success "Workspace: Single desktop (no desktop switching confusion)"
    
    ###########################################################################
    # 15. CLIPBOARD MANAGER - Never lose links again
    ###########################################################################
    log ""
    log "=== 15. Clipboard Manager ==="
    
    mkdir -p "$HOME/.config/autostart"
    
    cat > "$HOME/.config/autostart/adhd-clipboard.desktop" << 'EOF'
[Desktop Entry]
Comment=Clipboard history manager
Exec=klipper
Icon=edit-paste
Name=📋 Clipboard History
Type=Application
X-KDE-AutostartEnabled=true
X-KDE-StartuplistId=klipper
EOF

    kwriteconfig5 --file klipperrc --group "General" --key "MaxClipItems" 50
    kwriteconfig5 --file klipperrc --group "General" --key "AutoSave" true
    kwriteconfig5 --file klipperrc --group "General" --key "IgnoreImages" false
    
    log_success "Clipboard: 50 items history, auto-save"
    
    ###########################################################################
    # 16. QUICK NOTE WIDGET - Always visible notes
    ###########################################################################
    log ""
    log "=== 16. Quick Notes Widget ==="
    
    cat > "$HOME/.local/bin/adhd-quick-note.sh" << 'EOF'
#!/bin/bash
NOTE_FILE="$HOME/.config/adhd-quick-notes.txt"
mkdir -p "$HOME/.config"

if [ ! -f "$NOTE_FILE" ]; then
    echo "" > "$NOTE_FILE"
fi

NOTE=$(zenity --text-info \
    --title="📝 Quick Notes" \
    --width=500 \
    --height=400 \
    --editable \
    --font="Noto Sans 12" \
    "$(cat $NOTE_FILE)" 2>/dev/null)

echo "$NOTE" > "$NOTE_FILE"
EOF
    chmod +x "$HOME/.local/bin/adhd-quick-note.sh"

    cat > "$HOME/Desktop/Quick-Notes.desktop" << 'EOF'
[Desktop Entry]
Comment=Open quick notes
Exec=/home/nxyme/.local/bin/adhd-quick-note.sh
Icon=text-plain
Name=📝 Quick Notes
Type=Application
EOF

    log_success "Quick Notes: One-click notes, desktop shortcut"
    
    ###########################################################################
    # 17. FOCUS MODE - Hide all but active app
    ###########################################################################
    log ""
    log "=== 17. Focus Mode (Hide All) ==="
    
    cat > "$HOME/.local/bin/adhd-focus-hide.sh" << 'EOF'
#!/bin/bash
FOCUS_LOCK="$HOME/.config/adhd-focus-lock"

if [ -f "$FOCUS_LOCK" ]; then
    rm -f "$FOCUS_LOCK"
    qdbus org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.showTaskManager 2>/dev/null
    qdbus org.kde.KWin /KWin org.kde.KWin.setShowingDesktop false 2>/dev/null
    notify-send "🔓 Focus Mode OFF" "All windows visible"
else
    touch "$FOCUS_LOCK"
    qdbus org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.hideTaskManager 2>/dev/null
    qdbus org.kde.KWin /KWin org.kde.KWin.setShowingDesktop true 2>/dev/null
    notify-send "🔒 Focus Mode ON" "Desktop cleared for focus"
fi
EOF
    chmod +x "$HOME/.local/bin/adhd-focus-hide.sh"

    cat > "$HOME/Desktop/Focus-Mode.desktop" << 'EOF'
[Desktop Entry]
Comment=Toggle focus mode
Exec=/home/nxyme/.local/bin/adhd-focus-hide.sh
Icon=focusmode
Name=🔒 Focus Mode Toggle
Type=Application
EOF

    log_success "Focus Mode: Hide all windows with one click"
    
    ###########################################################################
    # 18. ONE-CLICK APP LAUNCHER
    ###########################################################################
    log ""
    log "=== 18. One-Click App Launcher ==="
    
    cat > "$HOME/.local/bin/adhd-app-launcher.sh" << 'EOF'
#!/bin/bash
CHOICE=$(zenity --list \
    --title="🚀 Quick Launch" \
    --text="Select app to open:" \
    --column="App" \
    --height=400 \
    --width=350 \
    "📁 Files (Dolphin)" \
    "💻 Terminal (Alacritty)" \
    "🌐 Browser (Brave)" \
    "📝 Notes" \
    "📋 Clipboard" \
    "🎵 Music" \
    "🧠 ADHD Dashboard" \
    2>/dev/null)

case "$CHOICE" in
    "📁 Files (Dolphin)") dolphin & ;;
    "💻 Terminal (Alacritty)") alacritty & ;;
    "🌐 Browser (Brave)") brave-browser & ;;
    "📝 Notes") "$HOME/.local/bin/adhd-quick-note.sh" ;;
    "📋 Clipboard") qdbus org.kde.klipper /klipper showPopupMenu & ;;
    "🎵 Music") audacious & ;;
    "🧠 ADHD Dashboard") "$HOME/.local/bin/adhd-dashboard.sh" & ;;
esac
EOF
    chmod +x "$HOME/.local/bin/adhd-app-launcher.sh"

    cat > "$HOME/Desktop/App-Launcher.desktop" << 'EOF'
[Desktop Entry]
Comment=Quick app launcher
Exec=/home/nxyme/.local/bin/adhd-app-launcher.sh
Icon=launcher
Name="🚀 Quick Launch"
Type=Application
EOF

    log_success "App Launcher: One-click to any frequently used app"
    
    ###########################################################################
    # 19. GENTLE ACCOUNTABILITY - Check-in system
    ###########################################################################
    log ""
    log "=== 19. Gentle Accountability System ==="
    
    cat > "$HOME/.local/bin/adhd-accountability.sh" << 'EOF'
#!/bin/bash
ACCOUNTABILITY_DIR="$HOME/.config/adhd-accountability"
mkdir -p "$ACCOUNTABILITY_DIR"

LAST_CHECKIN="$ACCOUNTABILITY_DIR/last-checkin.txt"
STREAK_FILE="$ACCOUNTABILITY_DIR/streak.txt"

get_streak() {
    if [ -f "$STREAK_FILE" ]; then
        cat "$STREAK_FILE"
    else
        echo "0"
    fi
}

checkin() {
    TODAY=$(date +%Y-%m-%d)
    LAST=$(cat "$LAST_CHECKIN" 2>/dev/null)
    
    if [ "$LAST" != "$TODAY" ]; then
        STREAK=$(get_streak)
        STREAK=$((STREAK + 1))
        echo "$TODAY" > "$LAST_CHECKIN"
        echo "$STREAK" > "$STREAK_FILE"
        
        notify-send -u normal "🔥 $STREAK Day Streak!" "Great job! You've checked in $STREAK days in a row."
        
        zenity --info --title="🔥 $STREAK Day Streak!" \
            --text="Amazing! You're on a $STREAK day streak!\n\nKeep it going tomorrow 💪" 2>/dev/null
    else
        STREAK=$(get_streak)
        zenity --info --title="Already Checked In" \
            --text="You've already checked in today!\n\nCurrent streak: $STREAK days 🔥" 2>/dev/null
    fi
}

case "$1" in
    checkin) checkin ;;
    streak) 
        STREAK=$(get_streak)
        echo "🔥 Current streak: $STREAK days"
        ;;
    *) checkin ;;
esac
EOF
    chmod +x "$HOME/.local/bin/adhd-accountability.sh"

    cat > "$HOME/Desktop/Daily-Checkin.desktop" << 'EOF'
[Desktop Entry]
Comment=Daily accountability check-in
Exec=/home/nxyme/.local/bin/adhd-accountability.sh
Icon=football-green
Name=🔥 Daily Check-in
Type=Application
EOF

    log_success "Accountability: Daily check-in with streak tracking"
    
    ###########################################################################
    # 20. IMMEDIATE DOPAMINE - Celebration moments
    ###########################################################################
    log ""
    log "=== 20. Immediate Dopamine Celebrations ==="
    
    cat > "$HOME/.local/bin/adhd-celebrate.sh" << 'EOF'
#!/bin/bash
CELEBRATIONS=(
    "🎉 Amazing work!"
    "🚀 You're on fire!"
    "💪 Superb progress!"
    "🌟 Brilliant!"
    "🔥 On a roll!"
    "⭐ Brilliant execution!"
    "👏 Outstanding!"
    "🎯 Bullseye!"
)

RANDOM_CELEBRATION=${CELEBRATIONS[$((RANDOM % ${#CELEBRATIONS[@]}))]}

if [ "$1" = "silent" ]; then
    notify-send -u low "$RANDOM_CELEBRATION" "Keep going! You're doing great!"
else
    notify-send -u normal "$RANDOM_CELEBRATION" "Task completed! Celebrate this win! 🎊"
fi
EOF
    chmod +x "$HOME/.local/bin/adhd-celebrate.sh"

    cat > "$HOME/.local/bin/adhd-milestone.sh" << 'EOF'
#!/bin/bash
MILESTONE_FILE="$HOME/.config/adhd-milestones.txt"

add_milestone() {
    echo "$(date): $1" >> "$MILESTONE_FILE"
}

show_milestones() {
    if [ -f "$MILESTONE_FILE" ]; then
        zenity --text-info \
            --title="🏆 Your Milestones" \
            --width=500 \
            --height=400 \
            "$(tail -20 $MILESTONE_FILE)"
    else
        zenity --info --text="No milestones yet. Add your first win!" 2>/dev/null
    fi
}

case "$1" in
    add) add_milestone "$2" ;;
    show) show_milestones ;;
    *) add_milestone "Completed focus session" ;;
esac
EOF
    chmod +x "$HOME/.local/bin/adhd-milestone.sh"

    log_success "Dopamine: Random celebrations + milestone tracker"
    
    ###########################################################################
    # 21. ENERGY-AWARE DND - Auto Do Not Disturb
    ###########################################################################
    log ""
    log "=== 21. Energy-Aware Do Not Disturb ==="
    
    cat > "$HOME/.local/bin/adhd-energy-mode.sh" << 'EOF'
#!/bin/bash
ENERGY_FILE="$HOME/.config/adhd-energy-mode"

get_energy() {
    if [ -f "$ENERGY_FILE" ]; then
        cat "$ENERGY_FILE"
    else
        echo "normal"
    fi
}

set_energy() {
    echo "$1" > "$ENERGY_FILE"
    case "$1" in
        high-focus)
            kwriteconfig5 --file plasmanotifyrc --group Notifications --key DoNotDisturb true
            notify-send -u low "🧠 High Focus Mode" "Notifications silenced" &
            ;;
        low-energy)
            kwriteconfig5 --file plasmanotifyrc --group Notifications --key DoNotDisturb true
            notify-send -u low "🔋 Low Energy Mode" "Taking it easy today" &
            ;;
        normal)
            kwriteconfig5 --file plasmanotifyrc --group Notifications --key DoNotDisturb false
            notify-send -u low "⚡ Normal Mode" "Notifications enabled" &
            ;;
    esac
    qdbus org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript 'plasmoid.setProperty("value", '$( [ "$1" = "normal" ] && echo "0" || echo "1" )')' 2>/dev/null || true
}

CHOICE=$(zenity --list \
    --title="⚡ Energy Mode" \
    --text="How's your energy today?" \
    --column="Mode" \
    "🧠 High Focus (DND)" \
    "🔋 Low Energy (DND)" \
    "⚡ Normal Mode" \
    2>/dev/null)

case "$CHOICE" in
    "🧠 High Focus (DND)") set_energy high-focus ;;
    "🔋 Low Energy (DND)") set_energy low-energy ;;
    "⚡ Normal Mode") set_energy normal ;;
esac
EOF
    chmod +x "$HOME/.local/bin/adhd-energy-mode.sh"

    cat > "$HOME/Desktop/Energy-Mode.desktop" << 'EOF'
[Desktop Entry]
Comment=Set energy mode
Exec=/home/nxyme/.local/bin/adhd-energy-mode.sh
Icon=energy
Name=⚡ Energy Mode
Type=Application
EOF

    log_success "Energy Mode: Auto-DND based on energy level"
    
    ###########################################################################
    # 22. APPLY ALL CHANGES
    ###########################################################################
    log ""
    log "=== 19. Applying All Changes ==="
    
    kwriteconfig5 --file kdeglobals --group "KDE" --key "widgetStyle" "Breeze"
    
    qdbus org.kde.KWin /KWin org.kde.KWin.reconfigure 2>/dev/null || true
    qdbus org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.loadScriptInContext "" "$HOME/.config/plasma/adhd-init.js" 2>/dev/null || true
    
    sleep 1
    
    log_success "All changes applied"
    
    ###########################################################################
    # SUMMARY
    ###########################################################################
    log ""
    log "=========================================="
    log "✅ 100% ADHD SYSTEM ADAPTATION COMPLETE"
    log "=========================================="
    log ""
    log "📋 What was adapted (22 areas):"
    log "   • Fonts: 12pt, 42px cursor, higher contrast"
    log "   • Dolphin: Simplified, confirm delete, larger icons"
    log "   • Terminal: 12pt font, less transparency, more scrollback"
    log "   • Kate: Auto-save every 2 min"
    log "   • Notifications: Max 2, 8s delay, TopCenter"
    log "   • KWin: 1600K night color, simpler window switching"
    log "   • Plasma: Faster animations, higher contrast"
    log "   • Keyboard: Faster repeat, optimized for 60%"
    log "   • Mouse: 48px cursor, faster scroll"
    log "   • Browser: Simplified preferences"
    log "   • Auto-start: ADHD tools on login"
    log "   • Desktop: Quick access shortcuts"
    log "   • KRunner: Faster app launching (Alt+Space)"
    log "   • Workspace: Single desktop (no confusion)"
    log "   • Clipboard: 50 items history"
    log "   • Quick Notes: Always-visible notes"
    log "   • Focus Mode: Hide all windows"
    log "   • App Launcher: One-click to frequent apps"
    log "   • Accountability: Daily check-in with streak tracking"
    log "   • Dopamine: Random celebrations + milestone tracker"
    log "   • Energy Mode: Auto-DND based on energy level"
    log ""
    log "🔄 To reverse: ./adhd-full-setup.sh restore"
    log "⚠️  Logout/login required for full effect"
}

show_status() {
    echo ""
    echo "=== ADHD Full System Status ==="
    echo ""
    echo "📁 Configs installed:"
    [ -f "$HOME/.config/dolphinrc" ] && echo "  ✓ Dolphin" || echo "  ✗ Dolphin"
    [ -f "$HOME/.config/alacritty/alacritty.toml" ] && echo "  ✓ Terminal" || echo "  ✗ Terminal"
    [ -f "$HOME/.config/katerc" ] && echo "  ✓ Kate" || echo "  ✗ Kate"
    [ -f "$HOME/.config/plasmanotifyrc" ] && echo "  ✓ Notifications" || echo "  ✗ Notifications"
    echo ""
    echo "🧠 Scripts installed:"
    [ -f "$HOME/.local/bin/adhd-dashboard.sh" ] && echo "  ✓ Dashboard" || echo "  ✗ Dashboard"
    [ -f "$HOME/.local/bin/adhd-keyboard-helper.sh" ] && echo "  ✓ Keyboard Helper" || echo "  ✗ Keyboard Helper"
    echo ""
    echo "🖥️ Desktop shortcuts:"
    [ -f "$HOME/Desktop/ADHD-Control.desktop" ] && echo "  ✓ ADHD Control" || echo "  ✗ ADHD Control"
    [ -f "$HOME/Desktop/Open-Files.desktop" ] && echo "  ✓ File Manager" || echo "  ✗ File Manager"
    [ -f "$HOME/Desktop/Open-Terminal.desktop" ] && echo "  ✓ Terminal" || echo "  ✗ Terminal"
    echo ""
}

case "$1" in
    install)
        backup_config
        install_adaptations
        ;;
    restore)
        restore_config
        ;;
    status)
        show_status
        ;;
    backup)
        backup_config
        ;;
    *)
        echo "🧠 ADHD Full System Adaptation"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  install  - Install 100% ADHD adaptations"
        echo "  restore  - Restore from backup (one-click reverse)"
        echo "  backup   - Create backup only"
        echo "  status   - Show current status"
        echo ""
        ;;
esac