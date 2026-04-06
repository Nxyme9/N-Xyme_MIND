# Portability Fix — Momus Red-Team Challenge

> **Goal**: Eliminate all remaining hardcoded `/home/nxyme` paths, fix bootstrap failures on fresh machines, and ensure MCP servers start and execute tools reliably.
> **Scope**: Config files, shell scripts, Python source, documentation, bootstrap flow.
> **Approach**: TDD-first — write tests that detect hardcoded paths and bootstrap failures, then fix the code.

---

## Challenge Results

### CHALLENGES FOUND: 5

| # | Category | File | Line | Issue |
|---|----------|------|------|-------|
| 1 | Hardcoded path | `README.md` | 8 | `cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND` in quick start |
| 2 | Hardcoded path | `packages/nx-mind-mcp/README.md` | 52 | Default `NX_MIND_ROOT` hardcoded |
| 3 | Hardcoded path | `packages/trigger-guardian-mcp/README.md` | 65 | `PYTHONPATH` hardcoded in example |
| 4 | Hardcoded path | `scripts/model-router-proxy.service` | 8-9 | systemd `WorkingDirectory` and `Environment` hardcoded |
| 5 | Bootstrap issue | `bootstrap.sh` | 65, 155 | `uv venv --clear` flag inconsistent; duplicate content (file has 181 lines with duplicated bootstrap logic from line 92-181) |

### Additional Issues Found (non-blocking but relevant)

| # | Category | File | Issue |
|---|----------|------|-------|
| 6 | MCP risk | `opencode.json` line 74 | `./venvs/athena/bin/python` — relative path, works only if cwd is workspace root |
| 7 | MCP risk | `opencode.json` line 82 | `./bin/github-mcp-server` — binary may not exist on fresh machine |
| 8 | Bootstrap | `bootstrap.sh` | No `set -e` enforcement after `uv` install — PATH export on line 58 doesn't persist in subshell |
| 9 | Health check | `bin/health-check.sh` line 36 | Checks `config/` and `.opencode/opencode.json` but misses `opencode.json` root file |
| 10 | Repair | `bin/repair-paths.sh` line 12 | `sed` replaces `./` with `${ROOT}/` — would break `./venvs/athena/bin/python` into `/absolute/path/venvs/athena/bin/python` which is correct, but the regex is too broad and could corrupt JSON values containing `./` that aren't paths |

### VERDICT: FAIL

The workspace has 5 concrete hardcoded path issues and 5 additional bootstrap/MCP risks that would cause failures on a fresh machine or different user.

---

## Implementation Plan

### Phase 1: Test Infrastructure (TDD Foundation)

**Task 1.1: Create portability test suite**
- File: `tests/unit/test_portability.py`
- Tests:
  - `test_no_hardcoded_home_paths_in_source()` — scans all `.py` files for `/home/` patterns
  - `test_no_hardcoded_home_paths_in_configs()` — scans all `.json` files in `config/`, `.opencode/`, root
  - `test_no_hardcoded_home_paths_in_scripts()` — scans all `.sh` files in `bin/`, `scripts/`
  - `test_bootstrap_uses_root_variable()` — verifies `bootstrap.sh` uses `$ROOT` not hardcoded paths
  - `test_env_sh_no_hardcoded_paths()` — verifies `env.sh` is portable
  - `test_opencode_json_uses_relative_paths()` — verifies MCP commands use `./` not absolute paths

**Task 1.2: Create bootstrap integration test**
- File: `tests/integration/test_bootstrap.py`
- Tests:
  - `test_bootstrap_creates_venvs()` — dry-run bootstrap, verify venv paths created
  - `test_bootstrap_creates_directories()` — verify `.opencode/`, `data/`, `.context/` created
  - `test_bootstrap_copies_config()` — verify `opencode.json` → `.opencode/opencode.json`

### Phase 2: Fix Hardcoded Paths in Source

**Task 2.1: Fix documentation paths**
- File: `README.md` line 8
  - Change: `cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND` → `cd /path/to/N-Xyme_MIND`
- File: `docs/BOOTSTRAP.md` line 6
  - Change: `cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND` → `cd /path/to/N-Xyme_MIND`
- File: `docs/ARCHITECTURE-BLUEPRINT.md` line 4
  - Change: Remove or generalize the location path
- File: `docs/HANDOFF.md` lines 17-33
  - Change: Replace all `/home/nxyme/` references with `$HOME/` or `~/`
- File: `docs/MASTER_SYSTEM.md` lines 29, 36, 159, 175
  - Change: Replace with relative or variable-based paths
- File: `docs/MASTERPLAN.md` line 265
  - Change: Already documented as an issue — update to show fix
- File: `docs/TROUBLESHOOTING.md` lines 51-56
  - Change: Update example commands to use generic paths
- File: `docs/DEPLOYMENT-RETROSPECTIVE.md` line 52
  - Change: Keep as historical reference but add note about fix
- File: `docs/MCP_REGISTRY.md` lines 10, 35
  - Change: Use `$HOME` in examples
- File: `docs/DELEGATION-MASTERPLAN.md` line 263
  - Change: Use relative path

**Task 2.2: Fix package README paths**
- File: `packages/nx-mind-mcp/README.md` line 52
  - Change: `NX_MIND_ROOT` default from `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND` → `$(pwd)` or unset
- File: `packages/trigger-guardian-mcp/README.md` line 65
  - Change: `PYTHONPATH` example from hardcoded to `$(pwd)/packages/trigger-guardian-mcp`

**Task 2.3: Fix systemd service file**
- File: `scripts/model-router-proxy.service` lines 8-9
  - Change: `WorkingDirectory=/home/nxyme/N-Xyme_MIND` → `WorkingDirectory=%h/N-Xyme_MIND` (systemd home expansion)
  - Change: `Environment=PYTHONPATH=/home/nxyme/N-Xyme_MIND` → `Environment=PYTHONPATH=%h/N-Xyme_MIND`

**Task 2.4: Fix modelrouter scripts**
- File: `modelrouter/scripts/create_all_vpn_connections.sh` line 5
  - Change: `CERT_DIR="/home/nxyme/.local/share/..."` → `CERT_DIR="${HOME}/.local/share/..."`
- File: `modelrouter/scripts/import_vpn_configs.sh` line 5
  - Change: Same as above

**Task 2.5: Fix health check and repair scripts**
- File: `bin/health-check.sh` line 36
  - Already uses `$ROOT` — the grep pattern `/home/nxyme` is intentional (it's checking FOR hardcoded paths). No change needed.
- File: `bin/health-l0-blink.sh` line 14
  - Same — intentional grep for hardcoded paths. No change needed.
- File: `bin/repair-paths.sh` line 9
  - Comment mentions `/home/nxyme` — acceptable as documentation. No change needed.

**Task 2.6: Fix STANDALONE.md**
- File: `STANDALONE.md` line 100
  - Change: Example grep command from `/home/nxyme` to `$HOME` or generic

### Phase 3: Fix Bootstrap Issues

**Task 3.1: Fix bootstrap.sh duplicate content**
- File: `bootstrap.sh`
  - Issue: Lines 92-181 are a duplicate of lines 1-91 (with minor differences)
  - Fix: Remove duplicate content (lines 92-181)
  - The duplicate has `--clear` flag removed and `--python python3` removed — consolidate to the better version

**Task 3.2: Fix bootstrap.sh uv PATH persistence**
- File: `bootstrap.sh` line 58
  - Issue: `export PATH="$HOME/.local/bin:$PATH"` doesn't persist if `uv` install script runs in a subshell
  - Fix: Add `source "$HOME/.local/bin/env" 2>/dev/null || true` after install, or use full path `$HOME/.local/bin/uv`

**Task 3.3: Fix bootstrap.sh venv creation consistency**
- File: `bootstrap.sh` lines 65-77
  - Issue: First venv uses `--python python3 --clear`, others use `--clear` only or no flags
  - Fix: Standardize all venv creation to use `uv venv <path> --python python3 2>/dev/null || uv venv <path>`

**Task 3.4: Add missing bootstrap steps**
- File: `bootstrap.sh`
  - Add: `npm install` or `npx` availability check (MCP servers use `npx -y`)
  - Add: Create `bin/github-mcp-server` symlink or download step (referenced in `opencode.json` line 82)
  - Add: Install Python dependencies for all package venvs, not just `venvs/athena`

### Phase 4: Fix MCP Server Risks

**Task 4.1: Ensure github-mcp-server exists**
- File: `bootstrap.sh`
  - Add step to install `github-mcp-server` binary or provide fallback
  - Alternative: Change `opencode.json` line 82 to use `npx -y @github/github-mcp-server` instead of local binary

**Task 4.2: Add MCP startup validation**
- File: `bin/health-l1-pulse.sh` (or new script)
  - Add: Test each MCP server can start (not just venv exists)
  - Test: `./venvs/athena/bin/python -m athena.mcp_server --help` or similar
  - Test: `./packages/nx-mind-mcp/venv/bin/python -m nx_mind_mcp --help`

**Task 4.3: Fix relative path dependency in opencode.json**
- File: `opencode.json`
  - All MCP commands use `./` relative paths — this is correct IF OpenCode runs from workspace root
  - Add: Comment or documentation noting that OpenCode must be launched from workspace root
  - Alternative: Use `${workspaceRoot}/` if OpenCode supports variable expansion

### Phase 5: Update Tests and Verify

**Task 5.1: Run portability tests**
- Execute: `python -m pytest tests/unit/test_portability.py -v`
- All tests must pass

**Task 5.2: Run bootstrap dry-run**
- Execute: `bash -n bootstrap.sh` (syntax check)
- Execute: `bash bootstrap.sh` in a clean temp directory

**Task 5.3: Run health checks**
- Execute: `bash bin/health-check.sh`
- Execute: `bash bin/health-l0-blink.sh`
- All checks must pass

---

## Commit Strategy (Atomic)

Each commit is independent and reversible:

1. **`test: add portability test suite`** — `tests/unit/test_portability.py`, `tests/integration/test_bootstrap.py`
2. **`fix: remove hardcoded paths from documentation`** — all `docs/*.md`, `README.md`, `STANDALONE.md`
3. **`fix: remove hardcoded paths from package READMEs`** — `packages/*/README.md`
4. **`fix: make systemd service portable`** — `scripts/model-router-proxy.service`
5. **`fix: make modelrouter scripts portable`** — `modelrouter/scripts/*.sh`
6. **`fix: remove duplicate content from bootstrap.sh`** — `bootstrap.sh`
7. **`fix: improve bootstrap.sh robustness`** — PATH persistence, venv consistency, missing deps
8. **`fix: ensure github-mcp-server availability`** — `bootstrap.sh` + `opencode.json` fallback
9. **`test: verify all portability tests pass`** — final verification

---

## QA Scenarios

### QA 1: Portability Test Suite
- **Tool**: `pytest tests/unit/test_portability.py -v`
- **Steps**:
  1. Run the test suite
  2. Verify all 6 tests pass
  3. Verify no `/home/nxyme` found in any `.py`, `.json`, `.sh` files (except intentional grep patterns in health checks)
- **Expected**: All tests pass, zero hardcoded paths in source/configs/scripts

### QA 2: Bootstrap on Fresh Machine
- **Tool**: `bash bootstrap.sh` in a clean Docker container or temp directory
- **Steps**:
  1. Create temp directory, clone repo
  2. Run `bash bootstrap.sh`
  3. Verify venvs created at correct paths
  4. Verify directories `.opencode/`, `data/`, `.context/` exist
  5. Verify `.opencode/opencode.json` exists
- **Expected**: Bootstrap completes without errors, all expected files/dirs exist

### QA 3: MCP Server Startup
- **Tool**: Manual MCP server invocation
- **Steps**:
  1. `source env.sh`
  2. `./venvs/athena/bin/python -c "import athena.mcp_server; print('OK')"`
  3. `./packages/nx-mind-mcp/venv/bin/python -c "import nx_mind_mcp; print('OK')"`
  4. `./packages/trigger-guardian-mcp/.venv/bin/python -c "import trigger_guardian_mcp; print('OK')"`
  5. `./packages/athena-context-mcp/venv/bin/python -c "import athena_context_mcp; print('OK')"`
- **Expected**: All 4 MCP servers import successfully

### QA 4: Health Check Pass
- **Tool**: `bash bin/health-check.sh`
- **Steps**:
  1. Run health check
  2. Verify exit code is 0
  3. Verify no hardcoded path failures
- **Expected**: All checks pass, exit code 0

### QA 5: No Regressions
- **Tool**: `bash bin/health-l0-blink.sh`
- **Steps**:
  1. Run L0 blink check
  2. Verify it completes in <1s
  3. Verify no hardcoded path detections in source
- **Expected**: Pass, <1s execution

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `sed` in repair-paths.sh corrupts JSON | Medium | High | Add JSON validation after sed, or use Python-based path replacement |
| `npx` not available on fresh machine | High | Medium | Add `npm`/`npx` check to bootstrap |
| `github-mcp-server` binary missing | High | Medium | Use `npx` fallback or install step |
| venv shebangs break after move | Medium | High | Already handled by `repair-paths.sh` |
| systemd service `%h` not supported | Low | Low | Test on target systems |
