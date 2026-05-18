---
name: memory-health-monitor
description: "Memory Health Monitor — dashboard showing: total vectors, agents covered, freshness, coverage gaps, search success rate."
---

# Memory Health Monitor

## Purpose
Provide live health dashboard for the entire memory system. Track coverage, freshness, quality, and operational metrics.

## Dashboard Metrics

### 1. VOLUME METRICS
| Metric | How to compute |
|--------|---------------|
| Total sessions | Count files in data/sessions/ by prefix |
| Total chunks | Count memory entries (list_memory) |
| Total vectors | Count entries with embeddings |
| Total compacted | Count entries with type:compacted |
| Storage used | Sum of file sizes in data/memory/ |
| Compression ratio | Total raw / total compacted |

### 2. COVERAGE METRICS
| Metric | How to compute |
|--------|---------------|
| Agents covered | Unique agent: tags across all entries |
| Sources covered | chatgpt, deepseek, nxyme, opencode |
| Date range | Min/max date tags |
| Type distribution | Count by type: code, error, decision, conversation |
| Gap analysis | Periods with no entries > 7 days |

### 3. FRESHNESS METRICS
| Metric | How to compute |
|--------|---------------|
| Most recent entry | Max date tag |
| Entries < 7 days | Count date: in current week |
| Entries < 30 days | Count date: in current month |
| Stale entries (>90d) | Count date: > 90 days ago |
| Average age | Mean of recency values |

### 4. QUALITY METRICS
| Metric | How to compute |
|--------|---------------|
| Tag completion rate | % entries with agent + date + type + topic tags |
| Importance distribution | Count per bucket: critical, important, normal, low, noise |
| Embedding coverage | % entries with valid embeddings |
| Dedup rate | % entries marked as duplicate vs unique |
| Empty/tiny entries | Entries < 50 chars (potential garbage) |

### 5. SEARCH METRICS
| Metric | How to compute |
|--------|---------------|
| Recent searches | Count of search_memory/search_semantic calls |
| Avg results per search | Mean result count |
| Zero-result rate | % searches returning 0 results |
| Avg search latency | Mean response time |
| Top searched agents | Most queried agent: filter |
| Top searched topics | Most common query terms |

## Health Score
```
health = (
    coverage_weight * 0.3 +
    freshness_weight * 0.25 +
    quality_weight * 0.25 +
    search_health * 0.2
) * 100

coverage_weight = min(agents_covered / 19, 1.0)  # 19 agents total
freshness_weight = min(entries_last_30d / 100, 1.0)  # target 100/mo
quality_weight = tag_completion_rate * embedding_coverage  # both 0-1
search_health = 1.0 - (zero_result_rate * 0.5)  # penalize empty searches
```

## Reporting Format

```
╔════════════════════════════════════════════════════╗
║        CORTEX MEMORY HEALTH REPORT                ║
╠════════════════════════════════════════════════════╣
║ HEALTH SCORE: 72/100  ▲ +5 from last week         ║
╠════════════════════════════════════════════════════╣
║ 📊 VOLUME                                           ║
║  Sessions: 13,813 (6,834 ChatGPT, 47 N-Xyme, ...)  ║
║  Chunks: 142,500                                    ║
║  Vectors: 138,200 (97% embedded)                    ║
║  Storage: 2.4 GB raw → 180 MB compacted (13x)      ║
╠════════════════════════════════════════════════════╣
║ 🎯 COVERAGE                                         ║
║  Agents: 14/19 (73%)  ⚠️ Missing: Vision, Phi-4   ║
║  Sources: 4/4 (100%)                                ║
║  Date range: 2024-09 → 2026-05                      ║
║  Gap: 12-day gap in April 2026                      ║
╠════════════════════════════════════════════════════╣
║ 🌱 FRESHNESS                                        ║
║  Last entry: 2 minutes ago                          ║
║  Entries < 7d: 340 (good)                           ║
║  Entries < 30d: 1,200                               ║
║  Stale > 90d: 98,000 (68%) ⚠️ Archive mostly      ║
╠════════════════════════════════════════════════════╣
║ ✅ QUALITY                                           ║
║  Tag completion: 82% ▲ (+3%)                        ║
║  Importance: ████ critical ████████ important       ║
║  Dedup rate: 7.8%                                   ║
║  Garbage: 1,200 entries < 50 chars                  ║
╠════════════════════════════════════════════════════╣
║ 🔍 SEARCH                                            ║
║  Recent queries: 45                                  ║
║  Avg results: 12.3                                   ║
║  Zero-result rate: 4.2%  ✅                           ║
║  Top agent: Sisyphus (32% of queries)                ║
╚════════════════════════════════════════════════════╝
```

## Scheduled Reporting
- **Daily**: Auto-generate health report
- **Weekly**: Compare trend (delta from last week)
- **Threshold alerts**: 
  - Health score drops > 10 points → notify user
  - Zero-result rate > 15% → investigate search pipeline
  - Tag completion < 60% → run auto-tagger on missing entries
  - Storage grows > 10% in a day → compaction needed

## NEVER
- Run health check on raw sessions (only processed/ingested data)
- Report metrics without comparing to previous period
- Skip error handling for any data source
- Assume zero results means "no data" — check if search is broken

## ALWAYS
- Show trend (▲/▼) vs previous report
- Surface actionable items (gaps to fill, compaction needed)
- Highlight top-value entries and biggest gaps
- Recommend next actions based on health score
