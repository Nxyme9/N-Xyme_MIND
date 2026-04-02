# Rule 13: Phone App Development Protocol

## The Problem

Jarvis runs on desktop. User wants remote control from phone (Xiaomi Redmi 15, mid-range).

## The Solution: Hybrid (PWA + Telegram)

**Why hybrid?**
- PWA = full dashboard, lightweight, works on any phone
- Telegram = quick commands, zero install, works on any phone
- Both talk to same FastAPI backend embedded in Jarvis

**Why not native Android?**
- Mid-range phone (Xiaomi Redmi 15) can't handle heavy apps
- PWA runs in Chrome (already installed)
- No app store needed
- Reuses existing Python stack

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   Phone (PWA)   │────▶│  FastAPI Server │
│   Chrome/WebView│◀────│  (in Jarvis)    │
└─────────────────┘     └────────┬────────┘
                                 │
┌─────────────────┐              │
│  Telegram Bot   │──────────────┘
│  (quick cmds)   │
└─────────────────┘
```

## Technology Stack

### Backend (add to Jarvis)
- **FastAPI** — Async, WebSocket support, auto OpenAPI docs
- **uvicorn** — ASGI server, runs in daemon thread
- **Bridge** — Hook into existing `event_bus` for real-time events

### Frontend (PWA)
- **Vanilla HTML/CSS/JS** — No framework overhead
- **Workbox** — Service worker for offline + push notifications
- **Web App Manifest** — `display: standalone`, feels native
- **WebSocket client** — Real-time status/chat updates

### Quick Commands (Telegram)
- **python-telegram-bot** — Async, lightweight
- Bot receives text → publishes to `event_bus`
- Responses pushed back via `send_message`

## Feature Priority

### Must-Have (Week 1)
- Text command input
- Status monitoring
- Chat history
- Notifications
- Pomodoro control

### Nice-to-Have (Week 2)
- Voice commands (Web Speech API)
- Memory search
- Task management

### Defer (Week 3+)
- Screen sharing / camera
- File access
- Native Android app

## Development Protocol

### Phase 1: API Server (2-3 hours)
1. Add `jarvis/api/server.py` — FastAPI app with CORS
2. Endpoints: `POST /command`, `GET /status`, `GET /chat`, `WS /ws`
3. Bridge to `event_bus` for real-time events
4. Run uvicorn in daemon thread
5. Auth: API key in header, generated on first run

### Phase 2: PWA Frontend (3-4 hours)
1. Add `jarvis/api/static/` with `index.html`, `style.css`, `app.js`
2. Mobile-first layout: header, chat area, input bar
3. WebSocket for live updates
4. `manifest.json` for installability
5. Service worker for offline support

### Phase 3: Telegram Bot (1-2 hours)
1. Add `jarvis/api/telegram_bot.py`
2. Pairing via code shown in desktop dashboard
3. Text messages → `event_bus`
4. Responses → `bot.send_message`

### Phase 4: Polish (1-2 hours)
1. QR code for easy phone pairing
2. Push notifications (Web Push + Telegram)
3. Voice input via Web Speech API
4. Connection status indicator

## Security Protocol

| Layer | Mechanism |
|-------|-----------|
| Network | Local-only (LAN), firewall blocks WAN |
| Auth | API key in header, shown in desktop UI + QR |
| WebSocket | Token in query param, validated on connect |
| Rate limiting | 10 commands/minute per client |
| Sensitive tools | Require desktop confirmation (risk ≥ 3) |
| No cloud | Everything stays on LAN |

## Performance Targets (Xiaomi Redmi 15)

| Metric | Target |
|--------|--------|
| PWA load | < 2s |
| Command round-trip | < 500ms |
| WebSocket reconnect | < 3s |
| Memory (PWA tab) | < 30MB |
| Battery impact | Negligible |

## Watch Out For

- **Local IP discovery**: QR code with `http://192.168.x.x:8080?key=abc123`
- **PySide6 thread safety**: Use `event_bus` bridge, never touch Qt from API thread
- **PWA mic access**: Requires HTTPS or localhost. For LAN, use self-signed cert or text-only

## Escalation Triggers

Go native Android only if:
- PWA performance unacceptable after optimization
- Need deep Android integration (background service, biometric)
- Want to distribute via Play Store

## The Rule

> **For remote phone control: Start with FastAPI + PWA + Telegram bot. Only go native if PWA proves inadequate. Always test on target device (Xiaomi Redmi 15) early.**
