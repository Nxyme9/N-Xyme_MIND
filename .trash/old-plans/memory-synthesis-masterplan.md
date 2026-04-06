# MASTER PLAN: Global Memory Synthesis + Full Embedding Implementation

> **Created**: 2026-04-04
> **Goal**: Transform scattered, partially-embedded memory into a fully synthesized, 100% semantically-searchable unified memory system
> **Philosophy**: REBUILD FRESH — no patching, clean implementation

---

## Current State (Problem)

| Component | Status | Problem |
|-----------|--------|---------|
| 9 scattered databases | Fragmented | Memory spread across 3.65GB in 9 locations |
| 323 memories | 23.5% embedded | 247 memories have NO embeddings |
| Semantic search | Opt-in only | Not enabled by default |
| 26 "preferences" | 90% garbage | Test prompts, ALPHA-BLUE junk |
| 4 empty databases | Dead weight | jarvis_memory, jarvis_events, orchestrator, nervous_system |
| ChromaDB | Not initialized | No local vector fallback |
| 131K global messages | Zero indexing | Session history completely unsearchable |
| Auto-embed pipeline | Missing | New memories never get embedded |

---

## Target State (Solution)

| Component | Target | Impact |
|-----------|--------|--------|
| Unified memory dump | Single JSON at `.context/unified-memory-dump.json` | All sources synthesized |
| 323 memories | 100% embedded (768-dim nomic) | Full semantic search |
| Semantic search | Enabled by default | Every query uses vectors |
| Preferences | Clean, real preferences only | Agent loads correct context |
| Empty databases | Dropped or repurposed | Clean codebase |
| ChromaDB | Initialized with all memories | Local fallback working |
| Global messages | Top 500 indexed | Session history searchable |
| Auto-embed | Pipeline on memory creation | No future gaps |

---

## Execution Waves

### Wave 0: ENVIRONMENT VALIDATION + BACKUP (PRE-FLIGHT)
**Priority**: MANDATORY before any work

#### T0.1: Validate Environment
- **Agent**: `quick`
- **Task**: Check Ollama running (`curl localhost:11434`), verify `nomic-embed-text` model available, check chromadb installed, verify all 9 DB paths accessible, verify Python 3.10+
- **Success**: All checks pass, report generated

#### T0.2: Backup Database
- **Agent**: `quick`
- **Task**: Copy `context/memory/mind_from_mind.db` to `context/memory/mind_from_mind.db.backup.<timestamp>`. Verify backup integrity with `SELECT COUNT(*) FROM memories`
- **Success**: Backup file exists, row count matches original

---

### Wave 1: CRITICAL — Embedding Backfill + Semantic Enable
**Priority**: BLOCKING — do this first (after Wave 0)
**Parallel**: T1.1 and T1.2 can run simultaneously

#### T1.1: Backfill 247 Missing Embeddings
- **Agent**: `deep` (implementation)
- **File**: `scripts/backfill-embeddings.py`
- **Task**: Read all 323 memories from `context/memory/mind_from_mind.db`, check which lack embeddings in `memory_embeddings` table, generate embeddings via Ollama `nomic-embed-text:latest` (768-dim), insert missing ones
- **Success**: `SELECT COUNT(*) FROM memory_embeddings` returns 323
- **Constraints**: Use Ollama local (no API calls), batch process, handle Ollama not running gracefully

#### T1.2: Enable Semantic Search by Default
- **Agent**: `quick` (simple config change)
- **File**: `src/memory/router.py`
- **Task**: Change `self._semantic_enabled = False` to `self._semantic_enabled = True` in `MemoryRouter.__init__`. Also ensure `prime_semantic()` is called during boot
- **Success**: Semantic search runs without explicit enable call
- **Constraints**: Don't break existing search pipeline
---

### Wave 2: DATA CLEANUP
**Priority**: HIGH — clean the noise
**Parallel**: T2.1, T2.2, T2.3 can all run simultaneously

#### T2.1: Clean Preferences
- **Agent**: `deep` (needs judgment + implementation)
- **File**: `scripts/clean-preferences.py`
- **Task**: Read all 26 preferences from `mind_from_mind.db` (kind='preference'), filter out test prompts/ALPHA-BLUE junk/duplicates, keep only real user preferences. Archive originals to `preferences_archive` table, write cleaned list back
- **Success**: Only real preferences remain (estimated 3-5 real ones)
- **Constraints**: Archive to `preferences_archive` table first, never hard delete

#### T2.2: Drop Empty Databases
- **Agent**: `quick` (simple file operations)
- **Files**: `context/memory/jarvis_memory.db`, `context/memory/jarvis_events.db`, `modelrouter/data/orchestrator.db`, `data/nervous_system.db`
- **Task**: Verify all tables are 0 rows, move to `.trash/` directory (don't delete permanently), update any code references
- **Success**: 4 empty DBs moved to `.trash/`, no broken imports
- **Constraints**: Verify 0 rows before moving, keep for 30 days before permanent delete

#### T2.3: Initialize ChromaDB Local Fallback
- **Agent**: `deep` (setup + indexing)
- **File**: `scripts/init-chromadb.py`
- **Task**: Create ChromaDB at `.context/chroma_db/`, index all 323 memories with their embeddings, verify search works
- **Success**: ChromaDB collection has 323 documents, semantic search returns results
- **Constraints**: Use same nomic-embed-text model, don't duplicate embeddings

---

### Wave 3: GLOBAL MEMORY INDEXING
**Priority**: MEDIUM — unlock 131K messages
**Sequential**: T3.1 then T3.2 (T3.2 depends on T3.1 output)

#### T3.1: Index Top 500 Global Messages
- **Agent**: `deep` (large data processing)
- **File**: `scripts/index-global-messages.py`
- **Task**: Query `opencode-global.db` for 500 most recent/important messages (by session recency + message count), generate embeddings, store in new `global_message_index` table in `mind_from_mind.db`
- **Success**: 500 messages indexed with embeddings, searchable via unified router
- **Constraints**: Limit to 500 to avoid 3.6GB DB scan, use batch processing

#### T3.2: Extract Knowledge Graph from Sessions
- **Agent**: `deep` (pattern extraction)
- **File**: `scripts/extract-knowledge-graph.py`
- **Task**: Analyze top 100 sessions from `opencode-global.db`, extract entities (projects, decisions, architecture choices, user preferences) and relations, write to `.context/memory_graph/entities.json` and `.context/memory_graph/relations.json`
- **Success**: Knowledge graph with 50+ entities and 100+ relations
- **Constraints**: Focus on actionable knowledge, not conversation noise

---

### Wave 4: AUTO-EMBED PIPELINE + VERIFICATION
**Priority**: MEDIUM — prevent future gaps
**Sequential**: T4.1 then T4.2

#### T4.1: Auto-Embed Pipeline
- **Agent**: `deep` (architecture + implementation)
- **File**: `src/memory/embedding_pipeline.py` (new)
- **Task**: Create pipeline that automatically embeds new memories when created. Hook into memory save pathway. Add `embed_on_save=True` flag. Batch process if Ollama is available
- **Success**: New memories automatically get embeddings, no manual backfill needed
- **Constraints**: Non-blocking (don't slow memory save), graceful degradation if Ollama down

#### T4.2: Full System Verification
- **Agent**: `quick` (test script)
- **File**: `scripts/verify-memory-system.py`
- **Task**: Run comprehensive verification: embedding coverage = 100%, semantic search returns results, ChromaDB queryable, knowledge graph loadable, unified memory dump valid, all connectors healthy
- **Success**: All checks pass, report generated
- **Constraints**: Must be re-runnable for future health checks

---

## Delegation Map

| Wave | Task | Agent | Category | Skills | Parallel? |
|------|------|-------|----------|--------|-----------|
| 0 | T0.1: Validate env | `quick` | quick | [] | ✅ with T0.2 |
| 0 | T0.2: Backup DB | `quick` | quick | [] | ✅ with T0.1 |
| 1 | T1.1: Backfill embeddings | `deep` | deep | [] | ✅ with T1.2 |
| 1 | T1.2: Enable semantic | `quick` | quick | [] | ✅ with T1.1 |
| 2 | T2.1: Clean preferences | `deep` | deep | [] | ✅ with T2.2, T2.3 |
| 2 | T2.2: Drop empty DBs | `quick` | quick | [] | ✅ with T2.1, T2.3 |
| 2 | T2.3: Init ChromaDB | `deep` | deep | [] | ✅ with T2.1, T2.2 |
| 3 | T3.1: Index global msgs | `deep` | deep | [] | ❌ after Wave 2 |
| 3 | T3.2: Knowledge graph | `deep` | deep | [] | ❌ after T3.1 |
| 4 | T4.1: Auto-embed pipeline | `deep` | deep | [] | ❌ after Wave 3 |
| 4 | T4.2: Verification | `quick` | quick | [] | ❌ after T4.1 |
---

## Execution Order

```
Wave 0 (Parallel) ──→ Wave 1 (Parallel) ──→ Wave 2 (Parallel) ──→ Wave 3 (Sequential) ──→ Wave 4 (Sequential)
  T0.1 + T0.2          T1.1 + T1.2          T2.1 + T2.2 + T2.3     T3.1 → T3.2            T4.1 → T4.2
```

**Total estimated time**: ~8-12 minutes with parallel execution

---

## Success Criteria

- [ ] T0: Environment validated, database backed up
- [ ] T1.1: 323/323 memories embedded (100% coverage)
- [ ] T1.2: Semantic search enabled by default
- [ ] T2.1: Preferences cleaned (only real ones remain, junk archived)
- [ ] T2.2: 4 empty databases moved to .trash/
- [ ] T2.3: ChromaDB initialized with 323 documents
- [ ] T3.1: 500 global messages indexed with embeddings
- [ ] T3.2: Knowledge graph with 50+ entities, 100+ relations
- [ ] T4.1: Auto-embed pipeline working (new memories auto-embedded)
- [ ] T4.2: All verification checks pass
