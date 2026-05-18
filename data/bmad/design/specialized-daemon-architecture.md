# Specialized Daemon Architecture

## Problem
One daemon doing everything: 73μs routing CONTENDED with 2.9s code searches and 25ms embeds.

## Solution
Three daemons, each optimized for one job, communicating via stdin/stdout JSON-L.

```
User/MCP                              Sidecars
    │                                      │
    ▼                                      │
┌──────────────────┐                      │
│  ROUTER DAEMON   │──code_search────▶┌──────────────────┐
│  (Mojo, 73μs)   │──embed──────────▶│  CODEX DAEMON    │
│  10 msg types    │◀─results────────│  (Python/RAM)    │
│  Zero deps       │                  │  62 files indexed│
│  5MB RAM         │                  │  Sub-ms search   │
└────────┬─────────┘                  │  200MB RAM       │
         │                           └──────────────────┘
         │ embed/generate             ┌──────────────────┐
         └──────────────────────────▶│  BRIDGE DAEMON   │
                                     │  (Python/socket)  │
                                     │  Rosetta v13 GPU  │
                                     │  3ms embed        │
                                     │  500MB VRAM       │
                                     └──────────────────┘
```

---

## 1. Router Daemon (`router.mojo`)
**Purpose:** Pure query routing. Never blocked. Never slow.

| Aspect | Detail |
|--------|--------|
| **Language** | Mojo 1.0 |
| **Protocol** | stdin/stdout JSON-L |
| **Msg types** | `route`, `status`, `metrics`, `correction` |
| **RAM** | ~5MB (25 tool strings + TF-IDF) |
| **Startup** | <1ms (no deps, no imports) |
| **Routing** | TF-IDF (73μs) + confidence scoring |
| **Rosetta fallback** | Sends embed request to Bridge via subprocess, waits for result |
| **Codex fallback** | Sends search request to Codex via subprocess, waits for result |
| **Pipeline** | route → TF-IDF → confidence > 0.6? → return || embed query → cosine sim → return |
| **Graceful degradation** | Bridge down? → TF-IDF only. Codex down? → no search. Router never dies. |

**Message flow:**
```
→ {"type": "route", "query": "save this note", "id": "1"}
← {"type": "route_result", "tool": "memory_write", "confidence": 0.34, "latency_us": 81, "id": "1"}
  (low confidence → would call Bridge for Rosetta embed)
```

**10 message types → 4 (router-only):**
- `route` — TF-IDF routing (73μs, no deps)
- `status` — health check
- `metrics` — latency stats
- `correction` — log to JSONL (simple file append)

Removed from router (moved to sidecars): `embed`, `code_search`, `code_review`, `batch_write`, `load`, `generate`, `memory_search`

---

## 2. Codex Daemon (`codex_daemon.py` → `codex.mojo`)
**Purpose:** Persistent code index in RAM. Sub-ms semantic search.

| Aspect | Detail |
|--------|--------|
| **Language** | Python → migrate to Mojo |
| **Protocol** | stdin/stdout JSON-L |
| **Msg types** | `search`, `index`, `review`, `status` |
| **RAM** | ~200MB (62+ file embeddings at 896-dim × 4 bytes) |
| **Startup** | 186ms (embed 62 files × 3ms each via Bridge) |
| **Search** | embed query (3ms via Bridge) + cosine sim (sub-ms) = ~4ms |
| **Index** | Full re-index on demand or on file change |

**Message flow:**
```
→ {"type": "search", "query": "routing engine", "top_k": 5, "id": "1"}
← {"type": "search_result", "query": "routing engine", "results": [...], "total": 62, "id": "1"}

→ {"type": "review", "file": "src/daemon.mojo", "id": "2"}
← {"type": "review_result", "file": "...", "lines": 423, "defs": 2, "memory": 90, "id": "2"}
```

---

## 3. Bridge Daemon (`bridge_daemon.py`)
**Purpose:** Persistent connection to Rosetta v13 on GPU. Single socket, no reconnect overhead.

| Aspect | Detail |
|--------|--------|
| **Language** | Python (until Mojo FFI stable) |
| **Protocol** | stdin/stdout JSON-L |
| **Msg types** | `embed`, `generate`, `status` |
| **Connection** | Persistent Unix socket to llama-server at /tmp/llama.sock |
| **Embed** | Send text → receive 896-dim vector → return JSON → ~3ms warm |
| **Startup** | 75ms (pre-embed 25 tool descriptions for router) |
| **Graceful** | If llama-server down → cache last response, retry |

**Message flow:**
```
→ {"type": "embed", "text": "find memory keys", "id": "1"}
← {"type": "embed_result", "embedding": [0.01, ...], "dim": 896, "latency_us": 3200, "id": "1"}
```

---

## 4. Benefits

| Metric | Current | Specialized | Improvement |
|--------|---------|-------------|-------------|
| `route` latency | 73μs (contended) | **73μs (always free)** | No blocking |
| `code_search` | 2,946ms (Python spawn) | **<5ms** (RAM cache) | **~600x** |
| `embed` | 25ms avg | **3ms** (persistent) | **~8x** |
| Codex Python | Loaded per call | **Loaded once** | **300ms saved per call** |
| Bridge socket | Created per call | **Kept open** | **~5ms saved per call** |
| Crash resilience | Everything dies | **Router survives** | Router ≤73μs always up |
| Parallel operations | 1 at a time | **3 concurrent** | Router + Codex + Bridge |

---

## 5. Implementation Plan

### Phase 1: Split (1 hour)
1. Create `bridge_daemon.py` — extract from `embed_bridge.py`, add persistent connection
2. Create `codex_daemon.py` — already exists, make it persistent (not per-call)
3. Strip `embed`/`code_search` from router → they forward to sidecars

### Phase 2: Persist (1 hour)
4. Make Codex load index ONCE at startup (currently reloads per call)
5. Make Bridge hold socket open (currently opens/closes per call)
6. Add health checks — Router tries sidecar once, falls back to TF-IDF on failure

### Phase 3: Parallel (2 hours)
7. Router spawns Codex + Bridge as subprocesses at startup
8. Router communicates via pipes (already stdin/stdout)
9. Router handles multiple concurrent requests (route while codex searches)

### Phase 4: Mojo-native (future)
10. `Codex in Mojo` — port from Python to Mojo with llama.cpp FFI
11. `Bridge in Mojo` — port socket connection to Mojo's `OwnedDLHandle`

---

## 6. File Locations

```
services/
├── router/
│   └── daemon.mojo           ← Cleaned router (4 msg types)
├── codex/
│   ├── codex_daemon.py       ← Persistent search daemon
│   └── codex.mojo            ← Mojo-native version (future)
├── bridge/
│   └── bridge_daemon.py      ← Persistent Rosetta/socket daemon
└── mojo-router/src/          ← Legacy (keep as backup)
    ├── daemon.mojo           ← Current monolith
    └── *_bridge.py           ← Current bridges
```
