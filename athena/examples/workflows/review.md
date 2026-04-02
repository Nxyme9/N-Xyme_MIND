---
description: Weekly Integration Review — cross-domain health check and priority alignment
---

# Weekly Integration Review (`/review`)

> **Purpose**: Generate a cross-domain life health check, surface constraint conflicts, and identify the week's highest-leverage action.
> **Frequency**: Weekly, or on demand via `/review`.

## Steps

### 1. Load Context

// turbo
Load the following files for current state:

- `.context/memory_bank/activeContext.md`
- `.context/memory_bank/userContext.md`

### 2. Generate Domain Health Check

Scan `activeContext.md` for recent activity across all 6 domains (Career, Finances, Health, Relationships, Growth, Environment). Rate each domain 1-10 based on:

- **Recent activity level** (active = good for Career/Growth; may be bad for Health if over-index)
- **Trend** (↑ improving, → stable, ↓ declining)
- **Attention needed** (flag if declining for ≥2 weeks)

Output as:

```
DOMAIN HEALTH CHECK
| Domain       | Status | Trend  | Attention? |
|--------------|--------|--------|------------|
| Career       | X/10   | ↑/→/↓  | ✅/❌       |
| Finances     | X/10   | ↑/→/↓  | ✅/❌       |
| Health       | X/10   | ↑/→/↓  | ✅/❌       |
| Relationships| X/10   | ↑/→/↓  | ✅/❌       |
| Growth       | X/10   | ↑/→/↓  | ✅/❌       |
| Environment  | X/10   | ↑/→/↓  | ✅/❌       |
```

### 3. Detect Constraint Conflicts

Cross-reference active tasks and commitments. Flag conflicts:

```
CONSTRAINT CONFLICTS DETECTED
⚠️ [Conflict 1 description]
⚠️ [Conflict 2 description]
→ Proposed resolution: [specific tradeoff]
```

### 4. List Pending Decisions

Scan `activeContext.md` for open tasks and pending decisions. Classify each:

```
DECISIONS PENDING
| Decision        | Door Type | Deadline | Recommended Action |
|-----------------|-----------|----------|-------------------|
| [Decision 1]    | One/Two   | [Date]   | [Action]          |
| [Decision 2]    | One/Two   | [Date]   | [Action]          |
```

### 5. Identify Highest-Leverage Action

Based on all the above, output:

```
THIS WEEK'S FOCUS
Based on your priorities and current status, the highest-leverage 
action this week is: [specific, single focus]
```

### 6. Quicksave

// turbo
Run quicksave to checkpoint the review:

```bash
python3 .agent/scripts/quicksave.py "Weekly Integration Review completed. [1-line summary of key finding]."
```

## Output Format

Combine all sections into a single, clean artifact. Keep it to one page. If the user wants deeper analysis on any domain, they can ask.

## Notes

- This workflow references **Protocol 382: Cross-Domain Constraint Propagation**.
- The health ratings are based on available context, not self-reported data. If data is missing, flag it: "Health domain rated with low confidence — no recent data."
- Avoid sycophancy. If everything is fine, say so briefly. If something is declining, say it directly.
