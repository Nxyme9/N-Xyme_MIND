# Tightening Review & Wiring Plan

> **Goal**: Wire or kill the 5 dead modules, fix broken tests, clean dead files, and make the tightening actually tighten.
> **Scope**: `src/intelligence/`, `src/state/`, `tests/`, `bin/quality-gates/`
> **Approach**: TDD-first. Every wiring change gets tests BEFORE implementation.

---

## Wave 0: Fix Broken Tests (Unblock Everything)

### Task 0.1: Fix `test_delegation_flow.py::test_cache_hit_exact_match`
- **File**: `tests/integration/test_delegation_flow.py` line ~252
- **Problem**: `assert data["found"] is True` fails — the `check-results.sh` script doesn't find the cached result
- **Action**: Debug the test setup. The `_setup_result_store()` writes a result, then `check-results.sh` should find it. Check if the result store file path matches what the script reads.
- **QA**: `python -m pytest tests/integration/test_delegation_flow.py::TestResultStore::test_cache_hit_exact_match -v` → PASS

### Task 0.2: Fix `test_full_system_wiring.py` pytest fixture error
- **File**: `tests/integration/test_full_system_wiring.py` line 21
- **Problem**: `def test(name, fn, skip=False)` is not a valid pytest test — pytest interprets `name` as a fixture
- **Action**: Rewrite as proper pytest parametrized tests or a test class with individual test methods
- **QA**: `python -m pytest tests/integration/test_full_system_wiring.py -v` → no errors

### Task 0.3: Clean dead files
- **Delete**: `src/metrics_store.py.bak`, `src/metrics_store_MUTATED.py`
- **QA**: `ls src/metrics_store.py.bak src/metrics_store_MUTATED.py` → both return "No such file"

**Commit**: `fix: repair broken tests and remove dead files`

---

## Wave 1: Wire Budget Tracker (Enforcement, Not Just Stats)

### Task 1.1: TDD — Write tests for budget tracker integration
- **File**: `tests/intelligence/test_budget_tracker.py` (NEW)
- **Tests**:
  - `test_record_usage_increments_budget` — call `record_usage(session_id, tokens)`, verify `get_status()` shows correct used_budget
  - `test_record_continuation_increments_count` — call `record_continuation(session_id)`, verify continuation_count > 0
  - `test_is_near_limit_at_80_percent` — set budget to 100, record 80 tokens, verify `is_near_limit` is True
  - `test_is_diminishing_returns_at_threshold` — record 3 continuations, verify `is_diminishing_returns` is True
  - `test_get_nudge_message_when_near_limit` — verify nudge message is returned
  - `test_reset_session_clears_usage` — record usage, reset, verify used_budget is 0
  - `test_global_tracker_singleton` — `get_budget_tracker()` returns same instance
- **QA**: `python -m pytest tests/intelligence/test_budget_tracker.py -v` → 7 PASS

### Task 1.2: Wire budget tracker into delegation flow
- **File**: `src/intelligence/delegation_logger.py`
- **Action**: After logging a delegation, call `get_budget_tracker().record_usage(session_id, tokens)`
- **File**: `src/intelligence/complexity_scorer.py` or wherever continuation is detected
- **Action**: Call `get_budget_tracker().record_continuation(session_id)` when a continuation is detected
- **File**: `src/intelligence/__init__.py`
- **Action**: Add `from src.intelligence.budget_tracker import BudgetTracker, BudgetState, get_budget_tracker` and export in `__all__`
- **QA**: Run existing delegation tests — they still pass. Budget tracker now has non-zero usage after delegation.

### Task 1.3: Add budget check to pre-flight
- **File**: `bin/quality-gates/gate-9-budget.sh` (NEW)
- **Action**: Create a shell wrapper that calls `get_budget_tracker().get_status("global")` and exits 1 if `is_near_limit` is True
- **File**: `src/intelligence/budget_gate.py` (NEW)
- **Action**: Python module that checks budget status and returns pass/fail
- **QA**: `bash bin/quality-gates/gate-9-budget.sh` → exits 0 (budget not near limit)

**Commit**: `feat: wire budget tracker into delegation flow with enforcement`

---

## Wave 2: Wire Permission Engine (Enforcement, Not Just Stats)

### Task 2.1: TDD — Write tests for permission engine
- **File**: `tests/intelligence/test_permission_engine.py` (NEW)
- **Tests**:
  - `test_default_mode_asks` — `check_permission("default", "read_file")` returns `("ask", ...)`
  - `test_allow_rule_matches` — add allow rule for `read.*`, check `read_file` → `("allow", ...)`
  - `test_deny_rule_blocks` — add deny rule for `write.*`, check `write_file` → `("deny", ...)`
  - `test_deny_takes_priority_over_allow` — add both rules, deny wins
  - `test_bypass_mode_allows_all` — set mode to "bypass", any tool → `("allow", ...)`
  - `test_downhill_mode_allows_readonly` — set mode to "downhill", read tool → allow
  - `test_uphill_mode_asks` — set mode to "uphill", any tool → ask
  - `test_add_rule_routes_to_correct_list` — add allow rule, verify it's in `always_allow_rules`
  - `test_get_stats_returns_counts` — add rules, verify stats match
  - `test_global_engine_singleton` — `get_permission_engine()` returns same instance
- **QA**: `python -m pytest tests/intelligence/test_permission_engine.py -v` → 10 PASS

### Task 2.2: Wire permission engine into tool execution
- **File**: `src/intelligence/__init__.py`
- **Action**: Add `from src.intelligence.permission_engine import PermissionEngine, PermissionRule, ToolPermissionContext, get_permission_engine` and export in `__all__`
- **File**: `src/intelligence/tool_executor.py` (NEW) or integrate into existing delegation flow
- **Action**: Before executing any tool, call `get_permission_engine().check_permission(session_id, tool_name, content)`. If result is "deny", raise `PermissionError`. If "ask", log warning.
- **File**: `bin/quality-gates/gate-10-permissions.sh` (NEW)
- **Action**: Shell wrapper that checks permission for a given tool+content pair
- **QA**: Existing tests still pass. Permission engine returns non-empty stats after tool execution.

### Task 2.3: Resolve duplicate with athena permissions
- **File**: `athena/src/athena/core/permissions.py` vs `src/intelligence/permission_engine.py`
- **Action**: Decide which one is canonical. If athena's is the real one, delete `src/intelligence/permission_engine.py` and re-export from athena. If the intelligence one is preferred, delete the athena one. Document the decision.
- **QA**: Only one PermissionEngine exists in the codebase. All imports point to the canonical one.

**Commit**: `feat: wire permission engine into tool execution with enforcement`

---

## Wave 3: Wire Tool Contract (Or Kill It)

### Task 3.1: TDD — Write tests for tool contract
- **File**: `tests/intelligence/test_tool_contract.py` (NEW)
- **Tests**:
  - `test_tooldef_defaults` — `ToolDef(name="test")` has correct defaults
  - `test_tooldef_validate_with_custom_fn` — set `validate_input`, call `validate()`, verify result
  - `test_tooldef_validate_without_fn` — no `validate_input`, returns `(True, "No validation defined")`
  - `test_tooldef_check_perms_with_custom_fn` — set `check_permissions`, call `check_perms()`, verify result
  - `test_tooldef_to_dict_excludes_callbacks` — `to_dict()` doesn't include `validate_input` or `check_permissions`
  - `test_registry_register_and_get` — register tool, get by name, verify match
  - `test_registry_get_read_only_tools` — register mix of read-only and destructive, filter correctly
  - `test_registry_get_destructive_tools` — register mix, filter correctly
  - `test_global_registry_singleton` — `get_tool_registry()` returns same instance
  - `test_register_tool_convenience_fn` — `register_tool(ToolDef(...))` adds to global registry
- **QA**: `python -m pytest tests/intelligence/test_tool_contract.py -v` → 10 PASS

### Task 3.2: Resolve duplicate with agent-framework ToolRegistry
- **File**: `src/intelligence/tool_contract.py` vs `src/agent-framework/src/tool_registry.py`
- **Action**: The agent-framework one is already wired into the router. The intelligence one is dead. **RECOMMENDATION**: Delete `src/intelligence/tool_contract.py` entirely. The agent-framework ToolRegistry already does everything this does, plus execution. If the intelligence module needs tool contracts, import from agent-framework.
- **Alternative**: If keeping it, wire it into the delegation flow — register all MCP tools at startup, validate inputs before delegation.
- **QA**: Only one ToolRegistry exists. All imports point to it.

### Task 3.3: If keeping — wire into delegation
- **File**: `src/intelligence/__init__.py`
- **Action**: Export `ToolDef`, `ToolRegistry`, `get_tool_registry`, `register_tool`
- **File**: Delegation pre-flight — before delegating, look up tool in registry, validate input
- **QA**: Delegation flow validates tool inputs against contracts.

**Commit**: `feat: wire tool contract into delegation OR refactor: remove duplicate tool_contract.py`

---

## Wave 4: Wire Task ID System (Or Kill It)

### Task 4.1: TDD — Write tests for task ID functions
- **File**: `tests/state/test_models.py` (NEW, or extend existing)
- **Tests**:
  - `test_generate_task_id_has_correct_prefix` — `generate_task_id("bash")` starts with "b_"
  - `test_generate_task_id_unknown_type` — `generate_task_id("unknown")` starts with "x_"
  - `test_generate_task_id_unique` — two calls return different IDs
  - `test_is_terminal_task_status` — verify each status in TERMINAL_STATUSES returns True
  - `test_is_terminal_task_status_non_terminal` — "pending", "running" return False
  - `test_validate_task_status_transition_from_terminal` — from "completed" to anything → False
  - `test_validate_task_status_transition_valid` — from "pending" to "running" → True
  - `test_validate_task_status_transition_invalid_status` — to "nonexistent" → False
- **QA**: `python -m pytest tests/state/test_models.py -v` → 8 PASS

### Task 4.2: Export from `src/state/__init__.py`
- **File**: `src/state/__init__.py`
- **Action**: Add `generate_task_id`, `is_terminal_task_status`, `validate_task_status_transition`, `TASK_ID_PREFIXES`, `TASK_STATUSES`, `TERMINAL_STATUSES` to imports and `__all__`
- **QA**: `from src.state import generate_task_id` works

### Task 4.3: Wire into delegation flow
- **File**: `src/intelligence/delegation_logger.py`
- **Action**: Use `generate_task_id()` instead of whatever ID scheme is currently used
- **File**: Wherever task status transitions happen
- **Action**: Use `validate_task_status_transition()` before changing status
- **QA**: Delegation logs show prefixed task IDs (b_, a_, w_, d_, m_). Invalid status transitions are rejected.

**Commit**: `feat: wire task ID system into delegation flow`

---

## Wave 5: Upgrade Security Gate (Beyond Keywords)

### Task 5.1: TDD — Write tests for path-aware security
- **File**: `tests/intelligence/test_security_gate.py` (extend existing)
- **Tests**:
  - `test_file_path_auth_blocked` — task mentions `src/auth/login.py` → BLOCK
  - `test_file_path_crypto_blocked` — task mentions `src/crypto/` → BLOCK
  - `test_file_path_payments_blocked` — task mentions `src/payments/` → BLOCK
  - `test_file_path_env_blocked` — task mentions `.env` → BLOCK
  - `test_file_path_secret_blocked` — task mentions `secret_manager.py` → BLOCK
  - `test_safe_file_path_passes` — task mentions `src/ui/button.py` → PASS
  - `test_bash_command_injection_blocked` — task contains `; rm -rf /` → BLOCK
  - `test_eval_blocked` — task contains `eval(user_input)` → BLOCK
  - `test_exec_blocked` — task contains `exec(code)` → BLOCK
  - `test_false_positive_button_passes` — task "add auth button to dashboard" → PASS (not modifying auth code)
- **QA**: `python -m pytest tests/intelligence/test_security_gate.py -v` → all PASS

### Task 5.2: Add file path detection to security gate
- **File**: `src/intelligence/security_gate.py`
- **Action**: Add `SECURITY_PATHS` list (`auth/`, `security/`, `crypto/`, `payments/`, `env/`, `.env`, `secret`, `credential`, `token`, `password`, `api_key`, `private_key`). Check if task description mentions any of these paths.
- **Action**: Add regex patterns for file paths: `r'(?:src/)?(?:auth|security|crypto|payments|env)/'`
- **QA**: Security gate blocks tasks that mention security-sensitive paths, not just keywords.

**Commit**: `feat: upgrade security gate to detect file paths, not just keywords`

---

## Wave 6: Integration Test — Full Wiring Verification

### Task 6.1: Write end-to-end wiring test
- **File**: `tests/integration/test_tightening_wiring.py` (NEW)
- **Tests**:
  - `test_delegation_records_budget` — delegate a task, verify budget tracker shows usage
  - `test_delegation_uses_task_id_prefix` — delegate a bash task, verify task ID starts with "b_"
  - `test_delegation_checks_permissions` — delegate with permission engine, verify check was called
  - `test_security_gate_blocks_auth_task` — delegate "implement auth middleware", gate-8 blocks
  - `test_security_gate_passes_safe_task` — delegate "add button to dashboard", gate-8 passes
  - `test_all_gates_run_in_sequence` — run all quality gates on a safe task, all pass
  - `test_budget_nudge_message_when_near_limit` — exhaust budget, verify nudge message
  - `test_permission_deny_blocks_tool` — set deny rule, try to execute tool, raises PermissionError
- **QA**: `python -m pytest tests/integration/test_tightening_wiring.py -v` → 8 PASS

### Task 6.2: Update `__init__.py` exports
- **File**: `src/intelligence/__init__.py`
- **Action**: Add all new exports: `BudgetTracker`, `BudgetState`, `get_budget_tracker`, `PermissionEngine`, `PermissionRule`, `ToolPermissionContext`, `get_permission_engine`
- **File**: `src/state/__init__.py`
- **Action**: Add task ID exports

**Commit**: `test: add integration tests for full tightening wiring`

---

## Commit Strategy

```
1. fix: repair broken tests and remove dead files
   - Fix test_cache_hit_exact_match assertion
   - Fix test_full_system_wiring.py pytest fixture error
   - Delete src/metrics_store.py.bak, src/metrics_store_MUTATED.py

2. test: add unit tests for budget tracker
   - 7 tests covering all BudgetState and BudgetTracker functionality

3. feat: wire budget tracker into delegation flow
   - delegation_logger.py calls record_usage after logging
   - Export from __init__.py
   - Add gate-9-budget.sh

4. test: add unit tests for permission engine
   - 10 tests covering all permission scenarios

5. feat: wire permission engine into tool execution
   - Check permissions before tool execution
   - Add gate-10-permissions.sh
   - Resolve duplicate with athena permissions

6. test: add unit tests for tool contract
   - 10 tests covering ToolDef and ToolRegistry

7. refactor: resolve duplicate ToolRegistry (delete or wire)
   - Either delete tool_contract.py or wire it into delegation

8. test: add unit tests for task ID system
   - 8 tests covering generate_task_id, is_terminal, validate_transition

9. feat: wire task ID system into delegation flow
   - Export from state/__init__.py
   - Use generate_task_id in delegation_logger
   - Use validate_task_status_transition for status changes

10. feat: upgrade security gate to detect file paths
    - Add SECURITY_PATHS list
    - Add file path regex patterns
    - Extend tests

11. test: add integration tests for full tightening wiring
    - 8 end-to-end tests verifying all modules work together

12. chore: update __init__.py exports for all new modules
    - intelligence/__init__.py: budget, permission, tool contract exports
    - state/__init__.py: task ID exports
```

---

## Execution Notes

- **Order matters**: Wave 0 first (fix broken tests), then Waves 1-5 in any order, Wave 6 last
- **TDD discipline**: Tests written BEFORE implementation in each wave
- **Kill vs Wire decision**: For tool_contract.py, decide in Wave 3 whether to wire or delete. Don't half-wire.
- **Duplicate resolution**: For PermissionEngine and ToolRegistry, pick ONE canonical implementation. Delete the other.
- **No new modules**: This plan wires existing modules. Zero new files except tests and gate wrappers.
- **Gate proof**: Each wave ends with `python -m pytest` output showing all tests pass
