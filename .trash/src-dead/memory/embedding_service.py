"""
Embedding Service — Ported from N-Xyme MIND

Provides semantic embeddings using Ollama (local) or Sentence-Transformers.
Falls back to hash-based pseudo-embeddings if neither available.

Usage:
    service = EmbeddingService()
    result = service.embed("Hello world")
    print(result.dimensions)  # 768
"""

import hashlib
import logging
import math
import time
from typing import List, Optional

import httpx
import numpy as np

logger = logging.getLogger(__name__)

# Check if Sentence-Transformers available
SENTENCE_TRANSFORMERS_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    pass


class EmbeddingService:
    """
    Embedding service that uses:
    1. Ollama (nomic-embed-text) - primary
    2. Sentence-Transformers - fallback
    3. Hash-based pseudo-embedding - last resort
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
        self._http_client = None

        # Initialize Sentence-Transformers if available
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.st_encoder = SentenceTransformer(st_model)
                logger.info(f"EmbeddingService: Sentence-Transformers loaded ({st_model})")
            except Exception as e:
                logger.warning(f"EmbeddingService: Failed to load ST: {e}")

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        # Try Ollama first
        try:
            embedding = await self._embed_ollama(text)
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

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        results = []
        for text in texts:
            embedding = await self.embed(text)
            results.append(embedding)
        return results

    async def _embed_ollama(self, text: str) -> Optional[List[float]]:
        """Generate embedding using Ollama."""
        client = self._get_client()
        resp = await client.post(
            f"{self.ollama_url}/api/embed",
            json={"model": self.ollama_model, "input": text},
        )
        resp.raise_for_status()
        data = resp.json()
        embeddings = data.get("embeddings", [])
        if embeddings:
            return embeddings[0]
        return None

    def _embed_st(self, text: str) -> Optional[List[float]]:
        """Generate embedding using Sentence-Transformers."""
        if not self.st_encoder:
            return None
        embedding = self.st_encoder.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def _embed_hash(self, text: str) -> List[float]:
        """Generate hash-based pseudo-embedding (last resort)."""
        hash_bytes = hashlib.sha256(text.encode()).digest()
        # Convert to 768-dim vector
        embedding = []
        for i in range(768):
            byte_idx = i % len(hash_bytes)
            value = (hash_bytes[byte_idx] / 255.0) * 2 - 1  # Normalize to [-1, 1]
            embedding.append(value)
        return embedding

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

    async def close(self):
        """Cleanup HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()


def create_catalyst_embedding_service() -> EmbeddingService:
    """Create embedding service for Catalyst."""
    return EmbeddingService(
        ollama_url="http://localhost:11434",
        ollama_model="nomic-embed-text",
    )
