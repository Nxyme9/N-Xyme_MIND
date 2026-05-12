#!/usr/bin/env bash
#
# nxvm-menu.sh — ADHD-Friendly Interactive VM Control Menu
# Uses whiptail for TUI. Arrow keys + Enter only. No typing required.
#

set -euo pipefail

command -v whiptail >/dev/null 2>&1 || { echo "❌ whiptail is required but not installed."; exit 1; }

# ──────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────

# NX-VM command path (adjust if needed)
NXVM_CMD="${NXVM_CMD:-nxvm}"

# Menu dimensions
MENU_HEIGHT=20
MENU_WIDTH=70
MENU_ITEM_HEIGHT=8

# Colors (ANSI escape codes for whiptail)
export NEWT_COLORS='
    root=white,black
    border=white,black
    window=lightgray,black
    shadow=black,gray
    title=yellow,black
    button=black,cyan
    actbutton=white,red
    checkbox=white,black
    actcheckbox=white,red
    entry=white,black
    diskentry=lightgray,black
    labentry=white,black
    text=white,black
    actsellabel=white,red
    compactbutton=white,black
    helpline=cyan,black
    actselline=white,red
'

# ──────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ──────────────────────────────────────────────────────────────

# Clean exit handler
cleanup() {
    clear
    echo -e "\n👋 NX-VM Menu exited. Goodbye!\n"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# Clear screen before each menu
clear_screen() {
    clear
}

# Show a brief message then return to menu
show_message() {
    local title="$1"
    local message="$2"
    whiptail --title "$title" \
             --msgbox "\n${message}\n" \
             12 60
}

# Show a yes/no confirmation
confirm_action() {
    local title="$1"
    local message="$2"
    whiptail --title "$title" \
             --yesno "\n${message}\n" \
             10 60
}

# ──────────────────────────────────────────────────────────────
# VM OPERATIONS
# ──────────────────────────────────────────────────────────────

vm_start() {
    local mode="$1"
    if $NXVM_CMD start "$mode" 2>&1; then
        show_message "✅ Success" "VM started in ${mode} mode! 🚀"
    else
        show_message "❌ Error" "Failed to start VM in ${mode} mode."
    fi
}

vm_stop() {
    if confirm_action "🛑 Stop VM" "Are you sure you want to stop the VM?"; then
        if $NXVM_CMD stop 2>&1; then
            show_message "✅ Success" "VM stopped successfully! 🛑"
        else
            show_message "❌ Error" "Failed to stop VM."
        fi
    fi
}

vm_status() {
    local status_output
    status_output=$($NXVM_CMD status 2>&1 || echo "VM is not running")
    show_message "📊 VM Status" "${status_output}"
}

vm_connect() {
    if confirm_action "🔌 Connect" "Connect to the running VM?"; then
        if $NXVM_CMD connect 2>&1; then
            show_message "✅ Connected" "Connected to VM! 🔌"
        else
            show_message "❌ Error" "Failed to connect to VM."
        fi
    fi
}

# ──────────────────────────────────────────────────────────────
# SETTINGS FUNCTIONS
# ──────────────────────────────────────────────────────────────

setting_audio_latency() {
    local choice
    choice=$(whiptail --title "🔊 Audio Latency" \
                      --menu "\nSelect audio latency mode:\n" \
                      $MENU_HEIGHT $MENU_WIDTH $MENU_ITEM_HEIGHT \
                      1 "🎵 Low (10ms) — Music production" \
                      2 "🎬 Medium (50ms) — Video editing" \
                      3 "⚡ High (100ms) — General use" \
                      3>&1 1>&2 2>&3) || return

    case "$choice" in
        1) $NXVM_CMD set audio-latency low 2>&1 && show_message "✅ Updated" "Audio latency set to LOW (10ms) 🎵" ;;
        2) $NXVM_CMD set audio-latency medium 2>&1 && show_message "✅ Updated" "Audio latency set to MEDIUM (50ms) 🎬" ;;
        3) $NXVM_CMD set audio-latency high 2>&1 && show_message "✅ Updated" "Audio latency set to HIGH (100ms) ⚡" ;;
    esac
}

setting_cpu_cores() {
    local choice
    choice=$(whiptail --title "🧠 CPU Cores" \
                      --menu "\nSelect number of CPU cores:\n" \
                      $MENU_HEIGHT $MENU_WIDTH $MENU_ITEM_HEIGHT \
                      1 "🔹 2 cores — Light tasks" \
                      2 "🔹🔹 4 cores — Normal use" \
                      3 "🔹🔹🔹 8 cores — Heavy workloads" \
                      4 "🔹🔹🔹🔹 16 cores — Maximum power" \
                      3>&1 1>&2 2>&3) || return

    local cores
    case "$choice" in
        1) cores=2 ;;
        2) cores=4 ;;
        3) cores=8 ;;
        4) cores=16 ;;
        *) return ;;
    esac

    $NXVM_CMD set cpu-cores "$cores" 2>&1 && show_message "✅ Updated" "CPU cores set to ${cores} 🧠"
}

setting_gpu_passthrough() {
    local choice
    choice=$(whiptail --title "🎮 GPU Passthrough" \
                      --menu "\nConfigure GPU passthrough:\n" \
                      $MENU_HEIGHT $MENU_WIDTH $MENU_ITEM_HEIGHT \
                      1 "✅ Enable — Full GPU access" \
                      2 "❌ Disable — Use virtual GPU" \
                      3>&1 1>&2 2>&3) || return

    case "$choice" in
        1) $NXVM_CMD set gpu-passthrough enable 2>&1 && show_message "✅ Enabled" "GPU passthrough enabled! 🎮" ;;
        2) $NXVM_CMD set gpu-passthrough disable 2>&1 && show_message "✅ Disabled" "GPU passthrough disabled." ;;
    esac
}

setting_memory() {
    local choice
    choice=$(whiptail --title "💾 Memory" \
                      --menu "\nSelect VM memory allocation:\n" \
                      $MENU_HEIGHT $MENU_WIDTH $MENU_ITEM_HEIGHT \
                      1 "📦 4 GB — Light tasks" \
                      2 "📦📦 8 GB — Normal use" \
                      3 "📦📦📦 16 GB — Heavy workloads" \
                      4 "📦📦📦📦 32 GB — Maximum" \
                      3>&1 1>&2 2>&3) || return

    local mem
    case "$choice" in
        1) mem="4G" ;;
        2) mem="8G" ;;
        3) mem="16G" ;;
        4) mem="32G" ;;
        *) return ;;
    esac

    $NXVM_CMD set memory "$mem" 2>&1 && show_message "✅ Updated" "Memory set to ${mem} 💾"
}

# ──────────────────────────────────────────────────────────────
# AUTO-REFRESH STATUS DISPLAY
# ──────────────────────────────────────────────────────────────

show_status_display() {
    while true; do
        local status_info
        status_info=$($NXVM_CMD status 2>&1 || echo "VM is not running")

        local current_time
        current_time=$(date '+%H:%M:%S')

        whiptail --title "📊 Live Status — ${current_time}" \
                 --msgbox "\n${status_info}\n\n───────────────────────────────────────\nAuto-refreshing… Press ESC to return to menu.\n" \
                 16 70 2>/dev/null || return
    done
}

# ──────────────────────────────────────────────────────────────
# MENU SCREENS
# ──────────────────────────────────────────────────────────────

menu_settings() {
    local choice
    while true; do
        choice=$(whiptail --title "⚙️  SETTINGS" \
                          --menu "\n  Configure VM settings:\n" \
                          $MENU_HEIGHT $MENU_WIDTH $MENU_ITEM_HEIGHT \
                          1 "🔊 Audio Latency" \
                          2 "🧠 CPU Cores" \
                          3 "🎮 GPU Passthrough" \
                          4 "💾 Memory" \
                          5 "🔙 Back to Main Menu" \
                          3>&1 1>&2 2>&3) || return

        case "$choice" in
            1) setting_audio_latency ;;
            2) setting_cpu_cores ;;
            3) setting_gpu_passthrough ;;
            4) setting_memory ;;
            5) return ;;
        esac
    done
}

menu_start_vm() {
    local choice
    while true; do
        choice=$(whiptail --title "🚀 START VM" \
                          --menu "\n  Select VM mode:\n" \
                          $MENU_HEIGHT $MENU_WIDTH $MENU_ITEM_HEIGHT \
                          1 "🎵 Music Mode — Low latency audio" \
                          2 "🎬 Video Mode — GPU optimized" \
                          3 "⚡ Production — Full power" \
                          4 "🔙 Back to Main Menu" \
                          3>&1 1>&2 2>&3) || return

        case "$choice" in
            1) vm_start "music" ;;
            2) vm_start "video" ;;
            3) vm_start "production" ;;
            4) return ;;
        esac
    done
}

menu_main() {
    local choice
    while true; do
        choice=$(whiptail --title "🖥️  NX-VM CONTROL CENTER" \
                          --menu "\n  Select an action:\n" \
                          $MENU_HEIGHT $MENU_WIDTH $MENU_ITEM_HEIGHT \
                          1 "🚀 Start VM" \
                          2 "🛑 Stop VM" \
                          3 "📊 Status" \
                          4 "🔌 Connect" \
                          5 "⚙️  Settings" \
                          6 "❌ Quit" \
                          3>&1 1>&2 2>&3)

        case "$choice" in
            1) menu_start_vm ;;
            2) vm_stop ;;
            3) show_status_display ;;
            4) vm_connect ;;
            5) menu_settings ;;
            6)
                if confirm_action "❌ Quit" "Exit NX-VM Control Center?"; then
                    cleanup
                fi
                ;;
            *) cleanup ;;
        esac
    done
}

# ──────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ──────────────────────────────────────────────────────────────

main() {
    clear_screen
    menu_main
}

main "$@"
