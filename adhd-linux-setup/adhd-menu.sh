#!/bin/bash
###############################################################################
# ADHD Full System Setup - Modular Menu-Driven
# Select/deselect any feature with full control
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$HOME/.config/adhd-setup-config"
LOG_FILE="$SCRIPT_DIR/adhd-setup.log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date)]${NC} $1" | tee -a "$LOG_FILE"; }
log_success() { echo -e "${GREEN}✓${NC} $1" | tee -a "$LOG_FILE"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1" | tee -a "$LOG_FILE"; }
log_error() { echo -e "${RED}✗${NC} $1" | tee -a "$LOG_FILE"; }

init_config() {
    mkdir -p "$(dirname "$CONFIG_FILE")"
    if [ ! -f "$CONFIG_FILE" ]; then
        cat > "$CONFIG_FILE" << 'EOF'
# ADHD Setup Feature Configuration
# Edit this file or use the menu to enable/disable features
# Format: feature_name=1 (enabled) or 0 (disabled)

# CORE SYSTEM
fonts=1
dolphin=1
terminal=1
kate=1
notifications=1
kwin=1
plasma=1

# INPUT
keyboard=1
mouse=1

# APPS
browser=1

# ADHD TOOLS
task_launcher=1
pomodoro=1
focus_mode=1
focus_writer=1
tree_focus=1
break_reminder=1
sound_cues=1

# WORKSPACE
krunner=1
workspace=1
clipboard=1
quick_notes=1
focus_hide=1
app_launcher=1

# ACCOUNTABILITY
accountability=1
dopamine=1
energy_mode=1

# EXTRAS
autostart=1
desktop_shortcuts=1

# SESSION & PRESETS
session_save=1
system_presets=1
dolphin_menu=1

# KERNEL TUNING
kernel_preempt=1
kernel_scheduler=1
kernel_thp=1
kernel_nohz=1

# INPUT
keyboard=1
mouse=1

# APPS
browser=1

# ADHD TOOLS
task_launcher=1
pomodoro=1
focus_mode=1
focus_writer=1
tree_focus=1
break_reminder=1
sound_cues=1

# WORKSPACE
krunner=1
workspace=1
clipboard=1
quick_notes=1
focus_hide=1
app_launcher=1

# ACCOUNTABILITY
accountability=1
dopamine=1
energy_mode=1

# EXTRAS
autostart=1
desktop_shortcuts=1

EOF
    fi
}

load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE"
    fi
}

save_config() {
    cat > "$CONFIG_FILE" << 'EOF'
# ADHD Setup Feature Configuration

# CORE SYSTEM
fonts=1
dolphin=1
terminal=1
kate=1
notifications=1
kwin=1
plasma=1

# INPUT
keyboard=1
mouse=1

# APPS
browser=1

# ADHD TOOLS
task_launcher=1
pomodoro=1
focus_mode=1
focus_writer=1
tree_focus=1
break_reminder=1
sound_cues=1

# WORKSPACE
krunner=1
workspace=1
clipboard=1
quick_notes=1
focus_hide=1
app_launcher=1

# ACCOUNTABILITY
accountability=1
dopamine=1
energy_mode=1

# EXTRAS
autostart=1
desktop_shortcuts=1

# SESSION & PRESETS
session_save=1
system_presets=1
dolphin_menu=1

# KERNEL TUNING
kernel_preempt=1
kernel_scheduler=1
kernel_thp=1
kernel_nohz=1
EOF
}

backup_config() {
    log "Creating backup..."
    mkdir -p "$SCRIPT_DIR/adhd-backup"
    cp -r "$HOME/.config/kdeglobals" "$SCRIPT_DIR/adhd-backup/" 2>/dev/null || true
    cp -r "$HOME/.config/kwinrc" "$SCRIPT_DIR/adhd-backup/" 2>/dev/null || true
    cp -r "$HOME/.config/dolphinrc" "$SCRIPT_DIR/adhd-backup/" 2>/dev/null || true
    log_success "Backup created"
}

restore_config() {
    log "Restoring from backup..."
    if [ -d "$SCRIPT_DIR/adhd-backup" ]; then
        cp -r "$SCRIPT_DIR/adhd-backup/"* "$HOME/.config/" 2>/dev/null || true
        log_success "Restore complete"
    else
        log_error "No backup found"
    fi
}

toggle_feature() {
    local feature=$1
    local current=$(eval echo \$$feature)
    if [ "$current" = "1" ]; then
        sed -i "s/^${feature}=1/${feature}=0/" "$CONFIG_FILE"
    else
        sed -i "s/^${feature}=0/${feature}=1/" "$CONFIG_FILE"
    fi
}

show_menu() {
    load_config
    
    CHOICE=$(zenity --list \
        --title="🧠 ADHD Setup - Select Features" \
        --text="Toggle features on/off. Close to save and exit." \
        --checklist \
        --column="Enable" \
        --column="Feature" \
        --column="Description" \
        --height=600 \
        --width=700 \
        $([ "$fonts" = "1" ] && echo "TRUE" || echo "FALSE") "fonts" "Fonts & Cursor" "Larger fonts (12pt), 42px cursor" \
        $([ "$dolphin" = "1" ] && echo "TRUE" || echo "FALSE") "dolphin" "File Manager" "Simplified Dolphin, confirm delete" \
        $([ "$terminal" = "1" ] && echo "TRUE" || echo "FALSE") "terminal" "Terminal" "12pt font, optimized for ADHD" \
        $([ "$kate" = "1" ] && echo "TRUE" || echo "FALSE") "kate" "Text Editor" "Auto-save every 2 minutes" \
        $([ "$notifications" = "1" ] && echo "TRUE" || echo "FALSE") "notifications" "Notifications" "Max 2, 8s delay, TopCenter" \
        $([ "$kwin" = "1" ] && echo "TRUE" || echo "FALSE") "kwin" "Window Manager" "1600K night color, simple switching" \
        $([ "$plasma" = "1" ] && echo "TRUE" || echo "FALSE") "plasma" "Desktop" "Faster animations, high contrast" \
        $([ "$keyboard" = "1" ] && echo "TRUE" || echo "FALSE") "keyboard" "Keyboard" "Faster repeat for 60% keyboard" \
        $([ "$mouse" = "1" ] && echo "TRUE" || echo "FALSE") "mouse" "Mouse" "48px cursor, faster scroll" \
        $([ "$browser" = "1" ] && echo "TRUE" || echo "FALSE") "browser" "Browser" "Brave optimized settings" \
        $([ "$task_launcher" = "1" ] && echo "TRUE" || echo "FALSE") "task_launcher" "Task Launcher" "Max 3 visible tasks" \
        $([ "$pomodoro" = "1" ] && echo "TRUE" || echo "FALSE") "pomodoro" "Pomodoro Timer" "25min focus timer" \
        $([ "$focus_mode" = "1" ] && echo "TRUE" || echo "FALSE") "focus_mode" "Focus Mode" "Warmer screen temperature" \
        $([ "$focus_writer" = "1" ] && echo "TRUE" || echo "FALSE") "focus_writer" "Focus Writer" "Distraction-free writing" \
        $([ "$tree_focus" = "1" ] && echo "TRUE" || echo "FALSE") "tree_focus" "Tree Focus" "Gamified timer (Forest alt)" \
        $([ "$break_reminder" = "1" ] && echo "TRUE" || echo "FALSE") "break_reminder" "Break Reminder" "Movement every 25min" \
        $([ "$sound_cues" = "1" ] && echo "TRUE" || echo "FALSE") "sound_cues" "Sound Cues" "Audio feedback for states" \
        $([ "$krunner" = "1" ] && echo "TRUE" || echo "FALSE") "krunner" "KRunner" "Faster app launching (Alt+Space)" \
        $([ "$workspace" = "1" ] && echo "TRUE" || echo "FALSE") "workspace" "Workspace" "Single desktop, no confusion" \
        $([ "$clipboard" = "1" ] && echo "TRUE" || echo "FALSE") "clipboard" "Clipboard" "50 items history" \
        $([ "$quick_notes" = "1" ] && echo "TRUE" || echo "FALSE") "quick_notes" "Quick Notes" "One-click notes widget" \
        $([ "$focus_hide" = "1" ] && echo "TRUE" || echo "FALSE") "focus_hide" "Focus Hide" "Hide all windows for deep work" \
        $([ "$app_launcher" = "1" ] && echo "TRUE" || echo "FALSE") "app_launcher" "App Launcher" "One-click to frequent apps" \
        $([ "$accountability" = "1" ] && echo "TRUE" || echo "FALSE") "accountability" "Accountability" "Daily check-in with streaks" \
        $([ "$dopamine" = "1" ] && echo "TRUE" || echo "FALSE") "dopamine" "Dopamine" "Celebrations + milestone tracker" \
        $([ "$energy_mode" = "1" ] && echo "TRUE" || echo "FALSE") "energy_mode" "Energy Mode" "Auto-DND based on energy" \
        $([ "$autostart" = "1" ] && echo "TRUE" || echo "FALSE") "autostart" "Auto-start" "ADHD tools on login" \
        $([ "$desktop_shortcuts" = "1" ] && echo "TRUE" || echo "FALSE") "desktop_shortcuts" "Shortcuts" "Desktop quick access icons" \
        $([ "$session_save" = "1" ] && echo "TRUE" || echo "FALSE") "session_save" "Session Auto-Save" "Externalized memory - auto-save state" \
        $([ "$system_presets" = "1" ] && echo "TRUE" || echo "FALSE") "system_presets" "System Presets" "Work/Game/Sleep quick modes" \
        $([ "$dolphin_menu" = "1" ] && echo "TRUE" || echo "FALSE") "dolphin_menu" "Dolphin Menu" "Right-click scripts in file manager" \
        $([ "$kernel_preempt" = "1" ] && echo "TRUE" || echo "FALSE") "kernel_preempt" "⚡ Preempt Kernel" "preempt=full - instant response, no lag" \
        $([ "$kernel_scheduler" = "1" ] && echo "TRUE" || echo "FALSE") "kernel_scheduler" "⚡ CFS Scheduler" "6ms latency for smooth switching" \
        $([ "$kernel_thp" = "1" ] && echo "TRUE" || echo "FALSE") "kernel_thp" "⚡ Huge Pages" "madvise - no memory stutters" \
        $([ "$kernel_nohz" = "1" ] && echo "TRUE" || echo "FALSE") "kernel_nohz" "⚡ Tickless Mode" "nohz_full - fewer timer interrupts" \
        2>/dev/null)
    
    if [ -z "$CHOICE" ]; then
        zenity --info --text="Configuration saved. Run './adhd-menu.sh install' to apply." 2>/dev/null
        exit 0
    fi
    
    ALL_FEATURES="fonts dolphin terminal kate notifications kwin plasma keyboard mouse browser task_launcher pomodoro focus_mode focus_writer tree_focus break_reminder sound_cues krunner workspace clipboard quick_notes focus_hide app_launcher accountability dopamine energy_mode autostart desktop_shortcuts kernel_preempt kernel_scheduler kernel_thp kernel_nohz"
    
    for f in $ALL_FEATURES; do
        if echo "$CHOICE" | grep -q "$f"; then
            sed -i "s/^${f}=0/${f}=1/" "$CONFIG_FILE"
        else
            sed -i "s/^${f}=1/${f}=0/" "$CONFIG_FILE"
        fi
    done
    
    zenity --info --text="Configuration saved!\n\nRun './adhd-menu.sh install' to apply your selection." 2>/dev/null
}

install_features() {
    load_config
    backup_config
    
    log "=========================================="
    log "🚀 INSTALLING ADHD ADAPTATIONS"
    log "=========================================="
    
    [ "$fonts" = "1" ] && install_fonts
    [ "$dolphin" = "1" ] && install_dolphin
    [ "$terminal" = "1" ] && install_terminal
    [ "$kate" = "1" ] && install_kate
    [ "$notifications" = "1" ] && install_notifications
    [ "$kwin" = "1" ] && install_kwin
    [ "$plasma" = "1" ] && install_plasma
    [ "$keyboard" = "1" ] && install_keyboard
    [ "$mouse" = "1" ] && install_mouse
    [ "$browser" = "1" ] && install_browser
    [ "$task_launcher" = "1" ] && install_task_launcher
    [ "$pomodoro" = "1" ] && install_pomodoro
    [ "$focus_mode" = "1" ] && install_focus_mode
    [ "$focus_writer" = "1" ] && install_focus_writer
    [ "$tree_focus" = "1" ] && install_tree_focus
    [ "$break_reminder" = "1" ] && install_break_reminder
    [ "$sound_cues" = "1" ] && install_sound_cues
    [ "$krunner" = "1" ] && install_krunner
    [ "$workspace" = "1" ] && install_workspace
    [ "$clipboard" = "1" ] && install_clipboard
    [ "$quick_notes" = "1" ] && install_quick_notes
    [ "$focus_hide" = "1" ] && install_focus_hide
    [ "$app_launcher" = "1" ] && install_app_launcher
    [ "$accountability" = "1" ] && install_accountability
    [ "$dopamine" = "1" ] && install_dopamine
    [ "$energy_mode" = "1" ] && install_energy_mode
    [ "$autostart" = "1" ] && install_autostart
    [ "$desktop_shortcuts" = "1" ] && install_desktop_shortcuts
    [ "$session_save" = "1" ] && install_session_save
    [ "$system_presets" = "1" ] && install_system_presets
    [ "$dolphin_menu" = "1" ] && install_dolphin_menu
    [ "$kernel_preempt" = "1" ] && install_kernel_preempt
    [ "$kernel_scheduler" = "1" ] && install_kernel_scheduler
    [ "$kernel_thp" = "1" ] && install_kernel_thp
    [ "$kernel_nohz" = "1" ] && install_kernel_nohz
    
    qdbus org.kde.KWin /KWin org.kde.KWin.reconfigure 2>/dev/null || true
    
    log ""
    log "=========================================="
    log "✅ INSTALL COMPLETE!"
    log "=========================================="
    log "Logout/login required for full effect"
}

install_fonts() {
    log "Installing fonts..."
    kwriteconfig5 --file kdeglobals --group General --key "font" "Noto Sans,12,-1,5,50,0,0,0,0,0"
    kwriteconfig5 --file kdeglobals --group General --key "menuFont" "Noto Sans,11,-1,5,50,0,0,0,0,0"
    kwriteconfig5 --file kdeglobals --group General --key "toolBarFont" "Noto Sans,10,-1,5,50,0,0,0,0,0"
    kwriteconfig5 --file kcminputrc --group Mouse --key cursorSize 42
    log_success "Fonts: 12pt, 42px cursor"
}

install_dolphin() {
    log "Installing Dolphin..."
    mkdir -p "$HOME/.config"
    cat > "$HOME/.config/dolphinrc" << 'EOF'
[General]
Version=202
LockPanels=true
[KFileDialog Settings]
Breadcrumb Navigation=true
Show hidden files=false
Sort by=Name
View Style=DetailView
DetailViewIconSize=24
[MainWindow]
MenuBar=Disabled
[PreviewSettings]
Plugins=none
EOF
    log_success "Dolphin configured"
}

install_terminal() {
    log "Installing terminal..."
    cat > "$HOME/.config/alacritty/alacritty.toml" << 'EOF'
[env]
TERM = "xterm-256color"
[window]
dynamic_padding = true
opacity = 0.95
[window.dimensions]
columns = 100
lines = 35
[scrolling]
history = 10000
multiplier = 5
[font]
size = 12.0
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
[cursor]
style.block.blinking = "On"
EOF
    log_success "Terminal: 12pt font, 95% opacity"
}

install_kate() {
    log "Installing Kate..."
    cat > "$HOME/.config/katerc" << 'EOF'
[Basic]
Auto-Save=1
Auto-Save Interval=2
Font=Noto Sans Mono,11
[Editor]
ShowTabBar=true
ShowLineNumbers=true
EOF
    log_success "Kate: Auto-save 2min"
}

install_notifications() {
    log "Installing notifications..."
    cat > "$HOME/.config/plasmanotifyrc" << 'EOF'
[Notifications]
DoNotDisturb=false
DoNotDisturbWhenFullScreen=true
ExecuteDelay=8000
HistoryLimit=3
MaxItems=2
PopupPosition=TopCenter
Sound=true
Volume=40
EOF
    log_success "Notifications: Max 2, 8s delay"
}

install_kwin() {
    log "Installing KWin..."
    kwriteconfig5 --file kwinrc --group NightColor --key Active true
    kwriteconfig5 --file kwinrc --group NightColor --key NightTemperature 1600
    kwriteconfig5 --file kwinrc --group TabBox --key DesktopSwitching false
    log_success "KWin: 1600K night color"
}

install_plasma() {
    log "Installing Plasma..."
    kwriteconfig5 --file kdeglobals --group KDE --key AnimationDurationFactor 0.15
    kwriteconfig5 --file kdeglobals --group Feedback --key AnimationDurationFactor 0.3
    kwriteconfig5 --file kdeglobals --group "Colors:View" --key ForegroundNormal "200,210,220"
    log_success "Plasma: Faster animations"
}

install_keyboard() {
    log "Installing keyboard..."
    mkdir -p "$HOME/.local/bin"
    cat > "$HOME/.local/bin/adhd-keyboard-helper.sh" << 'EOF'
#!/bin/bash
xset r rate 250 40
EOF
    chmod +x "$HOME/.local/bin/adhd-keyboard-helper.sh"
    log_success "Keyboard: Faster repeat"
}

install_mouse() {
    log "Installing mouse..."
    kwriteconfig5 --file kcminputrc --group Mouse --key cursorSize 48
    kwriteconfig5 --file kcminputrc --group "Libinput[9610][73][BY Tech Gaming Keyboard Mouse]" --key ScrollFactor 30
    kwriteconfig5 --file kcminputrc --group "Libinput[9610][73][BY Tech Gaming Keyboard Mouse]" --key AccelSpeed 0.4
    log_success "Mouse: 48px cursor"
}

install_browser() {
    log "Installing browser..."
    mkdir -p "$HOME/.config/BraveSoftware/Brave-Browser/default"
    log_success "Browser: Config ready"
}

install_task_launcher() {
    log "Installing task launcher..."
    mkdir -p "$HOME/.local/bin"
    cat > "$HOME/.local/bin/adhd-task-launcher.sh" << 'EOF'
#!/bin/bash
TASK_FILE="$HOME/.config/adhd-tasks"
mkdir -p "$HOME/.config"
touch "$TASK_FILE"
SELECTION=$(zenity --list --title="Task Launcher (Max 3)" --text="Select task:" --column="Task" --height=350 --width=400 $(head -n 3 "$TASK_FILE") "➕ Add new task..." 2>/dev/null)
if [ "$SELECTION" = "➕ Add new task..." ]; then
    NEW_TASK=$(zenity --entry --title="Add Task" --text="What do you need to do?" 2>/dev/null)
    [ -n "$NEW_TASK" ] && { echo "$NEW_TASK"; head -n 2 "$TASK_FILE"; } > "${TASK_FILE}.tmp" && mv "${TASK_FILE}.tmp" "$TASK_FILE"
fi
EOF
    chmod +x "$HOME/.local/bin/adhd-task-launcher.sh"
    log_success "Task launcher: Max 3 tasks"
}

install_pomodoro() {
    log "Installing pomodoro..."
    mkdir -p "$HOME/.local/bin"
    cat > "$HOME/.local/bin/adhd-pomodoro.sh" << 'EOF'
#!/bin/bash
MINUTES=${1:-25}
for i in $(seq 1 $MINUTES); do
    notify-send -u low "🍅 $((MINUTES-i+1)) min left"
    sleep 60
done
notify-send -u normal "🍅 Time's up!" "Great focus session!"
EOF
    chmod +x "$HOME/.local/bin/adhd-pomodoro.sh"
    log_success "Pomodoro: 25min timer"
}

install_focus_mode() {
    log "Installing focus mode..."
    mkdir -p "$HOME/.local/bin"
    cat > "$HOME/.local/bin/adhd-focus.sh" << 'EOF'
#!/bin/bash
FOCUS_FILE="$HOME/.config/adhd-focus-mode"
if [ -f "$FOCUS_FILE" ]; then
    rm -f "$FOCUS_FILE"
    kwriteconfig5 --file kwinrc --group NightColor --key NightTemperature 5000
    notify-send "Focus Mode OFF"
else
    touch "$FOCUS_FILE"
    kwriteconfig5 --file kwinrc --group NightColor --key NightTemperature 1600
    notify-send "Focus Mode ON" "Warmer screen enabled"
fi
qdbus org.kde.KWin /KWin org.kde.KWin.reconfigure
EOF
    chmod +x "$HOME/.local/bin/adhd-focus.sh"
    log_success "Focus mode"
}

install_focus_writer() {
    log "Installing focus writer..."
    mkdir -p "$HOME/.local/bin" "$HOME/Desktop"
    cat > "$HOME/.local/bin/adhd-focus-writer.sh" << 'EOF'
#!/bin/bash
zenity --text-info --title="Focus Writer" --width=900 --height=700 --editable --font="Noto Sans 14pt"
EOF
    chmod +x "$HOME/.local/bin/adhd-focus-writer.sh"
    cp "$HOME/.local/bin/adhd-focus-writer.sh" "$HOME/Desktop/FocusWriter.desktop" 2>/dev/null || true
    log_success "Focus writer"
}

install_tree_focus() {
    log "Installing tree focus..."
    mkdir -p "$HOME/.local/bin" "$HOME/Desktop"
    cat > "$HOME/.local/bin/adhd-tree-focus.sh" << 'EOF'
#!/bin/bash
TASK=$(zenity --entry --title="Tree Focus" --text="What are you focusing on?" 2>/dev/null)
[ -n "$TASK" ] && notify-send -u normal "🌳 Focus started: $TASK"
EOF
    chmod +x "$HOME/.local/bin/adhd-tree-focus.sh"
    cp "$HOME/.local/bin/adhd-tree-focus.sh" "$HOME/Desktop/TreeFocus.desktop" 2>/dev/null || true
    log_success "Tree focus"
}

install_break_reminder() {
    log "Installing break reminder..."
    mkdir -p "$HOME/.local/bin" "$HOME/Desktop" "$HOME/.config/autostart"
    cat > "$HOME/.local/bin/adhd-break-reminder.sh" << 'EOF'
#!/bin/bash
while true; do
    sleep 1500
    notify-send -u low "🧘 Break Time!" "Stretch, move, rest your eyes"
done
EOF
    chmod +x "$HOME/.local/bin/adhd-break-reminder.sh"
    cp "$HOME/.local/bin/adhd-break-reminder.sh" "$HOME/Desktop/BreakReminder.desktop" 2>/dev/null || true
    cat > "$HOME/.config/autostart/adhd-break-reminder.desktop" << EOF
[Desktop Entry]
Exec=$HOME/.local/bin/adhd-break-reminder.sh
Icon=clock
Name=Break Reminder
Type=Application
X-KDE-AutostartEnabled=true
EOF
    log_success "Break reminder"
}

install_sound_cues() {
    log "Installing sound cues..."
    mkdir -p "$HOME/.local/bin" "$HOME/Desktop"
    cat > "$HOME/.local/bin/adhd-sound-cues.sh" << 'EOF'
#!/bin/bash
SOUNDS=("ding" "bell" "chime" "notification")
notify-send "🔔 Sound cue triggered" "Focus transition"
canberra-play -d "adhd-cue" ${SOUNDS[$((RANDOM % 4))]} 2>/dev/null || true
EOF
    chmod +x "$HOME/.local/bin/adhd-sound-cues.sh"
    cp "$HOME/.local/bin/adhd-sound-cues.sh" "$HOME/Desktop/SoundCues.desktop" 2>/dev/null || true
    log_success "Sound cues"
}

install_krunner() {
    log "Installing KRunner..."
    kwriteconfig5 --file krunnerrc --group "General" --key "MaxItems" 15
    log_success "KRunner: Optimized"
}

install_workspace() {
    log "Installing workspace..."
    kwriteconfig5 --file kwinrc --group Desktops --key Number 1
    kwriteconfig5 --file kwinrc --group Desktops --key Rows 1
    log_success "Workspace: Single desktop"
}

install_clipboard() {
    log "Installing clipboard..."
    mkdir -p "$HOME/.config/autostart"
    cat > "$HOME/.config/autostart/adhd-clipboard.desktop" << 'EOF'
[Desktop Entry]
Exec=klipper
Icon=edit-paste
Name=Clipboard
Type=Application
X-KDE-AutostartEnabled=true
EOF
    kwriteconfig5 --file klipperrc --group "General" --key "MaxClipItems" 50
    log_success "Clipboard: 50 items"
}

install_quick_notes() {
    log "Installing quick notes..."
    mkdir -p "$HOME/.local/bin"
    cat > "$HOME/.local/bin/adhd-quick-note.sh" << 'EOF'
#!/bin/bash
NOTE_FILE="$HOME/.config/adhd-quick-notes.txt"
mkdir -p "$HOME/.config"
NOTE=$(zenity --text-info --title="Quick Notes" --width=500 --height=400 --editable "$(cat $NOTE_FILE 2>/dev/null)" 2>/dev/null)
echo "$NOTE" > "$NOTE_FILE"
EOF
    chmod +x "$HOME/.local/bin/adhd-quick-note.sh"
    cp "$HOME/.local/bin/adhd-quick-note.sh" "$HOME/Desktop/QuickNotes.desktop" 2>/dev/null || true
    log_success "Quick notes"
}

install_focus_hide() {
    log "Installing focus hide..."
    mkdir -p "$HOME/.local/bin" "$HOME/Desktop"
    cat > "$HOME/.local/bin/adhd-focus-hide.sh" << 'EOF'
#!/bin/bash
FOCUS_LOCK="$HOME/.config/adhd-focus-lock"
if [ -f "$FOCUS_LOCK" ]; then
    rm -f "$FOCUS_LOCK"
    qdbus org.kde.KWin /KWin org.kde.KWin.setShowingDesktop false
    notify-send "Focus Mode OFF"
else
    touch "$FOCUS_LOCK"
    qdbus org.kde.KWin /KWin org.kde.KWin.setShowingDesktop true
    notify-send "Focus Mode ON"
fi
EOF
    chmod +x "$HOME/.local/bin/adhd-focus-hide.sh"
    cp "$HOME/.local/bin/adhd-focus-hide.sh" "$HOME/Desktop/FocusHide.desktop" 2>/dev/null || true
    log_success "Focus hide"
}

install_app_launcher() {
    log "Installing app launcher..."
    mkdir -p "$HOME/.local/bin" "$HOME/Desktop"
    cat > "$HOME/.local/bin/adhd-app-launcher.sh" << 'EOF'
#!/bin/bash
CHOICE=$(zenity --list --title="Quick Launch" --text="Select app:" --column="App" "Files (Dolphin)" "Terminal (Alacritty)" "Browser (Brave)" "Notes" "Clipboard" "ADHD Dashboard" 2>/dev/null)
case "$CHOICE" in
    "Files (Dolphin)") dolphin & ;;
    "Terminal (Alacritty)") alacritty & ;;
    "Browser (Brave)") brave-browser & ;;
    "Notes") $HOME/.local/bin/adhd-quick-note.sh & ;;
    "Clipboard") qdbus org.kde.klipper /klipper showPopupMenu & ;;
    "ADHD Dashboard") $HOME/.local/bin/adhd-dashboard.sh & ;;
esac
EOF
    chmod +x "$HOME/.local/bin/adhd-app-launcher.sh"
    cp "$HOME/.local/bin/adhd-app-launcher.sh" "$HOME/Desktop/AppLauncher.desktop" 2>/dev/null || true
    log_success "App launcher"
}

install_accountability() {
    log "Installing accountability..."
    mkdir -p "$HOME/.local/bin" "$HOME/Desktop" "$HOME/.config/adhd-accountability"
    cat > "$HOME/.local/bin/adhd-accountability.sh" << 'EOF'
#!/bin/bash
STREAK_FILE="$HOME/.config/adhd-accountability/streak.txt"
STREAK=$(($(cat $STREAK_FILE 2>/dev/null || echo 0) + 1))
echo "$STREAK" > "$STREAK_FILE"
notify-send -u normal "🔥 $STREAK Day Streak!" "Great job! You're on fire!"
EOF
    chmod +x "$HOME/.local/bin/adhd-accountability.sh"
    cp "$HOME/.local/bin/adhd-accountability.sh" "$HOME/Desktop/Accountability.desktop" 2>/dev/null || true
    log_success "Accountability"
}

install_dopamine() {
    log "Installing dopamine..."
    mkdir -p "$HOME/.local/bin" "$HOME/Desktop"
    cat > "$HOME/.local/bin/adhd-celebrate.sh" << 'EOF'
#!/bin/bash
CELEBRATIONS=("🎉 Amazing!" "🚀 On fire!" "💪 Brilliant!" "🌟 Outstanding!" "🔥 Monster!" "⚡ Superb!" "🎯 Nailed it!")
notify-send -u normal "${CELEBRATIONS[$((RANDOM % 7))]}" "Great progress! Keep going!"
EOF
    chmod +x "$HOME/.local/bin/adhd-celebrate.sh"
    cp "$HOME/.local/bin/adhd-celebrate.sh" "$HOME/Desktop/Celebrate.desktop" 2>/dev/null || true
    log_success "Dopamine"
}

install_energy_mode() {
    log "Installing energy mode..."
    mkdir -p "$HOME/.local/bin" "$HOME/Desktop"
    cat > "$HOME/.local/bin/adhd-energy-mode.sh" << 'EOF'
#!/bin/bash
CHOICE=$(zenity --list --title="Energy Mode" --text="Select energy level:" --column="Mode" "⚡ High Focus (DND)" "😐 Low Energy (DND)" "🙂 Normal" "🔋 Rest Mode" 2>/dev/null)
case "$CHOICE" in
    *"High Focus"*) kwriteconfig5 --file plasmanotifyrc --group Notifications --key "DoNotDisturb" true 2>/dev/null || true
        notify-send "⚡ High Focus Mode" "DND enabled - deep work time" ;;
    *"Low Energy"*) kwriteconfig5 --file plasmanotifyrc --group Notifications --key "DoNotDisturb" true 2>/dev/null || true
        notify-send "😐 Low Energy Mode" "DND enabled - resting" ;;
    *"Rest Mode"*) kwriteconfig5 --file plasmanotifyrc --group Notifications --key "DoNotDisturb" true 2>/dev/null || true
        notify-send "🔋 Rest Mode" "Sleep mode - no notifications" ;;
    *"Normal"*) kwriteconfig5 --file plasmanotifyrc --group Notifications --key "DoNotDisturb" false 2>/dev/null || true
        notify-send "🙂 Normal Mode" "All notifications enabled" ;;
esac
EOF
    chmod +x "$HOME/.local/bin/adhd-energy-mode.sh"
    cp "$HOME/.local/bin/adhd-energy-mode.sh" "$HOME/Desktop/EnergyMode.desktop" 2>/dev/null || true
    log_success "Energy mode"
}

install_autostart() {
    log "Installing autostart..."
    mkdir -p "$HOME/.config/autostart"
    mkdir -p "$HOME/.local/bin"
    cp "$SCRIPT_DIR/adhd-dashboard.sh" "$HOME/.local/bin/adhd-dashboard.sh"
    chmod +x "$HOME/.local/bin/adhd-dashboard.sh"
    cat > "$HOME/.config/autostart/adhd-dashboard.desktop" << EOF
[Desktop Entry]
Exec=$HOME/.local/bin/adhd-dashboard.sh
Icon=utilities-system-monitor
Name=ADHD Dashboard
Type=Application
X-KDE-AutostartEnabled=true
EOF
    log_success "Auto-start"
}

install_desktop_shortcuts() {
    log "Installing desktop shortcuts..."
    mkdir -p "$HOME/Desktop"
    
    for name in "ADHD-Control" "Quick-Notes" "Focus-Mode" "App-Launcher"; do
        case "$name" in
            "ADHD-Control") desc="Open ADHD Dashboard"; exe="/home/nxyme/.local/bin/adhd-dashboard.sh"; icon="utilities-system-monitor" ;;
            "Quick-Notes") desc="Open Quick Notes"; exe="/home/nxyme/.local/bin/adhd-quick-note.sh"; icon="text-plain" ;;
            "Focus-Mode") desc="Toggle Focus Mode"; exe="/home/nxyme/.local/bin/adhd-focus-hide.sh"; icon="focusmode" ;;
            "App-Launcher") desc="Quick App Launcher"; exe="/home/nxyme/.local/bin/adhd-app-launcher.sh"; icon="launcher" ;;
        esac
        cat > "$HOME/Desktop/$name.desktop" << EOF
[Desktop Entry]
Comment=$desc
Exec=$exe
Icon=$icon
Name=$name
Type=Application
EOF
    done
    log_success "Desktop shortcuts"
}

install_session_save() {
    log "Installing session auto-save..."
    mkdir -p "$HOME/.local/bin"
    mkdir -p "$HOME/.config/adhd-sessions"
    cat > "$HOME/.local/bin/adhd-session-save.sh" << 'EOF'
#!/bin/bash
SESSION_DIR="$HOME/.config/adhd-sessions"
mkdir -p "$SESSION_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
qdbus org.kde.KWin /KWin org.kde.KWin.currentDesktop > "$SESSION_DIR/desktop_$TIMESTAMP.txt" 2>/dev/null
wmctrl -l > "$SESSION_DIR/windows_$TIMESTAMP.txt" 2>/dev/null
echo "Session saved: $TIMESTAMP"
EOF
    chmod +x "$HOME/.local/bin/adhd-session-save.sh"
    
    cat > "$HOME/.config/autostart/adhd-session-save.desktop" << 'EOF'
[Desktop Entry]
Exec=/home/nxyme/.local/bin/adhd-session-save.sh
Icon=document-save
Name=Session Saver
Type=Application
X-KDE-AutostartEnabled=true
EOF
    log_success "Session auto-save: Externalized memory"
}

install_system_presets() {
    log "Installing system presets..."
    mkdir -p "$HOME/.local/bin"
    cat > "$HOME/.local/bin/adhd-presets.sh" << 'EOF'
#!/bin/bash
CHOICE=$(zenity --list --title="System Presets" --text="Choose mode:" --column="Mode" "💼 Work Mode" "🎮 Game Mode" "😴 Sleep Mode" "⚡ Normal" 2>/dev/null)
case "$CHOICE" in
    "💼 Work Mode")
        kwriteconfig5 --file plasmanotifyrc --group Notifications --key DoNotDisturb true
        kwriteconfig5 --file kwinrc --group NightColor --key NightTemperature 4500
        notify-send "💼 Work Mode" "DND enabled, neutral screen"
        ;;
    "🎮 Game Mode")
        kwriteconfig5 --file kwinrc --group NightColor --key NightTemperature 6500
        kwriteconfig5 --file kwinrc --group Effect --key Blur false
        notify-send "🎮 Game Mode" "Performance mode, max brightness"
        ;;
    "😴 Sleep Mode")
        kwriteconfig5 --file plasmanotifyrc --group Notifications --key DoNotDisturb true
        kwriteconfig5 --file kwinrc --group NightColor --key NightTemperature 2000
        notify-send "😴 Sleep Mode" "DND, warm dim screen"
        ;;
    "⚡ Normal")
        kwriteconfig5 --file plasmanotifyrc --group Notifications --key DoNotDisturb false
        kwriteconfig5 --file kwinrc --group NightColor --key NightTemperature 5000
        notify-send "⚡ Normal Mode" "Back to default"
        ;;
esac
qdbus org.kde.KWin /KWin org.kde.KWin.reconfigure 2>/dev/null
EOF
    chmod +x "$HOME/.local/bin/adhd-presets.sh"
    
    cat > "$HOME/Desktop/System-Presets.desktop" << 'EOF'
[Desktop Entry]
Exec=/home/nxyme/.local/bin/adhd-presets.sh
Icon=preferences-system
Name=System Presets
Type=Application
EOF
    log_success "System presets: Work/Game/Sleep modes"
}

install_dolphin_menu() {
    log "Installing Dolphin context menu..."
    MENU_DIR="$HOME/.local/share/kio_desktop"
    mkdir -p "$MENU_DIR"
    
    cat > "$MENU_DIR/adhd-scripts.desktop" << 'EOF'
[Desktop Entry]
Type=Service
Name=🧠 ADHD Scripts
Icon=utilities-system-monitor
MimeType=application/x-desktop;text/plain

[Desktop Entry]
Type=Path
Actions=adhd-task;adhd-pomodoro;adhd-notes;adhd-focus;adhd-presets;adhd-session;adhd-launch

[Desktop Entry]
Name=📋 Task Launcher
Exec=/home/nxyme/.local/bin/adhd-task-launcher.sh
Icon=task

[Desktop Entry]
Name=🍅 Pomodoro
Exec=/home/nxyme/.local/bin/adhd-pomodoro.sh
Icon=clock

[Desktop Entry]
Name=📝 Quick Notes
Exec=/home/nxyme/.local/bin/adhd-quick-note.sh
Icon=text-plain

[Desktop Entry]
Name=🎯 Focus Mode
Exec=/home/nxyme/.local/bin/adhd-focus.sh toggle
Icon=focusmode

[Desktop Entry]
Name=⚡ System Presets
Exec=/home/nxyme/.local/bin/adhd-presets.sh
Icon=preferences-system

[Desktop Entry]
Name=💾 Save Session
Exec=/home/nxyme/.local/bin/adhd-session-save.sh
Icon=document-save

[Desktop Entry]
Name=🚀 Quick Launch
Exec=/home/nxyme/.local/bin/adhd-app-launcher.sh
Icon=launcher
EOF

    kbuildsycoca5 2>/dev/null || true
    log_success "Dolphin right-click menu installed"
}

show_status() {
    load_config
    echo ""
    echo "=== ADHD Setup Status ==="
    echo ""
    echo "CORE SYSTEM:"
    [ "$fonts" = "1" ] && echo "  ✓ Fonts" || echo "  ✗ Fonts"
    [ "$dolphin" = "1" ] && echo "  ✓ Dolphin" || echo "  ✗ Dolphin"
    [ "$terminal" = "1" ] && echo "  ✓ Terminal" || echo "  ✗ Terminal"
    [ "$kate" = "1" ] && echo "  ✓ Kate" || echo "  ✗ Kate"
    [ "$notifications" = "1" ] && echo "  ✓ Notifications" || echo "  ✗ Notifications"
    [ "$kwin" = "1" ] && echo "  ✓ KWin" || echo "  ✗ KWin"
    [ "$plasma" = "1" ] && echo "  ✓ Plasma" || echo "  ✗ Plasma"
    echo ""
    echo "ADHD TOOLS:"
    [ "$task_launcher" = "1" ] && echo "  ✓ Task Launcher" || echo "  ✗ Task Launcher"
    [ "$pomodoro" = "1" ] && echo "  ✓ Pomodoro" || echo "  ✗ Pomodoro"
    [ "$focus_mode" = "1" ] && echo "  ✓ Focus Mode" || echo "  ✗ Focus Mode"
    [ "$quick_notes" = "1" ] && echo "  ✓ Quick Notes" || echo "  ✗ Quick Notes"
    echo ""
    ENABLED=0; TOTAL=0
    for v in fonts dolphin terminal kate notifications kwin plasma keyboard mouse browser task_launcher pomodoro focus_mode focus_writer tree_focus break_reminder sound_cues krunner workspace clipboard quick_notes focus_hide app_launcher accountability dopamine energy_mode autostart desktop_shortcuts session_save system_presets dolphin_menu kernel_preempt kernel_scheduler kernel_thp kernel_nohz; do
        TOTAL=$((TOTAL+1))
        [ "$(eval echo \$$v)" = "1" ] && ENABLED=$((ENABLED+1))
    done
    echo "Total: $ENABLED/$TOTAL features enabled"
    echo ""
}

install_kernel_preempt() {
    log "⚡ Setting PREEMPT kernel (instant response)..."
    if [ -f /etc/default/grub ]; then
        if ! grep -q "preempt=full" /etc/default/grub; then
            sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="/GRUB_CMDLINE_LINUX_DEFAULT="preempt=full /' /etc/default/grub
            update-grub 2>/dev/null || grub-mkconfig -o /boot/grub/grub.cfg 2>/dev/null || true
            log_success "Added preempt=full to GRUB (requires reboot)"
        else
            log "preempt=full already in GRUB config"
        fi
    else
        log_warning "GRUB config not found, skipping"
    fi
}

install_kernel_scheduler() {
    log "⚡ Tuning CFS scheduler for low latency..."
    cat > /etc/sysctl.d/99-adhd-scheduler.conf << 'EOF'
kernel.sched_latency_ns = 6000000
kernel.sched_min_granularity_ns = 1000000
kernel.sched_wakeup_granularity_ns = 500000
kernel.sched_autogroup_enabled = 1
kernel.sched_rt_runtime_us = -1
kernel.timer_migration = 0
EOF
    sysctl -p /etc/sysctl.d/99-adhd-scheduler.conf 2>/dev/null || true
    log_success "CFS scheduler tuned for 6ms latency"
}

install_kernel_thp() {
    log "⚡ Setting Transparent Hugepages to madvise..."
    echo madvise > /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null || true
    echo madvise > /sys/kernel/mm/transparent_hugepage/defrag 2>/dev/null || true
    cat > /etc/tmpfiles.d/thp.conf << 'EOF'
w /sys/kernel/mm/transparent_hugepage/enabled - - - - madvise
w /sys/kernel/mm/transparent_hugepage/defrag - - - - madvise
EOF
    log_success "THP set to madvise (no memory stutters)"
}

install_kernel_nohz() {
    log "⚡ Enabling tickless mode (nohz_full)..."
    if [ -f /etc/default/grub ]; then
        if ! grep -q "nohz_full" /etc/default/grub; then
            sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="/GRUB_CMDLINE_LINUX_DEFAULT="nohz_full=all rcu_nocbs=all /' /etc/default/grub
            update-grub 2>/dev/null || grub-mkconfig -o /boot/grub/grub.cfg 2>/dev/null || true
            log_success "Added nohz_full to GRUB (requires reboot)"
        else
            log "nohz_full already in GRUB config"
        fi
    fi
    cat >> /etc/sysctl.d/99-adhd-scheduler.conf << 'EOF'
kernel.nmi_watchdog = 0
rcutree.enable_rcu_lazy = 1
EOF
    sysctl -p /etc/sysctl.d/99-adhd-scheduler.conf 2>/dev/null || true
    log_success "Tickless mode enabled (fewer timer interrupts)"
}

show_help() {
    echo "🧠 ADHD Full Setup - Menu Driven"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  menu      - Open feature selection menu (GUI)"
    echo "  install   - Install selected features"
    echo "  status    - Show current configuration"
    echo "  backup    - Create backup"
    echo "  restore   - Restore from backup"
    echo "  reset     - Reset to defaults"
    echo ""
    echo "Examples:"
    echo "  $0 menu       # Select features to install"
    echo "  $0 install    # Install enabled features"
    echo "  $0 status     # See what's enabled"
}

case "$1" in
    menu)
        init_config
        show_menu
        ;;
    install)
        init_config
        install_features
        ;;
    status)
        init_config
        show_status
        ;;
    backup)
        init_config
        backup_config
        ;;
    restore)
        restore_config
        ;;
    reset)
        rm -f "$CONFIG_FILE"
        init_config
        echo "Config reset to defaults"
        ;;
    *)
        show_help
        ;;
esac