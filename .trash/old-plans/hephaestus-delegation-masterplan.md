# Hephaestus-Exclusive Coding Delegation System — Masterplan

## Overview

**Goal**: Ensure Hephaestus is the **ONLY** agent that writes code. All other agents must delegate coding work to Hephaestus via standardized prompts.

**Why**: Hephaestus uses `minimax-m2.5-free` (80.2% SWE-bench), which beats `qwen3.6-plus-free` (78.8%). Centralizing code writing eliminates mixed-quality output, enforces consistent patterns, and creates a single quality gate.

**Scope**: AGENTS.md rules, oh-my-opencode.json agent descriptions, delegation prompt templates, quality gates, fallback chains, context passing, parallel delegation, verification workflow.

**Out of scope**: Changing Hephaestus model, using other agents for coding, modifying any files (planning only).

---

## 1. Agent Role Matrix

### 1.1 Who Codes vs Who Doesn't

| Agent | Writes Code? | Role | What It Does Instead |
|-------|-------------|------|---------------------|
| **Hephaestus** | YES (exclusive) | Implementation | Writes code, creates files, edits files, builds features |
| Sisyphus | NO | Orchestrator | Plans, delegates to Hephaestus, verifies output, coordinates waves |
| Prometheus | NO | Plan Builder | Creates implementation plans with file lists, interfaces, acceptance criteria |
| Oracle | NO | Architecture Review | Reviews Hephaestus output for architectural soundness |
| Momus | NO | Adversarial Review | Red-teams Hephaestus output for edge cases, security flaws |
| Metis | NO | Pre-planning | Gap analysis before planning — identifies what Hephaestus needs to know |
| Explore | NO | Codebase Search | Finds existing patterns, file locations, code conventions for Hephaestus |
| Librarian | NO | External Research | Finds docs, API references, best practices for Hephaestus |
| Atlas | NO | Plan Executor | Executes non-coding steps (git ops, file moves, config reads) |
| Sisyphus-Junior | NO | Light Tasks | Simple non-coding tasks (reading files, checking status, formatting docs) |
| Multimodal-Looker | NO | Vision | Processes images/screenshots for Hephaestus to reference |

### 1.2 Coding vs Non-Coding Task Classification

**Coding tasks (ALWAYS → Hephaestus):**
- Writing new functions/classes/modules
- Editing existing code files (.ts, .tsx, .js, .py, .go, .rs, etc.)
- Creating new source files
- Refactoring code structure
- Writing tests (test files are code)
- Fixing bugs in code
- Adding imports/exports
- Modifying config files that affect runtime behavior (opencode.json, oh-my-opencode.json, pyproject.toml)

**Non-coding tasks (any agent can do):**
- Reading files, grepping, globbing
- Running bash commands (tests, lint, build)
- Git operations (status, diff, log, commit, push)
- Writing markdown/documentation (.md files)
- Creating directories
- Reviewing code (Oracle, Momus)
- Planning/architecture (Prometheus, Metis)
- Research/search (Explore, Librarian)
- Orchestrating/delegating (Sisyphus)

### 1.3 Gray Area Rules

| Task | Who Does It | Why |
|------|------------|-----|
| Writing .md documentation | Any agent | Not code, not executable |
| Writing shell scripts (.sh) | Hephaestus | Executable code |
| Writing JSON config | Hephaestus | Runtime behavior |
| Writing YAML config | Hephaestus | Runtime behavior |
| Writing SQL migrations | Hephaestus | Code that runs |
| Writing AGENTS.md updates | Sisyphus | Meta-rules, not application code |

---

## 2. Delegation Prompt Template

### 2.1 Standard 6-Section Prompt Format

Every delegation to Hephaestus MUST use this exact structure:

```
# SECTION 1: TASK BRIEF
**What**: [One sentence describing what to build/fix]
**Why**: [Why this is needed — business/technical reason]
**Scope**: [What's in scope, what's out of scope]

# SECTION 2: CONTEXT
**Files to modify**: [Exact file paths]
**Files to create**: [Exact file paths with parent directory]
**Existing patterns**: [Reference similar code — file:line]
**Conventions to follow**: [Project-specific style rules]

# SECTION 3: TECHNICAL SPEC
**Interfaces**: [Function signatures, type definitions]
**Inputs/Outputs**: [What goes in, what comes out]
**Error handling**: [How errors should be handled]
**Edge cases**: [Known edge cases to handle]

# SECTION 4: CONSTRAINTS
**Do NOT**: [Things to avoid — no new deps, no type changes, etc.]
**Must use**: [Required libraries, patterns, approaches]
**Performance**: [Any perf requirements]
**Security**: [Any security requirements]

# SECTION 5: ACCEPTANCE CRITERIA
**Definition of done**:
- [ ] [Criterion 1 — testable]
- [ ] [Criterion 2 — testable]
- [ ] [Criterion 3 — testable]
**Quality gates**: [Which gates must pass — lint, typecheck, tests]

# SECTION 6: VERIFICATION
**How to test**: [Exact commands to run]
**Expected output**: [What success looks like]
**Evidence files**: [What to save to .sisyphus/evidence/]
```

### 2.2 Concrete Example — Bug Fix

```
# SECTION 1: TASK BRIEF
**What**: Fix null pointer exception in user authentication middleware
**Why**: Users getting 500 errors when logging in with expired tokens
**Scope**: Fix auth middleware only — do NOT touch token generation or session storage

# SECTION 2: CONTEXT
**Files to modify**: src/middleware/auth.ts
**Files to create**: None
**Existing patterns**: See src/middleware/rate-limit.ts:45-62 for error handling pattern
**Conventions to follow**: Use project's Result<T> type, never throw raw errors

# SECTION 3: TECHNICAL SPEC
**Interfaces**: 
  - modify `validateToken(req: Request): Result<User>` to handle null token
  - return `Err('TOKEN_EXPIRED')` instead of crashing
**Inputs/Outputs**: 
  - Input: HTTP request with optional Authorization header
  - Output: Result<User> — Ok(user) or Err(reason)
**Error handling**: Return Err with specific reason, log warning, never throw
**Edge cases**: 
  - Missing Authorization header entirely
  - Malformed Bearer token (not base64)
  - Token with no expiry field

# SECTION 4: CONSTRAINTS
**Do NOT**: Add new dependencies, change User type, modify session storage
**Must use**: Result<T> from src/types/result.ts, logger from src/utils/logger.ts
**Performance**: No perf requirements for this fix
**Security**: Do NOT log token contents, only log token state (present/missing/expired)

# SECTION 5: ACCEPTANCE CRITERIA
**Definition of done**:
- [ ] No 500 errors when Authorization header is missing
- [ ] No 500 errors when token is malformed
- [ ] Returns 401 with { error: 'TOKEN_EXPIRED' } for expired tokens
- [ ] Existing valid token flow still returns 200
**Quality gates**: lint, typecheck, existing tests must pass

# SECTION 6: VERIFICATION
**How to test**: 
  - npm run test -- tests/middleware/auth.test.ts
  - npm run lint
  - npx tsc --noEmit
**Expected output**: All tests pass, exit code 0
**Evidence files**: Save test output to .sisyphus/evidence/auth-fix-test-output.txt
```

### 2.3 Concrete Example — New Feature

```
# SECTION 1: TASK BRIEF
**What**: Add rate limiting to API endpoints
**Why**: Prevent abuse and ensure fair usage across users
**Scope**: Rate limit middleware + Redis store + config — do NOT touch existing routes

# SECTION 2: CONTEXT
**Files to modify**: src/app.ts (add middleware), src/config/rate-limit.ts (create)
**Files to create**: 
  - src/middleware/rate-limit.ts
  - src/config/rate-limit.ts
  - tests/middleware/rate-limit.test.ts
**Existing patterns**: See src/middleware/auth.ts for middleware signature
**Conventions to follow**: All config from src/config/, all middleware in src/middleware/

# SECTION 3: TECHNICAL SPEC
**Interfaces**:
  - `createRateLimiter(config: RateLimitConfig): Middleware`
  - `RateLimitConfig = { windowMs: number, maxRequests: number, keyFn: (req) => string }`
**Inputs/Outputs**:
  - Input: HTTP request, extracts client IP or API key
  - Output: 429 with Retry-After header when limit exceeded, pass-through otherwise
**Error handling**: If Redis unavailable, fail open (allow requests, log error)
**Edge cases**:
  - Redis connection drops mid-request
  - Client sends requests faster than Redis can track
  - Multiple instances sharing same Redis

# SECTION 4: CONSTRAINTS
**Do NOT**: Modify existing route handlers, change auth middleware
**Must use**: ioredis (already in package.json), project's Middleware type
**Performance**: <1ms overhead per request for Redis check
**Security**: Rate limit by API key for authenticated, by IP for anonymous

# SECTION 5: ACCEPTANCE CRITERIA
**Definition of done**:
- [ ] 100 requests/min per API key allowed, 101st returns 429
- [ ] 20 requests/min per IP for anonymous, 21st returns 429
- [ ] Retry-After header present on 429 responses
- [ ] Redis failure → requests pass through, error logged
- [ ] New tests cover all edge cases
**Quality gates**: lint, typecheck, tests, no new npm audit vulnerabilities

# SECTION 6: VERIFICATION
**How to test**:
  - npm run test -- tests/middleware/rate-limit.test.ts
  - npm run lint
  - npx tsc --noExt
**Expected output**: All tests pass, no lint errors, no type errors
**Evidence files**: 
  - .sisyphus/evidence/rate-limit-test-output.txt
  - .sisyphus/evidence/rate-limit-lint-output.txt
```

### 2.4 Quick Fix Template (abbreviated for simple tasks)

For trivial fixes (typos, small corrections), use this shortened version:

```
**Task**: [What to fix]
**File**: [Exact path]
**Current**: [What's wrong — quote the line]
**Fix**: [What it should be]
**Verify**: [Command to confirm fix]
```

---

## 3. Enforcement Rules

### 3.1 AGENTS.md Rules to Add

Add these rules to AGENTS.md under a new `## Hephaestus-Exclusive Coding` section:

```markdown
## Hephaestus-Exclusive Coding

**RULE: Hephaestus is the ONLY agent that writes code.**

### 3.1.1 Absolute Prohibition

The following agents MUST NEVER write, edit, or create code files:
- Sisyphus, Prometheus, Oracle, Momus, Metis
- Explore, Librarian, Atlas, Sisyphus-Junior, Multimodal-Looker

**Code files** = any file with extensions: .ts, .tsx, .js, .jsx, .py, .go, .rs, .java, .c, .cpp, .h, .rb, .php, .swift, .kt, .sh, .bash, .sql, .tf, .yaml, .yml, .json (config), .toml, .xml

**Exception**: .md files (documentation) can be written by any agent.

### 3.1.2 Mandatory Delegation

When ANY non-Hephaestus agent encounters a task requiring code changes:
1. STOP immediately — do NOT read the file with intent to edit
2. Gather context: file paths, existing patterns, error messages
3. Delegate to Hephaestus using the 6-section prompt template
4. Wait for Hephaestus output
5. Verify output via quality gates
6. Report results

### 3.1.3 Self-Enforcement Check

Before ANY file write/edit/create operation, the agent MUST ask:
1. "Am I Hephaestus?" → If NO → STOP, delegate
2. "Is this a code file?" → If YES and NOT Hephaestus → STOP, delegate
3. "Is this documentation (.md)?" → If YES → any agent can proceed

### 3.1.4 Category Enforcement

The following categories MUST always delegate to Hephaestus for code:
- `routing` — delegation only, NEVER code
- `quick` — simple tasks, if code needed → delegate to Hephaestus
- `unspecified-low` — light tasks, if code needed → delegate to Hephaestus
- `writing` — documentation only, NEVER code

The following categories CAN contain code (but still use Hephaestus):
- `deep` → delegate to Hephaestus with `subagent_type="hephaestus"`
- `ultrabrain` → delegate to Hephaestus with `subagent_type="hephaestus"`
- `visual-engineering` → delegate to Hephaestus with `subagent_type="hephaestus"`

### 3.1.5 Violation Consequences

If a non-Hephaestus agent writes code:
1. The code is INVALIDATED — must be redone by Hephaestus
2. The commit is REVERTED
3. The agent's prompt is updated to reinforce the rule
4. The incident is logged to .sisyphus/rules/violations.log
```

### 3.2 oh-my-opencode.json Description Updates

Update agent descriptions to reinforce the coding prohibition:

```jsonc
// Sisyphus — add "NEVER writes code" to description
"description": "Primary orchestrator — plans, delegates to Hephaestus for ALL code, verifies output. NEVER writes code directly. NEVER edits .ts/.py/.js files."

// Prometheus — add "plans for Hephaestus"
"description": "Strategic planning — creates implementation plans for Hephaestus to execute. NEVER writes code. Plans include exact file paths, interfaces, and acceptance criteria."

// Oracle — add "reviews Hephaestus output"
"description": "Architecture review — reviews Hephaestus code output for design soundness. NEVER writes code. Provides guidance to Hephaestus via delegation prompts."

// Momus — add "red-teams Hephaestus output"
"description": "Adversarial review — red-teams Hephaestus code for edge cases and security flaws. NEVER writes code. Finds what Hephaestus missed."

// Metis — add "pre-planning for Hephaestus"
"description": "Gap analysis — identifies missing context before Hephaestus implements. NEVER writes code. Ensures Hephaestus has everything it needs."

// Explore — add "research for Hephaestus"
"description": "Codebase search — finds existing patterns, file locations, and conventions for Hephaestus to follow. NEVER writes code."

// Librarian — add "research for Hephaestus"
"description": "External research — finds docs, API references, and best practices for Hephaestus to use. NEVER writes code."

// Atlas — add "non-coding execution"
"description": "Plan executor — executes non-coding steps (git ops, file reads, bash commands). NEVER writes code. Delegates coding to Hephaestus."

// Sisyphus-Junior — add "light non-coding tasks"
"description": "Light tasks — quick fixes that don't involve code (reading files, checking status, formatting docs). If code changes needed, delegates to Hephaestus."

// Hephaestus — reinforce exclusivity
"description": "SOLE code writer — ALL code changes go through Hephaestus. Creates files, edits files, writes tests, fixes bugs. No other agent writes code."
```

### 3.3 Pre-Flight Validation Rule

Add to AGENTS.md under `## AGENT CALL PRE-FLIGHT CHECKLIST`:

```markdown
### Item 7: Coding Authorization (MANDATORY)

- [ ] **7. If task involves code → `subagent_type="hephaestus"`**
- [ ] **7b. If `subagent_type` ≠ "hephaestus" AND task involves code → BLOCKED**

**Code = writing/editing .ts, .tsx, .js, .py, .go, .rs, .sh, .yaml, .json, .toml files**
**NOT code = reading files, running tests, git ops, writing .md docs**
```

---

## 4. Quality Gates

### 4.1 Gate Pipeline for Hephaestus Output

Every Hephaestus output MUST pass through this pipeline before acceptance:

```
Hephaestus Output
    ↓
┌─────────────────────────────────┐
│ G1: Lint (ruff / eslint)        │ ← Exit code 0 required
├─────────────────────────────────┤
│ G2: Type Check (tsc / mypy)     │ ← Exit code 0 required
├─────────────────────────────────┤
│ G3: Format (black / prettier)   │ ← Exit code 0 required
├─────────────────────────────────┤
│ G4: Tests (pytest / vitest)     │ ← All tests pass
├─────────────────────────────────┤
│ G5: Secrets Scan (gitleaks)     │ ← No secrets found
├─────────────────────────────────┤
│ G6: Placeholder Check           │ ← No TODO/FIXME/HACK without ticket
├─────────────────────────────────┤
│ G7: Oracle Review               │ ← Architecture approval
├─────────────────────────────────┤
│ G8: Momus Review                │ ← No critical red-team findings
├─────────────────────────────────┤
│ PASS → Accept & Commit          │
│ FAIL → Return to Hephaestus     │
└─────────────────────────────────┘
```

### 4.2 Gate Commands

```bash
# G1: Lint
ruff check src/              # Python
eslint src/                  # TypeScript/JS

# G2: Type Check
npx tsc --noEmit             # TypeScript
mypy src/                    # Python

# G3: Format
npx prettier --check src/    # TypeScript/JS
black --check src/           # Python

# G4: Tests
pytest tests/ -v             # Python
npx vitest run               # TypeScript/JS

# G5: Secrets
gitleaks detect --source .   # All files

# G6: Placeholders
grep -rn "TODO\|FIXME\|HACK" src/ | grep -v ".sisyphus/"

# G7: Oracle Review (manual)
task(subagent_type="oracle", load_skills=[], run_in_background=false,
     description="Review Hephaestus output",
     prompt="Review the following code changes for architectural soundness:\n[diff output]\n\nCheck: 1. Follows existing patterns? 2. Proper error handling? 3. No over-engineering? 4. Security considerations?")

# G8: Momus Review (manual)
task(subagent_type="momus", load_skills=[], run_in_background=false,
     description="Red-team Hephaestus output",
     prompt="Red-team the following code changes. Find edge cases, security flaws, and design weaknesses:\n[diff output]\n\nAttack: 1. What edge cases are missed? 2. What could break in production? 3. What security issues exist? 4. What assumptions are fragile?")
```

### 4.3 Gate Failure Handling

```
If G1-G6 fail:
  1. Capture exact error output
  2. Return to Hephaestus with error message
  3. Hephaestus fixes → re-run gates
  4. Max 3 retries → escalate to Sisyphus

If G7 (Oracle) fails:
  1. Oracle provides specific feedback
  2. Return to Hephaestus with feedback
  3. Hephaestus revises → re-run G1-G6 → re-run G7
  4. Max 2 revisions → escalate to Sisyphus

If G8 (Momus) fails:
  1. Momus provides specific attack vectors
  2. Sisyphus evaluates: are findings valid?
  3. If valid → return to Hephaestus
  4. If invalid → Momus findings dismissed, proceed
  5. Max 2 revisions → escalate to Sisyphus
```

---

## 5. Fallback Chain

### 5.1 Hephaestus Failure Modes

| Failure Mode | Detection | Fallback Action |
|-------------|-----------|-----------------|
| Malformed output | Code doesn't parse | Return error → Hephaestus retry (max 2) |
| Wrong files edited | Diff shows unexpected files | Return with correct file list → Hephaestus retry |
| Incomplete implementation | Acceptance criteria not met | Return missing criteria → Hephaestus retry |
| Quality gate failure | G1-G6 exit code ≠ 0 | Return gate output → Hephaestus fix |
| Timeout | background_output timeout | Retry with simplified prompt |
| Model unavailable | API error | Use fallback model (see 5.2) |

### 5.2 Hephaestus Fallback Chain

```
Hephaestus attempt 1 fails:
  ↓
Reflection: What failed? Why? What's different?
  ↓
Hephaestus attempt 2 (same model, different prompt with error context):
  ↓
If attempt 2 fails:
  ↓
Oracle guidance: "Here's what failed. How should this be fixed?"
  ↓
Hephaestus attempt 3 (with Oracle guidance):
  ↓
If attempt 3 fails:
  ↓
Sisyphus scope reduction: "Break this into smaller pieces"
  ↓
Hephaestus attempt 4 (smaller scope):
  ↓
If attempt 4 fails:
  ↓
ESCALATE TO USER with full history:
  - What was attempted (4 times)
  - What failed each time
  - Oracle guidance received
  - Scope reduction attempted
```

### 5.3 Model Fallback for Hephaestus

Hephaestus fallback_models in oh-my-opencode.json (already configured):
```json
"fallback_models": [
  "opencode/qwen3.6-plus-free",
  "opencode/minimax-m2.5-free"
]
```

**Note**: The fallback to `qwen3.6-plus-free` is intentional — it's the second-best model. It should ONLY be used if `minimax-m2.5-free` is unavailable (API down, rate limited), NOT for quality reasons.

### 5.4 Fallback Escalation Matrix

| Attempt | Actor | Input | Max Time |
|---------|-------|-------|----------|
| 1 | Hephaestus | Original prompt | 5 min |
| 2 | Hephaestus | Original + error context | 5 min |
| 3 | Hephaestus | Original + Oracle guidance | 5 min |
| 4 | Hephaestus | Reduced scope from Sisyphus | 3 min |
| 5 | USER | Full history + recommendation | — |

---

## 6. Context Passing

### 6.1 The Context Problem

Hephaestus needs enough context to write correct code, but too much context:
- Wastes tokens
- Confuses the model with irrelevant information
- Increases hallucination risk

### 6.2 Context Budget

| Context Type | Max Size | Source |
|-------------|----------|--------|
| Task brief | 100 words | Sisyphus |
| File paths | 10 paths max | Explore |
| Code snippets | 50 lines per file | Explore |
| Error messages | Full output | Direct capture |
| Existing patterns | 2-3 examples | Explore |
| Type definitions | Full interfaces | Explore |
| Config values | Relevant keys only | Direct read |

### 6.3 Context Gathering Workflow

```
Sisyphus receives coding task
    ↓
Step 1: Delegate to Explore (background)
  task(subagent_type="explore", load_skills=[], run_in_background=true,
       description="Find code patterns",
       prompt="Find: 1. Similar existing implementations. 2. File structure. 3. Type definitions. 4. Error handling patterns. Return file paths + key line numbers.")
    ↓
Step 2: Wait for Explore results
    ↓
Step 3: Read only relevant files (Sisyphus does this)
  - Read type definitions
  - Read similar implementations (50 lines max)
  - Read config files (relevant sections only)
    ↓
Step 4: Synthesize context into 6-section prompt
    ↓
Step 5: Delegate to Hephaestus with synthesized prompt
```

### 6.4 Context Compression Rules

When passing context to Hephaestus:

```
DO:
- Include exact file paths
- Include function signatures
- Include type definitions
- Include error messages verbatim
- Reference existing code with file:line

DON'T:
- Include entire file contents (max 50 lines per file)
- Include unrelated code
- Include full git history
- Include multiple error logs (only the relevant one)
- Include AGENTS.md (Hephaestus has its own system prompt)
```

### 6.5 Context Template for Hephaestus Delegation

```typescript
// Context block — prepend to 6-section prompt
## Context Summary
- **Related files**: [file1:lines, file2:lines, file3:lines]
- **Existing pattern**: [file:line] — [one-line description]
- **Types to use**: [TypeName from file:line]
- **Error to fix**: [exact error message]
- **Constraints**: [project-specific rules from AGENTS.md]
```

---

## 7. Parallel Delegation

### 7.1 When to Parallelize

Parallel delegation to Hephaestus is appropriate when:
- Tasks are **independent** (no file overlap)
- Tasks target **different files**
- Tasks have **no ordering dependency**

### 7.2 Parallel Delegation Rules

```
Rule 1: Max 3 concurrent Hephaestus tasks
  - More than 3 → quality degrades
  - Queue additional tasks

Rule 2: No file overlap between parallel tasks
  - Task A edits src/auth.ts → Task B cannot edit src/auth.ts
  - If overlap detected → serialize, don't parallelize

Rule 3: Each parallel task gets its own branch
  - Branch naming: feature/<task>-hephaestus-<N>
  - Merge only after ALL parallel tasks pass gates

Rule 4: Sync barrier after all parallel tasks complete
  - Wait for ALL background Hephaestus tasks
  - Run quality gates on ALL outputs
  - Only proceed when ALL pass
```

### 7.3 Parallel Delegation Pattern

```typescript
// Wave 1: Independent tasks fire simultaneously
const task1 = task(
  subagent_type="hephaestus",
  load_skills=["git-master"],
  run_in_background=true,
  description="Fix auth middleware",
  prompt="[6-section prompt for auth fix]"
)

const task2 = task(
  subagent_type="hephaestus",
  load_skills=["git-master"],
  run_in_background=true,
  description="Add rate limiter",
  prompt="[6-section prompt for rate limiter]"
)

const task3 = task(
  subagent_type="hephaestus",
  load_skills=["git-master"],
  run_in_background=true,
  description="Update user schema",
  prompt="[6-section prompt for schema update]"
)

// Wave 2: Sync barrier — wait for ALL
const result1 = background_output(task_id=task1)
const result2 = background_output(task_id=task2)
const result3 = background_output(task_id=task3)

// Wave 3: Verify ALL
// Run quality gates on each result independently
// If any fail → return that specific task to Hephaestus
```

### 7.4 Queue Management

When more than 3 coding tasks exist:

```
Queue: [Task 4, Task 5, Task 6, ...]
Running: [Task 1, Task 2, Task 3]

When Task 1 completes:
  → Run quality gates on Task 1
  → If pass → commit Task 1
  → Start Task 4 from queue
  → Running: [Task 2, Task 3, Task 4]
```

---

## 8. Verification Workflow

### 8.1 End-to-End Verification Flow

```
User Request
    ↓
Sisyphus: Decompose task
    ↓
Sisyphus: Delegate research to Explore/Librarian (background)
    ↓
Sisyphus: Synthesize context into 6-section prompt
    ↓
Sisyphus: Delegate to Hephaestus (foreground for single, background for parallel)
    ↓
Hephaestus: Writes code
    ↓
Sisyphus: Run G1-G6 quality gates
    ↓
    ├─ FAIL → Return to Hephaestus with gate output (max 3 retries)
    └─ PASS → Continue
    ↓
Sisyphus: Delegate to Oracle for architecture review (G7)
    ↓
    ├─ FAIL → Return to Hephaestus with Oracle feedback (max 2 retries)
    └─ PASS → Continue
    ↓
Sisyphus: Delegate to Momus for adversarial review (G8)
    ↓
    ├─ FAIL → Sisyphus evaluates → return to Hephaestus if valid (max 2 retries)
    └─ PASS → Continue
    ↓
Sisyphus: Create atomic commit with git-master skill
    ↓
Sisyphus: Save evidence to .sisyphus/evidence/
    ↓
Sisyphus: Report completion to user
```

### 8.2 Evidence Collection

For every Hephaestus task, save:

```
.sisyphus/evidence/
├── <task-id>-prompt.md          # The exact prompt sent to Hephaestus
├── <task-id>-output.md          # Hephaestus's response
├── <task-id>-diff.patch         # Git diff of changes
├── <task-id>-gates.txt          # Quality gate output (G1-G6)
├── <task-id>-oracle-review.md   # Oracle's review (G7)
├── <task-id>-momus-review.md    # Momus's review (G8)
└── <task-id>-test-output.txt    # Test results
```

### 8.3 Verification Checklist

Before marking any Hephaestus task as complete:

```
- [ ] G1: Lint passes (exit code 0)
- [ ] G2: Type check passes (exit code 0)
- [ ] G3: Format check passes (exit code 0)
- [ ] G4: All tests pass
- [ ] G5: No secrets detected
- [ ] G6: No untracked placeholders
- [ ] G7: Oracle approved architecture
- [ ] G8: Momus found no critical issues
- [ ] Evidence files saved to .sisyphus/evidence/
- [ ] Commit message follows convention
- [ ] Only intended files were modified
- [ ] No unintended side effects (check git diff)
```

---

## 9. oh-my-opencode.json Changes

### 9.1 Required Description Updates

These are the EXACT changes needed in `oh-my-opencode.json`:

```jsonc
{
  "agents": {
    "sisyphus": {
      "description": "Primary orchestrator — plans, delegates to Hephaestus for ALL code, verifies output. NEVER writes code directly. NEVER edits .ts/.py/.js/.sh/.yaml/.json files."
    },
    "hephaestus": {
      "description": "SOLE code writer — ALL code changes go through Hephaestus. Creates files, edits files, writes tests, fixes bugs. No other agent writes code.",
      "model": "opencode/minimax-m2.5-free",
      "variant": "high",
      "temperature": 0.2,
      "reasoningEffort": "medium",
      "mode": "all",
      "fallback_models": [
        "opencode/qwen3.6-plus-free",
        "opencode/minimax-m2.5-free"
      ]
    },
    "prometheus": {
      "description": "Strategic planning — creates implementation plans for Hephaestus to execute. NEVER writes code. Plans include exact file paths, interfaces, and acceptance criteria."
    },
    "oracle": {
      "description": "Architecture review — reviews Hephaestus code output for design soundness. NEVER writes code. Provides guidance to Hephaestus via delegation prompts."
    },
    "momus": {
      "description": "Adversarial review — red-teams Hephaestus code for edge cases and security flaws. NEVER writes code. Finds what Hephaestus missed."
    },
    "metis": {
      "description": "Gap analysis — identifies missing context before Hephaestus implements. NEVER writes code. Ensures Hephaestus has everything it needs."
    },
    "explore": {
      "description": "Codebase search — finds existing patterns, file locations, and conventions for Hephaestus to follow. NEVER writes code."
    },
    "librarian": {
      "description": "External research — finds docs, API references, and best practices for Hephaestus to use. NEVER writes code."
    },
    "atlas": {
      "description": "Plan executor — executes non-coding steps (git ops, file reads, bash commands). NEVER writes code. Delegates coding to Hephaestus."
    },
    "sisyphus-junior": {
      "description": "Light tasks — quick non-coding tasks (reading files, checking status, formatting docs). If code changes needed, delegates to Hephaestus."
    }
  }
}
```

### 9.2 No Model Changes

**Hephaestus model stays**: `opencode/minimax-m2.5-free` with `variant: high`, `temperature: 0.2`, `reasoningEffort: medium`.

No changes to model, variant, temperature, or reasoning effort.

---

## 10. Implementation Phases

### Phase 1: Rules (AGENTS.md)
- Add `## Hephaestus-Exclusive Coding` section to AGENTS.md
- Add Item 7 to Pre-Flight Checklist
- Update `## AUTO-DELEGATION RULES` to enforce Hephaestus exclusivity
- Update `## Anti-Patterns` to add coding-by-non-Hephaestus

### Phase 2: Agent Descriptions (oh-my-opencode.json)
- Update all 10 agent descriptions with coding prohibition/authorization
- Hephaestus description reinforced as sole code writer

### Phase 3: Prompt Templates
- Create `.sisyphus/templates/hephaestus-delegation-prompt.md` with the 6-section template
- Create `.sisyphus/templates/quick-fix-prompt.md` with the abbreviated template

### Phase 4: Evidence Structure
- Create `.sisyphus/evidence/` directory if not exists
- Create `.sisyphus/evidence/.gitkeep` to track in git

### Phase 5: Verification Scripts
- Create `bin/quality-gates/gate-7-oracle-review.sh` (delegates to Oracle)
- Create `bin/quality-gates/gate-8-momus-review.sh` (delegates to Momus)

### Phase 6: Violation Tracking
- Create `.sisyphus/rules/violations.log` for tracking coding violations
- Create `.sisyphus/rules/hephaestus-exclusive-rules.md` for reference

---

## 11. Success Metrics

| Metric | Target | How to Measure |
|--------|--------|---------------|
| Code by non-Hephaestus | 0 files | Git blame — check author in commit messages |
| Hephaestus first-pass rate | >60% | Count G1-G6 passes on first attempt |
| Hephaestus final-pass rate | >95% | Count tasks that pass after ≤3 retries |
| Average retries per task | <2 | Track in violations.log |
| Parallel task success rate | >80% | Count parallel tasks that pass all gates |
| Context completeness score | >90% | Oracle rates context adequacy |
| User satisfaction | Subjective | User feedback on code quality |

---

## 12. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Hephaestus bottleneck (queue builds up) | Medium | Medium | Max 3 parallel tasks, queue management |
| Context too large for Hephaestus | Medium | Low | Context budget rules (Section 6.2) |
| Context too small for Hephaestus | High | High | Explore agent gathers context first |
| Non-Hephaestus agent writes code anyway | Low | High | AGENTS.md rules + pre-flight checklist |
| Quality gates too strict | Low | Medium | Gate failure returns to Hephaestus, not user |
| Quality gates too loose | Medium | High | Oracle + Momus review catches what gates miss |
| Model unavailable | Low | High | Fallback to qwen3.6-plus-free |

---

## Appendix A: Quick Reference Card

```
CODING TASK → Hephaestus ONLY
RESEARCH TASK → Explore / Librarian
REVIEW TASK → Oracle → Momus
PLANNING TASK → Prometheus
ORCHESTRATION → Sisyphus

Delegation prompt = 6 sections:
  1. Task Brief (what/why/scope)
  2. Context (files/patterns/conventions)
  3. Technical Spec (interfaces/I-O/errors/edges)
  4. Constraints (do-not/must-use/perf/security)
  5. Acceptance Criteria (testable checkboxes)
  6. Verification (commands/expected/evidence)

Quality gates = G1-G8:
  G1: Lint | G2: Types | G3: Format | G4: Tests
  G5: Secrets | G6: Placeholders | G7: Oracle | G8: Momus

Fallback = 4 attempts max:
  1. Original → 2. Error context → 3. Oracle guidance → 4. Reduced scope → USER

Parallel = max 3 concurrent Hephaestus tasks
  No file overlap between parallel tasks
  Sync barrier after all complete
```

---

**Document Version**: 1.0
**Created**: 2026-04-05
**Status**: READY FOR REVIEW
**Author**: Sisyphus (opencode/qwen3.6-plus-free)
