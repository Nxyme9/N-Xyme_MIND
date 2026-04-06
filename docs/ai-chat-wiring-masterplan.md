# N-Xyme MIND Dashboard TUI AI Chat — Complete Wiring Masterplan

**Status**: Draft  
**Created**: 2026-04-07  
**Target**: Fully integrated AI Chat with all N-Xyme MIND backend systems

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AICChatScreen (TUI Dashboard)                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  User Input → Intent Parser → Command Router → Response Formatter   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
              ┌───────────────────────┬─┴───────────────────────┐
              │                       │                       │
              ▼                       ▼                       ▼
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │ LOCAL LLM      │    │ BACKEND APIs    │    │ SYSTEM CMDS    │
    │ (Ollama)       │    │ (Direct Access)│    │ (subprocess)   │
    │                │    │                │    │                │
    │ • llama3.2:3b  │    │ • Memory Core  │    │ • health-*.sh  │
    │ • qwen2.5-coder│    │ • Learning Eng │    │ • systemctl    │
    └────────┬────────┘    │ • Model Router │    │ • sqlite3      │
             │             │ • MCP Tools    │    └────────┬────────┘
             │             └────────┬────────┘             │
             │                      │                      │
             └──────────────┬───────┴──────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │    N-Xyme MIND Core       │
              │                           │
              │  ┌─────────────────────┐  │
              │  │  Memory Core        │  │
              │  │  • TEMPRRetriever   │  │
              │  │  • Vector/Graph DB  │  │
              │  │  • MCP Server       │  │
              │  └─────────────────────┘  │
              │                           │
              │  ┌─────────────────────┐  │
              │  │  Learning Engine    │  │
              │  │  • Q-Learning       │  │
              │  │  • Routing Optimizer│  │
              │  │  • Outcome Logger   │  │
              │  └─────────────────────┘  │
              │                           │
              │  ┌─────────────────────┐  │
              │  │  Local LLM          │  │
              │  │  • Ollama Client    │  │
              │  │  • MCP Tool Loader  │  │
              │  └─────────────────────┘  │
              │                           │
              └───────────────────────────┘
```

---

## 2. Phase Breakdown

### Phase 1: Foundation (Week 1) — Wiring the basics
**Goal**: Get the chat actually talking to backend systems, not just LLM

| Feature | Backend System | Implementation | Priority |
|---------|---------------|----------------|----------|
| **Memory Search** | `packages/memory_core` | Add semantic search via `TEMPRRetriever` | P0 |
| **Routing Stats** | `.sisyphus/routing.db` | Query outcomes table, show agent performance | P0 |
| **Health Status** | `bin/health-*.sh` | Execute via subprocess, parse output | P1 |
| **System Stats** | Multiple | Aggregate from all packages | P1 |

### Phase 2: Intelligence (Week 2) — Smart responses
**Goal**: AI understands context, makes intelligent decisions

| Feature | Backend System | Implementation | Priority |
|---------|---------------|----------------|----------|
| **Intent Detection** | Custom classifier | Detect: query/stats/command/memory | P0 |
| **Context Injection** | `packages/memory_core` | Prepend relevant memories to LLM prompt | P0 |
| **Routing History** | `.sisyphus/routing.db` | Show recent routing decisions | P1 |
| **Agent Status** | `packages/learning_engine` | Query agent weights, success rates | P1 |

### Phase 3: Action (Week 3) — Execute real commands
**Goal**: Chat can actually DO things, not just report

| Feature | Backend System | Implementation | Priority |
|---------|---------------|----------------|----------|
| **Service Control** | `systemctl` / scripts | Start/stop/restart services | P0 |
| **MCP Tool Execution** | MCP servers | Direct tool calls via MCP | P1 |
| **SQL Queries** | SQLite DBs | Execute read queries on routing.db | P1 |
| **Log Retrieval** | `journalctl` / files | Fetch recent logs | P2 |

### Phase 4: Polish (Week 4) — UX and robustness
**Goal**: Production-ready with error handling

| Feature | Backend System | Implementation | Priority |
|---------|---------------|----------------|----------|
| **Error Handling** | All | Graceful degradation for each backend | P0 |
| **Loading States** | UI | Show spinner/progress for async ops | P1 |
| **Command History** | Local | Store recent commands | P1 |
| **Suggestions** | Pattern matching | Quick-reply suggestions | P2 |

---

## 3. Code Changes Required

### 3.1 Main File: `packages/platform_layer/tui/dashboard_v2.py`

**Current State** (lines 355-488):
- `AICChatScreen` class uses hardcoded system prompt only
- Direct LLM calls with no backend integration

**Required Changes**:

#### A. Add imports (after line 1):

```python
# Backend integrations
from packages.memory_core import search as memory_search, stats as memory_stats
from packages.memory_core import recall_session
from packages.learning_engine import status as learning_status, route_task
from packages.local_llm import LocalLLM
```

#### B. Create new helper class (after SYSTEM_PROMPT):

```python
class ChatBackend:
    """Bridge between chat and all backend systems."""
    
    # Intent patterns
    INTENTS = {
        "memory": ["search memory", "find in memory", "what do you remember", "semantic"],
        "stats": ["stats", "statistics", "show metrics", "performance"],
        "routing": ["routing", "agent performance", "delegation", "outcomes"],
        "health": ["health", "status", "check", "broken", "running"],
        "command": ["start", "stop", "restart", "run", "execute"],
        "memory_recall": ["session", "recall", "previous", "conversation"],
    }
    
    def __init__(self):
        self._cache = {}
        self._cache_ttl = 30  # seconds
    
    def detect_intent(self, query: str) -> list[str]:
        """Detect what the user is asking for."""
        query_lower = query.lower()
        detected = []
        for intent, patterns in self.INTENTS.items():
            if any(p in query_lower for p in patterns):
                detected.append(intent)
        return detected if detected else ["general"]
    
    async def get_memory_results(self, query: str, limit: int = 5) -> dict:
        """Query Athena memory."""
        try:
            results = memory_search(query, limit=limit)
            return {"status": "ok", "results": results}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def get_routing_stats(self) -> dict:
        """Get learning engine stats from SQLite."""
        try:
            stats = learning_status()
            return {"status": "ok", "stats": stats}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def get_health_summary(self) -> dict:
        """Run health checks and summarize."""
        try:
            import subprocess
            result = subprocess.run(
                ["bash", "bin/health-l0-blink.sh"],
                capture_output=True, text=True, timeout=10
            )
            return {
                "status": "ok" if result.returncode == 0 else "degraded",
                "output": result.stdout[:500]
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def execute_command(self, command: str) -> dict:
        """Execute a system command."""
        import subprocess
        try:
            # Parse command type
            if command.startswith("start "):
                svc = command[6:].strip()
                result = subprocess.run(
                    ["systemctl", "--user", "start", svc],
                    capture_output=True, text=True, timeout=30
                )
            elif command.startswith("stop "):
                svc = command[5:].strip()
                result = subprocess.run(
                    ["systemctl", "--user", "stop", svc],
                    capture_output=True, text=True, timeout=30
                )
            elif command.startswith("restart "):
                svc = command[8:].strip()
                result = subprocess.run(
                    ["systemctl", "--user", "restart", svc],
                    capture_output=True, text=True, timeout=30
                )
            elif "health" in command.lower():
                result = subprocess.run(
                    ["bash", "bin/health-l1-pulse.sh"],
                    capture_output=True, text=True, timeout=30
                )
            else:
                # Try as shell command
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True, timeout=30
                )
            
            return {
                "status": "ok" if result.returncode == 0 else "error",
                "output": result.stdout[:1000],
                "error": result.stderr[:500] if result.stderr else None
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Command timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
```

#### C. Modify `_send_query` method (lines 428-475):

Replace with:

```python
def _send_query(self, query: str) -> None:
    query = query.strip()
    if not query:
        return
    self._add_message("You", query, "chat-user")
    self._add_message("AI", "Thinking...", "chat-thinking")

    # Create backend bridge
    backend = ChatBackend()
    intents = backend.detect_intent(query)
    
    async def _get_response():
        try:
            if not LOCAL_LLM_AVAILABLE or LocalLLM is None:
                self._replace_last("AI", "⚠️ Local LLM not available.", "chat-error")
                return

            # Build context from backend systems
            context_parts = []
            
            # 1. Memory search (if relevant)
            if "memory" in intents or "memory_recall" in intents:
                mem_results = await backend.get_memory_results(query)
                if mem_results.get("status") == "ok" and mem_results.get("results"):
                    context_parts.append(f"## Memory Results\n{mem_results['results'][:3]}")
            
            # 2. Routing stats (if relevant)
            if "routing" in intents or "stats" in intents:
                routing = await backend.get_routing_stats()
                if routing.get("status") == "ok":
                    weights = routing.get("stats", {}).get("routing_weights", {})
                    context_parts.append(f"## Agent Performance\n{weights}")
            
            # 3. Health check (if relevant)
            if "health" in intents:
                health = await backend.get_health_summary()
                context_parts.append(f"## System Health\n{health.get('output', 'Unknown')}")
            
            # 4. Execute command (if relevant)
            if "command" in intents:
                cmd_result = await backend.execute_command(query)
                if cmd_result.get("status") == "ok":
                    context_parts.append(f"## Command Output\n{cmd_result.get('output', 'Success')}")
                else:
                    context_parts.append(f"## Command Error\n{cmd_result.get('error', 'Unknown error')}")

            # Build enhanced prompt
            system_prompt = self.SYSTEM_PROMPT
            if context_parts:
                system_prompt += "\n\n### Additional Context\n" + "\n\n".join(context_parts)

            # Call LLM
            llm = LocalLLM(model="llama3.2:3b")
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ]
            
            response = llm.chat(messages)
            content = response.get("message", {}).get("content", "No response")
            self._replace_last("AI", content, "chat-ai")

        except Exception as e:
            self._replace_last("AI", f"⚠️ Error: {e}", "chat-error")

    self.run_worker(_get_response(), exclusive=True)
```

### 3.2 New Files to Create

| File | Purpose |
|------|---------|
| `packages/platform_layer/tui/chat_backends.py` | All backend integrations (Phase 1-3) |
| `packages/platform_layer/tui/chat_intents.py` | Intent classification logic |
| `packages/platform_layer/tui/chat_commands.py` | Command execution handlers |

### 3.3 Database Queries for Routing Stats

```python
# In chat_backends.py - routing stats query
ROUTING_STATS_QUERY = """
SELECT agent, 
       COUNT(*) as total, 
       SUM(success) as successes,
       AVG(latency_ms) as avg_latency
FROM outcomes 
WHERE timestamp > datetime('now', '-7 days')
GROUP BY agent 
ORDER BY successes DESC
"""
```

---

## 4. Dependencies Between Components

```
                    ┌─────────────────────┐
                    │   AICChatScreen     │
                    └──────────┬──────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  ChatBackend   │  │  IntentParser   │  │ CommandExecutor │
│  (new class)   │  │  (new module)  │  │  (new module)   │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│memory_core API │  │Pattern Matcher │  │  subprocess    │
│learning_eng API│  │  (simple re)   │  │  systemctl     │
│LocalLLM         │  │                │  │  sqlite3       │
└─────────────────┘  └─────────────────┘  └─────────────────┘

DEPENDENCY GRAPH:
├── AICChatScreen
│   └── imports: ChatBackend, LocalLLM
│
├── ChatBackend (NEW)
│   ├── imports: packages.memory_core
│   ├── imports: packages.learning_engine
│   ├── imports: packages.local_llm
│   ├── imports: subprocess (stdlib)
│   └── imports: sqlite3 (stdlib)
│
├── IntentParser (NEW)
│   └── no external deps (pure Python)
│
└── CommandExecutor (NEW)
    ├── imports: subprocess
    └── imports: sqlite3
```

---

## 5. Testing Strategy

### 5.1 Unit Tests

| Test | File | Method |
|------|------|--------|
| Intent detection | `tests/test_chat_intents.py` | `test_detect_memory_intent()`, `test_detect_command_intent()` |
| Backend queries | `tests/test_chat_backends.py` | `test_memory_search()`, `test_routing_stats()` |
| Command execution | `tests/test_chat_commands.py` | `test_systemctl_start()`, `test_health_check()` |

### 5.2 Integration Tests

```python
# Test the full pipeline
async def test_chat_pipeline():
    backend = ChatBackend()
    
    # Test memory query
    result = await backend.get_memory_results("test query")
    assert result["status"] == "ok"
    
    # Test routing stats
    result = await backend.get_routing_stats()
    assert result["status"] == "ok"
    
    # Test intent detection
    intents = backend.detect_intent("show me memory stats")
    assert "memory" in intents
    assert "stats" in intents
```

### 5.3 Manual Testing Checklist

- [ ] Query: "what's broken?" → Health check + response
- [ ] Query: "search memory for test" → Athena search results
- [ ] Query: "show agent performance" → Routing stats from DB
- [ ] Command: "start model-router" → systemctl executed
- [ ] Command: "stop health monitor" → systemctl executed
- [ ] Query: "summarize recent logs" → Log output parsed

---

## 6. Priority Ordering

### P0 — Must Have (Week 1)
1. **Memory search integration** — Core value proposition
2. **Intent detection** — Route queries to correct backend
3. **Basic health check** — "what's broken?" works
4. **Service commands** — Start/stop services via chat

### P1 — Should Have (Week 2)
5. **Routing stats display** — Show agent performance
6. **Context injection** — Prepend memory results to LLM
7. **Error handling** — Graceful degradation
8. **Loading indicators** — Async feedback

### P2 — Nice to Have (Week 3-4)
9. **MCP tool execution** — Direct MCP calls
10. **Log retrieval** — Fetch and display logs
11. **Command history** - Store recent queries
12. **Suggestions** — Quick reply buttons

---

## 7. Implementation Checklist

### Week 1: Foundation
- [ ] Create `chat_backends.py` with ChatBackend class
- [ ] Add memory search integration
- [ ] Add routing stats query
- [ ] Add health check execution
- [ ] Wire into AICChatScreen._send_query()
- [ ] Test end-to-end

### Week 2: Intelligence
- [ ] Implement intent detection
- [ ] Build context injection pipeline
- [ ] Add caching for repeated queries
- [ ] Enhance error messages
- [ ] Add loading states

### Week 3: Action
- [ ] Implement service control commands
- [ ] Add MCP tool execution paths
- [ ] Add SQL query capability
- [ ] Add log retrieval
- [ ] Security: validate all commands

### Week 4: Polish
- [ ] Comprehensive error handling
- [ ] Performance optimization
- [ ] UX improvements
- [ ] Documentation
- [ ] Final integration test

---

## 8. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Ollama unavailable | Show clear error, fall back to basic responses |
| Memory search fails | Cache last successful result, show cached data |
| Command injection | Whitelist allowed commands, use subprocess.run with args list |
| Slow responses | Show loading indicator, use caching |
| Database locked | Use timeout, retry with backoff |

---

## 9. Example User Interactions After Implementation

```
User: "what's broken?"
AI: Running health check...
   ✅ L0 Blink: PASS
   ✅ L1 Pulse: PASS (services: model-router, proxies, ollama)
   ✅ Memory Core: OK (1563 memories, 89% recall)
   ✅ Learning Engine: OK (1,194 outcomes, 98.7% success)
   → System appears healthy!

User: "search memory for delegation patterns"
AI: Searching Athena...
   Found 3 relevant memories:
   1. "Delegation patterns stored - 2026-04-05" (score: 0.92)
   2. "Q-Learning weights updated - hephaestus +15%" (score: 0.88)
   3. "Route task called 340 times today" (score: 0.85)

User: "start the model-router"
AI: Executing command...
   ✅ systemctl --user start model-router.service
   → Service started successfully
```

---

## 10. Summary

This masterplan provides a **complete wiring** of the AICChatScreen to all N-Xyme MIND backend systems:

- **Phase 1**: Basic connectivity (memory, routing stats, health)
- **Phase 2**: Intelligent context (intent detection, context injection)
- **Phase 3**: Action capability (service control, MCP tools)
- **Phase 4**: Production polish (error handling, UX)

The implementation is **modular** — each component can be built and tested independently. The priority ordering ensures **immediate value** while building toward the full vision.