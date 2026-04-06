# N-Xyme_MIND Telegram Remote Control System - Masterplan

**Version:** 1.0  
**Created:** 2026-04-07  
**Status:** Awaiting User Approval

---

## Vision

Build an ADHD-friendly, frictionless Telegram remote control system for the N-Xyme_MIND workspace with:

- **ZERO typing** - all via button clicks + voice input
- **Maximum 2 taps** to any action
- **Pull chats** - communicate directly with OpenCode
- **Push to maximum capability** - voice input (voice → text → action)
- **Professional web dashboard** as frontend complement

---

## Research Synthesis

### 1. Dashboard Frameworks

| Option | Pros | Cons |
|--------|------|------|
| **FastAPI + React + WebSockets** | Real-time, Python backend already exists, modern | More setup |
| Mantine + Next.js | Production-ready components | Requires full Next.js setup |
| shadcn-nextjs-boilerplate | Beautiful UI, accessible | Heavy for simple needs |

**Recommendation:** FastAPI + React + WebSockets (aligns with existing API server)

### 2. Voice Pipeline Architecture

```
Voice → Download → Convert (FFmpeg) → VAD (Silero) → STT (faster-whisper small/int8) → Intent → Action → Response → TTS (Edge TTS) → Audio
```

**Target Latency:** 400-800ms end-to-end perceived

**Technology Stack:**
- **VAD:** Silero VAD (<1ms inference, MIT licensed)
- **STT:** faster-whisper small + int8 quantization (4-8x faster than Whisper)
- **TTS:** Edge TTS (already installed, streaming capable)
- **Audio:** FFmpeg for OGG → WAV conversion

### 3. Bot Framework Migration

| Current | Recommended |
|---------|-------------|
| Raw `requests` library | python-telegram-bot v20+ (async-first) |

**Migration Benefits:**
- 3-5x throughput improvement
- ~10x lower memory footprint
- Built-in webhook support
- Concurrent update handling

### 4. UX Patterns Found

17+ UX patterns identified:
- Inline keyboards with callback data
- Wizard/step-by-step flows
- Loading states with "typing..."
- MarkdownV2 formatting
- Voice message handling
- Deep linking
- Menu persistence

---

## Implementation Plan

### Phase 1: Core Bot Enhancement (Week 1)

**1.1 Migrate to python-telegram-bot v20+**
- Convert all handlers to async/await
- Implement Application.builder() pattern
- Add proper error handling with retry logic
- Setup webhook endpoint (or keep polling for dev)

**1.2 Add Advanced UX Features**
- [ ] Wizard for multi-step operations (session selection → action → confirm)
- [ ] Inline search (search sessions, files, commands)
- [ ] Loading states with custom loading messages
- [ ] Menu persistence (don't recreate menus every time)
- [ ] Callback data versioning for menu updates

**1.3 Session Management Improvements**
- [ ] Show full session context in buttons
- [ ] Quick actions: kill session, view logs, resume
- [ ] Session filtering (by agent, status, date)

**Files to Modify:**
- `athena/examples/scripts/menu_bot.py` → Complete rewrite to PTB v20+
- Create `athena/examples/scripts/bot_utils/` for handlers

### Phase 2: Voice Pipeline (Week 1-2)

**2.1 Voice Message Handling**
- [ ] Download and convert Telegram OGG to WAV 16kHz
- [ ] Integrate Silero VAD for speech detection
- [ ] Integrate faster-whisper for transcription

**2.2 Intent Processing**
- [ ] Rule-based intent classifier
- [ ] Natural language → action mapping
- [ ] Fallback to LLM for complex queries

**2.3 Voice Response**
- [ ] Edge TTS integration
- [ ] Stream audio to user (send chunks as generated)
- [ ] Voice message playback controls

**Files to Create:**
- `athena/examples/scripts/voice_pipeline.py` - Complete voice processing
- `athena/examples/scripts/intent_classifier.py` - NLP intent handling

**Install Requirements:**
```bash
pip install faster-whisper silero-vad edge-tts
```

### Phase 3: Web Dashboard (Week 2-3)

**3.1 Backend (FastAPI + WebSockets)**
- [ ] Extend existing API server at port 8100
- [ ] Add WebSocket endpoint for real-time updates
- [ ] Session state sync from bot
- [ ] Action execution endpoints (start session, kill, send message)

**3.2 Frontend (React + TypeScript)**
- [ ] Session list with real-time status
- [ ] Live session view (last 50 messages)
- [ ] Action buttons (kill, interrupt, continue)
- [ ] Voice input panel (record → send to bot)
- [ ] Dark mode (ADHD-friendly)

**3.3 Real-time Sync**
- [ ] Bot → WebSocket → Dashboard push
- [ ] Dashboard → Bot API → Telegram pull

**Files to Create:**
- `athena/examples/scripts/dashboard/` - Web dashboard
- `scripts/api-server.py` - Extended with WebSocket

### Phase 4: Advanced Features (Week 3-4)

**4.1 Multi-Session Management**
- [ ] Parallel session control
- [ ] Session groups/tags
- [ ] Broadcast messages to multiple sessions

**4.2 Memory Integration**
- [ ] Read from Athena memory MCP
- [ ] Write session summaries to memory
- [ ] Context-aware suggestions

**4.3 Voice Improvements**
- [ ] Continuous voice mode (push-to-talk)
- [ ] Multi-language support
- [ ] Noise filtering

**4.4 Accessibility**
- [ ] Keyboard shortcuts
- [ ] Screen reader support
- [ ] High contrast mode

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         N-Xyme_MIND SYSTEM                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐  │
│  │  Telegram   │◄──►│  Bot Server  │◄──►│    API Server (8100)    │  │
│  │   Client    │    │  (PTB v20+)  │    │    (FastAPI + WS)       │  │
│  └─────────────┘    └─────────────┘    └───────────┬─────────────┘  │
│         │                      │                     │                │
│         │              ┌───────┴───────┐             │                │
│         │              │               │             │                │
│         ▼              ▼               ▼             ▼                │
│  ┌─────────────┐  ┌───────────┐  ┌───────────┐  ┌───────────────┐  │
│  │   Voice     │  │  Session  │  │   Voice   │  │  Web Dashboard│  │
│  │  Pipeline   │  │  Manager  │  │  Pipeline │  │    (React)    │  │
│  │ (whisper)   │  │           │  │  (EdgeTTS)│  │               │  │
│  └─────────────┘  └───────────┘  └───────────┘  └───────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                     N-Xyme_MIND Core                            │  │
│  │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │  │
│  │   │ Sessions │  │  Memory   │  │  MCPs    │  │   Catalyst   │   │  │
│  │   │ (JSON)   │  │  (Athena) │  │ (stdio)  │  │    (TUI)     │   │  │
│  │   └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
athena/examples/scripts/
├── menu_bot.py                    # Current bot (to be rewritten)
├── bot/
│   ├── __init__.py
│   ├── main.py                    # PTB v20+ entry point
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── commands.py            # /start, /help, /status
│   │   ├── sessions.py             # Session management
│   │   ├── voice.py                # Voice message handling
│   │   └── callbacks.py            # Callback query handlers
│   ├── services/
│   │   ├── __init__.py
│   │   ├── session_manager.py      # Session CRUD
│   │   ├── voice_pipeline.py       # Voice STT/TTS
│   │   └── intent_classifier.py   # NLP intent handling
│   └── keyboards/
│       ├── __init__.py
│       ├── main_menu.py           # Main keyboard
│       ├── session_list.py        # Session selection
│       └── inline_search.py       # Inline search results
├── voice_pipeline.py              # Standalone voice processing
├── intent_classifier.py          # Standalone intent handling
└── dashboard/
    ├── backend/
    │   ├── main.py                # FastAPI + WebSocket server
    │   ├── routes/
    │   │   ├── sessions.py        # Session API
    │   │   └── actions.py         # Action API
    │   └── websocket/
    │       └── manager.py         # WS connection manager
    └── frontend/
        ├── package.json
        ├── src/
        │   ├── App.tsx
        │   ├── components/
        │   │   ├── SessionList.tsx
        │   │   ├── SessionView.tsx
        │   │   ├── ActionPanel.tsx
        │   │   └── VoiceInput.tsx
        │   └── hooks/
        │       ├── useWebSocket.ts
        │       └── useSessions.ts
        └── index.html
scripts/
└── api-server.py                  # Extend with WebSocket
```

---

## Dependencies

### Bot & Voice
```txt
python-telegram-bot>=20.0
faster-whisper>=0.10.0
silero-vad>=0.0.2
edge-tts>=6.1.0
aiohttp>=3.9.0
```

### Dashboard Backend
```txt
fastapi>=0.109.0
uvicorn[websockets]>=0.27.0
websockets>=12.0
sqlalchemy>=2.0.0
pydantic>=2.5.0
```

### Dashboard Frontend
```txt
react>=18.2.0
typescript>=5.3.0
@tanstack/react-query>=5.0.0
tailwindcss>=3.4.0
lucide-react>=0.300.0
```

---

## User Flow Examples

### Example 1: Kill Session (Current → Improved)

**Current (2 taps):**
1. Tap "Kill Session" button
2. Tap "Confirm" to kill

**Improved:**
1. Long press session → Context menu with "Kill" as first option
2. One-tap kill with haptic feedback

### Example 2: Start New Task

**Current:**
1. Type `/start` → Bot responds with menu
2. Navigate to task option
3. Type task description

**Voice-First (Zero Typing):**
1. Hold voice button → Say "start new session for auth bug fix"
2. Bot transcribes → extracts intent → shows confirmation
3. Tap "Confirm" → Session starts

### Example 3: Web Dashboard Flow

1. Open dashboard → See all sessions in real-time
2. Click session → See live conversation
3. Click "Kill" → Session terminated
4. Voice input → Sends to Telegram bot → Processed → Response shown

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time to action | < 3 seconds | From user input to action execution |
| Voice latency | < 1 second | From send to response audio |
| Dashboard sync | < 500ms | Bot action to dashboard update |
| Concurrent sessions | 50+ | Handle multiple parallel sessions |
| Zero-typing compliance | 100% | All actions available via buttons/voice |

---

## Next Steps

**Awaiting User Approval:**

1. [ ] Confirm Phase 1 scope
2. [ ] Confirm technology choices
3. [ ] Prioritize features (voice first vs dashboard first)

**After Approval:**
1. Start Phase 1 - Bot enhancement
2. Daily standups (async via Telegram)
3. Weekly demo to user
