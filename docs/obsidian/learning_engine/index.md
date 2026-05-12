# Learning Engine Layer

## Overview

The Learning Engine Layer is a self-learning system that consolidates all learning code from multiple locations. It provides Q-learning, multi-armed bandits, meta-learning, routing optimization, A/B testing, cross-session transfer, prompt evolution, and Bayesian confidence estimation.

## Public API

```python
# Record delegation outcome
record_outcome(agent="hephaestus", level=3, success=True, latency_ms=1500)

# Route task based on learned weights
recommendation = route_task(task_description="Fix bug", level=3)

# Get system status
status = status()

# Trigger retraining
retrain()
```

## Architecture

### Core Modules

| Module | Purpose | Key Classes | Key Functions |
|--------|---------|-------------|---------------|
| rl/q_learning.py | Q-Learning engine | QLearningEngine | update(), get_best_action() |
| rl/bandits.py | Multi-armed bandits | MultiArmedBandit | select_arm(), update() |
| meta/meta_learning.py | Meta-learning | MetaLearningEngine, EWCEngine, ActiveLearningEngine | compute_importance(), select_samples() |
| routing/adaptive_router.py | Adaptive routing | AdaptiveRouter, CircuitBreaker, CircuitState | route(), update_weights() |
| routing/weight_optimizer.py | Weight optimization | RoutingWeightOptimizer | get_optimal_agent() |
| routing/confidence.py | Bayesian confidence | BayesianConfidenceEstimator | estimate() |
| delegation/delegation_learner.py | Delegation learning | DelegationLearner, PatternInsight | analyze_delegations(), learn() |
| session_hooks.py | Session lifecycle | SessionLifecycleHook | on_session_start(), on_session_end() |
| cross_session_transfer.py | Cross-session | CrossSessionTransfer | extract_knowledge(), apply_knowledge() |
| prompt_evolution.py | Prompt evolution | PromptWizard, PromptVersion | evolve(), evaluate() |

### Sub-Module Details

#### RL Module (rl/)

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| q_learning.py | Q-learning for routing | QLearningEngine |
| bandits.py | Multi-armed bandit selection | MultiArmedBandit |
| policy.py | Policy management | PolicyManager |
| rewards.py | Composite reward calculation | CompositeReward |

#### Meta Module (meta/)

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| meta_learning.py | Meta-learning engine | MetaLearningEngine |
| ewc.py | Elastic Weight Consolidation | EWCEngine |
| active_learning.py | Active learning | ActiveLearningEngine |

#### Routing Module (routing/)

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| adaptive_router.py | Adaptive routing with CB | AdaptiveRouter, CircuitBreaker |
| weight_optimizer.py | Weight optimization | RoutingWeightOptimizer |
| confidence.py | Bayesian confidence | BayesianConfidenceEstimator |
| ab_testing.py | A/B testing framework | ABTestingFramework, ABTest |
| outcome_hook.py | Task outcome hooks | TaskOutcomeHook |

#### Delegation Module (delegation/)

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| delegation_learner.py | From delegations | DelegationLearner, PatternInsight |
| decomposer.py | Task decomposition | TaskDecomposer |

## Components

### Q-Learning Engine

- **Purpose**: Q-learning for agent selection based on task complexity and success
- **Key Methods**:
  - `update()`: Update Q-values based on outcome
  - `get_best_action()`: Get optimal agent for task

### Multi-Armed Bandit

- **Purpose**: Explore/exploit balance for agent selection
- **Algorithms**: Epsilon-greedy, UCB, Thompson Sampling

### Meta-Learning (EWC)

- **Purpose**: Continual learning without catastrophic forgetting
- **Key Methods**:
  - `compute_importance()`: Calculate Fisher information
  - `apply_penalty()`: Apply EWC regularization

### Adaptive Router

- **Purpose**: Main routing with learning and circuit breakers
- **Features**:
  - Q-learning + Bandits integration
  - Circuit breaker pattern for failed agents
  - Bayesian confidence estimation
- **Key Classes**:
  - `AdaptiveRouter`: Main router
  - `CircuitBreaker`: Fault tolerance
  - `CircuitState`: CLOSED, OPEN, HALF_OPEN

### A/B Testing Framework

- **Purpose**: Test routing strategies in production
- **Classes**: ABTestingFramework, ABTest, TestVariant

### Cross-Session Transfer

- **Purpose**: Transfer learned knowledge across sessions
- **Methods**: extract_knowledge(), apply_knowledge()

### Prompt Evolution

- **Purpose**: Evolve prompts based on performance
- **Classes**: PromptWizard, PromptVersion, EvaluationGrade

## Relationships

- **Depends on**: memory_core (for pattern storage), intelligence (for routing)
- **Used by**: intelligence layer (for routing decisions), orchestration (for agent selection)

## Notes

- Consolidates learning code from 3 locations (src/tools/learning/, src/tools/intelligence/, src/infrastructure/proxy/)
- Modular bundle with lazy-initialized singletons
- Includes session hooks for lifecycle tracking
- Bayesian confidence estimation for routing decisions
- Circuit breaker pattern prevents routing to failing agents