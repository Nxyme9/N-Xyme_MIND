# Agent Improvement Protocol

**Self-improvement cycle for N-Xyme MIND agents.**

Every agent can improve across sessions. This protocol defines a 5-session
improvement loop that any core agent or skill can execute when the
Orchestration Learner flags them for improvement.

---

## ══╡ OVERVIEW ╞══════════════════════════════════════════════════════

```
SESSION 1: LOAD TRAINING DATA
  │  Read examples, metrics, lessons learned for this agent
  │  Establish baseline success rate
  ▼
SESSION 2: IDENTIFY TOP 3 FAILURE PATTERNS
  │  Analyse clusters, find root causes
  │  Prioritise by frequency × impact
  ▼
SESSION 3: PRACTICE ON PUZZLES
  │  Solve puzzles targeting those failure patterns
  │  Safe environment — no real consequences
  ▼
SESSION 4: APPLY TO REAL TASKS
  │  Use corrected approaches on real work
  │  Track outcomes vs baseline
  ▼
SESSION 5: VERIFY IMPROVEMENT
  │  Compare success rate before/after
  │  If <10% improvement → try different approach
  │  If >20% improvement → store as "mastered"
  │  If no data yet → schedule re-evaluation
```

**Total time:** 5 sessions (can be consecutive or spread out)

**Prerequisites per session:**
- Training pipeline must have run at least once (`services/training/pipeline.py`)
- Puzzle generator available (`services/training/puzzle_generator.py`)
- Orchestration Learner skill loaded (`agents/skills/orchestration-learner/SKILL.md`)

---

## ══╡ SESSION 1: LOAD TRAINING DATA ╞════════════════════════════════

### Goal

Establish a baseline understanding of this agent's performance data.

### Protocol

```
PHASE 1: READ TRAINING DATA
  Load data/training/examples.jsonl
  Filter: agent == self.name
  Count records: total, successes, failures
  Compute baseline_success_rate = successes / max(total, 1)

PHASE 2: READ METRICS
  Load data/training/metrics.json
  Extract agent_summary for self.name:
    - overall_success_rate
    - daily_rate
    - weekly_rate
    - total_tasks

PHASE 3: READ LESSONS
  Load data/training/lessons-learned.jsonl
  Filter: agent == self.name
  Collect all lessons about this agent's failures

PHASE 4: READ CURRICULUM
  Load data/training/curriculum.json
  Filter: agent == self.name
  Get practice recommendations

PHASE 5: BASELINE REPORT
```

### Baseline Report Template

```
═══ AGENT IMPROVEMENT — BASELINE REPORT ═══════════════════════════

AGENT: {agent_name}
SESSION: 1/5 — LOAD DATA

TRAINING DATA STATUS:
  Total records:    {N}
  Successes:        {S}
  Failures:         {F}
  Baseline rate:    {rate:.1%}

METRICS:
  Daily rate:       {daily:.1%} ({daily_total} tasks)
  Weekly rate:      {weekly:.1%} ({weekly_total} tasks)
  Overall rate:     {overall:.1%} ({overall_total} tasks)

LESSONS FOR THIS AGENT:
  {lesson_1}
  {lesson_2}
  ...

CURRICULUM ITEMS:
  {curriculum_1}
  {curriculum_2}
  ...

DATA QUALITY:
  Records sufficient for analysis? {yes/no}
  (Need ≥ 10 records for reliable patterns)

═══════════════════════════════════════════════════════════════════
```

### Edge Cases

| Situation | Action |
|-----------|--------|
| No training data exists | Report "no data — run training pipeline first" |
| < 10 records | Report "insufficient data — continue collecting" |
| No failures | Report "no failures found — check for ceiling effect" |
| All failures | Report "critical — all {N} attempts failed" |

---

## ══╡ SESSION 2: IDENTIFY TOP 3 FAILURE PATTERNS ╞════════════════

### Goal

From the training data, identify the three most impactful failure patterns to fix.

### Protocol

```
PHASE 1: CLUSTER FAILURES
  From training data, group failures by:
  a) Tool being used
  b) Error message (normalised)
  c) Task type
  d) Parameter pattern

  For each cluster:
    count = number of failures
    impact = count * (1 - current_success_rate_for_tool)
    Store: {cluster_key, count, impact, example}

PHASE 2: RANK BY IMPACT
  Sort clusters by impact descending
  Top 3 = highest impact patterns

PHASE 3: ROOT CAUSE ANALYSIS
  For each of top 3:
    Read example errors
    Identify what went wrong:
      - Wrong tool? → tool selection error
      - Wrong args? → parameter error
      - Wrong order? → sequencing error
      - Missing context? → context error
      - Timeout? → capacity error

PHASE 4: IDENTIFY CORRECTED APPROACHES
  Search for the same task type in successes:
    What did the successful attempts do differently?
    If no successful attempts exist:
      Look at similar tasks (different tool, same pattern)
      Look at other agents handling same tool

PHASE 5: PATTERN REPORT
```

### Pattern Report Template

```
═══ AGENT IMPROVEMENT — PATTERN REPORT ════════════════════════════

AGENT: {agent_name}
SESSION: 2/5 — IDENTIFY PATTERNS

#1 FAILURE PATTERN (impact: {impact:.1f})
  Tool:         {tool}
  Error:        {error}
  Count:        {count}
  Success rate: {rate:.0%} with this tool
  Root cause:   {root_cause}
  Corrected approach:
    Instead of: {wrong_approach}
    Do:         {corrected_approach}
  Practice puzzle type: {puzzle_type}

#2 FAILURE PATTERN (impact: {impact:.1f})
  ...

#3 FAILURE PATTERN (impact: {impact:.1f})
  ...

═══════════════════════════════════════════════════════════════════
```

### Edge Cases

| Situation | Action |
|-----------|--------|
| < 3 failure clusters | Target all available clusters (even 1) |
| All clusters are the same tool | Target that tool with 3 different aspects |
| No clear root cause | Flag as "needs investigation — run puzzle # for exploration" |
| All successes, no failures | Identify ceiling effect — try harder tasks |

---

## ══╡ SESSION 3: PRACTICE ON PUZZLES ╞════════════════════════════

### Goal

In a safe environment, practice the corrected approaches for the top 3 failure patterns.

### Protocol

```
PHASE 1: GENERATE TARGETED PUZZLES
  For each failure pattern from Session 2:
    puzzle_type = derived from pattern (TOOL_FAILURE, DELEGATION_BROKEN, etc.)
    difficulty = EASY for first attempt
    count = 2-3 per pattern

  Run: python3 puzzle_generator.py --type {puzzle_type} \
       --difficulty EASY --agent {self.name} --count 3

PHASE 2: SOLVE EACH PUZZLE
  For each puzzle:
    Read puzzle description
    Identify which failure pattern this targets
    Apply the corrected approach from Session 2
    Solve the puzzle
    Record: solved? steps_taken? time?
    Store result in data/training/puzzle_results.jsonl

PHASE 3: ESCALATE DIFFICULTY
  For patterns solved on EASY:
    Generate MEDIUM difficulty of same type
    Solve MEDIUM puzzles
  For patterns failed on EASY:
    Re-read the corrected approach
    Try again on EASY
    If fail twice: flag "pattern not understood — need human intervention"

PHASE 4: PRACTICE REPORT
```

### Practice Report Template

```
═══ AGENT IMPROVEMENT — PRACTICE REPORT ═══════════════════════════

AGENT: {agent_name}
SESSION: 3/5 — PRACTICE

PATTERN #1: {error_pattern}
  EASY puzzles:   {solved_easy}/{total_easy}
  MEDIUM puzzles: {solved_medium}/{total_medium}
  Status: {mastered / needs work / escalated}

PATTERN #2: {error_pattern}
  ...

PATTERN #3: {error_pattern}
  ...

OVERALL:
  Puzzles solved: {total_solved}/{total_attempts}
  Improvement from practice: {improvement:.1%}
  Ready for real tasks? {yes/no}

═══════════════════════════════════════════════════════════════════
```

### Edge Cases

| Situation | Action |
|-----------|--------|
| Puzzle generator has no data | Use built-in templates (always available) |
| All puzzles solved easily | Skip to Session 4, mark pattern as "likely mastered" |
| All puzzles failed | Escalate to human — pattern needs redesign, not practice |
| Puzzle times out | Break into smaller steps, retry |

---

## ══╡ SESSION 4: APPLY TO REAL TASKS ╞════════════════════════════

### Goal

Transfer the corrected approaches from practice to real tasks.

### Protocol

```
PHASE 1: WATCH FOR TARGET TASKS
  Monitor incoming tasks that match top 3 failure patterns:
    - Same tool
    - Same task type  
    - Same error context
  
  When a matching task arrives:
    Flag it as "improvement target — using corrected approach"

PHASE 2: APPLY CORRECTED APPROACH
  Before acting, inject context from Sessions 2-3:
    "Note: previous attempts at {pattern} failed because {root_cause}.
     Using corrected approach: {corrected_approach}."

PHASE 3: RECORD OUTCOMES
  For each targeted task:
    Record: task, approach_used, outcome, was_corrected
    The training pipeline will pick this up automatically

PHASE 4: TRACK PROGRESS
  After 5-10 targeted tasks:
    success_count = tasks using corrected approach that succeeded
    total_count = all targeted tasks
    current_rate = success_count / max(total_count, 1)
    vs baseline_rate (from Session 1)
```

### Application Log Template

```
═══ AGENT IMPROVEMENT — APPLICATION LOG ═══════════════════════════

AGENT: {agent_name}
SESSION: 4/5 — APPLY

TARGETED TASKS ATTEMPTED: {N}

PATTERN #1: {error_pattern}
  Attempts:    {attempts}
  Successes:   {successes}
  Rate:        {rate:.0%}
  vs baseline: {baseline:.0%} → {rate:.0%}

PATTERN #2: ...
PATTERN #3: ...

NOTES:
  - {observation_1}
  - {observation_2}

═══════════════════════════════════════════════════════════════════
```

### Edge Cases

| Situation | Action |
|-----------|--------|
| No matching tasks arrive | Run puzzle generator with MEDIUM/HARD difficulty as proxy |
| < 5 tasks in reasonable time | Record what's available, note "limited data" |
| Corrected approach also fails | Revert to Session 2 — root cause analysis was wrong |
| Tasks succeed but slower | Accept slower if more correct — speed improves with practice |

---

## ══╡ SESSION 5: VERIFY IMPROVEMENT ╞════════════════════════════

### Goal

Compare before/after success rates and decide next steps.

### Protocol

```
PHASE 1: COMPARE METRICS
  Before (Session 1): baseline_success_rate
  After (Session 4): current_success_rate
  Improvement = current_rate - baseline_rate

PHASE 2: DECISION TREE

  if improvement >= 20%:
    → "PATTERN MASTERED"
    → Store in data/training/mastered_patterns.jsonl
    → Add to positive_replays buffer
    → Move to next failure pattern (if any)

  elif improvement >= 10%:
    → "PATTERN IMPROVING"
    → Continue practice on MEDIUM/HARD puzzles
    → Schedule Session 3 again with harder puzzles
    → Re-check after 10 more real tasks

  elif improvement >= 0%:
    → "PATTERN STALLED"
    → Root cause analysis may be wrong
    → Re-run Session 2 with fresh perspective
    → Try different corrected approach

  else (improvement < 0%):
    → "PATTERN REGRESSING"
    → STOP using corrected approach
    → Revert to previous approach
    → Escalate for human review
    → Document: "corrected approach made things worse"

PHASE 3: UPDATE MASTERED PATTERNS
  For each mastered pattern, store:
    {
      "agent": "{agent}",
      "pattern": "{error_pattern}",
      "tool": "{tool}",
      "old_success_rate": baseline,
      "new_success_rate": current,
      "improvement": improvement,
      "corrected_approach": "{approach}",
      "mastered_date": "{date}",
      "sessions_required": 5
    }

PHASE 4: GENERATE IMPROVEMENT REPORT
```

### Final Report Template

```
═══ AGENT IMPROVEMENT — FINAL REPORT ═════════════════════════════

AGENT: {agent_name}
SESSION: 5/5 — VERIFY

IMPROVEMENT SUMMARY:
                    BEFORE     AFTER    CHANGE
  Pattern #1:       {b1:.0%}   {a1:.0%}  {d1:+.0%}  {verdict_1}
  Pattern #2:       {b2:.0%}   {a2:.0%}  {d2:+.0%}  {verdict_2}
  Pattern #3:       {b3:.0%}   {a3:.0%}  {d3:+.0%}  {verdict_3}

OVERALL:
  Baseline rate:    {baseline:.0%}  (Session 1)
  Current rate:     {current:.0%}   (Session 5)
  Net change:       {change:+.0%}
  Total tasks:      {total_tasks}

MASTERED PATTERNS:
  - {pattern_1} ({date})
  - {pattern_2} ({date})

NEXT STEPS:
  {next_steps}

═══════════════════════════════════════════════════════════════════
```

### Edge Cases

| Situation | Action |
|-----------|--------|
| Not enough data after (total < 10) | Mark "insufficient — re-evaluate after 10 more tasks" |
| All patterns mastered | Run full improvement cycle on next 3 failure patterns |
| All patterns regressed | Full system review — agent may need prompt redesign |
| Data pipeline hasn't ingested outcomes | Force-run `python3 services/training/pipeline.py --once` |

---

## ══╡ PROTOCOL ACTIVATION ╞════════════════════════════════════════

### When to Run

The improvement protocol should be triggered when:

1. **Orchestration Learner flags an agent** (success rate < 50% or repeating failures detected)
2. **Curriculum recommends practice** (from `data/training/curriculum.json`)
3. **Scheduled maintenance** (run weekly for agents with >100 records)
4. **Manual request** ("Run improvement cycle for {agent}")

### How to Run

```python
# 1. Load the orchestration learner skill
skill("orchestration-learner")

# 2. Load this protocol
# (this document — follow the 5 sessions)

# 3. Execute sessions in order:
# Session 1: read_data
# Session 2: find_patterns
# Session 3: practice
# Session 4: apply
# Session 5: verify

# Between sessions, the agent continues normal work.
# Sessions can be spread across multiple user interactions.
```

### Success Criteria

The protocol is complete when:

- [ ] Session 1: Baseline report generated with ≥10 records
- [ ] Session 2: Top 3 failure patterns identified with root causes
- [ ] Session 3: Practice puzzles solved at EASY difficulty minimum
- [ ] Session 4: Corrected approaches applied to ≥5 real tasks
- [ ] Session 5: Before/after comparison completed
- [ ] Mastered patterns stored in `data/training/mastered_patterns.jsonl`
- [ ] Memory entry written: `memory:improvement:{agent}:{date}`

---

## ══╡ REFERENCES ╞══════════════════════════════════════════════════

- Orchestration Learner skill: `agents/skills/orchestration-learner/SKILL.md`
- Training pipeline: `services/training/pipeline.py`
- Puzzle generator: `services/training/puzzle_generator.py`
- Training data: `data/training/examples.jsonl`
- Learning bridge: `services/megatool-mcp/learning_bridge.py`
- Adaptive Router: `agents/skills/adaptive-router/SKILL.md`
- Reinforcement Learning (Sutton & Barto, 2018) — bandit algorithms
- Experience Replay (Mnih et al., 2015) — learning from past failures
- Curriculum Learning (Bengio et al., 2009) — progressive difficulty
