# Phase 3: Meta-Learning — Detailed Implementation Plan

> **Date:** 2026-04-08
> **Effort:** 4-5 days (simplified from 7-8)
> **Risk:** HIGH (complex ML, data sparsity)
> **Dependencies:** Phase 1 + Phase 2 complete
> **Oracle Review:** REQUIRED for all tasks

---

## Executive Summary

Phase 3 enables strategy selection learning. Oracle recommends **simplifications**: LinUCB over Neural Thompson Sampling (data efficiency), diagonal Fisher (sufficient for routing), simplified MAML (inner-loop only).

**GO/NO-GO: CONDITIONAL GO** — Only after Phase 1 + 2 complete, with ≥50 outcomes per strategy.

---

## Key Architecture Decisions (Oracle-Approved Simplifications)

| Component | Full Complexity | Simplified (Recommended) | Benefit |
|-----------|----------------|------------------------|---------|
| Bandit | Neural Thompson | **LinUCB** | 95% benefit, 20% complexity |
| MAML | Full PyTorch MAML | **Simplified inner-loop only** | 70% benefit, 30% complexity |
| EWC | Empirical Fisher | **Diagonal Fisher + weight decay** | 80% benefit, 25% complexity |
| Arms | 4 strategies | **3 strategies** (merge bandit+heuristic) | Less exploration burden |

---

## Task 3.1: LinUCB Strategy Selector

### Files to Create
- `packages/learning_engine/meta/strategy_selector.py`

### Architecture
```
Context: 390-dim (384 embedding + 4 task_type one-hot + 1 complexity + 1 session_time)
Arms: 3 (embedding_routing, graph_routing, heuristic_routing)
Algorithm: LinUCB with sliding window (7 days)
```

### Implementation
```python
class LinUCBArm:
    def __init__(self, strategy: str, dim: int = 390, alpha: float = 1.0):
        self.strategy = strategy
        self.A = np.eye(dim)  # Design matrix
        self.b = np.zeros(dim)  # Reward vector
        self.alpha = alpha
        self.pulls = 0
    
    def select(self, context: np.ndarray) -> float:
        A_inv = np.linalg.inv(self.A)
        theta = A_inv @ self.b
        p = theta @ context + self.alpha * np.sqrt(context @ A_inv @ context)
        return p
    
    def update(self, context: np.ndarray, reward: float):
        self.A += np.outer(context, context)
        self.b += reward * context
        self.pulls += 1

class LinUCBStrategySelector:
    def __init__(self, strategies: list = None):
        self.strategies = strategies or ["embedding", "graph", "heuristic"]
        self.arms = {s: LinUCBArm(s) for s in self.strategies}
    
    def select(self, context: np.ndarray) -> str:
        scores = {s: arm.select(context) for s, arm in self.arms.items()}
        return max(scores, key=scores.get)
    
    def update(self, strategy: str, context: np.ndarray, reward: float):
        self.arms[strategy].update(context, reward)
```

---

## Task 3.2: Simplified MAML (Inner-Loop Only)

### Files to Modify
- `packages/learning_engine/meta/maml.py` (rewrite)

### Architecture
```python
class MAMLRouter(nn.Module):
    def __init__(self, embedding_dim=384, hidden_dim=128, num_agents=11):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(embedding_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
        )
        self.heads = nn.ModuleList([nn.Linear(hidden_dim, 1) for _ in range(5)])  # L1-L5
    
    def inner_loop(self, support_x, support_y, steps=5, lr=0.01):
        """Fast adaptation on support set."""
        adapted = self.clone()
        for _ in range(steps):
            pred = adapted(support_x)
            loss = F.mse_loss(pred, support_y)
            grads = torch.autograd.grad(loss, adapted.parameters(), create_graph=True)
            for p, g in zip(adapted.parameters(), grads):
                p.data = p.data - lr * g
        return adapted
```

---

## Task 3.3: Diagonal Fisher EWC

### Files to Modify
- `packages/learning_engine/meta/ewc.py` (rewrite)

```python
class EWCEngine:
    def __init__(self, model: nn.Module, lambda_reg: float = 1000.0):
        self.model = model
        self.lambda_reg = lambda_reg
        self.fisher = {n: torch.zeros_like(p) for n, p in model.named_parameters()}
        self.optimal = {n: p.clone() for n, p in model.named_parameters()}
    
    def compute_fisher(self, dataloader):
        for inputs, targets in dataloader:
            self.model.zero_grad()
            output = self.model(inputs)
            loss = F.mse_loss(output, targets)
            loss.backward()
            for n, p in self.model.named_parameters():
                if p.grad is not None:
                    self.fisher[n] += p.grad.data ** 2
        for n in self.fisher:
            self.fisher[n] /= len(dataloader)
    
    def penalty(self):
        return sum((self.fisher[n] * (p - self.optimal[n])**2).sum() 
                   for n, p in self.model.named_parameters()) * self.lambda_reg
```

---

## Task 3.4: Meta-Learning Health Monitor

### Files to Create
- `packages/learning_engine/meta/health_monitor.py`

### Alerts
- Arm not selected in 48h → reinitialize
- Meta-loss > 1.0 → reduce LR 10x
- Validation accuracy < 40% after 200 tasks → fall back to heuristic
- Latency > 500ms → disable meta-learning

---

## Files Modified

| File | Action | Description |
|------|--------|-------------|
| `packages/learning_engine/meta/strategy_selector.py` | CREATE | LinUCB selector |
| `packages/learning_engine/meta/maml.py` | REWRITE | Simplified inner-loop MAML |
| `packages/learning_engine/meta/ewc.py` | REWRITE | Diagonal Fisher EWC |
| `packages/learning_engine/meta/health_monitor.py` | CREATE | Health monitoring |

---

## Go/No-Go Criteria

| Criterion | Threshold |
|-----------|-----------|
| Data availability | ≥50 outcomes per strategy |
| LinUCB convergence | Validation regret < 0.2 after 100 tasks |
| MAML few-shot | >60% accuracy with 5 support examples |
| EWC retained accuracy | >80% after 10 tasks |
| Mean latency | < 200ms |
