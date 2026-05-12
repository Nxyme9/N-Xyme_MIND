#!/bin/bash
###############################################################################
# ADHD Linux Accessibility Setup - One-Click Reversible
# 
# This script installs and configures ADHD-friendly accessibility features
# on Linux (KDE Plasma optimized).
#
# USAGE:
#   ./adhd-setup.sh install    - Install and configure all ADHD features
#   ./adhd-setup.sh backup    - Create backup of current config (pre-install)
#   ./adhd-setup.sh restore   - Restore from backup (one-click reversal)
#   ./adhd-setup.sh status    - Show current status
#   ./adhd-setup.sh verify    - Verify all features are working
#   ./adhd-setup.sh dashboard - Open ADHD control dashboard
#
###############################################################################

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/adhd-backup"
LOG_FILE="$SCRIPT_DIR/adhd-setup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}✗${NC} $1" | tee -a "$LOG_FILE"
}

###############################################################################
# BACKUP FUNCTION - Creates restore point before any changes
###############################################################################

backup_current_config() {
    log "Creating backup of current configuration..."
    
    mkdir -p "$BACKUP_DIR/config"
    mkdir -p "$BACKUP_DIR/autostart"
    
    # Backup user config files
    if [ -d "$HOME/.config" ]; then
        log "Backing up ~/.config..."
        cp -r "$HOME/.config/kdeglobals" "$BACKUP_DIR/config/" 2>/dev/null || true
        cp -r "$HOME/.config/kwinrc" "$BACKUP_DIR/config/" 2>/dev/null || true
        cp -r "$HOME/.config/plasmanotifyrc" "$BACKUP_DIR/config/" 2>/dev/null || true
        cp -r "$HOME/.config/kcminputrc" "$BACKUP_DIR/config/" 2>/dev/null || true
        cp -r "$HOME/.config/autostart" "$BACKUP_DIR/" 2>/dev/null || true
    fi
    
    # Create timestamp marker
    echo "$(date '+%Y-%m-%d %H:%M:%S')" > "$BACKUP_DIR/backup-timestamp.txt"
    
    log_success "Backup created at $BACKUP_DIR"
    log "To restore: ./adhd-setup.sh restore"
}

###############################################################################
# RESTORE FUNCTION - One-click reversal
###############################################################################

restore_from_backup() {
    log "Restoring from backup..."
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log_error "No backup found at $BACKUP_DIR"
        log "Run './adhd-setup.sh backup' first to create a backup."
        exit 1
    fi
    
    # Restore user config files
    if [ -d "$BACKUP_DIR/config" ]; then
        log "Restoring user configuration..."
        cp -r "$BACKUP_DIR/config/"* "$HOME/.config/" 2>/dev/null || true
    fi
    
    # Remove installed scripts
    rm -f "$HOME/.local/bin/adhd-*.sh 2>/dev/null || true
    
    # Remove autostart entries
    rm -f "$HOME/.config/autostart/adhd-*.desktop 2>/dev/null || true
    
    # Remove desktop shortcuts
    rm -f "$HOME/Desktop/ADHD-"*.desktop 2>/dev/null || true
    
    # Kill any running ADHD-related processes
    pkill -f "adhd-" 2>/dev/null || true
    
    log_success "Restore complete! You may need to restart Plasma (logout/login)"
}

###############################################################################
# INSTALL FUNCTION - Main installation
###############################################################################

install_adhd_features() {
    log "=========================================="
    log "Installing ADHD Accessibility Features"
    log "=========================================="
    
    # Create backup first
    backup_current_config
    
    # Ensure bin directory exists
    mkdir -p "$HOME/.local/bin"
    
    ###########################################################################
    # 1. Install ADHD Accessibility Tools
    ###########################################################################
    log ""
    log "=== Step 1: Installing Accessibility Tools ==="
    
    if command -v pacman &> /dev/null; then
        log "Installing tools via pacman..."
        sudo pacman -Sy --noconfirm kmag kontrast mousetweaks 2>/dev/null || log_warning "Some packages may not be available"
    fi
    log_success "Accessibility tools checked"
    
    ###########################################################################
    # 2. Configure Notification System (Gentle, Non-Punitive)
    ###########################################################################
    log ""
    log "=== Step 2: Configuring Notifications ==="
    
    cat > "$HOME/.config/plasmanotifyrc" << 'EOF'
[Notifications]
BypassIdleWindow=true
BypassIdleWindowItemCategory[]=@Invalid()
CategoryExclude=()
CategorySwitchItemCategory[]=()
DoNotDisturb=false
DoNotDisturbWhenFullScreen=true
ExecuteDelay=5000
GroupingStrategy=category
InhibitionAppletSuppress=false
InhibitionAppletSuppressLevel=1
HistoryLimit=5
MaxItems=3
NotificationFilter=true
PopupPosition=TopCenter
ShowNextToMouse=false
SkipTimedSuppression=false
Sound=true
UseExternalSounds=false
UseNotificationColors=false
Volume=50
WallpaperNotification=true
X-KDE-NextToMouse=false
EOF
    log_success "Notification config - TopCenter, max 3 items, gentle delay"
    
    ###########################################################################
    # 3. Create Constraint-Based Task Launcher (Max 3 tasks)
    ###########################################################################
    log ""
    log "=== Step 3: Creating Constraint-Based Task Launcher ==="
    
    cat > "$HOME/.local/bin/adhd-task-launcher.sh" << 'EOFSCRIPT'
#!/bin/bash
###############################################################################
# ADHD Constraint-Based Task Launcher
# Limits visible tasks to 3 maximum - reduces decision paralysis
###############################################################################

TASK_FILE="$HOME/.config/adhd-tasks"
mkdir -p "$HOME/.config"
touch "$TASK_FILE"

# Use zenity for GUI selection
SELECTION=$(zenity --list \
    --title="ADHD Task Launcher (Max 3)" \
    --text="Select a task to work on:" \
    --column="Task" \
    --height=350 \
    --width=450 \
    $(head -n 3 "$TASK_FILE" 2>/dev/null || echo "") \
    "➕ Add new task..." \
    2>/dev/null)

if [ "$SELECTION" = "➕ Add new task..." ]; then
    NEW_TASK=$(zenity --entry \
        --title="Add New Task" \
        --text="What do you need to do?" \
        --entry-text="" \
        2>/dev/null)
    
    if [ -n "$NEW_TASK" ]; then
        # Add to top, keep only 3
        { echo "$NEW_TASK"; head -n 2 "$TASK_FILE" 2>/dev/null; } > "${TASK_FILE}.tmp"
        mv "${TASK_FILE}.tmp" "$TASK_FILE"
        zenity --info --text "Task added: $NEW_TASK" 2>/dev/null
    fi
elif [ -n "$SELECTION" ]; then
    # Move selected to top (mark as working on)
    grep -v "^$SELECTION$" "$TASK_FILE" > "${TASK_FILE}.tmp"
    echo "$SELECTION" > "$TASK_FILE"
    cat "${TASK_FILE}.tmp" >> "$TASK_FILE"
    sed -i '3,$d' "$TASK_FILE"
    rm "${TASK_FILE}.tmp"
    zenity --info --text "Working on: $SELECTION" 2>/dev/null
fi
EOFSCRIPT

chmod +x "$HOME/.local/bin/adhd-task-launcher.sh"
log_success "Task launcher created - keeps max 3 tasks visible"
    
    ###########################################################################
    # 4. Configure Auto-Save (Externalized Memory)
    ###########################################################################
    log ""
    log "=== Step 4: Configuring Auto-Save (Externalized Memory) ==="
    
    cat > "$HOME/.local/bin/adhd-session-save.sh" << 'EOFSCRIPT'
#!/bin/bash
###############################################################################
# ADHD Session Auto-Save - Externalizes memory
# Saves all open windows, workspace state, and current tasks
###############################################################################

SESSION_DIR="$HOME/.config/adhd-sessions"
mkdir -p "$SESSION_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SESSION_FILE="$SESSION_DIR/session_$TIMESTAMP"

# Save current desktop
qdbus org.kde.KWin /KWin org.kde.KWin.currentDesktop > "$SESSION_DIR/current-desktop.txt" 2>/dev/null

# Save open windows
qdbus org.kde.KWin /KWin org.kde.KWin.getWindowIds > "$SESSION_DIR/open-windows.txt" 2>/dev/null

# Save tasks
cp "$HOME/.config/adhd-tasks" "$SESSION_DIR/tasks.txt" 2>/dev/null

# Save timestamp
echo "$TIMESTAMP" > "$SESSION_DIR/latest.txt"

# Clean old sessions (keep last 10)
ls -t "$SESSION_DIR"/session_*.txt 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null

echo "Session saved: $TIMESTAMP"
EOFSCRIPT

chmod +x "$HOME/.local/bin/adhd-session-save.sh"

# Autostart session save
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/adhd-session-save.desktop" << 'EOF'
[Desktop Entry]
Comment=Auto-saves session state for ADHD memory support
Exec=/home/nxyme/.local/bin/adhd-session-save.sh
GenericName=Session Auto-Save
Icon=document-save
Name=ADHD Session Auto-Save
Type=Application
X-KDE-Autostart-enabled=true
X-KDE-Autostart-phase=1
EOF
    log_success "Auto-save configured - saves session state on login"
    
    ###########################################################################
    # 5. Focus Mode with Visual Indicators
    ###########################################################################
    log ""
    log "=== Step 5: Configuring Focus Mode ==="
    
    cat > "$HOME/.local/bin/adhd-focus.sh" << 'EOFSCRIPT'
#!/bin/bash
###############################################################################
# ADHD Focus Mode Toggle
# Enables distraction-free mode with visual indicators
###############################################################################

FOCUS_STATE="$HOME/.config/adhd-focus-mode"

if [ "$1" = "status" ]; then
    if [ -f "$FOCUS_STATE" ]; then
        echo "🎯 Focus Mode: ON"
    else
        echo "🎯 Focus Mode: OFF"
    fi
    exit 0
fi

if [ -f "$FOCUS_STATE" ]; then
    # Disable focus mode
    rm "$FOCUS_STATE"
    
    # Reset Night Color
    qdbus org.kde.KWin /NightColor org.kde.KWin.NightColor.setEnabled false 2>/dev/null || true
    
    # Notification
    notify-send "Focus Mode OFF" "Notifications restored" -i "dialog-information" 2>/dev/null || true
    
    echo "Focus mode disabled"
else
    # Enable focus mode
    touch "$FOCUS_STATE"
    
    # Enable warmer screen (less blue = less stimulating)
    qdbus org.kde.KWin /NightColor org.kde.KWin.NightColor.setEnabled true 2>/dev/null || true
    qdbus org.kde.KWin /NightColor org.kde.KWin.NightColor.setTemperature 3000 2>/dev/null || true
    
    notify-send "Focus Mode ON" "Screen warmer, stay focused!" -i "dialog-information" 2>/dev/null || true
    
    echo "Focus mode enabled"
fi
EOFSCRIPT

chmod +x "$HOME/.local/bin/adhd-focus.sh"
log_success "Focus mode toggle created - ~/.local/bin/adhd-focus.sh"
    
    ###########################################################################
    # 6. Visual Timers for Time Blindness
    ###########################################################################
    log ""
    log "=== Step 6: Creating Visual Timers ==="
    
    # Pomodoro Timer
    cat > "$HOME/.local/bin/adhd-pomodoro.sh" << 'EOFSCRIPT'
#!/bin/bash
###############################################################################
# ADHD Pomodoro Timer - Visual feedback for time blindness
###############################################################################

MINUTES=${1:-25}
SECONDS=$((MINUTES * 60))

notify-send "🍅 Pomodoro Started" "$MINUTES minutes - Focus time!" -i "chronometer" 2>/dev/null &

# Show countdown in terminal
while [ $SECONDS -gt 0 ]; do
    printf "\r⏱ %02d:%02d " $((SECONDS/60)) $((SECONDS%60))
    sleep 1
    SECONDS=$((SECONDS-1))
done

echo ""
notify-send "✅ Pomodoro Complete!" "Great job! Take a 5min break." -i "dialog-information" 2>/dev/null &

# Play sound if available
paplay /usr/share/sounds/freedesktop/stereo/complete.ogg 2>/dev/null || true
EOFSCRIPT

chmod +x "$HOME/.local/bin/adhd-pomodoro.sh"

# Quick 5min Timer
cat > "$HOME/.local/bin/adhd-quicktimer.sh" << 'EOFSCRIPT'
#!/bin/bash
###############################################################################
# ADHD Quick Timer - 5 minute timer
###############################################################################

SECONDS=300

while [ $SECONDS -gt 0 ]; do
    printf "\r⏱ %02d:%02d " $((SECONDS/60)) $((SECONDS%60))
    sleep 1
    SECONDS=$((SECONDS-1))
done

echo ""
notify-send "⏰ 5 Minutes Done!" "Time's up!" -i "dialog-information" 2>/dev/null &
EOFSCRIPT

chmod +x "$HOME/.local/bin/adhd-quicktimer.sh"

log_success "Visual timers created - pomodoro (25min) and quicktimer (5min)"
    
    ###########################################################################
    # 7. ADHD Control Dashboard
    ###########################################################################
    log ""
    log "=== Step 7: Creating ADHD Dashboard ==="
    
    cat > "$HOME/.local/bin/adhd-dashboard.sh" << 'EOFSCRIPT'
#!/bin/bash
###############################################################################
# ADHD Control Dashboard
# Simple central control for all ADHD features
###############################################################################

CHOICE=$(zenity --list \
    --title="🧠 ADHD Control Center" \
    --width=400 --height=500 \
    --text="Choose an action:" \
    --column="Action" \
    --column="Description" \
    "🎯 Start Focus Mode" "Enable focus (warmer screen)" \
    "⏹ Stop Focus Mode" "Disable focus mode" \
    "🍅 Pomodoro (25min)" "Start 25-minute focus timer" \
    "⚡ Quick Timer (5min)" "Start 5-minute timer" \
    "✅ Task Launcher" "Open 3-task selector" \
    "💾 Save Session" "Save current state" \
    "🧠 Current Tasks" "View your tasks" \
    "↩️ Restore Backup" "Undo all changes" \
    2>/dev/null)

case "$CHOICE" in
    "🎯 Start Focus Mode")
        ~/.local/bin/adhd-focus.sh on
        zenity --info --text "Focus mode ON!" 2>/dev/null
        ;;
    "⏹ Stop Focus Mode")
        ~/.local/bin/adhd-focus.sh off
        zenity --info --text "Focus mode OFF" 2>/dev/null
        ;;
    "🍅 Pomodoro (25min)")
        ~/.local/bin/adhd-pomodoro.sh &
        zenity --info --text "Pomodoro started!\n25 minutes of focus time." 2>/dev/null
        ;;
    "⚡ Quick Timer (5min)")
        ~/.local/bin/adhd-quicktimer.sh &
        zenity --info --text "Quick timer started!\n5 minutes." 2>/dev/null
        ;;
    "✅ Task Launcher")
        ~/.local/bin/adhd-task-launcher.sh
        ;;
    "💾 Save Session")
        ~/.local/bin/adhd-session-save.sh
        zenity --info --text "Session saved!" 2>/dev/null
        ;;
    "🧠 Current Tasks")
        TASKS=$(cat "$HOME/.config/adhd-tasks" 2>/dev/null || echo "No tasks")
        zenity --info --text "Your Tasks:\n\n$TASKS" 2>/dev/null
        ;;
    "↩️ Restore Backup")
        if zenity --question --text "Restore all original settings?\n\nThis will remove all ADHD customizations."; then
            cd "$(dirname "$0")"
            ./adhd-setup.sh restore
            zenity --info --text "Restored!" 2>/dev/null
        fi
        ;;
esac
EOFSCRIPT

chmod +x "$HOME/.local/bin/adhd-dashboard.sh"

# Desktop shortcut
cat > "$HOME/Desktop/ADHD-Control-Center.desktop" << 'EOF'
[Desktop Entry]
Comment=ADHD Control Center Dashboard
Exec=/home/nxyme/.local/bin/adhd-dashboard.sh
Icon=utilities-system-monitor
Name=🧠 ADHD Control Center
Type=Application
X-KDE-StartuplistId=adhd-dashboard
EOF

# Menu launcher
cat > "$HOME/.local/share/applications/adhd-dashboard.desktop" << 'EOF'
[Desktop Entry]
Comment=ADHD Control Center Dashboard
Exec=/home/nxyme/.local/bin/adhd-dashboard.sh
Icon=utilities-system-monitor
Name=🧠 ADHD Control Center
Type=Application
Categories=Utility;Accessibility;
EOF

log_success "Dashboard created - search 'ADHD' in app menu or use desktop shortcut"
    
    ###########################################################################
    # 8. Configure Visual Feedback (Enhanced animations)
    ###########################################################################
    log ""
    log "=== Step 8: Configuring Visual Feedback ==="
    
    # Add enhanced feedback settings
    cat >> "$HOME/.config/kdeglobals" << 'EOF'

[Feedback]
AnimationDurationFactor=0.5
EffectEnabled=true
Intensity=0.7
Priority=3

[Effects]
AnimateDesktop=true
AnimateWindows=true
AnimateIcons=true
AnimatePopups=true
AnimateCapplet=true
DialogButtonLayout=0
FadeMenu=true
FadeEffects=true
FadeSpeed=0.5
WindowDrag=false
FocusHighlight=true
DialogParent=false
TooltipFadeDuration=150
MenuFadeDuration=200
WindowShadow=true
DropShadow=true
EOF
    log_success "Visual feedback configured - clearer, more visible animations"
    
    ###########################################################################
    # 9. Create Desktop Launcher for Task Launcher
    ###########################################################################
    log ""
    log "=== Step 9: Creating Desktop Integration ==="
    
    cat > "$HOME/Desktop/ADHD-Task-Launcher.desktop" << 'EOF'
[Desktop Entry]
Comment=Open ADHD task launcher (max 3 tasks)
Exec=/home/nxyme/.local/bin/adhd-task-launcher.sh
Icon=task-attention
Name=🗋 ADHD Task Launcher
Type=Application
EOF

log_success "Desktop integration complete"
    
    ###############################################################################
    ###############################################################################
    # 10. Create Focus Writer Mode (Distraction-Free Writing)
    ###############################################################################
    log ""
    log "=== Step 10: Creating Focus Writer Mode ==="
    
    cat > "$HOME/.local/bin/adhd-focus-writer.sh" << 'EOFSCRIPT'
#!/bin/bash
###############################################################################
# ADHD Focus Writer Mode - Distraction-free writing environment
# Minimizes all non-essential UI for deep focus work
###############################################################################

TOGGLE_FILE="$HOME/.config/adhd-focus-writer"

toggle_focus_writer() {
    if [ -f "$TOGGLE_FILE" ]; then
        # Disable Focus Writer
        rm -f "$TOGGLE_FILE"
        
        # Restore desktop effects
        qdbus org.kde.KWin /KWin org.kde.KWin.reconfigure 2>/dev/null
        
        # Show taskbar
        qdbus org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.showTaskManager 2>/dev/null
        
        zenity --info --title="Focus Writer OFF" --text="Focus Writer mode disabled.\nTaskbar restored." 2>/dev/null
    else
        # Enable Focus Writer
        mkdir -p "$HOME/.config"
        touch "$TOGGLE_FILE"
        
        # Hide taskbar for clean writing
        qdbus org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.hideTaskManager 2>/dev/null
        
        # Disable animations for performance
        kwriteconfig5 --file kwinrc --group Compositing --key Enabled false 2>/dev/null
        
        # Set zenity fullscreen for writing
        zenity --info --title="Focus Writer ON" --text="Focus Writer mode enabled.\n\n🧠 Writing Mode Active:\n• Taskbar hidden\n• Animations disabled\n• Type to begin writing...\n\nPress Ctrl+C in terminal to disable when done." 2>/dev/null
    fi
}

# Launch distraction-free writer
launch_focus_writer() {
    mkdir -p "$HOME/.local/share/adhd-focus-writer"
    
    # Create a clean writing window
    zenity --text-info \
        --title="🧠 Focus Writer - Distraction Free" \
        --width=900 \
        --height=700 \
        --editable \
        --font="Noto Sans 14pt" &
}

# If no args, show menu
if [ -z "$1" ]; then
    CHOICE=$(zenity --list \
        --title="Focus Writer" \
        --text="Choose an option:" \
        --column="Option" \
        "Launch Focus Writer" \
        "Toggle Focus Mode" \
        2>/dev/null)
    
    case "$CHOICE" in
        "Launch Focus Writer") launch_focus_writer ;;
        "Toggle Focus Mode") toggle_focus_writer ;;
    esac
elif [ "$1" = "toggle" ]; then
    toggle_focus_writer
elif [ "$1" = "launch" ]; then
    launch_focus_writer
fi
EOFSCRIPT

    chmod +x "$HOME/.local/bin/adhd-focus-writer.sh"
    log_success "Focus Writer mode - distraction-free writing"
    
    ###############################################################################
    ###############################################################################
    # 11. Create Tree/Forest Focus Timer Alternative
    ###############################################################################
    log ""
    log "=== Step 11: Creating Tree Focus Timer ==="
    
    cat > "$HOME/.local/bin/adhd-tree-focus.sh" << 'EOFSCRIPT'
#!/bin/bash
###############################################################################
# ADHD Tree Focus Timer - Gamified focus like Forest app
# Grows a visual tree while you focus - kills tree if you leave app
###############################################################################

TREE_DIR="$HOME/.config/adhd-tree-focus"
mkdir -p "$TREE_DIR"

# Default durations (minutes)
FOCUS_TIME=25
BREAK_TIME=5

grow_tree() {
    local duration=$1
    local task_name=$2
    
    # Create tree visual
    local tree_size=0
    local max_size=20
    
    # Progress bar as tree growth
    for i in $(seq 1 $max_size); do
        local progress=$((i * 100 / max_size))
        
        # ASCII tree that grows
        local trunk=$(printf '%0.s█' $((i / 2)))
        local leaves=$(printf '🌿' $((i / 3)))
        
        # Show progress
        echo "$leaves$trunk"
        echo "Progress: $progress%"
        echo "Task: $task_name"
        
        sleep $((duration * 60 / max_size))
    done
    
    # Tree complete notification
    notify-send -u normal "🌳 Tree Complete!" "Great focus session: $task_name"
}

pomodoro_tree() {
    local task=$(zenity --entry \
        --title="🌳 Tree Focus Timer" \
        --text="What are you focusing on?" \
        --entry-text="My task" 2>/dev/null)
    
    if [ -n "$task" ]; then
        zenity --question \
            --title="Start Focus" \
            --text="Start $FOCUS_TIME minute focus session?\n\n🌱 Your tree will grow..." \
            --ok-label="Start Growing 🌳" \
            --cancel-label="Cancel" 2>/dev/null
        
        if [ $? -eq 0 ]; then
            # Run timer in background with visual
            (
                for i in $(seq 1 $FOCUS_TIME); do
                    local mins_left=$((FOCUS_TIME - i + 1))
                    notify-send -u low "🌳 Growing... $mins_left min left"
                    sleep 60
                done
                notify-send -u normal "🌳 Session Complete!" "Great job focusing on: $task"
            ) &
            
            # Show growing tree
            grow_tree $FOCUS_TIME "$task"
        fi
    fi
}

case "$1" in
    start) pomodoro_tree ;;
    *) pomodoro_tree ;;
esac
EOFSCRIPT

    chmod +x "$HOME/.local/bin/adhd-tree-focus.sh"
    log_success "Tree Focus Timer - gamified focus like Forest"
    
    ###############################################################################
    ###############################################################################
    # 12. Create Break Reminder (Movement/Stretch)
    ###############################################################################
    log ""
    log "=== Step 12: Creating Break Reminder ==="
    
    cat > "$HOME/.local/bin/adhd-break-reminder.sh" << 'EOFSCRIPT'
#!/bin/bash
###############################################################################
# ADHD Break Reminder - Gentle movement reminders
# Uses Pomodoro technique: 25min work, 5min movement break
###############################################################################

BREAK_INTERVAL=${1:-25}  # Default 25 minutes
BREAK_DURATION=${2:-5}  # Default 5 minute break

start_break_reminders() {
    while true; do
        sleep $((BREAK_INTERVAL * 60))
        
        # Show gentle notification
        notify-send -u low -t 10000 \
            "🧘 Break Time!" \
            "Time to stretch, move around, or rest your eyes.\n\nTake care of yourself! 💪"
        
        # Optional: Play gentle sound
        # paplay /usr/share/sounds/freedesktop/stereo/service-login.ogg 2>/dev/null &
        
        # Show zenity reminder
        zenity --question \
            --title="Break Time!" \
            --text="You've been working for $BREAK_INTERVAL minutes.\n\nTake a 5-minute break to:\n• Stretch\n• Get water\n• Rest your eyes\n\nReady to continue?" \
            --ok-label="Continue Working" \
            --cancel-label="Take Longer Break" 2>/dev/null
        
        if [ $? -ne 0 ]; then
            # User wants longer break - wait more
            sleep $((BREAK_DURATION * 60))
        fi
    done
}

case "$1" in
    start) start_break_reminders ;;
    stop) pkill -f adhd-break-reminder.sh ;;
    *) echo "Usage: $0 [start|stop]" ;;
esac
EOFSCRIPT

    chmod +x "$HOME/.local/bin/adhd-break-reminder.sh"
    log_success "Break Reminder - movement every 25 minutes"
    
    ###############################################################################
    ###############################################################################
    # 13. Create Sound Cues for Focus State
    ###############################################################################
    log ""
    log "=== Step 13: Creating Sound Cue System ==="
    
    cat > "$HOME/.local/bin/adhd-sound-cues.sh" << 'EOFSCRIPT'
#!/bin/bash
###############################################################################
# ADHD Sound Cues - Audio feedback for focus state changes
# Plays distinct sounds for: start focus, end focus, break, task complete
###############################################################################

SOUND_DIR="/usr/share/sounds"
FOCUS_SOUND="$SOUND_DIR/freedesktop/stereo/message.ogg"
BREAK_SOUND="$SOUND_DIR/freedesktop/stereo/service-logout.ogg"
DONE_SOUND="$SOUND_DIR/freedesktop/stereo/complete.ogg"

play_focus_start() {
    notify-send -u low "🎯 Focus Started" "Time to concentrate!"
    paplay "$FOCUS_SOUND" 2>/dev/null || echo "🔇"
}

play_focus_end() {
    notify-send -u normal "⏰ Focus Session Complete!" "Great work! Take a break."
    paplay "$DONE_SOUND" 2>/dev/null || echo "🔇"
}

play_break_start() {
    notify-send -u low "☕ Break Time" "Rest and recharge!"
    paplay "$BREAK_SOUND" 2>/dev/null || echo "🔇"
}

case "$1" in
    focus-start) play_focus_start ;;
    focus-end) play_focus_end ;;
    break) play_break_start ;;
    *)
        echo "ADHD Sound Cues - usage:"
        echo "  $0 focus-start  # Play start focus sound"
        echo "  $0 focus-end    # Play end focus sound"
        echo "  $0 break        # Play break sound"
        ;;
esac
EOFSCRIPT

    chmod +x "$HOME/.local/bin/adhd-sound-cues.sh"
    log_success "Sound Cues - audio feedback for focus states"
    
    ###############################################################################
    ###############################################################################
    # 14. Update Dashboard with New Tools
    ###############################################################################
    log ""
    log "=== Step 14: Updating Dashboard with New Tools ==="
    
    # Update dashboard to include new tools
    cat > "$HOME/.local/bin/adhd-dashboard.sh" << 'EOFSCRIPT'
#!/bin/bash
###############################################################################
# ADHD Control Dashboard - All-in-one control center
# Updated with all ADHD tools
###############################################################################

while true; do
    CHOICE=$(zenity --list \
        --title="🧠 ADHD Control Center" \
        --text="Choose an action:" \
        --column="Action" \
        "📋 Task Launcher (Max 3)" \
        "🍅 Pomodoro Timer (25min)" \
        "⏱️ Quick Timer (5min)" \
        "🎯 Toggle Focus Mode" \
        "✍️ Focus Writer" \
        "🌳 Tree Focus Timer" \
        "🔔 Break Reminder" \
        "🔊 Sound Cues Test" \
        "📊 View Current Status" \
        "❌ Exit" \
        --height=500 \
        --width=400 \
        2>/dev/null)
    
    case "$CHOICE" in
        "📋 Task Launcher (Max 3)")
            "$HOME/.local/bin/adhd-task-launcher.sh"
            ;;
        "🍅 Pomodoro Timer (25min)")
            "$HOME/.local/bin/adhd-pomodoro.sh"
            ;;
        "⏱️ Quick Timer (5min)")
            "$HOME/.local/bin/adhd-quicktimer.sh"
            ;;
        "🎯 Toggle Focus Mode")
            "$HOME/.local/bin/adhd-focus.sh" toggle
            ;;
        "✍️ Focus Writer")
            "$HOME/.local/bin/adhd-focus-writer.sh" launch
            ;;
        "🌳 Tree Focus Timer")
            "$HOME/.local/bin/adhd-tree-focus.sh" start
            ;;
        "🔔 Break Reminder")
            "$HOME/.local/bin/adhd-break-reminder.sh" start &
            zenity --info --text "Break reminder started!\nYou'll be reminded every 25 minutes." 2>/dev/null
            ;;
        "🔊 Sound Cues Test")
            "$HOME/.local/bin/adhd-sound-cues.sh" focus-start
            ;;
        "📊 View Current Status")
            "$HOME/.local/bin/adhd-dashboard.sh" status 2>/dev/null || (
                FOCUS_STATUS="ON" && [ ! -f "$HOME/.config/adhd-focus-mode" ] && FOCUS_STATUS="OFF"
                zenity --info --text "Current Status:\n\n🎯 Focus Mode: $FOCUS_STATUS\n📋 Tasks: Max 3 visible\n🍅 Timer: 25min Pomodoro\n🔔 Break: Every 25min\n\nRun './adhd-setup.sh status' for full status." 2>/dev/null
            )
            ;;
        "❌ Exit"|"")
            break
            ;;
    esac
done
EOFSCRIPT

    chmod +x "$HOME/.local/bin/adhd-dashboard.sh"
    log_success "Dashboard updated with all new tools"
    
    ###############################################################################
    ###############################################################################
    # 15. Configure Auto-Start for Frictionless Access
    ###############################################################################
    log ""
    log "=== Step 15: Configuring Auto-Start ==="
    
    mkdir -p "$HOME/.config/autostart"
    
    # Auto-start ADHD dashboard on login
    cat > "$HOME/.config/autostart/adhd-dashboard.desktop" << 'EOF'
[Desktop Entry]
Comment=ADHD Control Dashboard - Starts on login for quick access
Exec=/home/nxyme/.local/bin/adhd-dashboard.sh
Icon=utilities-system-monitor
Name=🧠 ADHD Control Center
Type=Application
X-KDE-AutostartEnabled=true
X-KDE-StartuplistId=adhd-dashboard
Categories=Utility;Accessibility;
EOF

    # Auto-start break reminder
    cat > "$HOME/.config/autostart/adhd-break-reminder.desktop" << 'EOF'
[Desktop Entry]
Comment=ADHD Break Reminder - Gentle movement reminders
Exec=/home/nxyme/.local/bin/adhd-break-reminder.sh start
Icon=clock
Name=🔔 ADHD Break Reminder
Type=Application
X-KDE-AutostartEnabled=false
X-KDE-StartuplistId=adhd-break-reminder
Categories=Utility;Accessibility;
EOF

    # Auto-start session saver
    cat > "$HOME/.config/autostart/adhd-session-save.desktop" << 'EOF'
[Desktop Entry]
Comment=ADHD Session Auto-Save - Externalizes memory
Exec=/home/nxyme/.local/bin/adhd-session-save.sh
Icon=document-save
Name=💾 ADHD Session Saver
Type=Application
X-KDE-AutostartEnabled=true
X-KDE-StartuplistId=adhd-session-save
Categories=Utility;Accessibility;
EOF

    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    
    log_success "Auto-start configured - dashboard available on login"
    
    ###############################################################################
    # Final Summary
    ###############################################################################
    log ""
    log "=========================================="
    log "✅ SETUP COMPLETE!"
    log "=========================================="
    log ""
    log "📋 Installed Features:"
    log "   • Constraint-based task launcher (max 3 tasks)"
    log "   • Visual Pomodoro timer (25min)"
    log "   • Quick timer (5min)"
    log "   • Focus mode (warmer screen)"
    log "   • Auto-save (externalized memory)"
    log "   • One-click reversible"
    log "   • Focus Writer (distraction-free writing)"
    log "   • Tree Focus Timer (Forest alternative)"
    log "   • Break Reminder (movement every 25min)"
    log "   • Sound Cues (audio feedback)"
    log ""
    log "🚀 How to use:"
    log "   • Dashboard: ~/.local/bin/adhd-dashboard.sh"
    log "   • Search 'ADHD' in your app menu"
    log "   • Desktop: 'ADHD Control Center' icon"
    log ""
    log "🔄 To reverse: ./adhd-setup.sh restore"
    log ""
    log "⚠️  Logout and login for changes to take effect!"
}

###############################################################################
# STATUS FUNCTION
###############################################################################

show_status() {
    echo ""
    echo "=== ADHD Linux Setup Status ==="
    echo ""
    
    # Check backup
    if [ -d "$BACKUP_DIR" ]; then
        echo "✓ Backup exists: $BACKUP_DIR"
    else
        echo "✗ No backup found"
    fi
    
    # Check scripts
    echo ""
    echo "📦 Installed Scripts:"
    [ -f "$HOME/.local/bin/adhd-focus.sh" ] && echo "  ✓ Focus Mode" || echo "  ✗ Focus Mode"
    [ -f "$HOME/.local/bin/adhd-task-launcher.sh" ] && echo "  ✓ Task Launcher" || echo "  ✗ Task Launcher"
    [ -f "$HOME/.local/bin/adhd-pomodoro.sh" ] && echo "  ✓ Pomodoro Timer" || echo "  ✗ Pomodoro"
    [ -f "$HOME/.local/bin/adhd-quicktimer.sh" ] && echo "  ✓ Quick Timer" || echo "  ✗ Quick Timer"
    [ -f "$HOME/.local/bin/adhd-dashboard.sh" ] && echo "  ✓ Dashboard" || echo "  ✗ Dashboard"
    
    # Focus mode status
    echo ""
    if [ -f "$HOME/.config/adhd-focus-mode" ]; then
        echo "🎯 Focus Mode: ON"
    else
        echo "🎯 Focus Mode: OFF"
    fi
    
    echo ""
}

###############################################################################
# MAIN
###############################################################################

case "$1" in
    install)
        install_adhd_features
        ;;
    backup)
        backup_current_config
        ;;
    restore)
        restore_from_backup
        ;;
    status)
        show_status
        ;;
    dashboard)
        "$HOME/.local/bin/adhd-dashboard.sh"
        ;;
    *)
        echo "🧠 ADHD Linux Accessibility Setup"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  install    - Install and configure all ADHD features"
        echo "  backup     - Create backup of current config"
        echo "  restore    - Restore from backup (one-click reversal)"
        echo "  status     - Show current status"
        echo "  dashboard - Open ADHD control dashboard"
        echo ""
        ;;
esac