# Delegation Orchestration Optimization Masterplan

> **Goal**: Transform manual delegation into intelligent, self-optimizing orchestration
> **Based on**: 3 parallel agents (explore + librarian + oracle) + existing nxyme-auto-delegation-upgrade.md
> **Date**: 2026-04-05
> **Status**: READY FOR IMPLEMENTATION

---

## 1. Current State Assessment

### What Works ✅
| Component | Status |
|:----------|:-------|
| 11 agents configured | ✅ All with models, fallbacks, permissions |
| 6-section prompt protocol | ✅ TASK, OUTCOME, TOOLS, MUST DO, MUST NOT, CONTEXT |
| 3-tier context passing | ✅ Always/Conditional/On-demand |
| Hephaestus-exclusive coding | ✅ Enforced in AGENTS.md |
| Direct delegation paths | ✅ Prometheus/Oracle/Momus → Hephaestus |
| Anti-loop protocol | ✅ 6 rules, max attempts, fingerprinting |
| Quality gates | ✅ 7 gates in pipeline |
| Fallback chains | ✅ All agents have 2 fallbacks |

### What's Missing ❌
| Gap | Impact | Priority |
|:----|:-------|:---------|
| **No complexity scorer** | Can't auto-route based on task difficulty | P0 |
| **No performance tracking** | Can't learn from delegation failures | P0 |
| **No shared result store** | Agents duplicate work | P0 |
| **No prompt validation** | Bad prompts sent to agents | P1 |
| **No cost-aware routing** | Wastes tokens on expensive models | P1 |
| **No workload balancing** | Can overload single agent | P1 |
| **No auto-review chain** | Manual Oracle/Momus triggering | P1 |
| **No failure rerouting** | Static fallbacks, not adaptive | P2 |
| **No delegation visualization** | Can't see delegation chains | P2 |

---

## 2. Architecture: Intelligent Delegation Loop

```
User Input
    ↓
┌─────────────────────────────────────┐
│  COMPLEXITY SCORER (bin/complexity-score.sh)
│  - Analyzes task text
│  - Returns L1-L5 complexity score
│  - <2 seconds execution
└────────────────┬────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│  ROUTING ENGINE (AGENTS.md rules)
│  L1 (trivial)    → sisyphus-junior
│  L2 (simple)     → hephaestus
│  L3 (moderate)   → hephaestus + explore
│  L4 (complex)    → prometheus → hephaestus
│  L5 (architect)  → metis → prometheus → hephaestus
└────────────────┬────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│  DELEGATION DISPATCHER
│  - Validates prompt (6-section check)
│  - Injects context (3-tier)
│  - Checks shared results first
│  - Routes to optimal agent
└────────────────┬────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│  AGENT EXECUTION
│  - Runs task with validated prompt
│  - Records performance metrics
│  - Stores results in shared store
└────────────────┬────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│  AUTO-REVIEW CHAIN
│  - Quality gates (7 gates)
│  - Oracle review (architecture)
│  - Momus review (red-team)
│  - Auto-fix if review fails
└────────────────┬────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│  FEEDBACK LOOP
│  - Records success/failure
│  - Updates routing weights
│  - Learns from patterns
└─────────────────────────────────────┘
```

---

## 3. Implementation Waves

### Wave 1: Foundation (P0 — 3 tasks, parallel)

#### Task 1: Complexity Scorer
**File**: `bin/complexity-score.sh`
**What**: Analyzes task text, returns L1-L5 score
**How**: Keyword-based heuristic + line count + file count
**Output**: JSON `{level: 3, confidence: 0.8, reason: "multi-file change"}`

```bash
#!/usr/bin/env bash
# Complexity Scorer — L1-L5 task complexity estimation
# Usage: complexity-score.sh "task description"

TASK="$1"
SCORE=1

# Keyword analysis
echo "$TASK" | grep -qi "typo\|fix.*comma\|update.*version\|rename" && SCORE=1
echo "$TASK" | grep -qi "fix.*bug\|add.*feature\|create.*file" && SCORE=2
echo "$TASK" | grep -qi "refactor\|multi-file\|middleware\|auth" && SCORE=3
echo "$TASK" | grep -qi "architecture\|system.*design\|build.*from.*scratch" && SCORE=4
echo "$TASK" | grep -qi "rewrite\|migrate\|redesign.*entire" && SCORE=5

# File count analysis
FILE_COUNT=$(echo "$TASK" | grep -o "[0-9]\+ files" | grep -o "[0-9]\+" || echo "0")
[ "$FILE_COUNT" -gt 5 ] 2>/dev/null && [ "$SCORE" -lt 4 ] && SCORE=4
[ "$FILE_COUNT" -gt 10 ] 2>/dev/null && [ "$SCORE" -lt 5 ] && SCORE=5

echo "{\"level\": $SCORE, \"confidence\": 0.8, \"reason\": \"keyword-based\"}"
```

#### Task 2: Performance Ledger
**File**: `.sisyphus/agent-performance.json`
**What**: Track delegation outcomes per agent per task type
**Format**:
```json
{
  "hephaestus": {
    "implementation": {"success": 45, "failure": 3, "avg_tokens": 12000},
    "bugfix": {"success": 28, "failure": 1, "avg_tokens": 8000}
  },
  "explore": {
    "research": {"success": 67, "failure": 2, "avg_tokens": 5000}
  }
}
```

#### Task 3: Shared Result Store
**File**: `.sisyphus/results/`
**What**: Structured result storage for cross-agent sharing
**Format**: `.sisyphus/results/{task_id}.json`
```json
{
  "task_id": "task_001",
  "agent": "explore",
  "task_type": "research",
  "result_path": ".sisyphus/results/task_001_output.md",
  "timestamp": "2026-04-05T10:30:00Z",
  "tokens_used": 5000,
  "success": true
}
```

### Wave 2: Intelligence (P1 — 3 tasks, sequential)

#### Task 4: Prompt Validator
**File**: `bin/validate-prompt.sh`
**What**: Validates delegation prompts have all 6 sections
**Check**: TASK, EXPECTED OUTCOME, REQUIRED TOOLS, MUST DO, MUST NOT DO, CONTEXT
**Output**: Pass/Fail with missing sections listed

#### Task 5: Auto-Review Chain
**File**: Update AGENTS.md masterprompt
**What**: Auto-fire gates → Oracle → Momus after implementation
**Trigger**: After Hephaestus completes any implementation task

#### Task 6: Cost-Aware Routing
**File**: Update AGENTS.md routing rules
**What**: Route to cheapest effective agent based on task complexity
**Matrix**:
```
L1 → sisyphus-junior (minimax, low) — cheapest
L2 → hephaestus (minimax, high) — moderate
L3 → hephaestus + explore (parallel minimax) — moderate
L4 → prometheus (qwen) → hephaestus (minimax) — expensive
L5 → metis (qwen) → prometheus (qwen) → hephaestus (minimax) — most expensive
```

### Wave 3: Optimization (P2 — 2 tasks, parallel)

#### Task 7: Failure Rerouting
**File**: Update AGENTS.md fallback chains
**What**: Dynamic fallback based on failure pattern, not static model chain
**Logic**: If agent fails → try different agent → try different model → escalate

#### Task 8: Delegation Visualization
**File**: `.sisyphus/delegation-logs/`
**What**: Log every delegation with chain depth, agent, outcome
**Format**: `.sisyphus/delegation-logs/{session_id}.jsonl`

---

## 4. AGENTS.md Updates Required

### Add Section: Delegation Routing Matrix

```markdown
## 🔄 DELEGATION ROUTING MATRIX

### Complexity-Based Routing

| Level | Complexity | Agent(s) | Model | Max Concurrent |
|:------|:-----------|:---------|:------|:---------------|
| L1 | Trivial (typo, version bump) | sisyphus-junior | minimax-m2.5-free | 1 |
| L2 | Simple (single-file fix) | hephaestus | minimax-m2.5-free | 1 |
| L3 | Moderate (multi-file change) | hephaestus + explore | minimax-m2.5-free | 3 |
| L4 | Complex (new feature) | prometheus → hephaestus | qwen → minimax | 1+1 |
| L5 | Architect (system design) | metis → prometheus → hephaestus | qwen → qwen → minimax | 1+1+1 |

### Auto-Delegation Rules

- User says "fix typo" → L1 → sisyphus-junior
- User says "fix bug in X" → L2 → hephaestus
- User says "add feature X" → L3 → hephaestus + explore
- User says "build X system" → L4 → prometheus → hephaestus
- User says "redesign architecture" → L5 → metis → prometheus → hephaestus

### Auto-Review Chain

After ANY implementation task:
1. Run quality gates (typecheck, lint, format, test, secrets, placeholders, agent-calls)
2. If gates pass → Oracle review (architecture)
3. If Oracle approves → Momus review (red-team)
4. If Momus approves → Mark complete
5. If ANY step fails → Hephaestus fixes → Retry (max 2)
```

### Add Section: Performance Tracking

```markdown
## 📊 AGENT PERFORMANCE TRACKING

### Performance Ledger

Location: `.sisyphus/agent-performance.json`

After EVERY delegation, record:
- Agent name
- Task type
- Success/failure
- Tokens used
- Time taken
- Error message (if failed)

### Routing Weight Updates

Every 10 delegations:
- Calculate success rate per agent per task type
- Adjust routing preferences based on success rate
- Flag agents with <50% success rate for review
```

### Add Section: Shared Result Store

```markdown
## 🗂️ SHARED RESULT STORE

### Location: `.sisyphus/results/`

Before starting ANY task:
1. Check `.sisyphus/results/` for existing results
2. If found, use existing result instead of re-doing work
3. If not found, proceed with task and store result

### Result Format

```json
{
  "task_id": "task_001",
  "agent": "explore",
  "task_type": "research",
  "result_path": ".sisyphus/results/task_001_output.md",
  "timestamp": "2026-04-05T10:30:00Z",
  "tokens_used": 5000,
  "success": true
}
```
```

---

## 5. Success Metrics

| Metric | Before | After | Target |
|:-------|:-------|:------|:-------|
| Delegation success rate | ~70% | ~90% | +20% |
| Redundant work | High | Low | -50% |
| Token cost per task | Variable | Optimized | -25% |
| Manual review triggers | 100% | 0% | Auto |
| Task completion time | Variable | Optimized | -30% |

---

## 6. Implementation Priority

| Priority | Task | Effort | Impact | Dependencies |
|:---------|:-----|:-------|:-------|:-------------|
| **P0** | Complexity scorer | 30 min | High | None |
| **P0** | Performance ledger | 15 min | High | None |
| **P0** | Shared result store | 15 min | High | None |
| **P1** | Prompt validator | 20 min | Medium | P0 tasks |
| **P1** | Auto-review chain | 10 min | High | P0 tasks |
| **P1** | Cost-aware routing | 10 min | Medium | P0 tasks |
| **P2** | Failure rerouting | 30 min | Medium | P1 tasks |
| **P2** | Delegation visualization | 20 min | Low | P0 tasks |

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|:-----|:-----------|:-------|:-----------|
| Over-engineering | High | Medium | Start with P0 only, measure impact |
| Token budget increase | Medium | High | Keep performance tracking lightweight |
| Agent behavior changes | Low | Medium | Test with existing tasks first |
| Backward compatibility | Low | High | Ensure existing delegations continue working |

---

## 8. Verification Checklist

After all changes:

- [ ] `bin/complexity-score.sh` exists and returns L1-L5 scores
- [ ] `.sisyphus/agent-performance.json` exists and tracks outcomes
- [ ] `.sisyphus/results/` directory exists with result format
- [ ] `bin/validate-prompt.sh` validates 6-section prompts
- [ ] AGENTS.md has delegation routing matrix
- [ ] AGENTS.md has auto-review chain
- [ ] AGENTS.md has performance tracking section
- [ ] AGENTS.md has shared result store section
- [ ] 3 real tasks tested with auto-delegation
- [ ] Token cost per task reduced by 25%+
