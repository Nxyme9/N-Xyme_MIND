# Remaining Execution Plan — N-Xyme_MIND

**Planner:** Prometheus  
**Date:** 2026-05-17  
**Status:** Plan (Not Implemented)  
**Audience:** Sisyphus (orchestrator), Hephaestus (builder)

---

## 1. Current State Assessment

### 1.1 What Exists (Built)
| Component | Path | Status | Notes |
|-----------|------|--------|-------|
| Mojo TF-IDF router (daemon) | `services/mojo-router/src/daemon.mojo` | ✅ Working prototype | ~400μs routing, stdin/stdout JSON-L |
| Mojo CLI router | `services/mojo-router/src/main.mojo` | ✅ Working | CLI version of TF-IDF routing |
| Embedding bridge | `services/mojo-router/src/embed_bridge.py` | ✅ Working | Manages llama-server subprocess, Unix socket |
| Llama.cpp FFI | `services/mojo-router/src/llama_ffi.mojo` | ✅ Skeletal | FFI bindings exist, `tokenize()` is stub |
| nx-agents Rust MCP | `services/nx-agents-mcp/` | ✅ Working | Session, memory, audit — running as `bins/nx_agents` |
| RosEnna trainer design | `data/bmad/design/rosenna-trainer-architecture-2026-05-16.md` | ✅ Designed | Comprehensive architecture doc, NOT built |
| Mojo inference research | `data/bmad/research/` | ✅ Complete | Full technical research done |
| nx-dictate archive | `archive/data_chaos/data_chaos/` | ✅ Archived | PRD, architecture, epics, scripts exist but detached |
| Product brief | `data/bmad/product-brief-*.md` | ✅ Complete | Core vision and scope defined |
| Training data | `archive/data_chaos/data_chaos/training/` | ✅ Raw data | 100+ session transcripts, categorized |
| Brainstorming | `data/bmad/brainstorming/` | ✅ Complete | 38 ideas across technical/UX/quality |

### 1.2 Gap Analysis
| Missing | Impact | Blocks |
|---------|--------|--------|
| Mojo daemon watchdog/auto-restart | Daemon dies silently → routing stops | All downstream features |
| Embedding integration (Rosetta) | TF-IDF only, no semantic routing | Rosetta training feedback loop |
| nx-dictate tray app | No voice dictation from any app | ADHD flow preservation |
| LSP auto-diagnose plugin | Dead LSP servers → broken IDE features | Developer UX |
| Session digest plugin | No session summaries → lost context | Memory consolidation |
| Training feedback loop | Rosetta can't self-improve | Accuracy <100% |
| Session log mining | Failure patterns invisible | No guardrails |

---

## 2. Dependency Graph

```
                ┌────────────────────────────────────┐
                │  [EPIC A] Mojo Daemon Auto-Restart  │
                │  + Embedding Integration             │
                └──────────┬─────────────────────────┘
                           │
          ┌────────────────┼────────────────────┐
          ▼                ▼                     ▼
┌─────────────────┐ ┌──────────────┐  ┌──────────────────────┐
│ [EPIC B]        │ │ [EPIC E]    │  │ [EPIC C]             │
│ nx-dictate      │ │ Training    │  │ LSP Auto-Diagnose    │
│ Tray App        │ │ Feedback    │  │ Plugin               │
│                 │ │ Loop        │  │                      │
│ Depends on:     │ │             │  │ Independent from     │
│ Embedding infra │ │ Depends on: │  │ Epics A, B, E       │
│ (for injection) │ │ Embedding   │  │ Starts immediately   │
│                 │ │ Integration │  │                      │
└────────┬────────┘ │ (Epic A)    │  └──────────────────────┘
         │          └──────────────┘
         ▼
┌─────────────────────────────┐
│ [EPIC D] Session Digest     │──── Independent parallel workstream
│ Plugin                      │
│                             │
│ Depends on: nx-agents MCP   │
│ (already working)           │
└─────────────────────────────┘

         ┌──────────────────────┐
         │ [EPIC F] Session     │──── Depends on: Epic A (for logging),
         │ Log Mining           │    Epic E (for patterns), Epic D (for input)
         │                      │
         │ HIGHEST VALUE LAST   │
         └──────────────────────┘
```

### 2.1 Parallel Groups
| Group | Epics | Rationale |
|-------|-------|-----------|
| **[P1]** | Epic C (LSP plugin), Epic D (Digest plugin) | Zero dependencies on embedding |
| **[P2]** | Epic A (Mojo daemon), Epic C can continue refining | A is priority foundation |
| **[P3]** | Epic B (nx-dictate), Epic E (Training loop) | Both need Epic A |
| **[P4]** | Epic F (Session mining) | Needs output from E and D |

---

## 3. Execution Plan — Ordered by Dependency & ROI

---

## EPIC A: Mojo Daemon Auto-Restart + Embedding Integration

**Goal:** Productionize the Mojo daemon with watchdog reliability and wire in embedding-based semantic routing.

**ROI:** ★★★★★ (Foundation for everything else)  
**Effort:** 3-4 hours  
**Risk:** Medium (Mojo 1.0 compatibility)

### A.1: Mojo Version Audit & Compatibility Check
- **Tasks:**
  - [ ] Check current Mojo version (`mojo --version`) — was 0.26.2, may be 1.0.0b1 now
  - [ ] Verify daemon.mojo compiles with installed version
  - [ ] If Mojo 1.0, migrate syntax (`fn` → `def`, FFI API changes)
  - [ ] Document any breaking changes encountered
- **Acceptance:** Daemon compiles and runs without errors
- **Effort:** 30 min
- **Dependencies:** None

### A.2: Watchdog / Auto-Restart System
- **Tasks:**
  - [ ] Create `services/mojo-router/watchdog.sh` — simple bash watchdog
    ```bash
    #!/bin/bash
    while true; do
      if ! pgrep -f "mojo.*daemon"; then
        echo "[watchdog] daemon died, restarting..."
        mojo run daemon.mojo &
      fi
      sleep 5
    done
    ```
  - [ ] Create systemd service file: `services/mojo-router/nx-mojo-daemon.service`
    ```ini
    [Unit]
    Description=N-Xyme Mojo Routing Daemon
    After=network.target

    [Service]
    Type=simple
    Restart=always
    RestartSec=3
    ExecStart=/home/nxyme/.modular/bin/mojo run /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/services/mojo-router/src/daemon.mojo
    User=nxyme

    [Install]
    WantedBy=default.target
    ```
  - [ ] Add `Justfile` entry: `just mojo-watchdog`
  - [ ] Test: kill daemon → verify auto-restart within 5s
- **Acceptance:** Daemon restarts within 5s of any crash
- **Effort:** 45 min
- **Dependencies:** A.1

### A.3: Wire Embedding Bridge into Daemon
- **Tasks:**
  - [ ] In `daemon.mojo`, spawn `embed_bridge.py` as subprocess on startup
  - [ ] Add protocol: when TF-IDF confidence < threshold (e.g., score < 3.0), send request to embedding bridge for semantic match
  - [ ] Parse embedding bridge response (`{"type": "embed_result", ...}`)
  - [ ] Compare embedding against all 25 tool embedding cache (pre-compute tool embeddings at startup)
  - [ ] Return tool with highest cosine similarity
- **Acceptance:** Queries with low TF-IDF confidence fall through to embedding-based routing
- **Effort:** 2 hours
- **Dependencies:** A.2

### A.4: Tool Embedding Cache
- **Tasks:**
  - [ ] On daemon startup, compute embeddings for all 25 tool descriptions via llama-server
  - [ ] Store in memory as `List[List[Float32]]`
  - [ ] Implement cosine similarity function in Mojo
  - [ ] Benchmark: embedding lookup vs TF-IDF latency
- **Acceptance:** Tool embeddings computed once at startup, used for <100μs similarity search
- **Effort:** 45 min
- **Dependencies:** A.3

### A.5: Daemon Integration Test
- **Tasks:**
  - [ ] Test suite: 25 queries (one per tool) → verify correct tool returned
  - [ ] Test edge cases: gibberish input, empty string, very long query
  - [ ] Benchmark: log p50/p95/p99 latency
  - [ ] Test: kill daemon → watchdog restart → verify state continuity
- **Acceptance:** All 25 tools return correct call ≥95% on golden test set
- **Effort:** 30 min
- **Dependencies:** A.3, A.4

---

## EPIC B: nx-dictate Tray App

**Goal:** Rebuild voice dictation as a system-tray app with hotkey push-to-talk, Faster-Whisper, and session-isolated injection.

**ROI:** ★★★★☆ (ADHD flow preservation — big quality-of-life win)  
**Effort:** 6-8 hours  
**Risk:** Low (proven design, existing archive)

### B.1: Project Scaffold
- **Tasks:**
  - [ ] Create `apps/nx-dictate/` directory structure
    ```
    apps/nx-dictate/
    ├── run_dictate.py         # CLI entry
    ├── engine.py             # Faster-Whisper wrapper
    ├── tray.py               # PyQt6 system tray
    ├── injection.py          # wtype/ydotool/dotool/xdotool
    ├── state.py              # State machine
    ├── hotkey.py             # evdev/pynput global hotkey
    ├── audio/
    │   ├── capture.py
    │   └── processing.py
    ├── config/
    │   ├── loader.py
    │   └── schema.py
    └── requirements.txt
    ```
  - [ ] Copy relevant patterns from `archive/data_chaos/data_chaos/apps/nx_dictate/`
  - [ ] Create `Justfile` entry: `just run-dictate`, `just install-dictate`
- **Acceptance:** Fresh scaffold with importable modules
- **Effort:** 30 min
- **Dependencies:** None

### B.2: Core Engine — Faster-Whisper + Audio Capture
- **Tasks:**
  - [ ] Implement `engine.py` — lazy-load Faster-Whisper model on first transcription
  - [ ] Implement `audio/capture.py` — sounddevice InputStream with configurable device
  - [ ] Implement `audio/processing.py` — VAD silence trimming, noise suppression
  - [ ] Wire together: capture audio → process → transcribe → return text
- **Acceptance:** Can record from mic and get transcription text
- **Effort:** 2 hours
- **Dependencies:** B.1

### B.3: State Machine + PyQt6 System Tray
- **Tasks:**
  - [ ] Implement `state.py` — state machine (IDLE/RECORDING/PROCESSING/WARNING/ERROR)
  - [ ] Implement `tray.py` — QSystemTrayIcon with color states, tooltip, context menu
  - [ ] Implement hotkey listener (`hotkey.py` — evdev for Wayland, pynput fallback for X11)
  - [ ] Wire: hotkey press → RECORDING → audio capture → hotkey release → PROCESSING → transcription → IDLE
- **Acceptance:** Tray icon shows state changes, hotkey starts/stops recording
- **Effort:** 2 hours
- **Dependencies:** B.2

### B.4: Text Injection Backend
- **Tasks:**
  - [ ] Implement `injection.py` — fallback chain: wtype → ydotool → dotool → xdotool → clipboard
  - [ ] Auto-detect available backends at startup
  - [ ] Inject transcribed text into previously focused window
  - [ ] Clipboard fallback on injection failure with notification
- **Acceptance:** Text appears in IDE/text editor after hotkey release
- **Effort:** 1 hour
- **Dependencies:** B.3

### B.5: Config, Settings Dialog, and Service File
- **Tasks:**
  - [ ] Implement `config/loader.py` — .env + CLI args
  - [ ] Implement `config/schema.py` — pydantic validation
  - [ ] Build PyQt6 settings dialog (model size, hotkey, audio device, toggles)
  - [ ] Create systemd service file: `apps/nx-dictate/nx-dictate.service`
  - [ ] Create install script: `apps/nx-dictate/install.sh`
- **Acceptance:** Settings persist across restarts, can install as systemd service
- **Effort:** 1.5 hours
- **Dependencies:** B.3

### B.6: Acceptance Test
- **Tasks:**
  - [ ] AC1: Tray icon appears on launch
  - [ ] AC2: Icon turns red on hotkey press
  - [ ] AC3: Text appears in active window on hotkey release
  - [ ] AC4: Settings dialog opens from tray menu
  - [ ] AC5: Quit cleans up processes
- **Acceptance:** All 5 acceptance criteria pass
- **Effort:** 30 min
- **Dependencies:** B.4, B.5

---

## EPIC C: LSP Auto-Diagnose Plugin

**Goal:** OpenCode plugin that monitors LSP server health, auto-restarts dead servers, and diagnoses common failures.

**ROI:** ★★★★☆ (Prevents broken IDE — high frustration reduction)  
**Effort:** 2-3 hours  
**Risk:** Low (standalone plugin, no infra dependencies)

### C.1: Plugin Scaffold
- **Tasks:**
  - [ ] Create `plugins/lsp-auto-diagnose/`
    ```
    plugins/lsp-auto-diagnose/
    ├── SKILL.md        # Plugin metadata
    ├── diagnose.py     # Health check logic
    └── install.sh      # Symlink into opencode plugins
    ```
  - [ ] Create SKILL.md with `bmad-lsp-diagnose` identifier
  - [ ] Register plugin path in `config/nx_agents.json` skills paths
- **Acceptance:** Plugin discovered by opencode on next load
- **Effort:** 15 min
- **Dependencies:** None

### C.2: LSP Health Check Engine
- **Tasks:**
  - [ ] Implement `diagnose.py` with:
    - [ ] Detect active LSP servers via `lsof -i :<port>` or `.cache/` socket files
    - [ ] For each server, send `initialize` LSP request, check response
    - [ ] Categorize: healthy / stalled / dead / misconfigured
    - [ ] Log results to `data/lsp-diagnose/health.jsonl`
  - [ ] Support: pyright, rust-analyzer, typescript-language-server, bash-language-server
- **Acceptance:** Lists all LSP servers with health status
- **Effort:** 1 hour
- **Dependencies:** C.1

### C.3: Auto-Restart + Notification
- **Tasks:**
  - [ ] Implement: if server stalled >30s → kill and restart
  - [ ] Implement: if server dead → restart with original config
  - [ ] Send desktop notification on restart (via notify-send)
  - [ ] Rate-limit: max 3 restarts per 5 minutes per server
- **Acceptance:** Dead LSP servers auto-restart within 10s
- **Effort:** 45 min
- **Dependencies:** C.2

### C.4: Periodic Health Check + Justfile
- **Tasks:**
  - [ ] Add cron-like periodic check (every 60s via `threading.Timer`)
  - [ ] Create `Justfile` entry: `just lsp-status`, `just lsp-diagnose`
  - [ ] Add install target: `just install-lsp-plugin`
  - [ ] Test: kill a language server manually → verify diagnose + restart
- **Acceptance:** Plugin runs continuously in background, auto-restarts dead servers
- **Effort:** 30 min
- **Dependencies:** C.3

---

## EPIC D: Session Digest Plugin

**Goal:** Generate concise daily session digests from nx-agents session logs — summaries of what was done, patterns, and continuity notes.

**ROI:** ★★★☆☆ (Context preservation for ADHD — medium value)  
**Effort:** 2-3 hours  
**Risk:** Low (depends on existing MCP data only)

### D.1: Plugin Scaffold
- **Tasks:**
  - [ ] Create `plugins/session-digest/`
    ```
    plugins/session-digest/
    ├── SKILL.md
    ├── digest.py       # Digest generation logic
    └── install.sh
    ```
  - [ ] Register in skill paths
- **Acceptance:** Plugin discovered by opencode
- **Effort:** 15 min
- **Dependencies:** None

### D.2: Session Log Parser
- **Tasks:**
  - [ ] Read session logs from `services/nx-agents-mcp/data/sessions/**/*.jsonl`
  - [ ] Parse each line: tool called, timestamp, agent name
  - [ ] Group by session, then by agent, then by date
  - [ ] Extract: call count, tools used, errors, ralph loop iterations
  - [ ] Handle: incomplete sessions, empty logs, malformed JSON
- **Acceptance:** Can parse all session logs and produce structured data
- **Effort:** 45 min
- **Dependencies:** D.1

### D.3: Digest Generator
- **Tasks:**
  - [ ] For each session, generate:
    - **Summary:** "5 calls across 3 tools. 1 ralph loop completed."
    - **Key actions:** memory writes, file changes, delegations
    - **Errors:** any failures or retries
    - **Context:** last task, active loops, XP gained
  - [ ] Daily digest: merge all sessions for a day
  - [ ] Output to `data/digests/YYYY-MM-DD.md`
  - [ ] Format as readable markdown with collapsible sections
- **Acceptance:** Running `digest.py --today` produces a readable session summary
- **Effort:** 1 hour
- **Dependencies:** D.2

### D.4: Auto-Digest + Justfile
- **Tasks:**
  - [ ] Add auto-trigger: run digest on `session_end` call
  - [ ] Create `Justfile` entries: `just digest`, `just digest-today`, `just digest-week`
  - [ ] Add desktop notification: "Daily digest ready → data/digests/"
- **Acceptance:** Digest auto-generates at end of each session
- **Effort:** 30 min
- **Dependencies:** D.3

---

## EPIC E: Training Feedback Loop

**Goal:** Build the hot-training pipeline from the RosEnna architecture: log routing misses → auto-generate training data → retrain Rosetta → hot-reload into llama-server.

**ROI:** ★★★★★ (Core differentiator — enables 100% accuracy)  
**Effort:** 6-8 hours  
**Risk:** High (ML pipeline, multiple moving parts)

### E.1: Miss Logger (Daemon Integration)
- **Tasks:**
  - [ ] In `daemon.mojo`, when wrong tool is returned (detected via user correction):
    - Log: `{"query": "...", "wrong_tool": "...", "correct_tool": "...", "timestamp": ...}`
    - Write to `training/corrections.jsonl`
  - [ ] Implement confidence threshold: if TF-IDF score < 3.0 AND embedding similarity < 0.7, flag as potential miss
  - [ ] Create `training/` directory structure:
    ```
    training/
    ├── corrections.jsonl     # Live corrections from daemon
    ├── generated/            # Augmented training data
    ├── models/               # Trained GGUF output
    └── pipeline.py           # Training pipeline entry point
    ```
- **Acceptance:** Misses are logged to `corrections.jsonl` with full context
- **Effort:** 1 hour
- **Dependencies:** Epic A (A.3)

### E.2: Data Augmenter
- **Tasks:**
  - [ ] Implement `training/augment.py`:
    - For each correction, generate 10 positive paraphrases (via LLM or template-based)
    - Generate 5 hard negatives (similar phrasing → wrong tool)
    - Format as contrastive triplets: (anchor, positive_tool_desc, negative_tool_desc)
  - [ ] Output to `training/generated/augmented_{timestamp}.jsonl`
  - [ ] Validate: each generated pair has correct tool label
- **Acceptance:** 1 correction → 15 training pairs generated
- **Effort:** 1.5 hours
- **Dependencies:** E.1

### E.3: RosEnna Trainer — Implementation
- **Tasks:**
  - [ ] Create `training/pipeline.py` — entry point
  - [ ] Implement data loader: read corrections, load tool descriptions, create triplets
  - [ ] Implement encoder: load Qwen2.5-0.5B with LoRA, mean pooling head
  - [ ] Implement InfoNCE loss
  - [ ] Implement training loop with curriculum learning (4 phases from design doc)
  - [ ] Implement GGUF export via llama.cpp convert script
  - [ ] Target: ~30 min training on RTX 3080 Ti for 10 epochs
- **Acceptance:** Training completes, outputs GGUF model
- **Effort:** 3 hours
- **Dependencies:** E.2, design doc (`data/bmad/design/rosenna-trainer-architecture-2026-05-16.md`)

### E.4: Hot-Reload Integration
- **Tasks:**
  - [ ] Implement daemon protocol: `{"type": "reload_model", "path": "rosenna-v1.gguf"}`
  - [ ] On training completion, signal llama-server via Unix socket to reload model
  - [ ] Verify: new model loaded, embeddings change for same query
  - [ ] Auto-trigger retrain when: ≥100 new corrections OR 24h since last retrain
- **Acceptance:** New model hot-reloaded without restarting daemon
- **Effort:** 1 hour
- **Dependencies:** E.3, A.3

### E.5: Accuracy Validation
- **Tasks:**
  - [ ] Create golden test set (80+ curated queries from `real_validator.py`)
  - [ ] Run accuracy evaluation before and after each retrain
  - [ ] Log Accuracy@1, Accuracy@5, MRR, confusion matrix
  - [ ] Target: >95% Accuracy@1 on golden test set
- **Acceptance:** Validated accuracy metrics for each model version
- **Effort:** 30 min
- **Dependencies:** E.4

---

## EPIC F: Session Log Mining

**Goal:** Mine session logs for recurring failure patterns → generate automated guardrails for agents.

**ROI:** ★★★☆☆ (Learning from failures — high long-term value, not urgent)  
**Effort:** 4-5 hours  
**Risk:** Medium (pattern detection is inexact)

### F.1: Log Aggregator
- **Tasks:**
  - [ ] Read all session logs from `services/nx-agents-mcp/data/sessions/`
  - [ ] Read audit logs from `services/nx-agents-mcp/data/audit/`
  - [ ] Read corrections from `training/corrections.jsonl`
  - [ ] Normalize: unify timestamps, agent names, tool names
  - [ ] Output to `data/mining/aggregated.jsonl`
- **Acceptance:** All log sources merged into single normalized stream
- **Effort:** 45 min
- **Dependencies:** Epic D (D.2 — reuse parser)

### F.2: Failure Pattern Detector
- **Tasks:**
  - [ ] Detect patterns:
    - Repeated same tool call in short period → "loop bounce"
    - Tool call followed by immediate different tool → "context switch"
    - Error tool call >3 times in session → "failure cascade"
    - Ralph loop exceeding max iterations → "runaway loop"
  - [ ] For each pattern: count occurrences, list affected agents, note timestamps
  - [ ] Output to `data/mining/patterns.json`
- **Acceptance:** Produces structured list of detected patterns with counts
- **Effort:** 1.5 hours
- **Dependencies:** F.1

### F.3: Guardrail Generator
- **Tasks:**
  - [ ] For each detected pattern, generate a guardrail suggestion:
    - Pattern: "loop bounce" → Guardrail: "Rate-limit same tool to 3 calls/minute"
    - Pattern: "failure cascade" → Guardrail: "Auto-stop after 3 errors, escalate"
    - Pattern: "runaway loop" → Guardrail: "Hard max 10 ralph iterations"
  - [ ] Output to `data/mining/guardrails.md` as actionable recommendations
  - [ ] Format: pattern → frequency → impact → proposed guardrail → automation candidate
- **Acceptance:** Guardrails.md lists actionable recommendations
- **Effort:** 1 hour
- **Dependencies:** F.2

### F.4: Automated Guardrail Injection (Stretch)
- **Tasks:**
  - [ ] Generate/update agent hints files with guardrail rules
  - [ ] Or inject into `config/nx_agents.json` as rate-limit configurations
  - [ ] Create `Justfile` entry: `just mine-logs`, `just apply-guardrails`
- **Acceptance:** Guardrails auto-applied to agent configurations
- **Effort:** 1 hour
- **Dependencies:** F.3

---

## 4. Effort Summary

| Epic | Effort | Parallel Group | Priority | Risk | ROI |
|------|--------|----------------|----------|------|-----|
| **A:** Mojo Daemon + Embedding | 3-4h | P2 | **#1** | Medium | ★★★★★ |
| **C:** LSP Auto-Diagnose | 2-3h | P1 | **#2** | Low | ★★★★☆ |
| **D:** Session Digest | 2-3h | P1 | **#3** | Low | ★★★☆☆ |
| **B:** nx-dictate Tray App | 6-8h | P3 | **#4** | Low | ★★★★☆ |
| **E:** Training Feedback Loop | 6-8h | P3 | **#5** | High | ★★★★★ |
| **F:** Session Log Mining | 4-5h | P4 | **#6** | Medium | ★★★☆☆ |
| **Total** | **23-31h** | | | | |

### Execution Strategy
- **Wave 1 (P1 — immediate, parallel):** Epic C + Epic D → can start RIGHT NOW, no dependencies
- **Wave 2 (P2 — foundation):** Epic A → everything else depends on this
- **Wave 3 (P3 — high value):** Epic B + Epic E → parallel after A done
- **Wave 4 (P4 — polish):** Epic F → after E and D produce data

---

## 5. Key Dependencies / Known Risks

| Risk | Epic | Likelihood | Mitigation |
|------|------|-----------|------------|
| Mojo 1.0 breaks daemon compilation | A | Medium | Pin to working version, document migration |
| llama-server not built / missing | A | Low | Add build step to Justfile |
| Faster-Whisper VRAM >12GB (large model) | B | Medium | Default to base model, document RAM limits |
| Training pipeline complexity | E | High | Use existing design doc as blueprint, start simple |
| Session logs unstructured / missing fields | D, F | Medium | Graceful fallback: "no data" instead of crash |
| Pattern detection false positives | F | Medium | Human review gate before auto-applying guardrails |

---

## 6. Implementation Sequence (Recommended Sprint)

### Sprint A: "Foundation" (Day 1)
| Day | Focus | Deliverable |
|-----|-------|-------------|
| AM | Epic C (LSP) + Epic D (Digest) | Both plugins scaffolded and working |
| PM | Epic A (Mojo Daemon) | Watchdog, embed integration, tool cache |

### Sprint B: "Value" (Day 2)
| Day | Focus | Deliverable |
|-----|-------|-------------|
| AM | Epic B (nx-dictate) | Core engine + tray + injection working |
| PM | Epic E (Training Loop) | Miss logger + augmenter + first train cycle |

### Sprint C: "Polish" (Day 3)
| Day | Focus | Deliverable |
|-----|-------|-------------|
| AM | Epic B completion | Settings, service file, acceptance tests |
| PM | Epic F (Log Mining) | Pattern detection + guardrail generation |

---

## 7. Verification / Success Criteria

| # | Criterion | Epic |
|---|-----------|------|
| 1 | Daemon survives crash → auto-restarts <5s | A |
| 2 | Low-confidence TF-IDF queries fall through to embedding | A |
| 3 | Dead LSP server detected and restarted within 10s | C |
| 4 | Session digest generated on session end | D |
| 5 | Hotkey press → record → transcribe → inject in <3s total | B |
| 6 | Training pipeline runs end-to-end, produces GGUF | E |
| 7 | Pattern detection finds ≥3 real patterns from logs | F |

---

*This is a PLAN document. Do not implement. Execute via Sisyphus orchestration with Hephaestus for implementation tasks.*
