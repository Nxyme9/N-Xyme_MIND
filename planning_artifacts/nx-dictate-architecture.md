---
stepsCompleted: ["step-01-init"]
inputDocuments: ["nx-dictate-prd.md", "nx-dictate/ux-design-specification.md"]
workflowType: 'architecture'
created: 2026-04-26
---

# Technical Architecture - N-Xyme Dictate

**Author:** Architecture Team  
**Date:** 2026-04-26  
**Version:** 1.0  
**Status:** Approved

---

## 1. Architecture Principles

### 1.1 Core Design Tenets

| Principle | Rationale | Implementation |
|-----------|----------|----------------|
| **Fast startup, low latency** | Sub-500ms hotkey-to-audio-capture per PRD | Lazy model loading, pre-initialized audio stream |
| **Modular design** | Separable concerns, testability | Distinct components with clear interfaces |
| **Graceful degradation** | No single point of failure | Backend fallback chain, clipboard fallback |
| **Local-only processing** | Privacy, no cloud dependency | Faster-Whisper CPU/GPU inference |
| **Windowless operation** | Flow preservation | System tray only, no main window |

### 1.2 Architecture Decisions

| Decision | Trade-off | Rationale |
|----------|----------|----------|
| **aiohttp over FastAPI** | Less opinionated, lower overhead | Sufficient for REST endpoints, simpler dependency tree |
| **PyQt6 over Tkinter** | Native system tray, better event handling | Required for QSystemTrayIcon |
| **sounddevice over pyaudio** | Python 3.10+ compatibility, better buffer management | Current standard |
| **evdev for hotkeys** | Wayland native input capture | Works without display focus |
| **State machine pattern** | Explicit state transitions, easier debugging | Required per UX spec |

---

## 2. Component Architecture

### 2.1 Package Structure

```
nx_dictate/
├── __init__.py                 # Package version, exports
├── run_dictate.py              # CLI entry point, argument parsing
├── main.py                    # Application orchestrator
│
├── api.py                     # aiohttp REST API (legacy, use server/)
├── injection.py               # Text injection (legacy, use core/)
│
├── ui.py                     # PyQt6 GUI: TrayIconManager, SettingsDialog
├── hotword.py                # Voice activity detection
├── audio_processing.py       # Noise suppression, normalization
│
├── core/
│   ├── __init__.py
│   ├── engine.py            # Faster-Whisper wrapper, model management
│   ├── hotkey.py          # Global hotkey listener (evdev/pynput)
│   ├── state.py          # State machine (IDLE/RECORDING/PROCESSING/WARNING/ERROR)
│   └── injection.py     # Text injection backends (wtype/ydotool/dotool/xdotool)
│
├── server/
│   ├── __init__.py
│   └── main.py          # aiohttp server + WebSocket/SSE
│
├── audio/
│   ├── __init__.py
│   ├── capture.py      # Audio capture (sounddevice)
│   ├── buffer.py     # Circular audio buffer
│   └── processing.py # VAD, noise suppression
│
├── config/
│   ├── __init__.py
│   ├── loader.py     # Environment + config file loader
│   └── schema.py    # Configuration schema validation
│
└── utils/
    ├── __init__.py
    ├── logging.py   # Structured logging
    └── notify.py    # System notifications
```

### 2.2 Component Responsibilities

#### Core Components

| Component | Responsibilities | Public API |
|-----------|-----------------|-------------|
| **`core.engine.WhisperEngine`** | Model loading, transcription, vocabulary boost | `load(model_size, device)`, `transcribe(audio)`, `unload()` |
| **`core.state.StateMachine`** | State transitions, event handling | `transition(event)`, `get_state()`, `on_change(callback)` |
| **`core.hotkey.HotkeyListener`** | Global hotkey registration, event dispatch | `start()`, `stop()`, `on_press(callback)`, `on_release(callback)` |
| **`core.injection.TextInjector`** | Backend detection, text injection, clipboard fallback | `inject(text)`, `copy_to_clipboard(text)`, `get_backend()` |

#### Audio Components

| Component | Responsibilities | Public API |
|-----------|-----------------|-------------|
| **`audio.capture.AudioCapture`** | Device enumeration, stream management | `list_devices()`, `start(device_id)`, `stop()`, `on_audio(callback)` |
| **`audio.buffer.AudioBuffer`** | Ring buffer for audio chunks | `write(data)`, `read()`, `clear()`, `size()` |
| **`audio.processing.AudioProcessor`** | VAD, noise suppression, normalization | `process(audio_chunk)`, `set_vad_enabled(bool)` |

#### UI Components

| Component | Responsibilities | Public API |
|-----------|-----------------|-------------|
| **`ui.TrayIconManager`** | System tray, icon states, context menu | `set_icon(state)`, `set_tooltip(text)`, `show_menu()` |
| **`ui.SettingsDialog`** | Configuration UI, model/device selection | `open()`, `close()`, `get_settings()` |
| **`ui.DictationUI`** | Application UI orchestrator | `initialize()`, `update_state(state)`, `run()`, `quit()` |

#### Server Components

| Component | Responsibilities | Public API |
|-----------|-----------------|-------------|
| **`server.main.APIServer`** | HTTP server, WebSocket, SSE | `start(host, port)`, `stop()`, `on_transcribe(callback)` |

#### Utility Components

| Component | Responsibilities | Public API |
|-----------|-----------------|-------------|
| **`config.loader.ConfigLoader`** | Load .env, args, config file | `load()`, `get(key)`, `set(key, value)` |
| **`utils.logging.logger`** | Structured logging with rotation | `setup()`, `get(name)` |
| **`utils.notify.Notifier`** | System notifications | `notify(title, message)`, `notify_error(error)` |

---

## 3. Data Flow

### 3.1 Core Dictation Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION                            │
│  [Hotkey Press] ────────────────────────► [Hotkey Release]        │
└─────────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        STATE: IDLE → RECORDING                                        │
│  ┌────────────────────────────────────────────────────────────────────────────┐   │
│  │ core.state.StateMachine.transition("hotkey_press")                            │   │
│  │   → Notify: state_changed(RECORDING)                                        │   │
│  │   → TrayIconManager.set_icon(RED)                                           │   │
│  └────────────────────────────────────────────────────────────────────────────┘   │
└────────────────��────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          AUDIO CAPTURE                                        │
│  ┌────────────────────────────────────────────────────────────────────────────┐   │
│  │ audio.capture.AudioCapture.start(device_id)                                │   │
│  │   → sounddevice.InputStream callback                                       │   │
│  │   → audio.buffer.AudioBuffer.write(chunk)                                  │   │
│  └────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       STATE: RECORDING → PROCESSING                                     │
│  ┌────────────────────────────────────────────────────────────────────────────┐   │
│  │ core.state.StateMachine.transition("hotkey_release")                       │   │
│  │   → Notify: state_changed(PROCESSING)                                       │   │
│  │   → TrayIconManager.set_icon(BLUE)                                        │   │
│  │   → audio.buffer.AudioBuffer.read() → audio                               │   │
│  └────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       AUDIO PROCESSING (optional)                                      │
│  ┌────────────────────────────────────────────────────────────────────────────┐   │
│  │ audio.processing.AudioProcessor.process(audio)                             │   │
│  │   → VAD: trim silence at start/end                                          ���   ���
│  │   → Noise suppression (if enabled)                                        │   │
│  │   → Normalization: peak normalization                                      │   │
│  └────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       TRANSCRIPTION                                          │
│  ┌────────────────────────────────────────────────────────────────────────────┐   │
│  │ core.engine.WhisperEngine.transcribe(audio)                                  │   │
│  │   → faster_whisper.WhisperModel.transcribe()                            │   │
│  │   → Return: (text, language, chunks)                                     │   │
│  └────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                  ��
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       TEXT INJECTION                                         │
│  ┌────────────────────────────────────────────────────────────────────────────┐   │
│  │ IF config.auto_inject:                                                   │   │
│  │   core.injection.TextInjector.inject(text)                                  │   │
│  │   → Try: wtype → ydotool → dotool → xdotool (fallback chain)               │   │
│  │   → On failure: copy_to_clipboard(text)                                 │   │
│  │   → notify("Copied to clipboard")                                      │   │
│  │ ELSE:                                                                  │   │
│  │   notify("Transcribed: {text}")                                          │   │
│  └────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       STATE: PROCESSING → IDLE                                        │
│  ┌────────────────────────────────────────────────────────────────────────────┐   │
│  │ core.state.StateMachine.transition("transcription_done")                   │   │
│  │   → Notify: state_changed(IDLE)                                       │   │
│  │   → TrayIconManager.set_icon(GRAY)                                     │   │
│  │   → Stats: sessions += 1, words += word_count(text)                      │   │
│  └────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 API Request Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        API REQUEST                                            │
│  POST /transcribe { audio: base64 }                                            │
└─────────────────────────────────────────────────────────────────────────────��─��─┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    API SERVER (aiohttp)                                        │
│  ┌────────────────────────────────────────────────────────────────────────────┐   │
│  │ server.main.APIServer.handle_transcribe(request)                            │   │
│  │   → Decode base64 → audio bytes                                           │   │
│  │   → Convert to numpy array                                              │   │
│  │   → core.engine.WhisperEngine.transcribe(audio)                          │   │
│  │   → Return: { text, confidence, duration_ms }                           │   │
│  └────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. API Design

### 4.1 HTTP Endpoints

| Endpoint | Method | Description | Request | Response |
|---------|--------|------------|----------|----------|
| `/` | GET | Service info | — | `{"name": "nx-dictate", "version": "1.0.0", "status": "ready"}` |
| `/health` | GET | Health check | — | `{"status": "healthy", "model_loaded": bool, "model_size": string}` |
| `/transcribe` | POST | Transcribe audio | `{"audio": "<base64>", "language": "en"}` | `{"text": string, "confidence": float, "duration_ms": int}` |
| `/stats` | GET | Performance stats | — | `{"sessions": int, "words": int, "avg_latency_ms": float}` |
| `/settings` | GET | Current settings | — | `{"model_size": string, "device": string, ...}` |
| `/settings` | PATCH | Update settings | `{"model_size": "base"}` | `{"success": bool}` |
| `/stream` | GET | SSE stream | — | Event stream |
| `/webhook` | POST | Configure webhook | `{"url": string, "events": ["transcription_complete"]}` | `{"success": bool}` |

### 4.2 Request Formats

**POST /transcribe Request:**
```json
{
  "audio": "<base64_encoded_audio>",
  "language": "en",
  "task": "transcribe",
  "beam_size": 5,
  "best_of": 5
}
```

**POST /transcribe Response:**
```json
{
  "text": "transcribed text",
  "language": "en",
  "confidence": 0.95,
  "duration_ms": 1500,
  "words": [
    {"word": "transcribed", "start": 0.0, "end": 0.3},
    {"word": "text", "start": 0.4, "end": 0.7}
  ]
}
```

### 4.3 Error Responses

| Status Code | Error | Cause |
|------------|-------|-------|
| 400 | `invalid_audio` | Missing or malformed audio data |
| 400 | `audio_too_short` | Audio below minimum threshold |
| 400 | `invalid_language` | Unsupported language |
| 500 | `model_not_loaded` | Whisper model failed to load |
| 500 | `transcription_failed` | Engine error |
| 500 | `injection_failed` | Text injection error |

**Error Response Format:**
```json
{
  "error": "model_not_loaded",
  "message": "Failed to load Whisper model: base",
  "details": {}
}
```

### 4.4 WebSocket API

**WebSocket Endpoint:** `ws://<host>:<port>/ws`

| Direction | Event | Payload |
|-----------|-------|---------|
| Server → Client | `state_changed` | `{"state": "recording", "timestamp": 1234567890}` |
| Server → Client | `transcription_progress` | `{"progress": 0.5, "text": "partial..."}` |
| Server → Client | `transcription_complete` | `{"text": "final result", "confidence": 0.95}` |
| Server → Client | `error` | `{"error": "transcription_failed", "message": "..."}` |

---

## 5. State Machine Design

### 5.1 State Definitions

| State | Description | Icon Color | Tooltip |
|-------|-------------|-----------|--------|
| `IDLE` | Waiting for input | Gray (#646464) | "N-Xyme Dictate — Ready" |
| `RECORDING` | Audio capture active | Red (#DC2626) | "N-Xyme Dictate — Recording..." |
| `PROCESSING` | Transcribing audio | Blue (#2563EB) | "N-Xyme Dictate — Processing..." |
| `WARNING` | Low confidence result | Yellow (#D97706) | "N-Xyme Dictate — Low confidence" |
| `ERROR` | Error occurred | Orange (#DC2626) | "N-Xyme Dictate — Error" |

### 5.2 State Transitions

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         STATE MACHINE                                          │
│                                                                         │
│    ┌──────┐  hotkey_press      ┌───────────┐  hotkey_release   ┌──────────┐│
│    │ IDLE │ ────��────────────► │ RECORDING │ ─────────────────► │PROCESSING││
│    └──────┘                    └───────────┘                    └──────────┘│
│       ▲                                                                 │   │
│       │                    transcription_done                    ┌────┴─┐  │
│       │              ───────────────────────────────────────────► │ IDLE  │  │
│       │                                              │         └────┬──┘  │
│       │                                              │            │     │
│       │                                              │            ▼     │
│       │                                              │      ┌──────────┐ │
│       │                                              └───── │ WARNING  │ │
│       │                      error                            └──────────┘ │
│       │              ──────────────────────────────────────────────┐   │
│       │                                                    │        ▼   │
│       │                                            ┌───────┴──┐        │
│       └─────────────────────────────────────────── │  ERROR   │        │
│                                                    └──────────┘        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Transition Matrix

| From | Event | To | Guard Condition | Side Effects |
|------|-------|-----|-----------------|--------------|
| IDLE | `hotkey_press` | RECORDING | — | Start audio capture, update icon (red), play start beep |
| IDLE | `api_start` | RECORDING | API mode | Start audio capture (no hotkey) |
| RECORDING | `hotkey_release` | PROCESSING | Audio buffer non-empty | Stop capture, update icon (blue), play stop beep |
| RECORDING | `hotkey_release` | IDLE | Audio buffer empty | Stop capture, ignore (too short) |
| RECORDING | `error` | ERROR | — | Stop capture, log error, update icon (orange) |
| PROCESSING | `transcription_done` | IDLE | confidence >= 0.5 | Inject text, show notification, increment stats |
| PROCESSING | `transcription_done` | WARNING | confidence < 0.5 | Show low-confidence notification |
| PROCESSING | `error` | ERROR | — | Log error, copy to clipboard, show error |
| WARNING | `hotkey_press` | RECORDING | — | Clear warning, retry |
| WARNING | `dismiss` | IDLE | — | Clear warning, no injection |
| ERROR | `hotkey_press` | RECORDING | — | Clear error, retry |
| ERROR | `dismiss` | IDLE | — | Clear error, no injection |
| * | `quit` | — | — | Cleanup, exit |

### 5.4 State Machine Implementation

```python
# core/state.py
from enum import Enum
from typing import Callable
from PyQt6.QtCore import pyqtSignal, QObject

class DictationState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    WARNING = "warning"
    ERROR = "error"

class StateMachine(QObject):
    """State machine with Qt signals for state changes."""
    
    state_changed = pyqtSignal(str)  # New state
    error_occurred = pyqtSignal(str)  # Error message
    
    VALID_TRANSITIONS = {
        DictationState.IDLE: {
            "hotkey_press": DictationState.RECORDING,
            "api_start": DictationState.RECORDING,
        },
        DictationState.RECORDING: {
            "hotkey_release": DictationState.PROCESSING,
            "error": DictationState.ERROR,
        },
        DictationState.PROCESSING: {
            "transcription_done": DictationState.IDLE,
            "low_confidence": DictationState.WARNING,
            "error": DictationState.ERROR,
        },
        DictationState.WARNING: {
            "hotkey_press": DictationState.RECORDING,
            "dismiss": DictationState.IDLE,
        },
        DictationState.ERROR: {
            "hotkey_press": DictationState.RECORDING,
            "dismiss": DictationState.IDLE,
        },
    }
    
    def __init__(self, initial_state: DictationState = DictationState.IDLE):
        super().__init__()
        self._state = initial_state
    
    @property
    def state(self) -> DictationState:
        return self._state
    
    def transition(self, event: str) -> bool:
        """Attempt state transition. Returns True if successful."""
        valid_targets = self.VALID_TRANSITIONS.get(self._state, {})
        target_state = valid_targets.get(event)
        
        if target_state is None:
            return False
        
        self._state = target_state
        self.state_changed.emit(target_state.value)
        return True
    
    def can_transition(self, event: str) -> bool:
        """Check if transition is valid without executing."""
        valid_targets = self.VALID_TRANSITIONS.get(self._state, {})
        return event in valid_targets
```

---

## 6. Configuration Management

### 6.1 Configuration Sources (Priority Order)

| Priority | Source | Description |
|----------|--------|-------------|
| 1 | CLI arguments | Highest priority, for one-off overrides |
| 2 | Environment variables | `.env` file for persistent config |
| 3 | Config file | JSON/YAML for structured config |
| 4 | Defaults | Lowest priority, built-in defaults |

### 6.2 Configuration Schema

```python
# config/schema.py
from pydantic import BaseModel, Field
from typing import Optional, List

class APIConfig(BaseModel):
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8765)
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])

class ModelConfig(BaseModel):
    size: str = Field(default="base")  # tiny, base, small, medium, large, turbo
    device: str = Field(default="auto")  # auto, cpu, cuda
    compute_type: str = Field(default="float16")  # float16, int8, int8_float16

class AudioConfig(BaseModel):
    sample_rate: int = Field(default=16000)
    channels: int = Field(default=1)
    chunk_size: int = Field(default=1024)
    device: Optional[str] = Field(default=None)
    noise_suppression: bool = Field(default=True)
    vad_enabled: bool = Field(default=True)

class HotkeyConfig(BaseModel):
    enabled: bool = Field(default=False)
    key: str = Field(default="f6")  # f6, back, forward
    push_to_talk: bool = Field(default=True)

class InjectionConfig(BaseModel):
    enabled: bool = Field(default=False)
    backend: Optional[str] = Field(default=None)  # auto-detect if None
    copy_on_failure: bool = Field(default=True)
    auto_paste: bool = Field(default=True

class FeedbackConfig(BaseModel):
    sound_enabled: bool = Field(default=True)
    sound_volume: int = Field(default=70)
    notifications_enabled: bool = Field(default=True)
    show_in_menu: bool = Field(default=True)

class LiveTypingConfig(BaseModel):
    enabled: bool = Field(default=False)
    silence_threshold_ms: int = Field(default=3000)

class AppConfig(BaseModel):
    api: APIConfig = Field(default_factory=APIConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    hotkey: HotkeyConfig = Field(default_factory=HotkeyConfig)
    injection: InjectionConfig = Field(default_factory=InjectionConfig)
    feedback: FeedbackConfig = Field(default_factory=FeedbackConfig)
    live_typing: LiveTypingConfig = Field(default_factory=LiveTypingConfig)
```

### 6.3 Environment Variables

| Variable | Type | Default | Description |
|----------|-----|---------|-------------|
| `API_HOST` | string | `127.0.0.1` | API bind address |
| `API_PORT` | int | `8765` | API port |
| `MODEL_SIZE` | string | `base` | Whisper model (tiny/base/small/medium/large/turbo) |
| `DEVICE` | string | `auto` | Compute device (auto/cpu/cuda) |
| `COMPUTE_TYPE` | string | `float16` | Quantization (float16/int8/int8_float16) |
| `AUDIO_DEVICE` | string | `auto` | Audio input device |
| `HOTKEY` | string | `f6` | Global hotkey |
| `AUTO_INJECT` | bool | `false` | Enable auto text injection |
| `SOUND_FEEDBACK` | bool | `true` | Enable audio feedback |
| `NOTIFICATIONS` | bool | `true` | Enable system notifications |
| `LOG_LEVEL` | string | `INFO` | Logging level |

---

## 7. Error Handling

### 7.1 Error Categories

| Category | Description | Recovery Strategy |
|----------|-------------|-------------------|
| `audio_device_not_found` | No microphone detected | Prompt user to check device |
| `audio_capture_failed` | sounddevice error | Retry, fallback to null |
| `model_not_found` | Whisper model download failed | Retry download |
| `model_load_failed` | Model initialization failed | Fallback to smaller model |
| `transcription_failed` | Whisper inference error | Log, retry once |
| `injection_failed` | Text injection failed | Copy to clipboard |
| `api_server_failed` | aiohttp server error | Restart server |

### 7.2 Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         ERROR HANDLING                                           │
│                                                                         │
│  [Error Occurs]                                                             │
│       │                                                                     │
│       ▼                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │ Log error with traceback                                               │   │
│  │   → utils.logging.logger.error("{error}", exc_info=True)               │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │ IF state == RECORDING:                                                │   │
│  │   Stop audio capture                                                  │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │ Determine error category                                              │   │
│  │   audio_device_not_found  → Retry with list_devices()                  │   │
│  │   model_load_failed     → Fallback to tiny model                    │   │
│  │   injection_failed    → Copy to clipboard, notify                │   │
│  │   transcription_failed → Show error notification                   │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │ State transition to ERROR                                          │   │
│  │   → TrayIconManager.set_icon(ERROR)                                  │   │
│  │   → TrayIconManager.notify_error(message)                      │   │
│  │   → StateMachine.transition("error")                               │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 7.3 Logging Strategy

| Level | Usage | Example |
|-------|-------|---------|
| `DEBUG` | Detailed flow tracing | `Audio chunk {n} samples: {sample_rate}` |
| `INFO` | State transitions | `State: IDLE → RECORDING` |
| `WARNING` | Recoverable issues | `Low confidence: {confidence}` |
| `ERROR` | Failures with recovery | `Transcription failed: {error}` |

### 7.4 Notification Strategy

| Event | Title | Body | Priority |
|-------|-------|------|----------|
| Recording started | — | — (audio-only) | Low |
| Recording stopped | — | — (audio-only) | Low |
| Transcription complete | "N-Xyme Dictate" | "{text[:50]}..." | Normal |
| Low confidence | "Low Confidence" | "Speech unclear, confidence: {conf}%" | Normal |
| Error | "Dictation Error" | "{error_message}" | High |

---

## 8. Dependencies

### 8.1 Core Dependencies

| Package | Version | Purpose | Source |
|---------|---------|---------|--------|
| `faster-whisper` | latest | Whisper CTranslate2 inference | PyPI |
| `sounddevice` | latest | Audio capture | PyPI |
| `aiohttp` | latest | HTTP server | PyPI |
| `numpy` | >=1.20 | Audio processing | PyPI |
| `python-dotenv` | latest | Configuration | PyPI |
| `pydantic` | >=2.0 | Config validation | PyPI |

### 8.2 Optional Dependencies

| Package | Purpose | Used By | Conditional |
|---------|---------|--------|------------|
| `PyQt6` | GUI interface | ui.py | GUI mode |
| `pytest` | Testing | tests/ | Development |
| `pytest-asyncio` | Async testing | tests/ | Development |
| `pytest-cov` | Coverage | tests/ | Development |
| `pynput` | Global hotkeys (X11) | core/hotkey.py | X11 only |
| `evdev` | Global hotkeys (input) | core/hotkey.py | Linux only |

### 8.3 System Requirements

```bash
# Ubuntu/Debian
sudo apt install portaudio19-dev python3-dev wl-clipboard

# Arch Linux
sudo pacman -S portaudio wl-clipboard

# Fedora
sudo dnf install portaudio-devel wl-clipboard
```

### 8.4 Model Files

| Model | Size | VRAM (float16) | VRAM (int8) | Use Case |
|-------|------|---------------|-------------|----------|
| tiny | 39M | ~1GB | ~0.5GB | Fast testing |
| base | 74M | ~1GB | ~0.5GB | Balanced |
| small | 244M | ~2GB | ~1GB | Better accuracy |
| medium | 769M | ~5GB | ~2.5GB | Production |
| large | 1550M | ~10GB | ~5GB | Best accuracy |

---

## 9. Security Considerations

### 9.1 Network Security

- **Default binding**: `127.0.0.1` (localhost only)
- **No authentication**: By default (local-only use)
- **Optional auth**: Token-based if exposed
- **TLS**: Not required for localhost

### 9.2 Audio Privacy

- **No network streaming**: All audio processed locally
- **No persistent storage**: Audio discarded after transcription
- **In-memory only**: Audio buffer cleared after use

### 9.3 Configuration Security

| File | Contains | Security |
|------|----------|----------|
| `.env` | API keys, model paths | Never commit to git |
| `config.json` | Settings | Safe to commit |
| `logs/` | Application logs | Rotate, may contain audio snippets |

### 9.4 Input Validation

```python
# All API inputs validated
async def handle_transcribe(request):
    # Validate audio present
    body = await request.json()
    if "audio" not in body:
        raise APIError("missing_audio", 400)
    
    # Validate base64
    try:
        audio_bytes = base64.b64decode(body["audio"])
    except Exception:
        raise APIError("invalid_audio", 400)
    
    # Validate size limit (10MB)
    if len(audio_bytes) > 10_000_000:
        raise APIError("audio_too_large", 400)
```

### 9.5 Process Isolation

```bash
# Run as user (not root)
# systemd service example:
[Service]
User=nxyme
Group=nxyme
```

---

## 10. Performance Optimization

### 10.1 Startup Optimization

| Optimization | Impact | Implementation |
|--------------|--------|----------------|
| Lazy model loading | -2s startup | Load model on first transcription |
| Pre-init audio stream | -100ms capture | Keep stream warm in RECORDING state |
| Config caching | -50ms | Cache config on import |

### 10.2 Runtime Optimization

| Optimization | Impact | Implementation |
|--------------|--------|----------------|
| Audio buffer pre-allocation | -10ms | Pre-allocate numpy arrays |
| Model beam search tuning | 2x speedup | beam_size=5, best_of=5 |
| VAD preprocessing | -30% audio | Trim silence before inference |

### 10.3 Memory Optimization

| Optimization | Impact | Implementation |
|--------------|--------|----------------|
| Lazy model load | -memory | Unload after 5 min idle |
| Audio buffer clear | -50MB | Clear buffer between sessions |
| Config GC | -memory | Delete unused config objects |

---

## 11. Testing Strategy

### 11.1 Unit Tests

| Module | Tests | Coverage Target |
|--------|-------|-----------------|
| `core/state.py` | State transitions | 100% |
| `core/engine.py` | Model loading, transcription | 80% |
| `core/injection.py` | Backend detection, injection | 90% |
| `audio/processing.py` | VAD, noise suppression | 90% |
| `config/loader.py` | Config loading, validation | 100% |

### 11.2 Integration Tests

| Scenario | Description |
|----------|-------------|
| Dictation flow | Hotkey → record → transcribe → inject |
| API flow | POST /transcribe → response |
| Error recovery | Model load fail → fallback |

### 11.3 Acceptance Tests

| ID | Test | Pass Criteria |
|----|-----|--------------|
| AC1 | Tray icon appears | QSystemTrayIcon visible |
| AC2 | State changes | Icon color matches state |
| AC3 | Recording | Audio captured on hotkey |
| AC4 | Injection | Text appears in target app |

---

## 12. Deployment Considerations

### 12.1 Systemd Service

```ini
[Unit]
Description=N-Xyme Dictate
After=sound.target

[Service]
Type=simple
User=nxyme
ExecStart=/usr/bin/python /home/nxyme/nx-dictate/run_dictate.py --hotkey
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

### 12.2 Docker (Future)

```dockerfile
FROM python:3.11-slim
RUN apt install portaudio19-dev wl-clipboard
COPY . /app
RUN pip install -r requirements.txt
CMD ["python", "run_dictate.py", "--headless"]
```

---

## 13. References

- [PRD](nx-dictate-prd.md) - Product requirements
- [UX Spec](nx-dictate/ux-design-specification.md) - User experience
- [Faster-Whisper Documentation](https://github.com/SYSTRAN/faster-whisper) - STT engine
- [PyQt6 Documentation](https://doc.qt.io/qtforpython/) - GUI framework
- [aiohttp Documentation](https://docs.aiohttp.org/) - HTTP server

---

## 14. Revision History

| Version | Date | Author | Changes |
|--------|------|--------|---------|
| 1.0 | 2026-04-26 | Architecture Team | Initial architecture document |

---

*End of Document*