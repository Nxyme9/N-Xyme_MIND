# Layer 10: Planning & Reasoning — Implementation Plan

## Context

**User Request**: Create a dense, robust implementation plan for Layer 10: Planning & Reasoning of N-Xyme MIND v1.0.

**Project Context**: 
- Location: /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/
- Master plan: .sisyphus/plans/N-XYME-V1.0-MASTERPLAN.md (Wave 4: Weeks 7-8)
- Python-only, MIT-licensed sources
- Existing: trigger_engine.py with ACTION_REGISTRY pattern

**Research Context**:
- Layer 10 currently has 3 planned files: htn_planner.py, temporal_planner.py, goal_reasoning.py
- Critical gaps: No plan validation, no plan repair, no multi-agent planning, no PDDL/STRIPS integration, no plan execution monitoring
- Repos: GTPyhop (HTN), temporal-planning (temporal), SELFGOAL (self-goal), orra (dynamic planning), exoclaw-temporal (durable execution)

## Task Dependency Graph

| Task | Depends On | Reason |
|------|------------|--------|
| Task 1: Design planning data structures | None | Foundation for all planning components |
| Task 2: Implement htn_planner.py | Task 1 | Requires core data structures |
| Task 3: Implement plan validation module | Task 2 | Validates HTN plans |
| Task 4: Implement plan repair module | Task 3 | Repairs validated plans |
| Task 5: Implement temporal_planner.py | Task 1, Task 3 | Durable execution with validation |
| Task 6: Implement goal_reasoning.py | Task 2, Task 5 | SELFGOAL patterns with HTN + temporal |
| Task 7: Implement plan execution monitor | Task 5 | Monitors plan progress |
| Task 8: Implement multi-agent coordination | Task 6 | Coordinates across agents |
| Task 9: Integration tests | All tasks | Verify end-to-end functionality |

## Parallel Execution Graph

**Wave 1 (Start immediately)**:
- Task 1: Design planning data structures (no dependencies)
- Task 2: Implement htn_planner.py (depends: Task 1)
- Task 5: Implement temporal_planner.py (depends: Task 1)

**Wave 2 (After Wave 1 completes)**:
- Task 3: Implement plan validation module (depends: Task 2)
- Task 6: Implement goal_reasoning.py (depends: Task 2, Task 5)

**Wave 3 (After Wave 2 completes)**:
- Task 4: Implement plan repair module (depends: Task 3)
- Task 7: Implement plan execution monitor (depends: Task 5)

**Wave 4 (After Wave 3 completes)**:
- Task 8: Implement multi-agent coordination (depends: Task 6, Task 7)
- Task 9: Integration tests (depends: All tasks)

**Critical Path**: Task 1 → Task 2 → Task 3 → Task 4 (plus Task 5, Task 6, Task 8)
**Estimated Parallel Speedup**: 35% faster than sequential due to independent data structure design

---

## Tasks

### Task 1: Design Planning Data Structures

**Description**: Create core data structures that will be used across all planning modules. This includes task definitions, plan representations, goal structures, and execution states.

**Delegation Recommendation**:
- Category: `deep` - Complex architectural design requiring careful type design
- Skills: [] - No external skills needed for data structure design

**Skills Evaluation**:
- OMITTED dev-browser: Not needed for data structure design
- OMITTED frontend-ui-ux: Not needed for data structure design

**Depends On**: None

**Acceptance Criteria**:
- [ ] Define Task, Method, Operator classes with proper type hints
- [ ] Define Plan, PlanStep, ExecutionState data classes
- [ ] Define Goal, GoalDecomposition structures
- [ ] Define ValidationResult, RepairResult types
- [ ] All structures importable without errors
- [ ] Unit tests pass for basic operations

### Task 2: Implement htn_planner.py

**Description**: Implement Hierarchical Task Network (HTN) planner based on GTPyhop patterns. This includes task decomposition, method selection, operator execution, and plan generation.

**Delegation Recommendation**:
- Category: `deep` - Complex algorithmic implementation with multiple components
- Skills: [] - Implementation skill covers Python coding

**Skills Evaluation**:
- OMITTED git-master: Not needed for new implementation
- OMITTED playwright: Not needed for backend logic

**Depends On**: Task 1

**Acceptance Criteria**:
- [ ] HTNPlanner class with decompose() method
- [ ] Task hierarchy support (compound tasks, primitive tasks)
- [ ] Method selection via task_task matching
- [ ] Operator execution with preconditions/postconditions
- [ ] Plan generation with ordering constraints
- [ ] Unit tests for task decomposition
- [ ] Integration with trigger_engine ACTION_REGISTRY pattern

### Task 3: Implement Plan Validation Module

**Description**: Create plan validation system to verify plan feasibility before execution. Includes precondition checking, resource estimation, conflict detection.

**Delegation Recommendation**:
- Category: `deep` - Complex logic requiring algorithmic design
- Skills: [] - Standard implementation

**Skills Evaluation**:
- OMITTED all skills: Basic implementation task

**Depends On**: Task 2

**Acceptance Criteria**:
- [ ] PlanValidator class with validate() method
- [ ] Precondition satisfaction checking
- [ ] Resource requirement estimation
- [ ] Temporal constraint validation (durational, ordering)
- [ ] Conflict detection (resource conflicts, ordering conflicts)
- [ ] ValidationResult with detailed failure reasons
- [ ] Unit tests for all validation scenarios

### Task 4: Implement Plan Repair Module

**Description**: Implement dynamic plan repair for failed plans. Includes replanning, plan modification, goal reordering, and recovery strategies.

**Delegation Recommendation**:
- Category: `deep` - Complex recovery algorithm design
- Skills: [] - Standard implementation

**Skills Evaluation**:
- OMITTED all skills: Algorithm implementation

**Depends On**: Task 3

**Acceptance Criteria**:
- [ ] PlanRepair class with repair() method
- [ ] Failure diagnosis (identify failure point and reason)
- [ ] Local repair (modify failed step)
- [ ] Replanning (generate new sub-plan)
- [ ] Goal reordering (prioritize achievable goals)
- [ ] RepairResult with repair strategy used
- [ ] Unit tests for repair scenarios

### Task 5: Implement temporal_planner.py

**Description**: Implement temporal planner for durable execution with time constraints, scheduling, and temporal reasoning. Based on temporal-planning algorithms.

**Delegation Recommendation**:
- Category: `deep` - Complex algorithmic implementation
- Skills: [] - Standard implementation

**Skills Evaluation**:
- OMITTED all skills: Algorithm implementation

**Depends On**: Task 1, Task 3

**Acceptance Criteria**:
- [ ] TemporalPlanner class with schedule() method
- [ ] Time point and interval representations
- [ ] Temporal constraint solving (start, end, duration, precedence)
- [ ] Schedule optimization (minimize makespan, resource usage)
- [ ] Execution with temporal monitoring
- [ ] Integration with plan validation
- [ ] Unit tests for temporal reasoning

### Task 6: Implement goal_reasoning.py

**Description**: Implement SELFGOAL patterns for self-goal achievement. Includes goal reasoning, goal decomposition, goal refinement, and self-reflection.

**Delegation Recommendation**:
- Category: `deep` - Complex reasoning system design
- Skills: [] - Standard implementation

**Skills Evaluation**:
- OMITTED all skills: Reasoning system implementation

**Depends On**: Task 2, Task 5

**Acceptance Criteria**:
- [ ] GoalReasoner class with reason_about_goal() method
- [ ] Goal state representation
- [ ] Goal decomposition (break into sub-goals)
- [ ] Goal refinement (improve goal formulation)
- [ ] Self-reflection on goal achievement
- [ ] Integration with HTN and temporal planners
- [ ] Unit tests for goal reasoning

### Task 7: Implement Plan Execution Monitor

**Description**: Create execution monitoring system to track plan progress, detect execution anomalies, and provide real-time feedback.

**Delegation Recommendation**:
- Category: `deep` - Complex monitoring system
- Skills: [] - Standard implementation

**Skills Evaluation**:
- OMITTED all skills: Monitoring implementation

**Depends On**: Task 5

**Acceptance Criteria**:
- [ ] ExecutionMonitor class with track() method
- [ ] Plan step tracking (current step, completed, pending)
- [ ] Progress estimation (time remaining, completion percentage)
- [ ] Anomaly detection (stuck, regressing, timing violations)
- [ ] Execution events (start, complete, fail, skip)
- [ ] Integration with trigger_engine for alerts
- [ ] Unit tests for monitoring

### Task 8: Implement Multi-Agent Coordination

**Description**: Implement multi-agent planning coordination for distributed planning across agents. Includes task delegation, plan merging, conflict resolution.

**Delegation Recommendation**:
- Category: `deep` - Complex distributed system
- Skills: [] - Standard implementation

**Skills Evaluation**:
- OMITTED all skills: Coordination implementation

**Depends On**: Task 6, Task 7

**Acceptance Criteria**:
- [ ] MultiAgentCoordinator class with coordinate() method
- [ ] Agent capability registry
- [ ] Task delegation (assign sub-goals to agents)
- [ ] Plan merging (combine agent sub-plans)
- [ ] Coordination conflict detection
- [ ] Synchronization primitives
- [ ] Unit tests for coordination

### Task 9: Integration Tests

**Description**: Create comprehensive integration tests across all planning components. Verify end-to-end planning, execution, and monitoring.

**Delegation Recommendation**:
- Category: `unspecified-low` - Test implementation
- Skills: [] - Test implementation

**Skills Evaluation**:
- OMITTED all skills: Test implementation

**Depends On**: All tasks

**Acceptance Criteria**:
- [ ] End-to-end planning test (goal → decomposed → validated → executed)
- [ ] Plan repair test (simulate failure, verify repair)
- [ ] Temporal execution test (schedule and execute with timing)
- [ ] Multi-agent coordination test (2+ agents planning together)
- [ ] Integration with existing layers (trigger_engine, memory)
- [ ] All tests pass

---

## Commit Strategy

### Atomic Commits (per task)

1. **Task 1**: `feat: Add planning data structures`
   - Files: src/planning/types.py (new)
   - Tests: tests/unit/test_planning_types.py (new)
   - Commit message: "feat: Add core planning data structures (Task, Plan, Goal, ValidationResult)"

2. **Task 2**: `feat: Implement HTN planner`
   - Files: src/planning/htn_planner.py (new)
   - Tests: tests/unit/test_htn_planner.py (new)
   - Commit message: "feat: Implement HTN planner with task decomposition and method selection"

3. **Task 3**: `feat: Add plan validation`
   - Files: src/planning/validator.py (new)
   - Tests: tests/unit/test_validator.py (new)
   - Commit message: "feat: Add plan validation with precondition and resource checking"

4. **Task 4**: `feat: Add plan repair`
   - Files: src/planning/repair.py (new)
   - Tests: tests/unit/test_repair.py (new)
   - Commit message: "feat: Add dynamic plan repair with failure diagnosis"

5. **Task 5**: `feat: Implement temporal planner`
   - Files: src/planning/temporal_planner.py (new)
   - Tests: tests/unit/test_temporal_planner.py (new)
   - Commit message: "feat: Implement temporal planner with scheduling and time constraints"

6. **Task 6**: `feat: Implement goal reasoning`
   - Files: src/planning/goal_reasoning.py (new)
   - Tests: tests/unit/test_goal_reasoning.py (new)
   - Commit message: "feat: Implement SELFGOAL patterns for self-goal achievement"

7. **Task 7**: `feat: Add execution monitor`
   - Files: src/planning/monitor.py (new)
   - Tests: tests/unit/test_monitor.py (new)
   - Commit message: "feat: Add plan execution monitor with progress tracking"

8. **Task 8**: `feat: Add multi-agent coordination`
   - Files: src/planning/coordinator.py (new)
   - Tests: tests/unit/test_coordinator.py (new)
   - Commit message: "feat: Add multi-agent planning coordination"

9. **Task 9**: `test: Add integration tests for Layer 10`
   - Files: tests/integration/test_planning.py (new)
   - Commit message: "test: Add integration tests for planning layer"

### Final Commit

- `feat: Integrate Layer 10 with existing system`
  - Update src/planning/__init__.py
  - Update trigger_engine ACTION_REGISTRY
  - Commit message: "feat: Integrate planning layer with trigger engine and memory system"

---

## Success Criteria

### Per-File Success Criteria

1. **types.py** (Task 1):
   - All data classes importable
   - Type hints complete and correct
   - Unit tests pass

2. **htn_planner.py** (Task 2):
   - decompose() returns valid plan
   - Task hierarchy works
   - Method selection works
   - Unit tests pass

3. **validator.py** (Task 3):
   - validate() returns ValidationResult
   - Precondition checking works
   - Resource estimation works
   - Unit tests pass

4. **repair.py** (Task 4):
   - repair() returns RepairResult
   - Failure diagnosis accurate
   - Local repair modifies correctly
   - Unit tests pass

5. **temporal_planner.py** (Task 5):
   - schedule() returns valid temporal plan
   - Constraints satisfied
   - Optimization works
   - Unit tests pass

6. **goal_reasoning.py** (Task 6):
   - reason_about_goal() returns decomposition
   - Goal refinement improves goals
   - Self-reflection works
   - Unit tests pass

7. **monitor.py** (Task 7):
   - track() updates state correctly
   - Progress estimation accurate
   - Anomaly detection works
   - Unit tests pass

8. **coordinator.py** (Task 8):
   - coordinate() merges plans correctly
   - Delegation assigns to correct agents
   - Conflicts detected
   - Unit tests pass

9. **Integration tests** (Task 9):
   - All integration tests pass
   - End-to-end planning works
   - Multi-agent coordination works

### Overall Layer Success Criteria

- All 8 new files created in src/planning/
- 50+ unit tests passing
- 10+ integration tests passing
- Integration with trigger_engine ACTION_REGISTRY
- Integration with memory system
- Documentation complete
- No lint errors
- Type checking passes

---

## TODO List (ADD THESE)

> CALLER: Add these TODOs using TodoWrite/TaskCreate and execute by wave.

### Wave 1 (Start Immediately - No Dependencies)

- [ ] **1. Design Planning Data Structures**
  - What: Create types.py with Task, Method, Operator, Plan, PlanStep, Goal, ValidationResult, RepairResult classes
  - Depends: None
  - Blocks: 2, 5
  - Category: `deep`
  - Skills: []
  - QA: Import test passes, basic type operations work

- [ ] **2a. Implement htn_planner.py**
  - What: Implement HTNPlanner with task decomposition, method selection, operator execution
  - Depends: 1
  - Blocks: 3, 6
  - Category: `deep`
  - Skills: []
  - QA: Unit tests pass for decompose()

- [ ] **2b. Implement temporal_planner.py**
  - What: Implement TemporalPlanner with scheduling, time constraints, execution
  - Depends: 1, 3
  - Blocks: 6, 7
  - Category: `deep`
  - Skills: []
  - QA: Unit tests pass for schedule()

### Wave 2 (After Wave 1 Completes)

- [ ] **3. Implement Plan Validation**
  - What: Create validator.py with precondition, resource, temporal checking
  - Depends: 2a
  - Blocks: 4, 5
  - Category: `deep`
  - Skills: []
  - QA: Unit tests pass for validate()

- [ ] **6. Implement Goal Reasoning**
  - What: Create goal_reasoning.py with SELFGOAL patterns
  - Depends: 2a, 2b
  - Blocks: 8
  - Category: `deep`
  - Skills: []
  - QA: Unit tests pass for reason_about_goal()

### Wave 3 (After Wave 2 Completes)

- [ ] **4. Implement Plan Repair**
  - What: Create repair.py with failure diagnosis, local repair, replanning
  - Depends: 3
  - Blocks: 9
  - Category: `deep`
  - Skills: []
  - QA: Unit tests pass for repair()

- [ ] **7. Implement Execution Monitor**
  - What: Create monitor.py with progress tracking, anomaly detection
  - Depends: 2b
  - Blocks: 8, 9
  - Category: `deep`
  - Skills: []
  - QA: Unit tests pass for track()

### Wave 4 (After Wave 3 Completes)

- [ ] **8. Implement Multi-Agent Coordination**
  - What: Create coordinator.py with task delegation, plan merging, conflict resolution
  - Depends: 6, 7
  - Blocks: 9
  - Category: `deep`
  - Skills: []
  - QA: Unit tests pass for coordinate()

- [ ] **9. Integration Tests**
  - What: Create tests/integration/test_planning.py with end-to-end tests
  - Depends: All
  - Blocks: None
  - Category: `unspecified-low`
  - Skills: []
  - QA: All integration tests pass

## Execution Instructions

1. **Wave 1**: Fire these tasks IN PARALLEL
   ```
   task(category="deep", load_skills=[], run_in_background=false, prompt="Task 1: Design Planning Data Structures - Create types.py with Task, Method, Operator, Plan, PlanStep, ExecutionState, Goal, GoalDecomposition, ValidationResult, RepairResult data classes. Use @dataclass decorators. Include proper type hints. Put in src/planning/types.py. Write tests in tests/unit/test_planning_types.py.")
   task(category="deep", load_skills=[], run_in_background=false, prompt="Task 2a: Implement HTN Planner - Create src/planning/htn_planner.py with HTNPlanner class. Methods: __init__, decompose(task, state), _select_method(task), _apply_operator(operator, state). Support task hierarchy with compound and primitive tasks. Use types from types.py. Write unit tests in tests/unit/test_htn_planner.py.")
   task(category="deep", load_skills=[], run_in_background=false, prompt="Task 2b: Implement Temporal Planner - Create src/planning/temporal_planner.py with TemporalPlanner class. Methods: __init__, schedule(plan), _solve_constraints(), _optimize_schedule(). Support time points, intervals, precedence constraints. Use temporal-planning algorithms. Write unit tests in tests/unit/test_temporal_planner.py.")
   ```

2. **Wave 2**: After Wave 1 completes, fire next wave IN PARALLEL
   ```
   task(category="deep", load_skills=[], run_in_background=false, prompt="Task 3: Implement Plan Validation - Create src/planning/validator.py with PlanValidator class. Methods: __init__, validate(plan, state), _check_preconditions(), _estimate_resources(), _check_temporal(). Return ValidationResult with is_valid, failures[], warnings[]. Use types from types.py. Write unit tests in tests/unit/test_validator.py.")
   task(category="deep", load_skills=[], run_in_background=false, prompt="Task 6: Implement Goal Reasoning - Create src/planning/goal_reasoning.py with GoalReasoner class. Methods: __init__, reason_about_goal(goal, state), decompose_goal(), refine_goal(), reflect(). Implement SELFGOAL patterns. Use HTN and temporal planners. Write unit tests in tests/unit/test_goal_reasoning.py.")
   ```

3. **Wave 3**: After Wave 2 completes, fire next wave IN PARALLEL
   ```
   task(category="deep", load_skills=[], run_in_background=false, prompt="Task 4: Implement Plan Repair - Create src/planning/repair.py with PlanRepair class. Methods: __init__, repair(plan, failure), diagnose_failure(), local_repair(), replan(), reorder_goals(). Return RepairResult with strategy, modified_plan. Write unit tests in tests/unit/test_repair.py.")
   task(category="deep", load_skills=[], run_in_background=false, prompt="Task 7: Implement Execution Monitor - Create src/planning/monitor.py with ExecutionMonitor class. Methods: __init__, track(plan, state), get_progress(), detect_anomalies(). Track current_step, completed_steps, pending_steps. Detect stuck, regressing, timing violations. Write unit tests in tests/unit/test_monitor.py.")
   ```

4. **Wave 4**: After Wave 3 completes, fire remaining tasks
   ```
   task(category="deep", load_skills=[], run_in_background=false, prompt="Task 8: Implement Multi-Agent Coordination - Create src/planning/coordinator.py with MultiAgentCoordinator class. Methods: __init__, coordinate(goals, agents), delegate_task(), merge_plans(), detect_conflicts(). Maintain agent capability registry. Write unit tests in tests/unit/test_coordinator.py.")
   task(category="unspecified-low", load_skills=[], run_in_background=false, prompt="Task 9: Integration Tests - Create tests/integration/test_planning.py with: test_end_to_end_planning, test_plan_repair, test_temporal_execution, test_multi_agent_coordination, test_trigger_integration. Verify all planning components work together. All tests must pass.")
   ```

5. **Final QA**: Verify all tasks pass their QA criteria
   - Run unit tests: pytest tests/unit/test_planning*.py
   - Run integration tests: pytest tests/integration/test_planning.py
   - Type check: mypy src/planning/
   - Lint: ruff check src/planning/