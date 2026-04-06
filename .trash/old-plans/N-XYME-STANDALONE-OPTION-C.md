# N-Xyme MIND: Comprehensive Standalone Architecture Plan
## Option C - Build from Scratch (MIT Licensed Sources)

> **Synthesized from**: 28 comprehensive audits across nx_openmore, N-Xyme_CATALYST, and Deprecated repositories

---

## TL;DR

> **Goal**: Build N-Xyme MIND as a standalone, portable, self-healing AI coding workspace using OpenCode as reference (NOT a fork).
> 
> **Key Innovation**: LayerStack behavioral control system (7-layer: R/H/M/A/S/T/SB) powering trigger-guardian routing
> 
> **Architecture**: Agent orchestration layer + unified memory system + Python MCP framework + trigger engine + VPN rotator
> 
> **Deliverables**: Custom MCPs (athena-context, nx-mind, trigger-guardian), BMAD workflows, VPN rotation CLI, trigger engine
> 
> **Estimated Effort**: Medium (6 sprints)
> **Parallel Execution**: YES - 5 waves
> **Critical Path**: LayerStack → Trigger Guardian → Memory → Agent → BMAD

---

## Context

### Original Request
Build N-Xyme MIND as standalone using OpenCode as reference. Option C (build new, not fork).

### Research Findings (28 Audits Complete)

#### nx_openmore (7/7 audits - MIT Licensed)
| System | Key Innovation | Priority |
|--------|---------------|----------|
| Governance Engine | Risk-proportional Triple-Lock + Doom Loop Detection | HIGH |
| Sentinel Protocol | Unknown-unknown detection at session boundaries | HIGH |
| Flight Recorder | Immutable forensic audit trail | HIGH |
| DeltaManifest | O(1) file sync with SHA-256 fallback | HIGH |
| VPN Rotator | 429-adaptive rate limiting with weighted load balancing | HIGH |
| Skill Telemetry | JSONL-based skill usage tracking | MEDIUM |
| Event Bus | AsyncIO pub/sub with SQLite persistence | MEDIUM |

#### N-Xyme_CATALYST (7/7 audits - MIT Licensed)
| System | Key Innovation | Priority |
|--------|---------------|----------|
| BMAD System | 46 skills across 3 modules (core, bmm, tea), 9 agents | HIGH |
| Docker Infra | MCP-first architecture (12 servers, resource limits, health checks) | HIGH |
| Session Manager MCP | Session CRUD + handoff + orphan detection (10 tools) | HIGH |
| Code Health MCP | Syntax/lint/type checks (6 tools) | MEDIUM |
| Graphiti Memory | Neo4j knowledge graph + SQLite backup | MEDIUM |
| cowagent Skills | Markdown-based skill definitions with frontmatter | MEDIUM |
| Health Monitor | 17-service health monitoring (not fully implemented) | MEDIUM |

#### Deprecated Systems (14/14 audits)
| System | Why Deprecated | Lesson |
|--------|--------------|--------|
| C.O.D.E. OS LayerStack | Replaced by simpler trigger system | RESURRECT: 7-layer behavioral control |
| 80+ Microservices (SPINE) | Over-engineered for personal use | AVOID: Complexity without validation |
| Multi-cortex Memory | Neo4j empty (0 nodes) - no data pipeline | AVOID: Create DB before data flow |
| Istio + ArgoCD + Vault | 4 external systems to maintain | AVOID: Operational complexity |
| Voice-First Architecture | Text not primary mode | ADAPT: Keep text-first |
| Model Pool Routing | Overkill for delegation per agent | SIMPLIFY: Current AGENTS.md approach |

---

## Work Objectives

### Core Objective
Build N-Xyme MIND standalone using best-in-class patterns from 3 MIT-licensed source repos, synthesized into unified architecture.

### Concrete Deliverables
- [ ] `trigger-guardian` MCP with LayerStack behavioral routing
- [ ] `athena-context` MCP with DeltaManifest sync
- [ ] `nx-mind` MCP with session handoff + orphan detection
- [ ] BMAD workflow system (46 skills)
- [ ] VPN rotation CLI with 429-adaptive learning
- [ ] Trigger engine with ACTION_REGISTRY
- [ ] Python MCP framework (server.py pattern)

### Definition of Done
- [ ] All MCPs pass import validation
- [ ] VPN rotator passes integration tests (4/4)
- [ ] Trigger engine wired to triggers.json
- [ ] BMAD workflows executable via catalyst command
- [ ] Zero external dependencies (fully portable)

### Must Have
- Local-first (no cloud APIs for core functionality)
- Python-only (no npm/Node.js for MCPs)
- Single venv (./venv/)
- Docker optional (runs without containers)

### Must NOT Have
- No Neo4j/PostgreSQL external dependencies
- No Kubernetes/Helm deployment
- No service mesh (Istio)
- No model pooling (use delegation per agent)
- No voice-first assumptions

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **Automated tests**: Tests-after (TDD not required for this phase)
- **Framework**: pytest

### QA Policy
Every task includes agent-executed QA scenarios. Evidence saved to `.sisyphus/evidence/`.

- **Integration tests**: pytest for trigger engine, VPN rotator, memory connectors
- **QA Scenarios**: Each task verified by running command + asserting output

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation - Start Immediately):
├── Task 1: Implement LayerStack behavioral control (R/H/M/A/S/T/SB)
├── Task 2: Build trigger-guardian MCP with LayerStack routing
├── Task 3: Implement Governance Engine (Triple-Lock + Doom Loop)
├── Task 4: Implement Sentinel Protocol (unknown-unknown detection)
├── Task 5: Implement Flight Recorder (immutable audit log)
└── Task 6: Create Python MCP framework (server.py pattern)

Wave 2 (Memory System - After Wave 1):
├── Task 7: Implement DeltaManifest sync engine
├── Task 8: Implement athena-context MCP (DeltaManifest + governance)
├── Task 9: Implement nx-mind MCP (session CRUD + handoff)
├── Task 10: Implement Skill Telemetry (JSONL tracking)
├── Task 11: Implement Event Bus (AsyncIO pub/sub)
└── Task 12: Wire memory connectors to new MCPs

Wave 3 (Agent Orchestration - After Wave 2):
├── Task 13: Implement BMAD workflow system (46 skills)
├── Task 14: Implement session-manager MCP (from CATALYST)
├── Task 15: Implement code-health MCP (from CATALYST)
├── Task 16: Create catalyst command CLI
└── Task 17: Create trigger-status CLI

Wave 4 (VPN + Integration - After Wave 3):
├── Task 18: Enhance VPN rotator with 429-adaptive learning
├── Task 19: Wire trigger-engine to triggers.json
├── Task 20: Create n-xyme CLI (entry point)
├── Task 21: Create bootstrap.sh (uv-only installer)
└── Task 22: Write comprehensive integration tests

Wave 5 (Documentation + Polish - After Wave 4):
├── Task 23: Write STANDALONE.md documentation
├── Task 24: Write UPGRADE.md migration guide
├── Task 25: Write DEPRECATIONS.md for deprecated patterns
└── Task 26: Final integration test pass
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 1-6 | — | 7-12 |
| 7-12 | 1-6 | 13-17 |
| 13-17 | 7-12 | 18-22 |
| 18-22 | 13-17 | 23-26 |
| 23-26 | 18-22 | FINAL |

### Agent Dispatch Summary

- **Wave 1**: Tasks 1-6 → `ultrabrain` (complex systems)
- **Wave 2**: Tasks 7-12 → `deep` (memory systems)
- **Wave 3**: Tasks 13-17 → `deep` + `writing` (workflows)
- **Wave 4**: Tasks 18-22 → `deep` + `artistry` (CLI)
- **Wave 5**: Tasks 23-26 → `writing` (documentation)

---

## TODOs

### Wave 1: Foundation

- [ ] 1. **Implement LayerStack Behavioral Control System**

  **What to do**:
  - Create `src/trigger_engine/layerstack.py` implementing 7-layer control:
    - **R-Layer (Research)**: R0 offline → R1 quick check → R2 deep research
    - **H-Layer (Heartbeat)**: Scheduled check-in cadences per kernel
    - **M-Layer (Memory)**: M0 no memory → M1 light → M2 deep context
    - **A-Layer (Autonomy)**: A0 direct → A1 short plan → A2 full plan
    - **S-Layer (Safety)**: S0 normal → S1 mild → S2 Stabilize → S3 hard protect
    - **T-Layer (Task)**: Complex task decomposition
    - **SB-Layer (Soft Branch)**: Implicit kernel switching
  - Create `src/trigger_engine/risk_classifier.py` for Lambda/Rho/Sigma/Normal classification
  - Write tests in `tests/unit/test_layerstack.py`

  **Must NOT do**:
  - Do not implement voice-first assumptions
  - Do not add external API dependencies

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
  - **Reason**: LayerStack requires deep understanding of behavioral control systems
  - **Skills**: None required (complex logic)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2-6)
  - **Blocks**: Tasks 7-12 (Wave 2)

  **References**:
  - `/mnt/NXYME_CORE/99_Depricated/0_C.O.D.E. OS/kernels/CODEOS_LayerStack_v1.0.md` — Full LayerStack specification
  - `/mnt/N-Xyme_CODE/N-Xyme_MIND/src/trigger_engine.py` — Current ACTION_REGISTRY pattern

  **Acceptance Criteria**:
  - [ ] `python -c "from src.trigger_engine.layerstack import LayerStack; ls = LayerStack(); print(ls.layers)"` → 7 layers printed
  - [ ] `pytest tests/unit/test_layerstack.py` → PASS (10 tests, 0 failures)

  **QA Scenarios**:

  ```
  Scenario: LayerStack initializes with all 7 layers
    Tool: Bash
    Preconditions: Clean Python environment
    Steps:
      1. python -c "from src.trigger_engine.layerstack import LayerStack; ls = LayerStack(); print('R:', ls.R, 'H:', ls.H, 'M:', ls.M, 'A:', ls.A, 'S:', ls.S, 'T:', ls.T, 'SB:', ls.SB)"
    Expected Result: Output shows all 7 layers initialized
    Evidence: .sisyphus/evidence/task-01-layerstack-init.txt

  Scenario: Risk classifier categorizes task correctly
    Tool: Bash
    Preconditions: LayerStack installed
    Steps:
      1. python -c "from src.trigger_engine.risk_classifier import RiskClassifier; rc = RiskClassifier(); print(rc.classify('DELETE all files'))"
    Expected Result: Lambda or Rho classification (high risk)
    Evidence: .sisyphus/evidence/task-01-risk-classifier.txt
  ```

  **Commit**: YES (Wave 1 complete)
  - Message: `feat(layerstack): implement 7-layer behavioral control system`
  - Files: `src/trigger_engine/layerstack.py`, `src/trigger_engine/risk_classifier.py`, `tests/unit/test_layerstack.py`

---

- [ ] 2. **Build trigger-guardian MCP with LayerStack Routing**

  **What to do**:
  - Create `src/mcp/trigger_guardian/` directory with Python MCP server
  - Implement 6 tools from existing design:
    - `register_trigger` — Register phrase with callback
    - `list_triggers` — List all triggers
    - `check_trigger` — Check input against triggers
    - `get_trigger_handlers` — Get handlers for matched trigger
    - `log_trigger_event` — Log activation for analytics
    - `clear_triggers` — Clear all triggers
  - Wire LayerStack risk classification to trigger routing
  - Create `opencode.json` entry for trigger-guardian MCP

  **Must NOT do**:
  - Do not implement voice trigger support
  - Do not add external service dependencies

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Reason**: MCP server with complex routing logic
  - **Skills**: None required

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 1)
  - **Blocks**: Task 7 (athena-context)

  **References**:
  - `/mnt/NXYME_CORE/00_N-Xyme_MIND/src/trigger_engine.py` — Current trigger implementation
  - `/mnt/NXYME_CORE/00_N-Xyme_CATALYST/mcp-servers/session-manager/` — MCP server pattern (TypeScript, adapt to Python)

  **Acceptance Criteria**:
  - [ ] MCP server starts: `python -m src.mcp.trigger_guardian` → no errors
  - [ ] `register_trigger` tool works via stdio protocol

  **QA Scenarios**:

  ```
  Scenario: trigger-guardian MCP starts and responds to initialize
    Tool: Bash
    Preconditions: MCP directory created
    Steps:
      1. echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | python -m src.mcp.trigger_guardian
    Expected Result: Valid JSON-RPC response with server capabilities
    Evidence: .sisyphus/evidence/task-02-mcp-init.txt

  Scenario: register_trigger tool creates new trigger
    Tool: Bash
    Preconditions: MCP server running
    Steps:
      1. echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"register_trigger","arguments":{"phrase":"/test","handler":"callback"}}}' | python -m src.mcp.trigger_guardian
    Expected Result: Tool response with trigger registered
    Evidence: .sisyphus/evidence/task-02-register-trigger.txt
  ```

  **Commit**: YES (Wave 1 complete)
  - Files: `src/mcp/trigger_guardian/`, `opencode.json`

---

- [ ] 3. **Implement Governance Engine (Triple-Lock + Doom Loop)**

  **What to do**:
  - Create `src/trigger_engine/governance.py` implementing:
    - **Triple-Lock**: Semantic Search → Web Search → Save (ensures grounding before checkpointing)
    - **Risk-Proportional**: SNIPER (Lambda<10) bypasses lock; STANDARD/ULTRA enforces it
    - **Doom Loop Detection**: Hash tool+args, flag if same call repeats 3+ times in 60s
  - Integrate with LayerStack S-Layer (Safety)
  - Write tests in `tests/unit/test_governance.py`

  **Must NOT do**:
  - Do not implement cloud search APIs
  - Do not add persistent state (stateless circuit breaker)

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
  - **Reason**: Complex safety logic with circuit breaker patterns

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 1)
  - **Blocks**: Task 8

  **References**:
  - `/mnt/Library/nx_openmore/athena/src/athena/core/governance.py` — Reference implementation
  - `Task 1` output — LayerStack integration point

  **Acceptance Criteria**:
  - [ ] `pytest tests/unit/test_governance.py` → PASS
  - [ ] Doom loop detection triggers after 3 repeated calls

  **QA Scenarios**:

  ```
  Scenario: Doom loop detection triggers on repeated calls
    Tool: Bash
    Preconditions: Governance engine initialized
    Steps:
      1. python -c "from src.trigger_engine.governance import DoomLoopDetector; d = DoomLoopDetector(); [d.check('tool', 'args') for _ in range(3)]; print('Loop detected:', d.check('tool', 'args'))"
    Expected Result: True after 3 repeated calls
    Evidence: .sisyphus/evidence/task-03-doom-loop.txt
  ```

  **Commit**: YES (Wave 1 complete)

---

- [ ] 4. **Implement Sentinel Protocol**

  **What to do**:
  - Create `src/trigger_engine/sentinel.py`:
    - **Boot sentinel**: Cross-reference Active Context vs Canonical Constraints
    - **Shutdown sentinel**: Check for knowledge leaks and unfinished synthesis
    - **Unknown-unknown detection**: Flag high-risk keywords (Ruin Law), complexity hell (>10 pending tasks)
  - Integrate with SessionConnector for context loading
  - Write tests in `tests/unit/test_sentinel.py`

  **Must NOT do**:
  - Do not implement automated fixes (report only)

  **Parallelization**: YES (Wave 1)

  **References**:
  - `/mnt/Library/nx_openmore/athena/src/athena/intelligence/sentinel.py` — Reference

  **Acceptance Criteria**:
  - [ ] Sentinel detects missing focus at boot
  - [ ] Sentinel detects knowledge leak at shutdown

  **QA Scenarios**:

  ```
  Scenario: Boot sentinel detects missing focus
    Tool: Bash
    Preconditions: Empty active context
    Steps:
      1. python -c "from src.trigger_engine.sentinel import BootSentinel; s = BootSentinel(); print('Warnings:', s.check_boot())"
    Expected Result: List of warnings about missing focus
    Evidence: .sisyphus/evidence/task-04-boot-sentinel.txt
  ```

---

- [ ] 5. **Implement Flight Recorder**

  **What to do**:
  - Create `src/trigger_engine/flight_recorder.py`:
    - Immutable append-only log to JSONL
    - Records: timestamp, tool_name, params, status, rationale, pid
    - No delete capability (append-only)
  - Write tests in `tests/unit/test_flight_recorder.py`

  **Parallelization**: YES (Wave 1)

  **References**:
  - `/mnt/Library/nx_openmore/athena/src/athena/core/flight_recorder.py` — Reference

  **Acceptance Criteria**:
  - [ ] Records append to JSONL file
  - [ ] No delete operation exposed

---

- [ ] 6. **Create Python MCP Framework**

  **What to do**:
  - Create `src/mcp/framework.py`:
    - `MCPServer` base class
    - `MCPToolRegistry` for tool registration
    - `MCPClient` for stdio communication
    - JSON-RPC 2.0 protocol implementation
  - Use as base for all custom MCPs (Tasks 2, 8, 9, 14, 15)

  **Must NOT do**:
  - Do not use TypeScript (use Python only per constraint)

  **Parallelization**: YES (Wave 1)

  **References**:
  - `/mnt/NXYME_CORE/00_N-Xyme_CATALYST/mcp-servers/session-manager/` — TypeScript pattern (adapt to Python)
  - `/mnt/NXYME_CORE/99_Depricated/00_N-Xyme_MIND/mcp-servers/code-health/` — TypeScript pattern (adapt to Python)

  **Acceptance Criteria**:
  - [ ] Framework supports tool registration
  - [ ] Framework handles JSON-RPC requests/responses

---

### Wave 2: Memory System

- [ ] 7. **Implement DeltaManifest Sync Engine**

  **What to do**:
  - Create `src/memory/delta_manifest.py`:
    - O(1) quick-check: size + mtime first
    - SHA-256 hash only if size/mtime differ
    - Thread-safe with file locking
    - Atomic writes to manifest file
  - Write tests in `tests/unit/test_delta_manifest.py`

  **References**:
  - `/mnt/Library/nx_openmore/athena/src/athena/memory/delta_manifest.py` — Reference

---

- [ ] 8. **Implement athena-context MCP**

  **What to do**:
  - Create `src/mcp/athena_context/`:
    - 7 tools from existing design:
      - `query_unified_memory` — Cross-source search
      - `search_unified` — Semantic search
      - `query_sources` — List memory sources
      - `get_active_context` — Current session state
      - `get_product_context` — Agent identity
      - `get_user_context` — User preferences
      - `get_constraints` — Behavioral limits
      - `inject_context` — Context injection
  - Wire DeltaManifest for file tracking
  - Wire Governance for safety checks

  **References**:
  - `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/src/memory/athena_connector.py` — Existing connector

---

- [ ] 9. **Implement nx-mind MCP**

  **What to do**:
  - Create `src/mcp/nx_mind/`:
    - Tools from CATALYST session-manager:
      - `session_list` — List sessions
      - `session_read` — Read messages
      - `session_search` — Full-text search
      - `session_rename` — Rename session
      - `session_delete` — Delete session
      - `handoff_capture` — Capture context
      - `handoff_recover` — Recover context
      - `orphan_detect` — Find stale sessions
      - `orphan_clean` — Remove stale sessions
      - `global_todos` — Task tracking

  **References**:
  - `/mnt/NXYME_CORE/00_N-Xyme_CATALYST/mcp-servers/session-manager/` — Reference

---

- [ ] 10. **Implement Skill Telemetry**

  **What to do**:
  - Create `src/trigger_engine/skill_telemetry.py`:
    - JSONL append for skill invocations
    - Fields: skill_name, session_id, trigger_type (auto/manual), timestamp
    - `get_skill_stats()` API
    - `get_dead_skills()` detection

  **References**:
  - `/mnt/Library/nx_openmore/athena/src/athena/core/skill_telemetry.py` — Reference

---

- [ ] 11. **Implement Event Bus**

  **What to do**:
  - Create `src/trigger_engine/event_bus.py`:
    - AsyncIO pub/sub pattern
    - SQLite persistence
    - Correlation ID tracking
    - Pattern matching ("app.*" wildcards)

  **References**:
  - `/mnt/Library/nx_openmore/jarvis-new/src/core/event_bus.py` — Reference

---

- [ ] 12. **Wire Memory Connectors**

  **What to do**:
  - Update `src/memory/` connectors to use new MCPs:
    - `athena_connector.py` → athena-context MCP
    - `session_connector.py` → nx-mind MCP
    - `memory_mcp_connector.py` → trigger-guardian MCP
  - Ensure backward compatibility

---

### Wave 3: Agent Orchestration

- [ ] 13. **Implement BMAD Workflow System**

  **What to do**:
  - Create `src/bmad/`:
    - Import BMAD manifests (skill-manifest.csv, agent-manifest.csv)
    - Implement core skills (11 from core module)
    - Implement bmm skills (26 from bmm module)
    - Implement tea skills (9 from tea module)
  - Create `catalyst` CLI command

  **References**:
  - `/mnt/NXYME_CORE/01_CODING/00_N-Xyme_CATALYST/_bmad/` — BMAD source
  - `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/docs/CATALYST-INTEGRATION.md` — Current docs

---

- [ ] 14. **Implement code-health MCP**

  **What to do**:
  - Create `src/mcp/code_health/`:
    - 6 tools: syntax, lint, types, deps, dashboard, heartbeat

  **References**:
  - `/mnt/NXYME_CORE/99_Depricated/00_N-Xyme_MIND/mcp-servers/code-health/` — Reference

---

- [ ] 15. **Create catalyst CLI**

  **What to do**:
  - Create `bin/catalyst` entry point
  - Implement workflow execution commands
  - Wire to BMAD system

---

- [ ] 16. **Create trigger-status CLI**

  **What to do**:
  - Enhance existing `bin/trigger-status`
  - Add health monitoring (from CATALYST health monitor)

---

### Wave 4: VPN + Integration

- [ ] 17. **Enhance VPN Rotator**

  **What to do**:
  - Enhance `vpn/rotator.py`:
    - 429-adaptive rate limiting (learn quota from responses)
    - Token bucket rate limiting
    - Weighted load balancing using available_capacity
  - Add stealth mode with random delays

  **References**:
  - `/mnt/Library/nx_openmore/bin/rotator.py` — Reference
  - `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/vpn/rotator.py` — Current

---

- [ ] 18. **Wire Trigger Engine**

  **What to do**:
  - Update `src/trigger_engine.py`:
    - Load triggers from `triggers.json`
    - Wire LayerStack risk classification
    - Wire Governance engine
    - Wire Sentinel protocol

---

- [ ] 19. **Create n-xyme CLI**

  **What to do**:
  - Create `bin/n-xyme` entry point
  - Subcommands: catalyst, trigger-status, vpn-rotate, version

---

- [ ] 20. **Create bootstrap.sh**

  **What to do**:
  - Create `bootstrap.sh` (uv-only, no npm):
    - Check Python version (3.10+)
    - Create venv
    - Install dependencies
    - Install OpenCode if needed
    - Create symlinks

---

- [ ] 21. **Write Integration Tests**

  **What to do**:
  - Create `tests/integration/test_vpn_rotator.py` (extend existing)
  - Create `tests/integration/test_trigger_engine.py`
  - Create `tests/integration/test_mcp_servers.py`
  - Target: 4/4 tests passing

---

### Wave 5: Documentation

- [ ] 22. **Write STANDALONE.md**

  **What to do**:
  - Document standalone architecture
  - Include LayerStack explanation
  - Document MCP server architecture
  - Include upgrade path

---

- [ ] 23. **Write UPGRADE.md**

  **What to do**:
  - Pre-upgrade checklist
  - Automatic vs manual upgrade paths
  - Rollback procedures
  - Troubleshooting section

  **References**:
  - `/mnt/NXYME_CORE/99_Depricated/1_N-Xyme_MIND/docs/UPGRADE.md` — Template

---

- [ ] 24. **Write DEPRECATIONS.md**

  **What to do**:
  - Document deprecated patterns from audit:
    - Neo4j/PostgreSQL dependencies → NOT USED
    - Kubernetes/Helm → NOT USED
    - Istio service mesh → NOT USED
    - Model pooling → NOT USED
  - Link to MIT-licensed sources

---

- [ ] 25. **Final Integration Test Pass**

  **What to do**:
  - Run all tests
  - Verify MCP servers start
  - Verify VPN rotator works
  - Verify trigger engine wired

---

## Final Verification Wave

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read plan end-to-end. Verify all 25 tasks have implementation. Verify no forbidden patterns from Deprecated audit.

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `python -m py_compile` on all .py files. Check for `as any`, empty catches, `console.log`.

- [ ] F3. **Integration Test Pass** — `unspecified-high`
  Run `pytest tests/integration/` — verify 4/4 tests pass.

- [ ] F4. **Scope Fidelity Check** — `deep`
  Verify all Must Have present, all Must NOT Have absent, no scope creep.

---

## Commit Strategy

- **Wave 1**: `feat(foundation): layerstack, trigger-guardian, governance, sentinel, flight-recorder`
- **Wave 2**: `feat(memory): delta-manifest, athena-context, nx-mind, event-bus`
- **Wave 3**: `feat(orchestration): bmad, code-health, catalyst, trigger-status`
- **Wave 4**: `feat(vpn): enhanced rotator, n-xyme CLI, bootstrap`
- **Wave 5**: `docs: standalone, upgrade, deprecations guides`
- **Final**: `chore: integration tests pass`

---

## Success Criteria

### Verification Commands
```bash
python -m pytest tests/ -v  # All tests pass
python -m src.mcp.trigger_guardian --help  # MCP starts
python -m src.mcp.athena_context --help  # MCP starts
python -m src.mcp.nx_mind --help  # MCP starts
bin/n-xyme --version  # CLI works
```

### Final Checklist
- [ ] LayerStack implemented (7 layers)
- [ ] trigger-guardian MCP with 6 tools
- [ ] athena-context MCP with 8 tools
- [ ] nx-mind MCP with 10 tools
- [ ] Governance + Doom Loop detection
- [ ] Sentinel Protocol
- [ ] Flight Recorder
- [ ] BMAD 46 skills
- [ ] VPN rotator with 429-adaptive learning
- [ ] All MCPs import successfully
- [ ] Integration tests pass (4/4)
- [ ] Zero external DB dependencies
- [ ] Documentation complete (STANDALONE.md, UPGRADE.md, DEPRECATIONS.md)

---

## Source Attribution (MIT Licensed)

All code synthesized from MIT-licensed sources:

| Source | License | Components |
|--------|---------|------------|
| anomalyco/opencode | MIT | Agent system, MCP config patterns |
| code-yeongyu/oh-my-openagent | MIT | Agent orchestration, skill manifests |
| ollama/ollama | MIT | Local LLM runtime |
| nx_openmore custom code | MIT | Governance, Sentinel, Flight Recorder, DeltaManifest, VPN Rotator |
| N-Xyme_CATALYST custom code | MIT | BMAD workflows, session-manager, code-health MCP |
| Deprecated repos (analyzed) | Various | Anti-patterns to avoid, lessons learned |

---

## Anti-Patterns to Avoid (from Deprecated Audit)

1. ❌ **Neo4j without data pipeline** — Database created but never populated (0 nodes)
2. ❌ **Istio + ArgoCD + Vault** — 4 external systems to maintain
3. ❌ **Model pooling** — Overkill for delegation per agent
4. ❌ **Voice-first architecture** — Text is primary mode
5. ❌ **Hardcoded secrets in YAML** — Use environment variables
6. ❌ **Multi-cortex before validation** — Single stable system first
7. ❌ **Embedded DB in Helm** — Lifecycle coupling
8. ❌ **Complex model routing** — Simple delegation works better

---

*Plan generated from 28 comprehensive audits. Ready for `/start-work`.*
