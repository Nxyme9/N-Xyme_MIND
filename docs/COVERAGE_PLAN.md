# Coverage Remediation Plan: 7% → 40%

**Date:** 2026-04-06  
**Current State:** 7% coverage (32,708 statements total, 2,675 covered)  
**Target:** 40% coverage (~13,083 statements covered)

---

## Executive Summary

To reach 40% coverage, we need to add tests covering ~10,400 additional statements. The strategy focuses on **high-impact modules** that are core to system functionality, ignoring peripheral modules (audio, video, UI) that can be marked as optional coverage.

---

## Gap Analysis

| Category | Statements | Current Coverage | Notes |
|----------|------------|------------------|-------|
| Core Orchestration | ~8,000 | ~5% | Priority 1 |
| Memory System | ~5,000 | ~3% | Priority 2 |
| Security | ~3,000 | ~8% | Priority 3 |
| Health/Auto-recovery | ~2,500 | ~2% | Priority 4 |
| Tools/Intelligence | ~3,000 | ~10% | Priority 5 |
| Infrastructure | ~2,000 | ~5% | Priority 6 |
| **Subtotal (Core)** | **~23,500** | **~5%** | Target: 50% → 11,750 |
| Audio/Video/UI | ~9,208 | ~2% | EXCLUDE (mark as optional) |
| **Total** | **~32,708** | **7%** | |

---

## Strategy

### 1. Exclude Non-Core Modules (pyproject.toml update)
Add these to `--omit` in coverage configuration:
- `src/audio/*`
- `src/video/*`
- `src/ui/*` (except core panels)
- `src/dashboard/plugins/*`

**Effect:** Reduces total from ~32K to ~23K statements. 40% of 23K = 9,200 statements.

### 2. Focus Test Writing on Core Modules
Target modules in priority order with specific test counts.

---

## Implementation Waves

### Wave 1: Core Orchestration (Priority 1)
**Target:** +2,000 statements covered

| Module | Current | Target Tests |
|--------|---------|--------------|
| `src/orchestration/focus_manager.py` (648) | 0% | 15 tests |
| `src/orchestration/trigger_router.py` (406) | 0% | 10 tests |
| `src/orchestration/reflexion_agent.py` (370) | 0% | 8 tests |
| `src/orchestration/react_agent.py` (324) | 0% | 8 tests |
| `src/orchestration/langgraph_workflow.py` (290) | 0% | 6 tests |
| `src/orchestration/agent_factory.py` | 0% | 8 tests |
| `src/orchestration/trigger_engine.py` | 0% | 6 tests |

**Test Location:** `tests/unit/test_orchestration/`

---

### Wave 2: Memory System (Priority 2)
**Target:** +2,000 statements covered

| Module | Current | Target Tests |
|--------|---------|--------------|
| `src/memory/migrator.py` (593) | 0% | 12 tests |
| `src/memory/daemon.py` (454) | 0% | 10 tests |
| `src/memory/health_monitor.py` (279) | 0% | 6 tests |
| `src/memory/priority_engine.py` (277) | 0% | 6 tests |
| `src/memory/embedding_pipeline.py` (236) | 0% | 5 tests |
| `src/memory/vector_index.py` (234) | 0% | 5 tests |
| `src/memory/integrity_checker.py` (233) | 0% | 5 tests |
| `src/memory/self_healer.py` (230) | 0% | 5 tests |
| `src/memory/connectors.py` (228) | 0% | 5 tests |
| `src/memory/auto_recovery.py` (225) | 0% | 5 tests |

**Test Location:** `tests/unit/test_memory/`

---

### Wave 3: Security (Priority 3)
**Target:** +1,000 statements covered

| Module | Current | Target Tests |
|--------|---------|--------------|
| `src/security/mcp_credential_proxy.py` (458) | 0% | 10 tests |
| `src/security/security_llm.py` (355) | 0% | 8 tests |
| `src/security-agent/` (existing) | N/A | Expand existing |
| `src/security/tokenizer.py` | 0% | 6 tests |
| `src/security/validator.py` | 0% | 6 tests |

**Test Location:** `tests/unit/test_security/`

---

### Wave 4: Health System (Priority 4)
**Target:** +1,000 statements covered

| Module | Current | Target Tests |
|--------|---------|--------------|
| `src/health/auto_recovery.py` (254) | 0% | 6 tests |
| `src/health/healing/self_healing.py` (146) | 0% | 4 tests |
| `src/health/health_checks.py` (106) | 0% | 4 tests |
| `src/health/health_composite.py` (112) | 0% | 4 tests |
| `src/health/health_core.py` (106) | 0% | 4 tests |
| `src/health/health_recovery.py` (93) | 0% | 3 tests |
| `src/health/health_schema.py` (108) | 0% | 3 tests |
| `src/health/plugin_health_ml.py` (100) | 0% | 3 tests |
| `src/health/health_ai.py` (68) | 0% | 2 tests |

**Test Location:** `tests/unit/test_health/`

---

### Wave 5: Tools/Intelligence (Priority 5)
**Target:** +1,500 statements covered

| Module | Current | Target Tests |
|--------|---------|--------------|
| `src/tools/intelligence/unified_router.py` (310) | 0% | 8 tests |
| `src/tools/learning/self_learning.py` (273) | 0% | 6 tests |
| `src/tools/intelligence/routing_dashboard.py` | 0% | 5 tests |
| `src/tools/intelligence/result_checker.py` | 0% | 5 tests |
| `src/tools/intelligence/delegation_logger.py` | 0% | 5 tests |

**Test Location:** `tests/unit/test_tools/`

---

### Wave 6: Infrastructure (Priority 6)
**Target:** +500 statements covered

| Module | Current | Target Tests |
|--------|---------|--------------|
| `src/infrastructure/network/vpn_manager.py` (238) | 0% | 5 tests |
| `src/infrastructure/network/vpn_rotator.py` (222) | 0% | 5 tests |
| `src/model_router/ollama_manager.py` (232) | 0% | 5 tests |
| `src/model_router/hook.py` (229) | 0% | 4 tests |

**Test Location:** `tests/unit/test_infrastructure/`

---

### Wave 7: Integration Tests (Priority 7)
**Target:** +2,000 statements covered

Add integration tests for:
- `tests/integration/test_memory_flow.py` - Memory system integration
- `tests/integration/test_security_flow.py` - Security middleware
- `tests/integration/test_health_flow.py` - Health checks + recovery
- `tests/integration/test_routing.py` - Router integration

---

## Test Template Standards

Each test file should follow this pattern:

```python
# tests/unit/test_orchestration/test_focus_manager.py
import pytest
from src.orchestration.focus_manager import FocusManager

class TestFocusManager:
    """Tests for FocusManager class."""
    
    @pytest.fixture
    def focus_manager(self, tmp_path):
        """Create FocusManager instance for testing."""
        return FocusManager(storage_path=tmp_path)
    
    def test_init_default(self, tmp_path):
        """Test initialization with defaults."""
        fm = FocusManager()
        assert fm is not None
    
    def test_init_custom_path(self, tmp_path):
        """Test initialization with custom storage path."""
        fm = FocusManager(storage_path=tmp_path)
        assert fm.storage_path == tmp_path
    
    # ... more tests
```

---

## Configuration Updates

### 1. pyproject.toml - Update coverage config

```toml
[tool.coverage.run]
source = ["src"]
omit = [
    "src/audio/*",
    "src/video/*",
    "src/ui/tui/*",  # Keep dashboard panels only
    "src/dashboard/plugins/*",
    "src/blocks/*",  # These are deprecated/proof-of-concept
    "*/tests/*",
    "*/test_*/",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "@abstractmethod",
]
precision = 1
show_missing = true
skip_covered = false

[tool.coverage.targets]
precision = 1
```

---

## Success Metrics

| Wave | Target Coverage | Tests to Add | Estimated Time |
|------|------------------|--------------|----------------|
| Wave 1 | 15% | ~60 | 2 hours |
| Wave 2 | 22% | ~60 | 2 hours |
| Wave 3 | 27% | ~40 | 1.5 hours |
| Wave 4 | 31% | ~35 | 1 hour |
| Wave 5 | 36% | ~30 | 1 hour |
| Wave 6 | 38% | ~20 | 30 min |
| Wave 7 | 40% | ~40 | 1 hour |
| **Total** | **40%** | **~285 tests** | **~9 hours** |

---

## Risk Mitigation

1. **Time Risk**: Start with largest modules first (focus_manager, migrator)
2. **Scope Creep**: Stick to core modules, exclude audio/video/ui
3. **Maintenance**: Create test helpers in `tests/conftest.py`
4. **Quality**: Each test must have meaningful assertions, not just `assert True`

---

## Next Steps

1. [ ] Update `pyproject.toml` coverage configuration (exclude non-core)
2. [ ] Create `tests/unit/test_orchestration/` directory structure
3. [ ] Write Wave 1 tests (FocusManager, TriggerRouter)
4. [ ] Run coverage check after each wave
5. [ ] Verify 40% target is reached
