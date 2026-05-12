---
project: nx-dictate
type: desktop-app
created: 2026-04-26
---

# UX Design Specification — N-Xyme Dictate

## 1. Executive Summary

N-Xyme Dictate is a voice dictation system with full user control. It provides speech-to-text (STT) via Faster-Whisper, global hotkey push-to-talk from any application, automatic text injection into the active window, and a PyQt6 system tray interface with real-time status indicators. The primary workflow is: press hotkey → speak → see transcription → text auto-typed into cursor position. Target users are developers and power users who want full control over their dictation with minimal friction — no GUI windows to manage, just a tray icon and quick access to settings.

---

## 2. User Personas

| Persona | Description | Needs | Pain Points |
|---------|-----------|------|-----------|
| **Developer Dan** | Writes code all day, types more than talks | Frictionless dictation without leaving IDE, keyboard shortcuts, custom vocabulary for code terms | Context switching kills flow, existing tools are slow or inaccurate |
| **Power User Pat** | Uses keyboard-driven workflows, avoids mouse | Global hotkey that works everywhere, observable state, quick settings access | Status unclear — is it recording? What model loaded? |
| **Accessibility Alex** | Needs voice input due to RSI/typing fatigue | Reliable transcription, error recovery, audio feedback of state | No visual confirmation, no error messages |

### User Goals

- **Start dictation in <500ms** from hotkey press to mic active
- **See current state at a glance** — tray icon color + tooltip
- **Recover from errors gracefully** — clear feedback, fallback to clipboard
- **Configure without leaving workflow** — settings accessible from tray menu

---

## 3. Feature Requirements

### Core Features

| ID | Feature | Priority | Description |
|----|---------|----------|---------|
| F1 | Global Hotkey Push-to-Talk | Must | Mouse back-button (or configurable key) triggers recording start/stop |
| F2 | Text Injection | Must | Auto-type transcribed text into active window using ydotool/wtype/xdotool |
| F3 | HTTP API Server | Must | REST endpoints for transcription, health, stats; WebSocket for streaming |
| F4 | System Tray Icon | Must | Visual indicator of idle/recording/processing/warning/error states |
| F5 | Settings Dialog | Should | Model selection, audio device, hotkey, output behavior, feedback options |
| F6 | Custom Vocabulary | Should | Boost recognition of domain-specific terms via prompt injection |
| F7 | Live Typing Mode | Should | Type as user speaks with phrase buffering and silence detection |
| F8 | Audio Level Visualization | Could | Real-time audio input level display |
| F9 | Multi-language Support | Could | Configure recognition language (default: auto-detect) |

### State Machine

```
IDLE → (hotkey press) → RECORDING → (hotkey release) → PROCESSING → (result) → IDLE
                    ↓
                 ERROR (on any failure) → IDLE
```

### Transitions

| From | Event | To | Side Effects |
|-------|-------|-----|-----------|
| IDLE | `hotkey_press` | RECORDING | Start audio capture, update tray icon (red), play start beep |
| RECORDING | `hotkey_release` | PROCESSING | Stop audio capture, update tray icon (blue), play stop beep |
| PROCESSING | `transcription_done` | IDLE | Inject text, show notification, increment stats |
| * | `error` | ERROR | Show error notification, log, fall back to clipboard |
| ERROR | `hotkey_press` | RECORDING | Clear error, retry |

---

## 4. UI Layout

### 4.1 Tray Icon

**Location**: System tray (Qt QSystemTrayIcon)

**Icon States**:

| State | Color | Tooltip | Behavior |
|-------|-------|--------|---------|
| IDLE | Gray (#646464) | "N-Xyme Dictate — Ready" | No animation |
| RECORDING | Red (#DC2626) | "N-Xyme Dictate — Recording..." | Subtle pulse (optional) |
| PROCESSING | Blue (#2563EB) | "N-Xyme Dictate — Processing..." | None |
| WARNING | Yellow (#D97706) | "N-Xyme Dictate — Low confidence" | None |
| ERROR | Orange (#DC2626) | "N-Xyme Dictate — Error" | None |

### 4.2 Tray Menu Structure

```
[N-Xyme Dictate]           ← Header (disabled, bold)
──────────────────
Status: Ready          ← Current state (disabled)
Last: " transcribed text..."  ← Last result preview (disabled)
──────────────────
▶ Start Recording    ← Toggle action (recording state changes to "Stop")
──────────────────
🎧 Audio Device   →   ← Submenu with input device list
Current: [device name]  ← Current device indicator
──────────────────
⚙ Settings        ← Opens SettingsDialog
──────────────────
⚡ Live Typing Mode  ☐    ← Checkbox toggle
🔔 Sound Feedback  ☐    ← Checkbox toggle
──────────────────
📊 Sessions: 0 | Words: 0   ← Stats (disabled)
──────────────────
✖ Quit
```

### 4.3 Settings Dialog

**Type**: QDialog, non-modal, opens from tray menu

**Layout**: Vertical stack of collapsible groups

| Group | Controls | Default |
|-------|---------|--------|
| Whisper Model | QComboBox | large-v3-turbo |
| Hotkey | QLabel (read-only) | Mouse Back (record) / Mouse Forward (send) |
| Audio | QCheckBox noise suppression (checked), QCheckBox VAD (checked) |
| Output | QCheckBox copy to clipboard (checked), QCheckBox auto-paste (checked), QCheckBox auto-capitalize (checked), QCheckBox auto-punctuate (checked) |
| ADHD Feedback | QCheckBox sound on start (checked), QCheckBox sound on stop (checked), QCheckBox sound on complete (checked), QCheckBox show notifications (checked), QSlider volume (70%) |
| Live Typing | QCheckBox type as user speaks (checked), QSpinBox silence threshold seconds (3) |
| Close | QPushButton | Closes dialog, keeps app running |

### 4.4 Windowless Operation

- No main application window — all interaction via tray icon
- Double-click tray icon or tray menu → toggle recording
- Right-click tray icon → full context menu
- Settings dialog is the only persistent window

---

## 5. Interaction Flows

### 5.1 Core Dictation Flow

```
User presses mouse back button
    ↓
UI: IDLE → RECORDING
Audio: Begin capture from selected device
Tray icon: Red, tooltip "Recording..."
Sound (if enabled): Start beep
    ↓
User releases mouse back button
    ↓
UI: RECORDING → PROCESSING
Audio: Stop capture, send to Whisper
Tray icon: Blue, tooltip "Processing..."
Sound (if enabled): Stop beep
    ↓
Engine: Transcribe audio → text
    ↓
IF text AND auto_paste:
    injection.copy_and_paste(text)
    ↓
UI: PROCESSING → IDLE
Tray icon: Gray, tooltip "Ready"
Notify: "Transcribed: {text truncated}"
Stats: sessions += 1, words += word_count(text)
    ↓
ELSE on error:
    UI: → ERROR
    Tray notify: Error message
    Clipboard: Set text as fallback
    UI: → IDLE
```

### 5.2 Hotkey Button Map

| Button | Action | Default Behavior |
|--------|-------|-------------|
| Mouse Back (side) | Record | Press to start, release to stop |
| Mouse Forward (extra) | Send Enter | Press to insert newline in injected text |
| Mouse Middle (middle) | Language | Cycle through supported languages |

### 5.3 Error Recovery Flow

```
Transcription failure
    ↓
1. Log error locally
2. Set tray icon to ERROR (orange)
3. Show tray notification: "Transcription failed: {reason}"
4. Fallback: Copy text to clipboard (if partial result exists)
5. User manually Ctrl+V pastes
    ↓
Clear error on next recording press
```

---

## 6. Visual Design

### 6.1 Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `neutral` | #1F2937 | Menu background (dark mode) |
| `neutral-light` | #E5E7EB | Menu background (light mode) |
| `primary-idle` | #646464 | Idle tray icon |
| `primary-recording` | #DC2626 | Recording state |
| `primary-processing` | #2563EB | Processing state |
| `primary-warning` | #D97706 | Warning state |
| `primary-error` | #DC2626 | Error state |
| `accent` | #3B82F6 | Selected items |
| `text-primary` | #F9FAFB | Menu text |
| `text-secondary` | #9CA3AF | Disabled/secondary text |

### 6.2 Typography

| Element | Font | Size | Weight |
|---------|------|------|-------|
| Menu header | System UI | 12px | Bold |
| Menu items | System UI | 12px | Regular |
| Settings title | Sans Serif | 14px | Bold |
| Settings group | Sans Serif | 12px | Regular |
| Tooltip | System UI | 11px | Regular |

### 6.3 Icons

- Use system microphone icons from `/usr/share/icons/*/48x48/apps/audio-*.png` if available
- Fallback: Programmatically generated colored circle (64x64px) via QPainter
- No external icon dependencies for core functionality

### 6.4 Feedback Sounds

| Event | Sound | Default On |
|-------|-------|---------|
| Recording start | Short beep (440Hz, 50ms) | Yes |
| Recording stop | Short beep (440Hz, 50ms) | Yes |
| Transcription complete | Success chime (880Hz→1760Hz, 100ms) | Yes |
| Error | Error tone (220Hz, 200ms) | Yes |

Volume: 0–100%, default 70%

---

## 7. Non-Functional Requirements

### 7.1 Performance

| Metric | Target | Measurement |
|--------|-------|----------|
| Hotkey to audio capture | <500ms | Timestamp delta |
| Audio buffer start | <100ms | First audio chunk received |
| Transcription latency (base model, CPU) | <3s per minute of audio | Engine timing |
| Text injection latency | <200ms | injection.call() duration |
| UI state update | <50ms | Signal emit to icon change |
| Memory (idle, model loaded) | Model VRAM + 100MB | psutil process |
| Memory (recording) | +50MB | Additional audio buffer |

### 7.2 Accessibility

- All audio feedback toggles work without display
- Tray tooltip provides current state text
- System notifications convey transcription results
- Error messages are user-facing, not just logs

### 7.3 Security

- No network audio streaming by default (local only)
- No persistent audio storage
- API can bind to localhost only (127.0.0.1 default)
- Config in `.env` — never commit credentials

### 7.4 Platform

- **Primary**: Linux (Wayland/X11)
- **Audio backend**: PortAudio via sounddevice
- **Text injection**: wtype → ydotool → dotool → xdotool (fallback chain)
- **Hotkey**: evdev for mouse buttons, pynput disabled (Wayland-native)

---

## 8. Technical UI Components

### 8.1 Component Architecture

```
DictationUI
├── QApplication (singleton)
├── TrayIconManager
│   ├── QSystemTrayIcon
│   ├── QMenu (context menu)
│   └── SignalEmitter (Qt signals)
└── SettingsDialog
    ├── QGroupBox (6 sections)
    └── QWidget (controls)
```

### 8.2 Signal Map

| Signal | Type | Sender | Receiver | Action |
|--------|------|--------|---------|---------|
| `state_changed(str)` | pyqtSignal | DictationUI | TrayIconManager | update_state() |
| `text_received(str)` | pyqtSignal | DictationUI | TrayIconManager | notify_text() |
| `error_occurred(str)` | pyqtSignal | DictationUI | TrayIconManager | notify() + set_warning |

### 8.3 Key Bindings Reference

| Action | Default | Configurable |
|--------|---------|--------------|
| Start/stop recording | Mouse Back (BTN_SIDE) | Via HotkeyConfig |
| Send Enter | Mouse Forward (BTN_EXTRA) | Via HotkeyConfig |
| Cycle language | Mouse Middle (BTN_MIDDLE) | Via HotkeyConfig |
| Open settings | Tray double-click | No |
| Quit | Menu → Quit | No |

### 8.4 API Reference (for Frontend Integration)

```python
# Internal API (ui.py)
class DictationUI:
    def initialize(on_toggle: Callable, on_quit: Callable) -> bool
    def update_state(state: str)          # "idle", "recording", "processing", "warning", "error"
    def notify_text(text: str)          # Show transcription notification
    def notify(message: str)          # Show error notification
    def show_settings()               # Open SettingsDialog
    def run()                       # Enter QApplication event loop
    def quit()                      # Exit cleanly
```

---

## 9. Acceptance Criteria

| ID | Criterion | Validation |
|----|-----------|------------|
| AC1 | Tray icon appears on launch | Visual inspection |
| AC2 | Icon state changes on recording | Press back button → icon turns red |
| AC3 | Menu opens on right-click | Right-click tray |
| AC4 | Settings dialog opens | Click ⚙ Settings |
| AC5 | Recording starts on back button press | Audio capture active indicator |
| AC6 | Text injected on back button release | Text appears in active window |
| AC7 | Notification shows on transcription | System notification appears |
| AC8 | Stats update in menu | Sessions/words increment |
| AC9 | Error shows notification on failure | System notification with error |
| AC10 | Quit stops background services | No lingering processes |

---

## 10. File Reference

| File | Purpose |
|------|---------|
| `run_dictate.py` | CLI entry point, argument parsing |
| `ui.py` | PyQt6 implementation: TrayIconManager, SettingsDialog, DictationUI |
| `core/engine.py` | Faster-Whisper wrapper, model management |
| `core/hotkey.py` | Global hotkey (evdev) listener |
| `injection.py` | Text injection via ydotool/wtype/xdotool |
| `server/main.py` | WebSocket API for remote clients |
| `.env` | Configuration (API_HOST, API_PORT, MODEL_SIZE, HOTKEY, AUTO_INJECT) |