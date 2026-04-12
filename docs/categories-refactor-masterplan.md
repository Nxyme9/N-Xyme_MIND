# Categories Refactor Masterplan

## Goal
Consolidate 9 categories → 5 categories following industry gold standards

## Current State (9 Categories)

| Category | Purpose | Model |
|----------|---------|-------|
| visual-engineering | UI/UX work | minimax-m2.5 (medium) |
| ultrabrain | Complex logic | minimax-m2.5 (high) |
| deep | Autonomous research | minimax-m2.5 (medium) |
| artistry | Creative problem-solving | minimax-m2.5 (high) |
| quick | Trivial tasks | minimax-m2.5 |
| unspecified-low | Low-effort tasks | minimax-m2.5 |
| unspecified-high | High-effort tasks | minimax-m2.5 (medium) |
| routing | Delegation only | minimax-m2.5 |
| writing | Documentation | minimax-m2.5 (high) |

## Target State (5 Categories)

| Category | Purpose | Merged From | Model |
|----------|---------|-------------|-------|
| visual-engineering | UI/UX, styling, animations | visual-engineering | minimax-m2.5 (medium) |
| deep | Complex reasoning, research, implementation | deep + ultrabrain + artistry + unspecified-high | minimax-m2.5 (high) |
| quick | Trivial tasks, fixes | quick + unspecified-low | minimax-m2.5 |
| routing | Agent delegation only | routing | minimax-m2.5 |
| writing | Documentation, prose | writing | minimax-m2.5 (high) |

## Industry Gold Standard Rationale

Based on best practices from AI agent frameworks:

1. **Specialized (visual-engineering)** - Distinct skill set for UI/UX
2. **General Purpose (deep)** - Consolidate "smart" categories that all need high reasoning
3. **Lightweight (quick)** - Fast, trivial tasks don't need complexity tiers
4. **Meta (routing)** - Pure delegation, never writes code
5. **Content (writing)** - Distinct from code work

## Files Requiring Updates

### Configuration Files
- [ ] `oh-my-opencode.json` - categories section

### Code References
- [ ] `AGENTS.md` - category routing table (lines ~910, ~1022, ~1141, ~1192, ~1243, ~1292)
- [ ] `packages/orchestration/thinking_effort.py` - effort mapping (line 229)
- [ ] `packages/orchestration/athena_bridge.py` - task type mapping (lines 71, 79)

### Validation Scripts
- [ ] `bin/validate-config-driven.py` - allowed categories
- [ ] `bin/validate-agent-call.py` - category validation

### Documentation
- [ ] `docs/obsidian/data/index.md` - category definitions
- [ ] `docs/obsidian/root/config.md` - 9 categories reference
- [ ] `docs/N-XYME-STANDALONE-MASTERPLAN.md` - categories setup task

## Migration Strategy

### Phase 1: Update Configuration (oh-my-opencode.json)
1. Remove: ultrabrain, artistry, unspecified-low, unspecified-high
2. Update deep to use variant "high"

### Phase 2: Update Code References
1. Update thinking_effort.py mapping
2. Update athena_bridge.py mapping

### Phase 3: Update Validation
1. Update validate-config-driven.py
2. Update validate-agent-call.py

### Phase 4: Update Documentation
1. Update all docs references

## Backwards Compatibility

For existing code using old categories:
- ultrabrain → deep
- artistry → deep  
- unspecified-low → quick
- unspecified-high → deep

Add alias mapping in code to redirect old categories to new ones.

## Testing

After refactor:
1. Run quality gates
2. Verify agent routing works
3. Test each category responds correctly
4. Check validation scripts pass

## Status: NOT STARTED

This is a larger refactor - recommended to do after MCP integration work is complete.