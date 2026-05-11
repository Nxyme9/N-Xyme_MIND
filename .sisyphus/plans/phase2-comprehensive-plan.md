# N-Xyme MIND - Comprehensive Update Plan
## Phase 2 + Tray App + Voice Input Fix

---

## Part 1: Frontend Remaining Features (55 items)

### P0 - Critical This Week

**Chat (3)**:
- [ ] Copy message button (each message)
- [ ] Edit/regenerate message (inline edit)
- [ ] Message timestamp toggle

**Orchestration (4)**:
- [ ] Mock WebSocket connection
- [ ] Real-time agent status updates
- [ ] Task progress streaming
- [ ] Connection status indicator

**Dashboard (3)**:
- [ ] Real-time activity stream (auto-update every 5s)
- [ ] Activity expand details on click
- [ ] Clear activity log button

**Settings (2)**:
- [ ] Backup settings (download JSON)
- [ ] Restore settings (upload JSON)

### P1 - Next Week

**Memory (6)**:
- [ ] Bulk select/delete
- [ ] Memory export JSON
- [ ] Memory import JSON
- [ ] Mini-map
- [ ] Fullscreen mode
- [ ] Node context menu

**Orchestration (4)**:
- [ ] Drag-drop task reorder
- [ ] Task dependencies
- [ ] Queue export/import
- [ ] Clear completed tasks

**Dashboard (2)**:
- [ ] Metric comparison (vs last period)
- [ ] Interactive chart click details

**Cross-Cutting (2)**:
- [ ] Error boundaries
- [ ] Global loading overlay

### P2 - Following Week

**Settings (4)**:
- [ ] API key permissions
- [ ] API usage statistics
- [ ] Agent test button

**Responsive (3)**:
- [ ] Touch gestures
- [ ] Pull-to-refresh
- [ ] Mobile polish

---

## Part 2: Tray App Fix

**Current Issues**:
- Basic menu only, no voice/dictation controls
- Need to integrate with all frontend features

**Add to Tray Menu**:
- Services status (11 agents)
- Port status (3000, 8080, 11434, etc.)
- Quick actions:
  - Open Chat
  - Open Memory
  - Open Orchestration
  - Open Dashboard
- Voice Input toggle (enable/disable)
- Start/Stop services
- Settings
- Quit

---

## Part 3: Voice/Dictation Fix

**Current Issues**:
- Voice button exists but shows "Speech recognition not available"
- Need to make it functional with Web Speech API

**Implementation**:
- Use Web Speech API (`window.SpeechRecognition` or `window.webkitSpeechRecognition`)
- Show real-time transcription
- Mic button should pulse when "listening"
- Auto-stop after silence (3 seconds)
- Handle errors gracefully

---

## Implementation Order

1. **Fix Voice Input** - Make dictation actually work
2. **Update Tray App** - Add all feature controls
3. **P0 Features** - WebSocket, activity stream, backup/restore
4. **P1 Features** - Bulk ops, queues, metrics
5. **P2 Features** - Polish, responsive

---

## Success Criteria

| Item | Target |
|------|--------|
| Voice input | Working with Web Speech API |
| Tray app | Full feature control menu |
| Build | 0 errors |
| Mobile | All pages responsive |