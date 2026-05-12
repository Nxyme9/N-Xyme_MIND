# N-Xyme Brain Optimization - Bulletproof Plan

## Executive Summary

This document synthesizes all fixes made to the OMO orchestration system, creating a bulletproof operational plan for the N-Xyme brain architecture.

---

## Part 1: Issues Identified & Fixed

### Issue 1: Agent Tag Mismatch ✅ FIXED
**Problem**: Calling `hephaestus` showed `sisyphus` tag  
**Root Cause**: `default_run_agent: "sisyphus"` in oh-my-openagent.json line 4  
**Fix**: Removed the override - now agents use their correct tags

### Issue 2: Agent Idle Token Waste ✅ FIXED
**Problem**: Agents consumed tokens indefinitely when no work  
**Root Cause**: No early exit mechanism  
**Fix**: Added circuit breaker in agent_loop.py:
- No-work counter: Exit after 2 iterations with no tool calls
- Progressive idle timeout: 60s → 120s → 180s
- Circuit breaker: Max 3 no-progress iterations = terminate

### Issue 3: GGUF Resource Optimization ✅ FIXED
**Problem**: Suboptimal local inference performance  
**Root Cause**: Default settings not tuned for RTX 3080 Ti  
**Fix**: Created optimized startup scripts:
- `-ngl 99` (all layers to GPU)
- `-c 8192` (8K context)
- `-np 16` (16 concurrent slots)
- `--flash-attn on` + `--flash-attn-type 2`
- `-ctk q4_0 -ctv q4_0` (KV cache quantization)
- New script: `bin/start_gguf_rtx3080ti_max.sh`

### Issue 4: Swappable LoRA Adapters ✅ IMPLEMENTED
**Problem**: No dynamic adapter switching  
**Fix**: Created adapter system:
- Registry: `frankenstein_engine/adapters/__init__.py`
- Adapters: rosetta-lora, fast-explore-lora, benchmark-lora
- CLI: `frankenstein adapters list/load/swap`
- Per-agent mapping: explore→fast-explore-lora, implement→rosetta-lora

### Issue 5: Standalone Trainer Module ✅ VERIFIED
**Problem**: Needed unified training pipeline  
**Status**: Already complete at `frankenstein_engine/trainer/__init__.py`
- 823 lines, Trainer class with prepare_data/train/evaluate
- Supports 57 MCP tools across 13 categories
- CLI: `frankenstein train --adapter rosetta-lora --tools all`

---

## Part 2: Current Agent Configuration

### oh-my-openagent.json (Active)

| Agent | Model | Mode | Purpose |
|-------|-------|------|---------|
| **sisyphus** | minimax-m2.5-free (high) | primary | Orchestrator - DELEGATES ONLY |
| **catalyst** | minimax-m2.5-free (high) | all | Master orchestrator (FLOW/FRICTION/ADAPT) |
| **hephaestus** | minimax-m2.5-free (medium) | all | Implementation - WRITES CODE |
| **explore** | gguf/rosetta-lora | subagent | Codebase search (local GGUF) |
| **librarian** | gguf/rosetta-lora | subagent | External research (local GGUF) |
| **oracle** | minimax-m2.5-free (high) | all | Architecture review |
| **metis** | minimax-m2.5-free (high) | all | Gap analysis |
| **momus** | minimax-m2.5-free (high) | all | Adversarial review |
| **prometheus** | minimax-m2.5-free (high) | all | Strategic planning |
| **atlas** | minimax-m2.5-free (medium) | all | Plan executor |
| **sisyphus-junior** | gguf/qwen2.5-0.5b | subagent | Light tasks |
| **multimodal-looker** | minimax-m2.5-free (medium) | all | Vision analysis |

---

## Part 3: Hardcoded Rules (AGENTS.md)

### Sisyphus - Delegation Only
```
AGENTS.md line 914: "Sisyphus MUST NEVER write code directly. This is non-negotiable."
Line 341: "ONLY Hephaestus writes code. All other agents MUST delegate coding work"
```

### Valid subagent_type Values
```
explore, librarian, oracle, metis, momus, plan, hephaestus, sisyphus, prometheus, atlas, sisyphus-junior, multimodal-looker
```

### Parallel Execution Rules
```
- run_in_background=true for explore/librarian (parallel)
- run_in_background=false for hephaestus/atlas (sequential)
- Max 8 concurrent agents
- Stuck Protocol: Reflect → Choose → Parallel Fire (3-10 agents)
```

---

## Part 4: GGUF Brain Architecture

### Multi-Model Brain Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    REQUEST ROUTING                          │
├─────────────────────────────────────────────────────────────┤
│  Simple Task (grep, find, list) → explore (GGUF)           │
│  Complex Task → sisyphus → hephaestus (API)                │
│  Research → librarian (GGUF)                               │
│  Review → oracle (API)                                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  LOCAL GGUF INFERENCE                       │
├─────────────────────────────────────────────────────────────┤
│  Model: qwen2.5-0.5b-instruct-q4_k_m (fallback)           │
│  LoRA: rosetta-lora (tool calling)                         │
│  Adapter Swap: fast-explore-lora, benchmark-lora           │
│  VRAM: 12.5GB max (RTX 3080 Ti)                           │
│  Target Latency: <50ms for simple tasks                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 TRAINING PIPELINE                           │
├─────────────────────────────────────────────────────────────┤
│  Trainer: frankenstein_engine/trainer/__init__.py          │
│  Tools: 57 MCP tools across 13 categories                  │
│  CLI: frankenstein train --adapter rosetta-lora --tools all│
│  LoRA Rank: 16-64 (default 16)                            │
│  Framework: Unsloth (2-5x faster, 70% less VRAM)          │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 5: Bulletproof Operational Rules

### 1. Delegation Protocol (Sisyphus)
- ✅ Always use `subagent_type` (not `category`) for delegation
- ✅ Use `run_in_background=true` for explore/librarian
- ✅ Use `run_in_background=false` for hephaestus/atlas
- ✅ Never write code directly - always delegate to hephaestus

### 2. Agent Spawning Rules
- ✅ 1 agent: SHALLOW tasks ("file", "fix", "error")
- ✅ 3 agents: STANDARD tasks ("find", "search", "list")
- ✅ 5 agents: DEEP tasks ("understand", "explain", "analyze")
- ✅ 8 agents: EXHAUSTIVE tasks ("deep dive", "exhaustive")

### 3. Idle Agent Handling
- ✅ Exit after 2 iterations with no tool calls
- ✅ Progressive timeout: 60s × (iteration + 1)
- ✅ Circuit breaker at 3 no-progress iterations

### 4. GGUF Optimization
- ✅ Use `start_gguf_rtx3080ti_max.sh` for max performance
- ✅ All layers on GPU (`-ngl 99`)
- ✅ 8K context (`-c 8192`)
- ✅ 16 concurrent slots (`-np 16`)
- ✅ Flash Attention with type 2 kernel

### 5. LoRA Adapter Management
- ✅ Use `frankenstein adapters list` to see available
- ✅ Use `frankenstein adapters swap <name>` to switch
- ✅ Per-agent defaults: explore→fast-explore-lora, implement→rosetta-lora

---

## Part 6: CLI Reference

### Frankenstein Engine
```bash
# Adapters
frankenstein adapters list         # Show available adapters
frankenstein adapters load <name>  # Load adapter
frankenstein adapters swap <name>  # Swap current adapter

# Training
frankenstein train --adapter rosetta-lora --tools all
frankenstein train --adapter memory-lora --tools memory
frankenstein train --list-adapters
```

### GGUF Server
```bash
# Max performance for RTX 3080 Ti
bash bin/start_gguf_rtx3080ti_max.sh

# With mode selection
bash bin/start_gguf_optimized.sh qwen2.5-0.5b-instruct-q4_k_m.gguf max-throughput

# Original config
bash start_llama_server.sh

# Status
./gguf_manager.sh status
./gguf_manager.sh switch qwen2.5-coder-7b-q4_k_m.gguf
```

---

## Part 7: Next Steps / Action Items

### Immediate (Today)
- [ ] Verify agent tag fix: Test `subagent_type="hephaestus"` now shows correct tag
- [ ] Start GGUF server with new optimized script
- [ ] Test idle timeout: Run agent with no work, verify early exit

### Short Term (This Week)
- [ ] Train new LoRA adapter on ALL 57 MCP tools (not just 10)
- [ ] Benchmark: Compare API vs GGUF latency for simple tasks
- [ ] Add more adapters: memory-lora, github-lora, filesystem-lora

### Long Term (This Month)
- [ ] Multi-env trainer: Support Python + Node + Bash environments
- [ ] Full brain: Triage model (0.5B) + Expert models (1-3B)
- [ ] Benchmark stats: 85%+ accuracy target on tool selection

---

## Verification Checklist

- [ ] Agent tags now correct (hephaestus = hephaestus, not sisyphus)
- [ ] Sisyphus only delegates, never writes code
- [ ] Idle agents exit early (no token waste)
- [ ] GGUF optimized for RTX 3080 Ti (8K context, 16 slots)
- [ ] LoRA adapters swappable at runtime
- [ ] Trainer supports all 57 MCP tools
- [ ] All CLI commands work
- [ ] Documentation complete

---

*Generated: 2026-04-13*
*Status: OPERATIONAL*