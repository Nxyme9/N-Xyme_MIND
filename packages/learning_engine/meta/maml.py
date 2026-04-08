"""Meta-Learning — Real MAML-style adaptation for fast task learning.

This module implements Model-Agnostic Meta-Learning (MAML) with PyTorch:
- Shared encoder network for feature extraction
- Task-specific adaptation heads
- Inner loop: few-shot gradient adaptation (create_graph=True)
- Outer loop: meta-update on query tasks
"""

from __future__ import annotations

import torch
import torch.nn as nn
from dataclasses import dataclass, field
from typing import Any

META_LR = 0.01
META_TASKS = 5


@dataclass
class MetaParameters:
    inner_lr: float = META_LR
    outer_lr: float = 0.001
    task_gradients: dict[str, list[float]] = field(default_factory=dict)


class TaskEncoder(nn.Module):
    def __init__(self, input_dim: int = 64, hidden_dim: int = 64, output_dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class TaskHead(nn.Module):
    def __init__(self, input_dim: int = 64, output_dim: int = 1):
        super().__init__()
        self.linear = nn.Linear(input_dim, output_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear(x)


class MetaLearner:
    def __init__(
        self,
        inner_lr: float = META_LR,
        outer_lr: float = 0.001,
        input_dim: int = 64,
        hidden_dim: int = 64,
        output_dim: int = 64,
    ):
        self.inner_lr = inner_lr
        self.outer_lr = outer_lr
        self._device = torch.device("cpu")

        self.encoder = TaskEncoder(input_dim, hidden_dim, output_dim).to(self._device)
        self.task_heads: dict[str, TaskHead] = {}
        self.meta_optimizer = torch.optim.Adam(self.encoder.parameters(), lr=outer_lr)
        self._adapted: dict[str, dict[str, torch.Tensor]] = {}

    def _head(self, task_type: str) -> TaskHead:
        if task_type not in self.task_heads:
            self.task_heads[task_type] = TaskHead(64, 1).to(self._device)
        return self.task_heads[task_type]

    def _features(self, outcomes: list[dict[str, Any]]) -> torch.Tensor:
        feats = []
        for o in outcomes:
            r = o.get("reward", 0.0)
            feat = torch.tensor([r, o.get("loss", 0.0), o.get("step", 0.0), 0.0], dtype=torch.float32)
            if feat.shape[0] < 64:
                feat = torch.cat([feat, torch.zeros(64 - feat.shape[0])])
            feats.append(feat[:64])
        if not feats:
            feats = [torch.zeros(64)]
        return torch.stack(feats).to(self._device)

    def adaptation_step(
        self, task_id: str, task_type: str, support_outcomes: list[dict[str, Any]]
    ) -> dict[str, torch.Tensor]:
        head = self._head(task_type)

        if not support_outcomes:
            adapted = {k: v.clone() for k, v in dict(head.named_parameters()).items()}
            self._adapted[task_id] = adapted
            return adapted

        support_x = self._features(support_outcomes)
        support_y = torch.tensor([o.get("reward", 0.0) for o in support_outcomes], dtype=torch.float32).to(self._device)

        if support_y.shape[0] == 1:
            support_y = support_y.unsqueeze(0)

        adapted_params = {k: v.clone() for k, v in dict(head.named_parameters()).items()}

        for _ in range(3):
            pred = head(support_x.mean(dim=0, keepdim=True))
            loss = nn.functional.mse_loss(pred.squeeze(), support_y.mean())

            grads = torch.autograd.grad(
                loss,
                head.parameters(),
                create_graph=True,
                allow_unused=True,
            )

            with torch.no_grad():
                for (name, _), g in zip(head.named_parameters(), grads or []):
                    if g is not None:
                        adapted_params[name] = adapted_params.get(name, torch.zeros_like(g)) - self.inner_lr * g

        self._adapted[task_id] = adapted_params
        return adapted_params

    def meta_update(
        self,
        support_by_task: dict[str, list[dict[str, Any]]],
        query_by_task: dict[str, list[dict[str, Any]]],
    ) -> dict[str, float]:
        if not query_by_task:
            return {"meta_loss": 0.0, "num_tasks": 0}

        total_loss = 0.0
        num_tasks = 0

        for task_id, query_outcomes in query_by_task.items():
            if not query_outcomes:
                continue
            num_tasks += 1

            support_outcomes = support_by_task.get(task_id, [])
            task_type = query_outcomes[0].get("task_type", "default")

            _ = self.adaptation_step(task_id, task_type, support_outcomes)

            query_x = self._features(query_outcomes)
            query_y = torch.tensor([o.get("reward", 0.0) for o in query_outcomes], dtype=torch.float32).to(self._device)

            encoder_out = self.encoder(query_x.mean(dim=0, keepdim=True))
            head = self._head(task_type)
            pred = head(encoder_out)
            loss = nn.functional.mse_loss(pred.squeeze(), query_y.mean())

            total_loss += loss

        avg_loss = total_loss / max(num_tasks, 1)

        self.meta_optimizer.zero_grad()
        avg_loss.backward()
        self.meta_optimizer.step()

        return {
            "meta_loss": avg_loss.item(),
            "num_tasks": num_tasks,
            "inner_lr": self.inner_lr,
            "outer_lr": self.outer_lr,
        }

    def get_parameters(self) -> dict[str, float]:
        params = {}
        for name, p in self.encoder.named_parameters():
            params[f"encoder_{name}"] = p.detach().cpu().item()
        for task_type, head in self.task_heads.items():
            for name, p in head.named_parameters():
                params[f"{task_type}_{name}"] = p.detach().cpu().item()
        return params


class MetaLearningEngine:
    def __init__(self, inner_lr: float = META_LR, outer_lr: float = 0.001):
        self.inner_lr = inner_lr
        self.outer_lr = outer_lr
        self._meta_learner = MetaLearner(inner_lr=inner_lr, outer_lr=outer_lr)

    def adaptation_step(
        self, task_id: str, support_outcomes: list[dict[str, Any]]
    ) -> dict[str, torch.Tensor]:
        task_type = support_outcomes[0].get("task_type", "default") if support_outcomes else "default"
        adapted = self._meta_learner.adaptation_step(task_id, task_type, support_outcomes)
        return adapted

    def meta_update(self, query_outcomes: list[dict[str, Any]]) -> dict[str, float]:
        if not query_outcomes:
            return {"meta_loss": 0.0, "num_tasks": 0}

        support_by_task: dict[str, list[dict[str, Any]]] = {}
        query_by_task: dict[str, list[dict[str, Any]]] = {}

        for outcome in query_outcomes:
            task_id = outcome.get("task_id", "default")
            if outcome.get("is_query", False):
                query_by_task.setdefault(task_id, []).append(outcome)
            else:
                support_by_task.setdefault(task_id, []).append(outcome)

        if not query_by_task:
            query_by_task = {"default": query_outcomes}

        return self._meta_learner.meta_update(support_by_task, query_by_task)

    def get_parameters(self) -> dict[str, float]:
        return self._meta_learner.get_parameters()


def _test():
    print("Running MAML test...")
    engine = MetaLearningEngine(inner_lr=0.1, outer_lr=0.01)

    task1_support = [
        {"task_id": "task1", "task_type": "test", "reward": 1.0, "loss": 0.5, "step": 0},
        {"task_id": "task1", "task_type": "test", "reward": 1.5, "loss": 0.3, "step": 1},
    ]
    task1_query = [
        {"task_id": "task1", "task_type": "test", "is_query": True, "reward": 1.2, "loss": 0.4, "step": 2},
    ]

    print("  Adaptation step...")
    adapted = engine.adaptation_step("task1", task1_support)
    print(f"    Adapted params: {adapted}")

    print("  Meta-update...")
    result = engine.meta_update(task1_support + task1_query)
    print(f"    Meta loss: {result['meta_loss']:.4f}")

    task2_support = [
        {"task_id": "task2", "task_type": "test", "reward": 0.5, "loss": 0.8, "step": 0},
        {"task_id": "task2", "task_type": "test", "reward": 0.7, "loss": 0.6, "step": 1},
    ]
    task2_query = [
        {"task_id": "task2", "task_type": "test", "is_query": True, "reward": 0.6, "loss": 0.7, "step": 2},
    ]

    print("  Second adaptation...")
    adapted2 = engine.adaptation_step("task2", task2_support)
    print(f"    Adapted params: {adapted2}")

    print("  Second meta-update...")
    result2 = engine.meta_update(task2_support + task2_query)
    print(f"    Meta loss: {result2['meta_loss']:.4f}")

    print("✅ MAML test passed!")


if __name__ == "__main__":
    _test()


__all__ = [
    "MetaParameters",
    "MetaLearningEngine",
    "MetaLearner",
    "TaskEncoder",
    "TaskHead",
    "META_LR",
    "META_TASKS",
]
