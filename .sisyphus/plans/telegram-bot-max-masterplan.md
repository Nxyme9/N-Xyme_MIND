# N-Xyme_MIND Telegram Bot - Maximum Capability Masterplan

**Version:** 2.0  
**Created:** 2026-04-07  
**Status:** Ready for Implementation

---

## Vision

**Squeeze the living shit out of what's possible** - ADHD-friendly, ZERO typing, max 2 taps to any action.

---

## Research Synthesis

### Sources
- **explore** (bg_929d93e5): Bot enhancement patterns - codebase integration
- **librarian** (bg_b51652f6): Telegram Bot API v9.6 max capabilities  
- **oracle** (bg_f8a35f2f): Architecture advisory - priority ranking

### Key Findings
1. Bot currently doesn't use: Reply Keyboards, Bot Commands, TTS response, MCP tools
2. API 9.6 has: Mini Apps, Managed Bots, Checklists, Fullscreen, Homescreen shortcuts
3. Voice pipeline exists but only returns text, not voice back

---

## Implementation Phases

### Phase P0: Core UX (Week 1) — 1-TAP ACCESS

#### P0.1: Reply Keyboard (Priority: CRITICAL)
**Goal:** Replace inline menus with persistent reply keyboard = always visible, 1 tap = action

**Buttons:**
```
[📊 Sessions] [➕ New Task] [💀 Kill] [🎤 Voice] [⚡ Menu]
```

**Implementation:**
- Add `KeyboardButton` row to `build_main_menu()`
- Use `ReplyKeyboardMarkup` with `resize_keyboard=True`
- Persists across messages

**Files:** `athena/examples/scripts/bot/main.py`

**Complexity:** Easy | **Effort:** 1 hour

---

#### P0.2: Bot Commands Registration (Priority: CRITICAL)  
**Goal:** Register commands with @BotFather for deep linking

**Commands:**
```
/sessions - List all sessions
/task [desc] - Start new task
/status - System health
/kill - Kill session
/voice - Voice input mode
/menu - Open menu
/help - Show help
```

**Implementation:**
- Add function to list commands
- User manually registers via @BotFather (bot can't do this)

**Complexity:** Easy | **Effort:** 30 min

---

#### P0.3: Voice → TTS Response (Priority: CRITICAL)
**Goal:** Complete voice loop - user sends voice, bot responds with voice note

**Flow:**
1. User sends voice message
2. Bot downloads → faster-whisper transcribes
3. Parse intent → execute action
4. **NEW:** Generate Edge TTS audio response
5. Send voice note back to user

**Implementation:**
- Update `handle_voice_message()` 
- Add `generate_voice_response()` call
- Use `voice_pipeline.synthesize_speech()`
- Send as voice note via `bot.send_voice()`

**Files:** `athena/examples/scripts/bot/main.py`, `athena/examples/scripts/voice_pipeline.py`

**Complexity:** Medium | **Effort:** 2 hours

---

### Phase P1: Integration (Week 1-2)

#### P1.1: MCP Tool Invocation (Priority: HIGH)
**Goal:** Bot can trigger MCP tools directly

**Actions:**
- "Search memory [query]" → unified-memory.search_memories
- "Route task [desc]" → learning-engine.route_task
- "Get context" → athena-context.get_active_context

**Implementation:**
- Add `MCPBridge` class
- Map voice/text commands to MCP tool calls
- Handle responses back to Telegram

**Files:** `athena/examples/scripts/bot/main.py`, new `athena/examples/scripts/bot/mcp_bridge.py`

**Complexity:** Medium | **Effort:** 3 hours

---

#### P1.2: Shell Script Triggers (Priority: HIGH)
**Goal:** Buttons execute workspace scripts

**Buttons:**
- [🟢 Health Check] → `bin/health-l0-blink.sh`
- [🟡 Start MCPs] → `bin/start-all-mcp.sh`  
- [🔴 Stop MCPs] → `bin/stop-all-mcp.sh`
- [💾 Backup] → `bin/backup.sh`
- [🔍 Index Files] → `bin/index-drives.sh`

**Implementation:**
- Add `execute_script()` function
- Button callback triggers subprocess
- Capture output → send to user

**Files:** `athena/examples/scripts/bot/main.py`

**Complexity:** Medium | **Effort:** 2 hours

---

#### P1.3: Chat Actions (Priority: MEDIUM)
**Goal:** Show typing/recording states during processing

**Implementation:**
- `bot.send_chat_action(chat_id, "typing")` during intent parsing
- `bot.send_chat_action(chat_id, "upload_voice")` during TTS generation
- `bot.send_chat_action(chat_id, "upload_document")` during script execution

**Files:** `athena/examples/scripts/bot/main.py`

**Complexity:** Easy | **Effort:** 1 hour

---

### Phase P2: Advanced Features (Week 2-3)

#### P2.1: Telegram Mini App (Priority: HIGH)
**Goal:** Embed web dashboard in Telegram

**Implementation:**
1. Create web app HTML in `athena/examples/scripts/dashboard/frontend/`
2. Add button to open: `InlineKeyboardButton("📊 Dashboard", web_app=WebAppInfo(url=URL))`
3. Configure via @BotFather: `/setmenubutton`

**Files:** New `athena/examples/scripts/dashboard/frontend/index.html`

**Complexity:** Medium | **Effort:** 4 hours

---

#### P2.2: Checklist Workflows (Priority: MEDIUM)
**Goal:** Task management via checkboxes - ZERO typing

**Implementation:**
- Send inline keyboard with checkbox-style buttons
- Callback marks task complete
- Bot receives callback → updates state → triggers action

**Files:** `athena/examples/scripts/bot/main.py`

**Complexity:** Medium | **Effort:** 3 hours

---

#### P2.3: Managed Bots Architecture (Priority: LOW)
**Goal:** Spawn sub-bots for parallel workspace operations

**Use Cases:**
- One bot per long-running task
- Parallel session monitoring
- Notification routing

**Implementation:**
- Bot creates managed bots via API
- Token management
- Delegation logic

**Complexity:** Hard | **Effort:** 8+ hours

---

### Phase P3: Polish (Week 3+)

#### P3.1: Security Hardening
- Rate limiting per user
- Command whitelist
- Audit logging

#### P3.2: Webhook Deployment
- Replace polling with webhook
- Cloudflare/ngrok tunnel

#### P3.3: Full Testing
- Voice flow E2E test
- Button action tests
- MCP integration tests
- Load testing

---

## File Structure After Implementation

```
athena/examples/scripts/
├── bot/
│   ├── main.py              # PTB v20+ bot (enhanced)
│   ├── mcp_bridge.py       # NEW: MCP tool invocation
│   ├── script_runner.py    # NEW: Shell script execution
│   └── keyboards/
│       ├── reply_menu.py   # NEW: Reply keyboard
│       └── inline_menu.py  # Enhanced inline
├── voice_pipeline.py       # Voice STT + TTS
├── dashboard/
│   ├── backend/
│   │   └── main.py         # FastAPI + WebSocket
│   └── frontend/
│       ├── index.html      # NEW: Mini app frontend
│       └── app.js          # NEW: Mini app JS
└── start-remote-services.sh  # Already exists
```

---

## Dependencies

```txt
# Already installed
python-telegram-bot>=20.0
faster-whisper>=0.10.0
edge-tts>=6.1.0

# New additions needed
aiohttp>=3.9.0
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Time to action | < 3 seconds |
| Voice latency | < 2 seconds (transcribe + TTS) |
| Zero-typing compliance | 100% |
| Button response time | < 500ms |
| Mini app load time | < 2 seconds |

---

## Delegation Plan

| Task | Agent | Session | Status |
|------|-------|---------|--------|
| P0.1 Reply Keyboard | hephaestus | NEW | Pending |
| P0.2 Bot Commands | hephaestus | NEW | Pending |
| P0.3 Voice→TTS | hephaestus | NEW | Pending |
| P1.1 MCP Bridge | hephaestus | NEW | Pending |
| P1.2 Script Runner | hephaestus | NEW | Pending |
| P1.3 Chat Actions | hephaestus | NEW | Pending |
| P2.1 Mini App | hephaestus | NEW | Pending |
| P2.2 Checklists | hephaestus | NEW | Pending |
| Testing | review-work | NEW | Pending |

---

## Next Steps

1. Start P0.1 (Reply Keyboard) immediately
2. Work through phases in order
3. Test each feature before moving on
4. Full integration test at end

**START NOW** → P0.1: Reply Keyboard
