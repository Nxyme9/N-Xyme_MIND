#!/usr/bin/env python3
"""
Memory Embeddings — Semantic search for memory system.

Provides:
- embed_text(text): Generate embedding vector
- similarity_search(query, top_k): Find similar memories  
- batch_embed(documents): Bulk embedding for indexing

Uses Ollama (nomic-embed-text, 768 dims) as primary,
with Sentence-Transformers and hash fallbacks.
"""

import asyncio
import hashlib
import logging
import math
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Check availability
SENTENCE_TRANSFORMERS_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Embedding Engine
# ---------------------------------------------------------------------------

class EmbeddingEngine:
    """
    Synchronous wrapper for embedding generation.
    
    Uses Ollama (nomic-embed-text) as primary, falls back to
    Sentence-Transformers, then hash-based pseudo-embeddings.
    """
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "nomic-embed-text",
        st_model: str = "all-MiniLM-L6-v2",
    ):
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.st_model = st_model
        self.st_encoder = None
        self._sync_client = None
        
        # Lazy-load Sentence-Transformers on first fallback use
        self._st_loaded = False
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for text.
        
        Args:
            text: Input text to embed
            
        Returns:
            768-dimensional embedding vector
        """
        # Try Ollama first (sync via thread pool)
        try:
            embedding = self._embed_ollama_sync(text)
            if embedding:
                return embedding
        except Exception as e:
            logger.debug(f"Ollama embedding failed: {e}")
        
        # Fallback to Sentence-Transformers
        if self.st_encoder:
            try:
                embedding = self._embed_st(text)
                if embedding:
                    return embedding
            except Exception as e:
                logger.debug(f"ST embedding failed: {e}")
        
        # Last resort: hash-based pseudo-embedding
        return self._embed_hash(text)
    
    def _embed_ollama_sync(self, text: str) -> Optional[List[float]]:
        """Sync wrapper for Ollama API."""
        import httpx
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.ollama_model, "prompt": text},
            )
            resp.raise_for_status()
            data = resp.json()
            embedding = data.get("embedding")
            if embedding:
                return embedding
        return None
    
    def _embed_st(self, text: str) -> Optional[List[float]]:
        """Generate embedding using Sentence-Transformers, padded to 768-dim."""
        # Lazy-load on first use
        if not self._st_loaded:
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                try:
                    self.st_encoder = SentenceTransformer(self.st_model)
                    logger.info(f"EmbeddingEngine: Sentence-Transformers loaded ({self.st_model})")
                    self._st_loaded = True
                except Exception as e:
                    logger.warning(f"EmbeddingEngine: Failed to load ST: {e}")
                    return None
            else:
                return None

        if not self.st_encoder:
            return None
        embedding = self.st_encoder.encode(text, convert_to_numpy=True)
        vec = embedding.tolist()
        # Pad to 768-dim if ST model produces fewer dimensions
        if len(vec) < 768:
            vec = vec + [0.0] * (768 - len(vec))
        return vec[:768]  # Truncate if somehow larger
    
    def _embed_hash(self, text: str) -> List[float]:
        """Generate hash-based pseudo-embedding (last resort)."""
        hash_bytes = hashlib.sha256(text.encode()).digest()
        embedding = []
        for i in range(768):
            byte_idx = i % len(hash_bytes)
            value = (hash_bytes[byte_idx] / 255.0) * 2 - 1
            embedding.append(value)
        return embedding
    
    def batch_embed(self, documents: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple documents.
        
        Args:
            documents: List of text documents
            
        Returns:
            List of embedding vectors
        """
        return [self.embed_text(doc) for doc in documents]
    
    def similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(a * a for a in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)
    
    def similarity_search(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5,
    ) -> List[Tuple[int, float]]:
        """
        Find most similar documents to query.
        
        Args:
            query: Query text
            documents: List of document texts to search
            top_k: Number of results to return
            
        Returns:
            List of (index, score) tuples sorted by similarity
        """
        # Embed query
        query_vec = self.embed_text(query)
        
        # Embed all documents
        doc_vecs = self.batch_embed(documents)
        
        # Calculate similarities
        similarities = []
        for idx, doc_vec in enumerate(doc_vecs):
            score = self.similarity(query_vec, doc_vec)
            similarities.append((idx, score))
        
        # Sort by score descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]


# Global engine instance
_engine: Optional[EmbeddingEngine] = None


def get_engine() -> EmbeddingEngine:
    """Get the global embedding engine."""
    global _engine
    if _engine is None:
        _engine = EmbeddingEngine()
    return _engine


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

def embed_text(text: str) -> List[float]:
    """
    Generate embedding for text.
    
    Args:
        text: Input text
        
    Returns:
        768-dimensional embedding vector
    """
    return get_engine().embed_text(text)


def batch_embed(documents: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple documents.
    
    Args:
        documents: List of text documents
        
    Returns:
        List of embedding vectors
    """
    return get_engine().batch_embed(documents)


def similarity_search(
    query: str,
    documents: List[str],
    top_k: int = 5,
) -> List[Tuple[int, float]]:
    """
    Find most similar documents to query.
    
    Args:
        query: Query text
        documents: List of document texts to search
        top_k: Number of results
        
    Returns:
        List of (index, score) tuples
    """
    return get_engine().similarity_search(query, documents, top_k)


def similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    return get_engine().similarity(vec1, vec2)


# ---------------------------------------------------------------------------
# Vector Store (In-memory)
# ---------------------------------------------------------------------------

class VectorStore:
    """In-memory vector store for memory results."""
    
    def __init__(self, engine: Optional[EmbeddingEngine] = None):
        self.engine = engine or get_engine()
        self.documents: List[str] = []
        self.vectors: List[List[float]] = []
        self.metadata: List[dict] = []
    
    def add(self, text: str, metadata: Optional[dict] = None):
        """Add a document to the store."""
        vector = self.engine.embed_text(text)
        self.documents.append(text)
        self.vectors.append(vector)
        self.metadata.append(metadata or {})
    
    def search(self, query: str, top_k: int = 5) -> List[dict]:
        """Search the vector store."""
        query_vec = self.engine.embed_text(query)
        
        # Calculate similarities
        results = []
        for idx, vec in enumerate(self.vectors):
            score = self.engine.similarity(query_vec, vec)
            results.append({
                "index": idx,
                "text": self.documents[idx],
                "score": score,
                "metadata": self.metadata[idx],
            })
        
        # Sort and return top k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]


# ---------------------------------------------------------------------------
# Package Exports
# ---------------------------------------------------------------------------

__all__ = [
    "EmbeddingEngine",
    "VectorStore",
    "embed_text",
    "batch_embed",
    "similarity_search",
    "similarity",
    "get_engine",
]
