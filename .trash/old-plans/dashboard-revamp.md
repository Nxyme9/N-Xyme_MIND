# N-Xyme MIND Master Plan — Dashboard Revamp

## Phase 0: Quick Fixes (DONE)
- ✅ REMOVED darkmode toggle (was crashing)
- ✅ Changed [D] key to [P] for command palette
- ✅ Removed darkmode from dashboard_state.py

---

## Phase 1: AI Brain Chat Feature (PRIORITY)

### Current State
- `chat()` method exists in `src/dashboard/ai_brain.py` (line 454) - **NOT CONNECTED**
- AI Brain tab exists in TUI but only shows: Health Summary, Log Summary, Predictive Alerts
- No chat input field
- Prompt says "Press Ctrl+Shift+A" but hotkey doesn't exist

### Target State
A fully-featured AI chat interface that is **front and center** in the dashboard:
1. **Dedicated chat tab or prominent chat panel**
2. **Message bubbles UI** (user left, AI right)
3. **Input field** with send button
4. **Chat history** with scroll
5. **System prompt** that makes AI self-aware about the backend
6. **Live context** passed to AI (current tab, daemon status, etc.)

### Implementation Steps

#### Step 1.1: Add Chat UI to AI Brain Tab
- Add `TextArea` for user input
- Add `Button` to send message
- Add container for message display (scrollable)
- Location: `src/ui/tui/ultimate_dashboard.py` around line ~2150 (AI Brain tab)

#### Step 1.2: Wire Up `chat()` Method
- Create `on_chat_submit()` handler in ultimate_dashboard.py
- Call `DashboardAIBrain().chat(query, context)` 
- Display response in chat container
- Add to message history

#### Step 1.3: Create System Prompt for Self-Aware AI
Based on research, create a comprehensive system prompt:
```
You are the AI Brain of N-Xyme MIND, a sophisticated AI-powered workflow 
orchestration system. You are the central intelligence that users interact 
with to understand and control their backend system.

Your job is to:
1. Answer questions about the N-Xyme MIND backend system
2. Explain system architecture and components
3. Help users understand agent interactions and state
4. Provide insights into the orchestration system

Context you have access to:
- Current dashboard state
- Agent status (daemon, Ollama, proxies)
- Memory/knowledge base
- Routing system state
- Recent logs and errors

Always reference specific files/functions when discussing code.
```

#### Step 1.4: Chat History Management
- Store messages in memory (simple list)
- Display with proper styling (user vs AI bubbles)
- Token-aware truncation for long conversations
- Persist to Athena memory for session continuity

---

## Phase 2: Bottom Menu Strip

### Current State
- No dedicated clickable bottom menu strip exists
- Footer shows keyboard shortcuts (display only)
- Status bar shows tab info (display only)

### Target State
A functional bottom menu strip with quick actions. Options:
1. **Quick Action Buttons**: Run Daemon, Stop Daemon, Refresh, etc.
2. **Navigation**: Jump to common tabs
3. **Status Indicators**: Clickable status for daemon/proxy/Ollama

### Implementation Steps

#### Step 2.1: Define Bottom Menu Container
- Add `Horizontal` container at bottom of dashboard
- Position: Above Footer, below main content

#### Step 2.2: Add Action Buttons
- Start/Stop Daemon button
- Refresh button
- Settings button
- Each with icon + label

#### Step 2.3: Add Click Handlers
- `on_button_pressed()` already exists (line 2218)
- Add handlers for bottom menu buttons

---

## Phase 3: Polish & Cleanup

### Quick Actions
1. **Command Palette** - Already working (P key or Ctrl+K)
2. **Tab Navigation** - Already working (0-9 keys)
3. **Search** - Already working (S key)
4. **Settings** - Already working (X key)

### Fixes Needed
1. Remove broken references to "Ctrl+Shift+A" in AI Brain tab
2. Update help text to reflect new keybindings
3. Add proper keyboard hints

---

## File Changes Required

| File | Changes |
|------|---------|
| `src/ui/tui/ultimate_dashboard.py` | Add chat UI, bottom menu, fix keybindings |
| `src/dashboard/ai_brain.py` | Enhance chat() method with system prompt |
| `src/ui/tui/screens/chat.py` | NEW - Chat screen component |

---

## Testing Plan

1. **Dark Mode Removed**: Launch dashboard, verify no crashes on P key
2. **Chat Feature**: Send message, verify AI responds with context
3. **Menu Strip**: Click bottom buttons, verify actions work
4. **End-to-End**: Full dashboard workflow test

---

## Research Sources

- Ollama Python library: `ollama` package for chat API
- Streaming: `stream=True` for real-time responses
- Chat history: Sliding window with token counting
- System prompt: 7-component framework (Role, Instructions, Constraints, Format, Tools, Examples, Error Handling)