# N-Xyme Dictate

Voice dictation system with full control — HTTP API, global hotkeys, and text injection into any application.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Launch with GUI (default)
python run_dictate.py

# Or start API server only
python run_dictate.py --headless

# Enable global hotkey for push-to-talk
python run_dictate.py --hotkey --injection
```

## Features

| Feature | Description |
|---------|-------------|
| **Whisper STT** | Faster-Whisper for accurate speech-to-text |
| **HTTP API** | REST endpoints for transcription, health, stats |
| **Global Hotkey** | Push-to-talk from anywhere (configurable key) |
| **Text Injection** | Auto-type into active window (wl-clipboard, ydotool, wtype, xdotool) |
| **PyQt6 GUI** | System tray interface with recording state indicators |
| **Real-time** | Streaming transcription support |
| **Audio Processing** | Noise suppression, VAD, audio level monitoring |
| **Custom Vocabulary** | Boost recognition of domain-specific terms |

## Installation

### Prerequisites

```bash
# Ubuntu/Debian
sudo apt install portaudio19-dev python3-dev

# Arch Linux
sudo pacman -S portaudio

# Fedora
sudo dnf install portaudio-devel
```

### Install Dependencies

```bash
# Core only
pip install -r requirements.txt

# With GUI (recommended)
pip install -r requirements.txt
pip install PyQt6

# Development
pip install -e ".[dev]"
```

## Usage

### GUI Mode (Default)

```bash
python run_dictate.py
```

Launches PyQt6 interface with:
- System tray icon showing recording state
- Recording controls
- Audio level visualization
- Status indicators (idle/recording/processing/error)

### Headless API Server

```bash
python run_dictate.py --headless --host 0.0.0.0 --port 8765
```

Default: `http://127.0.0.1:8765`

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info |
| `/health` | GET | Health check |
| `/transcribe` | POST | Transcribe audio |
| `/stats` | GET | Performance stats |
| `/webhook` | POST | Configure webhook |
| `/stream` | GET | SSE stream |

### Example: Transcribe Audio

```bash
# Convert audio to base64 and send
curl -X POST http://127.0.0.1:8765/transcribe \
  -H "Content-Type: application/json" \
  -d '{"audio": "<base64_audio_data>"}'
```

### Global Hotkey Mode

```bash
python run_dictate.py --hotkey
```

Press the configured hotkey (default: `F6`) to start/stop recording.

### Text Injection Mode

```bash
python run_dictate.py --injection
```

Automatically types transcribed text into the active window.

### Command Line Options

| Option | Description |
|--------|-------------|
| `--headless` | Run API only (no GUI) |
| `--host` | API host (default: 127.0.0.1) |
| `--port` | API port (default: 8765) |
| `--hotkey` | Enable global hotkey listener |
| `--injection` | Enable text injection |
| `--model` | Whisper model (tiny/base/small/medium/large) |
| `--device` | Device (auto/cpu/cuda) |
| `--test` | Run self-test |

## Architecture

```
nx_dictate/
├── run_dictate.py          # Main entry point
├── api.py                # FastAPI HTTP server
├── injection.py          # Text injection (clipboard + keystroke simulation)
├── ui.py                # PyQt6 GUI
├── hotword.py           # Voice activity detection
├── audio_processing.py # Noise suppression, VAD
├── core/
│   ├── engine.py       # Whisper engine
│   ├── hotkey.py      # Global hotkey listener
│   └── state.py       # State management
├─�� server/
│   └── main.py       # API server implementation
└── scripts/
    └── fast_dictate.py # CLI launcher
```

### Components

| Component | Role |
|-----------|------|
| `run_dictate.py` | Entry point, CLI argument parsing |
| `api.py` | aiohttp REST API server |
| `injection.py` | Multi-backend text injection (wtype/ydotool/dotool/xdotool) |
| `ui.py` | PyQt6 system tray with visual indicators |
| `hotword.py` | Voice activity detection |
| `audio_processing.py` | Noise suppression, audio normalization |
| `core/engine.py` | Faster-Whisper wrapper |
| `core/hotkey.py` | Global hotkey registration (pynput) |

## Dependencies

### Core

| Package | Purpose |
|---------|---------|
| `faster-whisper` | Whisper CTranslate2 inference |
| `sounddevice` | Audio capture |
| `aiohttp` | HTTP server |
| `numpy` | Audio processing |
| `python-dotenv` | Configuration |

### Optional

| Package | Purpose |
|---------|---------|
| `PyQt6` | GUI interface |
| `pytest` | Testing |
| `pynput` | Global hotkeys |

## Configuration

### Environment Variables

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

### Supported Backends

Text injection supports multiple backends (auto-detected):

| Backend | Platform | Method |
|--------|----------|--------|
| `wtype` | Wayland | Direct typing |
| `ydotool` | X11/Wayland | Direct typing |
| `dotool` | All | Pipe to stdin |
| `xdotool` | X11 | Ctrl+V paste |
| `wl-clipboard` | Wayland | Clipboard + paste |

## Status Indicators

### Tray Icon States

| State | Icon | Meaning |
|-------|------|---------|
| Idle | Gray microphone | Waiting for input |
| Recording | Green pulsing | Recording audio |
| Processing | Spinning | Transcribing |
| Warning | Yellow | Low confidence |
| Error | Red | Error occurred |

### API Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Invalid request |
| 500 | Server error |

## Testing

```bash
# Run unit tests
pytest tests/

# Specific test module
pytest tests/test_commands.py -v

# With coverage
pytest --cov=nx_dictate tests/
```

## Troubleshooting

### "wl-copy not found"

Install Wayland clipboard tools:

```bash
# Ubuntu
sudo apt install wl-clipboard

# Arch
sudo pacman -S wl-clipboard
```

### "No audio input"

Check audio devices:

```bash
python -c "import sounddevice; print(sounddevice.query_devices())"
```

### "PyQt6 not available"

Install PyQt6:

```bash
pip install PyQt6
```

Or run in headless mode:

```bash
python run_dictate.py --headless
```

### "ydotool not working"

Ensure ydotool is running:

```bash
# Check status
ydotool status

# Start daemon
ydotool &
```

## License

MIT License