---
stepsCompleted: ["step-01-init"]
inputDocuments: ["nx-dictate/README.md", "nx-dictate/ux-design-specification.md"]
workflowType: 'prd'
created: 2026-04-26
---

# Product Requirements Document - N-Xyme Dictate

**Author:** User  
**Date:** 2026-04-26  
**Version:** 1.0  
**Status:** Draft

---

## 1. Executive Summary

N-Xyme Dictate is a voice dictation system with full user control. It provides speech-to-text (STT) transcription via Faster-Whisper, global hotkey push-to-talk functionality that works from any application, automatic text injection into the active window, and a PyQt6 system tray interface with real-time status indicators.

The primary workflow is seamless: press the configured hotkey → speak → see transcription → text automatically typed into the cursor position. Target users are developers and power users who want frictionless dictation with minimal GUI overhead—no windows to manage, just a tray icon and quick access to settings.

**Key Value Propositions:**
- Sub-500ms hotkey-to-audio-capture latency
- Full local processing (no cloud dependency)
- Multi-backend text injection (wtype/ydotool/dotool/xdotool)
- Real-time status via system tray

---

## 2. Problem Statement

### 2.1 The Problem

Developers and power users face several challenges with existing dictation solutions:

1. **Context switching kills flow**: Existing tools require focus-stealing windows or manual copy-paste workflows
2. **Slow or inaccurate transcription**: Cloud-dependent services introduce latency; local tools lack accuracy
3. **Uncertain state**: Users cannot determine if the system is recording, processing, or idle
4. **Limited control**: No way to customize vocabulary, hotkeys, or injection behavior
5. **Platform fragmentation**: Text injection methods vary by display server (X11 vs Wayland)

### 2.2 Why This Matters

- **Developer productivity**: Code dictation can increase coding speed by 30-50% for verbose languages
- **Accessibility**: RSI sufferers need voice input as an alternative to keyboard
- **Flow preservation**: Minimal friction dictation preserves mental state during creative work

---

## 3. Target Users

| Persona | Description | Primary Needs | Pain Points |
|---------|-------------|---------------|-------------|
| **Developer Dan** | Writes code all day, types more than talks | Frictionless dictation without leaving IDE, keyboard shortcuts, custom vocabulary for code terms | Context switching kills flow, existing tools are slow or inaccurate |
| **Power User Pat** | Uses keyboard-driven workflows, avoids mouse | Global hotkey that works everywhere, observable state, quick settings access | Status unclear — is it recording? What model loaded? |
| **Accessibility Alex** | Needs voice input due to RSI or typing fatigue | Reliable transcription, error recovery, audio feedback of state | No visual confirmation, no error messages |

### User Goals

- **Start dictation in <500ms** from hotkey press to mic active
- **See current state at a glance** — tray icon color + tooltip
- **Recover from errors gracefully** — clear feedback, fallback to clipboard
- **Configure without leaving workflow** — settings accessible from tray menu

---

## 4. User Stories

### 4.1 Core Dictation

| ID | User Story | Acceptance Criteria |
|----|-----------|--------------------|
| US-1 | As a Developer, I want to press a global hotkey to start/stop recording so that I can dictate from any application | 1. Hotkey press triggers audio capture start<br>2. Hotkey release triggers transcription<br>3. Text appears in previously-focused window |
| US-2 | As a Power User, I want visual feedback on the current state so that I know when dictation is active | 1. Tray icon shows different colors for idle/recording/processing/error<br>2. Tooltip displays current state text<br>3. State changes within 50ms of event |

### 4.2 Text Injection

| ID | User Story | Acceptance Criteria |
|----|-----------|--------------------|
| US-3 | As a Developer, I want transcribed text automatically injected into my active window so that I don't need to copy-paste | 1. Text is typed into the previously-focused application<br>2. Injection latency <200ms<br>3. Fallback to clipboard if injection fails |
| US-4 | As an Accessibility User, I want clipboard fallback so that I can manually paste if injection fails | 1. Text is copied to system clipboard on injection failure<br>2. Notification informs user of clipboard fallback |

### 4.3 Configuration

| ID | User Story | Acceptance Criteria |
|----|-----------|--------------------|
| US-5 | As a Power User, I want to configure model size and audio device so that I can optimize for my hardware | 1. Settings dialog accessible from tray menu<br>2. Model can be changed (tiny/base/small/medium/large)<br>3. Audio input device is selectable |
| US-6 | As a Developer, I want custom vocabulary so that domain-specific terms are recognized accurately | 1. Custom vocabulary can be configured via settings<br>2. Terms are boosted in Whisper prompt |

### 4.4 API & Monitoring

| ID | User Story | Acceptance Criteria |
|----|-----------|--------------------|
| US-7 | As a Developer, I want an HTTP API so that I can integrate dictation with other tools | 1. API serves on configurable host:port<br>2. `/transcribe` endpoint accepts audio via JSON<br>3. `/health` returns service status |

---

## 5. Functional Requirements

### 5.1 Must Have (Priority: Critical)

| ID | Requirement | Description | Dependencies |
|----|-------------|-------------|--------------|
| FR-1 | Global Hotkey Push-to-Talk | Mouse back-button (or configurable key) triggers recording start/stop from any application | `pynput` or `evdev` |
| FR-2 | Text Injection | Auto-type transcribed text into active window using multi-backend chain (wtype → ydotool → dotool → xdotool) | Platform-specific binary |
| FR-3 | HTTP API Server | REST endpoints for transcription, health, stats; SSE for streaming | `aiohttp` |
| FR-4 | System Tray Icon | Visual indicator of idle/recording/processing/warning/error states via QSystemTrayIcon | `PyQt6` |

### 5.2 Should Have (Priority: High)

| ID | Requirement | Description | Dependencies |
|----|-------------|-------------|--------------|
| FR-5 | Settings Dialog | Model selection, audio device, hotkey, output behavior, feedback options via QDialog | `PyQt6` |
| FR-6 | Custom Vocabulary | Boost recognition of domain-specific terms via prompt injection | Configuration file |
| FR-7 | Live Typing Mode | Type as user speaks with phrase buffering and silence detection | Audio buffer management |

### 5.3 Could Have (Priority: Nice-to-Have)

| ID | Requirement | Description | Dependencies |
|----|-------------|-------------|--------------|
| FR-8 | Audio Level Visualization | Real-time audio input level display in settings dialog | `PyQt6` charts |
| FR-9 | Multi-language Support | Configure recognition language (default: auto-detect) | Faster-Whisper language pack |

### 5.4 Requirements traceability

| Requirement ID | User Story | Priority |
|----------------|----------|----------|
| FR-1 | US-1 | Must |
| FR-2 | US-3 | Must |
| FR-3 | US-7 | Must |
| FR-4 | US-2 | Must |
| FR-5 | US-5 | Should |
| FR-6 | US-6 | Should |
| FR-7 | US-1 | Should |
| FR-8 | US-2 | Could |
| FR-9 | US-1 | Could |

---

## 6. Non-Functional Requirements

### 6.1 Performance

| Metric | Target | Measurement |
|--------|-------|-------------|
| Hotkey to audio capture | <500ms | Timestamp delta |
| Audio buffer start | <100ms | First audio chunk received |
| Transcription latency (base model, CPU) | <3s per minute of audio | Engine timing |
| Text injection latency | <200ms | injection.call() duration |
| UI state update | <50ms | Signal emit to icon change |
| Memory (idle, model loaded) | Model VRAM + 100MB | psutil process |
| Memory (recording) | +50MB | Additional audio buffer |

### 6.2 Accessibility

- All audio feedback toggles work without display
- Tray tooltip provides current state text
- System notifications convey transcription results
- Error messages are user-facing, not just logs

### 6.3 Security

- No network audio streaming by default (local only)
- No persistent audio storage
- API can bind to localhost only (127.0.0.1 default)
- Config in `.env` — never commit credentials

### 6.4 Platform Support

| Platform | Status | Notes |
|----------|--------|-------|
| Linux (Wayland) | Primary | wtype/ydotool backends |
| Linux (X11) | Supported | xdotool/ydotool backends |
| macOS | Not planned | Future consideration |
| Windows | Not planned | Future consideration |

---

## 7. Technical Architecture

### 7.1 Component Diagram

```
nx_dictate/
├── run_dictate.py           # CLI entry point, argument parsing
├── api.py                 # aiohttp REST API server
├── injection.py           # Multi-backend text injection (wtype/ydotool/dotool/xdotool)
├── ui.py                 # PyQt6 GUI: TrayIconManager, SettingsDialog, DictationUI
├── hotword.py            # Voice activity detection
├── audio_processing.py    # Noise suppression, VAD, audio normalization
├── core/
│   ├── engine.py        # Faster-Whisper wrapper, model management
│   ├── hotkey.py       # Global hotkey registration (pynput/evdev)
│   └── state.py        # State management (IDLE/RECORDING/PROCESSING/ERROR)
└── server/
    └── main.py        # API server + WebSocket implementation
```

### 7.2 State Machine

```
IDLE → (hotkey press) → RECORDING → (hotkey release) → PROCESSING → (result) → IDLE
                                         ↓
                                      ERROR (on any failure) → IDLE
```

### 7.3 Data Flow

```
[Hotkey Event] → [Audio Capture (sounddevice)] → [Audio Processing]
                                                            ↓
[Text Injection] ← [Whisper Engine (faster-whisper)] ← [Raw Audio Buffer]
```

### 7.4 Backend Fallback Chain

Text injection supports multiple backends (auto-detected):

| Priority | Backend | Platform | Method |
|----------|---------|----------|--------|
| 1 | `wtype` | Wayland | Direct typing |
| 2 | `ydotool` | X11/Wayland | Direct typing |
| 3 | `dotool` | All | Pipe to stdin |
| 4 | `xdotool` | X11 | Ctrl+V paste |
| 5 | `wl-clipboard` | Wayland | Clipboard + paste |

---

## 8. UI/UX Requirements

### 8.1 Tray Icon

**Location**: System tray (Qt QSystemTrayIcon)

**Icon States**:

| State | Color | Hex | Tooltip | Behavior |
|-------|-------|-----|--------|----------|
| IDLE | Gray | #646464 | "N-Xyme Dictate — Ready" | No animation |
| RECORDING | Red | #DC2626 | "N-Xyme Dictate — Recording..." | Subtle pulse (optional) |
| PROCESSING | Blue | #2563EB | "N-Xyme Dictate — Processing..." | None |
| WARNING | Yellow | #D97706 | "N-Xyme Dictate — Low confidence" | None |
| ERROR | Orange | #DC2626 | "N-Xyme Dictate — Error" | None |

### 8.2 Tray Menu Structure

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

### 8.3 Settings Dialog

**Type**: QDialog, non-modal, opens from tray menu

**Layout**: Vertical stack of collapsible groups

| Group | Controls | Default |
|-------|---------|--------|
| Whisper Model | QComboBox | large-v3-turbo |
| Hotkey | QLabel (read-only) | Mouse Back (record) / Mouse Forward (send) |
| Audio | QCheckBox noise suppression, QCheckBox VAD | All checked |
| Output | QCheckBox copy to clipboard, QCheckBox auto-paste, QCheckBox auto-capitalize, QCheckBox auto-punctuate | All checked |
| Feedback | QCheckBox sound on start/stop/complete, QCheckBox show notifications, QSlider volume (70%) | All checked, 70% |
| Live Typing | QCheckBox type as user speaks, QSpinBox silence threshold (3s) | Checked, 3s |

### 8.4 Windowless Operation

- **No main application window** — all interaction via tray icon
- **Double-click tray icon** → toggle recording
- **Right-click tray icon** → full context menu
- **Settings dialog** is the only persistent window

---

## 9. API Specification

### 9.1 HTTP Endpoints

| Endpoint | Method | Description | Request | Response |
|---------|--------|------------|----------|----------|
| `/` | GET | Service info | — | `{name, version, status}` |
| `/health` | GET | Health check | — | `{status: "healthy", model_loaded: bool}` |
| `/transcribe` | POST | Transcribe audio | `{audio: "<base64>", language?: string}` | `{text: string, confidence: float}` |
| `/stats` | GET | Performance stats | — | `{sessions: int, words: int, avg_latency_ms: float}` |
| `/webhook` | POST | Configure webhook | `{url: string, events: string[]}` | `{success: bool}` |
| `/stream` | GET | SSE stream | — | Server-Sent Events stream |

### 9.2 Request/Response Formats

**POST /transcribe Request:**
```json
{
  "audio": "<base64_encoded_audio>",
  "language": "en"  // optional, auto-detect if omitted
}
```

**POST /transcribe Response:**
```json
{
  "text": "transcribed text",
  "confidence": 0.95,
  "duration_ms": 1500
}
```

### 9.3 API Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Invalid request (malformed JSON, missing audio) |
| 500 | Server error (transcription failed, model not loaded) |

### 9.4 Configuration

Environment variables (`.env` file):

| Variable | Default | Description |
|----------|---------|--------------|
| `API_HOST` | 127.0.0.1 | API bind address |
| `API_PORT` | 8765 | API port |
| `MODEL_SIZE` | base | Whisper model (tiny/base/small/medium/large) |
| `DEVICE` | auto | Compute device (auto/cpu/cuda) |
| `HOTKEY` | f6 | Global hotkey |
| `AUTO_INJECT` | false | Enable auto text injection |

---

## 10. Configuration

### 10.1 Environment Variables

Create `.env` file:

```bash
# API Server
API_HOST=127.0.0.1
API_PORT=8765

# Whisper
MODEL_SIZE=base
DEVICE=auto  # auto, cpu, cuda

# Hotkey
HOTKEY=f6

# Injection
AUTO_INJECT=false
```

### 10.2 Command Line Options

| Option | Description | Default |
|--------|-------------|----------|
| `--headless` | Run API only (no GUI) | False |
| `--host` | API host | 127.0.0.1 |
| `--port` | API port | 8765 |
| `--hotkey` | Enable global hotkey listener | False |
| `--injection` | Enable text injection | False |
| `--model` | Whisper model size | base |
| `--device` | Device (auto/cpu/cuda) | auto |
| `--test` | Run self-test | False |

---

## 11. Dependencies

### 11.1 Core Dependencies

| Package | Purpose | Version |
|---------|---------|---------|
| `faster-whisper` | Whisper CTranslate2 inference | Latest |
| `sounddevice` | Audio capture | Latest |
| `aiohttp` | HTTP server | Latest |
| `numpy` | Audio processing | Latest |
| `python-dotenv` | Configuration | Latest |

### 11.2 Optional Dependencies

| Package | Purpose | Used By |
|---------|---------|---------|
| `PyQt6` | GUI interface | ui.py |
| `pytest` | Testing | tests/ |
| `pynput` | Global hotkeys (X11) | core/hotkey.py |

### 11.3 System Requirements

```bash
# Ubuntu/Debian
sudo apt install portaudio19-dev python3-dev wl-clipboard

# Arch Linux
sudo pacman -S portaudio wl-clipboard

# Fedora
sudo dnf install portaudio-devel wl-clipboard
```

---

## 12. Success Metrics

### 12.1 Key Performance Indicators

| KPI | Target | Measurement |
|-----|--------|--------------|
| Hotkey-to-record latency | <500ms | Timestamp delta in logs |
| Transcription accuracy | >95% on clear audio | Manual validation set |
| Text injection success rate | >95% | Logged injection results |
| API uptime | >99.5% | Health check pings |
| User satisfaction | >4/5 | Survey (future) |

### 12.2 Usage Metrics

| Metric | Description |
|--------|-------------|
| `sessions` | Total dictation sessions completed |
| `words` | Total words transcribed |
| `avg_latency_ms` | Average transcription latency |
| `injection_failures` | Failed injection count (for fallback debugging) |

### 12.3 Acceptance Criteria

| ID | Criterion | Validation |
|----|-----------|-------------|
| AC1 | Tray icon appears on launch | Visual inspection |
| AC2 | Icon state changes on recording | Press back button → icon turns red |
| AC3 | Menu opens on right-click | Right-click tray |
| AC4 | Settings dialog opens | Click Settings in menu |
| AC5 | Recording starts on back button press | Audio capture indicator active |
| AC6 | Text injected on back button release | Text appears in active window |
| AC7 | Notification shows on transcription | System notification appears |
| AC8 | Stats update in menu | Sessions/words increment |
| AC9 | Error shows notification on failure | System notification with error |
| AC10 | Quit stops background services | No lingering processes |

---

## 13. Definitions

| Term | Definition |
|------|-------------|
| **Push-to-Talk** | Recording mode triggered by holding a hotkey; audio captured while hotkey is held |
| **Text Injection** | Automatic typing of transcribed text into the active application window |
| **Faster-Whisper** | CTranslate2-optimized Whisper implementation for faster inference |
| **VAD** | Voice Activity Detection - identifies speech vs. silence in audio |
| **SSE** | Server-Sent Events - unidirectional streaming from server to client |
| **Backend** | Platform-specific method for text injection (wtype, ydotool, etc.) |

---

## 14. References

- [README.md](../nx-dictate/README.md) - Project documentation
- [ux-design-specification.md](../nx-dictate/ux-design-specification.md) - Detailed UX specifications
- [Faster-Whisper Documentation](https://github.com/SYSTRAN/faster-whisper) - STT engine
- [PyQt6 Documentation](https://doc.qt.io/qtforpython/) - GUI framework

---

## 15. Revision History

| Version | Date | Author | Changes |
|--------|------|--------|---------|
| 1.0 | 2026-04-26 | User | Initial PRD creation |

---

*End of Document*