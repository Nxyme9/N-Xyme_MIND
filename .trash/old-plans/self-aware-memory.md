# Master Plan: Self-Aware PC Memory System

## Vision
A continuously running daemon that maintains real-time awareness of all PC data across 5 drives (9TB), automatically indexing, synthesizing, and self-healing — like a living memory system that never sleeps.

## Current State
- ✅ 15 modules built (scanner, extractor, chunker, embedder, connector, watcher, scheduler, cleanup)
- ✅ Test scan: 200 files → 3,093 chunks in 107s
- ✅ All dependencies installed (watchdog, pdfplumber, PyMuPDF, xxhash)
- ❌ No continuous daemon running
- ❌ No self-monitoring or self-healing
- ❌ No knowledge synthesis (just raw chunks)
- ❌ No priority/importance learning

## Architecture: The Living Memory System

```
┌─────────────────────────────────────────────────────────────────┐
│                    SELF-AWARENESS LOOP                          │
│                                                                 │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐   │
│  │  PERCEIVE   │───▶│  UNDERSTAND  │───▶│     ACT         │   │
│  │             │    │              │    │                 │   │
│  │ • Watchdog  │    │ • Synthesize │    │ • Index new     │   │
│  │ • Scanner   │    │ • Rank       │    │ • Update old    │   │
│  │ • Health    │    │ • Learn      │    │ • Heal broken   │   │
│  └─────────────┘    └──────────────┘    └─────────────────┘   │
│        ▲                                         │             │
│        └─────────────────────────────────────────┘             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              MEMORY CORE (Always Running)               │   │
│  │                                                         │   │
│  │  • File Watcher (real-time)                            │   │
│  │  • Embedding Queue (async)                             │   │
│  │  • Knowledge Graph (relationships)                     │   │
│  │  • Health Monitor (self-check)                         │   │
│  │  • Priority Engine (what matters)                      │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Waves

### Wave 1: Continuous Daemon (3 tasks)
**Goal**: System runs 24/7 as a background service

| Task | File | Description | Agent |
|------|------|-------------|-------|
| T1.1 | `src/memory/daemon.py` | Main daemon loop with graceful start/stop/restart | hephaestus |
| T1.2 | `src/memory/health_monitor.py` | Self-monitoring: embedding health, DB integrity, disk space | hephaestus |
| T1.3 | `src/memory/priority_engine.py` | Learns what files are important (access frequency, recency, content value) | hephaestus |

**Acceptance Criteria**:
- [ ] Daemon starts with `python3 -m src.memory.daemon`
- [ ] Runs continuously without crashing
- [ ] Graceful shutdown on SIGTERM/SIGINT
- [ ] Health check endpoint (HTTP or file-based)
- [ ] Logs all activity to `context/memory/daemon.log`

### Wave 2: Knowledge Synthesis (3 tasks)
**Goal**: System doesn't just store chunks — it understands relationships

| Task | File | Description | Agent |
|------|------|-------------|-------|
| T2.1 | `src/memory/knowledge_graph.py` | Extract entities/relationships from indexed content | hephaestus |
| T2.2 | `src/memory/synthesizer.py` | Generate summaries, find connections between files | hephaestus |
| T2.3 | `src/memory/topic_model.py` | Auto-categorize files into topics/clusters | hephaestus |

**Acceptance Criteria**:
- [ ] Knowledge graph with 100+ entities from indexed files
- [ ] Auto-generated summaries for each directory
- [ ] Topic clusters (e.g., "Python projects", "Documentation", "Configs")
- [ ] Query returns related files, not just keyword matches

### Wave 3: Self-Healing (3 tasks)
**Goal**: System fixes itself without human intervention

| Task | File | Description | Agent |
|------|------|-------------|-------|
| T3.1 | `src/memory/self_healer.py` | Detect and fix corrupted embeddings, stale entries | hephaestus |
| T3.2 | `src/memory/integrity_checker.py` | Periodic integrity checks (ChromaDB, SQLite, file existence) | hephaestus |
| T3.3 | `src/memory/auto_recovery.py` | Re-embed failed files, rebuild corrupted indexes | hephaestus |

**Acceptance Criteria**:
- [ ] Auto-detects corrupted embeddings
- [ ] Re-embeds failed files automatically
- [ ] Rebuilds corrupted indexes without data loss
- [ ] Reports healing actions in logs

### Wave 4: Real-Time Awareness (3 tasks)
**Goal**: System knows what's happening on the PC right now

| Task | File | Description | Agent |
|------|------|-------------|-------|
| T4.1 | `src/memory/activity_tracker.py` | Track file access patterns, active projects | hephaestus |
| T4.2 | `src/memory/context_awareness.py` | Understand what user is working on (based on recent files) | hephaestus |
| T4.3 | `src/memory/proactive_indexer.py` | Pre-index files user is likely to need next | hephaestus |

**Acceptance Criteria**:
- [ ] Knows which projects are "active" (recently modified)
- [ ] Prioritizes indexing active project files
- [ ] Can answer "what am I working on?" query
- [ ] Pre-indexes likely-needed files

### Wave 5: System Service (3 tasks)
**Goal**: Runs as a proper system service (systemd)

| Task | File | Description | Agent |
|------|------|-------------|-------|
| T5.1 | `bin/n-xyme-memory.service` | systemd service file | hephaestus |
| T5.2 | `bin/n-xyme-memory.sh` | Service management script (start/stop/status/restart) | hephaestus |
| T5.3 | `src/memory/dashboard.py` | Web dashboard showing system status, stats, health | hephaestus |

**Acceptance Criteria**:
- [ ] `systemctl start n-xyme-memory` works
- [ ] Auto-starts on boot
- [ ] `bin/n-xyme-memory.sh status` shows health
- [ ] Dashboard at http://localhost:8769 shows real-time stats

## Execution Order

```
Wave 1 (Daemon) → Wave 2 (Synthesis) → Wave 3 (Self-Healing) → Wave 4 (Awareness) → Wave 5 (Service)
```

## Success Metrics

| Metric | Target |
|--------|--------|
| Uptime | >99% (daemon runs continuously) |
| Index lag | <5 seconds (file change → indexed) |
| Self-healing | 100% of corrupted embeddings fixed automatically |
| Knowledge graph | 1000+ entities from full scan |
| Query latency | <500ms for any query |
| Memory usage | <4GB during operation |
| Disk usage | <50GB for indexes (9TB source) |

## Key Design Principles

1. **Never lose data** — if embedding fails, queue for retry
2. **Never block** — all operations async, non-blocking
3. **Never crash** — catch all exceptions, log and continue
4. **Always self-aware** — knows its own health, performance, gaps
5. **Always learning** — improves priority rankings over time
