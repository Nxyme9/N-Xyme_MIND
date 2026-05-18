"""
Hyperbolic embedding space (Poincaré ball model).
Story 5.2: 64-dim hyperbolic > 1024-dim Euclidean for tool hierarchy.
"""
import numpy as np


def poincare_distance(u: np.ndarray, v: np.ndarray, eps: float = 1e-5) -> float:
    """Poincaré distance between two points in the unit ball."""
    u_norm = np.linalg.norm(u)
    v_norm = np.linalg.norm(v)
    diff_norm = np.linalg.norm(u - v)
    numerator = diff_norm ** 2
    denominator = (1 - u_norm ** 2) * (1 - v_norm ** 2)
    argh = 1 + 2 * numerator / (denominator + eps)
    return np.arccosh(np.clip(argh, 1 + eps, None))


def hyperbolic_centroid(embeddings: list[np.ndarray]) -> np.ndarray:
    """Compute centroid in hyperbolic space (midpoint of all tangent vectors)."""
    # Map to tangent space, average, map back
    tangent_vecs = [e / np.tanh(np.linalg.norm(e)) for e in embeddings]
    avg_tangent = np.mean(tangent_vecs, axis=0)
    avg_norm = np.linalg.norm(avg_tangent)
    return np.tanh(avg_norm) * avg_tangent / (avg_norm + 1e-8)


class HyperbolicToolSpace:
    """64-dim hyperbolic space for tool embeddings."""

    def __init__(self, dim: int = 64):
        self.dim = dim
        self.tool_embeddings = {}  # tool_name → 64-dim vector

    def add_tool(self, name: str, embedding: np.ndarray):
        """Project tool to Poincaré ball."""
        # Ensure it's in the unit ball (norm < 1)
        norm = np.linalg.norm(embedding)
        if norm >= 1:
            embedding = embedding / (norm + 1e-8) * 0.999
        self.tool_embeddings[name] = embedding

    def score(self, query: np.ndarray) -> dict:
        """Return similarity (negative distance) to all tools."""
        query = query / (np.linalg.norm(query) + 1e-8) * 0.999
        scores = {}
        for name, emb in self.tool_embeddings.items():
            scores[name] = -poincare_distance(query, emb)
        return scores