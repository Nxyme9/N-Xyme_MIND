# Unified PC Memory System — Implementation Plan

## TL;DR

> **Quick Summary**: Build a unified memory system that scans ALL 5 drives (/mnt/*), extracts content (code, PDF, Markdown, DOCX), generates embeddings using existing pipeline, and makes everything searchable via the memory router.
> 
> **Deliverables**:
> - Multi-drive scanner for /mnt/* (Linux mounts)
> - Content extractors: code (tree-sitter), PDF (PyMuPDF), DOCX (python-docx), Markdown
> - Integration with existing embedding_pipeline.py (nomic-embed-text)
> - Incremental sync via watchdog + xxhash
> - New memory connector for file content queries
> 
> **Estimated Effort**: XL (large multi-phase project)
> **Parallel Execution**: YES - 5 waves with independent tasks
> **Critical Path**: Phase 1 foundation → Phase 2 extraction → Phase 3 embedding → Phase 4 sync → Phase 5 query

---

## Context

### Original Request
Build a unified memory system that scans ALL drives on this PC, extracts content, generates embeddings, and makes everything searchable via the memory router.

### Current State (MUST NOT BREAK)
- 323 embeddings in memory_embeddings table
- 175 global messages indexed with vectors
- 54 entities, 104 relations in knowledge graph
- ChromaDB 1.5.5 installed with HNSW support
- Embedding engine: Ollama (nomic-embed-text, 768 dims) with Sentence-Transformers fallback

### Drives to Scan
| Drive | Size | Mount Point |
|-------|------|-------------|
| Library | 5.5T | /mnt/Library |
| WIN_LIBRARY | 1.8T | /mnt/WIN_LIBRARY |
| NXYME_CORE | 894G | /mnt/NXYME_CORE |
| NXYME_IMAGES | 894G | /mnt/NXYME_IMAGES |
| backup | 894G | /mnt/backup |

### Interview Summary
**Key Discussions**:
- Test strategy: Tests after (implement first, add tests)
- Priority order: SCAN FIRST (get data indexed), then query second
- Risk tolerance: Break things but fix fast - existing memory MUST NOT BREAK

**Research Findings**:
- Existing code: file_indexer.py only watches Windows D:/, H:/ drives - NEEDS EXTENSION
- Embedding pipeline: Reuse existing (don't break 323 embeddings)
- Connectors: Pluggable architecture - can add new connector easily

### Technical Decisions Made
| Component | Decision | Rationale |
|-----------|----------|-----------|
| Embedding | Keep nomic-embed-text | Don't break 323 existing embeddings |
| Vector DB | Extend existing SQLite | Backward compatibility critical |
| Code parsing | tree-sitter-language-pack | 248 languages, production-ready |
| PDF extraction | PyMuPDF + pdfplumber | Hybrid (detection + extraction) |
| Incremental sync | watchdog + xxhash | Fast change detection |
| Summarization | Selective (>10KB) | Avoid LLM overload |

### Metis Review
**Identified Gaps** (addressed):
- Scope creep: Only index code, PDF, DOCX, Markdown - no media files
- Error handling: Add retry logic with exponential backoff for failing files
- Duplicates: Track file content hash to skip re-indexing unchanged files
- Batch processing: Process files in batches of 50 to avoid memory issues

---

## Work Objectives

### Core Objective
Build a unified memory system that indexes all file content across 5 drives (/mnt/*) into the existing memory system, making it searchable via the memory router.

### Concrete Deliverables
1. Multi-drive scanner (`src/memory/multi_drive_scanner.py`) - scans all /mnt/* mounts
2. Content extractors for code, PDF, DOCX, Markdown
3. Integration with existing embedding_pipeline.py
4. Incremental sync with watchdog
5. New memory connector for file content queries

### Definition of Done
- [ ] All 5 drives scanned and indexed
- [ ] Existing 323 embeddings still working (backward compat)
- [ ] New file content queryable via memory router
- [ ] Incremental sync operational (file changes detected and indexed)

### Must Have
- Backward compatibility with existing memory system
- Multi-drive support (/mnt/*)
- Content extraction for: code (.py, .js, .ts, .go, .rs, etc.), PDF, DOCX, Markdown
- Incremental sync (watch for changes, update embeddings)
- File content searchable via memory router

### Must NOT Have (Guardrails)
- DO NOT modify existing embedding_pipeline.py in ways that break existing embeddings
- DO NOT change the memory_embeddings table schema
- DO NOT modify existing connectors
- DO NOT index media files (images, videos, audio)
- DO NOT index files >100MB

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (existing test patterns)
- **Automated tests**: Tests after (per user request)
- **Framework**: pytest (existing in project)

### QA Policy
Every task includes agent-executed QA scenarios - run the scanner, verify output, check embeddings exist.

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation - can run in parallel):
├── T1: Multi-drive configuration + mount point verification
├── T2: Content extractor base classes + registry
├── T3: Code extractor (tree-sitter)
├── T4: PDF extractor (PyMuPDF)
├── T5: DOCX/Markdown extractors
└── T6: Fast-hash dedup filter

Wave 2 (Extraction Pipeline - max parallel):
├── T7: File discovery + filtering (all /mnt/* drives)
├── T8: Chunker + text normalization
├── T9: Embedding queue integration
├── T10: Extraction worker pool (multiprocessing)
└── T11: Progress tracking + stats

Wave 3 (Embedding Integration - sequential):
├── T12: Integrate with embedding_pipeline.py
├── T13: Add new columns to file_index table (hash, summary, source_drive)
├── T14: Batch embedding processing
└── T15: Error handling + retry logic

Wave 4 (Sync + Query):
├── T16: Watchdog-based incremental sync
├── T17: xxhash-based change detection
├── T18: New memory connector (FileSystemConnector)
├── T19: Router integration + query testing
└── T20: Health check + monitoring

Wave 5 (Testing + Polish):
├── T21: Integration tests (full scan of small drive)
├── T22: Performance tuning (batch sizes, worker count)
├── T23: Documentation + CLI commands
└── T24: Backward compat verification (ensure 323 embeddings still work)

Wave FINAL (Verification):
├── F1: Plan compliance audit
├── F2: Code quality review
├── F3: Real manual QA (scan + query)
└── F4: Scope fidelity check
```

### Dependency Matrix

| Task | Blocks | Blocked By |
|------|--------|------------|
| T1 | T7 | - |
| T2 | T3, T4, T5 | - |
| T3 | - | T2 |
| T4 | - | T2 |
| T5 | - | T2 |
| T6 | T9 | - |
| T7 | T11 | T1 |
| T8 | T9 | T3, T4, T5 |
| T9 | T12 | T6, T8 |
| T10 | T11 | T3, T4, T5, T8 |
| T11 | - | T7, T10 |
| T12 | T13 | T9 |
| T13 | T14 | T12 |
| T14 | T15 | T13 |
| T15 | T16 | T14 |
| T16 | T18 | T15 |
| T17 | T18 | T16 |
| T18 | T19 | T17 |
| T19 | T20 | T18 |
| T20 | T21 | T19 |
| T21 | T22 | T20 |
| T22 | T23 | T21 |
| T23 | T24 | T22 |
| T24 | F1-F4 | T23 |

---

## TODOs

> Implementation + Test = ONE Task. Every task includes QA scenarios for agent execution.

- [ ] 1. **Multi-drive configuration + mount point verification**

  **What to do**:
  - Create `src/memory/config.py` with drive configuration
  - Verify all 5 mount points exist and are accessible
  - Add mount point health checks
  - Create config schema for watched directories

  **Must NOT do**:
  - Modify existing config files
  - Hardcode paths outside /mnt/*

  **Recommended Agent Profile**:
  - **Category**: quick
  - **Skills**: []
  - Reason: Simple config + verification task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T2-T6)
  - **Blocks**: T7
  - **Blocked By**: None

  **References**:
  - `src/memory/registry.py` - Config pattern to follow
  - `src/file_indexer.py:15-30` - Mount point handling

  **Acceptance Criteria**:
  - [ ] Config loads all 5 drive paths
  - [ ] Health check confirms all drives accessible
  - [ ] CLI command to list drives works

  **QA Scenarios**:
  ```
  Scenario: Verify all drives accessible
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from src.memory.config import DRIVES; print([d for d in DRIVES if d.exists()])"
    Expected Result: List of 5 drive paths that exist
    Evidence: .sisyphus/evidence/task-1-drives.json

  Scenario: Missing drive handling
    Tool: Bash
    Preconditions: None
    Steps:
      1. Simulate missing drive by temporarily modifying config
    Expected Result: Graceful error, not crash
    Evidence: .sisyphus/evidence/task-1-missing-drive.log
  ```

  **Commit**: YES (group 1)
  - Message: `feat(memory): add multi-drive config`
  - Files: `src/memory/config.py`, `tests/test_config.py`

---

- [ ] 2. **Content extractor base classes + registry**

  **What to do**:
  - Create abstract base class `ContentExtractor` in `src/memory/extractors/__init__.py`
  - Create extractor registry pattern
  - Define supported file types mapping
  - Add extractor health check

  **Must NOT do**:
  - Implement actual extractors (that's T3-T5)
  - Modify existing code

  **Recommended Agent Profile**:
  - **Category**: quick
  - **Skills**: []
  - Reason: Simple abstract base class + registry

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1, T3-T6)
  - **Blocks**: T3, T4, T5
  - **Blocked By**: None

  **References**:
  - `src/memory/connectors.py` - Registry pattern to follow
  - `src/memory/registry.py` - Health check pattern

  **Acceptance Criteria**:
  - [ ] ContentExtractor base class defined
  - [ ] Registry can register/retrieve extractors
  - [ ] Supports: code, pdf, docx, markdown

  **QA Scenarios**:
  ```
  Scenario: Registry registration
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from src.memory.extractors import extractor_registry; print(extractor_registry.list())"
    Expected Result: List of registered extractors
    Evidence: .sisyphus/evidence/task-2-registry.json
  ```

  **Commit**: YES (group 1)
  - Message: `feat(memory): add content extractor base classes`
  - Files: `src/memory/extractors/__init__.py`

---

- [ ] 3. **Code extractor (tree-sitter)**

  **What to do**:
  - Install tree-sitter-language-pack
  - Implement `CodeExtractor` class
  - Support languages: Python, JavaScript, TypeScript, Go, Rust, Java, C/C++, Ruby, PHP, Swift, Kotlin
  - Extract function definitions, classes, imports as chunks
  - Handle parsing errors gracefully

  **Must NOT do**:
  - Index entire file (too large for embedding)
  - Fail on syntax errors (try best-effort parsing)

  **Recommended Agent Profile**:
  - **Category**: deep
  - **Skills**: []
  - Reason: Complex parsing logic, error handling

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1, T2, T4-T6)
  - **Blocks**: T8
  - **Blocked By**: T2

  **References**:
  - `scripts/block-scanner.py` - Existing AST-based extraction
  - tree-sitter documentation

  **Acceptance Criteria**:
  - [ ] Extracts code chunks for 5+ languages
  - [ ] Handles syntax errors gracefully (doesn't crash)
  - [ ] Returns chunks with metadata (language, type, line numbers)

  **QA Scenarios**:
  ```
  Scenario: Python code extraction
    Tool: Bash
    Preconditions: None
    Steps:
      1. Create test file: echo 'def hello(): return "world"' > /tmp/test.py
      2. Run: python -c "from src.memory.extractors import CodeExtractor; e = CodeExtractor(); print(e.extract('/tmp/test.py'))"
    Expected Result: List of extracted chunks with function definition
    Evidence: .sisyphus/evidence/task-3-python.json

  Scenario: JavaScript code extraction
    Tool: Bash
    Preconditions: None
    Steps:
      1. Create test file: echo 'function foo() { return 1; }' > /tmp/test.js
      2. Run: python -c "from src.memory.extractors import CodeExtractor; e = CodeExtractor(); print(e.extract('/tmp/test.js'))"
    Expected Result: List of extracted chunks
    Evidence: .sisyphus/evidence/task-3-js.json
  ```

  **Commit**: YES (group 1)
  - Message: `feat(memory): add tree-sitter code extractor`
  - Files: `src/memory/extractors/code.py`, `tests/test_code_extractor.py`

---

- [ ] 4. **PDF extractor (PyMuPDF)**

  **What to do**:
  - Install PyMuPDF (fitz) and pdfplumber
  - Implement `PDFExtractor` class
  - Detect page type (text-based vs scanned)
  - Extract text with page metadata
  - Extract tables using pdfplumber
  - Handle corrupted PDFs gracefully

  **Must NOT do**:
  - OCR (too slow for initial build)
  - Index image-only PDFs (skip with warning)

  **Recommended Agent Profile**:
  - **Category**: deep
  - **Skills**: []
  - Reason: Complex PDF parsing with multiple libraries

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1, T2, T3, T5, T6)
  - **Blocks**: T8
  - **Blocked By**: T2

  **References**:
  - PyMuPDF documentation
  - `athena/scripts/code_indexer.py` - Existing extraction patterns

  **Acceptance Criteria**:
  - [ ] Extracts text from PDF
  - [ ] Detects page type (text vs image)
  - [ ] Returns chunks with page numbers
  - [ ] Handles corrupted PDFs gracefully

  **QA Scenarios**:
  ```
  Scenario: PDF text extraction
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from src.memory.extractors import PDFExtractor; e = PDFExtractor(); print(len(e.extract('sample.pdf')))"
    Expected Result: List of extracted chunks with text
    Evidence: .sisyphus/evidence/task-4-pdf.json
  ```

  **Commit**: YES (group 1)
  - Message: `feat(memory): add PDF extractor`
  - Files: `src/memory/extractors/pdf.py`, `tests/test_pdf_extractor.py`

---

- [ ] 5. **DOCX/Markdown extractors**

  **What to do**:
  - Install python-docx
  - Implement `DOCXExtractor` class
  - Implement `MarkdownExtractor` class
  - Extract paragraphs, headings, tables from DOCX
  - Extract headings, code blocks, lists from Markdown

  **Must NOT do**:
  - Render Markdown (just extract text)

  **Recommended Agent Profile**:
  - **Category**: deep
  - **Skills**: []
  - Reason: Two extractors, moderate complexity

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1-T4, T6)
  - **Blocks**: T8
  - **Blocked By**: T2

  **References**:
  - python-docx documentation

  **Acceptance Criteria**:
  - [ ] DOCX: extracts paragraphs, headings
  - [ ] Markdown: extracts headings, code blocks
  - [ ] Both return chunks with metadata

  **QA Scenarios**:
  ```
  Scenario: DOCX extraction
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from src.memory.extractors import DOCXExtractor; e = DOCXExtractor(); print(len(e.extract('sample.docx')))"
    Expected Result: List of extracted chunks
    Evidence: .sisyphus/evidence/task-5-docx.json
  ```

  **Commit**: YES (group 1)
  - Message: `feat(memory): add DOCX and Markdown extractors`
  - Files: `src/memory/extractors/docx.py`, `src/memory/extractors/markdown.py`

---

- [ ] 6. **Fast-hash dedup filter**

  **What to do**:
  - Install xxhash
  - Implement `FastHashFilter` class
  - Compute xxhash for file content
  - Store hash → file path mapping
  - Skip files with matching hash (no re-indexing)

  **Must NOT do**:
  - Use slow SHA256 (use xxhash)
  - Store full content (only hash)

  **Recommended Agent Profile**:
  - **Category**: quick
  - **Skills**: []
  - Reason: Simple hash computation + storage

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1-T5)
  - **Blocks**: T9
  - **Blocked By**: None

  **References**:
  - `src/file_indexer.py` - Existing file tracking

  **Acceptance Criteria**:
  - [ ] Computes xxhash for files
  - [ ] Persists hash state to JSON file
  - [ ] Skips unchanged files

  **QA Scenarios**:
  ```
  Scenario: Hash computation
    Tool: Bash
    Preconditions: None
    Steps:
      1. echo "test content" > /tmp/hashfile.txt
      2. Run: python -c "from src.memory.dedup import FastHashFilter; f = FastHashFilter(); print(f.compute_hash('/tmp/hashfile.txt'))"
    Expected Result: Hex hash string
    Evidence: .sisyphus/evidence/task-6-hash.json
  ```

  **Commit**: YES (group 1)
  - Message: `feat(memory): add fast-hash dedup filter`
  - Files: `src/memory/dedup.py`

---

- [ ] 7. **File discovery + filtering**

  **What to do**:
  - Implement `FileDiscoverer` class
  - Walk all 5 /mnt/* directories recursively
  - Apply filters: extensions, size, hidden files
  - Generate file manifest with metadata
  - Handle permission errors gracefully

  **Must NOT do**:
  - Index all files (filter by extension)
  - Follow symlinks (avoid infinite loops)

  **Recommended Agent Profile**:
  - **Category**: deep
  - **Skills**: []
  - Reason: Multi-drive traversal, permission handling

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T1)
  - **Parallel Group**: Wave 2
  - **Blocks**: T11
  - **Blocked By**: T1

  **References**:
  - `src/file_indexer.py:40-80` - File walking logic
  - os.walk documentation

  **Acceptance Criteria**:
  - [ ] Walks all 5 mount points
  - [ ] Filters by extension (.py, .js, .pdf, .docx, .md)
  - [ ] Excludes hidden files and files >100MB
  - [ ] Returns file manifest

  **QA Scenarios**:
  ```
  Scenario: File discovery
    Tool: Bash
    Preconditions: T1 complete
    Steps:
      1. Run: python -c "from src.memory.scanner import FileDiscoverer; d = FileDiscoverer(); files = d.discover('/mnt/Library'); print(len(files))"
    Expected Result: Count of discovered files
    Evidence: .sisyphus/evidence/task-7-files.json
  ```

  **Commit**: YES (group 2)
  - Message: `feat(memory): add file discovery`
  - Files: `src/memory/scanner.py`

---

- [ ] 8. **Chunker + text normalization**

  **What to do**:
  - Implement `Chunker` class
  - Split content into chunks (max 2000 tokens)
  - Normalize whitespace, remove control chars
  - Add overlap for context continuity
  - Handle edge cases (empty files, binary)

  **Must NOT do**:
  - Lose content (preserve all text)
  - Create too-small chunks (<100 chars)

  **Recommended Agent Profile**:
  - **Category**: deep
  - **Skills**: []
  - Reason: Text processing logic

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T3-T5)
  - **Parallel Group**: Wave 2
  - **Blocks**: T9
  - **Blocked By**: T3, T4, T5

  **References**:
  - Existing chunking in embedding_pipeline.py

  **Acceptance Criteria**:
  - [ ] Chunks content at logical boundaries
  - [ ] Normalizes whitespace
  - [ ] Handles empty files gracefully

  **QA Scenarios**:
  ```
  Scenario: Text chunking
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from src.memory.chunker import Chunker; c = Chunker(); print(c.chunk('short text'))
    Expected Result: List of chunks
    Evidence: .sisyphus/evidence/task-8-chunks.json
  ```

  **Commit**: YES (group 2)
  - Message: `feat(memory): add text chunker`
  - Files: `src/memory/chunker.py`

---

- [ ] 9. **Embedding queue integration**

  **What to do**:
  - Integrate with existing embedding_pipeline.py
  - Add new queue for file embeddings
  - Use existing nomic-embed-text model
  - Batch processing (10 at a time)
  - Background thread worker

  **Must NOT do**:
  - Break existing embedding pipeline
  - Change existing memory_embeddings schema

  **Recommended Agent Profile**:
  - **Category**: deep
  - **Skills**: []
  - Reason: Integration with existing code

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T6, T8)
  - **Parallel Group**: Wave 2
  - **Blocks**: T12
  - **Blocked By**: T6, T8

  **References**:
  - `src/memory/embedding_pipeline.py:30-60` - Existing queue integration
  - `src/memory/embeddings.py` - EmbeddingEngine

  **Acceptance Criteria**:
  - [ ] Embeddings added via existing pipeline
  - [ ] Queue processes in background
  - [ ] Batch processing works

  **QA Scenarios**:
  ```
  Scenario: Embedding queue
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from src.memory.embedding_queue import EmbeddingQueue; q = EmbeddingQueue(); q.add('test_id', 'test content'); print(q.size())"
    Expected Result: Queue size = 1
    Evidence: .sisyphus/evidence/task-9-queue.json
  ```

  **Commit**: YES (group 2)
  - Message: `feat(memory): add embedding queue integration`
  - Files: `src/memory/embedding_queue.py`

---

- [ ] 10. **Extraction worker pool**

  **What to do**:
  - Implement multiprocessing worker pool
  - Distribute extraction across workers
  - Process files in parallel
  - Handle worker failures gracefully
  - Report progress

  **Must NOT do**:
  - Use threading (GIL issues)
  - Spawn too many workers (>8)

  **Recommended Agent Profile**:
  - **Category**: deep
  - **Skills**: []
  - Reason: Multiprocessing coordination

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T3-T5, T8)
  - **Parallel Group**: Wave 2
  - **Blocks**: T11
  - **Blocked By**: T3, T4, T5, T8

  **References**:
  - multiprocessing.Pool documentation

  **Acceptance Criteria**:
  - [ ] Processes files in parallel
  - [ ] Handles worker failures
  - [ ] Reports progress

  **QA Scenarios**:
  ```
  Scenario: Worker pool
    Tool: Bash
    Preconditions: T3-T5 implemented
    Steps:
      1. Run: python -c "from src.memory.worker_pool import ExtractionPool; p = ExtractionPool(max_workers=4); print(p.is_alive())"
    Expected Result: True
    Evidence: .sisyphus/evidence/task-10-pool.json
  ```

  **Commit**: YES (group 2)
  - Message: `feat(memory): add extraction worker pool`
  - Files: `src/memory/worker_pool.py`

---

- [ ] 11. **Progress tracking + stats**

  **What to do**:
  - Implement progress tracking
  - Track: files scanned, extracted, embedded
  - Persist state to JSON
  - CLI progress display
  - Handle resume after interruption

  **Must NOT do**:
  - Lose progress on crash
  - Update too frequently (performance)

  **Recommended Agent Profile**:
  - **Category**: quick
  - **Skills**: []
  - Reason: Simple state tracking

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T7, T10)
  - **Parallel Group**: Wave 2
  - **Blocks**: None
  - **Blocked By**: T7, T10

  **References**:
  - `src/file_indexer.py` - Existing progress tracking

  **Acceptance Criteria**:
  - [ ] Tracks progress in JSON
  - [ ] CLI shows progress bar
  - [ ] Resumes after interruption

  **QA Scenarios**:
  ```
  Scenario: Progress tracking
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from src.memory.progress import ProgressTracker; p = ProgressTracker(); p.update('scanned', 10); print(p.get())"
    Expected Result: Progress dict with counts
    Evidence: .sisyphus/evidence/task-11-progress.json
  ```

  **Commit**: YES (group 2)
  - Message: `feat(memory): add progress tracking`
  - Files: `src/memory/progress.py`

---

- [ ] 12. **Integrate with embedding_pipeline.py**

  **What to do**:
  - Use existing embed_memory function
  - Add metadata (source drive, file type, hash)
  - Store in memory_embeddings with new columns
  - Test backward compatibility

  **Must NOT do**:
  - Break existing 323 embeddings
  - Change schema in ways that break existing

  **Recommended Agent Profile**:
  - **Category**: deep
  - **Skills**: []
  - Reason: Integration with existing pipeline

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T9)
  - **Parallel Group**: Wave 3
  - **Blocks**: T13
  - **Blocked By**: T9

  **References**:
  - `src/memory/embedding_pipeline.py:80-120` - embed_memory function

  **Acceptance Criteria**:
  - [ ] Embeddings stored via existing pipeline
  - [ ] Metadata stored alongside embeddings
  - [ ] Existing embeddings still work

  **QA Scenarios**:
  ```
  Scenario: Embedding integration
    Tool: Bash
    Preconditions: T9 complete
    Steps:
      1. Run: python -c "from src.memory.embedding_pipeline import embed_memory; id = embed_memory('test', 'test content'); print(id)"
    Expected Result: memory_id returned
    Evidence: .sisyphus/evidence/task-12-embed.json
  ```

  **Commit**: YES (group 3)
  - Message: `feat(memory): integrate with embedding pipeline`
  - Files: `src/memory/file_embedding.py`

---

- [ ] 13. **Add new columns to file_index table**

  **What to do**:
  - ALTER TABLE to add: source_drive, file_hash, summary, indexed_at
  - Handle migration for existing data
  - Update schema documentation

  **Must NOT do**:
  - Drop existing columns
  - Break existing queries

  **Recommended Agent Profile**:
  - **Category**: quick
  - **Skills**: []
  - Reason: Simple schema migration

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T12)
  - **Parallel Group**: Wave 3
  - **Blocks**: T14
  - **Blocked By**: T12

  **References**:
  - `src/memory/migrator.py` - Existing migration patterns

  **Acceptance Criteria**:
  - [ ] New columns added
  - [ ] Existing data preserved
  - [ ] Migration handles existing files

  **QA Scenarios**:
  ```
  Scenario: Schema migration
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "import sqlite3; conn = sqlite3.connect('context/memory/mind_from_mind.db'); c = conn.execute('PRAGMA table_info(memory_embeddings)'); print([r for r in c])"
    Expected Result: List of columns including new ones
    Evidence: .sisyphus/evidence/task-13-schema.json
  ```

  **Commit**: YES (group 3)
  - Message: `feat(memory): add file metadata columns`
  - Files: `src/memory/migrations/add_file_columns.py`

---

- [ ] 14. **Batch embedding processing**

  **What to do**:
  - Implement batch processing (50 files at a time)
  - Parallel embedding generation
  - Progress callbacks
  - Handle rate limits

  **Must NOT do**:
  - Overload embedding service
  - Lose batches on error

  **Recommended Agent Profile**:
  - **Category**: deep
  - **Skills**: []
  - Reason: Batch processing logic

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T13)
  - **Parallel Group**: Wave 3
  - **Blocks**: T15
  - **Blocked By**: T13

  **References**:
  - `src/memory/embeddings.py:50-80` - Batch processing

  **Acceptance Criteria**:
  - [ ] Processes in batches of 50
  - [ ] Reports progress
  - [ ] Handles errors gracefully

  **QA Scenarios**:
  ```
  Scenario: Batch processing
    Tool: Bash
    Preconditions: T13 complete
    Steps:
      1. Run: python -c "from src.memory.batch_embedding import BatchProcessor; p = BatchProcessor(); print(p.process_batch(['file1', 'file2']))"
    Expected Result: Processed count
    Evidence: .sisyphus/evidence/task-14-batch.json
  ```

  **Commit**: YES (group 3)
  - Message: `feat(memory): add batch embedding processing`
  - Files: `src/memory/batch_embedding.py`

---

- [ ] 15. **Error handling + retry logic**

  **What to do**:
  - Add exponential backoff retry
  - Handle extraction failures gracefully
  - Log errors with context
  - Skip corrupted files (don't crash)

  **Must NOT do**:
  - Silent failures
  - Retry infinitely

  **Recommended Agent Profile**:
  - **Category**: deep
  - **Skills**: []
  - Reason: Error handling logic

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T14)
  - **Parallel Group**: Wave 3
  - **Blocks**: T16
  - **Blocked By**: T14

  **References**:
  - `athena/src/athena/memory/vectors.py` - Error handling patterns

  **Acceptance Criteria**:
  - [ ] Retry with exponential backoff (max 3 retries)
  - [ ] Log errors with file path
  - [ ] Continue processing on failure

  **QA Scenarios**:
  ```
  Scenario: Error handling
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from src.memory.error_handling import retry_with_backoff; @retry_with_backoff(max_retries=2); def failing(): raise Exception('test'); failing()"
    Expected Result: Exception after retries
    Evidence: .sisyphus/evidence/task-15-error.json
  ```

  **Commit**: YES (group 3)
  - Message: `feat(memory): add error handling and retry logic`
  - Files: `src/memory/error_handling.py`

---

- [ ] 16. **Watchdog-based incremental sync**

  **What to do**:
  - Implement watchdog Observer
  - Watch all 5 mount points
  - Queue changed files for re-indexing
  - Debounce rapid changes

  **Must NOT do**:
  - Re-index on every keystroke
  - Miss file deletions

  **Recommended Agent Profile**:
  - **Category**: deep
  - **Skills**: []
  - Reason: Watchdog integration

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T15)
  - **Parallel Group**: Wave 4
  - **Blocks**: T18
  - **Blocked By**: T15

  **References**:
  - `src/file_indexer.py:100-150` - Watchdog usage

  **Acceptance Criteria**:
  - [ ] Watches all 5 mount points
  - [ ] Queues changed files
  - [ ] Debounces rapid changes (1s)

  **QA Scenarios**:
  ```
  Scenario: Watchdog sync
    Tool: Bash
    Preconditions: T15 complete
    Steps:
      1. Run: python -c "from src.memory.watcher import FileWatcher; w = FileWatcher(); w.start(); import time; time.sleep(2); w.stop()"
    Expected Result: Watcher starts and stops without error
    Evidence: .sisyphus/evidence/task-16-watch.json
  ```

  **Commit**: YES (group 4)
  - Message: `feat(memory): add watchdog incremental sync`
  - Files: `src/memory/watcher.py`

---

- [ ] 17. **xxhash-based change detection**

  **What to do**:
  - Compare file hash before/after changes
  - Skip re-indexing if hash unchanged
  - Update hash after processing
  - Handle file moves/renames

  **Must NOT do**:
  - Use slow SHA256
  - Re-index unchanged files

  **Recommended Agent Profile**:
  - **Category**: deep
  - **Skills**: []
  - Reason: Hash comparison logic

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T16)
  - **Parallel Group**: Wave 4
  - **Blocks**: T18
  - **Blocked By**: T16

  **References**:
  - T6 (FastHashFilter)

  **Acceptance Criteria**:
  - [ ] Detects file changes via hash
  - [ ] Skips unchanged files
  - [ ] Handles file moves

  **QA Scenarios**:
  ```
  Scenario: Change detection
    Tool: Bash
    Preconditions: None
    Steps:
      1. echo "v1" > /tmp/changetest.txt
      2. Run: python -c "from src.memory.change_detector import ChangeDetector; d = ChangeDetector(); print(d.has_changed('/tmp/changetest.txt'))"
      3. echo "v2" > /tmp/changetest.txt
      4. Run: python -c "from src.memory.change_detector import ChangeDetector; d = ChangeDetector(); print(d.has_changed('/tmp/changetest.txt'))"
    Expected Result: True (detected change)
    Evidence: .sisyphus/evidence/task-17-change.json
  ```

  **Commit**: YES (group 4)
  - Message: `feat(memory): add xxhash change detection`
  - Files: `src/memory/change_detector.py`

---

- [ ] 18. **New memory connector (FileSystemConnector)**

  **What to do**:
  - Implement `FileSystemConnector` class
  - Implement `search()` method
  - Query file content by hash
  - Return results with metadata

  **Must NOT do**:
  - Break existing connectors
  - Duplicate existing functionality

  **Recommended Agent Profile**:
  - **Category**: deep
  - **Skills**: []
  - Reason: New connector implementation

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T16, T17)
  - **Parallel Group**: Wave 4
  - **Blocks**: T19
  - **Blocked By**: T16, T17

  **References**:
  - `src/memory/connectors.py` - Existing connector patterns

  **Acceptance Criteria**:
  - [ ] FileSystemConnector registered
  - [ ] search() returns file results
  - [ ] Integrated with registry

  **QA Scenarios**:
  ```
  Scenario: Connector search
    Tool: Bash
    Preconditions: T17 complete
    Steps:
      1. Run: python -c "from src.memory.connectors import get_connector; c = get_connector('filesystem'); print(c.search('test'))"
    Expected Result: List of results
    Evidence: .sisyphus/evidence/task-18-connector.json
  ```

  **Commit**: YES (group 4)
  - Message: `feat(memory): add filesystem connector`
  - Files: `src/memory/connectors/filesystem.py`

---

- [ ] 19. **Router integration + query testing**

  **What to do**:
  - Integrate new connector with MemoryRouter
  - Add filesystem to enabled sources
  - Test unified query
  - Verify backward compat

  **Must NOT do**:
  - Break existing router
  - Change existing query behavior

  **Recommended Agent Profile**:
  - **Category**: deep
  - **Skills**: []
  - Reason: Router integration

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T18)
  - **Parallel Group**: Wave 4
  - **Blocks**: T20
  - **Blocked By**: T18

  **References**:
  - `src/memory/router.py` - Router implementation
  - `src/memory/registry.py` - Connector registration

  **Acceptance Criteria**:
  - [ ] Router queries filesystem
  - [ ] Results returned with scores
  - [ ] Existing sources still work

  **QA Scenarios**:
  ```
  Scenario: Router integration
    Tool: Bash
    Preconditions: T18 complete
    Steps:
      1. Run: python -c "from src.memory.router import MemoryRouter; r = MemoryRouter(); result = r.query('test query'); print(result.total_results)"
    Expected Result: Total results including filesystem
    Evidence: .sisyphus/evidence/task-19-router.json
  ```

  **Commit**: YES (group 4)
  - Message: `feat(memory): integrate filesystem with router`
  - Files: `src/memory/router_integration.py`

---

- [ ] 20. **Health check + monitoring**

  **What to do**:
  - Add health check for filesystem connector
  - Add monitoring stats
  - CLI command for status
  - Alert on failures

  **Must NOT do**:
  - Over-monitor (performance impact)

  **Recommended Agent Profile**:
  - **Category**: quick
  - **Skills**: []
  - Reason: Simple health check

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T19)
  - **Parallel Group**: Wave 4
  - **Blocks**: T21
  - **Blocked By**: T19

  **References**:
  - `src/memory/registry.py` - Health check pattern

  **Acceptance Criteria**:
  - [ ] Health check returns status
  - [ ] CLI shows stats
  - [ ] Monitors index health

  **QA Scenarios**:
  ```
  Scenario: Health check
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from src.memory.health import check_filesystem; print(check_filesystem())"
    Expected Result: Health status dict
    Evidence: .sisyphus/evidence/task-20-health.json
  ```

  **Commit**: YES (group 4)
  - Message: `feat(memory): add health monitoring`
  - Files: `src/memory/health.py`

---

- [ ] 21. **Integration tests (full scan of small drive)**

  **What to do**:
  - Test full scan of /mnt/backup (smallest drive)
  - Verify embeddings created
  - Verify query returns results
  - Measure performance

  **Must NOT do**:
  - Break existing functionality
  - Overload system resources

  **Recommended Agent Profile**:
  - **Category**: unspecified-high
  - **Skills**: []
  - Reason: Integration testing

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T20)
  - **Parallel Group**: Wave 5
  - **Blocks**: T22
  - **Blocked By**: T20

  **Acceptance Criteria**:
  - [ ] Full scan completes
  - [ ] Embeddings created
  - [ ] Query returns results

  **QA Scenarios**:
  ```
  Scenario: Full scan integration
    Tool: Bash
    Preconditions: All previous tasks complete
    Steps:
      1. Run: python -c "from src.memory.scanner import full_scan; full_scan('/mnt/backup')"
      2. Wait for completion
      3. Run: python -c "from src.memory.router import MemoryRouter; r = MemoryRouter(); print(r.query('code').total_results)"
    Expected Result: Results > 0
    Evidence: .sisyphus/evidence/task-21-integration.json
  ```

  **Commit**: YES (group 5)
  - Message: `test(memory): add integration tests`
  - Files: `tests/test_integration.py`

---

- [ ] 22. **Performance tuning**

  **What to do**:
  - Tune batch sizes
  - Optimize worker count
  - Profile bottleneck
  - Reduce memory usage

  **Must NOT do**:
  - Break functionality for speed
  - Use unsafe optimizations

  **Recommended Agent Profile**:
  - **Category**: unspecified-high
  - **Skills**: []
  - Reason: Performance optimization

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T21)
  - **Parallel Group**: Wave 5
  - **Blocks**: T23
  - **Blocked By**: T21

  **Acceptance Criteria**:
  - [ ] Batch size optimized (50)
  - [ ] Worker count tuned (4-8)
  - [ ] Memory usage reasonable

  **QA Scenarios**:
  ```
  Scenario: Performance test
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from src.memory.perf import benchmark; print(benchmark())"
    Expected Result: Performance metrics
    Evidence: .sisyphus/evidence/task-22-perf.json
  ```

  **Commit**: YES (group 5)
  - Message: `perf(memory): tune performance`
  - Files: `src/memory/perf.py`

---

- [ ] 23. **Documentation + CLI commands**

  **What to do**:
  - Document all modules
  - Add CLI commands
  - Add --help documentation
  - Create quickstart guide

  **Must NOT do**:
  - Over-document (maintain instead)

  **Recommended Agent Profile**:
  - **Category**: writing
  - **Skills**: []
  - Reason: Documentation writing

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T22)
  - **Parallel Group**: Wave 5
  - **Blocks**: T24
  - **Blocked By**: T22

  **References**:
  - `src/file_indexer.py` - CLI pattern

  **Acceptance Criteria**:
  - [ ] CLI commands work
  - [ ] Help shows usage
  - [ ] Quickstart guide exists

  **QA Scenarios**:
  ```
  Scenario: CLI help
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -m src.memory.cli --help
    Expected Result: Help text
    Evidence: .sisyphus/evidence/task-23-cli.json
  ```

  **Commit**: YES (group 5)
  - Message: `docs(memory): add CLI and documentation`
  - Files: `src/memory/cli.py`, `docs/memory.md`

---

- [ ] 24. **Backward compat verification**

  **What to do**:
  - Verify existing 323 embeddings still work
  - Test memory router with existing sources
  - Ensure no regressions
  - Report status

  **Must NOT do**:
  - Break existing functionality

  **Recommended Agent Profile**:
  - **Category**: unspecified-high
  - **Skills**: []
  - Reason: Verification testing

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T23)
  - **Parallel Group**: Wave 5
  - **Blocks**: F1-F4
  - **Blocked By**: T23

  **References**:
  - `src/memory/embedding_pipeline.py` - Existing embeddings

  **Acceptance Criteria**:
  - [ ] 323 existing embeddings still queryable
  - [ ] Router returns existing results
  - [ ] No errors on existing data

  **QA Scenarios**:
  ```
  Scenario: Backward compat
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python -c "from src.memory.router import MemoryRouter; r = MemoryRouter(); result = r.query('existing'); print(result.total_results)"
    Expected Result: Existing results still returned
    Evidence: .sisyphus/evidence/task-24-compat.json
  ```

  **Commit**: YES (group 5)
  - Message: `test(memory): verify backward compatibility`
  - Files: `tests/test_compat.py`

---

## Final Verification Wave

- [ ] F1. **Plan Compliance Audit** — Read plan, verify all tasks implemented
- [ ] F2. **Code Quality Review** — Lint, typecheck, no security issues
- [ ] F3. **Real Manual QA** — Full scan, query, verify results
- [ ] F4. **Scope Fidelity Check** — No feature creep, all requirements met

---

## Commit Strategy

| Group | Tasks | Message | Files |
|-------|-------|---------|-------|
| 1 | T1-T6 | `feat(memory): add foundation (config, extractors, dedup)` | Multiple |
| 2 | T7-T11 | `feat(memory): add scanning pipeline (discovery, chunking, workers)` | Multiple |
| 3 | T12-T15 | `feat(memory): add embedding integration (pipeline, batch, error handling)` | Multiple |
| 4 | T16-T20 | `feat(memory): add sync and query (watcher, connector, router)` | Multiple |
| 5 | T21-T24 | `test, perf, docs: integration tests, tuning, documentation` | Multiple |

---

## Success Criteria

### Verification Commands
```bash
# List all drives
python -m src.memory.cli list-drives

# Start full scan
python -m src.memory.cli scan --all

# Check status
python -m src.memory.cli status

# Query memory
python -m src.memory.cli query "search term"
```

### Final Checklist
- [ ] All 5 drives scanned and indexed
- [ ] Existing 323 embeddings still working
- [ ] New file content queryable via router
- [ ] Incremental sync operational
- [ ] All tests pass
- [ ] Backward compatibility verified
