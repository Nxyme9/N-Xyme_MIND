---
stepsCompleted: [1, 2]
inputDocuments:
  - "data/bmad/brainstorming/brainstorming-session-20260516.md"
date: 2026-05-16
author: N-Xyme
---

# Product Brief: N-Xyme_MIND

## Executive Summary

N-Xyme_MIND is a three-tier bleeding-edge tool call system that routes natural language requests to 25+ MCP tools at sub-ms speed. Mojo handles 90% of requests deterministically, Rosetta (fine-tuned Qwen2.5) handles ambiguous patterns at 40ms, and the main LLM only fires on novel requests (~1%). The system is designed for zero-token-waste: agents describe what they need, not how to call tools.

---

## Core Vision

### Problem Statement

Current AI agent systems waste 60-80% of context tokens on tool descriptions. Every agent session loads 22+ tool schemas at ~500 tokens each = 11K tokens of overhead before any real work. Tool routing is handled by the main LLM (seconds latency), adding cost and hallucination risk. When the ecosystem collapsed, six conflicting configs created cascading failures — wrong models, lost sessions, permission prompts on every command.

### Why Existing Solutions Fall Short

- **OpenCode's native MCP**: All tools to all agents, no filtering. Token bloat.
- **OMO/plugin-based injection**: Config hooks break on version updates. Fragile.
- **Single-LLM routing**: The main model shouldn't decide which tool to call — it's a deterministic mapping, not a reasoning problem.

### Proposed Solution

**Three-tier routing:**

| Tier | Engine | Speed | Accuracy | Coverage |
|------|--------|-------|----------|----------|
| 1 | Mojo TF-IDF | sub-ms | 100% deterministic | 90% of requests |
| 2 | Rosetta Qwen2.5-0.5B GGUF | ~40ms | 100% after training | ~9% of requests |
| 3 | Main LLM (DeepSeek/MiniMax) | seconds | — | ~1% novel requests |

### Key Differentiators

1. **Zero token waste on tool descriptions** — Rosetta knows all tools by heart
2. **Mojo sub-ms deterministic routing** — no LLM needed for 90% of tool calls
3. **Live training feedback loop** — Rosetta retrains on missed patterns until 100%
4. **One config, one truth** — `config/nx_agents.json` replaces 6+ conflicting configs
5. **ADHD-native design** — streak/XP/achievements, RSD-safe language, time estimates

---

## Target Users

### Primary: N-Xyme (Solo Builder)

Weaponized ADHD, deep technical expertise. Needs frictionless interaction — any delay or prompt breaks flow. Builds complex distributed AI systems alone. Values speed over ceremony, results over process.

### Secondary: Future Ecosystem Contributors

Once stabilized, the three-tier routing system becomes reusable for any opencode deployment. Plugin system with session isolation, hot-loaded agents, and the Mojo-Rosetta routing stack is a standalone product.

---

## Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Tool call accuracy (Mojo tier) | 100% on known patterns | Not yet measured |
| Rosetta training accuracy | 100% | Need retraining with 25 tools |
| Context saved by tiered routing | 10K tokens/session | Not yet measured |
| Agent registration time | Instant (plugin) | Working via config injection |
| Permission prompts | ZERO | Fixed via "permission": "allow" |
| Session continuity | Full context restore | welcome_back tool exists |

---

## Scope

### In Scope (Phase 1 — Mojo-Rosetta)

- Build Mojo tool router (TF-IDF scoring against 25 tool descriptions)
- Retrain Rosetta with our 25-tool set via nx_trainer pipeline
- Wire both into MCP `ask()` tool as routing backend
- Validate 100% accuracy on all tool calls

### In Scope (Phase 2 — Integration)

- Wire Mojo GGUF for 50ms inference (from current 500ms Python)
- Auto-retrain pipeline: log misses → generate training data → retrain
- nx-dictate tray app with session-isolated voice dictation

### Out of Scope (Future)

- Multi-modal routing (Vision queries → image tools)
- Cross-session learning from failure patterns
- Plugin marketplace / shareable routing models

---

## Constraints

- Must work with free-tier models (DeepSeek V4 Flash Free, MiniMax M2.5 Free)
- Must run on consumer GPU (3080 Ti, 12.5GB VRAM)
- One source of truth: `agents/{name}/agent.js`
- No opencode plugin dependency — bypass via config injection

---

## Next Steps

1. Build Mojo TF-IDF tool router (services/mojo-router/)
2. Generate Rosetta training data (training/mojo_rosetta.jsonl)
3. Retrain Rosetta via rosetta-train --preset qwen2.5-0.5b
4. Wire into MCP ask() tool as three-tier backend
5. Validate: all 25 tools return correct calls at 100%
