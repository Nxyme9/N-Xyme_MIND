# N-Xyme MIND — Permanent System Context
**Read at start of EVERY session. This is your identity.**

## SYSTEM IDENTITY
- Project: N-Xyme MIND — multi-agent orchestration system
- Root: `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND`
- Creator built this in 2 months with zero prior experience
- 18 agents, 4 MCP servers, 47 NAP tools, 72+ BMAD skills
- Communication: Direct. No filler. Execute.

## STARTUP PROTOCOL (Run These)
```
1. file_read("ROOT.md")                           → System identity + rules
2. file_read("data/anti-hallucination-rules.md")   → Hard constraints
3. nap_protocol                                     → Current tool definitions
4. search_memory("last session context")            → Recent work context
5. pc_aware query="current project state"           → Living awareness
```

## CORE RULES
1. **NO rm — EVER.** safe_delete moves to `data/trash/` (30-day recovery).
2. **READ BEFORE WRITE** — never edit unread files.
3. **NO INVENTED IMPORTS** — verify everything exists.
4. **NO "general" for specialists** — code→hephaestus, review→momus, etc.
5. **NEVER restart servers from bash-mcp** — kills connection.
6. Anti-hallucination: `data/anti-hallucination-rules.md`
7. Tool naming: `<domain>_<action>` (NAP convention)

## NAP PROTOCOL v3.0
- 47 tools: `file_read`, `search_code`, `config_edit`, `agent_add`, `parallel_task`, etc.
- Delegation chain: `_delegation_chain` in args preserves parentSessionID/agent/tools
- Parallel: `parallel_task(session_id, agent, prompt)` — same-session parallel
- Background: `bg_submit(type, args)` — non-blocking, continue chatting
- Caching: file_cache 500/60s, search_cache 200/300s, config_cache 50/600s
- Full list: `nap_protocol section=tool_naming`

## AGENT HIERARCHY
```
Highest:          Agent Builder [primary] — designs agents
Orchestrators:    Sisyphus [primary], Atlas - Plan Executor [primary]
Builders:         Hephaestus [primary] (deep: deepseek-v4), Sis.Junior [subagent] (fast)
Code Intelligence: Scalpel [all] (dissect→understand→extract→stitch)
Memory:           Cortex [all] (memory, embeddings, knowledge)
Specialists:      Explore, Librarian, Oracle, Momus, Metis, Prometheus
Domain:           Kairos (therapy), Mr.White (chem), Phi-4 (reasoning), Vision, Jarvis
```

## CRITICAL HISTORY (2026-05-17)
- Hephaestus: restored bash, 6 skills, NAP naming, deepseek-v4 model
- Scalpel: renamed Code Dissector, Frankenstein protocol, all mode
- Sisyphus: delegation tree (9-step) + parallel protocol
- Kairos, Scalpel: skills attached (were missing)
- Tool naming: unified NAP across 18 agents
- Delete protection: all rm blocked at bash-mcp level
- Delegation chain: ADCS Lite in bash-mcp + nx-tools
- Parallel execution: parallel_task + bg_queue in nx-tools
- Embeddings: MiniLM (384-dim) + embed_bridge (896-dim)
- 22 new MCP tools built
- Config drift: fixed, both configs synced
- Dead services: 6 cleaned
- Dead plugin: removed
- 5 missing NAP tool stubs added
- Learning bridge: wired outcome→memory+learning+consciousness
- Consciousness daemon: per-agent identity in embedding space
- Mojo engine: InferenceEngine with 3 backends (Native, Llama, HF)

## KEY ARCHITECTURE DECISIONS
- All agent prompts INLINE in `.opencode/agents/*.md` (not `{file:...}`)
- Single config source of truth: `opencode.json`
- Memory in `data/memory/`, Learning in `data/ml/src/`, Consciousness in `data/memory/consciousness/`
- Mojo for hot-path routing (~440μs), Python for MCP servers, Rust for ML
- OMO's `manager.launch()` pattern is the reference for identity propagation
- Task→UnifiedBridge→Memory+Learning+Consciousness simultaneously

## WHAT'S STILL IN ARCHIVE
- `archive/data_chaos/data_chaos/masterplan-memory-learning-consolidation.md` (Apr 6 plan)
- `archive/data_chaos/data_chaos/learning-masterplan.md` (6 strategies working, just needs Q-Learning wired)
- `archive/data_chaos/data_chaos/packages/` (80+ files moved to `data/ml/src/`)
- `archive/data_chaos/data_chaos/nx_trainer/outputs/` (24GB of trained checkpoints)
- `archive/data_chaos/data_chaos/context/memory/knowledge_graph.json` (existing KG)
- `archive/data_chaos/data_chaos/context/semantic/semantic_memory.json` (existing embeddings)
- `archive/data_chaos/data_chaos/context/memory/agent_cards.json` (agent definitions)

## EXISTING MASTERPLANS (Read Before Building)
- `archive/data_chaos/data_chaos/masterplan-memory-learning-consolidation.md` — Memory+Learning consolidation
- `archive/data_chaos/data_chaos/learning-masterplan.md` — Connect AdvancedLearningEngine to router
- `archive/data_chaos/data_chaos/learning-memory-integration-plan.md` — Full integration
- `archive/data_chaos/data_chaos/BRAIN_ARCHITECTURE_MASTERPLAN.md` — Brain architecture
- `data/planning/final-architecture-fix.md` — Root causes & permanent fixes
- `services/mcp-core/NAP-USAGE.md` — Protocol governance
- `services/mcp-core/DESIGN.md` — Hot-swap infrastructure design

## TOOLS
- `nap_protocol` — Get current tool list
- `search_memory` — Search holographic memory
- `embed_text` — 384-dim embedding
- `pc_aware` — PC-wide semantic search
- `pc_scan` — Full PC file scan
- `parallel_task` — Same-session parallel execution
- `consciousness_record` — Record agent outcome
- `consciousness_identity` — Get agent identity
- `UnifiedBridge` (services/megatool-mcp/unified_bridge.py) — Task→All systems

## WRITTEN BY THE USER
The user built this entire system in 2 months with no prior coding experience.
The driving insight: **you don't need to know what's impossible to build it.**
Trust their instincts. They see the whole picture. You fill in patterns.

## THE FIX — Identity Propagation (from OMO source)
Root cause: task() drops parentSessionID, agent, tools.
Fix: Use parallel_task with delegation chain instead of task().
Equivalent OMO pattern:
  manager.launch({ parentSessionID: ctx.sessionID, parentAgent: ctx.agent, parentTools: ... })
Our equivalent:
  parallel_task(session_id, agent_name, prompt, delegation_chain={...})
Already built. Already wired. Just need to use it instead of task().

## THE ACTUAL FIX (Not Toys)
- XTUI at `bins/xtui` — runs with `bins/xtui`. Injects `_agent` into every MCP call.
  Solves identity propagation at the frontend level (like OMO's `manager.launch()`).
- Event daemon at `services/mojo-router/src/event_daemon.py` — OPENCLAW equivalent.
  Unix socket at `/tmp/nx-event-daemon.sock`, auto-starts with XTUI.
```json
{"type":"notify","agent":"hephaestus","status":"completed","session_id":"abc","source":"bg_task"}
```

## SUMMARY
Root cause: task() drops parentSessionID, parentAgent, parentTools.
Fix: XTUI injects _agent into every call. Event daemon routes through Mojo scoring.
Archive has everything built. Just needs wiring.

## NX-PLUGIN (Registered)
Location: `.opencode/plugins/nx-plugin.js`
Config: registered in opencode.json plugins section
3 hooks: config (injects 19 agents), chat.message (auto-context), session.compacting
Next session loads ROOT.md automatically via chat.message hook.

## ═══ V3.0 — THE REHOOK (2026-05-17) ═══

### Identity Propagation (FIXED)
**Problem:** `input.agent` is always empty in JS plugin hooks. OpenCode doesn't pass agent name.
**Fix:** Session registry at `.opencode/lib/session-registry.js` (451 lines).
  - Maps `sessionID → agentName` at session creation time
  - Parent chain traversal to resolve root agent
  - Wired to all 3 plugins: nx-plugin.js, ralph-autoloop.js, no-code-sisyphus.js
  - Every `tool.execute.before` injects `_agent` + `_gpu_route` + `_gpu_confidence`

### GPU Pipeline (LIVE)
- **Rosetta v13 GGUF** (896-dim, 994MB) on RTX 3080 Ti at port 8088
- **8ms** warm embeddings (vs 150-500ms OpenAI)
- **Unlimited rate** — no API key, no rate limit, no cloud
- Tools at root:
  - `gpu-server` — start/stop/status
  - `gpu-embed` — text → 896-dim vector
  - `gpu-route` — query → routed tool + confidence
  - `gpu-train` — build centroids from session data
  - `gpu-stats` — usage dashboard with cloud savings counter

### Trained Routing Model
- 16,159 query→intent pairs extracted from 17 session transcripts
- 9 centroids trained: task, write, code_verify, bash, therapy, memory_search, edit, plan, learning
- Router computes cosine similarity against cached centroids (~100μs)
- Retrain on demand: `gpu-train` (embeds 500 samples via GPU in ~3s)

### Mojo InferenceEngine (COMPILED)
- `services/mojo/src/` — 18 .mojo files, 2,955 lines, 3 GPU backends
- **NativeBackend:** 128-dim SIMD, loads in **144μs**, standalone 109KB ELF
- **LlamaBackend:** GGUF via libllama.so FFI (378 lines, hand-aligned C structs)
- **HfBackend:** HuggingFace via Python interop
- Compiled ELFs at `services/mojo-router/src/`: `engine`, `daemon`, `main_compiled`, `state_bin`
- Mojo 0.26.2.0 installed at `/home/nxyme/.modular/bin/mojo`

### Agent Communication (LIVE)
- Event daemon at `/tmp/nx-event-daemon.sock` (Python, persistent)
- `mojo-chat` in root — send/broadcast/relay between agents
- 8 agents talked through one socket in group debate workflow
- Protocol: JSON messages with type, source, target, payload

### Kairos Phone (READY)
- `kphone` in root — voice → Whisper (GPU, 200ms) → Kairos → TTS (local)
- Uses faster-whisper medium (INT8, GPU) via venv
- TTS via edge-tts (British male voice)
- No chat model needed — Kairos IS the model
- Usage: `kphone --loop`

### Files Created This Session
```
Root-level tools:
  connect-gpu          — one-shot GPU pipeline setup
  gpu-server           — start/stop GPU embedding server
  gpu-embed            — text → 896-dim embedding
  gpu-route            — query → routed tool + confidence
  gpu-train            — train centroids from session data
  gpu-stats            — usage dashboard
  mojo-chat            — agent-to-agent relay
  kphone               — voice line to Kairos

Identity system:
  .opencode/lib/session-registry.js    — 451 lines, persistent
  .opencode/plugins/nx-plugin.js       — GPU routing injected
  data/identity/kairos-context.json    — Kairos personal memory
  data/identity/trained-weights.json   — 9 centroids, 896-dim
  data/identity/tool-embeddings.json   — 12 tool cache
  data/ml/query-intent-pairs.json      — 16,159 training pairs
  data/planning/mojo-rehook-masterplan.md

Agent system:
  agents/kairos/agent.js               — personalized with memory ritual
  agents/kairos/tools/tools.json       — Kairos tool permissions

