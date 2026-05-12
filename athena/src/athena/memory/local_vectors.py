"""
athena.memory.local_vectors — ChromaDB Backend

Drop-in replacement for vector operations when Supabase is not available.
Activated when EMBEDDING_PROVIDER=ollama (local-only mode).

Uses ChromaDB persistent storage for zero-config local vector search.
No API keys, no cloud dependencies — pure local operation.
"""

from pathlib import Path
from typing import Any

import chromadb

CHROMA_PATH = Path("./athena/.agent/chroma_db")


def get_chroma_client():
    """Get or create a persistent ChromaDB client."""
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_PATH))


def _search_collection(
    collection_name: str,
    query_embedding: list[float],
    limit: int = 5,
    threshold: float = 0.3,
) -> list[dict[str, Any]]:
    """Generic search across any ChromaDB collection.

    Args:
        collection_name: Name of the ChromaDB collection to search.
        query_embedding: The embedding vector to search with.
        limit: Maximum number of results to return.
        threshold: Minimum similarity threshold (0-1).

    Returns:
        List of dicts with keys: content, file_path, title, similarity.
    """
    try:
        client = get_chroma_client()
        coll = client.get_collection(collection_name)
        results = coll.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
        )

        output = []
        for i, doc in enumerate(results["documents"][0]):
            distance = results["distances"][0][i]
            similarity = 1 - distance
            if similarity >= threshold:
                meta = results["metadatas"][0][i]
                output.append(
                    {
                        "content": doc,
                        "file_path": meta.get("file_path", ""),
                        "title": meta.get("title", ""),
                        "similarity": similarity,
                    }
                )
        return output
    except Exception:
        return []


def search_sessions(
    query_embedding: list[float], limit: int = 5, threshold: float = 0.3
) -> list[dict[str, Any]]:
    """Search sessions collection."""
    return _search_collection("sessions", query_embedding, limit, threshold)


def search_case_studies(
    query_embedding: list[float], limit: int = 5, threshold: float = 0.3
) -> list[dict[str, Any]]:
    """Search case_studies collection."""
    return _search_collection("case_studies", query_embedding, limit, threshold)


def search_protocols(
    query_embedding: list[float], limit: int = 5, threshold: float = 0.3
) -> list[dict[str, Any]]:
    """Search protocols collection."""
    return _search_collection("protocols", query_embedding, limit, threshold)


def search_capabilities(
    query_embedding: list[float], limit: int = 5, threshold: float = 0.3
) -> list[dict[str, Any]]:
    """Search capabilities collection."""
    return _search_collection("capabilities", query_embedding, limit, threshold)


def search_playbooks(
    query_embedding: list[float], limit: int = 5, threshold: float = 0.3
) -> list[dict[str, Any]]:
    """Search playbooks collection."""
    return _search_collection("playbooks", query_embedding, limit, threshold)


def search_references(
    query_embedding: list[float], limit: int = 5, threshold: float = 0.3
) -> list[dict[str, Any]]:
    """Search references collection."""
    return _search_collection("references", query_embedding, limit, threshold)


def search_frameworks(
    query_embedding: list[float], limit: int = 5, threshold: float = 0.3
) -> list[dict[str, Any]]:
    """Search frameworks collection."""
    return _search_collection("frameworks", query_embedding, limit, threshold)


def search_workflows(
    query_embedding: list[float], limit: int = 5, threshold: float = 0.3
) -> list[dict[str, Any]]:
    """Search workflows collection."""
    return _search_collection("workflows", query_embedding, limit, threshold)


def search_entities(
    query_embedding: list[float], limit: int = 5, threshold: float = 0.3
) -> list[dict[str, Any]]:
    """Search entities collection."""
    return _search_collection("entities", query_embedding, limit, threshold)


def search_user_profile(
    query_embedding: list[float], limit: int = 5, threshold: float = 0.3
) -> list[dict[str, Any]]:
    """Search user_profile collection."""
    return _search_collection("user_profile", query_embedding, limit, threshold)


def search_system_docs(
    query_embedding: list[float], limit: int = 5, threshold: float = 0.3
) -> list[dict[str, Any]]:
    """Search system_docs collection."""
    return _search_collection("system_docs", query_embedding, limit, threshold)


def index_document(
    collection_name: str,
    doc_id: str,
    content: str,
    embedding: list[float],
    metadata: dict,
) -> bool:
    """Add or update a single document in ChromaDB.

    Args:
        collection_name: Name of the collection.
        doc_id: Unique identifier for the document.
        content: The document text content.
        embedding: The embedding vector for the content.
        metadata: Dict with metadata fields (file_path, title, etc.).

    Returns:
        True if successful, False otherwise.
    """
    try:
        client = get_chroma_client()
        coll = client.get_or_create_collection(collection_name)
        coll.upsert(
            ids=[doc_id],
            documents=[content],
            embeddings=[embedding],
            metadatas=[metadata],
        )
        return True
    except Exception:
        return False


def index_batch(
    collection_name: str,
    ids: list[str],
    contents: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
) -> bool:
    """Batch upsert multiple documents into ChromaDB.

    Args:
        collection_name: Name of the collection.
        ids: List of unique document identifiers.
        contents: List of document text contents.
        embeddings: List of embedding vectors.
        metadatas: List of metadata dicts.

    Returns:
        True if successful, False otherwise.
    """
    try:
        client = get_chroma_client()
        coll = client.get_or_create_collection(collection_name)
        coll.upsert(
            ids=ids,
            documents=contents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return True
    except Exception:
        return False
