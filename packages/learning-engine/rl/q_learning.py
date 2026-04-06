"""Reinforcement Learning — Q-Learning implementation.

Tabular Q-Learning with TD updates for optimal action selection.
Q(s, a) = Q(s, a) + α * (r + γ * max_a' Q(s', a') - Q(s, a))
"""

from __future__ import annotations

import json
import math
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Configuration
DEFAULT_ALPHA = 0.1  # Learning rate for Q-learning
DEFAULT_GAMMA = 0.9  # Discount factor
DEFAULT_EPSILON = 0.1  # Exploration rate (epsilon-greedy)


class ActionType(Enum):
    """Available actions for routing decisions."""

    EXPLORE = "explore"
    DELEGATE = "delegate"
    ORACLE = "oracle"
    LIBRARIAN = "librarian"
    HEPHAESTUS = "hephaestus"
    MULTIMODAL = "multimodal"


@dataclass
class QState:
    """A state representation for Q-learning (task + context hash)."""

    task: str
    context_hash: str

    def to_key(self) -> str:
        return f"{self.task}|{self.context_hash}"

    @staticmethod
    def from_context(task: str, context: dict[str, Any]) -> "QState":
        ctx_hash = _hash_context(context)
        return QState(task=task, context_hash=ctx_hash[:16])


@dataclass
class QTable:
    """Q-value table with (state, action) -> value mapping."""

    values: dict[str, dict[str, float]] = field(
        default_factory=lambda: defaultdict(dict)
    )

    def get(self, state: QState, action: ActionType) -> float:
        key = state.to_key()
        return self.values.get(key, {}).get(action.value, 0.0)

    def set(self, state: QState, action: ActionType, value: float) -> None:
        self.values[state.to_key()][action.value] = value

    def update(self, state: QState, action: ActionType, delta: float) -> None:
        key = state.to_key()
        if key not in self.values:
            self.values[key] = {}
        if action.value not in self.values[key]:
            self.values[key][action.value] = 0.0
        self.values[key][action.value] += delta

    def to_json(self) -> str:
        return json.dumps(self.values, separators=(",", ":"))


def _hash_context(context: dict[str, Any]) -> str:
    """Create a deterministic hash from context dict."""
    if not context:
        return "empty"
    s = "|".join(f"{k}:{v}" for k, v in sorted(context.items()))
    return str(abs(hash(s)) % 1000000)


class QLearningEngine:
    """Tabular Q-Learning for optimal action selection."""

    def __init__(
        self,
        alpha: float = DEFAULT_ALPHA,
        gamma: float = DEFAULT_GAMMA,
        db_path: str | None = None,
    ):
        self.alpha = alpha
        self.gamma = gamma
        self._q_table = QTable()
        self._db_path = db_path
        self._load_from_db()

    def _load_from_db(self) -> None:
        if not self._db_path:
            return
        try:
            conn = sqlite3.connect(self._db_path)
            cur = conn.execute("SELECT state_action_json FROM q_learning WHERE id=1")
            row = cur.fetchone()
            if row:
                self._q_table.values = json.loads(row[0])
            conn.close()
        except Exception:
            pass

    def _save_to_db(self) -> None:
        if not self._db_path:
            return
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS q_learning (
                    id INTEGER PRIMARY KEY,
                    state_action_json TEXT
                )
            """)
            conn.execute(
                "INSERT OR REPLACE INTO q_learning (id, state_action_json) VALUES (1, ?)",
                (self._q_table.to_json(),),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def select_action(
        self,
        state: QState,
        available_actions: list[ActionType],
        epsilon: float = DEFAULT_EPSILON,
    ) -> ActionType:
        """Epsilon-greedy action selection."""
        import random

        if random.random() < epsilon:
            return random.choice(available_actions)

        best = available_actions[0]
        best_value = self._q_table.get(state, best)
        for action in available_actions:
            val = self._q_table.get(state, action)
            if val > best_value:
                best_value = val
                best = action
        return best

    def update(
        self,
        state: QState,
        action: ActionType,
        reward: float,
        next_state: QState | None = None,
    ) -> None:
        """Update Q-value using TD learning."""
        current_q = self._q_table.get(state, action)

        if next_state:
            max_next_q = max(self._q_table.get(next_state, a) for a in ActionType)
            target = reward + self.gamma * max_next_q
        else:
            target = reward

        td_error = target - current_q
        self._q_table.update(state, action, self.alpha * td_error)
        self._save_to_db()

    def get_q_values(self, state: QState) -> dict[str, float]:
        """Get all Q-values for a state."""
        return {action.value: self._q_table.get(state, action) for action in ActionType}


__all__ = [
    "ActionType",
    "QState",
    "QTable",
    "QLearningEngine",
    "DEFAULT_ALPHA",
    "DEFAULT_GAMMA",
    "DEFAULT_EPSILON",
]
