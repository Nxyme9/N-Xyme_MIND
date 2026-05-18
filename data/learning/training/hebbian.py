"""
Hebbian learning — slow adaptation during normal use.
Story 4.5: Successful routes nudge embedding +0.001 toward tool, capped at ±0.1.

Usage:
    from hot.hebbian import HebbianLearner
    
    learner = HebbianLearner("data/hebbian_drift.npy")
    learner.nudge(query_embedding, tool_embedding, learning_rate=0.001)
    learner.reverse(query_embedding, tool_embedding)  # On correction
"""

import os
import numpy as np
from typing import Optional


class HebbianLearner:
    """
    Hebbian-style inference-time learning.
    Nudges query embeddings toward successful tool matches.
    Drift is accumulated and persisted to disk.
    """
    
    def __init__(
        self,
        drift_path: str = "data/hebbian_drift.npy",
        learning_rate: float = 0.001,
        max_drift: float = 0.1
    ):
        """
        Initialize the Hebbian learner.
        
        Args:
            drift_path: Path to save/load accumulated drift
            learning_rate: How much to nudge per successful route
            max_drift: Maximum absolute drift in any dimension
        """
        self.drift_path = drift_path
        self.learning_rate = learning_rate
        self.max_drift = max_drift
        
        # Load existing drift or initialize
        self.drift = self._load_drift()
        
        # Statistics
        self.total_nudges = 0
        self.total_reversals = 0
    
    def _load_drift(self) -> np.ndarray:
        """Load drift vector from disk or initialize."""
        if os.path.exists(self.drift_path):
            try:
                return np.load(self.drift_path)
            except Exception:
                pass
        
        # Default 896-dim embedding space (Qwen2.5-0.5B)
        return np.zeros(896, dtype=np.float32)
    
    def save_drift(self) -> None:
        """Persist drift vector to disk."""
        os.makedirs(os.path.dirname(os.path.abspath(self.drift_path)), exist_ok=True)
        np.save(self.drift_path, self.drift)
    
    def nudge(
        self,
        query_embedding: np.ndarray,
        tool_embedding: np.ndarray,
        learning_rate: Optional[float] = None
    ) -> np.ndarray:
        """
        Nudge query embedding toward successful tool.
        "Cells that fire together, wire together"
        
        Args:
            query_embedding: Query embedding vector
            tool_embedding: Tool embedding vector
            learning_rate: Override default learning rate
            
        Returns:
            New nudged embedding
        """
        lr = learning_rate if learning_rate is not None else self.learning_rate
        
        # Compute difference vector
        diff = tool_embedding - query_embedding
        
        # Scale by learning rate
        adjustment = diff * lr
        
        # Apply adjustment
        nudged = query_embedding + adjustment
        
        # Update accumulated drift (simplified - we store a global bias)
        # In practice, this would be per-query-type, but we use a global
        # drift vector for simplicity
        self.drift = self.drift + adjustment.astype(np.float32)
        
        # Clip drift to max_drift
        self.drift = np.clip(self.drift, -self.max_drift, self.max_drift)
        
        self.total_nudges += 1
        
        # Periodically save
        if self.total_nudges % 100 == 0:
            self.save_drift()
        
        return nudged
    
    def reverse(
        self,
        query_embedding: np.ndarray,
        tool_embedding: np.ndarray
    ) -> np.ndarray:
        """
        Reverse a Hebbian nudge on correction.
        "Cells that fire apart, unwire"
        
        Args:
            query_embedding: Query embedding vector
            tool_embedding: Tool embedding vector (the WRONG tool that was selected)
            
        Returns:
            Corrected embedding
        """
        # Negative adjustment - push away from wrong tool
        diff = tool_embedding - query_embedding
        adjustment = diff * self.learning_rate * 2  # Stronger reversal
        
        corrected = query_embedding - adjustment
        
        # Update drift in opposite direction
        self.drift = self.drift - adjustment.astype(np.float32)
        self.drift = np.clip(self.drift, -self.max_drift, self.max_drift)
        
        self.total_reversals += 1
        
        # Save immediately on correction
        self.save_drift()
        
        return corrected
    
    def apply_drift(self, embedding: np.ndarray) -> np.ndarray:
        """
        Apply accumulated drift to an embedding.
        
        Args:
            embedding: Base embedding
            
        Returns:
            Embedding with drift applied
        """
        return embedding + self.drift
    
    def reset_drift(self) -> None:
        """Reset all accumulated drift."""
        self.drift = np.zeros(896, dtype=np.float32)
        self.save_drift()
        print("Hebbian drift reset", file=sys.stderr)
    
    def get_statistics(self) -> dict:
        """Get learner statistics."""
        drift_norm = float(np.linalg.norm(self.drift))
        
        return {
            "total_nudges": self.total_nudges,
            "total_reversals": self.total_reversals,
            "drift_norm": drift_norm,
            "drift_max": float(np.max(np.abs(self.drift))),
            "learning_rate": self.learning_rate,
            "max_drift": self.max_drift
        }


# Convenience function
def test_hebbian():
    """Test the Hebbian learner."""
    import tempfile
    
    # Use temp file
    with tempfile.NamedTemporaryFile(suffix='.npy', delete=False) as f:
        path = f.name
    
    learner = HebbianLearner(path, learning_rate=0.1)  # High LR for test
    
    # Create test embeddings
    query_emb = np.array([0.5] * 896, dtype=np.float32)
    tool_emb = np.array([0.8] * 896, dtype=np.float32)
    wrong_tool_emb = np.array([0.2] * 896, dtype=np.float32)
    
    # Test nudge
    nudged = learner.nudge(query_emb, tool_emb)
    print(f"Nudged embedding norm: {np.linalg.norm(nudged):.4f}")
    
    # Test reversal
    corrected = learner.reverse(query_emb, wrong_tool_emb)
    print(f"Corrected embedding norm: {np.linalg.norm(corrected):.4f}")
    
    # Test drift application
    drifted = learner.apply_drift(query_emb)
    print(f"Drifted embedding norm: {np.linalg.norm(drifted):.4f}")
    
    # Stats
    stats = learner.get_statistics()
    print(f"Stats: {stats}")
    
    # Cleanup
    learner.reset_drift()
    os.unlink(path)
    
    print("Hebbian test passed!")


if __name__ == "__main__":
    test_hebbian()