# N-Xyme MIND — Master Synthesis Plan
## Date: 2026-05-17 | Generated from Full System Context Analysis

---

## 📋 EXECUTIVE SUMMARY

**What You Have:** A bleeding-edge AI agent orchestration system with 16 agents, BMAD workflows, Rust MCP services, Mojo router, MiniLM embeddings, Whisper pipelines, and massive archive of ML assets (27GB vectors, 37K transcripts, complete learning engine).

**What's Missing:** Connection between what exists and what's running. The infrastructure is there, but agents don't use it automatically.

**The Goal:** Create at the speed of imagination — eliminate friction between thought and creation.

---

### 0. Fix OpenCode Config Validation (v1.15.3+ Schema Change)
**Priority:** CRITICAL  
**Why:** `session_storage` and `session_logs` are unrecognized keys in OpenCode v1.15.3 — breaks `bins/nx` startup with "4 of 5 requests failed"  
**Affected Files:** 
- `/home/nxyme/.config/opencode/opencode.jsonc` — global config (was fixed, reverted by sync script)
- `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/opencode.json` — project config (has unrecognized keys on lines 67-68)
- `bins/nx-validate` — auto-heal script may be reverting the fix  
**Root Cause:** OpenCode v1.15.3 removed `session_storage`/`session_logs` from schema. Session paths now handled via `$OPENCODE_SESSION_DIR` env var or default location.
**Fix Strategy:**
1. Remove `session_storage`, `session_logs` from ALL opencode config files
2. Move session path config to `nx_agents.json` custom fields (already done: `session_config`, `opencode_db`, `opencode_logs`)
3. Update `bins/nx-validate` to NOT re-add these keys during auto-heal
4. Use `$OPENCODE_CONFIG_CONTENT` env var (already set by `bins/nx` line 19) to bypass file config entirely  
**Time:** 30 minutes  
**Impact:** `bins/nx` starts without errors ✅ FIXED  
**Fix Applied:** Updated `bins/nx` launcher to strip N-Xyme custom keys (`session_config`, `memory_config`, `opencode_db`, `opencode_logs`, `opencode_diffs`) from `OPENCODE_CONFIG_CONTENT` before passing to OpenCode. Custom config stored in `NX_SESSIONS_ROOT` and `NX_MEMORY_ROOT` env vars for N-Xyme tools.  

## 🔴 P0: CRITICAL FIXES (Do First)

### 1. Delete Meta-Observer Permanently
**Priority:** CRITICAL  
**Why:** File still exists as `.jsbroken` — orphaned but not deleted  
**Action:** `rm /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/.opencode/plugins/meta-observer.jsbroken`  
**Time:** 1 minute  
**Impact:** Prevents accidental reload

### 2. Fix Session Call Tracking
**Priority:** CRITICAL  
**Why:** All sessions show `calls=0` despite having streak/XP — tracking is broken  
**Action:** Fix `record_success()` in `main.rs` to increment `calls`  
**Time:** 30 minutes  
**Impact:** Accurate session metrics

### 3. Wire Plugin Circuit Breaker
**Priority:** CRITICAL  
**Why:** Single plugin can take down entire system (meta-observer proved this)  
**Action:** Connect `archive/.../packages/intelligence/circuit_breaker.py` to active plugin system  
**Time:** 2 hours  
**Impact:** System resilience

### 4. Connect Session Memory to Persistent Storage
**Priority:** CRITICAL  
**Why:** `memory: {}` for all sessions — no persistence  
**Action:** Wire `memory_write/read` to actual file storage  
**Time:** 1 hour  
**Impact:** Sessions retain context

### 5. Fix Debug Output Pollution
**Priority:** HIGH  
**Why:** `println!` polluting JSON-RPC responses  
**Action:** Change all `println!` → `eprintln!` in minilm crate  
**Time:** 30 minutes  
**Impact:** Clean MCP responses

---

## 🟡 P1: HIGH PRIORITY (Foundation)

### 6. Mojo RAM Semantic Search Engine
**Priority:** HIGH  
**Why:** Foundation for everything else — instant context access  
**What:** Load 73MB drive index into Mojo RAM → embed → search in microseconds  
**Components:** `codex.mojo` (CodexSearch struct), MiniLM, drive index  
**Time:** 2-4 hours  
**Impact:** 10x faster code/memory discovery

### 7. Voice-to-Code Bridge
**Priority:** HIGH  
**Why:** Eliminates typing friction — speak intent → working code  
**What:** Streaming Whisper → Intent Parser → Mojo RAM Search → Ralph Loop Generation  
**Components:** `streaming_whisper.py`, nx_agents MCP, Ralph Loop  
**Time:** 4-6 hours  
**Impact:** Create code by speaking

### 8. Holographic Context Reader
**Priority:** HIGH  
**Why:** Auto-inject context when reading files — never lose context  
**What:** When opening file, query holographic memory for past bugs, decisions, related code  
**Components:** Holographic memory, Mojo RAM, file watchers  
**Time:** 2 hours  
**Impact:** Understand WHY code was written, not just WHAT

### 9. Connect ChromaDB to Active System
**Priority:** HIGH  
**Why:** 27GB vectors sitting idle — make them queryable  
**What:** Wire ChromaDB 27GB to nx_agents MCP for semantic search  
**Components:** ChromaDB, nx_agents MCP, memory_search tool  
**Time:** 2 hours  
**Impact:** Access to entire project history

### 10. Cross-Agent Memory Sharing
**Priority:** HIGH  
**Why:** Sisyphus can't see what Hephaestus remembers — zero sharing  
**What:** Shared memory structure between agents  
**Components:** Session state, memory_write/read, agent configs  
**Time:** 2 hours  
**Impact:** Agents learn from each other

---

## 🟢 P2: MEDIUM PRIORITY (Creative Tools)

### 11. Holographic Lyric Video Generator
**Priority:** MEDIUM  
**Why:** You have complete 15-stage pipeline — just wire it to Mojo RAM  
**What:** Drop song → AI generates lyric video with perfect timing  
**Components:** Whisper pipeline, AE integration, FFmpeg, CUDA  
**Time:** 6-8 hours  
**Impact:** Hours of manual AE work → minutes

### 12. Self-Healing Editor
**Priority:** MEDIUM  
**Why:** Pattern-aware editing with memory-backed suggestions  
**What:** "Make error handling consistent" → finds patterns → generates → verifies  
**Components:** Holographic memory, Ralph Loop, code_review tool  
**Time:** 4-6 hours  
**Impact:** Code that works first time

### 13. Training Pipeline Integration
**Priority:** MEDIUM  
**Why:** Corrections accumulate but never trigger retraining  
**What:** Corrections → auto-retrain → update model → hot reload  
**Components:** `training_trigger.py`, MiniLM, corrections.jsonl  
**Time:** 4 hours  
**Impact:** Self-improving system

### 14. Music-to-Visual Engine
**Priority:** MEDIUM  
**Why:** Stem separation + beat detection → synchronized visuals  
**What:** Music in → AI generates synchronized visuals → video out  
**Components:** Demucs, beat detection, Mojo RAM, FFmpeg  
**Time:** 8 hours  
**Impact:** Creative pipeline automation

### 15. Pattern Library
**Priority:** MEDIUM  
**Why:** Never solve same problem twice  
**What:** Reuse proven patterns across codebase  
**Components:** Holographic memory, Mojo RAM, code_search  
**Time:** 2 hours  
**Impact:** Instant pattern reuse

---

## 🔵 P3: LOW PRIORITY (Optimization)

### 16. Consolidate Scattered Memory
**Priority:** LOW  
**Why:** 37K transcripts scattered across 3+ locations  
**What:** Single index for all transcripts  
**Components:** Drive index, deduplication scripts  
**Time:** 4 hours  
**Impact:** Clean memory structure

### 17. Remove Duplicate Sessions
**Priority:** LOW  
**Why:** 5,847 files in "New Folder" — duplicates  
**What:** Deduplicate and archive  
**Components:** File comparison, archive scripts  
**Time:** 2 hours  
**Impact:** Storage optimization

### 18. Optimize ChromaDB + SQLite Storage
**Priority:** LOW  
**Why:** 27GB ChromaDB unoptimized, SQLite not vacuumed  
**What:** Compact databases, optimize indices  
**Components:** ChromaDB tools, SQLite vacuum  
**Time:** 2 hours  
**Impact:** Faster queries, less storage

### 19. Build Memory Health Monitoring
**Priority:** LOW  
**Why:** No health metrics being generated  
**What:** Monitor memory quality, corruption, performance  
**Components:** `health_monitor.py`, metrics collection  
**Time:** 2 hours  
**Impact:** Proactive memory management

### 20. A/B Test Routing Accuracy
**Priority:** LOW  
**Why:** No benchmarking of TF-IDF vs ML routing  
**What:** Compare routing accuracy, measure improvement  
**Components:** Benchmarking scripts, metrics  
**Time:** 2 hours  
**Impact:** Data-driven routing improvements

---

## 📊 EXECUTION TIMELINE

### Week 1: Stabilize + Foundation
- [ ] P0.1: Delete meta-observer (1 min)
- [ ] P0.2: Fix session call tracking (30 min)
- [ ] P0.3: Wire plugin circuit breaker (2h)
- [ ] P0.4: Connect session memory (1h)
- [ ] P0.5: Fix debug output (30 min)
- [ ] P1.6: Mojo RAM Search Engine (2-4h)
- [ ] P1.7: Voice-to-Code Bridge (4-6h)

**Week 1 Total:** ~15-20 hours

### Week 2: Creative Tools
- [ ] P1.8: Holographic Context Reader (2h)
- [ ] P1.9: Connect ChromaDB (2h)
- [ ] P1.10: Cross-Agent Memory Sharing (2h)
- [ ] P2.11: Holographic Lyric Video (6-8h)
- [ ] P2.12: Self-Healing Editor (4-6h)

**Week 2 Total:** ~16-20 hours

### Week 3: Self-Improvement
- [ ] P2.13: Training Pipeline Integration (4h)
- [ ] P2.14: Music-to-Visual Engine (8h)
- [ ] P2.15: Pattern Library (2h)
- [ ] P3.16: Consolidate Scattered Memory (4h)
- [ ] P3.17: Remove Duplicate Sessions (2h)

**Week 3 Total:** ~20 hours

### Week 4: Optimization
- [ ] P3.18: Optimize ChromaDB + SQLite (2h)
- [ ] P3.19: Build Memory Health Monitoring (2h)
- [ ] P3.20: A/B Test Routing Accuracy (2h)
- [ ] Integration testing + documentation (8h)

**Week 4 Total:** ~14 hours

**Grand Total:** ~65-74 hours (~2-3 weeks at 30h/week)

---

## 🎯 SUCCESS METRICS

| Metric | Current | Target (Week 4) | How to Measure |
|--------|---------|-----------------|----------------|
| Session call tracking | 0% accurate | 100% accurate | `calls` field increments |
| Plugin isolation | None | Circuit breaker active | Plugin failure containment test |
| Memory persistence | 0% | 100% | Session restart retains memory |
| Mojo RAM search | Not implemented | <1ms latency | Benchmark search queries |
| Voice-to-code | Not implemented | Working | Speak intent → get code |
| ChromaDB connection | Idle | Queryable | Search returns results |
| Cross-agent sharing | 0% | 100% | Agents access shared memory |
| Lyric video pipeline | Manual | Automated | Drop song → get video |
| Training loop | Never runs | Auto-trigger at 100 corrections | Correction count → retrain |
| Memory health | No metrics | Real-time monitoring | Health dashboard |

---

## ⚠️ RISKS & MITIGATIONS

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Mojo RAM integration fails | High | Medium | Fallback to JSONL vectors |
| Voice-to-code accuracy low | Medium | Low | Use beam size 5, VAD filter |
| ChromaDB 27GB migration slow | High | Low | Incremental loading |
| Plugin breaker breaks existing | High | Low | Test with no-code-sisyphus first |
| Training loop degrades model | High | Low | Keep baseline model, A/B test |
| Lyric pipeline timing issues | Medium | Medium | Use SilenceSnap + MusiAlign |

---

## 🔗 DEPENDENCY CHAIN

```
P0 Fixes → P1 Foundation → P2 Creative Tools → P3 Optimization
    ↓           ↓               ↓                ↓
  System     Mojo RAM       Lyric Video      Consolidation
  Stability  Voice-Code     Self-Heal        Optimization
             Context        Training         Health Monitor
             ChromaDB       Pattern Lib      A/B Testing
             Cross-Agent    Music-Visual
```

**Critical Path:** P0.1 → P0.2 → P0.4 → P1.6 → P1.7 → P2.11 → P2.13

---

## 💡 SYNTHESIS INSIGHTS

### The Core Pattern
Every tool follows the same pattern:
```
[Input] → [Mojo RAM Search] → [Holographic Memory] → [Generation] → [Output]
```

### The Compounding Effect
- Week 1: 2x faster (Foundation)
- Week 2: 5x faster (Creative Tools)
- Week 3: 10x faster (Self-Improvement)
- Week 4: 50x faster (Optimization)

### The Ultimate Vision
**"Create at the speed of imagination"**
- You think it → You speak it → It appears
- Zero friction between thought and creation
- Self-improving system that gets smarter over time

---

## 🚀 NEXT STEPS

1. **Start with P0.1** — Delete meta-observer (1 minute)
2. **Then P0.2** — Fix session tracking (30 minutes)
3. **Then P1.6** — Build Mojo RAM Search (2-4 hours)
4. **Then chain the rest** — Each tool makes the next faster

**The infrastructure is there. The pieces are ready. Time to weaponize it.**

---

*This plan synthesizes everything from the full system context analysis: 37K transcripts, 30GB databases, 27GB vectors, complete ML pipeline, and the meta-observer incident lessons.*
