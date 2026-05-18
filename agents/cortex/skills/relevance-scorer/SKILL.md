---
name: relevance-scorer
description: "Relevance Scorer — scores chunks by type: decisions (10x) > code (5x) > errors (3x) > tool calls (1x) > system (0.1x)."
---

# Relevance Scorer

## Purpose
Score memory chunks by their long-term value to the N-Xyme system. Enable smart retention, pruning, and search ranking.

## Scoring Matrix

| Content Type | Base Score | Multiplier | Max Score | Rationale |
|-------------|-----------|-----------|-----------|-----------|
| **Decision** | 8 | 10x | 80 | Architecture decisions are permanent knowledge |
| **Code** | 5 | 5x | 25 | Written code is concrete and reusable |
| **Error** | 3 | 3x | 9 | Error patterns prevent future failures |
| **Plan** | 4 | 4x | 16 | Plans show intent and strategy |
| **Review** | 3 | 3x | 9 | Reviews capture quality judgments |
| **Tool Call** | 1 | 1x | 1 | Tool calls are operational, low long-term value |
| **Conversation** | 2 | 2x | 4 | Context but rarely reusable |
| **System** | 0.1 | 0.1x | 0.1 | Noise, boilerplate, repeated config |

## Adjustment Factors

### Recency Multiplier
| Age | Multiplier | Reason |
|-----|-----------|--------|
| 0-7 days | 1.0x | Current context |
| 7-30 days | 0.8x | Recent history |
| 30-90 days | 0.5x | Aging |
| 90-180 days | 0.3x | Cold storage |
| 180+ days | 0.1x | Archive only |

### Completeness Boost
| Factor | Boost |
|--------|-------|
| Full code with tests | +5 |
| Complete error with stack trace | +3 |
| Decision with alternatives considered | +5 |
| Partial/incomplete content | -2 |
| Truncated | -5 |

### Metadata Quality
| Has metadata | Boost |
|-------------|-------|
| Agent + date + type + tags | +2 |
| Agent + date + type | +1 |
| Only type or empty | 0 |

## Scoring Protocol

```
1. Classify chunk type (use auto-tagger)
2. Assign base score from matrix
3. Apply content-type multiplier
4. Apply recency multiplier
5. Apply completeness boost
6. Apply metadata quality boost
7. Normalize to 0-100 scale
8. Assign importance tag: [importance:score]
```

### Importance Buckets
| Score Range | Bucket | Action |
|------------|--------|--------|
| 50-100 | Critical | Forever keep, always index |
| 20-49 | Important | Keep through compaction |
| 5-19 | Normal | Default retention |
| 1-4 | Low | Compact with summary |
| < 1 | Noise | May be dropped in compaction |

## Search Ranking
When search returns results, sort by:
1. Primary: relevance score (descending)
2. Secondary: recency (descending)
3. Tertiary: completeness (descending)

## NEVER
- Assign score without classifying type first
- Give system shell output score > 1 (it's noise)
- Score raw session files (only processed chunks)
- Retroactively lower decisions score (< 10 minimum for decisions)

## ALWAYS
- Report score distribution: how many critical vs noise
- Surface top-10 highest-value memories
- Track score changes over compaction cycles
