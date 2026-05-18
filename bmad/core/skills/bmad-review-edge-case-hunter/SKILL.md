---
name: bmad-review-edge-case-hunter
description: Walk every branching path and boundary condition in content, report only unhandled edge cases. Use when you need exhaustive edge-case analysis.
argument-hint: "[code-or-spec-path] [context]"
---

# Edge Case Hunter — Exhaustive Boundary Analysis

## Overview
Walk every branching path, boundary condition, and state transition in a system. Report ONLY unhandled edge cases. Method-driven, not attitude-driven.

## On Activation
1. **Map branches.** List all decision points.
2. **Identify boundaries.** Numeric limits, state transitions, null paths.
3. **Walk paths.** What happens at each boundary?
4. **Report.** Only unhandled cases.

## Edge Case Categories
1. **Empty/null** — What happens with no input?
2. **Boundary** — At the limit? Just over? Just under?
3. **Concurrent** — Two things happening at the same time?
4. **Failure** — Network down? File missing? Permission denied?
5. **State** — Wrong order? Missing initialization? Orphaned state?

## Output Format
```
## Unhandled Edge Cases
1. [path/condition] — What happens? — Severity: [high/med/low]
2. ...

## Handled (for reference)
- [condition] — handled by [mechanism]
```