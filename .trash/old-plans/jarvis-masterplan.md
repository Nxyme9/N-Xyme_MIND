# JARVIS MASTERPLAN: Complete AI Assistant on Wayland/Linux

## TL;DR

> **Goal**: Reuse existing Jarvis code + add Wayland/Linux support
> **Approach**: Don't rebuild — adapt the jarvis-new implementation
> **Target**: "Say 'Hey Jarvis' and it does what you want"

---

## Existing Jarvis Code (FOUND!)

**Location**: `/run/media/nxyme/NXYME_CORE/01_CODING/00_N-Xyme_CATALYST/jarvis-new/`

| Component | File | What It Does |
|-----------|------|-------------|
| **STT** | `ear.py` | FasterWhisper + Porcupine wake word |
| **TTS** | `mouth.py` | Piper voice (ONNX models) |
| **Brain** | `brain.py` | Groq Llama 3.3 70B / Ollama Llama 3.2 3B |
| **Vision** | `eye.py` | Camera + face detection |
| **Desktop** | `skills/desktop.py` | Clipboard, keyboard, window management |
| **System** | `skills/system.py` | Volume, brightness, screenshot, notifications |
| **Media** | `skills/media.py` | Playback control |
| **Web** | `skills/web_navigator.py` | Selenium automation |
| **Sites** | `skills/sites/` | YouTube, Spotify, WhatsApp, Notion |

---

## Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| Terminal Stack | ✅ DONE | Kitty + Fish + Starship + Atuin + Yazi + Delta + tmux |
| Music Control | ✅ DONE | playerctl installed, aliases working |
| Jarvis Code | ✅ FOUND | jarvis-new implementation ready |
| Voice Control | 🔴 ADAPT | Need to port Windows code to Linux/Wayland |
| PC Control | 🔴 ADAPT | Need Wayland alternatives for keyboard/mouse |
| Social Media | 🔴 TODO | Need toot + newsboat |
| Calendar | 🔴 TODO | Need khal |
| Notifications | 🔴 TODO | Need dunst |

---

## Adaptation Strategy (NOT rebuild)

### What to Keep
- `ear.py` — FasterWhisper works on Linux
- `mouth.py` — Piper works on Linux
- `brain.py` — Groq/Ollama works everywhere
- `skills/` — Most skills are platform-agnostic

### What to Adapt
- `ear.py` — Porcupine wake word → use hotkey instead (or Porcupine Linux)
- `desktop.py` — Windows keyboard/mouse → wtype + wayland-automation
- `system.py` — Windows volume → pactl (Linux)
- `eye.py` — Camera → PipeWire (Linux)

### What to Add
- `skills/mastodon.py` — Mastodon posting via toot
- `skills/calendar.py` — Calendar via khal
- `skills/rss.py` — RSS via newsboat
- Fish aliases for Jarvis commands

---

## TODOs

- [ ] 1. Install voice tools (faster-whisper, Piper, espeak-ng)
  - pip install faster-whisper
  - yay -S piper espeak-ng

- [ ] 2. Install PC control tools (wtype, wayland-automation, dunst)
  - sudo pacman -S wtype dunst libnotify
  - pip install wayland-automation

- [ ] 3. Install social tools (toot, newsboat)
  - sudo pacman -S toot newsboat

- [ ] 4. Install calendar tools (khal)
  - sudo pacman -S khal

- [ ] 5. Adapt Jarvis for Linux/Wayland
  - Port ear.py (FasterWhisper — already Linux compatible)
  - Port mouth.py (Piper — already Linux compatible)
  - Port desktop.py (use wtype instead of pyautogui)
  - Port system.py (use pactl instead of Windows APIs)

- [ ] 6. Create Fish aliases for Jarvis
  - alias jarvis="cd ~/jarvis && python3 jarvis.py"
  - alias jarvis-listen="cd ~/jarvis && python3 jarvis.py --listen"

- [ ] 7. Test voice commands end-to-end
  - Test STT (speak → text)
  - Test TTS (text → speech)
  - Test commands (voice → action)

---

## Jarvis Commands

| Command | What It Does |
|---------|--------------|
| "Hey Jarvis" | Wake word (or press hotkey) |
| "Open browser" | Opens Firefox/Chrome |
| "Play music" | playerctl play |
| "Pause music" | playerctl pause |
| "What time is it" | Speaks current time |
| "Check notifications" | Shows desktop notifications |
| "Read my emails" | Reads email subject lines |
| "What's on my calendar" | Shows today's events |
| "Post to Mastodon" | Posts text to Mastodon |
| "Volume up/down" | pactl volume control |
| "Open file manager" | Opens yazi |
| "Search for X" | Web search |

---

## Summary

| Layer | Source | Status |
|-------|--------|--------|
| **Voice Input** | jarvis-new/ear.py (FasterWhisper) | 🔴 ADAPT |
| **Voice Output** | jarvis-new/mouth.py (Piper) | 🔴 ADAPT |
| **AI Brain** | jarvis-new/brain.py (Groq/Ollama) | ✅ READY |
| **PC Control** | jarvis-new/skills/desktop.py | 🔴 ADAPT |
| **System** | jarvis-new/skills/system.py | 🔴 ADAPT |
| **Music** | playerctl | ✅ DONE |
| **Social** | toot + newsboat | 🔴 TODO |
| **Calendar** | khal | 🔴 TODO |
| **Terminal Stack** | Kitty + Fish + Starship + Atuin + Yazi + Delta + tmux | ✅ DONE |

Ready to execute with `/start-work`?
