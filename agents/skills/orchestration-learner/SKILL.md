---
name: orchestration-learner
description: "Orchestration Learner — skill any agent can load to improve its orchestration decisions using training data, success-rate bandits, failure prediction, prompt optimization, task decomposition, and escalation detection."
---

# Orchestration Learner — SKILL

**Purpose:** A protocol any agent can load to improve its orchestration and delegation decisions by learning from historical training data.

**Loading agent:** Catalyst, Sisyphus, Atlas, or any agent that makes delegation/orchestration decisions.

**Prerequisites:**
- Training data pipeline running (`services/training/pipeline.py`)
- Training data at `data/training/examples.jsonl`
- Access to `data/training/curriculum.json`, `data/training/metrics.json`
- Puzzle generator at `services/training/puzzle_generator.py`

---

## ══╡ SECTION 1: CORE ARCHITECTURE ╞════════════════════════════════════

```
                     ┌──────────────────────────────────────┐
                     │      ORCHESTRATION LEARNER            │
                     │                                      │
                     │  ┌─────────┐  ┌──────────┐  ┌─────┐ │
                     │  │ QUERY   │  │ BANDIT   │  │FAIL │ │
                     │  │ TRAINING│  │ SELECTOR│  │PRED │ │
                     │  │  DATA   │  │          │  │     │ │
                     │  └────┬────┘  └────┬─────┘  └──┬──┘ │
                     │       │            │           │     │
                     │       ▼            ▼           ▼     │
                     │  ┌──────────────────────────────┐    │
                     │  │     DECISION ENGINE           │    │
                     │  │  • Best agent for this task   │    │
                     │  │  • Best tools for this task   │    │
                     │  │  • Best prompt for this task  │    │
                     │  │  • Escalate or keep trying    │    │
                     │  └──────────────┬───────────────┘    │
                     │                 │                     │
                     │                 ▼                     │
                     │  ┌──────────────────────────────┐    │
                     │  │     OUTPUT                    │    │
                     │  │  • Delegation recommendation  │    │
                     │  │  • Prompt template suggestion │    │
                     │  │  • Escalation flag            │    │
                     │  │  • Confidence score            │    │
                     │  └──────────────────────────────┘    │
                     └──────────────────────────────────────┘
```

This skill implements 5 core capabilities:

| # | Capability | Algorithm | Reference |
|---|-----------|-----------|-----------|
| 1 | **Contextual Bandit** — choose delegation target | Upper Confidence Bound (UCB) | Sutton & Barto Ch.2 |
| 2 | **Failure Prediction** — predict tool failure | Similarity-weighted historical rate | Mnih et al. 2015 |
| 3 | **Prompt Optimization** — best prompt structure | Template matching + A/B results | Wei et al. 2022 (CoT) |
| 4 | **Task Decomposition** — break into subtasks | Recursive split by tool boundary | Chain-of-Thought |
| 5 | **Escalation Detection** — stop vs retry | Diminishing returns threshold | Adaptive Router (Sec 5) |

---

## ══╡ SECTION 2: QUERY TRAINING DATA ╞════════════════════════════════

### Data Sources

The learner reads from four sources:

| Source | Path | Format | Purpose |
|--------|------|--------|---------|
| Training examples | `data/training/examples.jsonl` | JSONL | Agent-task-outcome tuples with rewards |
| Curriculum | `data/training/curriculum.json` | JSON | Priority-ordered practice tasks |
| Metrics | `data/training/metrics.json` | JSON | Aggregate success rates per agent |
| Lessons learned | `data/training/lessons-learned.jsonl` | JSONL | Actionable insights from failure clusters |

### Query Protocol

To query training data for decision support:

```
1. Check if data/training/examples.jsonl exists
   → If NO: return "no training data — use default policies"
   → If YES but empty: return "training data empty — use default policies"

2. Filter by agent name (current agent)
   → Count records: total, successes, failures
   → Compute success_rate = successes / max(total, 1)

3. Filter by tool name (for tool-specific guidance)
   → Count tool-specific successes/failures
   → Compute tool_success_rate = tool_successes / max(tool_total, 1)

4. Filter by task type (for task-specific guidance)
   → If task keywords match known patterns, get pattern-specific rate

5. Return structured summary
```

### Example Query

```
Query: "What is Hephaestus's success rate with file_write?"

Result:
  agent:            Hephaestus
  tool:             file_write
  total_calls:      47
  successes:        42
  failures:         5
  success_rate:     0.894
  common_errors:    ["FileNotFoundError", "permission denied"]
  trend:            improving (95% last 7 days)
  recommendation:   "High confidence — proceed with file_write"
```

---

## ══╡ SECTION 3: CONTEXTUAL BANDIT — AGENT SELECTION ╞═══════════════

### Problem

Given a task, which agent should I delegate to?

### Algorithm: UCB1 (Upper Confidence Bound)

Adapted from Sutton & Barto "Reinforcement Learning" (Ch. 2, 2018):

```
For each candidate agent a:
  Q(a) = success_rate(a)  — historical success rate
  N(a) = total_attempts(a)
  N_total = sum(N(a) for all agents)
  
  Exploration bonus = sqrt(2 * ln(N_total) / N(a))
  
  Score(a) = Q(a) + exploration_bonus

Select agent = argmax Score(a)
```

### When to Use

- You have multiple agents that could handle the task
- You have historical data on their success rates
- You want to balance exploration (try new agents) vs exploitation (best known)

### Protocol

```
PHASE 1: QUERY
  Read data/training/metrics.json → get agent_summary
  For each candidate agent:
    total = agent_summary[agent].total_tasks
    success_rate = agent_summary[agent].overall_success_rate

PHASE 2: SCORE
  For each candidate:
    if total == 0:
      score = 1.0 + high_exploration_bonus  (never tried → explore)
    else:
      exploration_bonus = sqrt(2 * ln(all_attempts) / total)
      score = success_rate + exploration_bonus

PHASE 3: SELECT
  Sort by desc score
  Pick top agent
  If score < 0.3: flag "low confidence — consider escalation"

PHASE 4: RECORD
  After task completes:
    Read the outcome from training data
    The bandit updates automatically on next query
```

### Example

```
Task: "Implement a new MCP tool"
Candidates: Hephaestus, Sisyphus Junior, Atlas

Data:
  Hephaestus:    total=200, success_rate=0.85  → score=0.85 + 0.12 = 0.97
  Sisyphus Jr:   total=80,  success_rate=0.70  → score=0.70 + 0.17 = 0.87
  Atlas:         total=150, success_rate=0.65  → score=0.65 + 0.14 = 0.79

Select: Hephaestus (score=0.97)
```

---

## ══╡ SECTION 4: FAILURE PREDICTION ╞════════════════════════════════

### Problem

Given the current task and state, which tools/approaches are likely to fail?

### Algorithm: Similarity-Weighted Historical Failure Rate

References experience replay (Mnih et al. 2015) — learn from past failures:

```
For each candidate approach (tool + parameter pattern):
  1. Find similar past attempts:
     - Same tool
     - Similar parameters (by key overlap)
     - Same agent
     - Similar error context
  
  2. Compute failure_rate = failures / max(total, 1)
  
  3. If failure_rate > 0.3:
     Flag as "RISKY — past failures: {count}"
     
  4. If failure_rate > 0.5:
     Flag as "HIGH RISK — consider alternative approach"
     
  5. If failure_rate > 0.7:
     Flag as "BLOCKED — do not attempt without user approval"
```

### Failure Pattern Matching

Match current task against known failure clusters:

```
For each failure cluster in lessons-learned.jsonl:
  agent_match = cluster.agent == current_agent
  tool_match = cluster.tool == proposed_tool
  
  if agent_match AND tool_match:
    error_overlap = similarity(cluster.error_pattern, current_error_context)
    if error_overlap > 0.6:
      "WARNING: Similar to past failure #{cluster.count}
       Error: {cluster.example_error}
       Consider: {suggested_drill}"
```

### Escalation Prediction

Before delegating, check if this task type has a history of escalating:

```
Query: "Has {agent} escalated task type '{task_type}' before?"

1. Read examples.jsonl
2. Filter: agent == target AND outcome == "failure" 
   AND reward == -1.0 (escalation)
3. Count escalations for this task pattern
4. If > 3: "This task type has required escalation {N}x before.
            Pre-escalate to next level."
```

---

## ══╡ SECTION 5: PROMPT OPTIMIZATION ╞════════════════════════════════

### Problem

Given a task, what prompt structure produces the best results for this agent?

### Algorithm: Template Matching + A/B History

Inspired by Chain-of-Thought prompting (Wei et al. 2022):

```
For each known prompt template:
  template_type = classify_task(task)
  
  Template types:
  ┌──────────────────┬──────────────────────────┬──────────────────┐
  │ Task Type        │ Best Prompt Structure    │ Example          │
  ├──────────────────┼──────────────────────────┼──────────────────┤
  │ Code generation  │ Spec → Examples → CORS   │ Hephaestus       │
  │ Debugging        │ Symptom → Hypothesis →   │ Scalpel          │
  │                  │ Test → Fix               │                  │
  │ Research         │ Question → Sub-questions  │ Librarian        │
  │                  │ → Synthesize              │                  │
  │ Decision         │ Options → Criteria →     │ Oracle           │
  │                  │ Evaluate → Recommend      │                  │
  │ Review           │ Artifact → Lenses →      │ Momus            │
  │                  │ Findings → Severity       │                  │
  │ Therapy          │ State → Validate →       │ Kairos           │
  │                  │ Explore → Plan            │                  │
  │ Orchestration    │ Goal → Subtasks →        │ Catalyst         │
  │                  │ Dependencies → Route      │                  │
  └──────────────────┴──────────────────────────┴──────────────────┘
```

### Prompt Evaluation

Before using a template, check if it has been A/B tested:

```
Query: "Has prompt template '{template}' for agent '{agent}' 
        been A/B tested?"

Check: search_memory("prompt:ab-test:{agent}:*")
If found:
  Use the winning variant
  If no A/B test: use best template type from table above
```

### Dynamic Prompt Generation

For high-value tasks, construct a prompt that includes failure context:

```
SYSTEM: You are {agent}. Your task is {task}.

PAST FAILURES TO AVOID:
- {failure_1} — {solution_1}
- {failure_2} — {solution_2}

KNOWN SUCCESSFUL APPROACHES:
- {approach_1} — worked {N}x before
- {approach_2} — worked {M}x before

TOOLS AVAILABLE:
{tools_list}

PROCEED WITH:
{suggested_approach}
```

---

## ══╡ SECTION 6: TASK DECOMPOSITION ╞════════════════════════════════

### Problem

How do I break a complex problem into delegable subtasks?

### Algorithm: Recursive Split by Tool Boundary

Inspired by Chain-of-Thought decomposition (Wei et al. 2022):

```
def decompose(task):
  1. Classify task type
  2. For each top-level step required:
     a. What tool/agent is needed for this step?
     b. Is this step simple enough to delegate as-is?
        → YES: create subtask "agent → action"
        → NO: recursively decompose this step
  3. Check dependencies between subtasks
  4. Order subtasks: dependencies first, independent in parallel
  5. Return: [{agent, action, depends_on}, ...]
```

### Decomposition Patterns

| Task Pattern | Decomposition | Delegation Targets |
|-------------|---------------|-------------------|
| "Implement feature X" | Design → Build → Test → Review | Oracle → Hephaestus → Hephaestus → Momus |
| "Fix bug Y" | Diagnose → Fix → Verify | Scalpel → Hephaestus → Explore |
| "Research topic Z" | Search → Read → Synthesize | Librarian → Explore → Hermes |
| "Improve memory recall" | Audit → Propose → Implement → Verify | Momus → Oracle → Hephaestus → Explore |
| "Multi-step workflow" | Plan → Parallel work → Integrate → Verify | Prometheus → multiple → Hephaestus → Momus |

### Learning from Past Decompositions

Check training data for how similar tasks were decomposed:

```
Query: "How was task '{similar_task}' decomposed in the past?"

1. Search for tasks with similar keywords in examples.jsonl
2. Group by approach_used patterns
3. Find the most common decomposition pattern for that task type
4. Use that pattern, with adjustments for the specific context
```

---

## ══╡ SECTION 7: ESCALATION DETECTION ╞══════════════════════════════

### Problem

When should I escalate to a higher-level agent vs keep trying?

### Algorithm: Diminishing Returns Threshold

```
For the current task and current approach:
  attempts_so_far = count of similar past attempts
  success_rate_for_approach = Q(approach)
  
  if attempts_so_far == 0:
    → GO (first attempt, nothing to compare)
  
  elif attempts_so_far == 1:
    → GO (one failure is not a pattern)
  
  elif attempts_so_far >= 2:
    if success_rate_for_approach < 0.3:
      → ESCALATE (approach has >70% failure rate)
    elif success_rate_for_approach < 0.5:
      → RECOMMEND ESCALATION (approach is unreliable)
      But allow one more attempt with different method
    else:
      → GO (approach still viable)

  if attempts_so_far >= 5:
    if max(consecutive_successes) == 0:
      → STOP + escalation report
      "This task has failed {N}x across {M} approaches."
```

### Escalation Recommendation Format

When the learner recommends escalation, output:

```
═══ ORCHESTRATION LEARNER — ESCALATION RECOMMENDATION ═══

TASK: {task}
CURRENT AGENT: {agent}
RECOMMENDED TARGET: {target_agent}

REASON:
  {N} previous attempts with this approach
  Success rate: {rate:.0%}
  {explanation of why escalation is warranted}

ALTERNATIVE APPROACHES:
  - {alt_1} (success rate: {rate_1:.0%})
  - {alt_2} (success rate: {rate_2:.0%})

CONFIDENCE: {score}%
═══
```

---

## ══╡ SECTION 8: FULL PROTOCOL ╞════════════════════════════════════

When you load this skill, follow these phases:

### PHASE 1: LOAD & DIAGNOSE

```
1. Read training data status
   If data/training/examples.jsonl exists:
     Count records, check freshness (last modified)
     Read data/training/metrics.json for agent summary
     Read data/training/curriculum.json for practice tasks
   Else:
     Note: "No training data available — using default policies"

2. Identify current agent's failure patterns
   Query: "agent={self}" from examples.jsonl
   Top 3 failure patterns by count
   Top 3 tools with lowest success rate
```

### PHASE 2: ANALYSE TASK

```
3. Classify the incoming task:
   - Code? Research? Review? Orchestration? Therapy?
   - Single step or multi-step?
   - What tools are needed?
   - Has this task type been seen before?

4. Query training data for similar tasks:
   - What agent handled it best?
   - What approach worked?
   - What failed?
   - What was the reward?
```

### PHASE 3: DECIDE

```
5. Contextual Bandit — choose delegation target (Section 3)
   If multiple agents can handle → UCB1 scoring

6. Failure Prediction — flag risks (Section 4)
   If current approach has >30% failure rate → flag
   If >50% → recommend different approach
   If >70% → block

7. Prompt Optimization — choose prompt structure (Section 5)
   Match task type to best template
   Include failure context if available

8. Escalation Detection — GO/ESCALATE/STOP (Section 7)
   Check diminishing returns
   If escalate → recommend target and reason
```

### PHASE 4: OUTPUT

```
9. Produce decision:
   ┌────────────────────────────────────────────┐
   │ RECOMMENDATION                              │
   │                                             │
   │ Task:  {task}                               │
   │ Agent: {recommended_agent}                  │
   │ Approach: {prompt_template}                  │
   │ Risk:   {low/medium/high}                   │
   │ Escalate: {yes/no → target}                 │
   │ Confidence: {score}                         │
   └────────────────────────────────────────────┘

10. Record decision context for future learning
```

### PHASE 5: POST-TASK LEARNING

```
11. After task completes:
    - Read the outcome from logs
    - The training pipeline (pipeline.py) will process it
    - On next load, updated stats are available
```

---

## ══╡ SECTION 9: EDGE CASES ╞═══════════════════════════════════════

### Edge Case 1: No Training Data

```
If data/training/examples.jsonl does not exist:
  → Use default policies from adaptive-router
  → Skip all bandit/failure calculations
  → Return: "No training data — using default routing"
```

### Edge Case 2: Single Data Point

```
If agent has only 1-2 records:
  → Exploration bonus dominates (UCB)
  → Failure prediction is unreliable (N < 5)
  → Return: "Insufficient data — recommend exploration"
  → Do NOT make escalation decisions based on <5 records
```

### Edge Case 3: All Agents Equal

```
If all candidate agents have similar success rates:
  → Use secondary metrics: latency, cost, token usage
  → If still equal: round-robin
```

### Edge Case 4: Negative Trend

```
If agent's success rate is declining:
  weekly_rate < daily_rate < monthly_rate (all declining):
  → Flag agent for review
  → Reduce delegation to this agent
  → Increase verification gates
```

### Edge Case 5: Task Type Unknown

```
If task doesn't match any known template:
  → Use generic "Goal → Plan → Execute → Verify" template
  → Flag for inclusion in future training
```

---

## ══╡ SECTION 10: REFERENCES ╞═══════════════════════════════════════

- Training pipeline: `services/training/pipeline.py`
- Puzzle generator: `services/training/puzzle_generator.py`
- Training data: `data/training/examples.jsonl`
- Agent improvement protocol: `agents/skills/orchestration-learner/agent_improvement.md`
- Adaptive router: `agents/skills/adaptive-router/SKILL.md`
- Confidence gate: `agents/skills/confidence-gate/SKILL.md`
- Learning bridge: `services/megatool-mcp/learning_bridge.py`
- Sutton & Barto "Reinforcement Learning" (2nd ed., 2018) — bandit algorithms
- DeepMind "Reward is Enough" (Silver et al., 2021) — reward signals
- Mnih et al. "Human-level control through DRL" (Nature, 2015) — experience replay
- Wei et al. "Chain-of-Thought Prompting" (NeurIPS, 2022) — task decomposition
- Bengio et al. "Curriculum Learning" (ICML, 2009) — progressive difficulty
