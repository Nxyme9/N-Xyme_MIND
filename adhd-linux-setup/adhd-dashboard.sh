#!/bin/bash
DASH_DIR="$HOME/.config/adhd-dashboard"
mkdir -p "$DASH_DIR"

STREAK_FILE="$DASH_DIR/streak.txt"
FOCUS_FILE="$DASH_DIR/focus-sessions.txt"
ENERGY_FILE="$DASH_DIR/energy.txt"
NOTES_FILE="$DASH_DIR/notes.txt"

init() { [ -f "$STREAK_FILE" ] || echo "0" > "$STREAK_FILE"; [ -f "$FOCUS_FILE" ] || echo "0" > "$FOCUS_FILE"; [ -f "$ENERGY_FILE" ] || echo "5" > "$ENERGY_FILE"; [ -f "$NOTES_FILE" ] || touch "$NOTES_FILE"; }
init

while true; do
    STREAK=$(cat "$STREAK_FILE")
    FOCUS=$(cat "$FOCUS_FILE")
    ENERGY=$(cat "$ENERGY_FILE")
    LAST_NOTE=$(tail -3 "$NOTES_FILE" 2>/dev/null | head -1)
    
    EMOJI=""
    case $ENERGY in 0) EMOJI="😴";; 1) EMOJI="🥱";; 2) EMOJI="😐";; 3) EMOJI="🙂";; 4) EMOJI="⚡";; 5) EMOJI="🔥";; esac
    
    CHOICE=$(zenity --title="🧠 ADHD Dashboard" --text="
🔥 STREAK: $STREAK days | 🎯 Focus: $FOCUS sessions | $EMOJI Energy: $ENERGY/5

━━━━━━━━━━━━━━━━━━━━━━━━━━
$LAST_NOTE
" --ok-label="🔥 Log Day" --extra-button="🎯 Start Focus" --extra-button="🏁 End Focus" --extra-button="⚡ Set Energy" --extra-button="📝 Add Note" --extra-button="🔄 Reset Streak" --extra-button="❌ Quit" 2>/dev/null)
    
    case "$CHOICE" in
        "🎯 Start Focus")
            notify-send -u critical "🎯 FOCUS MODE" "No social media! Timer started." &
            ;;
        "🏁 End Focus")
            FOCUS=$((FOCUS+1)); echo "$FOCUS" > "$FOCUS_FILE"
            CELEB=("🎉 Amazing!" "🚀 On fire!" "💪 Brilliant!" "🌟 Outstanding!" "🔥 Monster!")
            notify-send -u normal "🎯 Focus Done!" "${CELEB[$((RANDOM%5))]} Session #$FOCUS"
            ;;
        "🔥 Log Day")
            STREAK=$((STREAK+1)); echo "$STREAK" > "$STREAK_FILE"
            notify-send -u normal "🔥 $STREAK Day Streak!" "You're doing great!"
            ;;
        "⚡ Set Energy")
            E=$(zenity --scale --title="Energy Level" --text="How do you feel?" --min-value=0 --max-value=5 --value=$ENERGY 2>/dev/null)
            [ -n "$E" ] && echo "$E" > "$ENERGY_FILE"
            ;;
        "📝 Add Note")
            NOTE=$(zenity --entry --title="Quick Note" --text="What's on your mind?" 2>/dev/null)
            [ -n "$NOTE" ] && echo "[$(date '+%H:%M')] $NOTE" >> "$NOTES_FILE"
            ;;
        "🔄 Reset Streak")
            zenity --question --text="Reset streak to 0?" && echo "0" > "$STREAK_FILE"
            ;;
        "❌ Quit"|"") exit 0 ;;
    esac
done