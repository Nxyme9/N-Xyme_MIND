# Draft: Layer 3 Self-Learning Implementation

## Requirements Summary (from Masterplan)
- **Target**: Layer 3: Self-Learning v1.0
- **Files to create**: skill_lifecycle.py, prompt_evolution.py, self_learning.py
- **Novel features**: Skill lifecycle state machine (no framework implements this)

## Critical Gaps to Address

| Gap | Severity | Description |
|-----|----------|-------------|
| Skill lifecycle state machine | CRITICAL | Proposed→Experimental→Active→Deprecated→Archived |
| Skill evaluation tracking | CRITICAL | Success rate, latency, cost, user satisfaction |
| Prompt evolution engine | HIGH | Generate→Critique→Refine→Evaluate (RetroAgent patterns) |
| Skill discovery | HIGH | Automatic detection of needed skills |
| Skill composition | HIGH | Dynamic combination based on task decomposition |
| Cross-session skill persistence | MEDIUM | Learning persists across restarts |

## Research Sources
- crewAIInc/crewai — Skills as filesystem packages
- microsoft/autogen (57K⭐) — Agent runtime lifecycle  
- SkillOrchestra (arXiv 2602.19672) — Skill transfer learning
- RetroAgent (arXiv) — Retrospective dual intrinsic feedback

## Module Dependencies
- skill_lifecycle.py: Core state machine (PREREQUISITE for others)
- prompt_evolution.py: Depends on skill_lifecycle for skill context
- self_learning.py: Depends on both for tracking + evolution

## Implementation Priority
1. skill_lifecycle.py (state machine foundation)
2. Skill evaluation metrics in skill_lifecycle
3. prompt_evolution.py (prompt feedback loop)
4. self_learning.py (pattern extraction + adaptation)

## Test Strategy
- Unit tests for state machine transitions
- Integration tests for skill evaluation
- Mock agent protocol for prompt evolution
- Cross-session tests for persistence