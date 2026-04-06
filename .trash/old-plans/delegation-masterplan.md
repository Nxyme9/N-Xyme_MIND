# Master Delegation Plan: Portable OMO Platform

## Strategy: Parallel Execution with Correct Agent Matching

### Agent Pool

| Agent | Subagent | Best For | Model | Parallel? |
|-------|----------|----------|-------|-----------|
| **Hephaestus** | - | Implementation (writes code) | mimo-v2-pro (medium) | No |
| **Explore** | - | Codebase search | minimax-m2.5-free | Yes |
| **Librarian** | - | External research | minimax-m2.5-free | Yes |
| **Oracle** | - | Architecture review | minimax-m2.5-free | No |
| **Momus** | - | Adversarial red-team | mimo-v2-pro (high) | No |
| **Metis** | - | Gap analysis | mimo-v2-pro (high) | No |
| **Sisyphus-Junior** | - | Simple tasks | minimax-m2.5-free | No |
| **Atlas** | - | Plan executor | minimax-m2.5-free | No |

---

## Task-to-Agent Mapping

### Wave 1: Audit & Remediate

| Task | Agent | Category | Why | Dependency |
|------|-------|----------|-----|------------|
| T1: Audit hardcoded paths | **Explore** | explore | Finds all occurrences across codebase | None |
| T2: Fix Python source | **Hephaestus** | deep | Modifies multiple Python files | T1 results |
| T3: Fix opencode.json | **Sisyphus-Junior** | quick | Single JSON file edit | T1 results |
| T4: Fix bootstrap.sh | **Sisyphus-Junior** | quick | Single shell file edit | T2, T3 |

**Execution Order:**
```
T1 (Explore) ──┬──► T2 (Hephaestus) ──► T3 (Sisyphus-Junior)
               │                          │
               └──► T4 (Sisyphus-Junior) ◄┘
```

---

### Wave 2: Verification

| Task | Agent | Category | Why | Dependency |
|------|-------|----------|-----|------------|
| T5: Test venv creation | **Atlas** | unspecified-high | Executes bootstrap, verifies paths | T4 |
| T6: Test MCP tool calls | **Sisyphus-Junior** | quick | Runs JSON-RPC commands | T5 |
| T7: Path leak scan | **Explore** | explore | Grep for hardcoded paths | T2 (must be done) |
| T8: Fresh clone simulation | **Atlas** | unspecified-high | rsync + bootstrap + verify | T5, T6, T7 |

**Execution Order (Parallel where possible):**
```
T5 (Atlas) ──────► T8 (Atlas)
T6 (Sisyphus-Junior) ──► T8 (Atlas)
T7 (Explore) ────────────► T8 (Atlas)
                          ↓
                      T8 waits for ALL
```

---

### Wave 3: Agents & Config

| Task | Agent | Category | Why | Dependency |
|------|-------|----------|-----|------------|
| T9: Copy agent definitions | **Sisyphus-Junior** | quick | Read global, write project | None |
| T10: Verify config precedence | **Atlas** | unspecified-high | Test without global | T9 |
| T11: Document verification | **Sisyphus-Junior** | writing | Write VERIFICATION.md | T5-T10 |

**Execution Order:**
```
T9 (Sisyphus-Junior) ──► T10 (Atlas) ──► T11 (Sisyphus-Junior)
```

---

### Final Verification

| Task | Agent | Category | Why | Dependency |
|------|-------|----------|-----|------------|
| F1: Oracle review | **Oracle** | oracle | Architecture approval | All T1-T11 |
| F2: Momus red-team | **Momus** | momus | Adversarial challenge | F1 |

---

## Optimal Delegation Strategy

### Phase 1: T1 (Audit) — PARALLEL EXPLORE

```
┌─────────────────────────────────────────────────────────┐
│ PROMPT: "Audit ALL /home/nxyme hardcoded paths"        │
│ Agent: Explore (run_in_background=true)                  │
│ Output: List of files + line numbers                   │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ Metis (review)  │ ← Reviews T1 results
                   │ Gap analysis     │   Identifies missed paths
                   └─────────────────┘
```

### Phase 2: T2-T4 (Fix) — SEQUENTIAL HEPHAESTUS

```
┌─────────────────────────────────────────────────────────┐
│ PROMPT: "Fix T2: Python source files"                  │
│   - Files from T1 results                             │
│   - Replace Path('/home/nxyme/...') with env vars    │
│   - Use: Path(__file__).parent.parent               │
│ Agent: Hephaestus (run_in_background=false)         │
│ Output: All Python files fixed                       │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ PROMPT: "Fix T3: opencode.json paths"                │
│   - Verify all venv paths match bootstrap output      │
│ Agent: Sisyphus-Junior (run_in_background=false)    │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ PROMPT: "Fix T4: bootstrap.sh"                       │
│   - Create venvs at EXACT paths:                     │
│     ./venvs/athena/                                  │
│     ./packages/athena-context-mcp/venv/              │
│     ./packages/trigger-guardian-mcp/.venv/           │
│     ./packages/nx-mind-mcp/venv/                     │
│   - Add verification step                            │
│ Agent: Sisyphus-Junior (run_in_background=false)    │
└─────────────────────────────────────────────────────────┘
```

### Phase 3: T5-T8 (Verify) — PARALLEL ATLAS + EXPLORE

```
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│ T5: Atlas        │  │ T6: Sisyphus-Jr  │  │ T7: Explore     │
│ Test venvs       │  │ Test MCP calls    │  │ Path leak scan   │
│ bootstrap.sh     │  │ JSON-RPC tools   │  │ grep /home/nxyme│
│ test -f paths    │  │ list + call      │  │ Verify 0 matches│
└────────┬──────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                        │                       │
         └────────────────────────┼───────────────────────┘
                                  ▼
                    ┌─────────────────────────────┐
                    │ T8: Atlas                  │
                    │ Fresh clone simulation     │
                    │ rsync + bootstrap + verify│
                    │ WAITS for T5, T6, T7      │
                    └─────────────────────────────┘
```

### Phase 4: T9-T11 (Agents) — SEQUENTIAL

```
┌─────────────────────────────────────────────────────────┐
│ T9: Sisyphus-Junior                                    │
│ Read: ~/.config/opencode/oh-my-opencode.json           │
│ Write: ./oh-my-opencode.json (copy all agents)       │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ T10: Atlas                                            │
│ Test: mv global config, run opencode, verify works    │
│ Restore: mv global config back                         │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ T11: Sisyphus-Junior                                  │
│ Write: VERIFICATION.md                                 │
│ Include: path scan, venv test, MCP test, clone test   │
└─────────────────────────────────────────────────────────┘
```

### Phase 5: Final — ORACLE + MOMUS

```
┌─────────────────────────────────────────────────────────┐
│ F1: Oracle                                            │
│ Verify architecture:                                    │
│ - All paths relative?                                  │
│ - Bootstrap creates correct venvs?                    │
│ - Zero hardcoded paths remain?                        │
│ - Works without global config?                         │
│ Output: APPROVE / REJECT + issues                    │
└─────────────────────────────────────────────────────────┘
                            │ (only if F1 APPROVE)
                            ▼
┌─────────────────────────────────────────────────────────┐
│ F2: Momus                                             │
│ Red-team challenge:                                    │
│ - "Find 1 more hardcoded path"                        │
│ - "Break bootstrap in 1 step"                         │
│ - "Make MCP start but fail on tool"                   │
│ Output: CHALLENGES REMAINING: N | VERDICT            │
└─────────────────────────────────────────────────────────┘
```

---

## Agent Usage Summary

| Agent | Tasks | Total Time | Model |
|-------|-------|------------|-------|
| **Explore** | T1, T7 | ~10 min | minimax-m2.5-free |
| **Hephaestus** | T2 | ~20 min | mimo-v2-pro (medium) |
| **Sisyphus-Junior** | T3, T4, T6, T9, T11 | ~30 min | minimax-m2.5-free |
| **Atlas** | T5, T8, T10 | ~40 min | minimax-m2.5-free |
| **Metis** | Review T1 | ~10 min | mimo-v2-pro (high) |
| **Oracle** | F1 | ~15 min | minimax-m2.5-free |
| **Momus** | F2 | ~15 min | mimo-v2-pro (high) |
| **TOTAL** | 13 tasks | ~2.5 hours | - |

---

## Parallel Execution Matrix

```
Time ──────────────────────────────────────────────────►

T1: Explore ████████
T2: Hephaestus        ████████████████████████████
T3: Sisyphus-Jr                    ██████████████
T4: Sisyphus-Jr                                ██████████████
T5: Atlas                                      ████████████████
T6: Sisyphus-Jr                                 ████
T7: Explore                                    ████████
T8: Atlas                                              ████████████████████████████
T9: Sisyphus-Jr        ████████████
T10: Atlas                    ████████████████
T11: Sisyphus-Jr                                ████████████████████████████
F1: Oracle                                                    ████████████
F2: Momus                                                          ████████████
```

---

## Critical Path

```
T1 → T2 → T3 → T4 → T5 → T8 → T10 → T11 → F1 → F2
         ↑                      ↑
         └──────────────────────┘
              (T5 also needs T4)
```

**Critical path time: ~2 hours**

---

## Failover Strategy

| Agent Fails | Fallback | Action |
|-------------|----------|--------|
| Explore | Sisyphus-Junior | Manual grep, slower |
| Hephaestus | Atlas | More expensive, slower |
| Sisyphus-Junior | Hephaestus | Double-check work |
| Atlas | Hephaestus | Sequential instead of parallel |

---

## Quality Gates

| Gate | Agent | Check | Fail Action |
|------|-------|-------|-------------|
| G1 | Metis | T1 audit completeness | Re-run audit |
| G2 | Oracle | T2-T4 fix correctness | Re-fix files |
| G3 | Oracle | T5-T8 verification | Re-bootstrap |
| G4 | Momus | T9-T11 agent config | Re-copy config |

---

## Prompt Templates

### T1: Explore (Audit Paths)
```
Search ALL Python files for hardcoded "/home/nxyme" paths.

Command: grep -rn "/home/nxyme" --include="*.py" .

Output format:
- File:line:match
- Categorize: config | source | test | data

Return complete list with exact file paths and line numbers.
```

### T2: Hephaestus (Fix Python Files)
```
Fix ALL files from audit results.

For each file:
1. Replace Path("/home/nxyme/...") with Path(os.environ.get("PROJECT_ROOT", Path(__file__).parent.parent.parent))
2. Or use: Path(__file__).resolve().parent.parent.parent
3. Remove any hardcoded fallback to /home/nxyme

Pattern to replace:
  Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
  ↓
  Path(os.environ.get("ATHENA_CONTEXT_ROOT", Path(__file__).parent.parent))

Verify each fix compiles: python -m py_compile file.py
```

### T3: Sisyphus-Junior (Fix JSON)
```
Update /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/opencode.json:

1. Check filesystem MCP: /home/nxyme → ./ (or make configurable)
2. Verify all venv paths:
   - ./venvs/athena/bin/python
   - ./packages/athena-context-mcp/venv/bin/python
   - ./packages/trigger-guardian-mcp/.venv/bin/python
   - ./packages/nx-mind-mcp/venv/bin/python

Validate: python3 -m json.tool opencode.json > /dev/null
```

### T5: Atlas (Test Bootstrap)
```
Execute in /tmp (fresh environment):

1. Create test directory
2. Run: bash bootstrap.sh
3. Verify each venv exists:
   - test -f ./venvs/athena/bin/python
   - test -f ./packages/athena-context-mcp/venv/bin/python
   - test -f ./packages/trigger-guardian-mcp/.venv/bin/python
   - test -f ./packages/nx-mind-mcp/venv/bin/python
4. Verify each Python works:
   - ./venvs/athena/bin/python -c "import athena"
   - ./packages/*/venv/bin/python -c "import module"

Exit 0 only if ALL pass.
```

### T6: Sisyphus-Junior (Test MCP Calls)
```
Test MCP responds to JSON-RPC, not just starts.

For each MCP:
1. Start: timeout 5 MCP_COMMAND
2. Send: echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | MCP_COMMAND
3. Parse: Should return {"id":1,"result":{"tools":[...]}}
4. Fail if: "running on stdio" but no tools response

Example:
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | \
  ./packages/athena-context-mcp/venv/bin/python -m athena_context_mcp | \
  grep -q '"result"'
```

---

## Monitoring & Progress

| Checkpoint | Time | Gate |
|------------|------|------|
| T1 Complete | 10 min | Metis review |
| T2-T4 Complete | 30 min | Self-validate |
| T5-T7 Complete | 20 min | Oracle review |
| T8 Complete | 20 min | Self-validate |
| T9-T11 Complete | 30 min | Oracle review |
| F1-F2 Complete | 30 min | User sign-off |

---

## Success Criteria (Delegation)

- [ ] T1 uses Explore (not Hephaestus doing search)
- [ ] T2 uses Hephaestus (not Sisyphus-Junior doing code)
- [ ] T5-T8 uses Atlas (heavy execution)
- [ ] Parallel tasks run simultaneously (T5, T6, T7)
- [ ] Sequential dependencies respected (T2 after T1, T8 after T5-T7)
- [ ] Fallback agents ready if primary fails
