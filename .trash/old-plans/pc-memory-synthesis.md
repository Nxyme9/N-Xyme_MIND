# Master Plan: PC-Wide Memory Synthesis System

## Mission
Scan all mounted drives (~9TB across 5 drives), extract content, generate embeddings, and synthesize into the existing unified memory system for searchable recall.

## Current State
| Component | Status | Notes |
|-----------|--------|-------|
| Drives | ✅ 5 mounted | Library (5.5T), WIN_LIBRARY (1.8T), NXYME_CORE (894G), NXYME_IMAGES (879G), backup (879G) |
| Memory System | ✅ Working | SQLite + ChromaDB + embedding pipeline (nomic-embed-text via Ollama) |
| Router | ✅ Working | RRF fusion, time-decay, 3 sources |
| MCP Server | ✅ Working | 5 tools, clean stdio |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     DRIVE SCANNER                               │
│  /mnt/{Library,WIN_LIBRARY,NXYME_CORE,NXYME_IMAGES,backup}     │
│  → Recursive file discovery with type filtering                │
│  → xxhash64 change detection (skip unchanged)                  │
│  → Progress tracking + resume capability                       │
└─────────────┬───────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  CONTENT EXTRACTORS                             │
│  ThreadPoolExecutor(16 workers)                                 │
│  - PDF: pdfplumber → PyPDF2 fallback                           │
│  - Code: tree-sitter AST extraction                            │
│  - Markdown: direct parse                                      │
│  - Text: direct read                                           │
│  → Chunking: 512 tokens, 50 overlap                            │
└─────────────┬───────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  EMBEDDING PIPELINE                             │
│  Batch queue (100 chunks/batch)                                 │
│  → Ollama nomic-embed-text (768-dim)                           │
│  → ChromaDB HNSW storage                                       │
│  → SQLite metadata + file_registry                             │
└─────────────┬───────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  QUERY INTERFACE                                │
│  Extend Memory Router with file source                          │
│  → RRF fusion with existing memory                             │
│  → MCP tools: search_files, get_file_context                   │
│  → Time-decay + importance scoring                             │
└─────────────┬───────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  INCREMENTAL SYNC                               │
│  Watchdog for real-time updates                                 │
│  → Periodic full scan with hash check                          │
│  → Cleanup deleted files                                       │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Waves

### Wave 1: Foundation (Parallel - 3 tasks)
**Goal**: Core infrastructure for file scanning and tracking

| Task | File | Description | Agent | Dependencies |
|------|------|-------------|-------|--------------|
| T1.1 | `src/memory/file_registry.py` | SQLite schema + xxhash64 functions + change detection | hephaestus | None |
| T1.2 | `src/memory/drive_scanner.py` | Recursive file discovery with filtering + progress tracking | hephaestus | None |
| T1.3 | `src/memory/scan_config.py` | Configuration system (drives, types, exclusions, limits) | hephaestus | None |

**Acceptance Criteria**:
- [ ] Can scan a test directory and return file list
- [ ] xxhash64 detects file changes correctly
- [ ] Configuration loads from JSON/env
- [ ] Progress persists across restarts

### Wave 2: Content Extraction (Sequential - 3 tasks)
**Goal**: Extract and chunk content from multiple file types

| Task | File | Description | Agent | Dependencies |
|------|------|-------------|-------|--------------|
| T2.1 | `src/memory/content_extractors.py` | Multi-format extractor (PDF, code, MD, text) | hephaestus | T1.1, T1.2 |
| T2.2 | `src/memory/chunker.py` | Token-based chunking (512 tokens, 50 overlap) | hephaestus | T2.1 |
| T2.3 | `src/memory/metadata_extractor.py` | File metadata (type, size, modified, drive, language) | hephaestus | T2.1 |

**Acceptance Criteria**:
- [ ] PDF extraction works with fallback
- [ ] Code extraction via tree-sitter
- [ ] Markdown/text extraction
- [ ] Chunking produces correct token counts
- [ ] Metadata extraction for all file types

### Wave 3: Embedding Integration (Sequential - 3 tasks)
**Goal**: Connect extraction to existing embedding pipeline

| Task | File | Description | Agent | Dependencies |
|------|------|-------------|-------|--------------|
| T3.1 | `src/memory/file_embedder.py` | Batch embedding queue + ChromaDB storage | hephaestus | T2.1, T2.2 |
| T3.2 | `src/memory/scan_progress.py` | Progress tracking + resume capability | hephaestus | T3.1 |
| T3.3 | `src/memory/scan_orchestrator.py` | Main scan loop + error handling + logging | hephaestus | T3.1, T3.2 |

**Acceptance Criteria**:
- [ ] Batch embeddings (100 chunks/batch)
- [ ] ChromaDB storage with HNSW
- [ ] Progress persists and resumes
- [ ] Error handling (skip corrupt files, log warnings)
- [ ] Can scan 1000 files without crashing

### Wave 4: Query Interface (Parallel - 3 tasks)
**Goal**: Make scanned files searchable via memory router

| Task | File | Description | Agent | Dependencies |
|------|------|-------------|-------|--------------|
| T4.1 | `src/memory/file_connector.py` | MemoryConnector implementation for file search | hephaestus | T3.1 |
| T4.2 | `src/memory/mcp_file_tools.py` | MCP tools: search_files, get_file_context | hephaestus | T4.1 |
| T4.3 | `src/memory/file_rrf.py` | RRF fusion with existing memory sources | hephaestus | T4.1 |

**Acceptance Criteria**:
- [ ] File search via memory router
- [ ] MCP tools return correct results
- [ ] RRF fusion ranks files + memories together
- [ ] Time-decay applies to file results

### Wave 5: Incremental Sync (Sequential - 3 tasks)
**Goal**: Keep memory in sync with drive changes

| Task | File | Description | Agent | Dependencies |
|------|------|-------------|-------|--------------|
| T5.1 | `src/memory/file_watcher.py` | Watchdog integration for real-time updates | hephaestus | T4.1 |
| T5.2 | `src/memory/scan_scheduler.py` | Periodic full scan with hash check | hephaestus | T5.1 |
| T5.3 | `src/memory/cleanup.py` | Remove deleted files from index | hephaestus | T5.2 |

**Acceptance Criteria**:
- [ ] File changes detected in real-time
- [ ] Periodic scan only processes changed files
- [ ] Deleted files removed from index
- [ ] System handles drive unmount/remount

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Hash algorithm | xxhash64 | 10GB/s vs md5 1GB/s, collision-resistant |
| Chunk size | 512 tokens, 50 overlap | Optimal for retrieval, balances context vs precision |
| Batch size | 100 chunks/batch | Reduces Ollama overhead, fits in memory |
| Thread pool | 16 workers (extraction), 4 (embedding) | I/O bound extraction, CPU bound embedding |
| File filtering | Skip binaries, >10MB, common non-text | Focus on indexable content |
| Error handling | Log and continue | Don't fail on single corrupt file |
| Progress tracking | SQLite file_registry table | Resume from last checkpoint |
| Drive priority | Smaller drives first | Quick wins, validate system before large scans |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Disk I/O bottleneck | Async I/O, batch reads, limit concurrent threads |
| Memory limits | Stream files, don't load entire drive into memory |
| Ollama rate limits | Batch embeddings, add retry logic with backoff |
| Corrupt files | Try/except around each file, log errors, continue |
| Permission issues | Skip unreadable files, log warnings |
| Network drives | Add timeout, skip if unavailable |
| Drive unmount | Handle FileNotFoundError, resume when remounted |
| ChromaDB corruption | WAL mode, backup before major operations |

## Dependencies to Install

```bash
pip install xxhash pdfplumber tree-sitter tree-sitter-python tree-sitter-javascript tree-sitter-typescript watchdog
```

## Success Metrics

| Metric | Target |
|--------|--------|
| First scan time | <72 hours for 9TB |
| Incremental scan | <1 hour (hash check skips unchanged) |
| Embedding throughput | >100 chunks/minute |
| Search latency | <500ms for file queries |
| Error rate | <1% of files skipped |
| Memory usage | <2GB during scan |

## Execution Order

```
Wave 1 (Parallel) → Wave 2 (Sequential) → Wave 3 (Sequential) → Wave 4 (Parallel) → Wave 5 (Sequential)
     T1.1, T1.2, T1.3        T2.1 → T2.2 → T2.3        T3.1 → T3.2 → T3.3        T4.1, T4.2, T4.3        T5.1 → T5.2 → T5.3
```

**Total Tasks**: 15
**Estimated Time**: 3-5 days (depending on agent throughput)
**Critical Path**: T1 → T2 → T3 → T4 → T5 (sequential waves)
