#!/usr/bin/env python3
"""Semantic Reranker Module — Improves precision of hybrid retrieval.

Implements:
- Base Reranker abstract class with rerank(query, candidates, top_k) method
- CohereReranker: Uses Cohere rerank API (primary, requires API key)
- HuggingFaceReranker: Uses cross-encoder model (fallback/local, no API key required)
- Config for API key, model selection, and fallback behavior

Usage:
    from packages.memory_store.reranker import CohereReranker, HuggingFaceReranker

    # Primary: Cohere (requires COHERE_API_KEY)
    reranker = CohereReranker()
    results = reranker.rerank(query, candidates, top_k=10)

    # Fallback: HuggingFace cross-encoder (no API key)
    hf_reranker = HuggingFaceReranker()
    results = hf_reranker.rerank(query, candidates, top_k=10)
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------------
# Data Classes
# -------------------------------------------------------------------------------


@dataclass
class RerankedResult:
    """A single reranked result with original and rerank scores."""

    source: str
    content: Any
    original_score: float = 0.0
    rerank_score: float = 0.0
    rank_change: int = 0  # Positive = moved up, negative = moved down
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RerankerConfig:
    """Configuration for reranker behavior."""

    # Provider selection
    primary_provider: str = "cohere"  # "cohere" or "huggingface"
    fallback_to_huggingface: bool = True

    # Cohere config
    cohere_api_key: Optional[str] = None
    cohere_model: str = "rerank-english-v2.0"

    # HuggingFace config
    hf_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    hf_device: str = (
        "cpu"  # "cpu", "cuda" - avoid "auto" to prevent torch device lookup errors
    )

    # Behavior
    max_candidates: int = 50  # Max candidates to rerank
    min_score_threshold: float = 0.0  # Skip low-confidence results


# -------------------------------------------------------------------------------
# Base Reranker
# -------------------------------------------------------------------------------


class Reranker(ABC):
    """Abstract base class for semantic rerankers."""

    def __init__(self, config: Optional[RerankerConfig] = None):
        """Initialize reranker with optional config."""
        self.config = config or RerankerConfig()
        self._name = self.__class__.__name__

    @abstractmethod
    def rerank(
        self, query: str, candidates: List[Any], top_k: int = 10
    ) -> List[RerankedResult]:
        """Rerank candidates based on query relevance.

        Args:
            query: The search query string.
            candidates: List of candidate objects (must have 'content' and 'score' attributes).
            top_k: Number of top results to return.

        Returns:
            List of RerankedResult objects sorted by rerank_score (descending).
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this reranker is available (dependencies installed, API key valid, etc.)."""
        pass

    def _get_content(self, candidate: Any) -> str:
        """Extract content string from candidate object."""
        if hasattr(candidate, "content"):
            return str(candidate.content)
        elif isinstance(candidate, dict):
            return str(candidate.get("content", ""))
        return str(candidate)

    def _get_original_score(self, candidate: Any) -> float:
        """Extract original relevance score from candidate."""
        if hasattr(candidate, "score"):
            return float(candidate.score)
        elif hasattr(candidate, "relevance_score"):
            return float(candidate.relevance_score)
        elif isinstance(candidate, dict):
            return float(candidate.get("score", candidate.get("relevance_score", 0.0)))
        return 0.0

    def _get_source(self, candidate: Any) -> str:
        """Extract source from candidate."""
        if hasattr(candidate, "source"):
            return str(candidate.source)
        elif isinstance(candidate, dict):
            return str(candidate.get("source", "unknown"))
        return "unknown"


# -------------------------------------------------------------------------------
# Cohere Reranker
# -------------------------------------------------------------------------------


class CohereReranker(Reranker):
    """Cohere rerank API implementation.

    Requires COHERE_API_KEY environment variable or pass via config.
    Model: rerank-english-v2.0 (default) or rerank-multilingual-v2.0
    """

    def __init__(self, config: Optional[RerankerConfig] = None):
        super().__init__(config)
        self._client = None
        self._api_key = self._resolve_api_key()

    def _resolve_api_key(self) -> Optional[str]:
        """Resolve API key from config or environment."""
        if self.config.cohere_api_key:
            return self.config.cohere_api_key
        return os.environ.get("COHERE_API_KEY")

    def _get_client(self):
        """Lazy-load Cohere client."""
        if self._client is not None:
            return self._client

        if not self._api_key:
            logger.warning("Cohere API key not available")
            return None

        try:
            import cohere

            self._client = cohere.Client(self._api_key)
            # Test connection
            self._client.chat("test")
            return self._client
        except ImportError:
            logger.warning("cohere SDK not installed")
            return None
        except Exception as e:
            logger.warning(f"Failed to initialize Cohere client: {e}")
            return None

    def rerank(
        self, query: str, candidates: List[Any], top_k: int = 10
    ) -> List[RerankedResult]:
        """Rerank using Cohere API."""
        if not candidates:
            return []

        client = self._get_client()
        if client is None:
            logger.info("Cohere unavailable, returning original ranking")
            return self._fallback_rerank(query, candidates, top_k)

        # Prepare documents
        documents = [self._get_content(c) for c in candidates]

        try:
            response = client.rerank(
                query=query,
                documents=documents,
                top_n=min(top_k, len(documents)),
                model=self.config.cohere_model,
                return_documents=False,
            )

            # Build reranked results
            original_order = {self._get_content(c): i for i, c in enumerate(candidates)}
            results: List[RerankedResult] = []

            for i, result in enumerate(response.results):
                doc_idx = result.index
                original_idx = original_order.get(documents[doc_idx], doc_idx)
                rank_change = original_idx - i

                original_candidate = candidates[doc_idx]
                results.append(
                    RerankedResult(
                        source=self._get_source(original_candidate),
                        content=self._get_content(original_candidate),
                        original_score=self._get_original_score(original_candidate),
                        rerank_score=result.relevance_score,
                        rank_change=rank_change,
                        metadata={
                            "reranker": "cohere",
                            "model": self.config.cohere_model,
                            "original_rank": original_idx + 1,
                            "new_rank": i + 1,
                        },
                    )
                )

            return results

        except Exception as e:
            logger.warning(f"Cohere rerank failed: {e}, falling back to original")
            return self._fallback_rerank(query, candidates, top_k)

    def _fallback_rerank(
        self, query: str, candidates: List[Any], top_k: int
    ) -> List[RerankedResult]:
        """Return original ordering when API fails."""
        results = []
        for i, candidate in enumerate(candidates):
            results.append(
                RerankedResult(
                    source=self._get_source(candidate),
                    content=self._get_content(candidate),
                    original_score=self._get_original_score(candidate),
                    rerank_score=self._get_original_score(candidate),
                    rank_change=0,
                    metadata={"reranker": "cohere_fallback"},
                )
            )
        return results[:top_k]

    def is_available(self) -> bool:
        """Check if Cohere reranker is available."""
        if not self._api_key:
            return False
        return self._get_client() is not None


# -------------------------------------------------------------------------------
# HuggingFace Cross-Encoder Reranker
# -------------------------------------------------------------------------------


class HuggingFaceReranker(Reranker):
    """HuggingFace cross-encoder reranker (fallback/local, no API key required).

    Uses sentence-transformers CrossEncoder for local reranking.
    Default model: cross-encoder/ms-marco-MiniLM-L-6-v2
    """

    def __init__(self, config: Optional[RerankerConfig] = None):
        super().__init__(config)
        self._model = None

    def _load_model(self):
        """Lazy-load cross-encoder model."""
        if self._model is not None:
            return

        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(
                self.config.hf_model,
                device=self.config.hf_device,
                max_length=512,
            )
            logger.info(f"Loaded HuggingFace cross-encoder: {self.config.hf_model}")
        except ImportError:
            logger.warning("sentence-transformers not installed")
            self._model = None
        except Exception as e:
            logger.warning(f"Failed to load cross-encoder model: {e}")
            self._model = None

    def rerank(
        self, query: str, candidates: List[Any], top_k: int = 10
    ) -> List[RerankedResult]:
        """Rerank using HuggingFace cross-encoder."""
        if not candidates:
            return []

        self._load_model()

        if self._model is None:
            logger.warning("Cross-encoder unavailable, returning original ranking")
            return self._fallback_rerank(candidates, top_k)

        # Prepare query-document pairs
        pairs = [(query, self._get_content(c)) for c in candidates]

        try:
            # Score all pairs
            scores = self._model.predict(pairs)

            # Track original order for rank change calculation
            results: List[RerankedResult] = []
            for i, (candidate, score) in enumerate(zip(candidates, scores)):
                results.append(
                    RerankedResult(
                        source=self._get_source(candidate),
                        content=self._get_content(candidate),
                        original_score=self._get_original_score(candidate),
                        rerank_score=float(score),
                        rank_change=0,  # Will calculate after sorting
                        metadata={
                            "reranker": "huggingface",
                            "model": self.config.hf_model,
                        },
                    )
                )

            # Sort by rerank score (descending)
            results.sort(key=lambda r: r.rerank_score, reverse=True)

            # Calculate rank changes
            original_order = {self._get_content(c): i for i, c in enumerate(candidates)}
            for new_rank, result in enumerate(results):
                original_rank = original_order.get(
                    self._get_content(result.content), new_rank
                )
                result.rank_change = original_rank - new_rank
                result.metadata["original_rank"] = original_rank + 1
                result.metadata["new_rank"] = new_rank + 1

            return results[:top_k]

        except Exception as e:
            logger.warning(f"Cross-encoder rerank failed: {e}")
            return self._fallback_rerank(candidates, top_k)

    def _fallback_rerank(
        self, candidates: List[Any], top_k: int
    ) -> List[RerankedResult]:
        """Return original ordering sorted by score when model fails."""
        results = []
        for i, candidate in enumerate(candidates):
            results.append(
                RerankedResult(
                    source=self._get_source(candidate),
                    content=self._get_content(candidate),
                    original_score=self._get_original_score(candidate),
                    rerank_score=self._get_original_score(candidate),
                    rank_change=0,
                    metadata={"reranker": "hf_fallback"},
                )
            )
        # Still sort by score in fallback
        results.sort(key=lambda r: r.rerank_score, reverse=True)
        return results[:top_k]

    def is_available(self) -> bool:
        """Check if HuggingFace reranker is available."""
        if self._model is None:
            self._load_model()
        return self._model is not None


# -------------------------------------------------------------------------------
# Factory and Utilities
# -------------------------------------------------------------------------------


def get_reranker(
    provider: Optional[str] = None, config: Optional[RerankerConfig] = None
) -> Reranker:
    """Get reranker instance based on provider preference.

    Args:
        provider: Preferred provider ("cohere" or "huggingface"). If None, uses config.
        config: Optional RerankerConfig. If not provided, uses defaults.

    Returns:
        Available Reranker instance (tries primary, falls back to HuggingFace).
    """
    cfg = config or RerankerConfig()
    provider = provider or cfg.primary_provider

    # Try primary provider
    if provider == "cohere":
        cohere_reranker = CohereReranker(cfg)
        if cohere_reranker.is_available():
            return cohere_reranker
        logger.info("Cohere not available, trying HuggingFace fallback")

    # Fallback to HuggingFace
    hf_reranker = HuggingFaceReranker(cfg)
    if hf_reranker.is_available():
        return hf_reranker

    # Last resort: return a dummy reranker that returns original order
    logger.warning("No reranker available, returning pass-through reranker")
    return PassThroughReranker(cfg)


class PassThroughReranker(Reranker):
    """Pass-through reranker that returns original order (when no reranker available)."""

    def rerank(
        self, query: str, candidates: List[Any], top_k: int = 10
    ) -> List[RerankedResult]:
        """Return original ordering."""
        results = []
        for i, candidate in enumerate(candidates):
            results.append(
                RerankedResult(
                    source=self._get_source(candidate),
                    content=self._get_content(candidate),
                    original_score=self._get_original_score(candidate),
                    rerank_score=self._get_original_score(candidate),
                    rank_change=0,
                    metadata={"reranker": "passthrough"},
                )
            )
        return results[:top_k]

    def is_available(self) -> bool:
        """Always available (pass-through)."""
        return True


# -------------------------------------------------------------------------------
# Module-level Singleton
# -------------------------------------------------------------------------------

_default_reranker: Optional[Reranker] = None


def get_default_reranker() -> Reranker:
    """Get or create default reranker instance."""
    global _default_reranker
    if _default_reranker is None:
        _default_reranker = get_reranker()
    return _default_reranker


def set_default_reranker(reranker: Reranker):
    """Set default reranker instance (for testing, swapping providers)."""
    global _default_reranker
    _default_reranker = reranker
