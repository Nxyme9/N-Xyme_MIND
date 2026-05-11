# Step 4: Quality Gates

**Goal:** Run quality gates on all agent outputs to ensure code quality and security

---

## Quality Gate Definitions

### Gate 1: Type Check
- **Tool:** TypeScript/JavaScript type checking
- **Pass:** 0 type errors
- **Fail:** Any type error

### Gate 2: Lint
- **Tool:** ESLint, Pylint, or language-specific linter
- **Pass:** 0 errors, warnings allowed
- **Fail:** Any error

### Gate 3: Format
- **Tool:** Prettier, Black, or language formatter
- **Pass:** No formatting changes needed
- **Fail:** Files would be reformatted

### Gate 4: Tests
- **Tool:** Jest, Pytest, or language test runner
- **Pass:** All tests pass (or pre-existing failures noted)
- **Fail:** New test failures

### Gate 5: Secrets Scan
- **Tool:** Secret scanning (git-secrets, detect-secrets)
- **Pass:** No secrets detected
- **Fail:** Any secret detected

### Gate 6: Placeholder Check
- **Tool:** Custom placeholder detection
- **Pass:** No TODOs, FIXMEs, or placeholders
- **Fail:** Any placeholder found

### Gate 7: Agent Call Validation
- **Tool:** BMAD agent call validation
- **Pass:** All agent calls follow spec
- **Fail:** Invalid agent calls

### Gate 8: Security Paths
- **Tool:** Security-sensitive path check
- **Pass:** No security-sensitive paths modified without review
- **Fail:** Security paths modified without Oracle review

---

## Execution

<step n="4.1" goal="Identify output files to validate">
<action>Collect all files modified by delegated agents</action>
<action>Filter by file type for appropriate gates</action>
<action>Store as {{files_to_validate}}</action>
</step>

<step n="4.2" goal="Run quality gates">
<action>For each gate, execute appropriate validation</action>
<action>Record pass/fail status for each file</action>
<action>Log gate results</action>
</step>

<step n="4.3" goal="Handle failures">
<action>If any gate fails, collect error output</action>
<action>Log failures to .sisyphus/quality-gates-failures.json</action>
<action>Report failures to user with fix suggestions</action>
<action>Do NOT auto-fix - let user decide</action>
</step>

<step n="4.4" goal="Aggregate quality metrics">
<action>Count passes and failures per gate</action>
<action>Calculate overall quality score</action>
<action>Store as {{quality_metrics}}</action>
</step>

---

## Gate Scripts

Quality gates use scripts from {project-root}/bin/quality-gates/:

```bash
# Run all gates
./bin/quality-gates/gate-1-typecheck.sh
./bin/quality-gates/gate-2-lint.sh
./bin/quality-gates/gate-3-format.sh
./bin/quality-gates/gate-4-test.sh
./bin/quality-gates/gate-5-secrets.sh
./bin/quality-gates/gate-6-placeholders.sh
./bin/quality-gates/gate-7-agent-call-check.sh
./bin/quality-gates/gate-8-security-paths.sh
```

---

## Output

- **quality_metrics:**
  - gates_passed: [list]
  - gates_failed: [list]
  - files_checked: number
  - errors_found: number
  - overall_score: percentage
- **quality_gate_results:** {gate: {status, files, errors}}