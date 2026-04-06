# Delegation Masterplan - Final

## Overview

This document serves as the authoritative reference for all ultrawork execution in the N-Xyme_MIND project. It defines the complete delegation strategy, quality gates, fallback mechanisms, and atomic commit rules that Sisyphus follows for maximum speed and accuracy.

## TL;DR

> **Quick Summary**: Comprehensive delegation masterplan with phased execution, quality gates, and fallback chains for ultrawork execution.
> 
> **Deliverables**:
> - Phase 0: Pre-flight validation
> - Wave 1: Research (background agents)
> - Wave 2: Implementation (synchronous execution)
> - Wave 3: Verification (quality gates + review)
> - Complete fallback chains
> - Timeout escalation strategy
> - Atomic commit rules
> 
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 3 waves with sync barriers
> **Critical Path**: Phase 0 → Wave 1 → Wave 2 → Wave 3

---

## Phase 0: Pre-flight Checks (MANDATORY)

Before any work begins, validate system readiness to prevent mid-execution failures.

### 0.1 Subagent Authentication

```
Task: Validate all subagent credentials and access
Tools: github_get_me, athena_permission_status
Criteria: All subagents return valid auth status
Action: If any agent returns auth failure → STOP and resolve
```

### 0.2 MCP Health Check

```
Task: Verify MCP server availability
Tools: athena_health_check
Criteria: Minimum 6/8 MCP servers working
Servers Required:
- athena (context/memory)
- github (repo access)
- context7 (live docs)
- serena (LSP)
- git (version control)
- sequential-thinking (reasoning)
Nice to Have (blocking not required):
- memory (knowledge graph)
- hindsight (session memory)
Action: If <6 working → proceed with caution, log degraded state
```

### 0.3 Disk Space Verification

```
Task: Check available disk space
Command: df -h
Criteria: >1GB available
Action: If <1GB → clean .sisyphus/cache, .sisyphus/evidence before proceeding
```

### 0.4 Token Budget Assessment

```
Task: Estimate token budget for execution
Criteria: >20% budget remaining
Action: If <20% → compress context, reduce scope, or split execution
```

---

## Wave Structure

### Wave 1: Research (Background Agents)

**Purpose**: Gather context and information before implementation

```
Timeline: Start immediately
Duration: 5-10 minutes (wait for background_output)
Agent: Explore + Librarian (run_in_background=true)
```

#### Tasks in Wave 1

| Task ID | Task | Agent | Skills | Category |
|---------|------|-------|--------|----------|
| W1-T1 | Explore codebase patterns | Explore | [] | routing |
| W1-T2 | Research external documentation | Librarian | [] | routing |
| W1-T3 | Validate context with Oracle | Oracle | [] | routing |

#### Sync Barrier (CRITICAL)

```
AFTER Wave 1 completes:
1. background_output(task_id) → retrieve all results
2. Validate: Check for empty results, errors
3. Synthesize: Merge findings into context
4. Proceed ONLY after barrier cleared
```

**Why Sync Barrier Matters**:
- Momus identified race condition: Wave 1 async, Wave 2 sync
- Without barrier → Wave 2 executes with stale/empty context
- This causes implementation failures and rework

#### Wave 1 Output Requirements

```
Required: All tasks complete with results
Validation:
- [ ] Explore returned file paths
- [ ] Librarian returned doc references
- [ ] No critical errors in output
If validation fails → STOP and re-run Wave 1
```

---

### Wave 2: Implementation (Synchronous Execution)

**Purpose**: Execute implementation tasks with proper category and skills

```
Timeline: After Wave 1 sync barrier cleared
Duration: Variable (task complexity)
Agent: Hephaestus (implementation) | Category-based delegation
```

#### Tasks in Wave 2

| Task ID | Task | Agent | Skills | Category | Fallback |
|---------|------|-------|--------|----------|----------|
| W2-T1 | Core implementation | Hephaestus | git-master | deep | Oracle → retry |
| W2-T2 | Feature development | Hephaestus | git-master | deep | Oracle → retry |
| W2-T3 | Configuration | Hephaestus | git-master | unspecified-high | Oracle → retry |

#### Skills Configuration (REQUIRED)

```
For ALL implementation tasks:
- git-master: REQUIRED for commits, branch management
- playwright: REQUIRED for UI/verification tasks
- dev-browser: For web interaction tasks
- frontend-ui-ux: For visual/UI tasks
```

#### TDD Integration (REQUIRED)

```
For implementation tasks:
1. RED: Write failing test first
2. GREEN: Minimal implementation to pass
3. REFACTOR: Improve while maintaining tests

Test framework:
- JavaScript/TypeScript: vitest, bun test
- Python: pytest
- Shell: bats
```

#### Rollback Strategy (NEW - from Metis)

```
If Hephaestus fails:
1. Oracle guidance → understand failure root cause
2. Fix based on guidance
3. Retry once
4. If still fails → escalate to Sisyphus for scope reduction

Rollback command: git checkout -- .
Keep checkpoint: git stash before risky operations
```

---

### Wave 3: Verification (Quality Gates + Review)

**Purpose**: Validate implementation meets quality standards

```
Timeline: After Wave 2 completes
Duration: 10-15 minutes
Agents: Oracle + Momus (sequential)
```

#### Quality Gates (6 Core + 4 New)

| Gate | Tool | Pass Criteria |
|------|------|----------------|
| G1: Type Check | tsc --noEmit | Exit code 0 |
| G2: Lint | eslint, ruff | Exit code 0 |
| G3: Format | prettier, black | Exit code 0 |
| G4: Tests | bun test, pytest | Exit code 0 |
| G5: Secrets | bin/quality-gates/gate-5-secrets.sh | Exit code 0 |
| G6: Placeholders | bin/quality-gates/gate-6-placeholders.sh | Exit code 0 |
| **G7: Dependency Scan** | npm audit, pip-audit | No critical/high vulns |
| **G8: Static Security** | semgrep, bandit | No critical findings |
| **G9: Performance** | Performance benchmarks | Within thresholds |
| **G10: Accessibility** | axe-core, lighthouse | No critical a11y issues |

#### Verification Flow

```
Wave 3 Execution:
1. Run G1-G6 (core gates) → ALL must pass
2. If pass → Run G7-G10 (security gates)
3. If ALL gates pass → Oracle review
4. Oracle passes → Momus review
5. Momus passes → Execution complete
6. Any failure → Fix and re-run gates
```

---

## Agent → Task Mapping (Complete)

### Primary Agents

| Agent | Role | Model | Tasks |
|-------|------|-------|-------|
| Sisyphus | Orchestrator | qwen3.6-plus-free (high) | Overall coordination |
| Prometheus | Plan Builder | qwen3.6-plus-free (high) | Planning |
| Hephaestus | Implementation | qwen3.6-plus-free (medium) | Code writing |
| Oracle | Architecture Review | qwen3.6-plus-free (high) | Design review |
| Momus | Adversarial Review | qwen3.6-plus-free (high) | Critical analysis |
| Explore | Codebase Search | minimax-m2.5-free | Research |
| Librarian | External Docs | minimax-m2.5-free | Research |
| Atlas | Plan Executor | minimax-m2.5-free | Subagent execution |

### Category Assignments

| Category | Model | Best For |
|----------|-------|----------|
| visual-engineering | kimi-k2.5-free (high) | UI/UX, React, CSS |
| ultrabrain | qwen3.6-plus-free (high) | Complex logic, hard problems |
| deep | qwen3.6-plus-free (medium) | Implementation, code writing |
| artistry | minimax-m2.5-free | Creative problem-solving |
| quick | minimax-m2.5-free | Trivial fixes |
| unspecified-low | minimax-m2.5-free | Low effort tasks |
| unspecified-high | minimax-m2.5-free | High effort tasks |
| routing | minimax-m2.5-free | Delegation only |
| writing | minimax-m2.5-free | Documentation |

### Skills Assignments

| Skill | Use Case | Required For |
|-------|----------|--------------|
| git-master | Commits, branches, history | ALL implementation tasks |
| playwright | Browser automation | UI verification, web testing |
| dev-browser | Browser interaction | Web navigation, forms |
| frontend-ui-ux | UI/UX development | Visual tasks |

---

## Fallback Chains (CRITICAL)

### Agent Failure Fallback

```
Explore fails:
1. Sisyphus-Junior (same task, simplified)
2. Atlas (same task, different approach)
3. Parallel fire (5 agents, different angles)

Librarian fails:
1. Explore (same task, different strategy)
2. Sisyphus-Junior (same task, simplified)
3. Web search fallback (direct search)

Hephaestus fails:
1. Oracle guidance (understand failure)
2. Retry with guidance
3. Sisyphus (scope reduction, re-plan)

Oracle fails:
1. Momus (alternative review)
2. Sisyphus (manual review)
3. User (escalation)

Momus fails:
1. Re-run Momus (retry once)
2. Oracle (alternative review)
3. User (escalation)
```

### Multi-Agent Fallback Matrix

| Primary | Fallback 1 | Fallback 2 | Fallback 3 | Escalate |
|---------|-----------|-----------|------------|----------|
| explore | sisyphus-junior | atlas | parallel fire (5) | user |
| librarian | explore | sisyphus-junior | parallel fire (3) | user |
| atlas | sisyphus-junior | hephaestus | parallel fire | user |
| hephaestus | oracle (guidance) | retry | sisyphus (re-plan) | user |
| oracle | momus | sisyphus | user | - |
| momus | re-run | oracle | user | - |

---

## Timeout Strategy

### Timeout Escalation Chain

```
Level 1: Simple Operations (2 min timeout)
- Glob, Read, Grep operations
- If timeout → immediate fallback

Level 2: Search Operations (5 min timeout)
- Explore, Librarian searches
- If timeout → retry once
- If retry fails → fallback to alternative agent

Level 3: Analysis Operations (10 min timeout)
- Oracle, Momus reviews
- If timeout → parallel fire (multiple agents)
- If parallel fails → escalate to user
```

### Timeout Configuration

| Operation | Default Timeout | Max Retries | Action on Failure |
|-----------|----------------|-------------|-------------------|
| File operations | 30s | 3 | Fallback to alternative |
| Agent execution | 2min | 2 | Fallback chain |
| Quality gates | 5min | 1 | Report failure |
| Review (Oracle/Momus) | 10min | 1 | Parallel fire |

---

## Atomic Commit Rules

### Pre-commit Checklist

```
Before ANY commit:
1. [ ] All quality gates pass (G1-G10)
2. [ ] Tests pass (unit + integration)
3. [ ] No debug code (console.log, print statements)
4. [ ] No TODO comments without tracking
5. [ ] No hardcoded credentials
6. [ ] Git status clean (no untracked noise)
```

### Commit Message Format

```
Format: [TYPE]: <subject>

Types:
- feat: New feature
- fix: Bug fix
- refactor: Code refactoring
- docs: Documentation
- test: Test additions/changes
- chore: Maintenance, deps
- style: Formatting, linting
- perf: Performance improvement
- security: Security fix

Examples:
- feat(auth): Add JWT authentication
- fix(login): Resolve session timeout bug
- refactor(api): Simplify error handling
- docs(readme): Update installation guide
```

### Branch Strategy

```
Main branch: main (protected)
- Direct push forbidden
- PR required for all changes
- Code review mandatory

Feature branches: feature/<name>
- Branch from main
- Rebase before merge
- Squash on merge
```

### Commit Frequency

```
During implementation:
- Commit after each task completion
- Minimum: 1 commit per wave
- Maximum: 5 commits per session

Commit messages should answer:
- What changed?
- Why changed?
- How to verify?
```

---

## TDD Integration

### Test-First Workflow

```
For ALL implementation tasks:

1. BEFORE writing code:
   - Write failing test (RED)
   - Verify test fails with meaningful error

2. Write minimal code (GREEN):
   - Only enough to pass the test
   - No premature optimization

3. Refactor (REFACTOR):
   - Improve code while maintaining tests
   - Add comments where non-obvious

4. Commit:
   - Include test in same commit as implementation
   - Message: "feat: Add feature with tests"
```

### Test Framework Standards

| Language | Framework | Config |
|----------|-----------|--------|
| TypeScript | vitest | vitest.config.ts |
| JavaScript | bun test | package.json |
| Python | pytest | pyproject.toml |
| Shell | bats | .bats/*.bats |

### Test Quality Requirements

```
Required per task:
- Happy path test (valid input → valid output)
- Edge case tests (empty, null, boundary)
- Error case tests (invalid input → graceful failure)

Coverage target:
- Core business logic: 80%+
- Utility functions: 90%+
- UI components: 60%+ (interaction tests)
```

---

## Security Gates (Detailed)

### G7: Dependency Vulnerability Scan

```
Tools: npm audit, pip-audit, dependabot
Command: npm audit --audit-level=high
Criteria: No critical or high vulnerabilities
Action: If found → update dependency or add to allowlist with justification
```

### G8: Static Security Analysis

```
Tools: semgrep, bandit, eslint (security rules)
Command: semgrep --config=auto
Criteria: No critical security findings
Check for:
- SQL injection
- XSS vulnerabilities
- Hardcoded secrets
- Insecure dependencies
```

### G9: Performance Benchmarks

```
Tools: lighthouse, web-vitals, custom benchmarks
Criteria: Within defined thresholds
Metrics:
- First Contentful Paint: <1.5s
- Time to Interactive: <3s
- Bundle size: <500KB (JS)
- API response: <200ms
```

### G10: Accessibility Audit

```
Tools: axe-core, lighthouse a11y
Command: lighthouse --only-categories=accessibility
Criteria: No critical accessibility issues
WCAG Level: A (minimum), AA (target)
```

---

## Execution Checklist

### Before Starting

```
[ ] Phase 0 complete (pre-flight checks)
[ ] Token budget >20%
[ ] All required MCP servers available
[ ] Clear task specification
```

### During Execution

```
[ ] Wave 1: Wait for sync barrier before Wave 2
[ ] Wave 2: Use correct category and skills
[ ] Wave 2: TDD workflow (test-first)
[ ] Wave 2: Git checkpoint before risky operations
[ ] Wave 3: Run all quality gates
[ ] Fallback triggered when needed
[ ] Timeouts respected
```

### After Completion

```
[ ] All quality gates pass
[ ] Oracle review passed
[ ] Momus review passed
[ ] Atomic commits created
[ ] Evidence files saved to .sisyphus/evidence/
[ ] Session summary saved
```

---

## Summary

This masterplan provides:

1. **Phase 0**: Pre-flight validation to prevent mid-execution failures
2. **Wave 1**: Research with proper sync barrier (solves Momus race condition)
3. **Wave 2**: Implementation with TDD, skills, and rollback (solves Metis gaps)
4. **Wave 3**: Verification with 10 quality gates including security (solves Metis/Momus gaps)
5. **Fallback Chains**: Multi-agent fallback for all failure scenarios
6. **Timeout Strategy**: Escalation chain for different operation types
7. **Atomic Commit Rules**: Pre-commit checklist, format, branch strategy
8. **TDD Integration**: Test-first workflow for all implementation tasks

This plan addresses all findings from Metis and Momus reviews and provides a complete reference for Sisyphus ultrawork execution.

---

**Document Version**: 1.0
**Last Updated**: 2026-04-04
**Status**: APPROVED FOR EXECUTION