# ADHD-Friendly VM Menu System - Design Spec

## Overview
Interactive TUI menu system using `whiptail` for frictionless VM control.
Zero typing required — arrow keys + enter only.

## Design Principles
1. **Large text** — whiptail `--title` and `--menu` with tall rows
2. **High contrast** — white text on dark background, clear selection highlight
3. **Emoji icons** — visual anchors for each option
4. **Single-key shortcuts** — number keys for quick selection
5. **Visual feedback** — status bar at bottom, clear current selection
6. **Auto-refresh** — status screen updates every 2 seconds

## Menu Structure

### MAIN MENU
```
╔══════════════════════════════════════════╗
║        🖥️  NX-VM CONTROL CENTER         ║
╠══════════════════════════════════════════╣
║  1. 🚀 Start VM                          ║
║  2. 🛑 Stop VM                           ║
║  3. 📊 Status                            ║
║  4. 🔌 Connect                           ║
║  5. ⚙️  Settings                          ║
║  6. ❌ Quit                               ║
╚══════════════════════════════════════════╝
```

### START SUBMENU
```
╔══════════════════════════════════════════╗
║        🚀  START VM MODE                 ║
╠══════════════════════════════════════════╣
║  1. 🎵 Music Mode                        ║
║  2. 🎬 Video Mode                        ║
║  3. ⚡ Production                         ║
║  4. 🔙 Back                              ║
╚══════════════════════════════════════════╝
```

### SETTINGS SUBMENU
```
╔══════════════════════════════════════════╗
║        ⚙️  SETTINGS                       ║
╠══════════════════════════════════════════╣
║  1. 🔊 Audio Latency                     ║
║  2. 🧠 CPU Cores                         ║
║  3. 🎮 GPU Passthrough                   ║
║  4. 💾 Memory                            ║
║  5. 🔙 Back                              ║
╚══════════════════════════════════════════╝
```

## Technical Approach
- **whiptail** for all interactive dialogs
- **bash functions** for each menu screen
- **trap** for clean exit on Ctrl+C
- **loop-based** menu navigation (return to previous menu after action)
- **status polling** with background process for auto-refresh
- **color support** via ANSI escape codes in whiptail

## File Structure
```
nxvm-menu.sh          # Main menu script
nxvm-menu.conf        # Configuration file (optional)
```

## Success Criteria
1. Menu displays with large, readable text
2. Arrow keys navigate, Enter selects
3. Number keys provide quick selection
4. Status screen auto-refreshes
5. Clean exit on Quit or Ctrl+C
6. All submenus functional
7. Calls existing `nxvm` commands correctly
