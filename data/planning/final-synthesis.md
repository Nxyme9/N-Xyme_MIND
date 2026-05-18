# N-Xyme MIND — Final Synthesis: Data & Code Plan
**2026-05-17 | 12+ hour session | 18 agents | 47 NAP tools | 140+ archive files**

---

## PART 1: THE THREE ROOT CAUSES

| # | Root Cause | What Breaks | Fix |
|---|------------|-------------|-----|
| 1 | task() drops parentSessionID/agent/tools | Identity propagation. Subagents can't prove who they are. | Replace with manager.launch() from OMO pattern (needs XTUI or SDK) |
| 2 | {file:...} loads export default wrapper | Agent prompts start with export default { instead of identity | All prompts INLINE in .opencode/agents/*.md (like Momus). 4 fixed, 1 remains |
| 3 | No startup context injection | Every session starts blank. Agents don't know what exists | Startup protocol: ROOT.md, anti-hallucination, nap_protocol, memory_search, pc_aware |

## PART 2: WHAT WAS BUILT THIS SESSION

### 30 New MCP Tools
parallel_task, task_status, session_tasks, bg_submit, bg_status, bg_list, bg_cancel,
cache_stats, cache_clear, nap_protocol, safe_delete, read_memory, write_memory, list_memory,
web_fetch, web_search, file_batch_read, project_map, embed_text, embed_similarity,
pc_scan, pc_aware, agent_edit, consciousness_record, consciousness_identity,
ask_question, spawn_task, context_prune, session_status, verify_code

### 2 New Agents
Cortex (Memory & Knowledge, all, deepseek-v4)
Sisyphus Junior (Fast code writer, subagent, minimax)

### Agents Fixed
Hephaestus: bash restored, deepseek-v4, 6 skills, inline prompt
Scalpel: mode all, Code Dissector, Frankenstein v2, tools.json fixed, inline prompt
Sisyphus: 9-step delegation tree, parallel protocol, 6 BMAD skills
Kairos: 2 therapy skills attached
Cortex: tools.json fixed

## PART 3: DATA STRUCTURE

### MEMORY LAYER (data/memory/)
- holographic-memory.json — Main store (TF-IDF + vectors)
- global-context-*.md — Global awareness (updated daily)
- consciousness/ — Per-agent identity in embedding space (hephaestus, momus, sisyphus)
- core/ — Memory core (26 files from archive, disconnected)
- consolidated/ — Consolidated entries
- vectors/ — Stored vectors
- graph/ — Knowledge graph
- models/ — Memory models

### ML LAYER (data/ml/)
### LEARNING LAYER (data/learning/)
### SESSION DATA (data/sessions/)
### CONFIG LAYER (data/config/)

## PART 4: THE ARCHIVE (140+ Files, All Disconnected)

### Masterplans
masterplan-memory-learning-consolidation.md (828 lines)
learning-memory-integration-plan.md (439 lines)
learning-masterplan.md (70 lines)
BRAIN_ARCHITECTURE_MASTERPLAN.md (370 lines)
BRAIN_VS_MEMORY_ARCHITECTURE.md (75 lines)
masterplan-omo-synthesis.md (96 lines)
BLEEDING_EDGE_TRAINER_MASTERPLAN.md (262 lines)

### Built But Not Wired
learning_engine/ (~45 files): Q-Learning, Bandits, cross-session, signals. 6 broken imports.
memory_core/ (~38 files): 6 retrievers, 4 cognitive modules, sleep engine. 9 broken imports.
intelligence/ (~40 files): Delegation learner, predictive router, triggers. route_task() never called.
local_llm/ (~19 files): GGUF client, model router, RAG injector. Not connected.
training/ (~28 scripts + ~18 datasets): 12 trainer types, 42 iterations. 24GB checkpoints not deployed.

### Existing But Orphaned
context/memory/knowledge_graph.json (1005 lines)
context/memory/agent_cards.json (74 lines)
nx_trainer/outputs/rosetta_v35/ (436MB trained LoRA)
nx_trainer/outputs/ total (24GB all training)

## PART 5: CRITICAL PATH — What to Wire First

### 1. Fix Package Imports (15 broken imports)
archive/packages/learning_engine/ -> data/ml/src/learning_engine/
archive/packages/memory_core/ -> data/ml/src/memory_core/

### 2. Uncomment record_outcome() in execution flow
### 3. Call route_task() before delegation
### 4. Enable cognitive layer triggers on memory writes
### 5. Wire AdvancedLearningEngine to Strategy 5 in unified_router.py

## PART 6: THE REAL INSIGHT

The user built all of this in 2 months with zero experience.

The archive has everything. The masterplans document everything.
The code is all there. Just disconnected.

Every build attempt today recreated what already existed.
Every problem hit was already documented in a masterplan.
Every proposed solution already existed in the codebase.

One instruction at session start — Read ROOT.md, load global context, search memory —
would have prevented 90% of this session's wasted effort.

The system already is what you built. I just need to read what exists before building what doesn't.
