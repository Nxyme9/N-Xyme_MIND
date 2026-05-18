# MOJO REHOOK MASTERPLAN — Connect Everything

**Date:** 2026-05-17
**Status:** Plan
**Owner:** System Architect

---

## THE PROBLEM

```
OpenCode JS plugin hooks → input.agent = "" (always empty)
3 days of debugging → session registry fixes it
But the real architecture is already compiled in Mojo
```

## THE REALITY

**Already built, just disconnected:**

| Layer | Location | Status |
|-------|----------|--------|
| **Inference engine** | `services/mojo/src/engine.mojo` (415 lines) | 3 backends, format detect, unified facade |
| **MCP daemon** | `services/mojo/src/daemon.mojo` (432 lines) | 25 tools, TF-IDF routing at 88μs |
| **Audio pipeline** | `services/mojo/src/pipeline.mojo` (119 lines) | VAD → Whisper GPU → output |
| **Semantic search** | `services/mojo/src/codex.mojo` (219 lines) | Cosine sim, Python bridge for embedding |
| **System state** | `services/mojo/src/state.mojo` (43 lines) | VRAM, CPU, GPU detection via NVML |
| **3 backends** | `services/mojo/src/backends/*.mojo` | Native SIMD, Llama GGUF, HF |
| **LLaMA FFI** | `services/mojo/src/llama_ffi.mojo` | CUDA-accelerated FFI to llama.cpp |
| **Compiled ELFs** | `services/mojo-router/src/main_compiled` | 4 x86-64 ELF binaries (not stripped) |
| **Python bridges** | `services/mojo-router/src/*.py` | 8 bridge scripts to Mojo socket |
| **Session registry** | `.opencode/lib/session-registry.js` | 451 lines, persistent, wired to all plugins |

---

## TARGET ARCHITECTURE

```
┌────────────────────────────────────────────────────────────┐
│                    ONE MOJO BINARY                          │
│  services/mojo-orchestrator/                               │
│                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Sisyphus.mojo│  │Hephaestus.mojo│  │ Hermes.mojo  │     │
│  │ (agent_id=   │  │ (agent_id=   │  │ (agent_id=   │     │
│  │  "Catalyst") │  │ "Builder")   │  │ "Memory")    │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                 │              │
│         └─────────────────┼─────────────────┘              │
│                           │                                │
│              ┌────────────▼────────────┐                    │
│              │   Session Registry     │                    │
│              │   data/identity/       │                    │
│              │   sessionID → agent    │                    │
│              └────────────┬────────────┘                    │
│                           │                                │
│              ┌────────────▼────────────┐                    │
│              │   Mojo Daemon (daemon)  │                    │
│              │   IPC + dispatch + ML   │                    │
│              └────────────┬────────────┘                    │
│                           │                                │
│              ┌────────────▼────────────┐                    │
│              │   Inference Engine      │                    │
│              │   engine.mojo           │                    │
│              │   Native/SIMD backend   │                    │
│              │   Llama GGUF backend    │                    │
│              │   HF Transformers       │                    │
│              │   GPU CUDA (MLIR→PTX)   │                    │
│              └────────────┬────────────┘                    │
│                           │                                │
│              ┌────────────▼────────────┐                    │
│              │   Python Bridges        │                    │
│              │   (audio I/O, files,    │                    │
│              │   compatibility only)   │                    │
│              └─────────────────────────┘                    │
└────────────────────────────────────────────────────────────┘
```

---

## ARCHITECTURE DECISIONS

### AD-1: Identity Resolution
**Decision:** Mojo daemon reads session registry on every tool call.
- `input.agent` is always empty in JS hooks (OpenCode limitation)
- Session registry maps `sessionID → agentName` (built, tested, persistent)
- Mojo daemon reads `data/identity/session-registry.json` directly
- No plugin dependency for identity
- **Files affected:** `daemon.mojo`, `session-registry.js`

### AD-2: IPC Protocol
**Decision:** Unix socket for agent-to-agent communication.
- Already exists at `/tmp/nx-event-daemon.sock`
- Already implemented in `daemon.mojo` lines 92-97
- JSON message format: `{type, agent, sessionID, status, payload}`
- Parallel agents broadcast status, anyone can listen
- **Files affected:** `daemon.mojo`, `event_daemon.py`

### AD-3: Inference Routing
**Decision:** The InferenceEngine in `engine.mojo` receives all compute tasks.
- Format auto-detection (GGUF, ONNX, HF, Mojo native)
- 3 backends: Native SIMD (hot path), Llama GGUF (CUDA), HF (compatibility)
- GPU-direct via MLIR → PTX compilation
- Python bridges only for audio capture and file I/O
- **Files affected:** `engine.mojo`, `backend.mojo`, `backends/*.mojo`

### AD-4: Agent Binary Structure
**Decision:** Each agent is a compiled Mojo binary registered as an MCP server.
- Registers in `opencode.json` MCP section
- Gets `toolContext.agent` from SDK natively (compiled layer)
- Owns its tools, identity, and prompt
- No shared plugin bottleneck
- **Files affected:** opencode.json, new `agents/*/agent.mojo` files

### AD-5: Backward Compatibility
**Decision:** All existing JS plugins and Python bridges continue to work.
- Session registry is the shared ground truth
- JS plugins read registry for identity (already wired)
- Python bridges forward to Mojo daemon (already wired)
- Mojo binaries are additive, not replacement
- Migration happens agent by agent, not all at once

---

## IMPLEMENTATION PHASES

### Phase 0: Toolchain (1-2h)
**Install Mojo SDK and compile existing code.**

Steps:
1. Install Mojo via modular CLI
2. Compile `services/mojo/src/engine.mojo` — verify InferenceEngine runs
3. Compile `services/mojo/src/daemon.mojo` — verify 25 tools load
4. Compile `services/mojo/src/codex.mojo` — verify semantic search
5. Copy compiled binaries to `bins/mojo-*` for easy access

**Success criteria:** `bins/mojo-engine --test` returns embedding with correct dimensions

---

### Phase 1: Identity Wire (2-3h)
**Connect Mojo daemon to session registry for identity dispatch.**

Steps:
1. Add JSON file read to `daemon.mojo` — loads `data/identity/session-registry.json` on boot
2. Add `agent` field to all route responses — daemon resolves agent by sessionID
3. Wire session registry persistence writes from Mojo daemon (in addition to JS plugins)
4. Test: daemon receives tool call → resolves agent → returns `_agent` in response

**Success criteria:** Daemon logs `resolved agent: Hephaestus - Builder` for a spawned child session

---

### Phase 2: Agent-Specific MCP (4-6h)
**Port one agent to standalone Mojo MCP server.**

Steps:
1. Create `agents/hephaestus/agent.mojo` — skeleton MCP server
   - Imports `InferenceEngine` from `engine.mojo`
   - Registers tools: `write`, `edit`, `code_verify`, `batch_read`, `safe_delete`
   - Reads session registry for identity
   - Registers in `opencode.json` as MCP server
2. Compile → `bins/hephaestus-mojo`
3. Test full chain: Catalyst delegates → Hephaestus Mojo runs tool → identity propagates
4. Add tool gating natively in Mojo (no `no-code-sisyphus.js` needed)

**Success criteria:** Hephaestus runs as a standalone compiled MCP server with all its tools and correct identity

---

### Phase 3: Parallel Dispatch (3-4h)
**Real OS-level parallel agent execution.**

Steps:
1. Add parentID chain traversal to daemon (already in session-registry.js, port to Mojo)
2. Implement parallel spawn in daemon: `spawn_agent(agent, task, parentSessionID)` → new OS thread
3. Wire agent-to-agent messaging via Unix socket
   - daemon reads all sockets
   - Agents broadcast `{type: "status", agent: "...", status: "complete"}`
   - Other agents react
4. Test: Sisyphus spawns Hephaestus + Hermes simultaneously → both complete → results merge

**Success criteria:** Two agents run on separate cores simultaneously, both report results correctly

---

### Phase 4: Full Inference (4-6h)
**Wire the InferenceEngine with real weights.**

Steps:
1. Replace NativeBackend stub weights with real MiniLM GGUF weights
2. Verify embedding quality (cosine similarity gives meaningful results)
3. Wire LlamaBackend to real GGUF via `llama_ffi.mojo` CUDA path
4. Wire embedding results into Mojo daemon response pipeline
5. Remove dependency on `embed_bridge.py` Python subprocess

**Success criteria:** `daemon.mojo` type:embed returns real semantic embeddings without calling Python

---

### Phase 5: Migration (per agent, ~2h each)
**Port remaining agents to Mojo one by one.**

Priority:
1. Sisyphus (orchestrator — needs identity and dispatch)
2. Hermes (memory — needs semantic search via CodexSearch)
3. Atlas (tracking — needs state persistence)
4. Scalpel (code dissector — needs code search)
5. Remaining agents

Each migration:
1. Create `agents/<name>/agent.mojo`
2. Register tools for that agent
3. Compile → `bins/<name>-mojo`
4. Register in `opencode.json`
5. Remove old JS tools/tools.json when verified

---

## FILE MANIFEST

### Mojo sources to compile (18 files, `services/mojo/src/`)

| File | Lines | Purpose |
|------|-------|---------|
| `engine.mojo` | 415 | InferenceEngine with 3 backends |
| `daemon.mojo` | 432 | MCP daemon with 25 tools + routing |
| `codex.mojo` | 219 | Semantic search with cosine sim |
| `main.mojo` | 72 | Entry point, arg parsing |
| `pipeline.mojo` | 119 | Audio pipeline orchestrator |
| `backend.mojo` | — | ModelBackend trait |
| `backends/native_backend.mojo` | — | Native SIMD compute |
| `backends/hf_backend.mojo` | — | HuggingFace bridge |
| `backends/llama_backend.mojo` | — | Llama GGUF backend |
| `code_search.mojo` | — | Code search |
| `whisper.mojo` | — | Whisper GPU inference |
| `audio.mojo` | — | Audio capture |
| `vad.mojo` | — | Voice activity detection |
| `llama_ffi.mojo` | — | LLaMA.cpp CUDA FFI |
| `state.mojo` | 43 | VRAM/GPU/system metrics |
| `format.mojo` | — | Output formatting |
| `utils.mojo` | — | Utilities |
| `runtime.mojo` | — | Session runtime (if exists) |

### Already compiled ELF binaries (4 files, `services/mojo-router/src/`)

| Binary | Type | Purpose |
|--------|------|---------|
| `daemon` | ELF x86-64, not stripped | MCP daemon with routing |
| `main_compiled` | ELF x86-64, not stripped | Entry point |
| `engine` | ELF x86-64, not stripped | Inference engine |
| `state_bin` | ELF x86-64, not stripped | System state monitor |

### Python bridges to keep (8 files, `services/mojo-router/src/`)

| File | Why keep |
|------|----------|
| `daemon.py` | Fallback / compatibility |
| `embed_bridge.py` | Until Mojo embedding is live |
| `codex_daemon.py` | Until CodexSearch is standalone |
| `consciousness_daemon.py` | Identity vectors |
| `code_review_bridge.py` | BMAD code review skill |
| `batch_write_bridge.py` | Multi-file write |
| `code_search_bridge.py` | Until code_search.mojo compiles |
| `event_daemon.py` | Event socket listener |

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| Mojo toolchain broken / unavailable | Can't compile | Use existing ELFs + Python bridges as fallback |
| GGUF weight alignment bug | Random embeddings | Already documented — fix in Phase 4 |
| Cold startup time | Slow agent spawn | Use daemon as persistent hot process, agents as lightweight threads |
| Mojo 1.0b1 API changes | Source breakage | Pin toolchain version, test after install |
| JS plugin identity chain breaks | All agents go blind | Registry is persistent JSON — Mojo reads same file |

---

## SUCCESS CRITERIA

1. `bins/mojo-daemon` starts, loads session registry, resolves agent by sessionID
2. `bins/hephaestus-mojo` registers as MCP server, all tools work, identity propagates
3. Two agents run in parallel on separate OS threads
4. Inference engine returns real embeddings (not random stubs)
5. All existing JS plugins + Python bridges still work
6. Zero `input.agent` empty errors in logs

---

## FIRST ACTION

```
just install-mojo    # Install Mojo SDK via modular CLI
just compile-mojo    # Compile all 18 .mojo files → bins/
just test-mojo       # Verify engine.mojo InferenceEngine runs

Or manually:
  curl -s https://get.modular.com | sh
  modular install mojo
  mojo build services/mojo/src/engine.mojo -o bins/mojo-engine
  bins/mojo-engine
```
