# MCP Recovery Plan — Post-CachyOS Reinstall

## TL;DR

> **Quick Summary**: After CachyOS reinstall, all Python-based MCPs are broken (Python 3.14 + contaminated venv + package version conflicts). Install Node.js for npm-based MCPs, `uv` for isolated Python MCPs (git, serena, hindsight), and Ollama for local LLM. Keep existing Go binary (github) and remote (context7).
> 
> **Deliverables**: 
> - Node.js + npm installed via pacman
> - `uv`/`uvx` installed for isolated Python MCP execution
> - Ollama installed for local LLM
> - opencode.json updated with npm/uvx commands (zero venv references)
> - All 8 MCP servers verified working
> 
> **Estimated Effort**: Medium
> **Parallel Execution**: YES — 3 waves
> **Critical Path**: Install runtimes → Update MCP configs → Test each server

---

## Context

### Original Request
User reinstalled CachyOS, barely recovered workspace data. Most MCPs are misconfigured/broken. User wants "zero Python" — but 3 MCPs (git, serena, hindsight) have NO npm alternative and require `uvx` (isolated Python runner, no venv contamination).

### Root Cause Analysis
- **Python 3.14** installed — `pydantic.v1` incompatible, cascades to break `anthropic`, `serena`, `mcp`, `fastmcp`
- **Venv contaminated** — pip shebangs reference old path `/run/media/liveuser/ecff8b13-ced1-4882-9058-ae48f125f200/@home/nxyme/...`
- **mcp package v1.26.0** — `ExperimentalClientFeatures` import error breaks `sequential-thinking`, `fastmcp`
- **Node.js missing** — no npm/npx available
- **Ollama missing** — hindsight and memory LLM features need local Ollama

### Research Findings (Librarian Agent — verified)
| Server | npm Package | Version | Notes |
|--------|-------------|---------|-------|
| sequential-thinking | `@modelcontextprotocol/server-sequential-thinking` | 0.6.2 | ✅ npm exists |
| memory | `@modelcontextprotocol/server-memory` | 0.6.3 | ✅ npm exists |
| git | ❌ NO npm package | — | Python only: `mcp-server-git` via uvx |
| serena | ❌ NO npm package | — | Python only: `serena` via uvx |
| github | Go binary | — | Already works at `bin/github-mcp-server` |
| context7 | Remote SSE | — | Already works at `mcp.context7.com` |
| athena | ❌ NO npm package | — | Custom, disable for now |
| hindsight | ❌ NO npm package | — | Custom, needs uvx + Ollama |

**Key insight**: `uvx` runs Python packages in isolated environments — no venv contamination, no pip needed. Install `uv` via pacman alongside Node.js.

---

## Work Objectives

### Core Objective
Replace all broken Python MCP servers with npm/uvx equivalents and verify all 8 MCPs work.

### Concrete Deliverables
1. Node.js installed (`node --version`, `npx --version`)
2. `uv` installed (`uvx --version`)
3. Ollama installed and running (`ollama list`)
4. `config/opencode.json` updated — zero venv references
5. `.opencode/data` directory created for memory MCP
6. All 8 MCP servers configured and testable

### Definition of Done
- [ ] `node --version` returns v20+ or v22+
- [ ] `npx --version` returns 10+
- [ ] `uvx --version` returns version
- [ ] `ollama list` works without error
- [ ] `python3 -m json.tool config/opencode.json` validates JSON
- [ ] Zero `./athena/.venv/bin/python` references in config
- [ ] All 8 MCP servers have config entries

### Must Have
- All 8 MCP servers configured (enabled or disabled with reason)
- No Python venv references in any MCP command
- Global memory MCP working (explicitly required by user)
- JSON config valid
- `uvx` available for git, serena, hindsight

### Must NOT Have
- No `./athena/.venv/bin/python` references in MCP commands
- No commented-out MCP entries
- No broken pip/package imports

---

## Execution Strategy

### Wave 1: Install Runtimes (sequential — needs sudo)
```
Task 1: Install Node.js + uv via pacman (nodejs npm uv)
Task 2: Install Ollama via AUR (paru -S ollama)
Task 3: Create missing directories (.opencode/data, .sisyphus/evidence)
```

### Wave 2: Update MCP Config (after runtimes installed)
```
Task 4: Update opencode.json — replace Python MCPs with npx/uvx equivalents
Task 5: Update .env with placeholder entries
```

### Wave 3: Verify All MCPs
```
Task 6: Test each MCP server individually
```

---

## TODOs

- [ ] 1. Install Node.js + uv via pacman

  **What to do**:
  - Run `sudo pacman -S nodejs npm` to install Node.js and npm
  - Run `sudo pacman -S uv` to install `uv` (Python package manager — provides `uvx` for isolated Python MCP execution)
  - Verify: `node --version`, `npx --version`, `uvx --version`
  - CachyOS repos should have current LTS Node.js and `uv`

  **Must NOT do**:
  - Install via nvm/fnm (adds complexity, user wants simple)
  - Install bun (broken, can fix later)
  - Fix the existing Python venv (we're bypassing it entirely)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Two pacman commands + verification

  **Parallelization**:
  - **Can Run In Parallel**: NO (needs sudo)
  - **Parallel Group**: Wave 1 (sequential with Task 2, 3)
  - **Blocks**: Task 4 (need npx and uvx available)
  - **Blocked By**: None

  **References**:
  - CachyOS is Arch-based — `pacman -S nodejs npm uv` is the standard install
  - `uv` provides `uvx` which runs Python packages in isolated environments (no venv contamination)
  - AGENTS.md § "Schema Safety Protocol" — system-level config change

  **Acceptance Criteria**:
  - [ ] `node --version` returns v20+ or v22+
  - [ ] `npx --version` returns 10+ 
  - [ ] `uvx --version` returns version
  - [ ] `which node` returns `/usr/bin/node`
  - [ ] `which uvx` returns path

  **QA Scenarios**:
  ```
  Scenario: Node.js installation verification
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: node --version
      2. Assert: output matches "v\d+\.\d+\.\d+"
      3. Run: npx --version
      4. Assert: output matches "\d+\.\d+\.\d+"
    Expected Result: Both commands return valid version strings
    Failure Indicators: "command not found" or version < v20
    Evidence: .sisyphus/evidence/task-1-node-install.txt

  Scenario: uv/uvx installation verification
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: uvx --version
      2. Assert: output contains version number
      3. Run: which uvx
      4. Assert: returns a valid path
    Expected Result: uvx available and responds
    Failure Indicators: "command not found"
    Evidence: .sisyphus/evidence/task-1-uv-install.txt
  ```

  **Commit**: NO

---

- [ ] 2. Install Ollama via AUR

  **What to do**:
  - Run `paru -S ollama` (CachyOS has paru AUR helper)
  - Enable and start service: `sudo systemctl enable --now ollama`
  - Verify: `ollama list` (should return empty list or error about no models)
  - Pull at least one model for testing: `ollama pull qwen2.5:3b` (small model for testing)

  **Must NOT do**:
  - Install via curl script (paru is available and cleaner)
  - Pull large models initially (just need one small one for testing)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: AUR install + service start

  **Parallelization**:
  - **Can Run In Parallel**: NO (needs sudo)
  - **Parallel Group**: Wave 1 (sequential with Task 1, 3)
  - **Blocks**: Task 6 (testing hindsight/memory)
  - **Blocked By**: None

  **References**:
  - Ollama Arch wiki: https://wiki.archlinux.org/title/Ollama
  - hindsight_mcp.py lines 8-10 — needs `qwen2.5:14b` model at `localhost:11434`

  **Acceptance Criteria**:
  - [ ] `systemctl status ollama` shows active (running)
  - [ ] `curl -s http://localhost:11434/api/tags` returns valid JSON
  - [ ] `ollama list` works without error

  **QA Scenarios**:
  ```
  Scenario: Ollama service running
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: systemctl is-active ollama
      2. Assert: output is "active"
      3. Run: curl -s http://localhost:11434/api/tags
      4. Assert: output contains "models"
    Expected Result: Service running, API responds
    Failure Indicators: "inactive" or connection refused
    Evidence: .sisyphus/evidence/task-2-ollama-status.txt
  ```

  **Commit**: NO

---

- [ ] 3. Create missing directories

  **What to do**:
  - `mkdir -p .opencode/data` — memory MCP data directory
  - `mkdir -p .sisyphus/evidence` — QA evidence directory (if missing)
  - Verify directories exist

  **Must NOT do**:
  - Delete any existing data
  - Change permissions on existing directories

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Two mkdir commands

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: Task 6 (memory MCP needs .opencode/data)
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] `.opencode/data` exists
  - [ ] `.sisyphus/evidence` exists

  **QA Scenarios**:
  ```
  Scenario: Directories created
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: ls -d .opencode/data .sisyphus/evidence
      2. Assert: both paths listed
    Expected Result: Both directories exist
    Failure Indicators: "No such file or directory"
    Evidence: .sisyphus/evidence/task-3-dirs.txt
  ```

  **Commit**: NO

---

- [ ] 4. Update opencode.json — replace Python MCPs with npm/uvx equivalents

  **What to do**:
  - Edit `config/opencode.json` MCP section
  - Replace each Python MCP command with npm/uvx/binary equivalent:

  **Verified Replacement Mapping:**

  | MCP | Current (broken Python) | Replacement | Type |
  |-----|------------------------|-------------|------|
  | `memory` | `./athena/.venv/bin/python -m mcp_memory_service.server` | `npx -y @modelcontextprotocol/server-memory` | npm ✅ |
  | `sequential-thinking` | `./athena/.venv/bin/python -m sequential_thinking` | `npx -y @modelcontextprotocol/server-sequential-thinking` | npm ✅ |
  | `git` | `./athena/.venv/bin/python -m mcp_server_git` | `uvx mcp-server-git --repository /home/n-xyme/nx_openmore` | uvx (no npm exists) |
  | `serena` | `./athena/.venv/bin/python -m serena.cli start-mcp-server` | `uvx --from git+https://github.com/oraios/serena serena start-mcp-server` | uvx (no npm exists) |
  | `hindsight` | `./athena/.venv/bin/python ./hindsight_mcp.py` | `uvx --from hindsight-all-slim python ./hindsight_mcp.py` | uvx (custom, needs Ollama) |
  | `athena` | `./athena/.venv/bin/python -m athena.mcp_server` | **DISABLE** (`enabled: false`) — no npm package, complex deps | disable |
  | `github` | `./bin/github-mcp-server stdio --toolsets all` | **KEEP AS-IS** (Go binary, works) | binary ✅ |
  | `context7` | Remote SSE URL | **KEEP AS-IS** (remote, works) | remote ✅ |

  **Config format for each npx/uvx server:**

  ```json
  "memory": {
    "type": "local",
    "command": ["npx", "-y", "@modelcontextprotocol/server-memory"],
    "environment": {
      "MEMORY_FILE_PATH": "/home/n-xyme/nx_openmore/.opencode/data/memory.jsonl"
    },
    "enabled": true,
    "timeout": 15000
  },
  "sequential-thinking": {
    "type": "local",
    "command": ["npx", "-y", "@modelcontextprotocol/server-sequential-thinking"],
    "environment": {
      "DISABLE_THOUGHT_LOGGING": "true"
    },
    "enabled": true,
    "timeout": 30000
  },
  "git": {
    "type": "local",
    "command": ["uvx", "mcp-server-git", "--repository", "/home/n-xyme/nx_openmore"],
    "enabled": true,
    "timeout": 15000
  },
  "serena": {
    "type": "local",
    "command": ["uvx", "--from", "git+https://github.com/oraios/serena", "serena", "start-mcp-server"],
    "enabled": true,
    "timeout": 60000
  }
  ```

  **Must NOT do**:
  - Remove any MCP entry entirely (disable with `enabled: false` instead)
  - Change environment variable names that are still needed
  - Break the JSON structure
  - Keep any `./athena/.venv/bin/python` references

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Reason**: Careful JSON editing with exact replacements, need to verify each command format matches opencode schema

  **Parallelization**:
  - **Can Run In Parallel**: NO (single file edit)
  - **Parallel Group**: Wave 2 (after runtimes installed)
  - **Blocks**: Task 6 (testing)
  - **Blocked By**: Task 1 (need npx + uvx available)

  **References**:
  - `config/opencode.json` — current MCP section (lines 8-102)
  - Librarian research results — verified npm package names and versions
  - `modelcontextprotocol/servers` GitHub repo — reference server names
  - AGENTS.md § "Schema Safety Protocol" — validate JSON before saving

  **Acceptance Criteria**:
  - [ ] `python3 -m json.tool config/opencode.json` validates without error
  - [ ] Zero `./athena/.venv/bin/python` references in config
  - [ ] All 8 MCP servers have entries (athena may be `enabled: false`)
  - [ ] `github` and `context7` unchanged (they work)
  - [ ] Memory MCP has `MEMORY_FILE_PATH` pointing to `.opencode/data/memory.jsonl`
  - [ ] Git MCP has `--repository` pointing to workspace root

  **QA Scenarios**:
  ```
  Scenario: JSON config valid
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python3 -m json.tool config/opencode.json > /dev/null
      2. Assert: exit code 0
    Expected Result: Valid JSON
    Failure Indicators: JSON parse error
    Evidence: .sisyphus/evidence/task-4-json-valid.txt

  Scenario: No Python venv references
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: grep -c "athena/.venv" config/opencode.json
      2. Assert: output is "0"
    Expected Result: Zero venv references remain
    Failure Indicators: Count > 0
    Evidence: .sisyphus/evidence/task-4-no-python.txt

  Scenario: All MCPs have entries
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python3 -c "import json; d=json.load(open('config/opencode.json')); print(len(d['mcp']))"
      2. Assert: output is "8"
    Expected Result: All 8 MCP servers configured
    Failure Indicators: Count < 8
    Evidence: .sisyphus/evidence/task-4-mcp-count.txt

  Scenario: Memory MCP configured with data path
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: python3 -c "import json; d=json.load(open('config/opencode.json')); print(d['mcp']['memory']['environment'].get('MEMORY_FILE_PATH',''))"
      2. Assert: output contains ".opencode/data"
    Expected Result: Memory MCP has data path configured
    Failure Indicators: Empty or wrong path
    Evidence: .sisyphus/evidence/task-4-memory-path.txt
  ```

  **Commit**: YES
  - Message: `fix(config): replace Python MCPs with npm/uvx equivalents`
  - Files: `config/opencode.json`

---

- [ ] 5. Update .env with placeholder entries

  **What to do**:
  - Add placeholder entries to `.env` for API keys the user needs to fill:
    - `OPENROUTER_API_KEY=` (empty, user fills later)
    - `GROQ_API_KEY=` (empty)
    - `CEREBRAS_API_KEY=` (empty)
    - `DEEPSEEK_API_KEY=` (empty)
  - Keep existing `GITHUB_PERSONAL_ACCESS_TOKEN`
  - Comment each with what it's for

  **Must NOT do**:
  - Put actual API key values (user said "will fix keys later")
  - Remove existing GITHUB_PERSONAL_ACCESS_TOKEN
  - Expose keys in logs

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Simple .env edit

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 4)
  - **Blocks**: None (providers work without keys, just rate-limited)
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] `.env` has all provider key placeholders
  - [ ] GITHUB_PERSONAL_ACCESS_TOKEN preserved

  **QA Scenarios**:
  ```
  Scenario: .env has all provider keys
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: grep -c "_KEY=" .env
      2. Assert: output >= 5
    Expected Result: All provider key entries present
    Failure Indicators: Missing entries
    Evidence: .sisyphus/evidence/task-5-env-keys.txt
  ```

  **Commit**: NO (sensitive file)

---

- [ ] 6. Test each MCP server individually

  **What to do**:
  - For each MCP server, attempt to start it and verify it responds:
    1. **github**: `./bin/github-mcp-server --help` — Go binary, should print usage
    2. **context7**: Already works (remote SSE) — just verify URL in config
    3. **memory**: `npx -y @modelcontextprotocol/server-memory --help` — npm, should run
    4. **sequential-thinking**: `npx -y @modelcontextprotocol/server-sequential-thinking --help` — npm
    5. **git**: `uvx mcp-server-git --help` — uvx, should download and run
    6. **serena**: `uvx --from git+https://github.com/oraios/serena serena --help` — uvx
    7. **hindsight**: `uvx --from hindsight-all-slim python ./hindsight_mcp.py` — uvx, needs Ollama
    8. **athena**: Disabled (`enabled: false`) — skip testing
  - Document which work, which need further setup

  **Must NOT do**:
  - Leave broken servers without documentation of what's wrong
  - Skip testing any server

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: Multiple test commands, needs to interpret results

  **Parallelization**:
  - **Can Run In Parallel**: NO (sequential tests, each needs to download packages)
  - **Parallel Group**: Wave 3 (after config updated)
  - **Blocks**: None (final verification)
  - **Blocked By**: Tasks 1, 2, 4

  **Acceptance Criteria**:
  - [ ] Each MCP server tested with documented result
  - [ ] Working servers confirmed working
  - [ ] Non-working servers have clear error + next steps
  - [ ] npm packages download and execute without Python errors
  - [ ] uvx packages download and execute without venv contamination

  **QA Scenarios**:
  ```
  Scenario: npm MCP servers respond
    Tool: Bash
    Preconditions: Node.js installed, opencode.json updated
    Steps:
      1. Run: npx -y @modelcontextprotocol/server-memory --help 2>&1 | head -5
      2. Assert: no "command not found" or Python errors
      3. Run: npx -y @modelcontextprotocol/server-sequential-thinking --help 2>&1 | head -5
      4. Assert: no "command not found" or Python errors
    Expected Result: Both npx commands execute cleanly
    Failure Indicators: Python import errors, module not found, npm 404
    Evidence: .sisyphus/evidence/task-6-npx-mcps.txt

  Scenario: uvx MCP servers respond
    Tool: Bash
    Preconditions: uv installed, opencode.json updated
    Steps:
      1. Run: uvx mcp-server-git --help 2>&1 | head -10
      2. Assert: no venv contamination errors, prints help
      3. Run: timeout 30 uvx --from git+https://github.com/oraios/serena serena --help 2>&1 | head -10
      4. Assert: no pydantic/anthropic import errors
    Expected Result: uvx runs packages in isolation, no venv issues
    Failure Indicators: pydantic.v1 errors, ExperimentalClientFeatures errors
    Evidence: .sisyphus/evidence/task-6-uvx-mcps.txt

  Scenario: Binary MCP server works
    Tool: Bash
    Preconditions: Binary exists at bin/
    Steps:
      1. Run: ./bin/github-mcp-server --help 2>&1 | head -3
      2. Assert: output contains "github" or usage info
    Expected Result: GitHub MCP binary responds
    Failure Indicators: Segfault, permission denied
    Evidence: .sisyphus/evidence/task-6-github-mcp.txt

  Scenario: Ollama API accessible
    Tool: Bash
    Preconditions: Ollama installed and running
    Steps:
      1. Run: curl -s http://localhost:11434/api/tags
      2. Assert: returns JSON with "models" key
    Expected Result: Ollama API responds
    Failure Indicators: Connection refused
    Evidence: .sisyphus/evidence/task-6-ollama-api.txt
  ```

  **Commit**: YES
  - Message: `fix(mcp): verify all MCP servers operational`
  - Files: `config/opencode.json` (if further fixes needed)

---

## Final Verification Wave

- [ ] F1. **Config Validation** — verify JSON, check all MCPs present, no Python venv refs
- [ ] F2. **Runtime Verification** — node, npx, ollama all installed and responding
- [ ] F3. **MCP Server Test** — each of the 8 MCPs tested individually
- [ ] F4. **Memory MCP Working** — global memory server responds and can store/retrieve

---

## Commit Strategy

- **Wave 1**: NO commits (system installs)
- **Wave 2**: `fix(config): replace Python MCPs with npm/binary equivalents` — config/opencode.json
- **Wave 3**: `fix(mcp): verify all MCP servers operational` — config/opencode.json (if further changes)

---

## Success Criteria

### Verification Commands
```bash
node --version                    # Expected: v20+ or v22+
npx --version                     # Expected: 10+
uvx --version                     # Expected: any version
ollama list                       # Expected: works without error
python3 -m json.tool config/opencode.json  # Expected: valid JSON
grep -c "athena/.venv" config/opencode.json  # Expected: 0
curl -s http://localhost:11434/api/tags  # Expected: JSON response
```

### Final Checklist
- [ ] Node.js + npm installed and working
- [ ] uv/uvx installed and working
- [ ] Ollama installed and running
- [ ] All 8 MCPs configured in opencode.json
- [ ] Zero Python venv references in MCP commands
- [ ] Global memory MCP functional (npm package)
- [ ] .env has all provider key placeholders
- [ ] athena MCP disabled (no npm alternative)
