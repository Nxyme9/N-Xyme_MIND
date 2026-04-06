# N-Xyme MIND v1.0 — Layer 3: Self-Learning Implementation Plan

> **Focus**: Build the self-learning engine with skill lifecycle state machine (NOVEL — no framework implements this)
> **Philosophy**: "We synthesize Frankenstein — stitch together what works from ALL sources, discard what failed."
> **Target**: Layer 3 implementation for v1.0

---

## TL;DR

| Component | Source | Pattern | License |
|-----------|--------|---------|---------|
| **Skill Lifecycle** | ace-agent/ace (891⭐) | Proposed→Experimental→Active→Deprecated→Archived | Apache 2.0 |
| **Skill Evaluation** | athena/core/skill_telemetry.py | Success rate, latency, cost tracking | ✅ MIT |
| **Prompt Evolution** | microsoft/PromptWizard (3.8k⭐) | Generate→Critique→Refine→Evaluate | ✅ MIT |
| **Self-Learning** | MemMachine (5.4k⭐) | Track outcomes → Extract patterns → Adapt | Apache 2.0 |
| **Skill Discovery** | SkillOrchestra (arXiv 2602.19672) | Automatic detection of needed skills | arXiv |

---

## Context

### Original Request (from Masterplan)

- **Layer**: 3 — Self-Learning
- **Files to create**: skill_lifecycle.py, prompt_evolution.py, self_learning.py
- **Current state**: Planned, not yet implemented

### Critical Gaps to Address

| Gap | Severity | Description |
|-----|----------|-------------|
| Skill lifecycle state machine | 🔴 CRITICAL | Proposed→Experimental→Active→Deprecated→Archived (NOVEL — no framework implements this) |
| Skill evaluation tracking | 🔴 CRITICAL | Success rate, latency, cost, user satisfaction |
| Prompt evolution engine | 🟡 HIGH | Generate→Critique→Refine→Evaluate (RetroAgent patterns) |
| Skill discovery | 🟡 HIGH | Automatic detection of needed skills |
| Skill composition | 🟡 HIGH | Dynamic combination based on task decomposition |
| Cross-session skill persistence | 🟢 MEDIUM | Learning persists across restarts |

### Repositories to Study

- **crewAIInc/crewai** — Skills as filesystem packages, tool registration
- **microsoft/autogen** (57K⭐) — Agent runtime lifecycle, state management
- **SkillOrchestra** (arXiv 2602.19672) — Skill transfer learning
- **RetroAgent** (arXiv) — Retrospective dual intrinsic feedback
- **ace-agent/ace** (891⭐) — Context evolution + playbook updates

### Existing Codebase Patterns

- **athena/core/skill_telemetry.py** (224 lines) — JSONL-based skill usage tracking
- **src/brain/memory/** — Working, episodic, semantic, procedural memory tiers
- **src/memory/** — Registry, router, connectors, embeddings, retrieval

---

## Work Objectives

### Core Objective

Implement Layer 3: Self-Learning with a complete skill lifecycle system that:
1. Tracks skill states through a finite state machine (proposed→experimental→active→deprecated→archived)
2. Records skill evaluations (success rate, latency, cost, user satisfaction)
3. Evolves prompts using generate→critique→refine→evaluate loops
4. Learns from outcomes to recommend actions based on past success
5. Automatically discovers needed skills from task decomposition

### Concrete Deliverables

```
src/learning/
├── __init__.py
├── skill_lifecycle.py       # Core state machine + evaluation
├── prompt_evolution.py     # Prompt feedback loops
├── self_learning.py         # Pattern extraction + adaptation
├── skill_discovery.py      # Automatic skill detection
├── skill_composition.py    # Dynamic skill combination
└── types.py                # Shared data structures

tests/test_learning/
├── __init__.py
├── test_skill_lifecycle.py
├── test_prompt_evolution.py
├── test_self_learning.py
├── test_skill_discovery.py
└── test_skill_composition.py
```

### Definition of Done

- [ ] Skill state machine implements all 5 states with valid transitions
- [ ] Skill evaluation tracks success rate, latency, cost, user satisfaction
- [ ] Prompt evolution runs generate→critique→refine→evaluate loop
- [ ] Self-learning extracts patterns from outcomes and recommends actions
- [ ] Skill discovery detects needed skills from task context
- [ ] Skill composition combines skills dynamically based on decomposition
- [ ] Cross-session persistence via JSONL/JSON storage
- [ ] All tests pass (100% coverage target)
- [ ] Integration with Layer 2 (Memory System) working
- [ ] Integration with Layer 5 (Agent Orchestration) working

---

## Task Dependency Graph

| Task | Depends On | Reason |
|------|------------|--------|
| **T1**: Create types.py (shared data structures) | None | Foundation for all other modules |
| **T2**: Implement SkillLifecycle state machine | T1 | Requires Skill, SkillEvaluation types |
| **T3**: Add skill evaluation tracking to SkillLifecycle | T2 | Built on state machine foundation |
| **T4**: Implement PromptEvolver class | T1 | Uses types, independent of lifecycle |
| **T5**: Implement SelfLearning class | T2, T4 | Depends on lifecycle + prompt evolution |
| **T6**: Implement SkillDiscovery | T1 | Independent, uses types |
| **T7**: Implement SkillComposition | T2, T6 | Depends on lifecycle + discovery |
| **T8**: Add cross-session persistence | T2, T3 | Requires lifecycle + evaluation |
| **T9**: Integration tests (Layer 2 + Layer 5) | T2, T4, T5, T6, T7 | All components complete |
| **T10**: Performance benchmarks | T9 | Requires all components |

---

## Parallel Execution Graph

```
Wave 1 (Start Immediately):
├── T1: Create types.py (no dependencies)
├── T4: Implement PromptEvolver (no dependencies)
└── T6: Implement SkillDiscovery (no dependencies)

Wave 2 (After Wave 1 completes):
├── T2: Implement SkillLifecycle state machine (depends: T1)
├── T5: Implement SelfLearning (depends: T1, T4)
└── T7: Implement SkillComposition (depends: T1, T6)

Wave 3 (After Wave 2 completes):
├── T3: Add skill evaluation tracking (depends: T2)
├── T8: Add cross-session persistence (depends: T2, T3)
└── T9: Integration tests (depends: T2, T4, T5, T6, T7)

Wave 4 (Final):
└── T10: Performance benchmarks (depends: T9)

Critical Path: T1 → T2 → T3 → T8 → T9 → T10
Estimated Parallel Speedup: ~45% faster than sequential
Max Concurrent: 3 (Wave 1), 3 (Wave 2), 3 (Wave 3)
```

---

## Task Categories + Skills Mapping

### Wave 1 (Parallel - 3 tasks)

**T1: Create types.py (shared data structures)**
- Category: `deep` — Design data structures that other modules depend on
- Skills: [] — No specialized skills needed for type definitions
- QA: Import all types in tests/test_learning/test_types.py

**T4: Implement PromptEvolver class**
- Category: `deep` — Complex feedback loop algorithm
- Skills: [] — No specialized skills for core algorithm
- QA: Run prompt evolution test with mock model

**T6: Implement SkillDiscovery**
- Category: `unspecified-high` — Pattern matching from task context
- Skills: [] — No specialized skills needed
- QA: Test skill detection from sample task descriptions

### Wave 2 (Parallel - 3 tasks)

**T2: Implement SkillLifecycle state machine**
- Category: `deep` — Finite state machine with validation
- Skills: [] — No specialized skills
- QA: Test all 5 states + transitions

**T5: Implement SelfLearning**
- Category: `unspecified-high` — Learning algorithm from outcomes
- Skills: [] — No specialized skills
- QA: Test pattern extraction and recommendation

**T7: Implement SkillComposition**
- Category: `unspecified-high` — Dynamic skill combination
- Skills: [] — No specialized skills
- QA: Test skill composition from task decomposition

### Wave 3 (Parallel - 3 tasks)

**T3: Add skill evaluation tracking**
- Category: `deep` — Metrics calculation and aggregation
- Skills: [] — Built on existing skill_telemetry patterns
- QA: Test success rate, latency, cost calculations

**T8: Add cross-session persistence**
- Category: `unspecified-high` — JSONL/JSON file operations
- Skills: [] — File I/O operations
- QA: Test persistence across restarts

**T9: Integration tests**
- Category: `unspecified-high` — Multi-component testing
- Skills: [] — Integration testing
- QA: All integration tests pass

### Wave 4 (Final - 1 task)

**T10: Performance benchmarks**
- Category: `unspecified-low` — Performance measurement
- Skills: [] — Benchmarking
- QA: Benchmarks complete with results

---

## Verification Strategy

### Test Infrastructure

- **Framework**: pytest
- **Coverage**: target 100%
- **Pattern**: Tests alongside implementation (TDD)

### QA Policy

Every task MUST include agent-executed QA scenarios. Evidence saved to `.sisyphus/evidence/`.

**T1 (types.py)**: Import test
- Tool: Bash (python -c "from src.learning.types import *")
- Expected: No ImportError

**T2 (SkillLifecycle state machine)**: State transitions
- Tool: Python (pytest tests/test_learning/test_skill_lifecycle.py)
- Expected: 5 states, valid transitions, invalid rejected

**T3 (skill evaluation)**: Metrics calculation
- Tool: Python (pytest tests/test_learning/test_evaluation.py)
- Expected: Success rate, latency, cost calculated correctly

**T4 (PromptEvolver)**: Evolution loop
- Tool: Python (pytest tests/test_learning/test_prompt_evolution.py)
- Expected: Generate→Critique→Refine→Evaluate produces improved prompt

**T5 (SelfLearning)**: Pattern recommendation
- Tool: Python (pytest tests/test_learning/test_self_learning.py)
- Expected: Recommends actions based on past success patterns

**T6 (SkillDiscovery)**: Skill detection
- Tool: Python (pytest tests/test_learning/test_skill_discovery.py)
- Expected: Detects relevant skills from task context

**T7 (SkillComposition)**: Dynamic combination
- Tool: Python (pytest tests/test_learning/test_skill_composition.py)
- Expected: Combines skills correctly based on task

**T8 (cross-session persistence)**: Data survival
- Tool: Python (pytest tests/test_learning/test_persistence.py)
- Expected: Data persists across process restarts

**T9 (integration)**: Layer 2 + Layer 5
- Tool: Python (pytest tests/test_learning/test_integration.py)
- Expected: All components work together

---

## Implementation Details

### Task 1: Create types.py (Shared Data Structures)

**Description**: Define all data structures used across learning modules.

**What to do**:
1. Create `src/learning/types.py`
2. Define `SkillState` enum (proposed, experimental, active, deprecated, archived)
3. Define `Skill` class (id, name, description, context, state, metrics)
4. Define `SkillMetrics` class (success_count, failure_count, avg_latency_ms, total_cost, user_satisfaction)
5. Define `SkillEvaluation` class (skill_id, timestamp, success, latency_ms, cost, user_feedback)
6. Define `PromptVersion` class (version, prompt, critique, refined, outcome, timestamp)
7. Define `LearnedPattern` class (context_pattern, action, success_rate, sample_count)
8. Define `TaskDecomposition` class (task, subtasks, required_skills, confidence)

**Must NOT do**:
- Don't include implementation logic (only type definitions)
- Don't add external dependencies beyond typing

**Recommended Agent Profile**:
- Category: `deep` — Design data structures that other modules depend on
- Skills: [] — No specialized skills needed for type definitions

**Acceptance Criteria**:
- [ ] SkillState enum with all 5 states
- [ ] Skill class with all required fields
- [ ] SkillMetrics class with all metrics
- [ ] SkillEvaluation class for tracking
- [ ] PromptVersion class for evolution history
- [ ] LearnedPattern class for pattern storage
- [ ] TaskDecomposition class for skill discovery input

---

### Task 2: Implement SkillLifecycle State Machine

**Description**: Core skill state machine with transition validation.

**What to do**:
1. Create `src/learning/skill_lifecycle.py`
2. Implement `SkillLifecycle` class:
   ```python
   class SkillLifecycle:
       STATES = ["proposed", "experimental", "active", "deprecated", "archived"]
       VALID_TRANSITIONS = {
           "proposed": ["experimental", "archived"],
           "experimental": ["active", "deprecated", "archived"],
           "active": ["deprecated", "archived"],
           "deprecated": ["archived", "active"],  # Can be reactivated
           "archived": []
       }
       
       def __init__(self, storage_path: Optional[Path] = None):
           self.skills: Dict[str, Skill] = {}
           self.storage_path = storage_path or Path(".athena/skills.json")
       
       def register(self, name: str, description: str, context: str) -> str:
           """Register new skill in proposed state."""
       
       def transition(self, skill_id: str, new_state: str) -> bool:
           """Transition skill to new state if valid."""
       
       def get_skill(self, skill_id: str) -> Optional[Skill]:
           """Get skill by ID."""
       
       def get_skills_by_state(self, state: SkillState) -> List[Skill]:
           """Get all skills in a specific state."""
       
       def get_active_skills(self, context: Optional[str] = None) -> List[Skill]:
           """Get active skills, optionally filtered by context relevance."""
   ```

3. Add validation for invalid transitions
4. Add auto-promotion logic (experimental → active after N successes)
5. Add auto-demotion logic (active → deprecated after failure threshold)

**Must NOT do**:
- Don't add evaluation tracking (Task 3)
- Don't add persistence (Task 8)
- Don't add discovery (Task 6)

**Recommended Agent Profile**:
- Category: `deep` — Finite state machine with validation
- Skills: [] — No specialized skills

**References**:
- athena/core/skill_telemetry.py:40-73 — Existing telemetry patterns
- ace-agent/ace (Apache 2.0) — Skill lifecycle patterns

**Acceptance Criteria**:
- [ ] All 5 states defined in enum
- [ ] Valid transitions enforced, invalid rejected
- [ ] Auto-promotion triggers after 3+ successes in experimental
- [ ] Auto-demotion triggers at 50%+ failure rate in active
- [ ] get_active_skills returns ranked by relevance

---

### Task 3: Add Skill Evaluation Tracking

**Description**: Track success rate, latency, cost, user satisfaction per skill.

**What to do**:
1. Extend `SkillLifecycle` with evaluation methods:
   ```python
   def record_evaluation(self, skill_id: str, evaluation: SkillEvaluation) -> None:
       """Record skill usage outcome."""
   
   def get_skill_metrics(self, skill_id: str) -> SkillMetrics:
       """Get calculated metrics for skill."""
   
   def get_success_rate(self, skill_id: str, window: Optional[int] = None) -> float:
       """Get success rate, optionally for last N evaluations."""
   
   def get_avg_latency(self, skill_id: str) -> float:
       """Get average latency in milliseconds."""
   
   def get_total_cost(self, skill_id: str) -> float:
       """Get total cost in USD."""
   
   def get_user_satisfaction(self, skill_id: str) -> Optional[float]:
       """Get average user satisfaction (0-1)."""
   ```

2. Add auto-transition evaluation in `record_evaluation`:
   - experimental → active: success_rate >= 0.7 after 5+ uses
   - active → deprecated: success_rate < 0.5 after 10+ uses
   - deprecated → archived: no usage for 30 days

3. Add metrics aggregation (rolling window support)

**Must NOT do**:
- Don't change state machine (Task 2 complete)
- Don't add persistence (Task 8)

**Recommended Agent Profile**:
- Category: `deep` — Metrics calculation and aggregation
- Skills: [] — Built on existing skill_telemetry patterns

**References**:
- athena/core/skill_telemetry.py:140-201 — get_skill_stats patterns
- athena/core/skill_telemetry.py:204-224 — get_dead_skills patterns

**Acceptance Criteria**:
- [ ] record_evaluation updates skill metrics
- [ ] get_success_rate returns correct percentage
- [ ] get_avg_latency returns milliseconds
- [ ] get_total_cost returns USD sum
- [ ] get_user_satisfaction returns 0-1 or None
- [ ] Auto-transitions trigger based on thresholds

---

### Task 4: Implement PromptEvolver Class

**Description**: Prompt feedback loop with generate→critique→refine→evaluate.

**What to do**:
1. Create `src/learning/prompt_evolution.py`
2. Implement `PromptEvolver` class:
   ```python
   class PromptEvolver:
       def __init__(self, model_provider: Optional[ModelProvider] = None):
           self.model = model_provider
           self.evolutions: Dict[str, List[PromptVersion]] = {}
       
       def create_prompt(self, name: str, initial_prompt: str) -> str:
           """Create new prompt with initial version."""
       
       def evolve(self, prompt_id: str, context: str, outcome: str) -> PromptVersion:
           """Run one complete feedback loop."""
       
       def _generate_variation(self, prompt: str, context: str) -> str:
           """Generate prompt variation."""
       
       def _critique(self, variation: str, context: str, outcome: str) -> str:
           """Self-critique the variation."""
       
       def _refine(self, variation: str, critique: str) -> str:
           """Improve based on critique."""
       
       def _evaluate(self, new: str, old: str, context: str) -> bool:
           """Compare prompts, return True if new is better."""
       
       def get_current_prompt(self, prompt_id: str) -> Optional[str]:
           """Get current version of prompt."""
       
       def get_history(self, prompt_id: str) -> List[PromptVersion]:
           """Get version history."""
       
       def get_best_prompt(self, prompt_id: str) -> Optional[str]:
           """Get best performing prompt version."""
   ```

3. Implement evolution loop (Generate → Critique → Refine → Evaluate)
4. Add model provider abstraction for LLM calls
5. Add version history tracking
6. Add A/B testing via LLM-as-judge

**Must NOT do**:
- Don't add skill lifecycle integration (Task 2 first)
- Don't add persistence (Task 8)

**Recommended Agent Profile**:
- Category: `deep` — Complex feedback loop algorithm
- Skills: [] — No specialized skills for core algorithm

**References**:
- microsoft/PromptWizard — Generate→Critique→Refine→Evaluate patterns
- N-XYME-MEMORY-LEARNING.md:351-428 — PromptEvolver implementation pattern

**Acceptance Criteria**:
- [ ] create_prompt initializes new prompt
- [ ] evolve runs full loop, returns new version
- [ ] get_current_prompt returns latest
- [ ] get_history returns all versions
- [ ] get_best_prompt returns highest-performing

---

### Task 5: Implement SelfLearning Class

**Description**: Track outcomes, extract patterns, adapt behavior.

**What to do**:
1. Create `src/learning/self_learning.py`
2. Implement `SelfLearning` class:
   ```python
   class SelfLearning:
       def __init__(self, skill_lifecycle: SkillLifecycle):
           self.skill_lifecycle = skill_lifecycle
           self.patterns: Dict[str, List[LearnedPattern]] = {}
       
       def record_success(self, context: str, action: str, outcome: str) -> None:
           """Record successful action for pattern extraction."""
       
       def record_failure(self, context: str, action: str, error: str) -> None:
           """Record failed action for anti-pattern tracking."""
       
       def _find_similar_contexts(self, context: str) -> List[str]:
           """Find semantically similar contexts."""
       
       def extract_patterns(self) -> int:
           """Extract patterns from recorded outcomes."""
       
       def get_recommended_actions(self, context: str) -> List[Tuple[str, float]]:
           """Get ranked actions based on past success."""
       
       def get_context_score(self, context: str, action: str) -> float:
           """Calculate success probability for action in context."""
       
       def adapt(self, feedback: Dict[str, Any]) -> None:
           """Adapt based on explicit feedback."""
   ```

2. Add pattern storage (context_pattern → action → success_rate)
3. Add semantic similarity for context matching
4. Add action recommendation ranking
5. Add adaptation from explicit feedback

**Must NOT do**:
- Don't add persistence (Task 8)
- Don't add skill discovery (Task 6)

**Recommended Agent Profile**:
- Category: `unspecified-high` — Learning algorithm from outcomes
- Skills: [] — No specialized skills

**References**:
- MemMachine (Apache 2.0) — Success/failure pattern learning
- N-XYME-MEMORY-LEARNING.md:162-169 — SelfLearning pattern

**Acceptance Criteria**:
- [ ] record_success stores outcome
- [ ] record_failure stores anti-pattern
- [ ] extract_patterns creates LearnedPattern entries
- [ ] get_recommended_actions returns ranked actions
- [ ] get_context_score calculates probability

---

### Task 6: Implement SkillDiscovery

**Description**: Automatic detection of needed skills from task context.

**What to do**:
1. Create `src/learning/skill_discovery.py`
2. Implement `SkillDiscovery` class:
   ```python
   class SkillDiscovery:
       def __init__(self, skill_lifecycle: SkillLifecycle):
           self.skill_lifecycle = skill_lifecycle
       
       def decompose_task(self, task: str) -> TaskDecomposition:
           """Decompose task into subtasks and required skills."""
       
       def detect_needed_skills(self, context: str) -> List[Tuple[str, float]]:
           """Detect skills needed for current context."""
       
       def suggest_new_skills(self, task: str) -> List[Dict[str, str]]:
           """Suggest new skills to create based on task gaps."""
       
       def _analyze_task_requirements(self, task: str) -> Dict[str, Any]:
           """Analyze task to extract requirements."""
       
       def _match_skills_to_requirements(self, requirements: Dict) -> List[Tuple[str, float]]:
           """Match existing skills to requirements."""
   ```

2. Add task decomposition (task → subtasks + required skills)
3. Add skill gap detection (existing vs. needed)
4. Add new skill suggestions based on task patterns

**Must NOT do**:
- Don't add skill composition (Task 7)
- Don't add persistence (Task 8)

**Recommended Agent Profile**:
- Category: `unspecified-high` — Pattern matching from task context
- Skills: [] — No specialized skills needed

**References**:
- SkillOrchestra (arXiv 2602.19672) — Automatic skill detection
- crewAIInc/crewai — Skill loading patterns

**Acceptance Criteria**:
- [ ] decompose_task returns TaskDecomposition
- [ ] detect_needed_skills returns ranked skills
- [ ] suggest_new_skills returns new skill proposals

---

### Task 7: Implement SkillComposition

**Description**: Dynamic skill combination based on task decomposition.

**What to do**:
1. Create `src/learning/skill_composition.py`
2. Implement `SkillComposition` class:
   ```python
   class SkillComposition:
       def __init__(self, skill_lifecycle: SkillLifecycle, skill_discovery: SkillDiscovery):
           self.skill_lifecycle = skill_lifecycle
           self.skill_discovery = skill_discovery
       
       def compose_skills(self, task: str) -> List[Skill]:
           """Compose optimal skill set for task."""
       
       def validate_composition(self, skills: List[Skill]) -> bool:
           """Validate skill composition is valid."""
       
       def optimize_composition(self, skills: List[Skill], task: str) -> List[Skill]:
           """Optimize skill order and subset for task."""
       
       def get_composition_confidence(self, skills: List[Skill], task: str) -> float:
           """Calculate confidence in composition."""
   ```

2. Add composition strategy (parallel, sequential, fallback)
3. Add conflict detection (skills that shouldn't combine)
4. Add optimization for skill ordering
5. Add confidence scoring

**Must NOT do**:
- Don't add persistence (Task 8)
- Don't add integration tests (Task 9)

**Recommended Agent Profile**:
- Category: `unspecified-high` — Dynamic skill combination
- Skills: [] — No specialized skills

**References**:
- microsoft/autogen — Agent composition patterns
- crewAIInc/crewai — Task composition patterns

**Acceptance Criteria**:
- [ ] compose_skills returns skill list
- [ ] validate_composition checks conflicts
- [ ] optimize_composition improves ordering
- [ ] get_composition_confidence returns 0-1

---

### Task 8: Add Cross-Session Persistence

**Description**: Learning persists across restarts via JSONL/JSON storage.

**What to do**:
1. Add persistence layer to all learning components:
   ```python
   def save(self, path: Path) -> None:
       """Save all state to disk."""
   
   def load(self, path: Path) -> None:
       """Load all state from disk."""
   
   def export_skills(self, path: Path) -> None:
       """Export skills to JSON."""
   
   def import_skills(self, path: Path) -> None:
       """Import skills from JSON."""
   ```

2. Add JSONL logging for skill evaluations
3. Add JSON storage for skill states
4. Add migration support for schema changes

**Must NOT do**:
- Don't change core logic (all tasks complete)

**Recommended Agent Profile**:
- Category: `unspecified-high` — JSONL/JSON file operations
- Skills: [] — File I/O operations

**References**:
- athena/core/skill_telemetry.py:28-73 — JSONL append patterns

**Acceptance Criteria**:
- [ ] save/load preserves all state
- [ ] Export/import works correctly
- [ ] Data survives process restart

---

### Task 9: Integration Tests

**Description**: Test integration with Layer 2 (Memory) and Layer 5 (Orchestration).

**What to do**:
1. Create integration test file
2. Test Layer 2 integration (Memory System):
   - Memory retrieval triggers skill recommendation
   - Skill evaluation updates memory patterns
   - Self-learning reads from memory
3. Test Layer 5 integration (Agent Orchestration):
   - Task decomposition triggers skill discovery
   - Skill composition provides skills to agents
   - Agent execution triggers evaluation recording

**Must NOT do**:
- Don't test beyond Layer 2 + Layer 5

**Recommended Agent Profile**:
- Category: `unspecified-high` — Multi-component testing
- Skills: [] — Integration testing

**References**:
- src/brain/memory/ — Layer 2 memory structure
- src/a2a_agents.py — Agent patterns

**Acceptance Criteria**:
- [ ] Layer 2 integration tests pass
- [ ] Layer 5 integration tests pass
- [ ] Cross-layer data flow works

---

### Task 10: Performance Benchmarks

**Description**: Measure performance of all learning components.

**What to do**:
1. Create benchmark suite:
   - Skill state machine: 1000 transitions
   - Prompt evolution: 100 iterations
   - Self-learning pattern extraction: 1000 outcomes
   - Skill discovery: 100 task decompositions
   - Skill composition: 100 compositions

2. Measure:
   - Latency per operation
   - Memory usage
   - Storage size growth

3. Document performance characteristics

**Recommended Agent Profile**:
- Category: `unspecified-low` — Performance measurement
- Skills: [] — Benchmarking

**Acceptance Criteria**:
- [ ] All benchmarks complete
- [ ] Results documented

---

## Commit Strategy

### Wave 1 Commits

**Commit 1**: `types: Add shared data structures for learning system`
- Files: src/learning/types.py, src/learning/__init__.py
- Pre-commit: python -c "from src.learning.types import *"

**Commit 2**: `learning: Implement PromptEvolver for prompt feedback loops`
- Files: src/learning/prompt_evolution.py
- Pre-commit: pytest tests/test_learning/test_prompt_evolution.py

**Commit 3**: `learning: Add SkillDiscovery for automatic skill detection`
- Files: src/learning/skill_discovery.py
- Pre-commit: pytest tests/test_learning/test_skill_discovery.py

### Wave 2 Commits

**Commit 4**: `learning: Implement SkillLifecycle state machine`
- Files: src/learning/skill_lifecycle.py
- Pre-commit: pytest tests/test_learning/test_skill_lifecycle.py

**Commit 5**: `learning: Implement SelfLearning for pattern extraction`
- Files: src/learning/self_learning.py
- Pre-commit: pytest tests/test_learning/test_self_learning.py

**Commit 6**: `learning: Add SkillComposition for dynamic combination`
- Files: src/learning/skill_composition.py
- Pre-commit: pytest tests/test_learning/test_skill_composition.py

### Wave 3 Commits

**Commit 7**: `learning: Add skill evaluation tracking to SkillLifecycle`
- Files: src/learning/skill_lifecycle.py (update)
- Pre-commit: pytest tests/test_learning/test_evaluation.py

**Commit 8**: `learning: Add cross-session persistence`
- Files: src/learning/skill_lifecycle.py, src/learning/prompt_evolution.py, src/learning/self_learning.py (update)
- Pre-commit: pytest tests/test_learning/test_persistence.py

**Commit 9**: `learning: Add integration tests`
- Files: tests/test_learning/test_integration.py
- Pre-commit: pytest tests/test_learning/test_integration.py

### Wave 4 Commits

**Commit 10**: `learning: Add performance benchmarks`
- Files: benchmarks/test_learning_benchmarks.py
- Pre-commit: python benchmarks/test_learning_benchmarks.py

---

## Success Criteria

### Verification Commands

```bash
# Type checking
python -m py_compile src/learning/types.py
python -m py_compile src/learning/skill_lifecycle.py
python -m py_compile src/learning/prompt_evolution.py
python -m py_compile src/learning/self_learning.py
python -m py_compile src/learning/skill_discovery.py
python -m py_compile src/learning/skill_composition.py

# Test execution
pytest tests/test_learning/ -v --tb=short

# Coverage
pytest tests/test_learning/ --cov=src/learning --cov-report=term-missing

# Integration
pytest tests/test_learning/test_integration.py -v

# Benchmarks
python benchmarks/test_learning_benchmarks.py
```

### Final Checklist

- [ ] All 10 tasks implemented
- [ ] All 10 commits made
- [ ] 100% test coverage target
- [ ] Type checking passes
- [ ] Integration tests pass
- [ ] Benchmarks complete
- [ ] Documentation added
- [ ] Integration with Layer 2 (Memory) working
- [ ] Integration with Layer 5 (Orchestration) working
- [ ] Cross-session persistence working

---

## Notes

1. **Model Provider**: PromptEvolver requires model_provider abstraction for LLM calls. Use existing pattern from src/model_providers.py.

2. **Athena Compatibility**: Learning data stored in .athena/ directory to match existing telemetry.

3. **Iterative Value**: Each task adds value independently. T1-T3 create foundation, T4-T7 add capabilities, T8-T10 finalize.

4. **Novel Feature**: Skill lifecycle state machine is the core differentiator — no other framework implements this pattern.

5. **Persistence Strategy**: Use JSONL for high-frequency events (evaluations), JSON for state (skills, patterns).

---

## TODO List (ADD THESE)

> CALLER: Add these TODOs using TodoWrite/TaskCreate and execute by wave.

### Wave 1 (Start Immediately - No Dependencies)

- [ ] **T1. Create types.py (shared data structures)**
  - What: Define SkillState enum, Skill class, SkillMetrics, SkillEvaluation, PromptVersion, LearnedPattern, TaskDecomposition
  - Depends: None
  - Blocks: T2, T4, T5, T6, T7
  - Category: `deep`
  - Skills: []
  - QA: Import test passes

- [ ] **T4. Implement PromptEvolver class**
  - What: Create PromptEvolver with generate→critique→refine→evaluate loop
  - Depends: None (can run in parallel with T1)
  - Blocks: T5
  - Category: `deep`
  - Skills: []
  - QA: pytest tests/test_learning/test_prompt_evolution.py passes

- [ ] **T6. Implement SkillDiscovery**
  - What: Create SkillDiscovery with task decomposition and skill detection
  - Depends: None (can run in parallel with T1)
  - Blocks: T7
  - Category: `unspecified-high`
  - Skills: []
  - QA: pytest tests/test_learning/test_skill_discovery.py passes

### Wave 2 (After Wave 1 Completes)

- [ ] **T2. Implement SkillLifecycle state machine**
  - What: Create SkillLifecycle with 5-state FSM, transition validation, auto-promotion/demotion
  - Depends: T1
  - Blocks: T3, T5, T7, T8, T9
  - Category: `deep`
  - Skills: []
  - QA: pytest tests/test_learning/test_skill_lifecycle.py passes

- [ ] **T5. Implement SelfLearning class**
  - What: Create SelfLearning with outcome tracking, pattern extraction, action recommendation
  - Depends: T1, T4
  - Blocks: T9
  - Category: `unspecified-high`
  - Skills: []
  - QA: pytest tests/test_learning/test_self_learning.py passes

- [ ] **T7. Implement SkillComposition**
  - What: Create SkillComposition with dynamic combination, conflict detection, optimization
  - Depends: T1, T6
  - Blocks: T9
  - Category: `unspecified-high`
  - Skills: []
  - QA: pytest tests/test_learning/test_skill_composition.py passes

### Wave 3 (After Wave 2 Completes)

- [ ] **T3. Add skill evaluation tracking**
  - What: Extend SkillLifecycle with record_evaluation, get_success_rate, get_avg_latency, get_total_cost, get_user_satisfaction
  - Depends: T2
  - Blocks: T8, T9
  - Category: `deep`
  - Skills: []
  - QA: pytest tests/test_learning/test_evaluation.py passes

- [ ] **T8. Add cross-session persistence**
  - What: Add save/load methods to all components, JSONL logging, JSON state storage
  - Depends: T2, T3
  - Blocks: T9
  - Category: `unspecified-high`
  - Skills: []
  - QA: pytest tests/test_learning/test_persistence.py passes

- [ ] **T9. Integration tests**
  - What: Test Layer 2 (Memory) and Layer 5 (Orchestration) integration
  - Depends: T2, T4, T5, T6, T7
  - Blocks: T10
  - Category: `unspecified-high`
  - Skills: []
  - QA: pytest tests/test_learning/test_integration.py passes

### Wave 4 (Final)

- [ ] **T10. Performance benchmarks**
  - What: Measure latency, memory, storage for all components
  - Depends: T9
  - Blocks: None
  - Category: `unspecified-low`
  - Skills: []
  - QA: Benchmarks complete with results

## Execution Instructions

1. **Wave 1**: Fire these tasks IN PARALLEL (no dependencies)
   ```
   task(category="deep", load_skills=[], run_in_background=false, prompt="Task 1: Create types.py with SkillState enum, Skill class, SkillMetrics, SkillEvaluation, PromptVersion, LearnedPattern, TaskDecomposition in src/learning/types.py")
   task(category="deep", load_skills=[], run_in_background=false, prompt="Task 4: Implement PromptEvolver with generate→critique→refine→evaluate loop in src/learning/prompt_evolution.py")
   task(category="unspecified-high", load_skills=[], run_in_background=false, prompt="Task 6: Implement SkillDiscovery with task decomposition and skill detection in src/learning/skill_discovery.py")
   ```

2. **Wave 2**: After Wave 1 completes, fire next wave IN PARALLEL
   ```
   task(category="deep", load_skills=[], run_in_background=false, prompt="Task 2: Implement SkillLifecycle state machine with 5 states (proposed→experimental→active→deprecated→archived), transition validation, auto-promotion/demotion in src/learning/skill_lifecycle.py")
   task(category="unspecified-high", load_skills=[], run_in_background=false, prompt="Task 5: Implement SelfLearning with record_success/record_failure, extract_patterns, get_recommended_actions in src/learning/self_learning.py")
   task(category="unspecified-high", load_skills=[], run_in_background=false, prompt="Task 7: Implement SkillComposition with compose_skills, validate_composition, optimize_composition in src/learning/skill_composition.py")
   ```

3. **Wave 3**: After Wave 2 completes, fire next wave IN PARALLEL
   ```
   task(category="deep", load_skills=[], run_in_background=false, prompt="Task 3: Add skill evaluation tracking to SkillLifecycle - record_evaluation, get_success_rate, get_avg_latency, get_total_cost, get_user_satisfaction, auto-transitions")
   task(category="unspecified-high", load_skills=[], run_in_background=false, prompt="Task 8: Add cross-session persistence - save/load methods, JSONL logging, JSON state storage for all learning components")
   task(category="unspecified-high", load_skills=[], run_in_background=false, prompt="Task 9: Create integration tests for Layer 2 (Memory) and Layer 5 (Orchestration) integration in tests/test_learning/test_integration.py")
   ```

4. **Wave 4**: After Wave 3 completes, fire final task
   ```
   task(category="unspecified-low", load_skills=[], run_in_background=false, prompt="Task 10: Create performance benchmarks for all learning components - measure latency, memory, storage in benchmarks/test_learning_benchmarks.py")
   ```

5. **Final QA**: Verify all tasks pass their QA criteria