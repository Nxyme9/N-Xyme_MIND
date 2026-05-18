# Step 1: Phase Detection and Routing

## MANDATORY EXECUTION RULES:
- Detect user intent from request
- Route to appropriate starting phase
- Chain phases in sequence
- Handle mode selection (Auto/Manual/Custom)

## PHASE DETECTION:

| Keywords | Starting Phase |
|----------|----------------|
| brainstorm, ideas, explore | Phase 2: Analysis (brainstorm) |
| market, competitors | Phase 2: Analysis (market research) |
| product, MVP, vision | Phase 3: Planning (product brief) |
| requirements, PRD | Phase 3: Planning (PRD) |
| architecture, design | Phase 4: Solutioning (architecture) |
| sprint, plan, tasks | Phase 4: Solutioning (sprint plan) |
| implement, build, code | Phase 5: Bridge → Phase 6: Execute |
| review, validate | Phase 7: Review |
| unclear | Ask user |

## EXECUTION:

### 1. Detect Mode
```
If Auto: Run all phases from detected starting point
If Manual: Show phase menu, wait for selection
If Custom: Show checkbox list, wait for selection
```

### 2. Execute Phase Chain with Diminishing Returns Detection
```
from src.diminishing_returns import DiminishingReturnsDetector, IterationScore

detector = DiminishingReturnsDetector(window=3, threshold=0.05)

For each phase in sequence:
    1. Load phase workflow
    2. Execute phase
    3. Score quality (0-1 scale)
    4. Record to detector: detector.record(IterationScore(...))
    5. Check: if detector.should_transition():
        - Log "Diminishing returns detected at phase {N}"
        - Skip remaining research/planning phases
        - Jump directly to BUILD phase
    6. Otherwise: continue to next phase
    7. Run bmad-memory (recall for next phase)
    8. Run bmad-resilience (review after phase)
```

**Quality Scoring Per Phase:**
- Analysis: coverage % of relevant topics
- Planning: completeness of requirements
- Solutioning: architecture decisions made
- Execution: tasks completed / total tasks
- Review: issues found / issues fixed

### 3. Handle Failures
```
If phase fails:
    1. Run bmad-resilience (recovery mode)
    2. If recovered: retry phase
    3. If not recovered: halt and notify user
```

### 4. Complete Pipeline
```
After final phase:
    1. Run bmad-memory (consolidate mode)
    2. Present summary to user
    3. Offer to start new pipeline
```
