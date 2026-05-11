---
epic_id: E-103
title: "Architecture Cleanup"
priority: P1
stories: 5
points: 12
created: 2026-05-11
sprint: sprint-3
status: pending
bmad_agents:
  lead: Winston (architect)
  dev: Amelia
---

# Epic E-103: Architecture Cleanup

**Priority:** P1 | **Stories:** 5 | **Points:** 12 | **Risk:** MEDIUM

## Epic Goal

Eliminate architectural debt by consolidating duplicate code, documenting unclear boundaries, and wiring disconnected components.

## Rationale

- Architecture scored 75/100 (B)
- memory_core/memory_store 85% duplication is the highest-priority architectural issue
- 148 CREATE TABLE without migration framework is a ticking time bomb
- intelligent_router_mcp and handoff system are well-designed but unwired

## Success Criteria

1. ADR decision on memory_core/memory_store consolidation
2. Router precedence documented with clear precedence rules
3. Migration framework operational
4. intelligent_router_mcp wired OR removed
5. Handoff system connected to spawn pipeline

---

## Story S-301: memory_core/memory_store Merge Decision

**Story ID:** S-301 | **Points:** 5 | **Priority:** HIGH | **TDD:** Design-First | **DEPENDS:** None | **BLOCKS:** S-303

### What
memory_core and memory_store are ~85% identical. Create ADR, choose: (a) merge into single memory_core, or (b) deprecate memory_store with migration guide.

### Files
- `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/memory_core/`
- `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/memory_store/`
- `docs/adr-001-memory-consolidation.md`

### Root Cause
Two parallel implementations diverged. Any bug fix must be applied twice. Maintenance nightmare.

### ADR Process
1. Analyze both implementations line-by-line
2. Document differences (the ~15% that differs)
3. Evaluate: merge vs deprecate
4. Write ADR with decision + rationale
5. Implement the chosen path

### ADR Template
```markdown
# ADR-001: Memory Core vs Memory Store Consolidation

## Status
Proposed | Accepted | Deprecated

## Context
[Describe the problem: two ~85% identical implementations]

## Decision
[Merge into single memory_core | Deprecate memory_store]

## Consequences
### Positive
- ...

### Negative
- ...

## Alternatives Considered
1. Keep both (rejected because...)
2. ...
```

### Acceptance Criteria
- AC-301.1: ADR exists at `docs/adr-001-memory-consolidation.md`
- AC-301.2: ADR includes analysis of both implementations
- AC-301.3: ADR includes decision + rationale
- AC-301.4: ADR includes consequences (positive/negative)
- AC-301.5: If merge: single package with unified API, all imports updated
- AC-301.6: If deprecate: memory_store marked `@deprecated`, migration guide created
- AC-301.7: All tests pass after implementation

### QA Commands
```bash
# Verify ADR exists
ls -la docs/adr-001-memory-consolidation.md

# If merge: verify single package
python3 -c "from memory_core import MemoryStore; print('OK')"
python3 -c "from memory_store import MemoryStore; print('DEPRECATED')"  # Should warn

# If deprecate: verify deprecation warning
python3 -W error::DeprecationWarning -c "from memory_store import MemoryStore"

# All tests pass
pytest tests/ -v
```

### BMad Agent Assignment
- Winston (architect): Decision authority, ADR writing
- Amelia (dev): Implementation after ADR decision

### Atomic Commit
```
refactor(memory): decision and implementation for core/store merge
```

---

## Story S-302: Router Precedence Documentation

**Story ID:** S-302 | **Points:** 2 | **Priority:** MEDIUM | **TDD:** Documentation Only | **DEPENDS:** None

### What
Document precedence between three_stage_router, adaptive_router, and nx_routing. Precedence currently undefined.

### Files
- `docs/ROUTER-PRECEDENCE.md` (create)
- `packages/two_stage_router.py`
- `packages/adaptive_router.py`
- `packages/nx_routing.py`

### Router Analysis Required
1. **two_stage_router**: What does it route? When is it called?
2. **adaptive_router**: What adaptation does it do? When is it used?
3. **nx_routing**: What's nx_routing's role? Is it a wrapper?

### Acceptance Criteria
- AC-302.1: `docs/ROUTER-PRECEDENCE.md` exists
- AC-302.2: Each router's purpose documented
- AC-302.3: Precedence rules clearly stated (which router called first, fallback path)
- AC-302.4: Test scenarios for all routing combinations documented
- AC-302.5: Code comments reference the doc

### QA Commands
```bash
# Document exists
ls -la docs/ROUTER-PRECEDENCE.md

# Check router files reference the doc
grep -l "ROUTER-PRECEDENCE" packages/*router*.py
```

### BMad Agent Assignment
- Winston (architect): Documentation
- Paige (tech-writer): Review and formatting

### Atomic Commit
```
docs(router): document precedence between router implementations
```

---

## Story S-303: Migration Framework Setup

**Story ID:** S-303 | **Points:** 2 | **Priority:** MEDIUM | **TDD:** Test-First | **DEPENDS:** S-301

### What
148 CREATE TABLE IF NOT EXISTS with no migration framework. Convert to versioned migrations.

### Files
- `nx_engine/database/` or similar (where 148 CREATE TABLE exist)
- `migrations/` (create)
- `alembic.ini` or custom migration runner (create)

### Root Cause
Schema changes are applied manually or via CREATE TABLE IF NOT EXISTS. No version history, no rollback capability.

### Implementation Options
1. **Alembic**: Full-featured, well-supported. Overkill for simple schema?
2. **Custom runner**: Simpler, matches existing patterns. Less support.

### Acceptance Criteria
- AC-303.1: Migration directory structure created (`migrations/versions/`)
- AC-303.2: Existing 148 CREATE TABLE converted to initial migration
- AC-303.3: `alembic upgrade head` or custom equivalent succeeds
- AC-303.4: Migration history tracked in database
- AC-303.5: New migrations can be created and applied
- AC-303.6: `alembic downgrade -1` or equivalent works for rollback testing

### QA Commands
```bash
# If using Alembic
alembic current
alembic history
alembic upgrade head
alembic downgrade -1
alembic upgrade head

# If using custom runner
python3 -m nx_engine.migrations.migrate --status
python3 -m nx_engine.migrations.migrate --upgrade
python3 -m nx_engine.migrations.migrate --rollback
```

### BMad Agent Assignment
- Amelia (dev): Implementation

### Atomic Commit
```
feat(migrations): add Alembic-based migration framework
```

---

## Story S-304: intelligent_router_mcp Wire OR Remove

**Story ID:** S-304 | **Points:** 2 | **Priority:** MEDIUM | **TDD:** Decision-First | **DEPENDS:** None

### What
intelligent_router_mcp exists in codebase but not wired into opencode.json. Either wire it OR remove dead code.

### Files
- `packages/intelligent_router_mcp.py` (or similar)
- `opencode.json` (check if MCP is registered)
- `docs/INTELLIGENT-ROUTER.md` (create if wiring)

### Root Cause
Dead code accumulates when features are prototyped but not productionized.

### Acceptance Criteria
- AC-304.1: Decision made: wire OR remove
- AC-304.2: If wire:
  - MCP registered in opencode.json
  - Integration point documented in `docs/INTELLIGENT-ROUTER.md`
  - Functionality tested and working
- AC-304.3: If remove:
  - Dead code fully removed (no orphan references)
  - opencode.json clean (no dangling MCP references)
  - No broken imports or references
- AC-304.4: No mixed state (partially wired == worse than fully removed)

### QA Commands
```bash
# If wire: verify registration
grep -i "intelligent" opencode.json

# If remove: verify no references
grep -r "intelligent_router" --include="*.py" packages/
grep -r "intelligent" opencode.json
```

### BMad Agent Assignment
- Winston (architect): Decision authority

### Atomic Commit
```
feat(intelligent_router): wire or remove dead code
```

---

## Story S-305: Handoff System Wiring

**Story ID:** S-305 | **Points:** 2 | **Priority:** MEDIUM | **TDD:** Test-First | **DEPENDS:** S-201

### What
handoff.py well-designed but NOT connected to spawn pipeline. Wire handoff_trigger() at appropriate spawn points.

### Files
- `packages/handoff.py` or similar
- `src/omo_orchestrator/` (spawn pipeline location)
- `docs/HANDOFF-SYSTEM.md` (create)

### Root Cause
Good code exists but isn't called. The spawn pipeline doesn't trigger handoffs.

### Acceptance Criteria
- AC-305.1: handoff_trigger() called at appropriate spawn points
- AC-305.2: Handoff conditions documented (when does handoff occur?)
- AC-305.3: `docs/HANDOFF-SYSTEM.md` created with integration docs
- AC-305.4: Handoff flow tested end-to-end
- AC-305.5: No handoff calls in async context without proper await (depends on S-201)

### QA Commands
```bash
# Verify handoff is called
grep -n "handoff" src/omo_orchestrator/spawn*.py
python3 -c "
import asyncio
from nx_engine.omo_orchestrator import spawn_task
# Test handoff triggers
"

# Verify docs exist
ls -la docs/HANDOFF-SYSTEM.md
```

### BMad Agent Assignment
- Amelia (dev): Implementation (after S-201 completes)

### Atomic Commit
```
feat(handoff): wire handoff system into spawn pipeline
```

---

## Quality Gates (All Stories)

| Gate | Command | Must Pass |
|------|---------|-----------|
| Typecheck | `mypy src/` | Zero errors |
| Lint | `ruff check src/` | Zero errors |
| Format | `ruff format --check src/` | Zero diffs |
| Tests | `pytest tests/ -v` | All pass |
| Secrets | `gitleaks detect --verbose` | Zero leaks |

---

## Timeline & Dependencies

| Wave | Day | Stories | Dependencies |
|------|-----|---------|--------------|
| Wave 1 | Day 2-4 | S-301: memory decision ( Winston) | None |
| Wave 1 | Day 2-4 | S-302: router docs (Winston) | None |
| Wave 1 | Day 2-4 | S-304: intelligent_router (Winston) | None |
| Wave 2 | Day 5-8 | S-303: migrations (Amelia) | S-301 |
| Wave 2 | Day 5-8 | S-305: handoff wiring (Amelia) | S-201 |

**Critical Path:** S-201 → S-305
**Estimated Sprint 2:** E3 can begin when S-201 completes (Wave 1 of Sprint 1)

---

## Definition of Done

All of the following must be true for this epic to be DONE:

1. ADR-001 decision made and implemented
2. Router precedence documented with clear rules
3. Migration framework operational with 148 tables migrated
4. intelligent_router_mcp either wired + documented OR removed cleanly
5. Handoff system connected to spawn pipeline
6. All 5 commits merged with passing CI
7. Architecture audit score improves from **75/100 to 85+/100**