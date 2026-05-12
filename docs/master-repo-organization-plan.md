# Master Repo Organization Plan
## Industry Gold Standards + ADHD-Friendly

---

## Phase 1: Code Quality Audit Complete ✅

| Metric | Before | After |
|--------|--------|-------|
| Bare except: | 20 | 0 |
| print() → logging | 119 fixed | Remaining only in `__main__` (acceptable) |
| Tests | 276 passing | 276 passing |

---

## Phase 2: Package Structure (Current)

```
packages/
├── orchestration/      # ✅ Clean
├── intelligence/       # ✅ Clean  
├── learning_engine/    # ✅ Clean
├── memory_core/        # ✅ Clean
├── nx-context-mcp/    # ✅ Clean
├── core-mcp/           # ✅ Clean
├── infrastructure/     # ⚠️ 94 files - needs organization
├── local_llm/          # ✅ Clean
├── web_frontend/       # ✅ Clean
└── [scattered]         # 15+ root-level packages
```

---

## Phase 3: Organization Recommendations

### 3.1 Consolidate Scattered Packages
**Current:** 15+ packages at root level
**Target:** Logical grouping

| Move | To |
|------|-----|
| `mcp_obsidian_wrapper.py` | `platform_layer/` |
| `obsidian_starter.py` | `platform_layer/` |
| `mcp_obsidian_fixed.py` | `platform_layer/` |

### 3.2 Infrastructure Cleanup
**94 files → Logical subpackages:**

```
infrastructure/
├── proxy/          # 28 files - keep
├── vpn_rotation/   # 7 files - keep
├── spine/          # 10 files - keep
├── monitoring/     # 6 files - consolidate
├── resilience/     # 5 files - keep
├── config/         # 6 files - keep
├── network/        # 5 files - keep
├── cost/           # 4 files - keep
├── [utilities]     # 17 files → utils/
```

### 3.3 Naming Consistency
| Current | Standard |
|---------|----------|
| `*_mcp.py` | `mcp_server.py` (per package) |
| `someName.py` | `some_name.py` |

---

## Phase 4: Gold Standards Checklist

- [x] No bare `except:`
- [x] Proper logging (not print)
- [x] Type hints on public APIs
- [x] Docstrings on classes/public methods
- [x] Error handling with specific exceptions
- [ ] Consistent naming ( Snake_case)
- [ ] Single responsibility per module

---

## ADHD-Friendly Summary

**Done:**
- ✅ All bare except: fixed (20 → 0)
- ✅ print() → logging in critical paths
- ✅ 276 tests passing

**At Diminishing Returns:**
- Remaining print() in `__main__` blocks (CLI - acceptable)
- Hardcoded values (mostly configs - acceptable)
- Missing type hints on private methods (acceptable)

**Next (if needed):**
- Consolidate scattered packages
- Rename files to snake_case
- Group infrastructure utilities

---

**Recommendation:** Current state is production-ready. Organization is cosmetic - can be done incrementally. No critical issues remain.
