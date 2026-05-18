# Step 1: Parallel Review

## MANDATORY EXECUTION RULES:
- Run Oracle + Momus in parallel
- Collect findings from both
- Merge into unified report
- Log failures to Graphiti

## EXECUTION:

### 1. Launch Parallel Reviews
```
Oracle: Architecture review (cloud model)
Momus: Plan quality review (local model)
```

### 2. Oracle Review Scope
- Architecture decisions valid?
- Security concerns addressed?
- Scalability considered?
- Technical debt identified?

### 3. Momus Review Scope
- Requirements complete?
- Acceptance criteria clear?
- Dependencies identified?
- Risks documented?

### 4. Merge Findings
```
📋 Review Report:

🏗️ Architecture (Oracle):
- [Finding 1]
- [Finding 2]

📝 Plan Quality (Momus):
- [Finding 1]
- [Finding 2]

VERDICT: [PASS/FAIL/CONDITIONAL]
```

### 5. Log to Graphiti
Store review findings as episodes for future reference.
