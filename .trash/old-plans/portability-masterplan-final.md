#PY|#KW|# N-Xyme_MIND Portability Masterplan - FINAL (REBUILD FRESH EDITION)
#NM|#KM|
#RH|#NH|## TL;DR
#QZ|#RW|
#ZT|#ZK|> **Mission**: Transform N-Xyme_MIND into a fully portable OMO platform clone-and-run platform.
#BH|#VT|> 
#MT|#NV|> **REBUILD FRESH PHILOSOPHY**: All implementations are NEW, not patched. Clean code = no technical debt.
#QV|#PM|> 
#ZQ|#ZJ|> **Key Decisions**:
#NZ|#BR|> - Phase 0 Pre-Flight FIRST (mandatory before any work)
#WH|#TZ|> - Use Hephaestus (not Sisyphus-Junior) for implementation
#VR|#SM|> - Memory directories in bootstrap from start (NEW)
#JV|#KB|> - TDD workflow for all tasks
#PS|#BY|> - ALL "fix" language converted to "REBUILD FRESH"
#XZ|#SS|---
#KM|#VP|
#QJ|#MH|## Context
#SM|#KS|
#RW|#SW|### Original Request
#VS|#XX|Transform N-Xyme_MIND into a portable OMO platform - clone to any machine, run bootstrap, it works.
#NM|#RJ|
#KQ|#VP|### Metis Gap Analysis (Consolidated)
#YH|#NV|
#PX|#JZ|| Gap | Priority | Status | Rebuild Fresh Approach |
#KZ|#TR||-----|----------|--------|----------------------|
#HN|#HZ|| M1: Memory directories not in bootstrap | HIGH | Open | CREATE NEW bootstrap.sh with memory dirs |
#NM|#RX|| M2: MetricsStore hardcoded path | MEDIUM | Open | WRITE NEW MetricsStore with env vars |
#PV|#VR|| M3: Memory bank files empty | MEDIUM | Open | Seed with defaults (NEW content) |
#WK|#PV|| D1: Phase 0 not run | CRITICAL | Open | Execute first |
#PB|#TQ|| D2: portable-omo-platform.md tasks not done | CRITICAL | Open | Execute T5-T11 |
#QV|#SH|| D3: Wrong agent used | HIGH | Open | Use Hephaestus |
#RP|#JQ|
#RZ|#RB|### Momus Challenges (Consolidated)
#PH|#WV|
#MR|#YJ|| Challenge | Priority | Rebuild Fresh Counter-Mitigation |
#KB|#KT||-----------|----------|-------------------------------|
#KZ|#ZZ|| 1. LanceDB Not Installed | RESOLVED | Uses SQLite, not needed |
#RP|#JY|| 2. MetricsStore-Memory Bridge Gap | HIGH | Create NEW integration module |
#TB|#XJ|| 3. Missing Memory Directory Creation | CRITICAL | CREATE NEW bootstrap.sh with dirs |
#HH|#NS|| 4. Phase 0 Pre-Flight Not Executed | CRITICAL | Execute FIRST |
#PZ|#PK|| 5. Timeline (Memory is weeks) | MEDIUM | Scope to MVP only |
#HW|#XN|
#NK|#YH|---
#WM|#PB|
#YS|#KQ|## Work Objectives
#BY|#TJ|
#NP|#QM|### Core Objective (REBUILD FRESH)
#BX|#PS|Create a verified portable workspace where:
#VZ|#SW|1. ✅ REBUILD bootstrap.sh creates ALL directories including memory_bank (NEW)
#NZ|#BJ|2. ✅ All paths relative OR environment-based (NEW implementation)
#RY|#PS|3. ✅ Phase 0 pre-flight runs before any work
#MS|#QY|4. ✅ Hephaestus implements, not Sisyphus-Junior
#TQ|#BZ|5. ✅ QA tests actual functionality
#YM|#YJ|
#VY|#VX|### Must Have (REBUILD FRESH)
#VZ|#TM|- Phase 0 pre-flight check passes
#QR|#BJ|- REBUILD bootstrap.sh creates `.context/memory_bank/` (NEW, not patched)
#WM|#KR|- REBUILD MetricsStore with env-based paths (NEW, not patched)
#JP|#PK|- Memory bank files seeded with valid content
#XN|#RT|- All 11 portable-omo-platform tasks completed
#QV|#VW|
#TN|#YY|### Must NOT Have
#KR|#YR|- ❌ Hardcoded `/home/nxyme` paths in source
#MW|#BH|- ❌ Sisyphus-Junior for implementation (use Hephaestus)
#JX|#WX|- ❌ Working without Phase 0 pre-flight
#YQ|#NR|- ❌ Missing memory directories in bootstrap
#SN|#TH|
#PM|#MP|---
#PJ|#KB|
#VV|#TT|## Execution Strategy
#PX|#PR|
#JJ|#PV|### Wave Structure
#ZQ|#HV|
#HM|#KJ|```
#WY|#RH|Wave 0: PRE-FLIGHT (MANDATORY - Sync Barrier)
#KS|#PX|├── P0: Run Phase 0 pre-flight checks
#SZ|#MX|└── BLOCKS: All other waves until complete
#BB|#PX|
#HK|#TX|Wave 1: BOOTSTRAP REBUILD (Foundation - BUILD FRESH)
#XB|#MP|├── T1: REBUILD NEW clean bootstrap.sh
#TX|#YW|├── T2: Seed memory bank files with defaults
#XS|#BN|├── T3: REBUILD NEW MetricsStore with env paths
#XY|#NW|└── T4: Create metrics-memory bridge
#HV|#WR|
#XX|#HW|Wave 2: PORTABLE-OMO PLATFORM TASKS
#NK|#JV|├── T5: Test venv creation at exact paths
#QX|#PZ|├── T6: IMPLEMENT NEW MCP verification test
#ZW|#KS|├── T7: Test path leak scan
#WM|#PW|├── T8: Test fresh clone simulation
#ZN|#QV|├── T9: Copy agent definitions to project
#JM|#JP|├── T10: Verify config precedence
#XB|#HB|└── T11: Document standalone verification
#QZ|#BX|
#NM|#YH|Wave 3: VERIFICATION
#YP|#NH|├── F1: Oracle architecture review
#SZ|#NJ|├── F2: Momus red-team challenge
#NW|#JQ|└── F3: Final user acceptance
#BB|#ZV|```
#BT|#BK|
#JV|#HN|### Critical Path
#QX|#XT|P0 (Phase 0) → Wave 1 → Wave 2 → Wave 3
#WQ|#PJ|
#TQ|#TH|---
#HS|#NJ|
#YH|#HX|## Task Dependency Graph
#QM|#HT|
#HX|#PK|| Task | Depends On | Reason |
#ZV|#BN||------|------------|--------|
#PY|#ZJ|| P0: Phase 0 pre-flight | None | Must run first - sync barrier |
#BS|#ZJ|| T1: REBUILD NEW bootstrap.sh | P0 | Create fresh clean script |
#HP|#JW|| T2: Seed memory bank files | P0 | Independent |
#BP|#KM|| T3: REBUILD NEW MetricsStore | P0 | Write new implementation |
#KW|#KK|| T4: Metrics-memory bridge | T3 | Uses MetricsStore |
#PN|#VQ|| T5-T11: Platform tasks | T1, T2, T3, T4 | All wave 1 tasks complete |
#NJ|#QS|| F1-F3: Verification | T5-T11 | All tasks complete |
#BT|#BK|
#MK|#KK|---
#VQ|#RM|
#HQ|#BJ|## Parallel Execution Graph
#TH|#XM|
#RX|#TT|### Wave 0 (Start Immediately - NO DEPENDENCIES)
#KV|#JH|- P0: Phase 0 pre-flight (blocks everything)
#ZR|#WY|
#SV|#VP|### Wave 1 (After P0 - PARALLEL OK - BUILD FRESH)
#NZ|#RP|- T1: REBUILD NEW bootstrap.sh (depends: P0)
#XH|#HW|- T2: Seed memory bank files (depends: P0)
#ZK|#KH|- T3: REBUILD NEW MetricsStore (depends: P0)
#BP|#JS|- T4: Create metrics-memory bridge (depends: T3)
#PK|#HP|
#VQ|#QP|### Wave 2 (After Wave 1 - MAX PARALLEL)
#JZ|#YH|- T5-T11: All 7 tasks can run in parallel
#PT|#QZ|
#KH|#HM|### Wave 3 (After Wave 2 - SEQUENTIAL)
#ZS|#TK|- F1, F2, F3: Sequential reviews
#JQ|#QX|
#QW|#NP|---
#JN|#QS|
#ZX|#KS|## TODOs
#BH|#QR|
#PB|#JX|### Wave 0: PRE-FLIGHT (MANDATORY)
#YJ|#WX|
#PT|#PS|- [ ] **P0. Phase 0 Pre-Flight Checks**
#HZ|#RS|
#HY|#NR|  **What to do**:
#ZB|#HX|  - Run `bash bin/health-l0-blink.sh` - verify <100ms
#WP|#KH|  - Check disk space: `df -h .` - need >1GB free
#MH|#KW|  - Check auth tokens: `echo $GITHUB_TOKEN` - not empty
#QJ|#MM|  - Check token budget: Run sample query, verify <80% context used
#WJ|#XS|  - Check MCP health: All 4 MCPs respond to ping
#QH|#PY|
#HB|#VM|  **Must NOT do**:
#KM|#YY|  - Don't skip any check
#MQ|#SR|  - Don't proceed if any check fails
#WJ|#QH|
#JS|#TZ|  **Delegation Recommendation**:
#RX|#BS|  - Category: `quick` - simple script execution
#YM|#VS|  - Skills: [] - no special skills needed
#HM|#TV|
#JV|#SJ|  **QA Scenarios**:
#TM|#XS|  ```
#SS|#HY|  Scenario: Pre-flight checks pass
#MK|#HY|    Tool: Bash
#SJ|#PB|    Steps:
#KB|#PB|      1. bash bin/health-l0-blink.sh
#PP|#QX|      2. df -h . | awk '{print $4}' | tail -1
#WX|#VY|      3. echo ${GITHUB_TOKEN:+set}
#RJ|#HT|    Expected: All checks pass, >1GB disk, token set
#WZ|#QM|  ```
#WY|#PN|
#KK|#NM|---
#YH|#NV|
#PH|#VJ|### Wave 1: BOOTSTRAP REBUILD (BUILD FRESH)
#MJ|#TT|
#BW|#ZQ|- [ ] **T1. REBUILD NEW Clean bootstrap.sh**
#WP|#BN|
#HY|#NR|  **What to do** (REBUILD FRESH - NOT FIX):
#MM|#MQ|  - CREATE NEW clean bootstrap.sh from scratch
#SJ|#RV|    - Do NOT patch existing code - write fresh
#TZ|#NM|    - Include memory directory creation from the start:
#NP|#KV|      ```bash
#QM|#QY|      mkdir -p "$ROOT/.opencode" "$ROOT/data" "$ROOT/.context" "$ROOT/.context/memory_bank" "$ROOT/.context/memory_graph"
#SX|#MW|      ```
#SH|#BK|  - Ensure no duplication in the new script
#BX|#NT|  - Add verification step after directory creation
#BX|#NT|
#JS|#TZ|  **Why REBUILD FRESH**:
#NM|#RX|  - Cleaner code, no technical debt
#KV|#JK|  - Memory directories included from start
#MB|#ZZ|  - No patch inheritance issues
#KB|#TT|
#JS|#TZ|  **Delegation Recommendation**:
#ZR|#MH|  - Category: `quick` - new file creation
#HX|#NT|  - Skills: [`git-master`] - for atomic commit
#TP|#HN|
#JV|#SJ|  **QA Scenarios**:
#BH|#PY|  ```
#JT|#RM|  Scenario: NEW Bootstrap creates memory directories
#MK|#HY|    Tool: Bash
#SJ|#PB|    Steps:
#RY|#HW|      1. rm -rf /tmp/test-bootstrap && mkdir /tmp/test-bootstrap
#TP|#VQ|      2. cd /tmp/test-bootstrap && cp -r /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/bootstrap.sh .
#RH|#MZ|      3. bash bootstrap.sh 2>&1 | tail -20
#TH|#BM|      4. test -d .context/memory_bank && echo "EXISTS"
#PN|#WB|      5. test -d .context/memory_graph && echo "EXISTS"
#RY|#XV|    Expected: Both directories created
#VK|#KP|  ```
#WP|#BN|
#JR|#XX|- [ ] **T2. Seed Memory Bank Files** (Already NEW)
#VH|#PZ|
#HY|#NR|  **What to do**:
#WM|#PS|  - Ensure activeContext.md has valid frontmatter + session context
#KS|#JK|  - Ensure productContext.md has identity + purpose
#XZ|#WJ|  - Ensure userContext.md has preferences
#VR|#JQ|  - Ensure constraints.md has behavioral limits
#YQ|#TR|  - Add "last_updated" timestamps
#NW|#NZ|
#JS|#TZ|  **Delegation Recommendation**:
#HS|#ZY|  - Category: `quick` - file content update
#PW|#KZ|  - Skills: [] - no special skills
#KN|#SR|
#JV|#SJ|  **QA Scenarios**:
#YV|#QQ|  ```
#MB|#HB|  Scenario: Memory bank files valid
#MK|#HY|    Tool: Bash
#SJ|#PB|    Steps:
#YN|#JP|      1. cat .context/memory_bank/activeContext.md | head -10
#NN|#TH|      2. cat .context/memory_bank/productContext.md | head -10
#ZN|#QK|      3. test -s .context/memory_bank/activeContext.md
#WM|#BV|      4. test -s .context/memory_bank/productContext.md
#PR|#WR|    Expected: All files have content, valid frontmatter
#KP|#RM|  ```
#VH|#PZ|
#TK|#BH|- [ ] **T3. REBUILD NEW MetricsStore with Env-Based Paths**
#QY|#XJ|
#HY|#NR|  **What to do** (REBUILD FRESH - NOT FIX):
#ZS|#MN|  - WRITE NEW MetricsStore implementation with env-based paths from start
#BZ|#NJ|    - Do NOT patch existing code - create fresh implementation
#QK|#HQ|    - Default behavior uses env var with fallback:
#MS|#JR|      ```python
#QK|#HQ|      def __init__(self, db_path: str = None):
#ZK|#ST|          if db_path is None:
#MS|#JR|              db_path = os.environ.get("METRICS_DB_PATH", "data/nervous_system.db")
#ZW|#WQ|      ```
#XH|#MM|  - Update get_store() function similarly
#VQ|#WJ|  - Ensure path is relative to workspace root
#BX|#NT|
#JS|#TZ|  **Why REBUILD FRESH**:
#NM|#RX|  - Cleaner code, no technical debt
#KV|#JK|  - Environment-based from inception
#MB|#ZZ|  - No patch inheritance issues
#KB|#TT|
#JS|#TZ|  **Delegation Recommendation**:
#BW|#SZ|  - Category: `deep` - new module creation
#BW|#ZT|  - Skills: [] - standard Python
#MN|#HS|
#JV|#SJ|  **QA Scenarios**:
#WM|#BP|  ```
#MQ|#JN|  Scenario: REBUILD MetricsStore uses env var
#MK|#HY|    Tool: Bash
#SJ|#PB|    Steps:
#QN|#QS|      1. METRICS_DB_PATH=/tmp/test.db ./venvs/athena/bin/python -c "
#PM|#BH|         from src.metrics_store import MetricsStore
#MS|#BM|         s = MetricsStore()
#TV|#VP|         print(s.db_path)
#ST|#ZN|         "
#JR|#QT|      2. unset METRICS_DB_PATH && ./venvs/athena/bin/python -c "
#PM|#BH|         from src.metrics_store import MetricsStore
#MS|#BM|         s = MetricsStore()
#TV|#VP|         print(s.db_path)
#JH|#TH|         "
#RW|#TW|    Expected: First uses /tmp/test.db, second uses data/nervous_system.db
#BJ|#ZK|  ```
#BT|#BK|
#MB|#ZW|- [ ] **T4. Create Metrics-Memory Bridge** (Already NEW)
#WZ|#WQ|
#HY|#NR|  **What to do**:
#JR|#HX|  - Create src/integrations/metrics_memory_bridge.py
#QY|#WN|  - Bridge should:
#VX|#ZM|    - Record memory operations to MetricsStore
#NV|#YW|    - Query metrics for memory system health
#MY|#PT|    - Publish alerts when memory operations fail
#ST|#XK|
#JS|#TZ|  **Delegation Recommendation**:
#QQ|#PP|  - Category: `deep` - new module creation
#XQ|#VY|  - Skills: [] - integration logic
#XS|#ZB|
#JV|#SJ|  **QA Scenarios**:
#ZZ|#YN|  ```
#VB|#WW|  Scenario: Bridge module exists and integrates
#MK|#HY|    Tool: Bash
#SJ|#PB|    Steps:
#PP|#PQ|      1. ./venvs/athena/bin/python -c "from src.integrations.metrics_memory_bridge import *; print('OK')"
#BZ|#SR|    Expected: Module loads without error
#XT|#SH|  ```
#VY|#QY|
#SZ|#YQ|---
#XY|#MP|
#NB|#XH|### Wave 2: PORTABLE-OMO PLATFORM TASKS
#HZ|#RS|
#KR|#TP|- [ ] **T5. Test Venv Creation at Exact Paths**
#QZ|#BX|
#HY|#NR|  **What to do**:
#QZ|#BZ|  - Run bootstrap in temp directory
#RN|#JX|  - Verify each venv exists at exact path
#KP|#NX|  - Verify each venv's Python works
#VS|#YM|
#JS|#TZ|  **Delegation Recommendation**:
#ZY|#PV|  - Category: `unspecified-high` - verification task
#NH|#YB|  - Skills: [] - standard bash
#KY|#YH|
#JV|#SJ|  **QA Scenarios**:
#ZY|#YQ|  ```
#BK|#SX|  Scenario: All venvs import correctly
#MK|#HY|    Tool: Bash
#SJ|#PB|    Steps:
#YV|#ZV|      1. cd /tmp && rm -rf test-venv && mkdir test-venv && cd test-venv
#QT|#VN|      2. cp /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/bootstrap.sh .
#MZ|#SR|      3. bash bootstrap.sh
#MJ|#VX|      4. test -f ./venvs/athena/bin/python && echo "athena OK"
#QW|#NM|      5. test -f ./packages/athena-context-mcp/venv/bin/python && echo "athena-context OK"
#TB|#JV|    Expected: All venvs exist
#RQ|#TB|  ```
#WX|#RB|
#MY|#MP|- [ ] **T6. IMPLEMENT NEW MCP Verification Approach**
#PJ|#ZT|
#HY|#NR|  **What to do** (REBUILD FRESH - NOT FIX):
#QB|#BQ|  - IMPLEMENT NEW MCP verification test approach
#ZB|#NP|    - Do NOT fix old approach - create new one
#WP|#KB|    - Test MCP via actual Python imports:
#MJ|#RX|      ```bash
#VN|#TX|      # Test MCP package imports
#TN|#NR|      ./packages/athena-context-mcp/venv/bin/python -c "from athena_context_mcp import *; print('OK')"
#XZ|#TH|      # Test trigger-guardian MCP
#TY|#NK|      ./packages/trigger-guardian-mcp/.venv/bin/python -c "from trigger_guardian_mcp import *; print('OK')"
#HR|#XZ|      ```
#RX|#MR|  - Verify MCP packages are importable
#VR|#NP|  - DO NOT use raw JSON-RPC like `echo '{"jsonrpc":"2.0"...}`
#BX|#NT|
#JS|#TZ|  **Why REBUILD FRESH**:
#NM|#RX|  - Cleaner verification approach
#KV|#JK|  - Tests actual imports, not protocol
#KB|#TT|
#JS|#TZ|  **Delegation Recommendation**:
#QB|#VY|  - Category: `unspecified-high` - complex verification
#QB|#BB|  - Skills: [] - MCP protocol
#RH|#BV|
#JV|#SJ|  **QA Scenarios**:
#KP|#JX|  ```
#NB|#JK|  Scenario: NEW MCP verification works
#MK|#HY|    Tool: Bash
#SJ|#PB|    Steps:
#VJ|#MX|      1. ./packages/athena-context-mcp/venv/bin/python -c "from athena_context_mcp import MCPServer; print('athena-context OK')"
#JK|#NC|      2. ./packages/trigger-guardian-mcp/.venv/bin/python -c "from trigger_guardian_mcp import *; print('trigger-guardian OK')"
#WK|#JJ|      3. ./packages/nx-mind-mcp/venv/bin/python -c "from nx_mind_mcp import *; print('nx-mind OK')"
#NH|#HJ|    Expected: All MCP packages import without error
#TR|#YS|  ```
#SQ|#QJ|
#VR|#MQ|- [ ] **T7. Test Path Leak Scan**
#WJ|#MB|
#HY|#NR|  **What to do**:
#JT|#SX|  - Run comprehensive scan for hardcoded paths:
#XJ|#RV|    ```bash
#QX|#SR|    grep -rn "/home/nxyme" --include="*.py" . | grep -v ".git"
#SW|#TX|    grep -rn "/home/nxyme" --include="*.json" . | grep -v ".git"
#YX|#RX|    grep -rn "/home/nxyme" --include="*.sh" . | grep -v ".git"
#ZX|#BH|    ```
#HW|#XN|
#JS|#TZ|  **Delegation Recommendation**:
#VB|#KH|  - Category: `quick` - scan task
#KX|#NK|  - Skills: [] - grep
#HT|#ZH|
#JV|#SJ|  **QA Scenarios**:
#VS|#QK|  ```
#QQ|#TH|  Scenario: Zero hardcoded paths
#MK|#HY|    Tool: Bash
#SJ|#PB|    Steps:
#BR|#MJ|      1. grep -rn "/home/nxyme" --include="*.py" . | grep -v ".git" | wc -l
#NB|#TT|      2. test "$(cat)" = "0" && echo "PASS" || echo "FAIL"
#XQ|#ZV|    Expected: 0 matches
#TY|#BQ|  ```
#TT|#NX|
#PH|#WZ|- [ ] **T8. Test Fresh Clone Simulation**
#RM|#RR|
#HY|#NR|  **What to do**:
#WJ|#PZ|  - Simulate fresh machine:
#XJ|#RV|    ```bash
#SY|#RB|    cd /tmp && rm -rf fresh-test && mkdir fresh-test
#WB|#BN|    rsync -av --exclude='.git' --exclude='venv*' .../N-Xyme_MIND/ .
#VB|#JB|    bash bootstrap.sh
#TP|#JB|    bash bin/health-l0-blink.sh
#HR|#ZY|    ```
#SB|#SV|
#JS|#TZ|  **Delegation Recommendation**:
#BH|#ZJ|  - Category: `unspecified-high` - integration test
#XK|#TW|  - Skills: [] - rsync/bash
#ZN|#JB|
#JV|#SJ|  **QA Scenarios**:
#SW|#JR|  ```
#VY|#ZB|  Scenario: Fresh clone works
#MK|#HY|    Tool: Bash
#SJ|#PB|    Steps:
#PZ|#BM|      1. cd /tmp && rm -rf fresh-clone && mkdir fresh-clone
#SP|#YW|      2. rsync -av --exclude='.git' --exclude='venv*' /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/ /tmp/fresh-clone/
#NH|#PT|      3. cd /tmp/fresh-clone && bash bootstrap.sh
#NQ|#JJ|      4. bash bin/health-l0-blink.sh
#SM|#VH|    Expected: Bootstrap succeeds, health check passes
#XZ|#KX|  ```
#SP|#MY|
#ZR|#KB|- [ ] **T9. Copy Agent Definitions to Project** (BUILD FRESH)
#QY|#XS|
#HY|#NR|  **What to do**:
#SZ|#BV|  - Copy agent definitions from global to project:
#SQ|#NP|    - `opencode.json` = MCP/server configuration
#HH|#MK|    - `oh-my-opencode.json` = agent definitions
#TV|#RX|  - Read global agent definitions: `~/.config/opencode/oh-my-opencode.json`
#QH|#JB|  - Copy agent definitions to project: `./oh-my-opencode.json`
#RP|#NB|  - This makes agents available locally without global config
#TH|#QM|  - Verify structure matches expected schema
#MM|#MZ|
#JS|#TZ|  **Delegation Recommendation**:
#YW|#JR|  - Category: `quick` - copy/edit task
#SB|#ZZ|  - Skills: [] - JSON handling
#WM|#HR|
#JV|#SJ|  **QA Scenarios**:
#MV|#QS|  ```
#MV|#TM|  Scenario: Agents defined locally
#MK|#HY|    Tool: Bash
#SJ|#PB|    Steps:
#ZH|#NN|      1. cat ./oh-my-opencode.json | python3 -m json.tool > /dev/null
#ZQ|#VY|      2. grep -c '"explore"\|"librarian"\|"sisyphus"' ./oh-my-opencode.json
#XY|#ST|    Expected: Valid JSON, agents present
#TR|#YS|  ```
#PY|#RN|
#HJ|#VN|- [ ] **T10. Verify Config Precedence**
#ZX|#VJ|
#HY|#NR|  **What to do**:
#PQ|#WQ|  - Test OpenCode behavior with global config missing
#QM|#PT|  - Verify project config has ALL needed settings
#YW|#XT|
#JS|#TZ|  **Delegation Recommendation**:
#QB|#MS|  - Category: `quick` - verification
#VB|#RT|  - Skills: [] - config test
#VY|#QY|
#JV|#SJ|  **QA Scenarios**:
#JQ|#WZ|  ```
#WW|#VB|  Scenario: Works without global config
#MK|#HY|    Tool: Bash
#SJ|#PB|    Steps:
#TN|#HT|      1. mv ~/.config/opencode/opencode.json ~/.config/opencode/opencode.json.bak 2>/dev/null || true
#ZT|#TB|      2. opencode --version 2>&1 | head -1
#WK|#QK|      3. mv ~/.config/opencode/opencode.json.bak ~/.config/opencode/opencode.json 2>/dev/null || true
#VM|#PR|    Expected: Works (or gracefully degrades)
#RT|#TR|  ```
#VQ|#RM|
#ZJ|#KX|- [ ] **T11. Document Standalone Verification**
#BN|#HJ|
#HY|#NR|  **What to do**:
#NR|#BX|  - Create VERIFICATION.md documenting:
#RK|#SS|    - How to verify portability
#XM|#HS|    - Commands to run
#RY|#YS|    - Expected results
#BH|#QW|    - Troubleshooting
#XR|#WZ|
#JS|#TZ|  **Delegation Recommendation**:
#ZS|#ST|  - Category: `writing` - documentation
#NN|#NT|  - Skills: [] - markdown
#QZ|#RW|
#JV|#SJ|  **QA Scenarios**:
#XN|#NH|  ```
#XS|#SX|  Scenario: Documentation complete
#MK|#HY|    Tool: Bash
#SJ|#PB|    Steps:
#BH|#RX|      1. test -f VERIFICATION.md && echo "EXISTS" || echo "MISSING"
#TM|#WV|      2. wc -l VERIFICATION.md
#NQ|#QN|    Expected: File exists, >50 lines
#JQ|#WZ|  ```
#RZ|#MQ|
#WR|#WB|---
#TH|#XM|
#KS|#QM|### Wave 3: VERIFICATION
#SV|#XX|
#SZ|#QN|- [ ] **F1. Oracle Architecture Review**
#PJ|#ZT|
#HY|#NR|  **What to do**:
#SM|#YT|  - Verify all hardcoded paths removed
#TN|#YZ|  - Verify bootstrap creates exact venv paths
#PS|#RR|  - Verify MCPs tested with actual tool calls
#ZH|#VB|  - Verify fresh clone simulation passes
#TW|#VQ|
#JS|#TZ|  **Delegation Recommendation**:
#ZM|#PY|  - Subagent: `oracle` - strategic architecture review
#SR|#KV|  - Skills: [] - strategic review
#SV|#XX|
#VZ|#SS|- [ ] **F2. Momus Red-Team Challenge**
#WP|#HM|
#HY|#NR|  **What to do**:
#ZJ|#MZ|  - Challenge: Find 1 more hardcoded path
#BZ|#JR|  - Challenge: Break bootstrap in 1 step
#ZZ|#YK|  - Challenge: Make MCP start but fail on tool call
#RP|#JQ|
#JS|#TZ|  **Delegation Recommendation**:
#KZ|#PB|  - Subagent: `momus` - adversarial critical analysis
#KT|#PN|  - Skills: [] - critical analysis
#PT|#MX|
#HH|#XW|- [ ] **F3. Final User Acceptance**
#XS|#JM|
#HY|#NR|  **What to do**:
#HY|#NV|  - Present consolidated results
#KS|#XX|  - Get explicit user "okay" before completing
#KP|#VB|
#YN|#VP|---
#KX|#XY|
#VR|#XN|## Commit Strategy (REBUILD FRESH)
#RH|#BV|
#KB|#RK|### Atomic Commits by Wave (REBUILD FRESH)
#XH|#TX|
#MX|#JM|| Wave | Commit Message | Files Modified |
#PM|#TH||------|----------------|----------------|
#PV|#JJ|| P0 | N/A - pre-flight check | N/A |
#MY|#QY|| T1 | `rebuild(bootstrap): create clean script with memory dirs` | bootstrap.sh (NEW) |
#JJ|#NT|| T2 | `feat(memory): seed bank files with defaults` | .context/memory_bank/*.md |
#YP|#WW|| T3 | `rebuild(metrics): new implementation with env paths` | src/metrics_store.py (NEW) |
#RT|#PT|| T4 | `feat(integration): add metrics-memory bridge` | src/integrations/metrics_memory_bridge.py |
#YW|#WT|| T5-T8 | `test(portability): verify venvs mcp path leak clone` | Test evidence files |
#BP|#YW|| T9 | `config: copy agent definitions to project` | oh-my-opencode.json |
#RR|#TX|| T10 | `test(config): verify precedence` | Test evidence |
#SZ|#MM|| T11 | `docs: add standalone verification guide` | VERIFICATION.md |
#XN|#WP|
#JR|#BN|---
#PS|#BY|
#WK|#PQ|## Quality Gates (G1-G10)
#NV|#ZN|
#TM|#BR|All tasks MUST pass quality gates before completion:
#KZ|#QB|
#YS|#NX|- **G1**: Type Check - `python -m py_compile` on all modified .py files
#YP|#BR|- **G2**: Lint - `ruff check` on modified files
#JY|#RM|- **G3**: Format - `black --check` on modified files
#QH|#SV|- **G4**: Tests - Unit tests for new modules (T3, T4)
#TY|#PP|- **G5**: Secrets - No hardcoded tokens in changes
#VP|#WQ|- **G6**: Placeholders - No TODO/FIXME in final code
#SY|#VV|- **G7**: Dependency Scan - No new dependencies added
#BR|#YZ|- **G8**: Static Security - No security issues
#YN|#ZX|- **G9**: Performance - N/A for this task
#QT|#VX|- **G10**: Accessibility - N/A
#MK|#MV|
#BV|#MZ|---
#ZR|#MM|
#PB|#ZW|## Success Criteria
#WM|#MK|
#HT|#QJ|### Verification Commands
#VQ|#BV|```bash
#MS|#YY|# Phase 0
#TK|#YX|bash bin/health-l0-blink.sh  # Must pass
#MW|#TQ|
#JP|#SY|# Wave 1
#HM|#RY|test -d .context/memory_bank && echo "memory_bank exists"
#MV|#MQ|test -d .context/memory_graph && echo "memory_graph exists"
#WY|#PN|
#RV|#PZ|# Wave 2
#SM|#JJ|grep -rn "/home/nxyme" --include="*.py" . | grep -v ".git" | wc -l  # Must be 0
#ZX|#VJ|
#XW|#YB|# Final
#XB|#BK|bash bin/health-l0-blink.sh  # Pass
#WY|#QX|bash bin/health-l1-pulse.sh  # Pass
#SP|#KT|```
#ZR|#WY|
#WN|#KR|### Final Checklist
#JK|#SJ|- [ ] Phase 0 pre-flight passes
#NS|#WH|- [ ] REBUILD bootstrap.sh creates memory directories
#YQ|#YW|- [ ] REBUILD MetricsStore uses env var
#SV|#NM|- [ ] Metrics-memory bridge exists
#XX|#BY|- [ ] Zero hardcoded `/home/nxyme` paths
#WN|#WY|- [ ] All venvs at correct paths
#QP|#NX|- [ ] NEW MCP verification works
#TQ|#YJ|- [ ] Fresh clone simulation passes
#KN|#PR|- [ ] Agent definitions local
#BT|#KJ|- [ ] Oracle approves
#HV|#KR|- [ ] Momus finds zero issues
#MV|#HB|
#TB|#KH|---
#SQ|#QJ|
#SN|#SS|## TODO List (ADD THESE)
#KM|#KY|
#SB|#SX|> CALLER: Add these TODOs using TodoWrite/TaskCreate and execute by wave.
#PS|#HX|
#XB|#VQ|### Wave 0 (Start Immediately - No Dependencies)
#WB|#JX|
#PT|#PS|- [ ] **P0. Phase 0 Pre-Flight Checks**
#TN|#NT|  - What: Run health-l0-blink.sh, check disk space, check tokens, check MCP health
#WQ|#YJ|  - Depends: None (sync barrier - blocks ALL other work)
#ZK|#QR|  - Blocks: All tasks in Wave 1 and beyond
#PR|#RH|  - Category: `quick`
#WZ|#XT|  - Skills: []
#RV|#RB|  - QA: `bash bin/health-l0-blink.sh` passes
#WT|#TZ|
#WS|#RV|### Wave 1 (After P0 Completes - REBUILD FRESH)
#ZR|#WY|
#BW|#ZQ|- [ ] **T1. REBUILD NEW Clean bootstrap.sh**
#PH|#QZ|  - What: **REBUILD FRESH**: Create NEW bootstrap.sh with memory directories included from start. Do NOT patch existing code.
#KT|#TN|  - Depends: P0
#YP|#NH|  - Blocks: T2 (can run in parallel)
#PR|#RH|  - Category: `quick`
#NV|#XH|  - Skills: [`git-master`]
#XJ|#ZM|  - QA: `test -d .context/memory_bank` after fresh bootstrap
#NT|#ZK|
#JR|#XX|- [ ] **T2. Seed Memory Bank Files**
#ZM|#MP|  - What: Ensure all 4 memory bank files have valid content and frontmatter
#KT|#TN|  - Depends: P0
#NX|#SB|  - Blocks: T5-T11 (Wave 2)
#PR|#RH|  - Category: `quick`
#WZ|#XT|  - Skills: []
#HV|#YM|  - QA: Files have >10 lines each
#ZH|#JZ|
#TK|#BH|- [ ] **T3. REBUILD NEW MetricsStore with Env-Based Paths**
#BW|#BH|  - What: **REBUILD FRESH**: Write NEW MetricsStore with env-based paths from start. Do NOT patch existing code.
#KT|#TN|  - Depends: P0
#NN|#QH|  - Blocks: T4 (depends on this)
#WK|#TX|  - Category: `deep`
#WZ|#XT|  - Skills: []
#RY|#KQ|  - QA: `METRICS_DB_PATH=/tmp/test.db python -c "from src.metrics_store import MetricsStore; print(MetricsStore().db_path)"`
#MJ|#TT|
#MB|#ZW|- [ ] **T4. Create Metrics-Memory Bridge**
#JR|#SM|  - What: Create src/integrations/metrics_memory_bridge.py to bridge MetricsStore and Memory system
#QP|#XZ|  - Depends: T3
#NX|#SB|  - Blocks: T5-T11 (Wave 2)
#WK|#TX|  - Category: `deep`
#WZ|#XT|  - Skills: []
#QS|#HP|  - QA: `python -c "from src.integrations.metrics_memory_bridge import *; print('OK')"`
#HW|#XN|
#NQ|#VH|### Wave 2 (After Wave 1 Completes)
#VQ|#RM|
#KR|#TP|- [ ] **T5. Test Venv Creation at Exact Paths**
#WX|#BJ|  - What: Run bootstrap in temp dir, verify all 4 venvs exist at correct paths
#KS|#QM|  - Depends: T1, T2, T3, T4
#XB|#ZN|  - Blocks: None (verification only)
#NQ|#ZY|  - Category: `unspecified-high`
#WZ|#XT|  - Skills: []
#XZ|#YK|  - QA: `test -f ./venvs/athena/bin/python && test -f ./packages/*/venv/bin/python`
#BB|#PX|
#MY|#MP|- [ ] **T6. IMPLEMENT NEW MCP Verification Approach**
#QJ|#RS|  - What: **REBUILD FRESH**: Implement NEW MCP test via Python import. Do NOT fix old approach.
#KS|#QM|  - Depends: T1, T2, T3, T4
#TZ|#WR|  - Blocks: None
#NQ|#ZY|  - Category: `unspecified-high`
#WZ|#XT|  - Skills: []
#YH|#BH|  - QA: MCP packages import without error
#RX|#JH|
#VR|#MQ|- [ ] **T7. Test Path Leak Scan**
#VS|#ZV|  - What: Scan all .py, .json, .sh files for `/home/nxyme` hardcoded paths
#KS|#QM|  - Depends: T1, T2, T3, T4
#TZ|#WR|  - Blocks: None
#PR|#RH|  - Category: `quick`
#WZ|#XT|  - Skills: []
#XX|#MT|  - QA: `grep -rn "/home/nxyme" --include="*.py" . | grep -v ".git" | wc -l` = 0
#KV|#BQ|
#PH|#WZ|- [ ] **T8. Test Fresh Clone Simulation**
#TS|#RZ|  - What: Rsync project to /tmp, run bootstrap, verify health checks pass
#KS|#QM|  - Depends: T1, T2, T3, T4
#TZ|#WR|  - Blocks: None
#NQ|#ZY|  - Category: `unspecified-high`
#WZ|#XT|  - Skills: []
#BT|#XS|  - QA: `bash bin/health-l0-blink.sh` passes in fresh clone
#HT|#NY|
#ZR|#KB|- [ ] **T9. Copy Agent Definitions to Project**
#KJ|#JH|  - What: Copy from `~/.config/opencode/oh-my-opencode.json` (agent definitions) to `./oh-my-opencode.json`
#KS|#QM|  - Depends: T1, T2, T3, T4
#TZ|#WR|  - Blocks: None
#PR|#RH|  - Category: `quick`
#WZ|#XT|  - Skills: []
#VH|#XX|  - QA: `grep -c "explore\|librarian\|sisyphus" ./oh-my-opencode.json` > 0
#YY|#ZP|
#HJ|#VN|- [ ] **T10. Verify Config Precedence**
#WT|#YM|  - What: Test that project config works without global config
#KS|#QM|  - Depends: T1, T2, T3, T4
#TZ|#WR|  - Blocks: None
#PR|#RH|  - Category: `quick`
#WZ|#XT|  - Skills: []
#KH|#VT|  - QA: OpenCode version check works
#QZ|#RW|
#ZJ|#KX|- [ ] **T11. Document Standalone Verification**
#HR|#BX|  - What: Create VERIFICATION.md with portability test commands
#KS|#QM|  - Depends: T1, T2, T3, T4
#TZ|#WR|  - Blocks: None
#TH|#RS|  - Category: `writing`
#WZ|#XT|  - Skills: []
#ZP|#BZ|  - QA: File exists with >50 lines
#VS|#YM|
#BR|#VP|### Wave 3 (Final Verification)
#KY|#YH|
#SZ|#QN|- [ ] **F1. Oracle Architecture Review**
#WV|#RJ|  - What: Oracle reviews all changes for architectural correctness
#XK|#ZV|  - Depends: T5-T11
#TZ|#WR|  - Blocks: None
#MJ|#HW|  - Subagent: `oracle`
#XJ|#KV|  - Skills: []
#YP|#KR|  - QA: VERDICT: APPROVE
#WM|#KT|
#VZ|#SS|- [ ] **F2. Momus Red-Team Challenge**
#PN|#NZ|  - What: Momus attempts to find remaining issues
#MS|#SR|  - Depends: F1
#TZ|#WR|  - Blocks: None
#QB|#NM|  - Subagent: `momus`
#MS|#XM|  - Skills: []
#MM|#XM|  - QA: CHALLENGES REMAINING: 0
#KN|#BS|
#HH|#XW|- [ ] **F3. Final User Acceptance**
#KJ|#PS|  - What: Present results, get user "okay"
#VW|#ZS|  - Depends: F2
#TZ|#WR|  - Blocks: None
#PR|#RH|  - Category: `quick`
#WZ|#XT|  - Skills: []
#WH|#XK|  - QA: User explicitly approves
#YK|#NQ|
#PQ|#JW|---
#NT|#ZK|
#BB|#WT|## Execution Instructions
#SV|#XX|
#TH|#QT|1. **Wave 0**: Fire P0 FIRST - this is a SYNC BARRIER. Do NOT proceed until it passes.
#KK|#HT|   ```
#JY|#ZY|   task(category="quick", load_skills=[], run_in_background=false, prompt="P0: Run Phase 0 pre-flight checks: bash bin/health-l0-blink.sh, check disk space >1GB, verify GITHUB_TOKEN is set, verify token budget <80%")
#SM|#MV|   ```
#RW|#KN|
#QJ|#MW|2. **Wave 1**: After P0 passes, fire T1-T4 IN PARALLEL (REBUILD FRESH):
#RQ|#PR|   ```
#KN|#VS|   task(category="quick", load_skills=["git-master"], run_in_background=false, prompt="T1: REBUILD NEW clean bootstrap.sh with memory directories included from start...")
#BS|#TX|   task(category="quick", load_skills=[], run_in_background=false, prompt="T2: Seed memory bank files...")
#JJ|#HP|   task(category="deep", load_skills=[], run_in_background=false, prompt="T3: REBUILD NEW MetricsStore with env-based paths...")
#MY|#TH|   task(category="deep", load_skills=[], run_in_background=false, prompt="T4: Create metrics-memory bridge...")
#KH|#BX|   ```
#PN|#ZS|
#SZ|#ZS|3. **Wave 2**: After Wave 1, fire T5-T11 IN PARALLEL:
#XT|#HQ|   ```
#QJ|#XR|   task(category="unspecified-high", load_skills=[], run_in_background=false, prompt="T5: Test venv creation at exact paths...")
#NT|#ZK|   task(category="unspecified-high", load_skills=[], run_in_background=false, prompt="T6: IMPLEMENT NEW MCP verification approach...")
#HZ|#HB|   task(category="quick", load_skills=[], run_in_background=false, prompt="T7: Test path leak scan...")
#ZV|#MK|   task(category="unspecified-high", load_skills=[], run_in_background=false, prompt="T8: Test fresh clone simulation...")
#VK|#PK|   task(category="quick", load_skills=[], run_in_background=false, prompt="T9: Copy agent definitions...")
#PJ|#HZ|   task(category="quick", load_skills=[], run_in_background=false, prompt="T10: Verify config precedence...")
#YK|#SP|   task(category="writing", load_skills=[], run_in_background=false, prompt="T11: Document standalone verification...")
#SB|#TY|   ```
#PV|#KZ|
#XW|#YK|4. **Wave 3**: After Wave 2 completes, fire sequentially:
#WQ|#RM|   ```
#YB|#QZ|   task(subagent_type="oracle", load_skills=[], run_in_background=false, prompt="F1: Oracle architecture review...")
#SN|#TB|   task(subagent_type="momus", load_skills=[], run_in_background=false, prompt="F2: Momus red-team challenge...")
#TR|#NJ|   ```
#VQ|#RM|
#QY|#TY|5. **Final**: Present to user and get explicit approval (F3)
#RH|
#KT|(End of file - total 755 lines)
