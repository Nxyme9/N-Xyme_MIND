"""Double DQN with Prioritized Experience Replay (PER).

This module provides enhanced RL capabilities:
- Double DQN: Reduces overestimation bias by using separate networks for action selection/evaluation
- PER: Samples experiences based on TD error magnitude for more efficient learning

Integration with routing optimizer in routing/optimizer.py.
"""

from __future__ import annotations

import logging
import random
from collections import deque
from dataclasses import dataclass
from typing import Any, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Try importing PyTorch for neural networks
TORCH_AVAILABLE = False
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.nn import functional as F

    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    optim = None
    F = None

# Configuration
DEFAULT_ALPHA = 0.6  # PER alpha (priority exponent)
DEFAULT_BETA = 0.4  # IS weight exponent (annealed to 1.0)
DEFAULT_EPSILON = 1e-6  # Small constant to avoid zero priority
DEFAULT_GAMMA = 0.99  # Discount factor
DEFAULT_TAU = 0.005  # Soft update target network parameter
DEFAULT_BUFFER_SIZE = 10000  # Replay buffer size
DEFAULT_BATCH_SIZE = 64  # Training batch size
DEFAULT_UPDATE_EVERY = 4  # Steps between updates
DEFAULT_TARGET_UPDATE = 1000  # Steps between target network updates


# ========== Sum Tree for PER ==========


class SumTree:
    """Sum Tree data structure for efficient priority-based sampling.

    Allows O(log n) sampling and O(log n) priority updates.
    """

    def __init__(self, capacity: int):
        """Initialize sum tree with given capacity.

        Args:
            capacity: Maximum number of experiences to store (must be power of 2)
        """
        # Ensure capacity is power of 2
        self.capacity = capacity
        self.tree = np.zeros(2 * capacity)
        self.size = 0
        self.write_index = 0

    def _propagate(self, index: int, change: float) -> None:
        """Propagate priority change up the tree."""
        parent = (index - 1) // 2
        self.tree[parent] += change
        if parent > 0:
            self._propagate(parent, change)

    def _retrieve(self, index: int, sum_value: float) -> int:
        """Find the leaf index corresponding to the given sum value."""
        left = 2 * index + 1
        right = left + 1

        if left >= len(self.tree):
            return index

        if sum_value <= self.tree[left]:
            return self._retrieve(left, sum_value)
        else:
            return self._retrieve(right, sum_value - self.tree[left])

    def add(self, priority: float, data: Any) -> None:
        """Add experience with given priority.

        Args:
            priority: Priority value (higher = sampled more often)
            data: Experience data to store
        """
        index = self.write_index + self.capacity

        # Store data (we maintain a separate array for this)
        if not hasattr(self, "data"):
            self.data = [None] * self.capacity
        self.data[self.write_index] = data

        # Update tree
        self._propagate(index, priority - self.tree[index])
        self.tree[index] = priority

        # Move to next position
        self.write_index = (self.write_index + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(self, sum_value: Optional[float] = None) -> Tuple[int, float, Any]:
        """Sample experience based on priority proportion.

        Args:
            sum_value: If None, random sample. If provided, sample at this value.

        Returns:
            Tuple of (index, priority, data)
        """
        if self.size == 0:
            raise ValueError("Cannot sample from empty tree")

        # Random sample if not provided
        if sum_value is None:
            sum_value = random.random() * self.tree[0]

        # Find the corresponding leaf
        index = self._retrieve(0, sum_value)
        leaf_index = index - self.capacity

        return leaf_index, self.tree[index], self.data[leaf_index]

    def update(self, index: int, priority: float) -> None:
        """Update priority for an existing experience.

        Args:
            index: Index of the experience to update
            priority: New priority value
        """
        tree_index = index + self.capacity
        change = priority - self.tree[tree_index]
        self.tree[tree_index] = priority
        self._propagate(tree_index, change)

    def total_priority(self) -> float:
        """Get total priority (root value)."""
        return self.tree[0]

    def __len__(self) -> int:
        return self.size


# ========== Prioritized Experience Replay Buffer ==========


@dataclass
class Experience:
    """Single experience in the replay buffer."""

    state: str  # State key (task|context)
    action: str  # Action taken
    reward: float  # Reward received
    next_state: Optional[str]  # Next state
    done: bool = False  # Whether episode is done
    td_error: float = 0.0  # TD error for priority


class PrioritizedReplayBuffer:
    """Prioritized Experience Replay buffer using Sum Tree.

    Samples experiences proportionally to their TD error magnitude.
    Uses Importance Sampling (IS) weights to correct for sampling bias.
    """

    def __init__(
        self,
        capacity: int = DEFAULT_BUFFER_SIZE,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
        epsilon: float = DEFAULT_EPSILON,
    ):
        """Initialize PER buffer.

        Args:
            capacity: Maximum number of experiences to store
            alpha: Priority exponent (0 = uniform, 1 = full priority)
            beta: IS weight exponent (0 = no correction, 1 = full correction)
            epsilon: Small constant to avoid zero priority
        """
        self.capacity = capacity
        self.alpha = alpha
        self.beta = beta
        self.epsilon = epsilon

        self.tree = SumTree(capacity)
        self.buffer: list[Experience] = []

        # For beta annealing
        self.beta_start = beta
        self.beta_frames = 100000
        self.frame = 0

        # Temporary storage for batch
        self._temp_indices: list[int] = []
        self._temp_priorities: list[float] = []

    def _get_priority(self, td_error: float) -> float:
        """Compute priority from TD error."""
        return (abs(td_error) + self.epsilon) ** self.alpha

    def add(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: Optional[str],
        done: bool = False,
    ) -> None:
        """Add experience to buffer.

        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state (None if terminal)
            done: Whether this is a terminal state
        """
        # Initial priority is max (to ensure all experiences are sampled eventually)
        priority = self.tree.total_priority() if len(self.tree) > 0 else 1.0

        experience = Experience(
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            done=done,
            td_error=abs(reward),  # Initial TD estimate
        )

        # Add to tree and buffer
        self.tree.add(priority, len(self.buffer))
        self.buffer.append(experience)

        # Remove old experiences if over capacity
        if len(self.buffer) > self.capacity:
            self.buffer.pop(0)

    def sample(self, batch_size: int = DEFAULT_BATCH_SIZE) -> Optional[dict]:
        """Sample batch of experiences using priorities.

        Args:
            batch_size: Number of experiences to sample

        Returns:
            Dictionary with batch data or None if not enough experiences
        """
        if len(self.tree) < batch_size:
            return None

        # Anneal beta
        self.frame += 1
        beta = min(
            1.0,
            self.beta_start + (1.0 - self.beta_start) * self.frame / self.beta_frames,
        )

        batch_states = []
        batch_actions = []
        batch_rewards = []
        batch_next_states = []
        batch_dones = []
        self._temp_indices = []
        self._temp_priorities = []

        # Sample experiences
        segment = self.tree.total_priority() / batch_size

        for i in range(batch_size):
            left = segment * i
            right = segment * (i + 1)

            # Random sample within segment
            sample_value = random.uniform(left, right)
            index, priority, _ = self.tree.sample(sample_value)

            # Get experience (convert tree index to buffer index)
            exp = self.buffer[index]

            batch_states.append(exp.state)
            batch_actions.append(exp.action)
            batch_rewards.append(exp.reward)
            batch_next_states.append(exp.next_state)
            batch_dones.append(exp.done)

            self._temp_indices.append(index)
            self._temp_priorities.append(priority)

        # Compute IS weights
        # weight_i = (N * p_i / sum(p))^(-beta)
        total_priority = sum(self._temp_priorities)
        weights = []
        for p in self._temp_priorities:
            if total_priority > 0:
                weight = (len(self.tree) * p / total_priority) ** (-beta)
            else:
                weight = 1.0
            weights.append(weight)

        # Normalize weights
        if weights:
            max_weight = max(weights)
            weights = [w / max_weight for w in weights]

        return {
            "states": batch_states,
            "actions": batch_actions,
            "rewards": batch_rewards,
            "next_states": batch_next_states,
            "dones": batch_dones,
            "indices": self._temp_indices,
            "weights": weights,
        }

    def update_priorities(self, indices: list[int], td_errors: list[float]) -> None:
        """Update priorities based on TD errors.

        Args:
            indices: Indices of experiences to update
            td_errors: New TD error values
        """
        for index, td_error in zip(indices, td_errors):
            if index < len(self.buffer):
                # Update stored TD error
                self.buffer[index].td_error = td_error
                # Update tree priority
                priority = self._get_priority(td_error)
                self.tree.update(index, priority)

    def __len__(self) -> int:
        return len(self.tree)


# ========== Neural Network for Double DQN ==========


class QNetwork(nn.Module if TORCH_AVAILABLE else object):
    """Q-Network for value function approximation.

    Uses PyTorch for neural network implementation.
    """

    def __init__(self, state_size: int, action_size: int, hidden_size: int = 128):
        """Initialize Q-Network.

        Args:
            state_size: Size of state embedding
            action_size: Number of possible actions
            hidden_size: Size of hidden layers
        """
        if not TORCH_AVAILABLE:
            self._available = False
            return

        super().__init__()
        self.fc1 = nn.Linear(state_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, action_size)
        self._available = True

    def forward(self, x: Any) -> Any:
        """Forward pass."""
        if not TORCH_AVAILABLE:
            return None
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        return self.fc3(x)


class DoubleDQN:
    """Double DQN with Prioritized Experience Replay.

    Uses two networks:
    - Online network: selects actions
    - Target network: evaluates actions

    This reduces overestimation bias present in standard DQN.
    """

    def __init__(
        self,
        state_size: int = 384,  # Embedding dimension
        action_size: int = 6,  # Number of actions
        hidden_size: int = 128,
        gamma: float = DEFAULT_GAMMA,
        tau: float = DEFAULT_TAU,
        update_every: int = DEFAULT_UPDATE_EVERY,
        target_update: int = DEFAULT_TARGET_UPDATE,
        buffer_size: int = DEFAULT_BUFFER_SIZE,
        batch_size: int = DEFAULT_BATCH_SIZE,
        learning_rate: float = 0.001,
        per_enabled: bool = True,
    ):
        """Initialize Double DQN.

        Args:
            state_size: Size of state embedding
            action_size: Number of possible actions
            hidden_size: Size of hidden layers
            gamma: Discount factor
            tau: Soft update parameter for target network
            update_every: Steps between updates
            target_update: Steps between target network hard updates
            buffer_size: Replay buffer size
            batch_size: Training batch size
            learning_rate: Learning rate for optimizer
            per_enabled: Whether to use PER (if False, uses uniform sampling)
        """
        self.gamma = gamma
        self.tau = tau
        self.update_every = update_every
        self.target_update = target_update
        self.batch_size = batch_size
        self.state_size = state_size
        self.action_size = action_size
        self.per_enabled = per_enabled

        # Training step counter
        self.step_counter = 0

        if not TORCH_AVAILABLE:
            logger.warning("PyTorch not available, DoubleDQN will use fallback mode")
            self._available = False
            return

        self._available = True

        # Initialize networks
        self.q_network = QNetwork(state_size, action_size, hidden_size)
        self.target_network = QNetwork(state_size, action_size, hidden_size)
        self.target_network.load_state_dict(self.q_network.state_dict())
        self.target_network.eval()

        # Optimizer
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=learning_rate)

        # Replay buffer
        if per_enabled:
            self.replay_buffer = PrioritizedReplayBuffer(capacity=buffer_size)
        else:
            # Simple uniform buffer if PER disabled
            self.replay_buffer = deque(maxlen=buffer_size)

    def _to_tensor(self, states: list) -> Any:
        """Convert states to PyTorch tensor."""
        if not TORCH_AVAILABLE or not self._available:
            return None

        # For string states, use one-hot or embedding lookup
        # This is a simplified version - in practice, use proper embeddings
        try:
            # Try to convert to numeric representation
            tensor = torch.tensor(
                [hash(s) % 1000 / 1000.0 for s in states], dtype=torch.float32
            ).unsqueeze(1)
            return tensor
        except Exception:
            return torch.zeros(len(states), self.state_size)

    def add_experience(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: Optional[str],
        done: bool = False,
    ) -> None:
        """Add experience to replay buffer.

        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state
            done: Whether episode is done
        """
        if not self._available:
            return

        if self.per_enabled:
            self.replay_buffer.add(state, action, reward, next_state, done)
        else:
            self.replay_buffer.append(
                Experience(
                    state=state,
                    action=action,
                    reward=reward,
                    next_state=next_state,
                    done=done,
                )
            )

    def _select_action(self, state: str, epsilon: float = 0.0) -> int:
        """Select action using online network (epsilon-greedy).

        Args:
            state: Current state
            epsilon: Exploration rate

        Returns:
            Selected action index
        """
        if not self._available:
            return 0

        if random.random() < epsilon:
            return random.randint(0, self.action_size - 1)

        with torch.no_grad():
            state_tensor = self._to_tensor([state])
            q_values = self.q_network(state_tensor)
            return q_values.argmax().item()

    def _soft_update(self) -> None:
        """Soft update target network parameters."""
        if not self._available:
            return

        for target_param, param in zip(
            self.target_network.parameters(), self.q_network.parameters()
        ):
            target_param.data.copy_(
                self.tau * param.data + (1.0 - self.tau) * target_param.data
            )

    def _hard_update(self) -> None:
        """Hard update target network (copy online network)."""
        if not self._available:
            return

        self.target_network.load_state_dict(self.q_network.state_dict())

    def update(self) -> Optional[dict]:
        """Perform one training update.

        Returns:
            Dictionary with loss information or None if no update performed
        """
        if not self._available:
            return None

        self.step_counter += 1

        # Check if we should update
        if self.step_counter % self.update_every != 0:
            return None

        # Get batch
        if self.per_enabled:
            batch = self.replay_buffer.sample(self.batch_size)
        else:
            # Uniform sampling
            if len(self.replay_buffer) < self.batch_size:
                return None

            batch_indices = random.sample(
                range(len(self.replay_buffer)), self.batch_size
            )
            experiences = [self.replay_buffer[i] for i in batch_indices]

            batch = {
                "states": [e.state for e in experiences],
                "actions": [e.action for e in experiences],
                "rewards": [e.reward for e in experiences],
                "next_states": [e.next_state for e in experiences],
                "dones": [e.done for e in experiences],
                "indices": batch_indices,
                "weights": [1.0] * self.batch_size,
            }

        if batch is None:
            return None

        # Convert to tensors
        states = self._to_tensor(batch["states"])
        actions = torch.tensor(
            [hash(a) % self.action_size for a in batch["actions"]],
            dtype=torch.long,
        )
        rewards = torch.tensor(batch["rewards"], dtype=torch.float32)
        dones = torch.tensor(batch["dones"], dtype=torch.float32)
        weights = torch.tensor(batch["weights"], dtype=torch.float32)

        # Compute current Q values
        current_q = self.q_network(states).gather(1, actions.unsqueeze(1)).squeeze()

        # Double DQN: use online network to select, target network to evaluate
        with torch.no_grad():
            # Action selection from online network
            next_actions = self.q_network(self._to_tensor(batch["next_states"])).argmax(
                dim=1
            )
            # Q-value from target network
            next_q = (
                self.target_network(self._to_tensor(batch["next_states"]))
                .gather(1, next_actions.unsqueeze(1))
                .squeeze()
            )

            # Target: r + gamma * Q(s', a'_selected)
            target_q = rewards + self.gamma * (1 - dones) * next_q

        # Compute TD errors for PER
        td_errors = torch.abs(current_q - target_q).detach().numpy()

        # Update priorities if using PER
        if self.per_enabled:
            self.replay_buffer.update_priorities(batch["indices"], td_errors.tolist())

        # Compute weighted loss
        loss = (weights * F.mse_loss(current_q, target_q, reduction="none")).mean()

        # Optimize
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), 1.0)
        self.optimizer.step()

        # Update target network periodically
        if self.step_counter % self.target_update == 0:
            self._hard_update()
        else:
            self._soft_update()

        return {
            "loss": loss.item(),
            "td_errors": td_errors.tolist(),
            "step": self.step_counter,
        }

    def select_action(
        self, state: str, available_actions: list[str], epsilon: float = 0.1
    ) -> str:
        """Select action for given state.

        Args:
            state: Current state
            available_actions: List of available action names
            epsilon: Exploration rate

        Returns:
            Selected action name
        """
        if not self._available:
            return available_actions[0] if available_actions else "hephaestus"

        action_idx = self._select_action(state, epsilon)

        # Map index to action name
        if action_idx < len(available_actions):
            return available_actions[action_idx]
        return available_actions[0]

    def get_q_value(self, state: str, action: str) -> float:
        """Get Q-value for state-action pair.

        Args:
            state: State
            action: Action

        Returns:
            Q-value estimate
        """
        if not self._available:
            return 0.0

        with torch.no_grad():
            state_tensor = self._to_tensor([state])
            q_values = self.q_network(state_tensor)
            action_idx = hash(action) % self.action_size
            return q_values[0, action_idx].item()

    @property
    def is_available(self) -> bool:
        """Check if Double DQN is available (requires PyTorch)."""
        return self._available


# ========== Integration with Routing Optimizer ==========


class DoubleDQNOptimizer:
    """Wrapper that integrates Double DQN with the routing optimizer.

    This class bridges the RL components with the existing routing system.
    """

    def __init__(self, optimizer: "RoutingWeightOptimizer"):
        """Initialize with existing routing optimizer.

        Args:
            optimizer: The existing RoutingWeightOptimizer to enhance
        """
        self._base_optimizer = optimizer

        # Initialize Double DQN
        self._ddqn = DoubleDQN(per_enabled=True)

        # Track learning
        self._learning_enabled = True

    def select_action(
        self,
        state: str,
        available_actions: list[str],
        level: int,
    ) -> Tuple[str, float]:
        """Select action using Double DQN or fallback to base optimizer.

        Args:
            state: Current state
            available_actions: Available actions
            level: Complexity level

        Returns:
            Tuple of (selected_action, confidence)
        """
        # Try Double DQN if available
        if self._ddqn.is_available and self._learning_enabled:
            epsilon = max(0.01, 0.5 / (1 + self._ddqn.step_counter / 1000))
            action = self._ddqn.select_action(state, available_actions, epsilon)

            # Get Q-value for confidence
            q_value = self._ddqn.get_q_value(state, action)
            confidence = min(1.0, abs(q_value) + 0.3)

            return action, confidence

        # Fallback to base optimizer
        recommendation = self._base_optimizer.get_optimal_agent(state, level)
        return recommendation.recommended_agent, recommendation.confidence

    def update(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: Optional[str],
        success: bool,
    ) -> None:
        """Update with experience.

        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state
            success: Whether task succeeded
        """
        if not self._ddqn.is_available or not self._learning_enabled:
            return

        # Convert reward to expected range
        normalized_reward = 1.0 if success else -1.0

        # Add to replay buffer
        self._ddqn.add_experience(
            state=state,
            action=action,
            reward=normalized_reward,
            next_state=next_state,
            done=not success,  # Consider failure as episode end
        )

        # Perform update
        self._ddqn.update()

    def enable_learning(self) -> None:
        """Enable learning updates."""
        self._learning_enabled = True

    def disable_learning(self) -> None:
        """Disable learning updates."""
        self._learning_enabled = False


# Forward reference for type hints


__all__ = [
    "SumTree",
    "Experience",
    "PrioritizedReplayBuffer",
    "QNetwork",
    "DoubleDQN",
    "DoubleDQNOptimizer",
    "DEFAULT_ALPHA",
    "DEFAULT_BETA",
    "DEFAULT_GAMMA",
    "DEFAULT_TAU",
    "DEFAULT_BUFFER_SIZE",
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_UPDATE_EVERY",
    "DEFAULT_TARGET_UPDATE",
]
