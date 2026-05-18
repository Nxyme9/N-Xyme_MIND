# FINAL FIX — N-Xyme Architecture Root Causes & Permanent Solutions

## THE 3 ROOT CAUSES

### 1. IDENTITY PROPAGATION (breaks everything)
Root: task() drops parentSessionID, parentAgent, parentTools
Fix: Replace task() with manager.launch() equivalent (OMO pattern)
Status: Understanding exists, implementation needs XTUI

### 2. PROMPT LOADING (agents don't know who they are)
Root: {file:...} loads entire agent.js including export default wrapper
Fix: All prompts must be INLINE in .opencode/agents/*.md (like Momus)
Status: Scalpel fixed. Hephaestus fixed. 3 more need fixing.

### 3. NO CROSS-SESSION MEMORY (agents start blank)
Root: No auto-injection of memory at session start
Fix: Every session loads ROOT.md, anti-hallucination rules, memory_search identity
Status: Infrastructure exists, injection not wired

## THE FIX PLAN

### IMMEDIATE (minutes)
1. Convert ALL remaining {file:...} agents to inline prompts
2. Add startup injection to every agent prompt

### SHORT (hours)
3. Wire outcome_logger to all task completions
4. Wire cross-session transfer to memory system
5. Set up session archiving

### MEDIUM (days)
6. Build XTUI with manager.launch() equivalent
7. Wire sleep engine for offline consolidation
8. Split megatool-mcp into modules

### LONG (weeks)
9. Replace static prompts with ML-loaded consciousness from embed_bridge
10. Full agent factory with identity in 896-dim embedding space
