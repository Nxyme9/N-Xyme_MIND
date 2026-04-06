# N-Xyme MIND: Frankenstein Synthesis Masterplan
## v0.1.0-alpha.1 — Build from MIT-Licensed Sources

> **Philosophy**: "We synthesize Frankenstein — stitch together what works from ALL sources, discard what failed."

---

## TL;DR

> **Goal**: Build v0.1.0-alpha.1 by synthesizing proven components from **5 MIT-licensed source repos**.
> 
> **Sources**:
> - **Athena Repo** ← PRIMARY SOURCE (core systems)
> - **nx_openmore** ← Athena lives here too (more patterns)
> - **N-Xyme_CATALYST** ← BMAD workflows, MCP patterns
> - **oh-my-openagent** ← Agent orchestration
> - **Deprecated** ← What NOT to build (learn from failures)
> 
> **What's IN**: Governance, Sentinel, Flight Recorder, Skill Telemetry, DeltaManifest, 3 MCPs, Health Checks
> **What's OUT**: LayerStack (failed), Memory Cortex (failed), Neo4j/PostgreSQL
> **Version**: v0.1.0-alpha.1
> **Tasks**: 7 across 5 waves
> **Target**: `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND_v0.1/`

---

## Source Matrix (MIT Licensed)

WS|| Source | GitHub | Location | What We Take | What We Skip |
QW||--------|--------|-----------|---------------|--------------|
RB|| **Athena-Public** | [winstonkoh87/athena-public](https://github.com/winstonkoh87/athena-public) (445⭐) | `/mnt/Library/nx_openmore/athena/` | Core systems (governance, sentinel, flight_recorder, skill_telemetry, delta_manifest) | Nothing - take all |
JC|| **OpenCode-Athena** | [ZebulonRouseFrantzich/opencode-athena](https://github.com/ZebulonRouseFrantzich/opencode-athena) (7⭐, MIT-0) | GitHub clone | BMAD + oh-my-opencode + OpenCode bridge patterns | `/athena-dev`, `/athena-review` commands, story complexity analysis |
JS|| **nx_openmore** | N/A (local) | `/mnt/Library/nx_openmore/` | VPN rotator, tool patterns, config system | Over-engineered parts |
HV|| **N-Xyme_CATALYST** | N/A (local) | `/mnt/NXYME_CORE/01_CODING/00_N-Xyme_CATALYST/` | BMAD workflows, session-manager MCP, code-health MCP | Docker infra (not needed) |
JS|| **oh-my-openagent** | [code-yeongyu/oh-my-openagent](https://github.com/code-yeongyu/oh-my-openagent) (48k⭐) | GitHub | Agent orchestration patterns, skill system | Everything else |
XJ|| **Deprecated** | N/A (local) | `/mnt/NXYME_CORE/99_Depricated/` | Anti-patterns to avoid | Specs without code |

---

## What We SYNTHESIZE (From Each Source)

### From Athena Repo (PRIMARY)
```
athena/src/athena/
├── core/
│   ├── governance.py          ✅ COPY: Doom Loop + Triple-Lock + Risk classification
│   ├── flight_recorder.py    ✅ COPY: JSONL audit trail
│   └── skill_telemetry.py    ✅ COPY: Usage tracking + dead skill detection
├── intelligence/
│   └── sentinel.py           ✅ COPY: Boot/shutdown checks + Protocol 420
└── memory/
    └── delta_manifest.py     ✅ COPY: O(1) file sync
```

### From nx_openmore
```
bin/
└── rotator.py                ✅ COPY: VPN rotator (429-adaptive + weighted LB)
athena/src/athena/
└── (already covered above)
```

### From N-Xyme_CATALYST
```
_bmad/                        ✅ COPY: BMAD workflow structure + 46 skills
mcp-servers/session-manager/  ✅ ADAPT: Python FastMCP pattern
mcp-servers/code-health/      ✅ ADAPT: Python FastMCP pattern
JT|```
KB|
GM|### From OpenCode-Athena (GitHub) — BMAD + Sisyphus Bridge
WM|```
WM|athena/                      ✅ PATTERNS: Commands, Bridge patterns, Todo sync
QM|├── commands/             ✅ ADAPT: /athena-dev, /athena-review workflow
QM|├── src/                  ✅ PATTERNS: Story complexity analysis
WM|└── README.md            ✅ ADAPT: Quality gate patterns, iterative review loop
WM|```
GM|
GM|### From oh-my-openagent (GitHub)
```
src/                          ✅ PATTERNS: Agent orchestration, skill system
```

### From Deprecated (LEARN FROM)
```
0_C.O.D.E. OS/
├── kernels/CODEOS_LayerStack_v1.0.md  ❌ SKIP: Spec only, never worked
└── kernels/CODEOS_MemoryCortex_v1.0.0.md ❌ SKIP: cortex/kernels/ never created
```

---

## What We SKIP (Failed Patterns)

| System | Source | Why Skipped |
|--------|--------|-------------|
| **LayerStack** | Deprecated | Spec-only (7 layers), never implemented |
| **Memory Cortex** | Deprecated | cortex/kernels/ directory never created |
| **Neo4j Memory** | CATALYST | Empty (0 nodes) — no data pipeline |
| **PostgreSQL/hindsight** | CATALYST | Over-engineered for personal use |
| **Istio/ArgoCD/Vault** | Deprecated | 4 external systems to maintain |
| **Model Pooling** | nx_openmore | Simple delegation works better |

---

## Architecture (Synthesized)

```
┌─────────────────────────────────────────────────────────────────┐
│                     N-Xyme MIND v0.1.0-alpha                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   athena-   │    │   nx-mind  │    │  trigger-   │        │
│  │  context-mcp │    │    -mcp    │    │  guardian-mcp│        │
│  │   (7 tools) │    │   (7 tools)│    │   (6 tools) │        │
│  └──────┬──────┘    └──────┬─────┘    └──────┬──────┘        │
│         │                    │                    │               │
│         └────────────────────┼────────────────────┘               │
│                              │                                    │
│                    ┌─────────▼─────────┐                        │
│                    │   ATHENA CORE      │                        │
│                    │  (MIT Licensed)    │                        │
│                    ├────────────────────┤                        │
│                    │ • Governance       │ ← Doom Loop + Triple-Lock│
│                    │ • Sentinel         │ ← Boot/Shutdown checks  │
│                    │ • Flight Recorder │ ← JSONL audit trail    │
│                    │ • Skill Telemetry │ ← Usage tracking       │
│                    │ • DeltaManifest    │ ← O(1) file sync      │
│                    └────────────────────┘                        │
│                              │                                   │
│         ┌────────────────────┼────────────────────┐            │
│         │                    │                    │               │
│  ┌─────▼─────┐    ┌───────▼───────┐    ┌────▼─────┐       │
│  │  Trigger   │    │   Health      │    │    VPN    │       │
│  │  Engine    │    │   Pipeline    │    │  Rotator  │       │
│  └─────────────┘    └───────────────┘    └───────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Version: v0.1.0-alpha.1

### Semantic Versioning (PEP 440)
```
v0.1.0-alpha.1
│ │ │ │  │
│ │ │ │  └── 1st alpha iteration
│ │ │ └───── alpha pre-release
│ │ └─────── minor (feature additions)
│ └───────── major (0 = pre-stable)
└─────────── always 0 before 1.0
```

### Version Progression
```
v0.1.0-alpha.1  ← NOW (synthesize from MIT sources)
v0.1.0-alpha.2  ← Bug fixes
v0.1.0-beta.1    ← Feature complete, user testing
v0.1.0-rc.1      ← Release candidate
v0.1.0           ← First stable
v1.0.0           ← Production-ready
```

---

## Project Structure

```
N-Xyme_MIND_v0.1/
├── src/nxyme_mind/              # Main package
│   ├── __init__.py             # __version__ = "0.1.0a1"
│   ├── __version__.py
│   ├── __main__.py             # python -m nxyme_mind
│   │
│   ├── athena/                 # SYNTHESIZED FROM ATHENA REPO
│   │   ├── core/
│   │   │   ├── governance.py       # COPY: Doom Loop + Triple-Lock
│   │   │   ├── flight_recorder.py  # COPY: JSONL audit
│   │   │   ├── skill_telemetry.py # COPY: Usage tracking
│   │   │   └── config.py           # ADAPT: Path constants
│   │   ├── intelligence/
│   │   │   └── sentinel.py         # COPY: Boot/Shutdown checks
│   │   └── memory/
│   │       └── delta_manifest.py    # COPY: O(1) sync
│   │
│   ├── mcp/                   # SYNTHESIZED FROM CATALYST
│   │   ├── athena_context/   # 7 tools
│   │   ├── nx_mind/          # 7 tools
│   │   └── trigger_guardian/ # 6 tools
│   │
│   ├── cli/                   # SYNTHESIZED
│   │   └── main.py           # Click-based CLI
│   │
│   └── core/                 # SYNTHESIZED FROM nx_openmore
│       ├── trigger_engine.py  # COPY
│       └── health.py          # ADAPT
│
├── vpn/                       # COPY FROM nx_openmore
│   └── rotator.py            # 429-adaptive + weighted LB
│
├── bin/                       # CLI tools
│   ├── health-check.sh
│   ├── trigger-status
│   ├── vpn-rotate
│   └── verify-install
│
├── tests/                     # Test suite
│   ├── unit/                 # 25+ tests
│   └── integration/          # 15+ tests
│
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md
│   └── CHANGELOG.md
│
├── pyproject.toml             # Ruff + pytest + mypy
├── ruff.toml
├── .pre-commit-config.yaml
├── Makefile
│
├── README.md
├── LICENSE                    # MIT
├── CONTRIBUTING.md
├── CHANGELOG.md
│
└── bootstrap.sh               # One-command installer
```

---

## Execution Waves

```
Wave 0: Pre-flight (Start Immediately)
└── Task 0: Setup foundation (version, ruff, LICENSE, pre-commit)

Wave 1: Package Structure
└── Task 1: Create src/nxyme_mind/ structure + __init__.py

Wave 2: Synthesize Core Systems (FROM ATHENA REPO)
└── Task 2: Copy governance, sentinel, flight_recorder, skill_telemetry, delta_manifest

Wave 3: Synthesize MCPs + Health (PARALLEL)
├── Task 3: Wire MCP packages (from CATALYST patterns)
├── Task 4: Rewrite health-check + CLI
└── Task 5: VPN rotator (from nx_openmore)

Wave 4: Tests
└── Task 6: Expand tests (40+ tests)

Wave 5: Release
└── Task 7: Docs + Release artifact + git tag

Critical Path: Task 0 → 1 → 2 → 3 → 7
```

---

## TODOs

### Wave 0: Pre-flight

- [ ] **0. Setup Foundation**

  **What to do**:
  1. Create `pyproject.toml` with version = "0.1.0a1"
  2. Create `src/nxyme_mind/__init__.py` with `__version__ = "0.1.0a1"`
  3. Create `LICENSE` (MIT)
  4. Create `CONTRIBUTING.md`
  5. Create `ruff.toml` (linting + formatting)
  6. Create `.pre-commit-config.yaml`
  7. Create `.gitignore`
  8. Create `Makefile` (lint, test, quality-gates)
  9. Create all `__init__.py` files

  **Sources**:
  - Athena repo: MIT License format
  - nx_openmore: ruff configuration patterns

  **Acceptance Criteria**:
  - [ ] `python -c "from nxyme_mind import __version__; assert __version__ == '0.1.0a1'"` → passes
  - [ ] `ruff check src/` → 0 errors
  - [ ] `ruff format --check src/` → all formatted
  - [ ] `grep -q "MIT License" LICENSE` → true

  **Commit**: `chore: setup foundation v0.1.0a1`

---

### Wave 1: Package Structure

- [ ] **1. Create Package Structure**

  **What to do**:
  1. Create directory tree:
     ```
     src/nxyme_mind/
     ├── __init__.py
     ├── __version__.py
     ├── __main__.py
     ├── athena/core/
     ├── athena/intelligence/
     ├── athena/memory/
     ├── mcp/athena_context/
     ├── mcp/nx_mind/
     ├── mcp/trigger_guardian/
     ├── cli/
     └── core/
     ```
  2. Create `src/nxyme_mind/__version__.py`:
     ```python
     VERSION = "0.1.0a1"
     VERSION_INFO = (0, 1, 0, "alpha", 1)
     ```
  3. Create `src/nxyme_mind/athena/core/config.py`:
     ```python
     from pathlib import Path
     PROJECT_ROOT = Path(__file__).resolve().parents[4]
     CONTEXT_DIR = PROJECT_ROOT / ".context"
     CANONICAL_PATH = PROJECT_ROOT / "CANONICAL.md"
     ```

  **Acceptance Criteria**:
  - [ ] `python -c "import nxyme_mind"` → no error
  - [ ] `python -m nxyme_mind --version` → v0.1.0a1
  - [ ] All `__init__.py` files exist

  **Commit**: `feat: create package structure`

---

### Wave 2: Synthesize Core (FROM ATHENA)

- [ ] **2. Synthesize Athena Core Systems**

  **What to do**:
  1. COPY from `/mnt/Library/nx_openmore/athena/src/athena/`:
     - `core/governance.py` → `src/nxyme_mind/athena/core/governance.py`
     - `core/flight_recorder.py` → `src/nxyme_mind/athena/core/flight_recorder.py`
     - `core/skill_telemetry.py` → `src/nxyme_mind/athena/core/skill_telemetry.py`
     - `intelligence/sentinel.py` → `src/nxyme_mind/athena/intelligence/sentinel.py`
     - `memory/delta_manifest.py` → `src/nxyme_mind/athena/memory/delta_manifest.py`
  2. ADAPT imports:
     - Replace `from athena.core.config import ...` → `from nxyme_mind.athena.core.config import ...`
  3. CREATE unit tests (≥5 per system)

  **Source**: Athena repo (MIT licensed)
  - `/mnt/Library/nx_openmore/athena/src/athena/core/governance.py` (315 lines)
  - `/mnt/Library/nx_openmore/athena/src/athena/intelligence/sentinel.py` (97 lines)
  - `/mnt/Library/nx_openmore/athena/src/athena/core/flight_recorder.py` (49 lines)
  - `/mnt/Library/nx_openmore/athena/src/athena/core/skill_telemetry.py` (224 lines)
  - `/mnt/Library/nx_openmore/athena/src/athena/memory/delta_manifest.py` (155 lines)

  **Acceptance Criteria**:
  - [ ] `python -c "from nxyme_mind.athena.core.governance import GovernanceEngine"` → no error
  - [ ] `python -c "from nxyme_mind.athena.intelligence.sentinel import check_boot_sentinel"` → no error
  - [ ] `python -c "from nxyme_mind.athena.core.flight_recorder import record_action"` → no error
  - [ ] `python -c "from nxyme_mind.athena.core.skill_telemetry import get_skill_stats"` → no error
  - [ ] `python -c "from nxyme_mind.athena.memory.delta_manifest import DeltaManifest"` → no error
  - [ ] `pytest tests/unit/test_governance.py` → ≥5 tests pass
  - [ ] `pytest tests/unit/test_sentinel.py` → ≥4 tests pass
  - [ ] `ruff check src/athena/` → 0 errors

  **QA Scenarios**:

  ```
  Scenario: Governance imports and Doom Loop works
    Tool: Bash
    Steps:
      1. python -c "from nxyme_mind.athena.core.governance import DoomLoopDetector; d = DoomLoopDetector(); print([d.record('tool', {}) for _ in range(3)])"
    Expected Result: [False, False, True]
    Evidence: .sisyphus/evidence/task-2-doom-loop.txt

  Scenario: Sentinel boot check works
    Tool: Bash
    Steps:
      1. python -c "from nxyme_mind.athena.intelligence.sentinel import check_boot_sentinel; print(check_boot_sentinel('# Current Focus\n- Task 1'))"
    Expected Result: None (no warnings for valid focus)
    Evidence: .sisyphus/evidence/task-2-sentinel.txt
  ```

  **Commit**: `feat: synthesize Athena core systems (MIT licensed)`

---

### Wave 3: Synthesize MCPs + Health (PARALLEL)

- [ ] **3. Synthesize MCP Packages**

  **What to do**:
  1. ADAPT from CATALYST patterns:
     - `athena-context-mcp`: 7 tools for context injection
     - `nx-mind-mcp`: 7 tools for MIND state
     - `trigger-guardian-mcp`: 6 tools for trigger routing
  2. Use FastMCP framework (Python)
  3. Wire to Athena core systems
  4. CREATE unit tests (≥5 per MCP)

  **Source**: N-Xyme_CATALYST (MIT licensed)
  - `/mnt/NXYME_CORE/01_CODING/00_N-Xyme_CATALYST/mcp-servers/session-manager/` → Python FastMCP pattern

  **Acceptance Criteria**:
  - [ ] `python -m nxyme_mind.mcp.athena_context` → starts
  - [ ] `python -m nxyme_mind.mcp.nx_mind` → starts
  - [ ] `python -m nxyme_mind.mcp.trigger_guardian` → starts
  - [ ] Each responds to `tools/list` with correct count (7/7/6)
  - [ ] `pytest tests/unit/test_*_mcp.py` → ≥14 tests pass

  **Commit**: `feat: synthesize MCP packages from CATALYST patterns`

---

- [ ] **4. Synthesize Health Pipeline**

  **What to do**:
  1. ADAPT from existing `bin/health-check.sh`
  2. CREATE `src/nxyme_mind/cli/main.py` (Click-based)
  3. Wire to Sentinel (boot/shutdown checks)
  4. CREATE `bin/health-check.sh` that calls Python health functions

  **Acceptance Criteria**:
  - [ ] `python -m nxyme_mind health` → runs
  - [ ] `bin/health-check.sh` → exits 0
  - [ ] `bin/trigger-status` → exits 0

  **Commit**: `feat: synthesize health pipeline`

---

- [ ] **5. Synthesize VPN Rotator**

  **What to do**:
  1. COPY from `/mnt/Library/nx_openmore/bin/rotator.py` (863 lines)
  2. ADAPT to `vpn/rotator.py`
  3. CREATE unit tests

  **Source**: nx_openmore (MIT licensed)

  **Acceptance Criteria**:
  - [ ] `python vpn/rotator.py --list` → lists providers
  - [ ] `pytest tests/unit/test_rotator.py` → tests pass

  **Commit**: `feat: synthesize VPN rotator from nx_openmore`

---

### Wave 4: Tests

- [ ] **6. Expand Test Suite**

  **What to do**:
  1. CREATE `tests/integration/test_mcp_servers.py`
  2. CREATE `tests/integration/test_health_pipeline.py`
  3. CREATE `tests/integration/test_trigger_e2e.py`
  4. Ensure total ≥40 tests

  **Acceptance Criteria**:
  - [ ] `pytest tests/ -v` → ≥40 tests pass
  - [ ] No skipped tests
  - [ ] Coverage ≥70%

  **Commit**: `test: expand test suite to 40+ tests`

---

### Wave 5: Release

- [ ] **7. Documentation + Release**

  **What to do**:
  1. CREATE `README.md` with:
     - Status: Alpha
     - Quick start
     - What's included
     - What's NOT included
  2. CREATE `CHANGELOG.md`
  3. CREATE `bin/verify-install`
  4. CREATE git tag: `v0.1.0-alpha.1`
  5. CREATE GitHub release artifact

  **Acceptance Criteria**:
  - [ ] `README.md` exists with quick start
  - [ ] `CHANGELOG.md` has v0.1.0-alpha.1 entry
  - [ ] `git tag v0.1.0-alpha.1` created
  - [ ] GitHub release artifact created
  - [ ] `bin/verify-install` → exits 0

  **Commit**: `chore: v0.1.0-alpha.1 release`

---

## Final Verification

```bash
# Version
python -m nxyme_mind --version  # → v0.1.0a1

# Quality gates
make lint    # → 0 errors
make test    # → ≥40 tests pass
make quality-gates  # → All pass

# Health
bin/health-check.sh  # → Exit 0
bin/trigger-status   # → Exit 0

# MCPs
python -m nxyme_mind.mcp.athena_context --help  # → Help
python -m nxyme_mind.mcp.nx_mind --help
python -m nxyme_mind.mcp.trigger_guardian --help

# Release
git tag -l "v0.1*"  # → v0.1.0-alpha.1
```

---

## Source Attribution (MIT Licensed)

| Source | License | What We Take |
|--------|---------|---------------|
| **Athena Repo** | MIT | governance, sentinel, flight_recorder, skill_telemetry, delta_manifest |
| **nx_openmore** | MIT | VPN rotator, tool patterns |
| **N-Xyme_CATALYST** | MIT | MCP patterns, session-manager, BMAD workflows |
| **oh-my-openagent** | MIT | Agent orchestration patterns |
| **Deprecated** | N/A | Anti-patterns only (what NOT to build) |

---

## Anti-Patterns Learned (From Deprecated)

| Pattern | Source | Why Avoid |
|--------|--------|-----------|
| LayerStack spec | Deprecated | 7 layers, spec-only, never implemented |
| Memory Cortex | Deprecated | cortex/kernels/ directory never created |
| Neo4j empty | CATALYST | 0 nodes — no data pipeline |
| Istio + ArgoCD | Deprecated | 4 external systems = burden |
| Model pooling | nx_openmore | Simple delegation works better |

---

## Success Criteria

- [ ] All 7 tasks complete
- [ ] ≥40 tests passing
- [ ] All MCPs functional
- [ ] Health checks working
- [ ] VPN rotator working
- [ ] Version consistent: v0.1.0a1
- [ ] LICENSE (MIT) included
- [ ] Git tag created
- [ ] GitHub release artifact
- [ ] No hardcoded paths
- [ ] ruff linting passes
- [ ] pre-commit hooks configured

---

*Frankenstein Synthesis: Stitch together what works from ALL sources.*
*Athena Repo → nx_openmore → CATALYST → oh-my-openagent → Learn from Deprecated*
*MIT Licensed. Production-Ready v0.1.0-alpha.1.*
