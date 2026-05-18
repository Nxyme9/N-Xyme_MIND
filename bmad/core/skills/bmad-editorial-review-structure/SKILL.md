---
name: bmad-editorial-review-structure
description: Structural editor that proposes cuts, reorganization, and simplification. Use when user says "review structure" or "improve organization".
argument-hint: "[document-path] [target-length] [retention-requirements]"
---

# Editorial Review — Structure

## Overview
Structural edit of a document. Propose cuts, reordering, and simplification while preserving all key information. Unlike prose edits, this changes organization.

## On Activation
1. **Analyze.** Outline the document's current structure.
2. **Evaluate.** What works? What's redundant? What's missing?
3. **Propose.** New structure with rationale.
4. **Before/After.** Show the transformation.

## Structural Lenses
1. **Hierarchy** — Are topics in the right order?
2. **Proportion** — Does section length match importance?
3. **Redundancy** — What's said multiple times?
4. **Gaps** — What's missing for the intended audience?
5. **Navigation** — Can a reader follow the argument?

## Output Format
```
**Current Structure:** [outline]
**Proposed Structure:** [new outline]
**Changes:**
- Cut: "Section X" (redundant with Y)
- Move: "Topic A" → Section 3 (better context)
- Merge: "B" and "C" → single section
```