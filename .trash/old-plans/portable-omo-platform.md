# Master Plan: N-Xyme_MIND Portable OMO Platform (BULLETPROOF)

## TL;DR

> **Mission**: Transform N-Xyme_MIND into a truly portable, self-contained OMO platform. Clone to ANY machine, run bootstrap, it works.
> 
> **Problem**: Previous plan had FALSE GREENS and SILENT REDS - tests passed but functionality broken.
> 
> **Root Causes Identified by 5-Agent Investigation**:
> 1. Bootstrap creates `venv/` but config expects `venvs/athena/` (path mismatch)
> 2. Python venvs contain ABSOLUTE paths - NOT portable when cloned
> 3. 55+ hardcoded `/home/nxyme` paths in Python source files
> 4. Health checks check wrong paths (false negatives)
> 5. QA "MCP starts" ≠ "MCP works" (false positives)
> 6. OpenCode config precedence bug - global overrides local

---

## Agent Investigation Summary

| Agent | Critical Finding |
|-------|-----------------|
| **Metis** | Bootstrap creates `venv/` but opencode.json expects `venvs/athena/` - 3 MCPs dead silently |
| **Momus** | Python venvs NOT portable - contain absolute paths to Python interpreter |
| **Explore** | Relative paths break from subdirectories, bootstrap incomplete |
| **Librarian** | OpenCode bug #19296: global config overrides local (opposite of docs) |
| **Oracle** | Current approach fundamentally broken; Docker or complete rewrite needed |

---

## Critical Issues (MUST FIX)

### ISSUE-1: Venv Path Mismatch (CRITICAL)
```
Bootstrap creates:  $ROOT/venv/
Config expects:      $ROOT/venvs/athena/
                     $ROOT/packages/*/venv/
                     $ROOT/packages/*/.venv/
```
**Impact**: 5 MCPs silently fail on fresh clone
**Fix**: Bootstrap MUST create venvs at exact paths config expects

### ISSUE-2: Venvs Not Portable (CRITICAL)
```
Venv contains:  /home/nxyme/.local/share/uv/python/cpython-3.12.../bin/python3.12
```
**Impact**: Cloned venvs point to non-existent paths on fresh machine
**Fix**: Use `uv venv --relocatable` OR recreate venvs during bootstrap

### ISSUE-3: Hardcoded Paths in Python Source (CRITICAL)
Found 55+ occurrences of `/home/nxyme` in:
- `athena_context_mcp/__init__.py` (fallback paths)
- `nx_mind_mcp/__init__.py` (fallback paths)
- `src/memory/mcp_server.py`
- Integration tests
**Fix**: Replace all with environment variable lookups

### ISSUE-4: Config Precedence Bug (HIGH)
OpenCode bug #19296: global config overrides project config
**Fix**: Copy ALL needed settings into project config (no dependency on global)

### ISSUE-5: QA Scenarios Are False Positives (HIGH)
Current QA: "MCP starts with timeout 3" = passing
Reality: MCP can start but fail on first tool call
**Fix**: Add actual tool call verification

---

## Work Objectives

### Core Objective
Create a **verified portable** workspace where:
1. ✅ Bootstrap creates ALL venvs at correct paths
2. ✅ All paths relative OR recreated during bootstrap
3. ✅ Zero hardcoded machine paths in source
4. ✅ QA tests actual functionality, not just startup
5. ✅ Works on fresh machine after `git clone + bootstrap`

### Must NOT Have
- ❌ Bootstrap creates wrong venv paths
- ❌ Cloned venvs with broken symlinks
- ❌ Hardcoded `/home/nxyme` anywhere in source
- ❌ QA that only tests "starts" not "works"
- ❌ Dependencies on global configs

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (AUDIT & REMEDIATE):
├── T1: Audit ALL hardcoded paths (55+ occurrences)
├── T2: Fix Python source files (replace with env vars)
├── T3: Fix opencode.json (all relative paths)
└── T4: Fix bootstrap.sh (create ALL correct venvs)

Wave 2 (VERIFICATION):
├── T5: Test venv creation at exact paths
├── T6: Test MCP actual tool calls (not just starts)
├── T7: Test path leak scan (zero /home/nxyme)
└── T8: Test fresh clone simulation

Wave 3 (AGENTS & CONFIG):
├── T9: Copy agent definitions to project oh-my-opencode.json
├── T10: Verify config precedence (no global dependency)
└── T11: Document standalone verification

FINAL: Oracle + Momus review of bulletproof plan
```

---

## TODOs

### Wave 1: Audit & Remediate

- [ ] 1. **Audit ALL Hardcoded Paths**
  
  **What to do**:
  - Run: `grep -rn "/home/nxyme" --include="*.py" . | grep -v ".git" | grep -v "__pycache__"`
  - Document every file with hardcoded path
  - Categorize: config vs source vs test vs data
  
  **QA Scenarios**:
  ```
  Scenario: Find all hardcoded paths
    Tool: Bash (grep)
    Steps:
      1. grep -rn "/home/nxyme" --include="*.py" . | wc -l
      2. List all files with matches
    Expected: Complete list, 55+ occurrences
    Evidence: .sisyphus/evidence/audit-hardcoded-paths.txt
  ```

- [ ] 2. **Fix Python Source Files**
  
  **What to do**:
  - For each file with hardcoded path:
    - Replace `Path("/home/nxyme/...")` with `Path(os.environ.get("PROJECT_ROOT", "."))`
    - Or use `Path(__file__).parent.parent` for relative resolution
  - Files to fix:
    - `packages/athena-context-mcp/athena_context_mcp/__init__.py` (lines 26, 62)
    - `packages/nx-mind-mcp/nx_mind_mcp/__init__.py` (lines 26, 62)
    - `src/memory/mcp_server.py` (if has hardcoded paths)
    - `tests/integration/test_core.py` (line 9)
  
  **Must NOT do**:
  - Don't use os.getcwd() - use __file__ based resolution
  - Don't assume CWD is project root
  - Don't leave ANY fallback with /home/nxyme
  
  **References**:
  - Pattern: `Path(os.environ.get("ATHENA_CONTEXT_ROOT", Path(__file__).parent.parent))`
  - Pattern: `PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent`
  
  **QA Scenarios**:
  ```
  Scenario: Verify no hardcoded paths remain
    Tool: Bash (grep)
    Steps:
      1. grep -rn "/home/nxyme" --include="*.py" . | wc -l
      2. Should be 0
    Expected: 0 hardcoded paths
    Evidence: .sisyphus/evidence/fix-source-paths.txt
  ```

- [ ] 3. **Fix opencode.json Paths**
  
  **What to do**:
  - Check filesystem MCP: `/home/nxyme` → `./` or make configurable
  - Verify all Python paths use `./venvs/athena/` NOT `./venv/`
  - All 5 Python venv paths must be exact:
    - `./venvs/athena/bin/python` (athena, unified-memory)
    - `./packages/athena-context-mcp/venv/bin/python`
    - `./packages/trigger-guardian-mcp/.venv/bin/python`
    - `./packages/nx-mind-mcp/venv/bin/python`
  
  **References**:
  - Current file: `./opencode.json`
  
  **QA Scenarios**:
  ```
  Scenario: Verify all paths match bootstrap output
    Tool: Bash
    Steps:
      1. grep "python" opencode.json | grep -oE "\./[^,]+" | sort -u
      2. Compare with bootstrap expected paths
    Expected: All paths exist after bootstrap
    Evidence: .sisyphus/evidence/fix-config-paths.txt
  ```

- [ ] 4. **Fix bootstrap.sh to Create ALL Venvs**
  
  **What to do**:
  - Modify bootstrap to create venvs at EXACT paths:
    ```bash
    # Create venvs at paths opencode.json expects
    uv venv ./venvs/athena
    uv venv ./packages/athena-context-mcp/venv
    uv venv ./packages/trigger-guardian-mcp/.venv
    uv venv ./packages/nx-mind-mcp/venv
    ```
  - Install dependencies in each venv:
    - `./venvs/athena/`: athena.mcp_server deps
    - `./packages/athena-context-mcp/venv/`: athena_context_mcp deps
    - etc.
  - Add verification step: `test -f ./venvs/athena/bin/python`
  
  **Must NOT do**:
  - Don't create `./venv/` - must be `./venvs/athena/`
  - Don't assume packages are installed - explicitly install each
  - Don't skip the verification step
  
  **References**:
  - Current: `./bootstrap.sh`
  - Expected paths: from opencode.json
  
  **QA Scenarios**:
  ```
  Scenario: Bootstrap creates exact venv paths
    Tool: Bash
    Steps:
      1. cd /tmp && rm -rf test && mkdir test && cd test
      2. Run bootstrap script
      3. test -f ./venvs/athena/bin/python && echo "EXISTS"
      4. test -f ./packages/athena-context-mcp/venv/bin/python && echo "EXISTS"
      5. test -f ./packages/trigger-guardian-mcp/.venv/bin/python && echo "EXISTS"
      6. test -f ./packages/nx-mind-mcp/venv/bin/python && echo "EXISTS"
    Expected: All 4 venvs created at correct paths
    Evidence: .sisyphus/evidence/bootstrap-venvs.txt
  ```

### Wave 2: Verification

- [ ] 5. **Test Venv Creation at Exact Paths**
  
  **What to do**:
  - Run bootstrap in temp directory
  - Verify each venv exists at exact path
  - Verify each venv's Python works:
    ```bash
    ./venvs/athena/bin/python -c "import athena"
    ./packages/athena-context-mcp/venv/bin/python -c "import athena_context_mcp"
    ./packages/nx-mind-mcp/venv/bin/python -c "import nx_mind_mcp"
    ./packages/trigger-guardian-mcp/.venv/bin/python -c "import trigger_guardian_mcp"
    ```
  
  **QA Scenarios**:
  ```
  Scenario: All venvs import correctly
    Tool: Bash
    Steps:
      1. For each venv, run: venv/bin/python -c "import module"
      2. Check exit code = 0
    Expected: All imports succeed
    Evidence: .sisyphus/evidence/test-venv-imports.txt
  ```

- [ ] 6. **Test MCP Actual Tool Calls (Not Just Starts)**
  
  **What to do**:
  - Create test script that:
    1. Starts MCP with timeout
    2. Sends JSON-RPC `tools/list` request
    3. Verifies response contains tools
    4. Sends actual tool call
    5. Verifies result
  - Example for filesystem MCP:
    ```bash
    echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | \
      timeout 5 ./packages/athena-context-mcp/venv/bin/python -m athena_context_mcp
    # Should return {"id":1,"result":{"tools":[...]}}
    ```
  
  **Must NOT do**:
  - Don't just check "running on stdio" output
  - Don't assume start = works
  - Don't skip error response checking
  
  **References**:
  - MCP Inspector: `npx -y @modelcontextprotocol/inspector`
  - Protocol: JSON-RPC 2.0 over stdio
  
  **QA Scenarios**:
  ```
  Scenario: MCP responds to tools/list
    Tool: Bash (stdio JSON-RPC)
    Steps:
      1. echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | timeout 5 MCP_COMMAND
      2. Parse JSON response
      3. Verify "result" contains "tools" array
    Expected: Valid JSON-RPC response with tools
    Evidence: .sisyphus/evidence/test-mcp-tools.txt
  ```

- [ ] 7. **Test Path Leak Scan**
  
  **What to do**:
  - Run comprehensive scan:
    ```bash
    # Check Python files
    grep -rn "/home/nxyme" --include="*.py" . | grep -v ".git"
    # Check JSON files
    grep -rn "/home/nxyme" --include="*.json" . | grep -v ".git"
    # Check shell files
    grep -rn "/home/nxyme" --include="*.sh" . | grep -v ".git"
    ```
  - Verify ZERO matches (except intentionally documented cases)
  
  **QA Scenarios**:
  ```
  Scenario: Zero hardcoded paths
    Tool: Bash (grep)
    Steps:
      1. grep -rn "/home/nxyme" --include="*.py" . | grep -v ".git"
      2. grep -rn "/home/nxyme" --include="*.json" . | grep -v ".git"
      3. grep -rn "/home/nxyme" --include="*.sh" . | grep -v ".git"
    Expected: 0 matches in all
    Evidence: .sisyphus/evidence/path-leak-scan.txt
  ```

- [ ] 8. **Test Fresh Clone Simulation**
  
  **What to do**:
  - Simulate fresh machine:
    ```bash
    cd /tmp
    rm -rf fresh-test
    mkdir fresh-test && cd fresh-test
    
    # Copy only portable files (exclude venvs, caches)
    rsync -av --exclude='.git' --exclude='venv*' --exclude='__pycache__' \
          --exclude='*.pyc' --exclude='node_modules' \
          /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/ .
    
    # Run bootstrap
    bash bootstrap.sh
    
    # Verify everything works
    bash bin/health-l0-blink.sh
    bash bin/health-l1-pulse.sh
    ```
  - Document any failures
  
  **QA Scenarios**:
  ```
  Scenario: Fresh clone works
    Tool: Bash
    Steps:
      1. cd /tmp && rm -rf fresh-test && mkdir fresh-test
      2. rsync (exclude venvs, caches) to fresh-test/
      3. cd fresh-test && bash bootstrap.sh
      4. ./venvs/athena/bin/python -c "import athena"
      5. ./packages/*/venv/bin/python -c "import module"
    Expected: Bootstrap succeeds, all imports work
    Evidence: .sisyphus/evidence/fresh-clone.txt
  ```

### Wave 3: Agents & Config

- [ ] 9. **Copy Agent Definitions to Project**
  
  **What to do**:
  - Read global config: `~/.config/opencode/oh-my-opencode.json`
  - Copy ALL agent definitions to project `./oh-my-opencode.json`
  - Verify structure matches expected schema
  
  **QA Scenarios**:
  ```
  Scenario: Verify agents defined locally
    Tool: Bash
    Steps:
      1. cat ./oh-my-opencode.json | python3 -m json.tool > /dev/null
      2. grep -c '"explore"\|"librarian"\|"sisyphus"' ./oh-my-opencode.json
    Expected: All agents defined, valid JSON
    Evidence: .sisyphus/evidence/agents-local.txt
  ```

- [ ] 10. **Verify Config Precedence (No Global Dependency)**
  
  **What to do**:
  - Test OpenCode behavior with global config missing:
    ```bash
    mv ~/.config/opencode/opencode.json ~/.config/opencode/opencode.json.bak
    opencode --version  # Should work with project config
    mv ~/.config/opencode/opencode.json.bak ~/.config/opencode/opencode.json
    ```
  - Verify project config has ALL needed settings:
    - model, small_model
    - enabled_providers
    - permission
    - agent definitions
  
  **References**:
  - OpenCode bug #19296: global overrides local (we're working around it)
  
  **QA Scenarios**:
  ```
  Scenario: Works without global config
    Tool: Bash
    Steps:
      1. mv ~/.config/opencode/opencode.json /tmp/
      2. opencode --version  # Should still work
      3. mv /tmp/opencode.json ~/.config/opencode/
    Expected: Works with project config only
    Evidence: .sisyphus/evidence/config-precedence.txt
  ```

- [ ] 11. **Document Standalone Verification**
  
  **What to do**:
  - Create `VERIFICATION.md` documenting:
    - How to verify portability
    - Commands to run
    - Expected results
    - Troubleshooting guide
  - Include:
    - Path leak check
    - Venv creation test
    - MCP tool call test
    - Fresh clone test
  
  **References**:
  - Template from librarian research: MCP testing tools
  
  **QA Scenarios**:
  ```
  Scenario: Documentation complete
    Tool: Bash
    Steps:
      1. cat VERIFICATION.md | head -50
      2. Verify includes: path scan, venv test, MCP test, clone test
    Expected: All 4 verification methods documented
    Evidence: .sisyphus/evidence/documentation.txt
  ```

---

## Final Verification Wave

- [ ] F1. **Oracle Architecture Review**
  
  Verify:
  - All hardcoded paths removed
  - Bootstrap creates exact venv paths
  - MCPs tested with actual tool calls
  - Fresh clone simulation passes
  - Zero dependencies on global config
  
  Output: `VERDICT: APPROVE/REJECT + issues`

- [ ] F2. **Momus Red-Team Challenge**
  
  Challenge:
  - "Find 1 more hardcoded path"
  - "Break the bootstrap in 1 step"
  - "Make an MCP start but fail on tool call"
  
  Output: `CHALLENGES REMAINING: N | VERDICT`

---

## Success Criteria

### Verification Commands
```bash
# 1. Zero hardcoded paths
grep -rn "/home/nxyme" --include="*.py" --include="*.json" --include="*.sh" . | grep -v ".git" | wc -l
# Expected: 0

# 2. Bootstrap creates exact paths
test -f ./venvs/athena/bin/python && \
test -f ./packages/athena-context-mcp/venv/bin/python && \
test -f ./packages/trigger-guardian-mcp/.venv/bin/python && \
test -f ./packages/nx-mind-mcp/venv/bin/python
# Expected: all pass

# 3. All imports work
./venvs/athena/bin/python -c "import athena" && \
./packages/athena-context-mcp/venv/bin/python -c "import athena_context_mcp"
# Expected: all pass

# 4. MCP tool call works
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | \
  timeout 5 ./packages/athena-context-mcp/venv/bin/python -m athena_context_mcp | \
  grep -q '"result"'
# Expected: pass

# 5. Fresh clone works
cd /tmp && rm -rf test && rsync --exclude='venv*' ... && bash bootstrap.sh && test -f ./venvs/athena/bin/python
# Expected: pass
```

### Final Checklist
- [ ] Zero `/home/nxyme` hardcoded paths
- [ ] Bootstrap creates ALL 4 venvs at correct paths
- [ ] All Python imports work in all venvs
- [ ] MCPs respond to tool calls (not just start)
- [ ] Works without global config
- [ ] Fresh clone simulation passes
- [ ] Oracle approves
- [ ] Momus finds zero remaining issues

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `uv venv --relocatable` still has issues | Venvs still broken on clone | Always recreate venvs during bootstrap |
| OpenCode config precedence bug | Global overrides local | Copy ALL settings to project |
| Some MCPs need external services | MCP starts but fails later | Document Ollama/GitHub token requirements |
| `bin/github-mcp-server` is x86-64 only | Won't work on ARM Mac | Document architecture limitation, or build from source |

---

## Timeline

| Wave | Tasks | Parallel | Time |
|------|-------|----------|------|
| 1 | 4 | No (sequential) | 1-2 hours |
| 2 | 4 | Yes | 30 min |
| 3 | 3 | Yes | 30 min |
| FINAL | 2 | No | 30 min |
| **TOTAL** | **13** | - | **~3 hours** |

---

## Key Principle

> **"If it doesn't work on a fresh machine, it's not portable."**

Previous plan had FALSE GREENS because:
- Tests ran on YOUR machine with YOUR environment
- "MCP starts" ≠ "MCP works"
- Bootstrap created wrong paths but tests didn't catch it

This plan requires ACTUAL fresh machine simulation before declaring success.
