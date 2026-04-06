# Secret Management Masterplan — Industry Gold Standard

## TL;DR

> **Quick Summary**: Migrate all hardcoded API keys to a proper secret management system with .env architecture, pre-commit scanning, automated rotation, and zero-secrets-in-config policy.
> 
> **Deliverables**:
> - `.env` architecture for project + global configs
> - Pre-commit secret scanning (gitleaks)
> - Secret rotation workflow
> - `.env.example` templates for all services
> - Documentation for secret management workflow
> 
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Audit → .env migration → Pre-commit hooks → Rotation

---

## Context

### Original Request
"what would be industry gold standard to adress hardcoded apis?" → "masterplan a proper industry gold standard"

### Current State
- **Global config** (`~/.config/opencode/opencode.json`) has 3 hardcoded API keys:
  - OpenCode API key
  - OpenRouter API key  
  - Google API key
- **Project config** (`opencode.json`) uses `${GITHUB_PERSONAL_ACCESS_TOKEN}` env var interpolation — correct pattern
- **Project `.env`** exists with `GITHUB_PERSONAL_ACCESS_TOKEN` — correct pattern
- **`.gitignore`** blocks `.env` files — correct pattern
- **No pre-commit secret scanning** — gap
- **No key rotation strategy** — gap
- **No `.env.example` templates** — gap

### Industry Standards Referenced
- OWASP Secret Management Cheat Sheet
- 12-Factor App Config methodology
- HashiCorp Vault patterns (adapted for solo dev)
- GitHub secret scanning patterns
- Pre-commit hooks ecosystem

---

## Work Objectives

### Core Objective
Eliminate all hardcoded secrets from config files and implement a defense-in-depth secret management system that prevents future leaks.

### Concrete Deliverables
- `.env` file for global OpenCode config
- `.env.example` templates for project + global
- Pre-commit hook with gitleaks
- Secret rotation documentation
- Updated config files with `${VAR}` interpolation
- Migration script for existing secrets

### Definition of Done
- [ ] Zero hardcoded secrets in any `.json`, `.yaml`, `.yml`, `.py`, `.sh` file
- [ ] All secrets sourced from `.env` files or environment variables
- [ ] Pre-commit hook blocks commits with secrets
- [ ] `.env.example` templates exist for all services
- [ ] Rotation workflow documented and tested
- [ ] `.gitignore` covers all secret file patterns

### Must Have
- All API keys in `.env` files (gitignored)
- Config files use `${VAR}` interpolation
- Pre-commit secret scanning
- `.env.example` templates with dummy values
- Migration script that preserves existing functionality

### Must NOT Have (Guardrails)
- No secrets in git history (if found, must be rotated, not just removed)
- No secrets in `.md` documentation files
- No secrets in commit messages
- No secrets in environment variable defaults (e.g., `${VAR:-default_key}`)
- No backup files with secrets (`.bak`, `.old`, `.backup`)

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: NO
- **Automated tests**: NO
- **Agent-Executed QA**: ALWAYS (mandatory for all tasks)

### QA Policy
Every task MUST include agent-executed QA scenarios.

- **Pre-commit hooks**: Bash — commit test file with secret, verify hook blocks it
- **.env files**: Bash — source .env, verify vars are set, verify .gitignore blocks commit
- **Config interpolation**: Bash — run opencode with .env sourced, verify it starts
- **Secret scanning**: Bash — run gitleaks scan, verify zero findings

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — audit + templates):
├── Task 1: Secret audit + inventory [quick]
├── Task 2: Create .env architecture [quick]
├── Task 3: Create .env.example templates [quick]
└── Task 4: Update config files to use ${VAR} [quick]

Wave 2 (After Wave 1 — scanning + rotation):
├── Task 5: Install + configure gitleaks pre-commit hook [quick]
├── Task 6: Create secret rotation workflow [quick]
└── Task 7: Create migration script [quick]

Wave 3 (After Wave 2 — cleanup + verification):
├── Task 8: Rotate all exposed secrets [deep]
├── Task 9: Clean git history of secrets [deep]
└── Task 10: Final verification + documentation [quick]

Wave FINAL (After ALL tasks — parallel review):
├── Task F1: Secret audit verification (oracle)
├── Task F2: Pre-commit hook test (quick)
├── Task F3: Config functionality test (quick)
└── Task F4: Documentation review (quick)
-> Present results -> Get explicit user okay

Critical Path: Task 1 → Task 2 → Task 4 → Task 5 → Task 8 → Task 9 → F1-F4 → user okay
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 4 (Waves 1 & 2)
```

---

## TODOs

- [ ] 1. Secret Audit + Inventory

  **What to do**:
  - Run comprehensive secret scan across entire workspace
  - Inventory all found secrets with: file, line, type, provider, severity
  - Check git history for previously committed secrets
  - Classify each secret: active, test, expired, dummy
  - Create secret inventory table

  **Must NOT do**:
  - Do NOT rotate keys yet (just inventory)
  - Do NOT commit any findings that include actual secrets
  - Do NOT modify any files

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Pattern matching and grep operations, no complex logic
  - **Skills**: `[]`
    - No special skills needed — pure file scanning

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4)
  - **Blocks**: Tasks 2, 4, 8, 9
  - **Blocked By**: None

  **References**:
  - `~/.config/opencode/opencode.json` — Known to have 3 hardcoded keys
  - `opencode.json` — Uses correct ${VAR} pattern (reference for migration target)
  - `.gitignore` — Check what's already excluded

  **Acceptance Criteria**:
  - [ ] Complete inventory table with all secrets found
  - [ ] Git history check for previously committed secrets
  - [ ] Severity classification for each secret

  **QA Scenarios**:

  ```
  Scenario: Secret scan finds all known secrets
    Tool: Bash (grep)
    Preconditions: Known secrets exist in ~/.config/opencode/opencode.json
    Steps:
      1. grep -rn "sk-[a-zA-Z0-9]\{20,\}" ~/.config/opencode/
      2. grep -rn "AIza[a-zA-Z0-9_-]\{30,\}" ~/.config/opencode/
      3. Verify both patterns match expected lines
    Expected Result: All 3 known API keys found with file:line references
    Evidence: .sisyphus/evidence/task-1-secret-scan.txt
  ```

  **Commit**: NO (audit only, no changes)

---

- [ ] 2. Create .env Architecture

  **What to do**:
  - Create `~/.config/opencode/.env` with all 3 API keys migrated from opencode.json
  - Create `~/N-Xyme_MIND/.env.example` template (project level)
  - Create `~/.config/opencode/.env.example` template (global level)
  - Update `.gitignore` to ensure all `.env*` patterns are covered
  - Set proper file permissions (600) on all .env files

  **Must NOT do**:
  - Do NOT commit .env files
  - Do NOT include real keys in .env.example files
  - Do NOT change file ownership

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple file creation and permission changes
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4)
  - **Blocks**: Tasks 4, 5, 8
  - **Blocked By**: Task 1 (needs inventory)

  **References**:
  - `~/.config/opencode/opencode.json` — Source of hardcoded keys to migrate
  - `~/N-Xyme_MIND/.env` — Existing .env file (reference for format)
  - `.gitignore` — Current exclusion patterns

  **Acceptance Criteria**:
  - [ ] `~/.config/opencode/.env` exists with 3 API keys, permissions 600
  - [ ] `~/N-Xyme_MIND/.env.example` exists with dummy values
  - [ ] `~/.config/opencode/.env.example` exists with dummy values
  - [ ] `.gitignore` covers `.env`, `.env.*`, `*.env`, `*.env.*`

  **QA Scenarios**:

  ```
  Scenario: .env files have correct permissions
    Tool: Bash (stat)
    Preconditions: .env files created
    Steps:
      1. stat -c "%a" ~/.config/opencode/.env
      2. stat -c "%a" ~/N-Xyme_MIND/.env
    Expected Result: Both return "600"
    Evidence: .sisyphus/evidence/task-2-env-permissions.txt

  Scenario: .env files are gitignored
    Tool: Bash (git check-ignore)
    Preconditions: .env files exist
    Steps:
      1. git check-ignore ~/N-Xyme_MIND/.env
      2. Verify exit code 0 (file is ignored)
    Expected Result: git check-ignore returns the file path (exit code 0)
    Evidence: .sisyphus/evidence/task-2-env-gitignore.txt
  ```

  **Commit**: YES (groups with 3)
  - Message: `chore(security): add .env architecture and templates`
  - Files: `.env.example`, `.gitignore`
  - Pre-commit: `git check-ignore .env`

---

- [ ] 3. Create .env.example Templates

  **What to do**:
  - Create project-level `.env.example` with all required variables
  - Create global-level `.env.example` with all required variables
  - Include comments explaining each variable's purpose
  - Use dummy/placeholder values (never real keys)
  - Include setup instructions in comments

  **Must NOT do**:
  - Do NOT include real API keys
  - Do NOT include real tokens
  - Do NOT leave variables without example values

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Template file creation
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4)
  - **Blocks**: None
  - **Blocked By**: Task 1 (needs inventory)

  **References**:
  - `~/N-Xyme_MIND/.env` — Current project .env (reference for variable names)
  - `~/.config/opencode/opencode.json` — Global config (reference for variable names)

  **Acceptance Criteria**:
  - [ ] `.env.example` has all variables with dummy values
  - [ ] Each variable has a comment explaining its purpose
  - [ ] No real secrets in example files

  **QA Scenarios**:

  ```
  Scenario: .env.example has no real secrets
    Tool: Bash (grep)
    Preconditions: .env.example files created
    Steps:
      1. grep -E "sk-|AIza|ghp_|AKIA" .env.example
      2. Verify no matches found
    Expected Result: grep returns no matches (exit code 1)
    Evidence: .sisyphus/evidence/task-3-no-secrets-in-example.txt
  ```

  **Commit**: YES (groups with 2)

---

- [ ] 4. Update Config Files to Use ${VAR} Interpolation

  **What to do**:
  - Update `~/.config/opencode/opencode.json` to remove hardcoded API keys
  - Replace with `${VAR}` syntax or remove provider section entirely (OpenCode reads env vars automatically)
  - Verify OpenCode still starts correctly after changes
  - Update any other config files with hardcoded secrets

  **Must NOT do**:
  - Do NOT break OpenCode startup
  - Do NOT remove provider configuration entirely if needed
  - Do NOT commit changes before testing

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: JSON editing, simple substitutions
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3)
  - **Blocks**: Tasks 5, 8
  - **Blocked By**: Tasks 1, 2 (needs inventory + .env created)

  **References**:
  - `~/.config/opencode/opencode.json` — Target file for secret removal
  - `~/N-Xyme_MIND/opencode.json` — Reference for correct ${VAR} pattern
  - OpenCode docs: env var interpolation in config files

  **Acceptance Criteria**:
  - [ ] No hardcoded API keys in any .json config file
  - [ ] OpenCode starts successfully after changes
  - [ ] All MCPs still connect correctly

  **QA Scenarios**:

  ```
  Scenario: No hardcoded secrets remain in config
    Tool: Bash (grep)
    Preconditions: Config files updated
    Steps:
      1. grep -E "sk-[a-zA-Z0-9]{20,}|AIza[a-zA-Z0-9_-]{30,}" ~/.config/opencode/opencode.json
      2. Verify no matches
    Expected Result: grep returns no matches (exit code 1)
    Evidence: .sisyphus/evidence/task-4-no-secrets-in-config.txt

  Scenario: OpenCode starts with env-based config
    Tool: Bash
    Preconditions: .env sourced, config updated
    Steps:
      1. source ~/.config/opencode/.env
      2. opencode --version (or equivalent startup test)
    Expected Result: OpenCode starts without errors
    Evidence: .sisyphus/evidence/task-4-opencode-starts.txt
  ```

  **Commit**: YES (groups with 2, 3)

---

- [ ] 5. Install + Configure Gitleaks Pre-commit Hook

  **What to do**:
  - Install gitleaks (via pip or binary)
  - Create `.gitleaks.toml` config file with custom rules
  - Add pre-commit hook to `.git/hooks/pre-commit`
  - Test hook by attempting to commit a file with a fake secret
  - Verify hook blocks the commit and reports the secret

  **Must NOT do**:
  - Do NOT install gitleaks globally if project-local is sufficient
  - Do NOT use overly aggressive rules that block legitimate code
  - Do NOT skip testing the hook

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Tool installation and hook configuration
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7)
  - **Blocks**: None
  - **Blocked By**: Task 4 (config must be clean first)

  **References**:
  - gitleaks docs: https://github.com/gitleaks/gitleaks
  - pre-commit.com docs: https://pre-commit.com/
  - `.git/hooks/pre-commit` — Hook location

  **Acceptance Criteria**:
  - [ ] gitleaks installed and accessible
  - [ ] `.gitleaks.toml` config file created
  - [ ] Pre-commit hook installed and executable
  - [ ] Hook blocks commits with secrets
  - [ ] Hook allows clean commits

  **QA Scenarios**:

  ```
  Scenario: Pre-commit hook blocks secret commit
    Tool: Bash (git)
    Preconditions: Pre-commit hook installed
    Steps:
      1. echo "API_KEY=sk-fake12345678901234567890" > test-secret.txt
      2. git add test-secret.txt
      3. git commit -m "test: should be blocked"
      4. Verify commit fails with gitleaks error
    Expected Result: git commit fails with "secret detected" message
    Evidence: .sisyphus/evidence/task-5-hook-blocks-secret.txt

  Scenario: Pre-commit hook allows clean commit
    Tool: Bash (git)
    Preconditions: Pre-commit hook installed
    Steps:
      1. echo "clean file" > test-clean.txt
      2. git add test-clean.txt
      3. git commit -m "test: should pass"
      4. Verify commit succeeds
    Expected Result: git commit succeeds
    Evidence: .sisyphus/evidence/task-5-hook-allows-clean.txt
  ```

  **Commit**: YES (groups with 6, 7)
  - Message: `chore(security): add gitleaks pre-commit hook`
  - Files: `.gitleaks.toml`, `.git/hooks/pre-commit`

---

- [ ] 6. Create Secret Rotation Workflow

  **What to do**:
  - Document rotation schedule for each secret type
  - Create rotation script template
  - Document step-by-step rotation process
  - Include rollback procedure
  - Set up calendar reminders (or cron-based rotation)

  **Must NOT do**:
  - Do NOT automate rotation without manual approval step
  - Do NOT store old secrets in plaintext
  - Do NOT rotate keys that are actively in use without coordination

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Documentation and script templates
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 7)
  - **Blocks**: None
  - **Blocked By**: Task 1 (needs inventory)

  **References**:
  - OWASP Secret Management: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html
  - 12-Factor App Config: https://12factor.net/config

  **Acceptance Criteria**:
  - [ ] Rotation schedule documented for each secret type
  - [ ] Rotation script template created
  - [ ] Rollback procedure documented
  - [ ] Calendar/cron reminder configured

  **QA Scenarios**:

  ```
  Scenario: Rotation workflow is documented
    Tool: Bash (file check)
    Preconditions: Documentation created
    Steps:
      1. Check rotation-doc.md exists
      2. Verify it covers all 3 API key types
      3. Verify rollback procedure is included
    Expected Result: File exists with all required sections
    Evidence: .sisyphus/evidence/task-6-rotation-doc.txt
  ```

  **Commit**: YES (groups with 5, 7)

---

- [ ] 7. Create Migration Script

  **What to do**:
  - Create `bin/migrate-secrets.sh` that:
    - Reads existing hardcoded keys from config files
    - Writes them to appropriate .env files
    - Updates config files to use ${VAR} interpolation
    - Backs up original config files
    - Validates migration succeeded
  - Make script idempotent (safe to run multiple times)
  - Test script on a copy of config files

  **Must NOT do**:
  - Do NOT run script on production configs without backup
  - Do NOT delete original configs until migration verified
  - Do NOT commit the script with test secrets

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Shell script creation
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6)
  - **Blocks**: Task 8
  - **Blocked By**: Tasks 1, 2, 4

  **References**:
  - `~/.config/opencode/opencode.json` — Source config
  - `~/N-Xyme_MIND/opencode.json` — Reference for ${VAR} pattern
  - `env.sh` — Reference for env var loading pattern

  **Acceptance Criteria**:
  - [ ] Script extracts secrets from config files
  - [ ] Script writes secrets to .env files
  - [ ] Script updates config files to use ${VAR}
  - [ ] Script creates backups of original files
  - [ ] Script validates migration succeeded
  - [ ] Script is idempotent

  **QA Scenarios**:

  ```
  Scenario: Migration script runs successfully
    Tool: Bash
    Preconditions: Config files have hardcoded secrets, .env files don't exist
    Steps:
      1. cp config files to temp location
      2. Run bin/migrate-secrets.sh on temp configs
      3. Verify .env files created with correct values
      4. Verify config files no longer have hardcoded secrets
    Expected Result: Migration completes with zero errors
    Evidence: .sisyphus/evidence/task-7-migration-success.txt
  ```

  **Commit**: YES (groups with 5, 6)

---

- [ ] 8. Rotate All Exposed Secrets

  **What to do**:
  - Rotate OpenCode API key (generate new key, update .env)
  - Rotate OpenRouter API key (generate new key, update .env)
  - Rotate Google API key (generate new key, update .env)
  - Verify all services work with new keys
  - Document rotation in changelog

  **Must NOT do**:
  - Do NOT rotate without having new keys ready
  - Do NOT delete old keys until new ones verified
  - Do NOT commit new keys to any file

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Requires coordination across multiple services, verification steps
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (sequential)
  - **Blocks**: Task 9
  - **Blocked By**: Tasks 4, 5, 7

  **References**:
  - OpenCode dashboard: API key management
  - OpenRouter dashboard: https://openrouter.ai/keys
  - Google Cloud Console: https://console.cloud.google.com/apis/credentials

  **Acceptance Criteria**:
  - [ ] All 3 API keys rotated
  - [ ] New keys work in .env files
  - [ ] Old keys are revoked
  - [ ] All services verified working with new keys

  **QA Scenarios**:

  ```
  Scenario: New API keys work after rotation
    Tool: Bash
    Preconditions: New keys in .env, old keys revoked
    Steps:
      1. source .env
      2. Test OpenCode connectivity
      3. Test OpenRouter connectivity
      4. Test Google API connectivity
    Expected Result: All services respond successfully
    Evidence: .sisyphus/evidence/task-8-keys-work.txt
  ```

  **Commit**: NO (secrets should never be committed)

---

- [ ] 9. Clean Git History of Secrets

  **What to do**:
  - Check git history for any previously committed secrets
  - If found, use `git filter-repo` or `BFG Repo-Cleaner` to remove them
  - Force push cleaned history (if applicable)
  - Verify no secrets remain in any commit

  **Must NOT do**:
  - Do NOT rewrite history without backup
  - Do NOT force push without understanding implications
  - Do NOT skip verification after cleanup

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Git history rewriting is risky and requires careful verification
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (sequential)
  - **Blocks**: None
  - **Blocked By**: Task 8

  **References**:
  - git-filter-repo: https://github.com/newren/git-filter-repo
  - BFG Repo-Cleaner: https://rtyley.github.io/bfg-repo-cleaner/

  **Acceptance Criteria**:
  - [ ] Git history scanned for secrets
  - [ ] Any found secrets removed from history
  - [ ] Verification scan shows zero secrets in any commit
  - [ ] Repository still functional after cleanup

  **QA Scenarios**:

  ```
  Scenario: Git history is clean of secrets
    Tool: Bash (gitleaks)
    Preconditions: History cleanup completed
    Steps:
      1. gitleaks detect --source . --verbose
      2. Verify zero findings
    Expected Result: gitleaks reports "no leaks found"
    Evidence: .sisyphus/evidence/task-9-history-clean.txt
  ```

  **Commit**: YES (after cleanup)
  - Message: `chore(security): clean git history of exposed secrets`

---

- [ ] 10. Final Verification + Documentation

  **What to do**:
  - Run full secret scan across workspace
  - Verify all .env files exist and have correct permissions
  - Verify all config files use ${VAR} interpolation
  - Verify pre-commit hook works
  - Create documentation for secret management workflow
  - Update AGENTS.md with secret management rules

  **Must NOT do**:
  - Do NOT skip any verification step
  - Do NOT document real secrets

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Verification and documentation
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 9)
  - **Blocks**: None
  - **Blocked By**: Tasks 8, 9

  **References**:
  - `AGENTS.md` — Add secret management rules
  - `.gitleaks.toml` — Verify config
  - All .env files — Verify permissions

  **Acceptance Criteria**:
  - [ ] Full secret scan passes with zero findings
  - [ ] All .env files have 600 permissions
  - [ ] All config files use ${VAR} interpolation
  - [ ] Pre-commit hook blocks secret commits
  - [ ] Documentation created and reviewed

  **QA Scenarios**:

  ```
  Scenario: Full workspace secret scan passes
    Tool: Bash (gitleaks + grep)
    Preconditions: All migration and rotation complete
    Steps:
      1. gitleaks detect --source . --verbose
      2. grep -rn "sk-[a-zA-Z0-9]\{20,\}" --include="*.json" --include="*.yaml" --include="*.py" .
      3. grep -rn "AIza[a-zA-Z0-9_-]\{30,\}" --include="*.json" --include="*.yaml" --include="*.py" .
    Expected Result: All scans return zero findings
    Evidence: .sisyphus/evidence/task-10-full-scan.txt
  ```

  **Commit**: YES
  - Message: `docs(security): add secret management documentation`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

- [ ] F1. **Secret Audit Verification** — `oracle`
  Scan entire workspace for any remaining hardcoded secrets. Check all config files, scripts, docs, and git history. Verify .env files exist with correct permissions. Verify .gitignore covers all secret patterns.
  Output: `Secrets Found: [0/N] | .env Files: [N/N] | Permissions: [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Pre-commit Hook Test** — `quick`
  Attempt to commit a file with a fake secret. Verify hook blocks it. Attempt to commit a clean file. Verify hook allows it.
  Output: `Block Test: [PASS/FAIL] | Allow Test: [PASS/FAIL] | VERDICT`

- [ ] F3. **Config Functionality Test** — `quick`
  Source .env files. Start OpenCode. Verify all MCPs connect. Verify all agents work. Verify no startup errors.
  Output: `OpenCode: [PASS/FAIL] | MCPs: [N/N] | Agents: [N/N] | VERDICT`

- [ ] F4. **Documentation Review** — `quick`
  Verify rotation workflow documented. Verify .env.example templates exist. Verify AGENTS.md updated. Verify no real secrets in docs.
  Output: `Rotation Doc: [YES/NO] | Templates: [N/N] | AGENTS.md: [YES/NO] | Secrets in Docs: [0/N] | VERDICT`

---

## Commit Strategy

- **2-4**: `chore(security): add .env architecture and templates` — .env.example, .gitignore
- **5-7**: `chore(security): add gitleaks pre-commit hook` — .gitleaks.toml, pre-commit hook
- **9**: `chore(security): clean git history of exposed secrets` — git filter-repo
- **10**: `docs(security): add secret management documentation` — docs, AGENTS.md

---

## Success Criteria

### Verification Commands
```bash
# Zero secrets in workspace
gitleaks detect --source . --verbose  # Expected: no leaks found

# .env files exist and are protected
stat -c "%a" .env  # Expected: 600
stat -c "%a" ~/.config/opencode/.env  # Expected: 600

# Config files have no hardcoded secrets
grep -rn "sk-[a-zA-Z0-9]\{20,\}" --include="*.json" .  # Expected: no matches

# Pre-commit hook works
git commit with secret → blocked
git commit without secret → allowed
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] Zero hardcoded secrets in any file
- [ ] All .env files have 600 permissions
- [ ] Pre-commit hook blocks secret commits
- [ ] Rotation workflow documented
- [ ] .env.example templates exist
- [ ] Git history clean of secrets
