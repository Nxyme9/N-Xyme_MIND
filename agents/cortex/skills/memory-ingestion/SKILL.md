---
name: memory-ingestion
description: "Memory Ingestion Manager — pipeline that reads sessions, extracts content, filters garbage, chunks intelligently, embeds via ONNX bridge, stores with rich metadata."
---

# Memory Ingestion Manager

## Purpose
Ingest raw session files into structured, tagged, embedded memory chunks with rich metadata.

## Pipeline Steps

### 1. DISCOVER
- Use `file_glob("data/sessions/*.jsonl")` to find all session files
- Filter by prefix: `chatgpt_*`, `ses_*`, `deepseek_*` to classify source
- Count total files, classify by type: archive vs project vs test vs unknown
- Report: `Found X sessions (Y ChatGPT, Z N-Xyme, W test)`

### 2. SCAN (for each batch of 50 files)
- Use `file_grep` to identify file size, line count, content structure
- Skip files < 100 bytes (garbage)
- Identify JSONL format vs plain text vs corrupted
- Each file read: first 10 lines to determine schema

### 3. EXTRACT
- Parse each session file for:
  - Messages (user vs assistant vs system)
  - Tool calls (name, args, result)
  - Errors, warnings, exceptions
  - Decisions made, code written
  - Agent identity from messages
  - Timestamps, dates
- Filter out: system noise, repeated boilerplate, empty messages
- Chunk intelligently:
  - Each message = 1 chunk
  - Code blocks split from text
  - Error traces as separate chunks
  - Group consecutive related messages into "episodes"

### 4. CLASSIFY
For each chunk, determine:
- **Source**: chatgpt, deepseek, opensesame, nxyme, unknown
- **Type**: conversation, code, error, decision, plan, review, tool_call, system
- **Agent**: which N-Xyme agent (Sisyphus, Hephaestus, etc.) or "external"
- **Date**: extract timestamp from session metadata

### 5. ANNOTATE
- Add structural tags:
  - `[agent:<name>]` — which agent
  - `[date:<YYYY-MM>]` — rough date
  - `[type:<type>]` — content type
  - `[source:<source>]` — origin
  - `[topic:<topic>]` — from keyword analysis
  - `[importance:<1-10>]` — relevance score
  - `[recency:<days>]` — how recent
- Compute semantic tags via embed_text + cluster analysis

### 6. EMBED
- For each chunk, generate embedding via `embed_text(chunk_text)`
- If chunk > 512 tokens, split into overlapping segments (256 token overlap)
- Store embedding in vector store with full metadata

### 7. STORE
- Write memory entry via `write_memory()` with:
  - `content`: The chunk text
  - `category`: `session/{source}/{type}`
  - Embedding vector
  - Tags as metadata
- Update index: `data/memory/vectors/index.json`

### 8. REPORT
After each batch:
```
Ingested: 50 sessions (1250 chunks)
  - 800 chatgpt archive
  - 400 nxyme project  
  - 50 test/unknown
Tags: 45 unique agents, 12 types
Embeddings: 1250 stored (avg 384-dim)
Time: 4.2s batch
```

## NEVER
- Modify raw session files
- Store without tagging
- Ingest binary/non-text files
- Skip error handling for corrupt files
- Process all files at once (batch by 50)

## ALWAYS
- Preserve raw data before any transformation
- Report stats after every batch
- Tag everything with agent, date, type
- Handle corrupt files gracefully (skip + log)
