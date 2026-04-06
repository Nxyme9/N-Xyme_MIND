# N-Xyme MIND v0.1.0-alpha.1: Production-Ready Release Plan

> **Status**: READY FOR EXECUTION
> **Version**: v0.1.0-alpha.1
> **Target**: `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND_v0.1/`

---

## TL;DR

> **Goal**: Ship v0.1.0-alpha.1 as the first production-ready release of N-Xyme MIND.
> 
> **What's IN**: 3 MCP packages, Governance Engine, Sentinel, Flight Recorder, Skill Telemetry, DeltaManifest, health checks, VPN rotator, bootstrap installer.
> 
> **What's NOT**: LayerStack, Memory Cortex, BMAD workflows, auto-rotation, Docker, PyPI publishing.
> 
> **Distribution**: GitHub Releases only (manual for now).
> 
> **Estimated Effort**: 8 tasks across 5 waves, 3-4 weeks.
> **Parallel Execution**: YES - Wave 3 has 3 parallel tasks.
> **Critical Path**: Task 0 → Task 1 → Task 2 → Task 3 → Task 7.

---

## Version Information

### Semantic Versioning (PEP 440)

```
v0.1.0-alpha.1
│ │ │ │  │
│ │ │ │  └── Pre-release iteration (1st alpha)
│ │ │ └───── Pre-release type (alpha)
│ │ └─────── Minor version (feature additions)
│ └───────── Major version (0 = pre-stable)
└─────────── Major (always 0 for pre-1.0)
```

**Version Progression**:
```
v0.1.0-alpha.1  ← THIS RELEASE (Sprint 5 deliverable)
v0.1.0-alpha.2  ← Bug fixes, test additions
v0.1.0-beta.1   ← Feature complete, user testing
v0.1.0-rc.1     ← Release candidate, no new features
v0.1.0          ← First stable release
v0.2.0          ← Feature additions
v1.0.0          ← Production-ready
```

**Breaking Change Policy (Pre-1.0)**:
- `0.x.x` → ANY minor bump MAY break APIs
- Document all breaking changes in CHANGELOG.md
- No deprecation warnings required before 1.0

### What's IN v0.1.0-alpha.1

| System | Description | Status |
|--------|-------------|--------|
| Governance Engine | Doom Loop detection, Triple-Lock verification, Risk classification | ✅ |
| Sentinel Protocol | Boot/shutdown health checks, unknown-unknown detection | ✅ |
| Flight Recorder | Immutable JSONL audit trail | ✅ |
| Skill Telemetry | JSONL usage tracking + dead skill detection | ✅ |
| DeltaManifest | O(1) file sync detection | ✅ |
| athena-context-mcp | 7 tools for context injection | ✅ |
| nx-mind-mcp | 7 tools for MIND state management | ✅ |
| trigger-guardian-mcp | 6 tools for trigger routing | ✅ |
| Trigger Engine | Event-driven action execution | ✅ |
| Health Check Pipeline | L0/L1/L2 health checks | ✅ |
| VPN Rotator | 9 providers, --list, manual rotation | ✅ |
| Bootstrap Installer | Arch/Debian/Fedora support | ✅ |

### What's NOT IN v0.1.0-alpha.1

| System | Reason | Sprint |
|--------|--------|--------|
| LayerStack | Spec-only, deprecated | Never |
| Memory Cortex | Failed before (cortex/kernels/ never created) | Never |
| BMAD Workflows | Not feature-complete | Sprint 6+ |
| Auto-rotation | Not implemented | Sprint 6+ |
| Multi-machine sync | Not tested | Sprint 6+ |
| Cross-session memory | Requires semantic embeddings | Sprint 6+ |
| Preemptive compaction | Not implemented | Sprint 6+ |
| Lifecycle hooks | Not designed | Sprint 6+ |
| Docker images | Not needed for alpha | Later |
| PyPI publishing | No demand yet | Later |

---

## Context

### Agent Synthesis Summary

| Agent | Key Finding | Applied To Plan |
|-------|-------------|-----------------|
| **Metis** | Add industry standards: ruff, type hints, pre-commit, deployment checklist | ✅ Task 0, Task 7 |
| **Momus** | 3 critical blockers: import adaptation, health-check confusion, MCP already done | ✅ Fixed in tasks |
| **Oracle** | Ship MCP packages first, GitHub releases only, v0.1.0-alpha.1 | ✅ Applied |
| **Librarian** | PEP 8/257/484 compliance, pyproject.toml standards | ✅ Task 0 |
| **Explore** | src/nxyme_mind/ package layout, entry points | ✅ Structure |

### Metis Critical Directives (Applied)

- ✅ MUST: Version = "0.1.0a1" (PEP 440 alpha format)
- ✅ MUST: Add ruff, type hints, pre-commit, deployment checklist
- ✅ MUST: Create LICENSE, CHANGELOG, CONTRIBUTING
- ✅ MUST: Add version consistency checks
- ✅ MUST NOT: Ship with version "1.0.0" (users will think production-ready)
- ✅ MUST NOT: Include quarantined files in release artifact

### Momus Blockers Fixed

1. ✅ **Import adaptation**: Create `src/athena/core/config.py` with required constants
2. ✅ **health-check confusion**: Task 4 says "Rewrite" not "Create"
3. ✅ **MCP tool counts**: Clarified actual tool counts (7/7/6)

### Oracle Strategic Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Version scope? | MCP packages first | Ship working features |
| Distribution? | GitHub releases only | Manual, no automation |
| Launch criteria? | MCPs start + respond | Minimum viable |
| When to ship? | After Sprint 5 | All features working |

---

## Work Objectives

### Core Objective
Ship v0.1.0-alpha.1 as a working, testable release of N-Xyme MIND.

### Concrete Deliverables
- [ ] `src/nxyme_mind/` package with proper Python structure
- [ ] `src/athena/` with 5 core systems (Governance, Sentinel, Flight Recorder, Skill Telemetry, DeltaManifest)
- [ ] 3 MCP packages functional (athena-context, nx-mind, trigger-guardian)
- [ ] Health check pipeline (L0/L1/L2)
- [ ] 40+ tests passing
- [ ] Bootstrap installer working
- [ ] Standard files (LICENSE, CHANGELOG, CONTRIBUTING, README)
- [ ] GitHub release artifact

### Definition of Done
- [ ] `pytest tests/ -v` passes (40+ tests)
- [ ] All MCPs start via stdio and respond to tools/list
- [ ] `bin/health-check` exits 0
- [ ] `bin/trigger-status` exits 0
- [ ] `bin/verify-install` exits 0
- [ ] `python -m nxyme_mind --version` outputs v0.1.0a1
- [ ] Git tag v0.1.0-alpha.1 created

### Must Have
- Python 3.10+ (PEP 440 compliant)
- MIT License (source repos are MIT)
- All MCPs local stdio (no network)
- Ruff linting + formatting
- Type hints for public APIs
- Google-style docstrings

### Must NOT Have (Guardrails)
- ❌ Version "1.0.0" (would mislead users)
- ❌ LayerStack (spec-only, deprecated)
- ❌ Memory Cortex (failed before)
- ❌ Neo4j/PostgreSQL (Python-only constraint)
- ❌ npm dependencies for MCPs (Python-only)
- ❌ Docker/PyPI (not needed for alpha)

---

## Project Structure

### Directory Layout

```
N-Xyme_MIND_v0.1/
├── src/nxyme_mind/                  # Main package (PEP 8: lowercase)
│   ├── __init__.py                 # __version__ = "0.1.0a1"
│   ├── __version__.py              # VERSION = "0.1.0a1"
│   ├── __main__.py                # python -m nxyme_mind
│   │
│   ├── core/                      # Core infrastructure
│   │   ├── __init__.py
│   │   ├── config.py              # Config loader with PROJECT_ROOT
│   │   ├── trigger_engine.py       # Trigger execution
│   │   └── health.py             # Health check system
│   │
│   ├── athena/                    # Athena framework (MIT licensed)
│   │   ├── __init__.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── governance.py       # Doom Loop + Triple-Lock
│   │   │   ├── flight_recorder.py  # JSONL audit trail
│   │   │   └── skill_telemetry.py # Usage tracking
│   │   ├── intelligence/
│   │   │   ├── __init__.py
│   │   │   └── sentinel.py        # Boot/shutdown checks
│   │   └── memory/
│   │       ├── __init__.py
│   │       └── delta_manifest.py   # O(1) file sync
│   │
│   ├── cli/                       # CLI tools
│   │   ├── __init__.py
│   │   ├── main.py                # Main CLI (click/typer)
│   │   ├── health.py             # health-check command
│   │   └── status.py             # trigger-status command
│   │
│   └── mcp/                      # MCP packages (Python)
│       ├── __init__.py
│       ├── athena_context/
│       │   ├── __init__.py
│       │   ├── server.py          # FastMCP server
│       │   └── tools.py          # 7 context tools
│       ├── nx_mind/
│       │   ├── __init__.py
│       │   ├── server.py          # FastMCP server
│       │   └── tools.py          # 7 MIND tools
│       └── trigger_guardian/
│           ├── __init__.py
│           ├── server.py          # FastMCP server
│           └── tools.py          # 6 trigger tools
│
├── bin/                           # CLI scripts
│   ├── health-check.sh            # Unified health check
│   ├── health-l0-blink.sh        # Pre-flight (<1s)
│   ├── health-l1-pulse.sh        # Service check (<10s)
│   ├── health-l2-vitals.sh       # Deep integrity (<60s)
│   ├── trigger-status             # Trigger status
│   ├── vpn-rotate                # VPN rotation
│   ├── verify-install            # Post-install verification
│   └── download-github-mcp.sh    # GitHub MCP downloader
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
│   ├── unit/
│   │   ├── test_governance.py    # ≥5 tests
│   │   ├── test_sentinel.py      # ≥4 tests
│   │   ├── test_flight_recorder.py # ≥3 tests
│   │   ├── test_skill_telemetry.py # ≥4 tests
│   │   ├── test_delta_manifest.py  # ≥5 tests
│   │   ├── test_athena_context_mcp.py # ≥5 tests
│   │   ├── test_nx_mind_mcp.py   # ≥5 tests
│   │   └── test_trigger_guardian_mcp.py # ≥4 tests
│   └── integration/
│       ├── test_core.py          # Existing (4 tests)
│       ├── test_mcp_servers.py   # MCP integration
│       └── test_health_pipeline.py # Health check e2e
│
├── vpn/                           # VPN rotator
│   ├── rotator.py                 # Main rotator
│   └── providers/                # 9 provider plugins
│
├── docs/                          # Documentation
│   ├── ARCHITECTURE.md
│   ├── MCP_REGISTRY.md
│   └── CHANGELOG.md              # Auto-generated later
│
├── pyproject.toml                  # Package metadata + tool configs
├── ruff.toml                      # Ruff linting config
├── .pre-commit-config.yaml        # Pre-commit hooks
├── .gitignore                     # Git ignore patterns
├── Makefile                       # Build targets
│
├── README.md                      # Project overview
├── LICENSE                        # MIT License
├── CONTRIBUTING.md               # Contribution guide
├── CHANGELOG.md                  # Version history
│
└── bootstrap.sh                  # One-command installer
```

---

## Standard Files

### pyproject.toml

```toml
[project]
name = "nxyme-mind"
version = "0.1.0a1"
description = "Personal AI coding workspace — standalone, portable, self-healing"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.10"
authors = [{name = "N-Xyme"}]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Typing :: Typed",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.1.0",
    "mypy>=1.0",
]

[project.scripts]
nxyme = "nxyme_mind.cli.main:cli"

[tool.ruff]
target-version = "py310"
line-length = 120
src = ["src"]

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "B", "SIM", "RUF"]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["nxyme_mind"]

[tool.ruff.format]
quote-style = "double"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"

[tool.mypy]
python_version = "3.10"
warn_return_any = true
disallow_untyped_defs = false  # Relaxed for alpha
```

### LICENSE (MIT)

```text
MIT License

Copyright (c) 2026 N-Xyme

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 0 (Pre-flight - Start Immediately):
└── Task 0: Setup (version, config, ruff, pre-commit, LICENSE)

Wave 1 (Foundation - After Wave 0):
└── Task 1: Create package structure + __init__.py files

Wave 2 (Core Systems - After Wave 1):
└── Task 2: Copy 5 core systems from source repos

Wave 3 (Parallel - After Wave 2):
├── Task 3: Wire MCP packages to core systems
├── Task 4: Rewrite health-check + CLI integration
└── Task 5: Bundle github-mcp

Wave 4 (Final - After Wave 3):
└── Task 6: Expand tests (40+ tests)

Wave 5 (Release - After Wave 4):
└── Task 7: Documentation + Release artifact

Critical Path: Task 0 → Task 1 → Task 2 → Task 3 → Task 7
Parallel Speedup: ~25% faster (Wave 3)
Max Concurrent: 3 (Wave 3)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| Task 0 | — | Tasks 1-7 |
| Task 1 | Task 0 | Task 2 |
| Task 2 | Task 1 | Tasks 3, 4, 5 |
| Task 3 | Task 2 | Task 6 |
| Task 4 | Task 2 | Task 6 |
| Task 5 | Task 2 | Task 6 |
| Task 6 | Tasks 3, 4, 5 | Task 7 |
| Task 7 | Task 6 | — |

---

## TODOs

### Wave 0: Pre-flight

- [ ] **0. Setup Project Foundation**

  **What to do**:
  1. Create `pyproject.toml` with version = "0.1.0a1", ruff config, pytest config
  2. Create `src/nxyme_mind/__init__.py` with `__version__ = "0.1.0a1"`
  3. Create `LICENSE` (MIT - copy from nx_openmore)
  4. Create `CONTRIBUTING.md` with code standards
  5. Create `ruff.toml` with lint rules
  6. Create `.pre-commit-config.yaml` with ruff + secret scanning
  7. Create `.gitignore` (exclude .venv/, __pycache__/, .sisyphus/, data/)
  8. Create `Makefile` with targets: install, test, lint, format, quality-gates, clean
  9. Create `__init__.py` files for all packages

  **Must NOT do**:
  - Do NOT set version to "1.0.0" (would mislead users)
  - Do NOT add npm dependencies
  - Do NOT add Neo4j/PostgreSQL

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Setup tasks, straightforward
  - **Skills**: None required

  **Parallelization**:
  - **Can Run In Parallel**: NO (sequential setup)
  - **Blocks**: Tasks 1-7

  **References**:
  - Metis standards checklist
  - PEP 440 (version format)
  - PEP 8 (style guide)
  - ruff documentation

  **Acceptance Criteria**:
  - [ ] `python -c "from src.nxyme_mind import __version__; assert __version__ == '0.1.0a1'"` → no error
  - [ ] `grep -q "0.1.0a1" pyproject.toml` → true
  - [ ] `grep -q "MIT License" LICENSE` → true
  - [ ] `ruff check src/ --exit-zero` → 0 errors
  - [ ] `ruff format --check src/` → all formatted
  - [ ] `test -f .pre-commit-config.yaml` → true
  - [ ] `make lint` → 0 errors
  - [ ] `make test` → tests run

  **QA Scenarios**:

  ```
  Scenario: Version consistency check
    Tool: Bash
    Preconditions: pyproject.toml created
    Steps:
      1. python -c "from src.nxyme_mind import __version__; print(__version__)"
      2. grep "version" pyproject.toml | head -1
    Expected Result: Both show "0.1.0a1"
    Evidence: .sisyphus/evidence/task-0-version.txt

  Scenario: Ruff linting passes
    Tool: Bash
    Preconditions: ruff.toml created
    Steps:
      1. ruff check src/ --output-format=text --exit-zero | head -20
    Expected Result: 0 errors
    Evidence: .sisyphus/evidence/task-0-lint.txt
  ```

  **Commit**: YES
  - Message: `chore: setup project foundation with ruff, pre-commit, version 0.1.0a1`
  - Files: `pyproject.toml`, `src/nxyme_mind/__init__.py`, `LICENSE`, `CONTRIBUTING.md`, `ruff.toml`, `.pre-commit-config.yaml`, `.gitignore`, `Makefile`

---

### Wave 1: Package Structure

- [ ] **1. Create Package Structure**

  **What to do**:
  1. Create directory structure:
     ```
     src/nxyme_mind/
     ├── __init__.py
     ├── __version__.py
     ├── __main__.py
     ├── core/
     │   ├── __init__.py
     │   ├── config.py
     │   ├── trigger_engine.py
     │   └── health.py
     ├── athena/
     │   ├── __init__.py
     │   ├── core/
     │   │   └── __init__.py
     │   ├── intelligence/
     │   │   └── __init__.py
     │   └── memory/
     │       └── __init__.py
     ├── cli/
     │   ├── __init__.py
     │   └── main.py
     └── mcp/
         ├── __init__.py
         ├── athena_context/
         │   └── __init__.py
         ├── nx_mind/
         │   └── __init__.py
         └── trigger_guardian/
             └── __init__.py
     ```
  2. Create `src/nxyme_mind/__version__.py`:
     ```python
     """Version information."""
     VERSION = "0.1.0a1"
     VERSION_INFO = (0, 1, 0, "alpha", 1)
     ```
  3. Create `src/nxyme_mind/__main__.py`:
     ```python
     """Allow: python -m nxyme_mind"""
     from nxyme_mind.cli.main import cli
     if __name__ == "__main__":
         cli()
     ```
  4. Create `src/nxyme_mind/core/config.py` with:
     ```python
     """Configuration loader."""
     from pathlib import Path
     
     PROJECT_ROOT = Path(__file__).resolve().parents[2]
     DATA_DIR = PROJECT_ROOT / "data"
     CONFIG_DIR = PROJECT_ROOT / "configs"
     CONTEXT_DIR = PROJECT_ROOT / ".context"
     
     def get_config(name: str) -> dict:
         """Load config file."""
         import json
         path = CONFIG_DIR / f"{name}.json"
         if path.exists():
             return json.loads(path.read_text())
         return {}
     ```

  **Must NOT do**:
  - Do NOT import from non-existent modules
  - Do NOT create actual implementations yet (just structure)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Structure creation, straightforward
  - **Skills**: None required

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Task 2

  **References**:
  - PEP 517/518 (build system)
  - src layout standard

  **Acceptance Criteria**:
  - [ ] All `__init__.py` files exist
  - [ ] `python -c "import nxyme_mind; print(nxyme_mind.__version__)"` → "0.1.0a1"
  - [ ] `python -m nxyme_mind --help` → shows help
  - [ ] `python -c "from nxyme_mind.core.config import PROJECT_ROOT"` → no error

  **QA Scenarios**:

  ```
  Scenario: Package imports work
    Tool: Bash
    Preconditions: Structure created
    Steps:
      1. python -c "import nxyme_mind; from nxyme_mind.core.config import PROJECT_ROOT; print(PROJECT_ROOT)"
    Expected Result: Path printed, no ImportError
    Evidence: .sisyphus/evidence/task-1-imports.txt
  ```

  **Commit**: YES
  - Message: `feat: create package structure with __init__.py files`
  - Files: `src/nxyme_mind/`, `tests/`, `bin/`

---

### Wave 2: Core Systems

- [ ] **2. Copy Core Systems from Source Repos**

  **What to do**:
  1. Copy from `/mnt/Library/nx_openmore/athena/src/athena/`:
     - `core/governance.py` → `src/nxyme_mind/athena/core/governance.py`
     - `core/flight_recorder.py` → `src/nxyme_mind/athena/core/flight_recorder.py`
     - `core/skill_telemetry.py` → `src/nxyme_mind/athena/core/skill_telemetry.py`
     - `intelligence/sentinel.py` → `src/nxyme_mind/athena/intelligence/sentinel.py`
     - `memory/delta_manifest.py` → `src/nxyme_mind/athena/memory/delta_manifest.py`
  2. Update imports in copied files:
     - Replace `from athena.core.config import ...` with local imports
     - Create `src/nxyme_mind/athena/core/config.py` with needed symbols:
       - `PROJECT_ROOT`
       - `CONTEXT_DIR`
       - `CANONICAL_PATH`
       - `get_project_root()`
  3. Create unit tests for each system (≥5 tests per file)

  **Must NOT do**:
  - Do NOT modify copied logic (just adapt imports)
  - Do NOT add features not in original

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Reason**: Copy + adapt imports
  - **Skills**: None required

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Tasks 3, 4, 5

  **References**:
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
  - [ ] `pytest tests/unit/test_governance.py -v` → ≥5 tests pass
  - [ ] `pytest tests/unit/test_sentinel.py -v` → ≥4 tests pass
  - [ ] `pytest tests/unit/test_flight_recorder.py -v` → ≥3 tests pass
  - [ ] `pytest tests/unit/test_skill_telemetry.py -v` → ≥4 tests pass
  - [ ] `pytest tests/unit/test_delta_manifest.py -v` → ≥5 tests pass
  - [ ] `ruff check src/` → 0 errors

  **QA Scenarios**:

  ```
  Scenario: Governance Engine imports correctly
    Tool: Bash
    Preconditions: Files copied
    Steps:
      1. python -c "from nxyme_mind.athena.core.governance import GovernanceEngine, DoomLoopDetector, RiskLevel; print('OK')"
    Expected Result: "OK" printed, no ImportError
    Evidence: .sisyphus/evidence/task-2-governance.txt

  Scenario: Doom Loop detection works
    Tool: Bash
    Preconditions: Governance imported
    Steps:
      1. python -c "from nxyme_mind.athena.core.governance import DoomLoopDetector; d = DoomLoopDetector(); print([d.record('tool', {}) for _ in range(3)])"
    Expected Result: [False, False, True]
    Evidence: .sisyphus/evidence/task-2-doom-loop.txt
  ```

  **Commit**: YES
  - Message: `feat: import core systems from nx_openmore (Governance, Sentinel, Flight Recorder, Skill Telemetry, DeltaManifest)`
  - Files: `src/nxyme_mind/athena/`, `tests/unit/test_*.py`

---

### Wave 3: MCP Integration (Parallel)

- [ ] **3. Wire MCP Packages to Core Systems**

  **What to do**:
  1. **athena-context-mcp** (7 tools):
     - `get_active_context` — reads `.context/activeContext.md`
     - `get_product_context` — reads `.context/productContext.md`
     - `get_user_context` — reads `.context/userContext.md`
     - `get_constraints` — reads `.context/constraints.md`
     - `get_bmad_agents` — reads `_bmad/_config/agents/`
     - `get_bmad_workflows` — reads `_bmad/*/workflows/`
     - `inject_context` — writes context to session
  2. **nx-mind-mcp** (7 tools):
     - `get_mind_state` — reads `.context/mind-state.json`
     - `update_mind_state` — writes to mind-state.json
     - `get_session_history` — reads session logs
     - `get_active_workflow` — scans `_bmad/catalyst/`
     - `set_context` — sets context key-value
     - `sync_to_memory` — syncs to memory MCP
     - `get_project_manifest` — reads `.context/project-manifest.json`
  3. **trigger-guardian-mcp** (6 tools):
     - `register_trigger` — adds to triggers.json
     - `list_triggers` — reads triggers.json
     - `check_trigger` — matches input against triggers
     - `get_trigger_handlers` — gets handlers for trigger
     - `log_trigger_event` — logs to event history
     - `clear_triggers` — resets triggers.json
  4. Wire each to FastMCP
  5. Add unit tests for each MCP

  **Must NOT do**:
  - Do NOT add new MCPs (3 is the limit)
  - Do NOT use network transports (stdio only)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Reason**: MCP implementation with FastMCP
  - **Skills**: None required

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 4, 5)
  - **Blocks**: Task 6

  **References**:
  - `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/trigger-guardian-mcp/` — Current implementation
  - `/mnt/NXYME_CORE/00_N-Xyme_CATALYST/mcp-servers/session-manager/` — Reference

  **Acceptance Criteria**:
  - [ ] `python -m nxyme_mind.mcp.athena_context` starts without error
  - [ ] `python -m nxyme_mind.mcp.nx_mind` starts without error
  - [ ] `python -m nxyme_mind.mcp.trigger_guardian` starts without error
  - [ ] Each MCP responds to `tools/list` with correct count (7/7/6)
  - [ ] `pytest tests/unit/test_athena_context_mcp.py -v` → ≥5 tests
  - [ ] `pytest tests/unit/test_nx_mind_mcp.py -v` → ≥5 tests
  - [ ] `pytest tests/unit/test_trigger_guardian_mcp.py -v` → ≥4 tests

  **QA Scenarios**:

  ```
  Scenario: athena-context-mcp starts and lists tools
    Tool: Bash
    Preconditions: MCP wired
    Steps:
      1. echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | timeout 5 python -m nxyme_mind.mcp.athena_context 2>/dev/null | head -1
    Expected Result: Valid JSON-RPC response
    Evidence: .sisyphus/evidence/task-3-athena-mcp.txt
  ```

---

- [ ] **4. Rewrite Health Check + CLI Integration**

  **What to do**:
  1. Rewrite `bin/health-check.sh` with new checks:
     - Sentinel boot check
     - Trigger count verification
     - MCP stdio start verification
     - Flight recorder accessibility
  2. Create `src/nxyme_mind/cli/main.py` with click/typer:
     ```python
     """CLI entry point."""
     import click
     from nxyme_mind import __version__
     
     @click.group()
     @click.version_option(version=__version__)
     def cli():
         """N-Xyme MIND CLI."""
         pass
     
     @cli.command()
     def status():
         """Show trigger status."""
         from nxyme_mind.core.trigger_engine import TriggerEngine
         te = TriggerEngine()
         click.echo(f"Triggers: {len(te.list_triggers())}")
     
     @cli.command()
     def health():
         """Run health checks."""
         # Run health checks
         click.echo("✓ All checks passed")
     ```

  **Must NOT do**:
  - Do NOT check for things that don't exist (OpenCode, Neo4j, etc.)
  - Do NOT add complex workflows

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Reason**: CLI + health check integration
  - **Skills**: None required

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 3, 5)
  - **Blocks**: Task 6

  **References**:
  - `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/bin/health-check.sh` (existing, rewrite)
  - Click documentation

  **Acceptance Criteria**:
  - [ ] `bin/health-check.sh` exits 0
  - [ ] `bin/trigger-status` exits 0
  - [ ] `python -m nxyme_mind --version` → v0.1.0a1
  - [ ] `python -m nxyme_mind status` → shows trigger count
  - [ ] `python -m nxyme_mind health` → runs health checks

  **QA Scenarios**:

  ```
  Scenario: Health check script runs successfully
    Tool: Bash
    Preconditions: Script rewritten
    Steps:
      1. bin/health-check.sh; echo "Exit code: $?"
    Expected Result: Exit code 0
    Evidence: .sisyphus/evidence/task-4-health.txt
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
  3. Update `pyproject.toml`:
     - Add github-mcp as optional dependency
     - Set `optional = true`

  **Must NOT do**:
  - Do NOT commit binary to git
  - Do NOT hardcode version

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Simple download script
  - **Skills**: None required

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 3, 4)
  - **Blocks**: Task 6

  **References**:
  - GitHub releases: `https://github.com/github/github-mcp-server/releases`

  **Acceptance Criteria**:
  - [ ] `bin/download-github-mcp.sh` downloads correct binary (or handles gracefully offline)
  - [ ] `bin/.github-mcp-version` exists after download
  - [ ] Bootstrap handles missing github-mcp gracefully

  **QA Scenarios**:

  ```
  Scenario: Download script handles offline gracefully
    Tool: Bash
    Preconditions: No network
    Steps:
      1. bin/download-github-mcp.sh 2>&1 | head -5
    Expected Result: Warning message, not crash
    Evidence: .sisyphus/evidence/task-5-offline.txt
  ```

---

### Wave 4: Tests

- [ ] **6. Expand Integration Tests (40+ Tests)**

  **What to do**:
  1. Create `tests/integration/test_mcp_servers.py`:
     - Each MCP starts via stdio
     - Each MCP responds to tools/list
     - Each tool returns valid response
  2. Create `tests/integration/test_health_pipeline.py`:
     - Run health-check → verify output
     - Run trigger-status → verify output
     - Simulate trigger evaluation
  3. Expand existing tests to reach 40+ total
  4. Run all tests: `pytest tests/ -v`

  **Must NOT do**:
  - Do NOT skip tests
  - Do NOT use `pytest.mark.skip`

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Reason**: Test writing, straightforward
  - **Skills**: None required

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Task 7

  **References**:
  - `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/tests/integration/test_core.py` — Existing pattern

  **Acceptance Criteria**:
  - [ ] `pytest tests/integration/ -v` → ≥15 tests pass
  - [ ] `pytest tests/ -v` → ≥40 tests pass
  - [ ] No skipped tests
  - [ ] Test coverage ≥70%

  **QA Scenarios**:

  ```
  Scenario: All tests pass
    Tool: Bash
    Preconditions: Tests expanded
    Steps:
      1. pytest tests/ -v --tb=short 2>&1 | tail -30
    Expected Result: All tests passed, ≥40 tests
    Evidence: .sisyphus/evidence/task-6-all-tests.txt
  ```

  **Commit**: YES
  - Message: `test: expand integration tests to 40+ tests`
  - Files: `tests/integration/`

---

### Wave 5: Release

- [ ] **7. Documentation + Release Artifact**

  **What to do**:
  1. Create `README.md`:
     ```markdown
     # N-Xyme MIND v0.1.0-alpha
     
     Personal AI coding workspace — standalone, portable, self-healing.
     
     ## Status: Alpha
     
     This is a pre-release. APIs may change.
     
     ## Quick Start
     
     ```bash
     bash bootstrap.sh
     python -m nxyme_mind --version
     ```
     
     ## What's Included
     - Governance Engine, Sentinel, Flight Recorder, Skill Telemetry, DeltaManifest
     - 3 MCP servers (athena-context, nx-mind, trigger-guardian)
     - Health check pipeline
     - VPN rotator
     
     ## What's NOT Included
     - LayerStack (deprecated)
     - Memory Cortex (failed)
     
     ## License: MIT
     ```
  2. Create `CHANGELOG.md`:
     ```markdown
     # Changelog
     
     ## [0.1.0-alpha.1] - 2026-04-04
     
     ### Added
     - Governance Engine with Doom Loop detection
     - Sentinel Protocol for boot/shutdown checks
     - Flight Recorder for JSONL audit trail
     - Skill Telemetry for usage tracking
     - DeltaManifest for O(1) file sync
     - 3 MCP servers (athena-context, nx-mind, trigger-guardian)
     - Health check pipeline
     - VPN rotator
     
     ### Known Issues
     - Multi-machine sync not implemented
     - github-mcp requires manual download
     ```
  3. Create `bin/verify-install`:
     ```bash
     #!/usr/bin/env bash
     set -e
     echo "Verifying N-Xyme MIND installation..."
     python -m nxyme_mind --version
     pytest tests/ -v -x
     bin/health-check.sh
     echo "✓ Installation verified"
     ```
  4. Create git tag: `v0.1.0-alpha.1`
  5. Create GitHub release artifact

  **Must NOT do**:
  - Do NOT hardcode paths in docs
  - Do NOT reference non-existent features

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Reason**: Documentation focus
  - **Skills**: `git-master` for clean tag

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: None (final task)

  **References**:
  - Keep a Changelog format
  - Semantic versioning

  **Acceptance Criteria**:
  - [ ] `README.md` exists with quick start
  - [ ] `CHANGELOG.md` has v0.1.0-alpha.1 entry
  - [ ] `bin/verify-install` exits 0
  - [ ] `git tag v0.1.0-alpha.1` created
  - [ ] GitHub release artifact created
  - [ ] `pytest tests/ -v` → ≥40 tests after fresh clone

  **QA Scenarios**:

  ```
  Scenario: Verify install script works
    Tool: Bash
    Preconditions: Docs created
    Steps:
      1. bin/verify-install
    Expected Result: Exit code 0, "Installation verified"
    Evidence: .sisyphus/evidence/task-7-verify.txt

  Scenario: Git tag exists
    Tool: Bash
    Preconditions: Tag created
    Steps:
      1. git tag -l "v0.1*"
    Expected Result: v0.1.0-alpha.1 listed
    Evidence: .sisyphus/evidence/task-7-tag.txt
  ```

  **Commit**: YES
  - Message: `chore: v0.1.0-alpha.1 release — documentation and release artifact`
  - Files: `README.md`, `CHANGELOG.md`, `bin/verify-install`, git tag

---

## Final Verification Wave

- [ ] **F1. Plan Compliance Audit** — `oracle`
  Verify all 7 tasks have implementation. Verify no LayerStack/Memory Cortex references.

- [ ] **F2. Code Quality Review** — `unspecified-high`
  Run `ruff check src/`. Run `ruff format --check src/`. Run `mypy src/`.

- [ ] **F3. Integration Test Pass** — `unspecified-high`
  Run `pytest tests/ -v` — verify ≥40 tests pass.

- [ ] **F4. Version Consistency** — `deep`
  Verify `__version__` = pyproject.toml = CHANGELOG = git tag.

- [ ] **F5. Release Artifact** — `unspecified-high`
  Verify tarball/zipball created with all required files.

---

## Commit Strategy

| Wave | Message | Files |
|------|---------|-------|
| Wave 0 | `chore: setup project foundation with ruff, pre-commit, version 0.1.0a1` | pyproject.toml, ruff.toml, LICENSE, Makefile |
| Wave 1 | `feat: create package structure with __init__.py files` | src/nxyme_mind/ |
| Wave 2 | `feat: import core systems from nx_openmore` | src/nxyme_mind/athena/ |
| Wave 3 | `feat: wire MCP packages and health checks` | src/nxyme_mind/mcp/, bin/, cli/ |
| Wave 4 | `test: expand integration tests to 40+ tests` | tests/ |
| Wave 5 | `chore: v0.1.0-alpha.1 release` | README.md, CHANGELOG.md, git tag |

---

## Success Criteria

### Verification Commands
```bash
# Version check
python -m nxyme_mind --version  # Expected: 0.1.0a1

# Quality gates
make lint        # Expected: 0 errors
make test        # Expected: ≥40 tests pass
make quality-gates  # Expected: All pass

# Health checks
bin/health-check.sh  # Expected: Exit 0
bin/trigger-status  # Expected: Exit 0

# MCP servers
python -m nxyme_mind.mcp.athena_context --help  # Expected: Help output
python -m nxyme_mind.mcp.nx_mind --help
python -m nxyme_mind.mcp.trigger_guardian --help

# Release
git tag -l "v0.1*"  # Expected: v0.1.0-alpha.1
```

### Final Checklist
- [ ] All 7 tasks complete
- [ ] ≥40 tests passing
- [ ] All MCPs functional
- [ ] Health checks working
- [ ] Version consistent (0.1.0a1)
- [ ] README, CHANGELOG, LICENSE present
- [ ] Git tag v0.1.0-alpha.1 created
- [ ] GitHub release artifact created
- [ ] No hardcoded paths
- [ ] No LayerStack/Memory Cortex
- [ ] ruff linting passes
- [ ] pre-commit hooks configured

---

## Distribution Plan

### v0.1.0-alpha.1 Release

| Channel | Status | Notes |
|---------|--------|-------|
| GitHub Releases | ✅ Primary | Manual upload, tarball + zipball |
| PyPI | ❌ Not yet | No demand, manual upload later |
| Docker Hub | ❌ Not yet | Native Linux works without |
| conda | ❌ Not later | No demand |

### Release Checklist
- [ ] Create git tag: `git tag -a v0.1.0-alpha.1 -m "v0.1.0-alpha.1"`
- [ ] Push tag: `git push origin v0.1.0-alpha.1`
- [ ] Create GitHub release with:
  - Tag: v0.1.0-alpha.1
  - Title: N-Xyme MIND v0.1.0-alpha.1
  - Description: Copy from CHANGELOG.md
  - Assets: Source code (tarball), zipball
- [ ] Verify release artifact:
  ```bash
  wget https://github.com/nxyme/n-xyme-mind/releases/download/v0.1.0-alpha.1/n-xyme-mind-0.1.0a1.tar.gz
  tar -xzf n-xyme-mind-0.1.0a1.tar.gz
  cd n-xyme-mind-0.1.0a1
  bash bootstrap.sh
  pytest tests/ -v
  ```

---

## Missing Patterns (Sprint 6+)

| Pattern | Description | Priority |
|---------|-------------|----------|
| Preemptive Context Compaction | Auto-compact at 85% context | High |
| Provider-Level Circuit Breaker | Track failures per LLM | High |
| Lifecycle Hook System | 40+ hooks for agent lifecycle | Medium |
| Cross-Session Semantic Memory | Learn from past sessions | Medium |
| MCP Auto-Discovery | Dynamic MCP registry | Low |

---

## Anti-Patterns to Avoid

1. ❌ **LayerStack** — Spec-only, deprecated, 7 layers = complexity without value
2. ❌ **Memory Cortex** — Failed before (cortex/kernels/ never created)
3. ❌ **New MCPs** — 3 is the limit
4. ❌ **Neo4j/PostgreSQL** — Python-only, local stdio
5. ❌ **npm for MCPs** — Python-only
6. ❌ **Version "1.0.0"** — Would mislead users
7. ❌ **Spec without code** — Every system must have working implementation

---

## Source Attribution (MIT Licensed)

| Source | License | Components |
|--------|---------|------------|
| nx_openmore | MIT | Governance Engine, Sentinel, Flight Recorder, Skill Telemetry, DeltaManifest |
| N-Xyme_CATALYST | MIT | MCP package patterns, session management |
| anomalyco/opencode | MIT | Agent system inspiration |
| code-yeongyu/oh-my-openagent | MIT | Agent orchestration patterns |

---

*Plan synthesized from 5 agent consultations: Metis, Momus, Oracle, Librarian, Explore*
*Version: v0.1.0-alpha.1 — Production-Ready Release Plan*
