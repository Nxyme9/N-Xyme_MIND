#!/usr/bin/env python3
"""
FAISS Index Manager - Holographic Memory MVP
Manages FAISS GPU index for session vector search.
"""
import os
import json
import logging
import numpy as np
from typing import List, Tuple, Optional, Dict
import threading

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEFAULT_INDEX_PATH = "data/memory/vectors/index.faiss"
DEFAULT_DIM = 768
DEFAULT_METRIC = "IP"  # Inner Product for cosine similarity (with normalized vectors)


class FAISSManager:
    """FAISS index manager with GPU support and session metadata."""

    def __init__(self, index_path: str = DEFAULT_INDEX_PATH, dim: int = DEFAULT_DIM):
        self.index_path = index_path
        self.dim = dim
        self._index = None
        self._session_ids: List[str] = []
        self._lock = threading.Lock()
        self._use_gpu = False

        # Try to import FAISS
        self._faiss_available = False
        self._gpu_resources = None
        try:
            import faiss
            self._faiss = faiss
            self._faiss_available = True
            logger.info("FAISS imported successfully")
        except ImportError:
            logger.warning("FAISS not available, using numpy fallback")
            self._faiss = None

    @property
    def is_loaded(self) -> bool:
        return self._index is not None

    def _init_gpu(self) -> bool:
        """Try to initialize GPU resources."""
        if not self._faiss_available:
            return False

        try:
            # Try to get GPU resources
            res = faiss.StandardGpuResources()
            self._gpu_resources = res
            self._use_gpu = True
            logger.info("GPU resources initialized")
            return True
        except Exception as e:
            logger.warning(f"GPU initialization failed: {e}, using CPU")
            self._use_gpu = False
            return False

    def load_index(self) -> bool:
        """Load existing FAISS index from disk, or create new one."""
        with self._lock:
            if self._index is not None:
                return True

            if not self._faiss_available:
                logger.warning("FAISS not available, cannot load index")
                return False

            # Try to load existing index
            if os.path.exists(self.index_path):
                try:
                    self._index = faiss.read_index(self.index_path)
                    logger.info(f"Loaded existing index from {self.index_path}")

                    # Load session IDs if available
                    ids_path = self.index_path.replace(".faiss", ".ids.json")
                    if os.path.exists(ids_path):
                        with open(ids_path, 'r') as f:
                            self._session_ids = json.load(f)
                        logger.info(f"Loaded {len(self._session_ids)} session IDs")

                    return True
                except Exception as e:
                    logger.warning(f"Failed to load index: {e}")

            # Create new index
            try:
                # Use Inner Product for cosine similarity (vectors must be normalized)
                # Fallback to L2 if IP not available
                try:
                    index = faiss.IndexFlatIP(self.dim)
                except Exception:
                    logger.warning("IndexFlatIP not available, using IndexFlatL2")
                    index = faiss.IndexFlatL2(self.dim)

                # Try to use GPU
                if self._gpu_resources is None:
                    self._init_gpu()

                if self._use_gpu and self._gpu_resources:
                    self._index = faiss.index_cpu_to_gpu(self._gpu_resources, 0, index)
                    logger.info("Created new GPU index")
                else:
                    self._index = index
                    logger.info("Created new CPU index")

                return True
            except Exception as e:
                logger.error(f"Failed to create index: {e}")
                return False

    def add_vector(self, session_id: str, embedding: np.ndarray) -> bool:
        """Add a vector to the index with session_id tracking."""
        with self._lock:
            # Ensure index is loaded
            if self._index is None:
                if not self.load_index():
                    logger.error("Cannot add vector - index not available")
                    return False

            # Convert to numpy and ensure correct dtype
            if isinstance(embedding, list):
                vec = np.array(embedding, dtype=np.float32)
            else:
                vec = embedding.astype(np.float32)

            # Reshape if needed
            if vec.ndim == 1:
                vec = vec.reshape(1, -1)

            # Verify dimension
            if vec.shape[1] != self.dim:
                logger.error(f"Vector dimension {vec.shape[1]} doesn't match index dimension {self.dim}")
                return False

            # Normalize for cosine similarity if using IP
            if hasattr(self._index, 'is_ip') and self._index.is_ip:
                faiss.normalize_L2(vec)

            try:
                self._index.add(vec)
                self._session_ids.append(session_id)
                logger.debug(f"Added vector for session: {session_id}, total: {self._index.ntotal}")
                return True
            except Exception as e:
                logger.error(f"Failed to add vector: {e}")
                return False

    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple[str, float]]:
        """Search for k most similar sessions."""
        with self._lock:
            if self._index is None:
                logger.warning("Index not loaded, attempting to load...")
                if not self.load_index():
                    return []

            # Convert and normalize query
            if isinstance(query_embedding, list):
                vec = np.array(query_embedding, dtype=np.float32)
            else:
                vec = query_embedding.astype(np.float32)

            if vec.ndim == 1:
                vec = vec.reshape(1, -1)

            # Normalize for cosine similarity
            if hasattr(self._index, 'is_ip') and self._index.is_ip:
                faiss.normalize_L2(vec)

            try:
                # Search - get k+1 to handle potential edge cases
                search_k = min(k + 1, self._index.ntotal)
                if search_k == 0:
                    return []

                distances, indices = self._index.search(vec, search_k)

                results = []
                for dist, idx in zip(distances[0], indices[0]):
                    if idx >= 0 and idx < len(self._session_ids):
                        session_id = self._session_ids[idx]
                        # Convert L2 distance to similarity score (approximate)
                        # For L2: lower is better, convert to similarity
                        # For IP: higher is better (already similarity)
                        if hasattr(self._index, 'is_ip') and self._index.is_ip:
                            score = float(dist)
                        else:
                            score = 1.0 / (1.0 + float(dist))
                        results.append((session_id, score))

                return results[:k]
            except Exception as e:
                logger.error(f"Search failed: {e}")
                return []

    def persist(self) -> bool:
        """Save index to disk."""
        with self._lock:
            if self._index is None:
                logger.warning("Nothing to persist - index not loaded")
                return False

            if not self._faiss_available:
                logger.warning("FAISS not available, cannot persist")
                return False

            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

                # For GPU index, need to move to CPU first
                index_to_save = self._index
                if self._use_gpu and hasattr(self._index, 'gpu_to_cpu'):
                    index_to_save = faiss.index_gpu_to_cpu(self._index)

                faiss.write_index(index_to_save, self.index_path)
                logger.info(f"Saved index to {self.index_path}")

                # Save session IDs
                ids_path = self.index_path.replace(".faiss", ".ids.json")
                with open(ids_path, 'w') as f:
                    json.dump(self._session_ids, f)
                logger.info(f"Saved {len(self._session_ids)} session IDs to {ids_path}")

                return True
            except Exception as e:
                logger.error(f"Failed to persist index: {e}")
                return False

    def get_stats(self) -> Dict:
        """Get index statistics."""
        with self._lock:
            return {
                "loaded": self._index is not None,
                "vector_count": self._index.ntotal if self._index else 0,
                "dimension": self.dim,
                "gpu_enabled": self._use_gpu,
                "session_count": len(self._session_ids)
            }


# Global singleton for the MCP tool to use
_manager: Optional[FAISSManager] = None
_manager_lock = threading.Lock()


def get_manager() -> FAISSManager:
    """Get or create the global FAISS manager."""
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = FAISSManager()
        return _manager


def initialize_index(force_rebuild: bool = False) -> bool:
    """Initialize the FAISS index, optionally rebuilding from session summaries."""
    manager = get_manager()

    # Check if already loaded
    if manager.is_loaded and not force_rebuild:
        return True

    # Try to load existing index
    if not force_rebuild and manager.load_index():
        if manager.is_loaded:
            return True

    # Need to rebuild from session summaries
    logger.info("Building FAISS index from session summaries...")

    # Import here to avoid requiring FAISS at module load time
    try:
        import faiss
    except ImportError:
        logger.error("FAISS not available. Install with: pip install faiss-gpu")
        return False

    # Load session summaries to get embeddings
    summaries_path = "data/memory/synapses/session-summaries.jsonl"
    if not os.path.exists(summaries_path):
        logger.error(f"Session summaries not found: {summaries_path}")
        return False

    # Read summaries and build index
    # We'll use simple text-based embeddings for now
    try:
        summaries = []
        with open(summaries_path, 'r') as f:
            for line in f:
                if line.strip():
                    summaries.append(json.loads(line))

        logger.info(f"Loaded {len(summaries)} session summaries")

        # For now, create placeholder embeddings (the actual implementation
        # would use the embedding server to encode session summaries)
        # This is a simplified version - in production, we'd encode each session

        # Create a simple hash-based embedding for each session
        for summary in summaries:
            session_id = summary.get("session_id", "unknown")
            # Create a simple deterministic embedding based on session content
            # In production, use the embedding server for actual embeddings
            content = json.dumps(summary, sort_keys=True)
            h = hashlib.md5(content.encode()).digest()
            vec = np.frombuffer(h * (DEFAULT_DIM // 16 + 1), dtype=np.float32)[:DEFAULT_DIM]
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm

            manager.add_vector(session_id, vec)

        # Persist the new index
        manager.persist()
        logger.info(f"Built index with {manager._index.ntotal if manager._index else 0} vectors")

        return True
    except Exception as e:
        logger.error(f"Failed to build index: {e}")
        return False


if __name__ == "__main__":
    # Test script
    print("FAISS Manager - Holographic Memory MVP")
    print("=" * 50)

    mgr = get_manager()
    print(f"Initial stats: {mgr.get_stats()}")

    if mgr.load_index():
        print(f"Loaded index: {mgr.get_stats()}")

        # Test search
        test_vec = np.random.randn(DEFAULT_DIM).astype(np.float32)
        test_vec = test_vec / np.linalg.norm(test_vec)
        results = mgr.search(test_vec, k=3)
        print(f"Test search results: {results[:3]}")
    else:
        print("Index not available")