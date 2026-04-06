# N-Xyme MIND Sprint 5: Consolidated Core System

## TL;DR

> **Goal**: Build a working standalone AI coding workspace by copying proven MIT-licensed code and completing the 3 existing MCP packages.
> 
> **Key Changes**: Reduced from 25 tasks to 6 tasks based on Metis/Momus/Oracle/Explore/Librarian feedback.
> 
> **Scope**: Copy Governance, Sentinel, Flight Recorder, Skill Telemetry, DeltaManifest from source repos. Complete 3 MCP packages. Skip LayerStack (spec-only) and Memory Cortex (failed before).
> 
> **Estimated Effort**: Short (6 tasks, 2-3 weeks)
> **Parallel Execution**: YES - Wave 3 has 3 parallel tasks
> **Critical Path**: Task 1 → Task 2 → Task 3 → Task 6

---

## Context

### Original Request
Build N-Xyme MIND as a standalone, portable, self-healing AI coding workspace using OpenCode as reference.

### Agent Synthesis (5 Agents Consulted)

| Agent | Key Finding | Applied To Plan |
|-------|-------------|-----------------|
| **Metis** | src/ has 177 files of unrelated bloat (audio/video/music) | Added quarantine task |
| **Momus** | Athena MCP gap, github-mcp bundling missing, hindsight MCP not addressed | Fixed all 5 critical issues |
| **Oracle** | Build Sentinel first, skip LayerStack forever, use JSON files for memory | Applied strategic guidance |
| **Librarian** | 6 missing patterns (Context Compaction, Circuit Breaker, Lifecycle Hooks) | Documented for Sprint 6+ |
| **Explore** | LayerStack NOT in codebase, no circular dependencies | Confirmed what's real |

### Research Complete

**Source Repositories (MIT Licensed)**:
- `nx_openmore`: Governance Engine (315 lines), Sentinel (97 lines), Flight Recorder (49 lines), Skill Telemetry (224 lines), DeltaManifest (155 lines)
- `N-Xyme_CATALYST`: 3 existing MCP packages (athena-context, nx-mind, trigger-guardian)

**What Exists in Workspace**:
- ✅ `vpn/rotator.py` (863 lines) - Working VPN rotator
- ✅ `src/trigger_engine.py` (300 lines) - Working trigger engine
- ✅ `tests/integration/test_core.py` - 4 passing tests
- ✅ `bootstrap.sh` - Working installer
- ⚠️ `src/` - 177 files (100+ are unrelated bloat)

**What NOT in Workspace**:
- ❌ Governance Engine (in source repo only)
- ❌ Sentinel Protocol (in source repo only)
- ❌ Flight Recorder (in source repo only)
- ❌ Skill Telemetry (in source repo only)
- ❌ DeltaManifest (in source repo only)

### Metis Critical Directives (Applied)

- ✅ MUST: Limit to 6 HIGH-IMPACT tasks
- ✅ MUST: Every task independently testable
- ✅ MUST: Copy proven code, don't reinvent
- ✅ MUST NOT: Touch unrelated src/ files (quarantine them)
- ✅ MUST NOT: Implement LayerStack (spec-only, deprecated)
- ✅ MUST NOT: Implement Memory Cortex (failed before)
- ✅ MUST: All MCPs = local stdio only
- ✅ MUST: Python-only implementation

### Momus Issues Fixed

1. ✅ **Athena MCP gap**: Explicitly addressed - keep as separate venv
2. ✅ **github-mcp bundling**: Added Task 5
3. ✅ **Wave 2 structure**: Fixed parallelization
4. ✅ **hindsight_mcp**: Added to graceful degradation
5. ✅ **T1 test scope**: Clarified what to test

### Oracle Strategic Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Build first? | Sentinel Protocol | Boot/shutdown lifecycle is prerequisite |
| Copy vs create? | COPY ALL | Proven code, no reinventing |
| LayerStack? | SKIP FOREVER | Spec-only, complexity without value |
| Memory? | JSON + markdown files | Simpler than cortex, WILL work |
| Exit criteria? | "Runs + tests pass" | NOT "perfect" |

---

## Work Objectives

### Core Objective
Consolidate N-Xyme MIND workspace by:
1. Removing dead code
2. Copying proven systems from source repos
3. Completing 3 existing MCP packages
4. Adding github-mcp bundling
5. Verifying everything works together

### Concrete Deliverables
- [ ] `src/governance.py` - Doom Loop + Triple-Lock + Risk classification
- [ ] `src/sentinel.py` - Boot/shutdown checks
- [ ] `src/flight_recorder.py` - JSONL audit trail
- [ ] `src/skill_telemetry.py` - Usage tracking
- [ ] `src/delta_manifest.py` - O(1) file sync
- [ ] 3 MCP packages functional (athena-context, nx-mind, trigger-guardian)
- [ ] github-mcp bundled
- [ ] 40+ tests passing
- [ ] bootstrap.sh verified

### Definition of Done
- [ ] `pytest tests/ -v` passes all tests (40+)
- [ ] All MCPs start via stdio
- [ ] `bin/health-check` exits 0
- [ ] `bin/trigger-status` exits 0
- [ ] `bin/verify-install` exits 0

### Must Have
- Python-only (no npm for MCPs)
- Local stdio MCPs (no network)
- Single venv preferred
- All code from MIT-licensed sources

### Must NOT Have (Guardrails from Oracle)
- ❌ LayerStack (spec-only, deprecated)
- ❌ Memory Cortex (failed before, will fail again)
- ❌ Neo4j/PostgreSQL dependencies
- ❌ Kubernetes/Helm deployment
- ❌ Voice-first architecture
- ❌ New MCP servers (3 is the limit)

### AI Slop Patterns to Avoid (from Metis)
- ❌ "Also tests for adjacent modules" - Keep tests scoped
- ❌ "Extracted to utility" - Inline is fine for small code
- ❌ "15 error checks for 3 inputs" - Minimal error handling
- ❌ "Added JSDoc everywhere" - Minimal docs

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation - Start Immediately):
└── Task 1: Clean & Validate (no dependencies)

Wave 2 (After Wave 1):
└── Task 2: Copy Core Systems (5 files from source repos)

Wave 3 (After Wave 2 - 3 tasks in PARALLEL):
├── Task 3: Complete 3 MCP Packages
├── Task 4: Wire Trigger Engine
└── Task 5: Bundle github-mcp

Wave 4 (After Wave 3):
└── Task 6: Integration Tests + Bootstrap Verification

Critical Path: Task 1 → Task 2 → Task 3 → Task 6
Parallel Speedup: ~30% faster (Wave 3)
Max Concurrent: 3 (Wave 3)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| Task 1 | — | Task 2 |
| Task 2 | Task 1 | Tasks 3, 4, 5 |
| Task 3 | Task 2 | Task 6 |
| Task 4 | Task 2 | Task 6 |
| Task 5 | Task 2 | Task 6 |
| Task 6 | Tasks 3, 4, 5 | — |

---

## TODOs

### Wave 1: Foundation

- [ ] **1. Foundation Cleanup**

  **What to do**:
  1. Remove dead MCP entries from `opencode.json`:
     - `athena` (broken path `./venvs/athena/bin/python`)
     - `unified-memory` (broken path `./venvs/athena/bin/python`)
     - `github` (optional, non-Python)
  2. Quarantine unrelated files from `src/` to `src/deprecated/`:
     - Audio: `arpeggiator.py`, `beat_detector.py`, `drum_machine.py`, `reverb_simulator.py`, etc.
     - Video: `video_export.py`, `video_processor.py`, `gif_creator.py`, etc.
     - Music: `chord_progression.py`, `midi_fx_chain.py`, `melody_generator.py`, etc.
     - Image: `image_processor.py`, `qr_generator.py`, `svg_renderer.py`, etc.
  3. Keep in `src/`:
     - `trigger_engine.py`
     - `trigger_router.py`
     - `athena_bridge.py`
     - `athena_executor.py`
     - `catalyst.py`
     - `athena/` (governance, sentinel, flight_recorder, skill_telemetry, delta_manifest)
  4. Remove dead Makefile targets: Neo4j, PM2, Fusion Bridge, Security Agent
  5. Add hindsight MCP to graceful degradation: log warning that PostgreSQL required
  6. Verify existing tests pass: `pytest tests/integration/test_core.py -v`

  **Must NOT do**:
  - Do NOT delete quarantined files (just move)
  - Do NOT modify `packages/` directory
  - Do NOT modify `_bmad/` directory
  - Do NOT modify `vpn/` directory
  - Do NOT modify `triggers.json`

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Cleanup work, straightforward file moves
  - **Skills**: `git-master` for proper git tracking

  **Parallelization**:
  - **Can Run In Parallel**: NO (sequential cleanup)
  - **Blocks**: Task 2

  **References**:
  - `opencode.json` — MCP server configuration
  - `Makefile` — Build targets to clean
  - `src/` — Directory to quarantine

  **Acceptance Criteria**:
  - [ ] `opencode.json` has ≤ 8 MCP entries (removed: athena, unified-memory, github)
  - [ ] `src/deprecated/` exists with quarantined files
  - [ ] `src/` contains only core infrastructure files
  - [ ] `Makefile` has no Neo4j/PM2/Fusion Bridge/Security Agent targets
  - [ ] `pytest tests/integration/test_core.py -v` passes 4/4
  - [ ] `git status` shows clean after quarantine commit

  **QA Scenarios**:

  ```
  Scenario: opencode.json has correct MCP entries
    Tool: Bash
    Preconditions: Clean workspace
    Steps:
      1. python -c "import json; cfg = json.load(open('opencode.json')); print([m['name'] for m in cfg.get('mcpServers', {}).values()])"
    Expected Result: List of ≤ 8 MCP server names
    Evidence: .sisyphus/evidence/task-01-mcp-list.txt

  Scenario: Quarantined files moved correctly
    Tool: Bash
    Preconditions: Quarantine complete
    Steps:
      1. ls src/deprecated/*.py | wc -l
    Expected Result: Count > 100 (majority of src/)
    Evidence: .sisyphus/evidence/task-01-quarantine-count.txt
  ```

  **Commit**: YES
  - Message: `chore: quarantine dead code and fix MCP configuration`
  - Files: `opencode.json`, `Makefile`, `src/deprecated/`, `.gitignore`

---

### Wave 2: Core Systems

- [ ] **2. Copy Core Systems from Source Repos**

  **What to do**:
  1. Copy from `/mnt/Library/nx_openmore/athena/src/athena/`:
     - `core/governance.py` → `src/athena/core/governance.py` (315 lines)
     - `core/flight_recorder.py` → `src/athena/core/flight_recorder.py` (49 lines)
     - `core/skill_telemetry.py` → `src/athena/core/skill_telemetry.py` (224 lines)
     - `memory/delta_manifest.py` → `src/athena/memory/delta_manifest.py` (155 lines)
     - `intelligence/sentinel.py` → `src/athena/intelligence/sentinel.py` (97 lines)
  2. Update imports in copied files to use local paths
  3. Create unit tests for each system:
     - `tests/unit/test_governance.py` (minimum 5 tests)
     - `tests/unit/test_sentinel.py` (minimum 4 tests)
     - `tests/unit/test_flight_recorder.py` (minimum 3 tests)
     - `tests/unit/test_skill_telemetry.py` (minimum 4 tests)
     - `tests/unit/test_delta_manifest.py` (minimum 5 tests)
  4. All tests must pass

  **Must NOT do**:
  - Do NOT modify copied code (just adapt imports)
  - Do NOT add features not in original
  - Do NOT create new systems

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Reason**: Copying code requires understanding dependencies
  - **Skills**: None required

  **Parallelization**:
  - **Can Run In Parallel**: NO (sequential copy + test)
  - **Blocks**: Tasks 3, 4, 5

  **References**:
  - `/mnt/Library/nx_openmore/athena/src/athena/core/governance.py` — Doom Loop + Triple-Lock
  - `/mnt/Library/nx_openmore/athena/src/athena/intelligence/sentinel.py` — Boot/shutdown checks
  - `/mnt/Library/nx_openmore/athena/src/athena/core/flight_recorder.py` — JSONL audit
  - `/mnt/Library/nx_openmore/athena/src/athena/core/skill_telemetry.py` — Usage tracking
  - `/mnt/Library/nx_openmore/athena/src/athena/memory/delta_manifest.py` — O(1) sync

  **Acceptance Criteria**:
  - [ ] `python -c "from src.athena.core.governance import GovernanceEngine"` → no error
  - [ ] `python -c "from src.athena.intelligence.sentinel import check_boot_sentinel"` → no error
  - [ ] `python -c "from src.athena.core.flight_recorder import record_action"` → no error
  - [ ] `python -c "from src.athena.core.skill_telemetry import get_skill_stats"` → no error
  - [ ] `python -c "from src.athena.memory.delta_manifest import DeltaManifest"` → no error
  - [ ] `pytest tests/unit/test_governance.py -v` → ≥5 tests pass
  - [ ] `pytest tests/unit/test_sentinel.py -v` → ≥4 tests pass
  - [ ] `pytest tests/unit/test_flight_recorder.py -v` → ≥3 tests pass
  - [ ] `pytest tests/unit/test_skill_telemetry.py -v` → ≥4 tests pass
  - [ ] `pytest tests/unit/test_delta_manifest.py -v` → ≥5 tests pass
  - [ ] `pytest tests/ -v` → ≥25 tests pass (all existing + new)

  **QA Scenarios**:

  ```
  Scenario: Governance Engine imports correctly
    Tool: Bash
    Preconditions: Files copied
    Steps:
      1. python -c "from src.athena.core.governance import GovernanceEngine, DoomLoopDetector, RiskLevel; print('OK')"
    Expected Result: "OK" printed, no ImportError
    Evidence: .sisyphus/evidence/task-02-governance-import.txt

  Scenario: Sentinel Protocol imports correctly
    Tool: Bash
    Preconditions: Files copied
    Steps:
      1. python -c "from src.athena.intelligence.sentinel import check_boot_sentinel, check_shutdown_sentinel; print('OK')"
    Expected Result: "OK" printed, no ImportError
    Evidence: .sisyphus/evidence/task-02-sentinel-import.txt

  Scenario: Doom Loop detection works
    Tool: Bash
    Preconditions: Governance imported
    Steps:
      1. python -c "from src.athena.core.governance import DoomLoopDetector; d = DoomLoopDetector(); print([d.check('tool', {}) for _ in range(3)])"
    Expected Result: [False, False, True]
    Evidence: .sisyphus/evidence/task-02-doom-loop.txt
  ```

  **Commit**: YES
  - Message: `feat: import core systems from nx_openmore`
  - Files: `src/athena/core/governance.py`, `src/athena/core/flight_recorder.py`, `src/athena/core/skill_telemetry.py`, `src/athena/memory/delta_manifest.py`, `src/athena/intelligence/sentinel.py`, `tests/unit/test_*.py`

---

### Wave 3: MCPs + Integration (Parallel)

- [ ] **3. Complete 3 MCP Packages**

  **What to do**:
  1. **athena-context-mcp** (7 tools):
     - `get_active_context` — read `.context/activeContext.md`
     - `get_product_context` — read `.context/productContext.md`
     - `get_user_context` — read `.context/userContext.md`
     - `get_constraints` — read `.context/constraints.md`
     - `get_bmad_agents` — read `_bmad/_config/agents/`
     - `get_bmad_workflows` — read `_bmad/*/workflows/`
     - `inject_context` — write context to session
  2. **nx-mind-mcp** (7 tools):
     - `get_mind_state` — read `.context/mind-state.json`
     - `update_mind_state` — write to mind-state.json
     - `get_session_history` — read session logs
     - `get_active_workflow` — scan `_bmad/catalyst/`
     - `set_context` — set context key-value
     - `sync_to_memory` — sync to memory MCP
     - `get_project_manifest` — read `.context/project-manifest.json`
  3. **trigger-guardian-mcp** (6 tools):
     - `register_trigger` — add to triggers.json
     - `list_triggers` — read triggers.json
     - `check_trigger` — match input against triggers
     - `get_trigger_handlers` — get handlers for trigger
     - `log_trigger_event` — log to event history
     - `clear_triggers` — reset triggers.json
  4. Wire each MCP to FastMCP framework
  5. Create unit tests for each MCP

  **Must NOT do**:
  - Do NOT add new MCPs (3 is the limit)
  - Do NOT use network MCPs
  - Do NOT modify source repos

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Reason**: MCP implementation requires FastMCP knowledge
  - **Skills**: None required

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 4, 5)
  - **Blocks**: Task 6

  **References**:
  - `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/trigger-guardian-mcp/` — Current skeleton
  - `/mnt/NXYME_CORE/00_N-Xyme_CATALYST/mcp-servers/session-manager/` — Reference implementation
  - `.context/` — Context files
  - `triggers.json` — Trigger definitions

  **Acceptance Criteria**:
  - [ ] `python -m packages.athena_context_mcp` starts without error
  - [ ] `python -m packages.nx_mind_mcp` starts without error
  - [ ] `python -m packages.trigger_guardian_mcp` starts without error
  - [ ] Each MCP responds to `tools/list` with correct count
  - [ ] `pytest tests/unit/test_athena_context_mcp.py -v` → ≥5 tests
  - [ ] `pytest tests/unit/test_nx_mind_mcp.py -v` → ≥5 tests
  - [ ] `pytest tests/unit/test_trigger_guardian_mcp.py -v` → ≥4 tests

  **QA Scenarios**:

  ```
  Scenario: athena-context-mcp starts and lists tools
    Tool: Bash
    Preconditions: MCP package installed
    Steps:
      1. echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | timeout 5 python -m packages.athena_context_mcp 2>/dev/null | head -1
    Expected Result: Valid JSON-RPC response
    Evidence: .sisyphus/evidence/task-03-athena-mcp-init.txt
  ```

  **Commit**: YES (with Task 4, 5)
  - Message: `feat: complete MCP package implementations`
  - Files: `packages/athena_context_mcp/`, `packages/nx_mind_mcp/`, `packages/trigger_guardian_mcp/`

---

- [ ] **4. Wire Trigger Engine to Core Systems**

  **What to do**:
  1. Add trigger actions to `src/trigger_engine.py`:
     - `run_sentinel_boot` → calls `check_boot_sentinel()`
     - `run_sentinel_shutdown` → calls `check_shutdown_sentinel()`
     - `record_flight` → calls `record_action()`
     - `log_skill_usage` → calls `log_skill_invocation()`
     - `check_governance` → calls `GovernanceEngine.verify()`
  2. Update `triggers.json` with new trigger definitions
  3. Create `bin/health-check` script:
     - Runs all sentinel checks
     - Reports system health
     - Exits 0 if healthy, 1 if issues
  4. Create `bin/trigger-status` (enhance existing):
     - Shows registered trigger count
     - Shows last execution time
     - Shows system health summary

  **Must NOT do**:
  - Do NOT add complex workflows
  - Do NOT add new trigger systems
  - Do NOT modify core system implementations

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Reason**: Wiring multiple systems
  - **Skills**: None required

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 3, 5)
  - **Blocks**: Task 6

  **References**:
  - `src/trigger_engine.py` — Current trigger implementation
  - `src/athena/intelligence/sentinel.py` — Sentinel interface
  - `src/athena/core/flight_recorder.py` — Flight recorder interface

  **Acceptance Criteria**:
  - [ ] `python -m src.trigger_engine --list` shows ≥ 12 triggers
  - [ ] `bin/health-check` exits 0
  - [ ] `bin/trigger-status` exits 0
  - [ ] `pytest tests/unit/test_trigger_engine_wiring.py -v` → ≥5 tests

  **QA Scenarios**:

  ```
  Scenario: Health check runs and reports status
    Tool: Bash
    Preconditions: Script exists
    Steps:
      1. bin/health-check
    Expected Result: Exit code 0, output shows health summary
    Evidence: .sisyphus/evidence/task-04-health-check.txt
  ```

---

- [ ] **5. Bundle github-mcp Binary**

  **What to do**:
  1. Create `bin/download-github-mcp.sh`:
     - Detect platform (linux/darwin)
     - Download from GitHub releases
     - Verify checksum
     - Store version in `bin/.github-mcp-version`
  2. Add to `bootstrap.sh`:
     - Call download script if github-mcp not present
     - Handle offline gracefully (skip with warning)
  3. Update `opencode.json`:
     - Add `github` MCP back with correct path
     - Set optional: true (graceful degradation if missing)
  4. Test on clean environment

  **Must NOT do**:
  - Do NOT commit the binary to git
  - Do NOT hardcode version (use `.github-mcp-version`)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Simple download + config
  - **Skills**: None required

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 3, 4)
  - **Blocks**: Task 6

  **References**:
  - GitHub releases: `https://github.com/github/github-mcp-server/releases`
  - `bootstrap.sh` — Existing installer

  **Acceptance Criteria**:
  - [ ] `bin/download-github-mcp.sh` downloads correct binary
  - [ ] `bin/.github-mcp-version` exists after download
  - [ ] `opencode.json` github entry has `optional: true`
  - [ ] Bootstrap works offline (skips github-mcp with warning)

  **QA Scenarios**:

  ```
  Scenario: Download script detects platform and downloads
    Tool: Bash
    Preconditions: Clean environment
    Steps:
      1. bin/download-github-mcp.sh
      2. ls -la bin/github-mcp-server 2>/dev/null || echo "Not downloaded"
    Expected Result: Binary exists or script handled gracefully
    Evidence: .sisyphus/evidence/task-05-download.txt
  ```

---

### Wave 4: Final Integration

- [ ] **6. Integration Tests + Bootstrap Verification**

  **What to do**:
  1. Expand integration tests:
     - `tests/integration/test_mcp_servers.py` — All 3 MCPs start + respond
     - `tests/integration/test_health_pipeline.py` — End-to-end health check
     - `tests/integration/test_trigger_e2e.py` — Trigger evaluation + action
  2. Verify bootstrap.sh:
     - Fresh venv creation
     - Dependency installation
     - All tests pass after bootstrap
  3. Create `bin/verify-install` script:
     - Runs all health checks
     - Verifies test count
     - Reports installation status
  4. Update documentation:
     - `STANDALONE.md` — Updated architecture
     - `docs/ARCHITECTURE.md` — System diagram
     - `docs/SPRINT5-RETROSPECTIVE.md` — What was built

  **Must NOT do**:
  - Do NOT add features beyond what was tested
  - Do NOT hardcode paths in docs

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Reason**: Documentation focus
  - **Skills**: `git-master` for clean commit

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on all previous)
  - **Blocks**: None (final task)

  **References**:
  - `tests/integration/test_core.py` — Existing pattern
  - `bootstrap.sh` — Installer to verify

  **Acceptance Criteria**:
  - [ ] `pytest tests/integration/ -v` → ≥15 tests pass
  - [ ] `pytest tests/ -v` → ≥40 tests pass
  - [ ] `bash bootstrap.sh` exits 0
  - [ ] `bin/verify-install` exits 0
  - [ ] `pytest tests/ -v` passes after fresh bootstrap
  - [ ] Documentation has no hardcoded paths

  **QA Scenarios**:

  ```
  Scenario: All tests pass
    Tool: Bash
    Preconditions: All tasks complete
    Steps:
      1. pytest tests/ -v --tb=short 2>&1 | tail -20
    Expected Result: All tests passed, no failures
    Evidence: .sisyphus/evidence/task-06-all-tests.txt

  Scenario: Verify install script works
    Tool: Bash
    Preconditions: Everything installed
    Steps:
      1. bin/verify-install
    Expected Result: Exit code 0, all checks pass
    Evidence: .sisyphus/evidence/task-06-verify-install.txt
  ```

  **Commit**: YES
  - Message: `chore: sprint 5 complete - integration tests and documentation`
  - Files: `tests/integration/`, `docs/`, `bin/verify-install`

---

## Final Verification Wave

- [ ] **F1. Plan Compliance Audit** — `oracle`
  Read plan end-to-end. Verify all 6 tasks have implementation. Verify no LayerStack or Memory Cortex references.

- [ ] **F2. Code Quality Review** — `unspecified-high`
  Run `python -m py_compile` on all .py files. Check for `as any`, empty catches.

- [ ] **F3. Integration Test Pass** — `unspecified-high`
  Run `pytest tests/ -v` — verify ≥40 tests pass.

- [ ] **F4. Scope Fidelity Check** — `deep`
  Verify all Must Have present, all Must NOT Have absent, no scope creep.

---

## Commit Strategy

| Wave | Message | Files |
|------|---------|-------|
| Wave 1 | `chore: quarantine dead code and fix MCP configuration` | opencode.json, Makefile, src/deprecated/ |
| Wave 2 | `feat: import core systems from nx_openmore` | src/athena/, tests/unit/ |
| Wave 3 | `feat: complete MCP packages and wire trigger engine` | packages/, bin/, triggers.json |
| Wave 4 | `chore: sprint 5 complete - integration tests` | tests/integration/, docs/, bin/verify-install |

---

## Success Criteria

### Verification Commands
```bash
# All tests pass
pytest tests/ -v --tb=short

# Health checks work
bin/health-check
bin/trigger-status

# MCPs start
python -m packages.athena_context_mcp &
python -m packages.nx_mind_mcp &
python -m packages.trigger_guardian_mcp &

# Bootstrap verified
bash bootstrap.sh
bin/verify-install
```

### Final Checklist
- [ ] All 6 tasks complete
- [ ] ≥40 tests passing
- [ ] All MCPs functional
- [ ] Health checks working
- [ ] Bootstrap verified
- [ ] Documentation updated
- [ ] No hardcoded paths
- [ ] No LayerStack (Oracle directive)
- [ ] No Memory Cortex (Oracle directive)

---

## Missing Patterns (For Sprint 6+)

Documented by Librarian but NOT in Sprint 5 scope:

| Pattern | Description | Priority |
|---------|-------------|----------|
| Preemptive Context Compaction | Auto-compact at 85% context | High |
| Provider-Level Circuit Breaker | Track failures per LLM provider | High |
| Lifecycle Hook System | 40+ hooks for agent lifecycle | Medium |
| Cross-Session Semantic Memory | Learn from past sessions | Medium |
| MCP Auto-Discovery | Dynamic MCP registry | Low |

---

## Anti-Patterns to Avoid (Oracle Guidance)

1. ❌ **LayerStack** — Spec-only, deprecated, 7 layers = complexity without value
2. ❌ **Memory Cortex** — Failed before (`cortex/kernels/` never created)
3. ❌ **New MCP servers** — 3 MCPs is the limit
4. ❌ **Audio/video/music files** — Quarantined, do not restore
5. ❌ **Neo4j/PostgreSQL** — Python-only, local stdio
6. ❌ **Spec without code** — Every system must have working implementation first

---

## Source Attribution (MIT Licensed)

| Source | License | Components |
|--------|---------|------------|
| nx_openmore | MIT | Governance Engine, Sentinel, Flight Recorder, Skill Telemetry, DeltaManifest |
| N-Xyme_CATALYST | MIT | MCP package templates, BMAD workflows |
| anomalyco/opencode | MIT | Agent system patterns |
| code-yeongyu/oh-my-openagent | MIT | Agent orchestration patterns |

---

*Plan synthesized from 5 agent consultations: Metis, Momus, Oracle, Librarian, Explore*
*Sprint 5 - Consolidated Core System*
