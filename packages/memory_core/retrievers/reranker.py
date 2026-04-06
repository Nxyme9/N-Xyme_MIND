#!/usr/bin/env python3
"""Cross-encoder reranker for retrieval results."""

from __future__ import annotations

import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Optional cross-encoder reranking using a small LLM or dedicated reranker model.
    
    Usage:
        reranker = CrossEncoderReranker(model="cross-encoder/ms-marco-MiniLM-L-6-v2")
        results = reranker.rerank("query", results, top_k=10)
    
    Note: Requires sentence-transformers package with cross-encoder support.
    """
    
    def __init__(self, model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model
        self._model = None
        self._available = False
    
    def _load_model(self):
        """Lazy-load the cross-encoder model."""
        if self._model is not None:
            return
        
        try:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.model_name)
            self._available = True
        except ImportError:
            logger.warning("sentence-transformers not installed. Cross-encoder reranking disabled.")
            self._available = False
        except Exception as e:
            logger.warning(f"Failed to load cross-encoder model: {e}")
            self._available = False
    
    def rerank(self, query: str, results: list, top_k: int = 10) -> list:
        """
        Rerank results using cross-encoder scoring.
        
        Args:
            query: Search query
            results: List of SearchResult objects with content
            top_k: Number of results to return
        
        Returns:
            Reranked results
        """
        if not results:
            return []
        
        self._load_model()
        
        if not self._available:
            # Fallback: return original results sorted by score
            return sorted(results, key=lambda r: getattr(r, 'score', 0), reverse=True)[:top_k]
        
        # Prepare pairs for cross-encoder
        pairs = [(query, getattr(r, 'content', '')) for r in results]
        
        # Score with cross-encoder
        scores = self._model.predict(pairs)
        
        # Update result scores
        for result, score in zip(results, scores):
            if hasattr(result, 'score'):
                result.score = float(score)
                if hasattr(result, 'metadata'):
                    result.metadata['reranker_score'] = float(score)
                    result.metadata['reranker'] = 'cross_encoder'
        
        # Sort and return top_k
        return sorted(results, key=lambda r: getattr(r, 'score', 0), reverse=True)[:top_k]
    
    def is_available(self) -> bool:
        """Check if cross-encoder reranking is available."""
        if self._model is None:
            self._load_model()
        return self._available