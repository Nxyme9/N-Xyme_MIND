---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - "data/bmad/brainstorming/brainstorming-session-20260516.md"
  - "data/bmad/product-brief-N-Xyme_MIND-2026-05-16.md"
  - "data/bmad/epics.md"
  - "config/rules/global.md"
  - "docs/SYSTEM.md"
workflowType: "architecture"
project_name: "N-Xyme_MIND"
user_name: "N-Xyme"
date: "2026-05-16"
---

# Architecture Decision Document — N-Xyme_MIND

## Session Context (15 hours, 2026-05-16)

Built from scratch after ecosystem collapse. Current state:
- 25-tool Rust MCP server with session isolation
- 15 agents loading from individual `agents/{name}/agent.js` files
- Single config (`config/nx_agents.json`) injected via `OPENCODE_CONFIG_CONTENT`
- Three-tier tool routing: Rust TF-IDF (11μs) → Mojo daemon (88μs) → LLM (seconds)
- Holographic memory: TF-IDF vectors (2-5μs) with ONNX auto-upgrade
- MiniLM Rust embedding engine (1411 lines, 384-dim)
- ONNX Runtime GPU installed (CUDA 13 compat via symlinks)
- Ralph Auto-Loop plugin with OMO pattern hooks
- LLM Pitfall Mitigation plugin with adaptive circuit breakers
- 53 source code repos scanned for patterns
- 100+ LLM pitfall mitigation ideas generated

---

## AD-1: Meta-Observer Architecture

### Problem
LLMs make systematic errors: loops, hallucinations, stuck states, bad decisions. 100 mitigation ideas were generated but none implemented.

### Decision
Build a single `meta-observer.js` plugin with three hooks, consolidating all 100 ideas into one classification → mitigation → learning pipeline.

### Classification (from 100 ideas — 64-dim signal)
| Signal | Source | Encoding |
|--------|--------|----------|
| Tool call count | Session tracking | Integer |
| Unique tools count | Session tracking | Integer |
| Consecutive same tool | Last call compare | Integer |
| Last 5 tools array | Sliding window | Pattern detect |
| Error rate (last 10) | Sliding window | Float 0-1 |
| Context utilization | MCP session_status | Float 0-1 |
| User corrections (last 3) | Input pattern | Boolean |
| Session duration | Timestamp diff | Minutes |

### Classification Output (from 100 ideas)
| State | Detected By | Mitigation |
|-------|------------|------------|
| ON_TRACK | Few errors, diverse tools | None — silent |
| STUCK | ≥5 same tool consec OR ≥20 calls with <5 unique tools | Inject hint: "Try different approach" |
| LOOPING | Same 2-3 tool pattern ≥3x | Block: "Describe problem first" |
| DISTRESS | Error rate >50% in last 5 | Block + reassess |
| FRUSTRATED (from #9) | 2+ user corrections in 3 calls | Escalate: switch model or approach |

### Hooks (from 100 ideas, OMO source, plugin API)
| Hook | Trigger | Action |
|------|---------|--------|
| `tool.execute.before` | Every tool call | Classify state → block if STUCK/LOOPING/DISTRESS |
| `experimental.chat.messages.transform` | Before every response | Inject context hint if necessary |
| `session.created` | New session | Warm-start with past failure patterns |

### Integration Points
- Reads tool calls from `input.tool`, `output.args`, `output.result`
- Injects hints via `output.messages.push()` in messages.transform
- Blocks bad calls via `throw new Error()` in execute.before
- Stores state in a session Map (in-memory only, no file I/O)
- No external dependencies — pure JS plugin, vanila opencode hooks

---

## AD-2: Ralph Loop Auto-Continuation (OMO Pattern)

### Problem
Ralph Loop doesn't auto-continue reliably. `session.idle` fires, increments, but continuation doesn't trigger properly.

### Decision
Implement OMO's exact pattern from `/home/nxyme/Documents/Source Code/oh-my-openagent-dev/src/hooks/ralph-loop/`:

1. State stored as file frontmatter (`.sisyphus/ralph-loop.local.md`)
2. `session.idle` fires → check `inFlight` set → get state → detect completion FIRST (scan for `<promise>DONE</promise>`) → if complete, clear + toast → if max iterations, clear → increment → `promptAsync` continuation
3. `session.deleted` → clear state
4. `session.error` with `MessageAbortedError` → clear state

Key difference from current: **detect completion BEFORE incrementing**, not after. Current version has the order wrong.

### OMO Source Pattern (verified from source code)
```
session.idle → inFlight check → recovery check → getState
  → detectCompletion in session messages (look for <promise>...</promise>)
  → if complete: handleDetectedCompletion (→ ultrawork verification or clear + toast)
  → if NOT complete: check max iterations → clear + warning if exceeded
  → incrementIteration (write to frontmatter file)
  → buildContinuationPrompt (with iterations/promise/task)
  → injectContinuationPrompt (promptAsync with inherited agent/tools)
  → toast notification
```

---

## AD-3: Plugin Architecture

### Problem
7 plugin files accumulated, 3 disabled, some redundant. Plugin management unpredictable.

### Decision
Consolidate to 3 active plugins maximum:

| # | Plugin | Version | Hooks | Purpose |
|---|--------|---------|-------|---------|
| 1 | `ralph-autoloop.js` | Current (needs fix) | `session.idle`, `session.deleted`, `session.error` | Loop auto-continuation |
| 2 | `meta-observer.js` | New | `tool.execute.before`, `experimental.chat.messages.transform`, `session.created` | LLM pitfall mitigation |
| 3 | `no-code-sisyphus.js` | Current (enabled) | `tool.execute.before` | Block orchestrator write/edit |

Exceeding 3 plugins means consolidation required. New features go into meta-observer, not new files.

### Plugin File Locations
```
.opencode/plugins/
├── ralph-autoloop.js          → OMO-pattern loop continuation
├── meta-observer.js           → Classifier + mitigations + learning
├── no-code-sisyphus.js        → Write blocker
└── auto-memory.js             → (to be merged into meta-observer)
└── llm-pitfalls.js            → (to be merged into meta-observer)
└── nx-session-loop-bridge.js  → (check if still needed)
```

---

## AD-4: MiniLM Rust Embedding Engine

### Problem
MiniLM Rust engine (1411 lines) compiles but uses random weights. All-MiniLM-L6-v2 GGUF (20MB) downloaded but Q4_K alignment bug prevents loading.

### Decision
Fix GGUF alignment calculation in `services/minilm/src/weights.rs`. The GGUF file header parses (101 tensors, 24 metadata) but tensor data offset fails.

GGUF format (per spec):
```
[0-3]   magic: "GGUF"
[4-7]   version: u32
[8-15]  tensor_count: u64  
[16-23] metadata_kv_count: u64
[24+]   metadata KV pairs (skip count items)
[tensor_info_offset+] tensor info entries: name, n_dims, dims[], type, offset
[data_start] aligned to ALIGNMENT (default 32) → tensor data blobs
```

Bug: `data_start` offset calculation doesn't include alignment padding. Fix: after parsing all tensor info entries, pad current position to next `alignment` boundary.

### Weight Status
- ONNX model: 86.6 MB, 120 tensors, weight matrices are GRAPH CONSTANTS (can't extract easily)
- GGUF model: 20 MB, Q4_K_M quantized, 101 tensors, proper weight extraction
- Current: random weights (garbage output)
- Target: loaded GGUF weights (real all-MiniLM-L6-v2 output)

---

## AD-5: Online Training Loop

### Problem
System doesn't learn from failures. Corrections are made, patterns emerge, but no feedback loop exists.

### Decision
Meta-observer stores every classification outcome. When a correction arrives:
1. Log: `{signal_vector} → {predicted_state} → {actual_outcome}`
2. Every 100 corrections → mini-batch weight update on classifier
3. Classifier improves for NEXT tool call — sub-5ms, no blocking

### Training Data Flow
```
Tool call → classifier predicts state → actual outcome observed
  → if correct prediction: reinforce weight
  → if wrong prediction: adjust weight toward correct state
  → every 100: persistent log + training signal
```

---

## AD-6: Model Routing by Task Type

### Problem
No Task type routing. Each model has known failure modes (MiniMax 88% hallucination on facts, DeepSeek 1M context but verbose, Ring tool call issues) but all tasks go to one model.

### Decision
Implement task-type routing in the meta-observer's `.messages.transform` hook:
- Detect task type from user input (regex: "auth", "database", "fix" → task categories)
- Route to best model per task type (DeepSeek for planning, MiniMax for coding)
- Inject model recommendation as context hint (not hard enforcement)
- Track which model performs best per task type over time — adjust recommendations

### Model Capability Matrix (from Librarian research)
| Model | Context | Best For | Known Failure Modes |
|-------|---------|----------|-------------------|
| DeepSeek V4 Flash | 1M | Planning, analysis, architecture | Verbose, over-explains, CoT leaks into tool calls |
| MiniMax M2.5 | 200K | Code implementation | 88% hallucination on facts, repetition at length |
| Ring 2.6 1T | 262K | Deep reasoning, math | Very new (May 8), no structured JSON, tool call issues |
| Qwen3.6 Plus | 1M | Vision, media | Free tier deprecated, CoT leaks into tool calls |
| Trinity Large Preview | 131K | Therapy, empathy | Preview quality, rough edges |

---

## AD-7: Data Pipeline Integration

### Problem
Session transcripts, audit logs, and memory vectors exist but aren't connected to the training loop.

### Decision
```
data/
├── sessions/{agent}/{date}/{id}.jsonl    → Source for decision mining
├── audit/{date}/{source}.jsonl            → Tool call audit trail
├── memory/
│   ├── vectors/ingest.jsonl              → Training data for corrections
│   ├── synapses/decisions.jsonl           → Architecture decisions logged
│   ├── synapses/outcomes.jsonl            → Classification outcomes
│   └── synapses/routing-stats.jsonl       → Model performance per task type
├── learning/
│   ├── outcomes/                          → Per-session learning outcomes
│   └── policies/                          → Routing policies
├── training/mojo_rosetta.jsonl            → Rosetta training pairs
└── trash/{date}/{file}                    → safe_delete recovery
```

---

## AD-8: Session Issues (from 15-hour build)

| Issue | Status | Fix |
|-------|--------|-----|
| Ralph Loop auto-continue broken | ❌ | AD-2: OMO pattern implementation |
| Meta-observer not built | ❌ | AD-1: Single plugin, three hooks |
| BMAD workflows interrupt building | ⚠️ | AD-3: Planning artifacts at session boundaries |
| No-code enforcement inconsistent | ⚠️ | AD-3: Plugin enabled + delegate gate |
| Plugin accumulation (7 files) | ⚠️ | AD-3: Consolidate to 3 |
| MiniLM GGUF weights not loading | ❌ | AD-4: Fix alignment calculation |
| Session transcripts in `unknown/` | ✅ | Fixed at 17:30 (session_id routing) |
| LLM pitfalls plugin too rigid | ⚠️ | AD-1: Meta-observer adaptive circuit breaker |
| MCP error handlers fragile | ⚠️ | safe_run wrapper added, needs testing |
| Mojo daemon has no ML capabilitiy | ❌ | LLama.cpp FFI (archived plan) |
| Model routing doesn't exist | ❌ | AD-6: Task type routing |
| Online training loop doesn't exist | ❌ | AD-5: Every 100 corrections → retrain |

**85% of issues identified in this session remain unfixed.** This document defines the architecture for fixing them.
