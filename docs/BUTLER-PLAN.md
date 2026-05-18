# AI Butler Plan — Voice-Controlled PC Butler

## Vision
Voice → dictation → Mojo agent → control PC, find files, run commands, manage sessions, answer questions. No screen needed.

## Stack (what you already have)

```
🎤 Voice → Whisper (GPU, nx_dictate)
   ↓ text
🧠 Mojo MCP daemon (daemon.mojo, 431 lines)
   ↓ routes to tools
🛠️ Tool library (120+ tools, Q0.5 head at 100%)
   ↓
💻 PC actions
```

## Phase 1 — Sleep mode (ready now)

| Voice command | Action |
|--------------|--------|
| "stop dictation" | Kill nx_dictate process |
| "start dictation" | Restart service |
| "volume up/down" | pactl set-sink-volume |
| "sleep in X hours" | systemctl suspend after delay |
| "check GPU temp" | nvidia-smi query |
| "what's running" | ps aux summary |
| "open [app]" | Run desktop entry |
| "search files for [query]" | fd/find with results spoken |

**Implementation**: ~50 lines in daemon.mojo. Matches voice command → tool call. Already have the router.

## Phase 2 — Wake mode (tomorrow)

| Voice command | Action |
|--------------|--------|
| "read my notifications" | Tail data/notifications/ |
| "what happened while I slept" | Session summary from logs |
| "run the training pipeline" | Kick off prepare_training_data.py |
| "check the repo" | git status + git log |
| "delegate [task] to [agent]" | call_omo_agent via voice |
| "build and compile [project]" | mojo build + run quality gates |

**Implementation**: ~100 lines. Same router, richer tool set.

## Phase 3 — Proactive butler (this week)

| Feature | What it does |
|---------|-------------|
| Morning briefing | GPU temp, session count, corrections mined, training status |
| Crash alert | If training pipeline hangs → voice alert "training stalled" |
| Resource monitor | If VRAM > 90% → "closing Firefox to free GPU memory" |
| Auto-delegate | "X corrections mined → retrain Q0.5 head" — done while you sleep |

## Files to create/modify

```
services/mojo/src/butler.mojo        — New: Voice command router (150 lines)
services/mojo/src/daemon.mojo        — Modify: Add butler tools to MCP (30 lines)
services/mojo/src/command_map.mojo   — New: Voice → tool mapping (80 lines)
services/dashboard/dashboard.py      — Modify: Add butler status panel (20 lines)
```

## Why it works with what you have

- **Dictation**: running on GPU Whisper large-v3
- **Router**: daemon.mojo already handles MCP JSON-RPC
- **Tools**: 120 tools at 100% routing accuracy
- **Persistence**: train while you sleep (prepare_training_data.py runs ~30 min)

You're 90% there. Phase 1 works tonight. Phase 2 is tomorrow morning.
