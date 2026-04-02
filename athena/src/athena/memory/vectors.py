"""
athena.memory.vectors — Thread-Safe v1.2

Optimizations:
    - Thread-Local Clients: Prevents httpx connection state corruption in parallel loops.
    - Atomic Cache: PersistentEmbeddingCache now uses Locks and Atomic Writes.
"""

import os
import sys
import hashlib
import json
import threading
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional

# Global cache instance
_embedding_cache = None
_embedding_cache_lock = threading.Lock()


def get_embedding_cache():
    global _embedding_cache
    with _embedding_cache_lock:
        if _embedding_cache is None:
            _embedding_cache = PersistentEmbeddingCache()
        return _embedding_cache


# Thread-local storage for Supabase clients
_thread_local = threading.local()


def get_client() -> Any:
    """Returns a thread-safe Supabase client instance, or None for Ollama provider."""
    # Check if we're using Ollama provider (no Supabase needed)
    provider = os.getenv("EMBEDDING_PROVIDER", "gemini").lower()
    if provider == "ollama":
        return None

    if not hasattr(_thread_local, "client"):
        try:
            from supabase import create_client
            from dotenv import load_dotenv

            load_dotenv()

            url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            if not url or not key:
                raise ValueError("Supabase credentials missing in environment.")
            _thread_local.client = create_client(url, key)
        except ImportError:
            # Supabase not installed - return None for graceful fallback
            return None
    return _thread_local.client


class PersistentEmbeddingCache:
    """JSON-backed persistent cache with Thread-Safe Atomic Writes and Background Saving."""

    def __init__(self, filename="embedding_cache.json"):
        # Correct pathing via project discovery
        from athena.core.config import AGENT_DIR

        self.cache_file = AGENT_DIR / "state" / filename
        self.lock = threading.Lock()
        self._cache: Dict[str, List[float]] = {}
        self._dirty = False
        self._load()

    def _load(self):
        if self.cache_file.exists():
            try:
                with self.lock:
                    self._cache = json.loads(self.cache_file.read_text())
            except Exception:
                self._cache = {}

    def _save_worker(self, content: str):
        """Worker thread for atomic disk operations."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            # Atomic swap pattern
            fd, temp_path = tempfile.mkstemp(dir=self.cache_file.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                os.replace(temp_path, self.cache_file)
            except Exception:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        except Exception:
            pass

    def _save(self):
        """Schedules a background atomic save."""
        try:
            with self.lock:
                if not self._dirty:
                    return
                content = json.dumps(self._cache)
                self._dirty = False

            # Offload IO to a daemon thread to avoid blocking caller
            threading.Thread(
                target=self._save_worker, args=(content,), daemon=True
            ).start()
        except Exception:
            pass

    def get(self, text_hash: str) -> Optional[List[float]]:
        with self.lock:
            return self._cache.get(text_hash)

    def set(self, text_hash: str, embedding: List[float]):
        with self.lock:
            self._cache[text_hash] = embedding
            self._dirty = True
        self._save()


def _hash_text(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _get_embedding_gemini(text: str) -> List[float]:
    """Fetch embedding from Google Gemini API (gemini-embedding-001, 3072 dims)."""
    import requests
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY missing.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={api_key}"
    payload = {
        "model": "models/gemini-embedding-001",
        "content": {"parts": [{"text": text}]},
    }

    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()["embedding"]["values"]


def _get_embedding_ollama(text: str) -> List[float]:
    """Fetch embedding from local Ollama instance.

    Requires Ollama running locally (default: http://localhost:11434).
    Default model: nomic-embed-text (768 dims). Override via OLLAMA_EMBED_MODEL.

    Install:
        curl -fsSL https://ollama.com/install.sh | sh
        ollama pull nomic-embed-text
    """
    import requests
    from dotenv import load_dotenv

    load_dotenv()

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

    response = requests.post(
        f"{base_url}/api/embed",
        json={"model": model, "input": text},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["embeddings"][0]


# Provider registry
_EMBEDDING_PROVIDERS = {
    "gemini": _get_embedding_gemini,
    "ollama": _get_embedding_ollama,
}


def get_embedding(text: str) -> List[float]:
    """Generate embedding with persistent disk caching.

    Provider is selected via EMBEDDING_PROVIDER env var:
        - "gemini" (default): Google Gemini API (3072 dims, requires GOOGLE_API_KEY)
        - "ollama": Local Ollama instance (768 dims default, zero-cost, fully offline)

    Set EMBEDDING_PROVIDER=ollama in your .env for local-only operation.
    """
    text_hash = _hash_text(text)
    cache = get_embedding_cache()
    cached = cache.get(text_hash)
    if cached:
        return cached

    provider_name = os.getenv("EMBEDDING_PROVIDER", "gemini").lower()
    provider_fn = _EMBEDDING_PROVIDERS.get(provider_name)
    if not provider_fn:
        raise ValueError(
            f"Unknown EMBEDDING_PROVIDER='{provider_name}'. "
            f"Supported: {', '.join(_EMBEDDING_PROVIDERS.keys())}"
        )

    embedding = provider_fn(text)
    cache.set(text_hash, embedding)
    return embedding


def search_rpc(
    rpc_name: str, query_embedding: List[float], limit: int = 5, threshold: float = 0.3
) -> List[Dict]:
    client = get_client()
    result = client.rpc(
        rpc_name,
        {
            "query_embedding": query_embedding,
            "match_threshold": threshold,
            "match_count": limit,
        },
    ).execute()
    return result.data


def _search_chroma(
    collection_name: str, query_embedding: List[float], limit: int = 5, threshold: float = 0.3
) -> List[Dict]:
    """Search ChromaDB collection as fallback when Supabase unavailable."""
    try:
        import chromadb
        from athena.core.config import PROJECT_ROOT

        chroma_path = str(PROJECT_ROOT / ".agent" / "chroma_db")
        client = chromadb.PersistentClient(path=chroma_path)
        collection = client.get_collection(collection_name)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
        )

        output = []
        if results and results.get("documents"):
            documents = results["documents"][0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            for i, doc in enumerate(documents):
                metadata = metadatas[i] if i < len(metadatas) else {}
                distance = distances[i] if i < len(distances) else 1.0
                similarity = 1.0 - distance

                if similarity >= threshold:
                    output.append({
                        "content": doc,
                        "file_path": metadata.get("file_path", ""),
                        "title": metadata.get("title", ""),
                        "similarity": similarity,
                    })
        return output
    except Exception:
        return []


# --- Collection-Specific Wrappers ---


def search_sessions(client, query_embedding, limit=5, threshold=0.3):
    if client is None:
        return _search_chroma("sessions", query_embedding, limit, threshold)
    return search_rpc("search_sessions", query_embedding, limit, threshold)


def search_case_studies(client, query_embedding, limit=5, threshold=0.3):
    if client is None:
        return _search_chroma("case_studies", query_embedding, limit, threshold)
    return search_rpc("search_case_studies", query_embedding, limit, threshold)


def search_protocols(client, query_embedding, limit=5, threshold=0.3):
    if client is None:
        return _search_chroma("protocols", query_embedding, limit, threshold)
    return search_rpc("search_protocols", query_embedding, limit, threshold)


def search_capabilities(client, query_embedding, limit=5, threshold=0.3):
    if client is None:
        return _search_chroma("capabilities", query_embedding, limit, threshold)
    return search_rpc("search_capabilities", query_embedding, limit, threshold)


def search_playbooks(client, query_embedding, limit=5, threshold=0.3):
    if client is None:
        return _search_chroma("playbooks", query_embedding, limit, threshold)
    return search_rpc("search_playbooks", query_embedding, limit, threshold)


def search_references(client, query_embedding, limit=5, threshold=0.3):
    if client is None:
        return _search_chroma("references", query_embedding, limit, threshold)
    return search_rpc("search_references", query_embedding, limit, threshold)


def search_frameworks(client, query_embedding, limit=5, threshold=0.3):
    if client is None:
        return _search_chroma("frameworks", query_embedding, limit, threshold)
    return search_rpc("search_frameworks", query_embedding, limit, threshold)


def search_workflows(client, query_embedding, limit=5, threshold=0.3):
    if client is None:
        return _search_chroma("workflows", query_embedding, limit, threshold)
    return search_rpc("search_workflows", query_embedding, limit, threshold)


def search_entities(client, query_embedding, limit=5, threshold=0.3):
    if client is None:
        return _search_chroma("entities", query_embedding, limit, threshold)
    return search_rpc("search_entities", query_embedding, limit, threshold)


def search_user_profile(client, query_embedding, limit=5, threshold=0.3):
    if client is None:
        return _search_chroma("user_profile", query_embedding, limit, threshold)
    return search_rpc("search_user_profile", query_embedding, limit, threshold)


def search_system_docs(client, query_embedding, limit=5, threshold=0.3):
    if client is None:
        return _search_chroma("system_docs", query_embedding, limit, threshold)
    return search_rpc("search_system_docs", query_embedding, limit, threshold)


def search_insights(client, query_embedding, limit=5, threshold=0.3):
    """Search insights table (Marketing Analysis, Strategic Notes)."""
    if client is None:
        return _search_chroma("insights", query_embedding, limit, threshold)
    return search_rpc("search_insights", query_embedding, limit, threshold)
