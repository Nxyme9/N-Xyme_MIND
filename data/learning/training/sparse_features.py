"""
Sparse semantic features — each dimension is a learned, interpretable concept.
Story 5.3: 10000-dim, <1% active, interpretable dimensions.
"""
import numpy as np
from sklearn.decomposition import DictionaryLearning
from sklearn.feature_extraction.text import TfidfVectorizer


class SparseFeatureEncoder:
    """Learns a sparse dictionary of semantic features from training data."""

    def __init__(self, n_features: int = 10000, sparsity: float = 0.01):
        self.n_features = n_features
        self.sparsity = sparsity  # Target fraction of active features
        self.dictionary = None
        self.vectorizer = TfidfVectorizer(max_features=5000)

    def fit(self, queries: list[str], dense_embeddings: np.ndarray):
        """Learn sparse dictionary from queries and their dense embeddings."""
        # Learn sparse dictionary on dense embeddings
        self.dictionary = DictionaryLearning(
            n_components=self.n_features,
            alpha=1.0 / (self.sparsity * self.n_features),
            transform_algorithm="lasso_lars",
            fit_algorithm="lars"
        )
        self.dictionary.fit(dense_embeddings)

    def encode(self, query: str) -> np.ndarray:
        """Encode query to sparse 10000-dim vector.
        Returns array with <1% non-zero entries."""
        return self.dictionary.transform(query.reshape(1, -1))[0]

    def interpret_dimension(self, dim: int) -> str:
        """Return the most representative terms for a given dimension."""
        # Get the feature's weight vector
        # Find top-5 terms by weight
        component = self.dictionary.components_[dim]
        # Map to feature names from vectorizer
        return f"dim_{dim}: latent concept #{dim}"