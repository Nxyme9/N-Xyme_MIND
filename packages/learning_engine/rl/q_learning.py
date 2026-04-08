"""Reinforcement Learning — Q-Learning implementation.

Tabular Q-Learning with TD updates for optimal action selection.
Q(s, a) = Q(s, a) + α * (r + γ * max_a' Q(s', a') - Q(s, a))

Vector-Enhanced: Uses embedding-based similarity clustering for state generalization.
"""

from __future__ import annotations

import json
import math
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

# Configuration
DEFAULT_ALPHA = 0.1  # Learning rate for Q-learning
DEFAULT_GAMMA = 0.9  # Discount factor
DEFAULT_EPSILON = 0.1  # Exploration rate (epsilon-greedy)
DEFAULT_SIMILARITY_THRESHOLD = 0.5  # Cosine similarity threshold for clustering


class ActionType(Enum):
    """Available actions for routing decisions."""

    EXPLORE = "explore"
    DELEGATE = "delegate"
    ORACLE = "oracle"
    LIBRARIAN = "librarian"
    HEPHAESTUS = "hephaestus"
    MULTIMODAL = "multimodal"


# FAISS availability check
FAISS_AVAILABLE = False
try:
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except ImportError:
    try:
        import numpy as np
    except ImportError:
        np = None


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

    def _to_key(self, state: QState | str) -> str:
        """Convert state to key. Accepts both QState objects and string keys.
        
        Args:
            state: QState object or pre-hashed string key
            
        Returns:
            String key for Q-table lookup
        """
        if isinstance(state, str):
            return state
        return state.to_key()

    def get(self, state: QState | str, action: ActionType) -> float:
        """Get Q-value for state-action pair.
        
        Args:
            state: QState object or string key
            action: Action to query
            
        Returns:
            Q-value (defaults to 0.0 if not found)
        """
        key = self._to_key(state)
        return self.values.get(key, {}).get(action.value, 0.0)

    def set(self, state: QState | str, action: ActionType, value: float) -> None:
        """Set Q-value for state-action pair.
        
        Args:
            state: QState object or string key
            action: Action to set
            value: Q-value to store
        """
        key = self._to_key(state)
        self.values[key][action.value] = value

    def update(self, state: QState | str, action: ActionType, delta: float) -> None:
        """Update Q-value with delta (TD learning).
        
        Args:
            state: QState object or string key
            action: Action to update
            delta: Value to add to Q-value
        """
        key = self._to_key(state)
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


# ========== Vector-Enhanced State Representation ==========

@dataclass
class VectorQState:
    """Embedding-based state representation for Q-learning.
    
    Uses FAISS index for efficient similarity-based state lookups.
    Allows Q-value generalization across semantically similar states.
    """
    
    task: str
    context_hash: str
    embedding: Optional[Any] = None  # numpy array
    
    def to_key(self) -> str:
        """Legacy key for backward compatibility."""
        return f"{self.task}|{self.context_hash}"
    
    @staticmethod
    def from_context(task: str, context: dict[str, Any], embedding: Optional[Any] = None) -> "VectorQState":
        """Create VectorQState from task and context."""
        ctx_hash = _hash_context(context)
        return VectorQState(task=task, context_hash=ctx_hash[:16], embedding=embedding)
    
    def get_embedding(self) -> Optional[Any]:
        """Get cached embedding or encode from task."""
        if self.embedding is not None:
            return self.embedding
        return None


class VectorStateIndex:
    """FAISS-based index for vector state lookups with similarity clustering."""
    
    def __init__(
        self,
        dimension: int = 384,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ):
        self.dimension = dimension
        self.similarity_threshold = similarity_threshold
        
        # FAISS index for approximate nearest neighbors
        self._index = None
        self._state_keys: list[str] = []  # Maps index positions to state keys
        self._state_embeddings: dict[str, Any] = {}  # key -> embedding
        self._pending_embeddings: list[Any] = []  # Queue for training
        
        if FAISS_AVAILABLE and np is not None:
            try:
                # Use IndexFlatIP for inner product (cosine with normalized vectors)
                # This is an exact search index - no training needed
                self._index = faiss.IndexFlatIP(dimension)
            except Exception:
                pass
    
    def add_state(self, state_key: str, embedding: Any) -> None:
        """Add a state with its embedding to the index."""
        if self._index is None:
            return
            
        # Normalize embedding for cosine similarity
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        # Convert to float32 for FAISS
        embedding = embedding.astype(np.float32)
        
        self._index.add(embedding.reshape(1, -1))
        self._state_keys.append(state_key)
        self._state_embeddings[state_key] = embedding
    
    def find_similar(self, embedding: Any, k: int = 5) -> list[tuple[str, float]]:
        """Find k most similar states to the given embedding.
        
        Returns:
            List of (state_key, similarity_score) tuples
        """
        if self._index is None or len(self._state_keys) == 0:
            return []
        
        # Normalize query embedding
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        # Convert to float32 for FAISS
        query = embedding.astype(np.float32).reshape(1, -1)
        
        # For exact search, k is limited by number of states
        actual_k = min(k, len(self._state_keys))
        distances, indices = self._index.search(query, actual_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= 0 and dist >= self.similarity_threshold:
                state_key = self._state_keys[idx]
                results.append((state_key, float(dist)))
        
        return results
    
    def get_state_embedding(self, state_key: str) -> Optional[Any]:
        """Get embedding for a specific state key."""
        return self._state_embeddings.get(state_key)
    
    def train(self, embeddings: list[Any]) -> None:
        """Train the index with a batch of embeddings (for IVF indices)."""
        # Flat index doesn't need training - no-op for backward compatibility
        pass
    
    @property
    def is_ready(self) -> bool:
        """Check if index is ready for queries."""
        return self._index is not None and len(self._state_keys) > 0
    
    def __len__(self) -> int:
        return len(self._state_keys)
    
    def add_state(self, state_key: str, embedding: Any) -> None:
        """Add a state with its embedding to the index."""
        if self._index is None:
            return
            
        # Normalize embedding for cosine similarity
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        # Convert to float32 for FAISS
        embedding = embedding.astype(np.float32)
        
        self._index.add(embedding.reshape(1, -1))
        self._state_keys.append(state_key)
        self._state_embeddings[state_key] = embedding
    
    def add_state(self, state_key: str, embedding: Any) -> None:
        """Add a state with its embedding to the index."""
        if self._index is None:
            return
            
        # Normalize embedding for cosine similarity
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        # Convert to float32 for FAISS
        embedding = embedding.astype(np.float32)
        
        self._index.add(embedding.reshape(1, -1))
        self._state_keys.append(state_key)
        self._state_embeddings[state_key] = embedding
    
    def find_similar(self, embedding: Any, k: int = 5) -> list[tuple[str, float]]:
        """Find k most similar states to the given embedding.
        
        Returns:
            List of (state_key, similarity_score) tuples
        """
        if self._index is None or len(self._state_keys) == 0:
            return []
        
        # Normalize query embedding
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        # Convert to float32 for FAISS
        query = embedding.astype(np.float32).reshape(1, -1)
        
        # For exact search, k is limited by number of states
        actual_k = min(k, len(self._state_keys))
        distances, indices = self._index.search(query, actual_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= 0 and dist >= self.similarity_threshold:
                state_key = self._state_keys[idx]
                results.append((state_key, float(dist)))
        
        return results
    
    def get_state_embedding(self, state_key: str) -> Optional[Any]:
        """Get embedding for a specific state key."""
        return self._state_embeddings.get(state_key)
    
    def train(self, embeddings: list[Any]) -> None:
        """Train the index with a batch of embeddings (for IVF indices)."""
        if self._index is None or not embeddings:
            return
        
        # Only train if index supports training
        if hasattr(self._index, 'is_trained') and not self._index.is_trained:
            # Stack and normalize embeddings
            emb_list = []
            for e in embeddings:
                if e is not None and np.linalg.norm(e) > 0:
                    emb_list.append(e / np.linalg.norm(e))
            
            if emb_list:
                emb_matrix = np.vstack(emb_list).astype(np.float32)
                self._index.train(emb_matrix)
    
    @property
    def is_ready(self) -> bool:
        """Check if index is ready for queries."""
        return self._index is not None and len(self._state_keys) > 0
    
    def __len__(self) -> int:
        return len(self._state_keys)


class QLearningEngine:
    """Tabular Q-Learning for optimal action selection with EWC regularization.
    
    Enhanced with vector-based state representation for similarity clustering.
    Uses FAISS index for efficient approximate nearest neighbor lookups.
    """

    def __init__(
        self,
        alpha: float = DEFAULT_ALPHA,
        gamma: float = DEFAULT_GAMMA,
        db_path: str | None = None,
        ewc_lambda: float = 0.1,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        use_vector_states: bool = True,
    ):
        self.alpha = alpha
        self.gamma = gamma
        self.ewc_lambda = ewc_lambda
        self.similarity_threshold = similarity_threshold
        self.use_vector_states = use_vector_states
        self._q_table = QTable()
        self._db_path = db_path
        
        # Vector state index for similarity-based lookups
        self._vector_index: Optional[VectorStateIndex] = None
        self._embedding_cache = None
        
        # Check if we can use vector states
        self._vector_enabled = False
        if use_vector_states and FAISS_AVAILABLE and np is not None:
            try:
                # Try to initialize embedding cache
                from ..embeddings.model_cache import get_embedding_cache
                self._embedding_cache = get_embedding_cache()
                self._vector_index = VectorStateIndex(
                    dimension=384,  # Matches EmbeddingCache.DIMENSION
                    similarity_threshold=similarity_threshold,
                )
                self._vector_enabled = True
            except Exception:
                self._vector_enabled = False

        # EWC integration (optional - graceful if import fails)
        self._ewc = None
        try:
            from ..meta.ewc import EWCEngine

            self._ewc = EWCEngine()
        except ImportError:
            pass

        self._load_from_db()
        
        # Rebuild vector index from existing Q-table states if enabled
        if self._vector_enabled and self._vector_index:
            self._rebuild_vector_index()

    def _rebuild_vector_index(self) -> None:
        """Rebuild vector index from existing Q-table states."""
        if not self._vector_enabled or not self._vector_index or not self._embedding_cache:
            return
        
        # Get all unique tasks from Q-table
        tasks = set()
        for state_key in self._q_table.values.keys():
            task = state_key.split("|")[0] if "|" in state_key else state_key
            if task:
                tasks.add(task)
        
        # Encode all tasks and add to index with task-only key
        for task in tasks:
            try:
                embedding = self._embedding_cache.encode(task)
                # Use task-only key to match similarity-based lookups
                self._vector_index.add_state(task, embedding)
            except Exception:
                continue

    def _get_task_from_state(self, state: QState | str) -> str:
        """Extract the task component from a QState or string key."""
        if isinstance(state, str):
            # Extract task from string key (format: "task|context_hash")
            return state.split("|")[0] if "|" in state else state
        return state.task
    
    def _get_embedding(self, task: str) -> Optional[Any]:
        """Get embedding for a task using the cache."""
        if not self._vector_enabled or not self._embedding_cache:
            return None
        try:
            return self._embedding_cache.encode(task)
        except Exception:
            return None

    def get_similar_states(self, state: QState | str, k: int = 5) -> list[tuple[str, float]]:
        """Find k most similar states to the given state based on embedding.
        
        Args:
            state: The query state (QState or string key)
            k: Number of similar states to return
            
        Returns:
            List of (task_key, similarity_score) tuples
        """
        if not self._vector_enabled or not self._vector_index:
            return []
        
        # Use task-only for similarity lookup
        task = self._get_task_from_state(state)
        embedding = self._get_embedding(task)
        if embedding is None:
            return []
        
        return self._vector_index.find_similar(embedding, k)

    def get_generalized_q_value(
        self,
        state: QState | str,
        action: ActionType,
    ) -> float:
        """Get Q-value with generalization across similar states.
        
        If no exact state match exists, uses similarity-based lookup
        to find Q-values from semantically similar states.
        """
        # First try exact match
        exact_q = self._q_table.get(state, action)
        
        # If no Q-values exist for this state, try generalization
        if exact_q == 0.0 and self._vector_enabled:
            similar_states = self.get_similar_states(state, k=3)
            if similar_states:
                # Collect Q-values from all Q-table entries that match similar tasks
                task = self._get_task_from_state(state)
                total_weight = 0.0
                weighted_q = 0.0
                
                for similar_task, similarity in similar_states:
                    # Find all Q-table entries that start with this similar task
                    action_key = action.value
                    for qtable_key, actions_dict in self._q_table.values.items():
                        # Check if this Q-table key matches the similar task
                        qtable_task = qtable_key.split("|")[0] if "|" in qtable_key else qtable_key
                        if qtable_task == similar_task:
                            task_q = actions_dict.get(action_key, 0.0)
                            if task_q != 0.0:
                                weighted_q += similarity * task_q
                                total_weight += similarity
                
                if total_weight > 0:
                    return weighted_q / total_weight
        
        return exact_q

    def update_with_embedding(
        self,
        state: QState | str,
        action: ActionType,
        reward: float,
        next_state: QState | str | None = None,
        task_id: str | None = None,
    ) -> None:
        """Update Q-value and optionally add state to vector index."""
        # Extract task for vector index - handle both QState and string
        task = self._get_task_from_state(state)
        
        # Add state to vector index if enabled
        if self._vector_enabled and self._vector_index and self._embedding_cache:
            embedding = self._get_embedding(task)
            if embedding is not None:
                # Use task-only key for similarity-based lookups
                self._vector_index.add_state(task, embedding)
        
        # Call standard update
        self.update(state, action, reward, next_state, task_id)

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
        state: QState | str,
        available_actions: list[ActionType],
        epsilon: float = DEFAULT_EPSILON,
        use_generalization: bool = True,
    ) -> ActionType:
        """Epsilon-greedy action selection with optional generalization.
        
        Args:
            state: Current state (QState or string key)
            available_actions: List of available actions
            epsilon: Exploration rate
            use_generalization: If True, use similarity-based Q-value generalization
        """
        import random

        if random.random() < epsilon:
            return random.choice(available_actions)

        best = available_actions[0]
        
        if use_generalization and self._vector_enabled:
            best_value = self.get_generalized_q_value(state, best)
            for action in available_actions[1:]:
                val = self.get_generalized_q_value(state, action)
                if val > best_value:
                    best_value = val
                    best = action
        else:
            best_value = self._q_table.get(state, best)
            for action in available_actions[1:]:
                val = self._q_table.get(state, action)
                if val > best_value:
                    best_value = val
                    best = action
        return best

    def update(
        self,
        state: QState | str,
        action: ActionType,
        reward: float,
        next_state: QState | str | None = None,
        task_id: str | None = None,
    ) -> None:
        """Update Q-value using TD learning with EWC regularization.

        Args:
            state: Current state (QState or string key)
            action: Action taken
            reward: Reward received
            next_state: Next state (for TD target)
            task_id: Optional task ID for EWC Fisher update
        """
        current_q = self._q_table.get(state, action)

        if next_state:
            max_next_q = max(self._q_table.get(next_state, a) for a in ActionType)
            target = reward + self.gamma * max_next_q
        else:
            target = reward

        td_error = target - current_q

        # EWC regularization: penalize changes to important Q-values
        ewc_penalty = 0.0
        if self._ewc and task_id:
            # Compute penalty based on current Q-value
            ewc_penalty = self._ewc.compute_penalty({"q_value": current_q})
            # Apply EWC regularization to TD update
            td_error = td_error - self.ewc_lambda * ewc_penalty

        self._q_table.update(state, action, self.alpha * td_error)

        # Update Fisher information after task completion
        if self._ewc and task_id:
            self._ewc.update_after_task({"q_value": current_q}, [{"reward": reward}])

        self._save_to_db()

    def get_q_values(self, state: QState | str) -> dict[str, float]:
        """Get all Q-values for a state.
        
        Args:
            state: QState object or string key
            
        Returns:
            Dictionary mapping action values to Q-values
        """
        return {action.value: self._q_table.get(state, action) for action in ActionType}


__all__ = [
    "ActionType",
    "QState",
    "QTable",
    "VectorQState",
    "VectorStateIndex",
    "QLearningEngine",
    "FAISS_AVAILABLE",
    "DEFAULT_ALPHA",
    "DEFAULT_GAMMA",
    "DEFAULT_EPSILON",
    "DEFAULT_SIMILARITY_THRESHOLD",
]
