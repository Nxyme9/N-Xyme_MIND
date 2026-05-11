# 🔧 AUDIT FIX MASTER PLAN
## N-Xyme_MIND Security & Quality Hardening

### Priority Matrix

| Priority | Issue | Impact | Effort | Files |
|----------|-------|--------|--------|-------|
| P0-CRITICAL | SQL Injection | Security | High | 11 |
| P0-CRITICAL | Command Injection | Security | Medium | 2 |
| P0-CRITICAL | Hardcoded Credentials | Security | Low | 3 |
| P1-HIGH | Bare except: patterns | Reliability | Medium | 48 |
| P2-MEDIUM | Duplicate SelfHealer (DRY) | Maintainability | Medium | 2 |
| P2-MEDIUM | Connection Pooling | Performance | High | 1 |
| P2-MEDIUM | Missing Type Hints | Maintainability | High | ~100 |
| P3-LOW | Test conftest.py | Testing | Low | 1 |
| P3-LOW | Feature Branch Workflow | Process | Medium | 1 |

---

## 🚀 PARALLEL EXECUTION WORKSTREAMS

### WORKSTREAM A: SECURITY (P0 - Can run parallel with B,C,D)

| Task | Agent | Files |
|------|-------|-------|
| Fix SQL Injection | hephaestus | packages/memory_core/self_healer.py, migrations/*.py, mcp_server.py, scripts/*.py, sqlite_mcp/__init__.py |
| Fix Command Injection | hephaestus | athena/scripts/boot.py, athena/examples/scripts/boot.py |
| Fix Hardcoded Credentials | sisyphus-junior | tests/test_langgraph_workflow.py, hindsight_mcp.py, hindsight_mcp/__main__.py |

### WORKSTREAM B: ERROR HANDLING (P1 - Can run parallel with A,C,D)

| Task | Agent | Files |
|------|-------|-------|
| Replace bare except: with specific exceptions | hephaestus | 48 files across packages/orchestration, packages/memory_core, scripts/ |
| Add logging to except Exception handlers | hephaestus | 151 files (review critical ones first) |

### WORKSTREAM C: ARCHITECTURE (P2 - Can run parallel with A,B,D)

| Task | Agent | Files |
|------|-------|-------|
| Extract shared SelfHealer base class | hephaestus | packages/orchestration/self_healer.py, packages/memory_core/self_healer.py |
| Add connection pooling to relational_store | hephaestus | packages/memory_core/stores/relational_store.py |
| Add type hints to infrastructure modules | hephaestus | packages/infrastructure/, packages/platform_layer/ |

### WORKSTREAM D: TESTING & PROCESS (P3 - Can run parallel with A,B,C)

| Task | Agent | Files |
|------|-------|-------|
| Create shared tests/conftest.py | sisyphus-junior | tests/conftest.py (new) |
| Document feature branch workflow | sisyphus-junior | docs/git-workflow.md (new) |

---

## 📋 DETAILED FIX INSTRUCTIONS

### P0.1: SQL Injection Fix (11 files)

**Pattern to fix:**
```python
# BAD - f-string SQL
f"SELECT * FROM {table_name}"
f"INSERT INTO {table} VALUES (...)"

# GOOD - Parameterized
cursor.execute("SELECT * FROM ?", (table_name,))  # for table names (whitelist)
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))  # for values
```

**Files requiring fix:**
1. packages/memory_core/self_healer.py (lines 273, 290, 341, 347, 367)
2. packages/memory_core/migrations/migrate_nx_openmore.py (146, 189, 232, 275)
3. packages/memory_core/migrations/migrate_nxyme_catalyst.py (220, 263)
4. packages/memory_core/mcp_server.py (191)
5. scripts/import-docs.py (50, 61)
6. scripts/rename-sessions.py (63, 84, 118)
7. scripts/synthesize-unified-memory.py (40)
8. packages/local_llm/caching.py (222)
9. packages/sqlite-mcp/sqlite_mcp/__init__.py (63, 88)

### P0.2: Command Injection Fix (2 files)

**Pattern to fix:**
```python
# BAD - os.system with f-string
os.system(f"cd {PROJECT_ROOT} && some_command")

# GOOD - subprocess with list (shell=False)
subprocess.run(["some_command", arg1], shell=False, cwd=PROJECT_ROOT)
```

**Files requiring fix:**
1. athena/scripts/boot.py (lines 45, 51, 59)
2. athena/examples/scripts/boot.py (lines 44, 50, 58, 111)

### P0.3: Hardcoded Credentials Fix (3 files)

**Pattern to fix:**
```python
# BAD
neo4j_password="password"
memory_llm_api_key="ollama"

# GOOD - Environment variable
import os
api_key = os.environ.get("MEMORY_LLM_API_KEY", "ollama")  # with default for dev
```

**Files requiring fix:**
1. tests/test_langgraph_workflow.py (lines 37, 69, 104, 150, 161)
2. hindsight_mcp.py (line 19)
3. hindsight_mcp/__main__.py (line 12)

### P1: Bare except: Fix (87 instances across 48 files)

**Priority files (affect orchestration):**
1. packages/orchestration/triggers/engine.py (line 72)
2. packages/orchestration/tool_categories.py (multiple)
3. packages/orchestration/__init__.py (line 78)
4. packages/memory_core/mcp_server.py (multiple)
5. scripts/gguf_auto_tuner.py (lines 52,65,76,120,132,137)
6. scripts/health_monitor.py (line 321)
7. bin/socks5-server.py (line 158)
8. bin/http-proxy-vpn.py (line 165)

**Pattern to fix:**
```python
# BAD
except:
except Exception:

# GOOD
except (ValueError, TypeError) as e:
    logger.error(f"Specific error: {e}")
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
```

---

## ✅ SUCCESS CRITERIA

- [ ] All P0 security issues fixed (SQL injection, cmd injection, credentials)
- [ ] All bare except: replaced with specific exception types
- [ ] Duplicate SelfHealer consolidated to single source
- [ ] Connection pooling added to relational_store
- [ ] Type hints added to 50+ infrastructure files
- [ ] Test conftest.py created with shared fixtures
- [ ] Feature branch workflow documented
- [ ] Run full test suite after changes

---

*Generated: 2026-04-09*
*Source: 10-agent parallel audit*