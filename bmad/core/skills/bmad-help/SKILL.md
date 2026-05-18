---
name: bmad-help
description: Analyzes current state and user query to answer BMad questions or recommend the next workflow or agent. Use when user says "what should I do next", "what do I do now", or asks about BMad.
argument-hint: "[current-state] [user-query]"
---

# BMad Help — Navigation & Recommendations

## Overview
Analyze the user's current state and query to recommend the next BMAD workflow, skill, or agent to use.

## On Activation
1. **Assess state.** What project phase? What was just completed?
2. **Understand query.** What does the user want to do?
3. **Recommend.** The most appropriate next skill/workflow.

## Recommendation Categories
- **Planning:** bmad-create-product-brief → bmad-edit-prd → bmad-create-ux-design → bmad-create-architecture → bmad-create-epics-and-stories → bmad-check-implementation-readiness
- **Implementation:** bmad-dev-story → bmad-code-review → bmad-retrospective
- **Research:** bmad-domain-research → bmad-market-research → bmad-technical-research
- **Quality:** bmad-validate-prd → bmad-testarch-test-design → bmad-testarch-trace
- **Meta:** bmad-memory-consolidate → bmad-memory-recall → bmad-distillator

## Output Format
```
**Current Phase:** [phase]
**Recommended Next:** [skill/workflow name]
**Rationale:** [why this is the right choice]
**Prerequisites:** [what to have ready]
```