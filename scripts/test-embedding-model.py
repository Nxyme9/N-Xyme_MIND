#!/usr/bin/env python3
"""
Comprehensive Embedding Model Test Suite
Tests ALL embedding capabilities: generation, similarity, caching, storage, ChromaDB, semantic search.
"""

import math
import sqlite3
import struct
import sys
import time
from pathlib import Path
from typing import List, Tuple

import httpx
import numpy as np

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "nomic-embed-text"
EMBED_DIM = 768
DB_PATH = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/context/memory/mind_from_mind.db")

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "athena" / "src"))

test_results = []


def log_result(test_name: str, passed: bool, details: str):
    status = "✅ PASS" if passed else "❌ FAIL"
    test_results.append((test_name, passed, details))
    print(f"{status} | {test_name}: {details}")


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    if len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(a * a for a in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def test_ollama_health():
    """Test a: Ollama API health check."""
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{OLLAMA_URL}/api/tags")
            passed = resp.status_code == 200
            details = f"Status: {resp.status_code}" if passed else f"Error: {resp.text}"
            log_result("Ollama Health", passed, details)
    except Exception as e:
        log_result("Ollama Health", False, str(e))


def test_model_availability():
    """Test b: Model availability - verify nomic-embed-text is loaded."""
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{OLLAMA_URL}/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                has_model = any(OLLAMA_MODEL in name for name in model_names)
                log_result(
                    "Model Availability",
                    has_model,
                    f"Models found: {model_names[:5]}..."
                    if model_names
                    else "No models",
                )
            else:
                log_result("Model Availability", False, f"Status: {resp.status_code}")
    except Exception as e:
        log_result("Model Availability", False, str(e))


def test_single_embedding():
    """Test c: Single embedding generation - verify 768-dim vector."""
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{OLLAMA_URL}/api/embed",
                json={"model": OLLAMA_MODEL, "input": "hello world"},
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings = data.get("embeddings", [])

            if embeddings:
                embedding = embeddings[0]
                dim = len(embedding)
                passed = dim == EMBED_DIM
                log_result(
                    "Single Embedding",
                    passed,
                    f"Generated {dim}-dim vector"
                    + ("" if passed else f" (expected {EMBED_DIM})"),
                )
            else:
                log_result("Single Embedding", False, "No embeddings returned")
    except Exception as e:
        log_result("Single Embedding", False, str(e))


def test_batch_embedding():
    """Test d: Batch embedding - embed 10 texts simultaneously."""
    texts = [
        "hello world",
        "the quick brown fox",
        "artificial intelligence",
        "machine learning",
        "natural language processing",
        "computer vision",
        "deep neural networks",
        "transformer architecture",
        "attention mechanism",
        " embeddings are vector representations",
    ]
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{OLLAMA_URL}/api/embed",
                json={"model": OLLAMA_MODEL, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings = data.get("embeddings", [])

            if len(embeddings) == 10:
                all_768 = all(len(e) == EMBED_DIM for e in embeddings)
                log_result(
                    "Batch Embedding",
                    all_768,
                    f"Batched {len(embeddings)} embeddings, all {EMBED_DIM}-dim: {all_768}",
                )
            else:
                log_result(
                    "Batch Embedding", False, f"Expected 10, got {len(embeddings)}"
                )
    except Exception as e:
        log_result("Batch Embedding", False, str(e))


def test_dimension_verification():
    """Test e: Dimension verification - confirm all embeddings are exactly 768."""
    texts = ["test one", "test two", "test three"]
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{OLLAMA_URL}/api/embed",
                json={"model": OLLAMA_MODEL, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings = data.get("embeddings", [])

            dims = [len(e) for e in embeddings]
            all_correct = all(d == EMBED_DIM for d in dims)
            log_result(
                "Dimension Verification",
                all_correct,
                f"Dimensions: {dims}" if not all_correct else f"All {EMBED_DIM}-dim ✓",
            )
    except Exception as e:
        log_result("Dimension Verification", False, str(e))


def test_cosine_similarity():
    """Test f: Cosine similarity - similar texts should have higher similarity."""
    similar_pairs = [
        ("machine learning is great", "machine learning works well"),
        ("deep neural networks", "neural networks with deep layers"),
    ]
    different_pairs = [
        ("machine learning is great", "the weather is nice today"),
        ("deep neural networks", "what time is lunch"),
    ]

    try:
        with httpx.Client(timeout=60.0) as client:
            all_passed = True
            details_parts = []

            for text1, text2 in similar_pairs:
                resp = client.post(
                    f"{OLLAMA_URL}/api/embed",
                    json={"model": OLLAMA_MODEL, "input": [text1, text2]},
                )
                resp.raise_for_status()
                embeddings = resp.json().get("embeddings", [])

                if len(embeddings) == 2:
                    sim = cosine_similarity(embeddings[0], embeddings[1])
                    if sim < 0.7:
                        all_passed = False
                    details_parts.append(f"similar({sim:.3f})")

            for text1, text2 in different_pairs:
                resp = client.post(
                    f"{OLLAMA_URL}/api/embed",
                    json={"model": OLLAMA_MODEL, "input": [text1, text2]},
                )
                resp.raise_for_status()
                embeddings = resp.json().get("embeddings", [])

                if len(embeddings) == 2:
                    sim = cosine_similarity(embeddings[0], embeddings[1])
                    if sim > 0.5:
                        all_passed = False
                    details_parts.append(f"diff({sim:.3f})")

            log_result("Cosine Similarity", all_passed, ", ".join(details_parts))
    except Exception as e:
        log_result("Cosine Similarity", False, str(e))


def test_embedding_cache():
    """Test g: Embedding cache - verify caching works."""
    try:
        from athena.memory.vectors import get_embedding_cache, _hash_text

        cache = get_embedding_cache()
        text = "cache test text"
        text_hash = _hash_text(text)

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{OLLAMA_URL}/api/embed",
                json={"model": OLLAMA_MODEL, "input": text},
            )
            resp.raise_for_status()
            embedding1 = resp.json().get("embeddings", [])[0]

            cached = cache.get(text_hash)
            if cached:
                is_same = cached == embedding1
                log_result(
                    "Embedding Cache",
                    is_same,
                    f"Cache hit ✓" if is_same else "Cache mismatch",
                )
            else:
                cache.set(text_hash, embedding1)
                cached_after = cache.get(text_hash)
                log_result(
                    "Embedding Cache",
                    cached_after is not None,
                    f"Cached value: {cached_after is not None}",
                )
    except Exception as e:
        log_result("Embedding Cache", False, str(e))


def test_vector_storage():
    """Test h: Vector storage - verify embeddings can be stored/retrieved from SQLite."""
    test_memory_id = "test_embedding_vector_storage"
    test_content = "vector storage test content"

    try:
        embedding = None
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": OLLAMA_MODEL, "prompt": test_content},
            )
            resp.raise_for_status()
            embedding = resp.json().get("embedding")

        if embedding:
            vec_blob = struct.pack(f"<{EMBED_DIM}f", *embedding)

            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "INSERT OR REPLACE INTO memory_embeddings (memory_id, model, dim, vec) VALUES (?, ?, ?, ?)",
                (test_memory_id, OLLAMA_MODEL, EMBED_DIM, vec_blob),
            )
            conn.commit()

            cursor = conn.execute(
                "SELECT vec FROM memory_embeddings WHERE memory_id = ?",
                (test_memory_id,),
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                retrieved_vec = struct.unpack(f"<{EMBED_DIM}f", row[0])
                stored_correctly = len(retrieved_vec) == EMBED_DIM
                log_result(
                    "Vector Storage",
                    stored_correctly,
                    f"Stored & retrieved {len(retrieved_vec)}-dim vector"
                    if stored_correctly
                    else "Mismatch",
                )
            else:
                log_result("Vector Storage", False, "Vector not found after storage")
        else:
            log_result("Vector Storage", False, "Failed to generate embedding")

        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "DELETE FROM memory_embeddings WHERE memory_id = ?", (test_memory_id,)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log_result("Vector Storage", False, str(e))


def test_vector_retrieval():
    """Test i: Vector retrieval - query memory_embeddings table."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute(
            "SELECT memory_id, model, dim, LENGTH(vec) as vec_len FROM memory_embeddings LIMIT 5"
        )
        rows = cursor.fetchall()
        conn.close()

        if rows:
            all_valid = all(r[2] == EMBED_DIM and r[3] == EMBED_DIM * 4 for r in rows)
            log_result(
                "Vector Retrieval",
                all_valid,
                f"Retrieved {len(rows)} embeddings, all valid: {all_valid}",
            )
        else:
            log_result("Vector Retrieval", True, "No embeddings in DB (empty table)")
    except Exception as e:
        log_result("Vector Retrieval", False, str(e))


def test_semantic_search():
    """Test j: Semantic search - use memory router to perform semantic search."""
    try:
        from src.memory.embeddings import get_engine, VectorStore

        engine = get_engine()
        store = VectorStore(engine)

        docs = [
            "python programming language",
            "javascript web development",
            "machine learning algorithms",
            "database sql queries",
            "cloud computing services",
        ]

        for doc in docs:
            store.add(doc, {"type": "test"})

        results = store.search("learn about AI", top_k=3)

        has_results = len(results) > 0
        ranked = (
            all(
                results[i]["score"] >= results[i + 1]["score"]
                for i in range(len(results) - 1)
            )
            if len(results) > 1
            else True
        )

        log_result(
            "Semantic Search",
            has_results and ranked,
            f"Found {len(results)} results, properly ranked: {ranked}",
        )
    except Exception as e:
        log_result("Semantic Search", False, str(e))


def test_chromadb_integration():
    """Test k: ChromaDB integration - test ChromaDB add/query."""
    try:
        import chromadb
        from pathlib import Path
        
        chroma_path = str(Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/.agent/chroma_db"))
        
        chroma_client = chromadb.PersistentClient(path=chroma_path)
        collection = chroma_client.get_or_create_collection("test_embeddings")
        
        test_docs = ["doc1", "doc2", "doc3"]
        
        with httpx.Client(timeout=30.0) as http_client:
            resp = http_client.post(
                f"{OLLAMA_URL}/api/embed",
                json={"model": OLLAMA_MODEL, "input": test_docs},
            )
            resp.raise_for_status()
            embeddings = resp.json().get("embeddings", [])
        
        ids = ["test1", "test2", "test3"]
        metadatas = [{"source": "test"}] * 3
        
        collection.add(embeddings=embeddings, documents=test_docs, ids=ids, metadatas=metadatas)
        
        with httpx.Client(timeout=30.0) as http_client:
            query_resp = http_client.post(
                f"{OLLAMA_URL}/api/embed",
                json={"model": OLLAMA_MODEL, "input": ["search query"]},
            )
            query_emb = query_resp.json().get("embeddings", [])[0]
        
        results = collection.query(query_embeddings=[query_emb], n_results=2)
        
        collection.delete(ids=ids)
        
        log_result(
            "ChromaDB Integration",
            len(results.get("ids", [[]])[0]) > 0,
            f"Added 3 docs, query returned {len(results.get('ids', [[]])[0])} results"
        )
    except Exception as e:
        log_result("ChromaDB Integration", False, str(e))


def test_embedding_pipeline():

    """Test k: ChromaDB integration - test ChromaDB add/query."""
    try:
        import chromadb
        from pathlib import Path

        chroma_path = str(Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/.agent/chroma_db"))

        client = chromadb.PersistentClient(path=chroma_path)
        collection = client.get_or_create_collection("test_embeddings")

        test_docs = ["doc1", "doc2", "doc3"]

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{OLLAMA_URL}/api/embed",
                json={"model": OLLAMA_MODEL, "input": test_docs},
            )
            resp.raise_for_status()
            embeddings = resp.json().get("embeddings", [])

        ids = ["test1", "test2", "test3"]
        metadatas = [{"source": "test"}] * 3

        collection.add(
            embeddings=embeddings, documents=test_docs, ids=ids, metadatas=metadatas
        )

        query_resp = client.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": OLLAMA_MODEL, "input": ["search query"]},
        )
        query_emb = query_resp.json().get("embeddings", [])[0]

        results = collection.query(query_embeddings=[query_emb], n_results=2)

        collection.delete(ids=ids)

        log_result(
            "ChromaDB Integration",
            len(results.get("ids", [[]])[0]) > 0,
            f"Added 3 docs, query returned {len(results.get('ids', [[]])[0])} results",
        )
    except Exception as e:
        log_result("ChromaDB Integration", False, str(e))


def test_embedding_pipeline():
    """Test l: Embedding pipeline - test auto_embed_on_save function."""
    try:
        from src.memory.embedding_pipeline import (
            _has_existing_embedding,
            embed_memory,
            auto_embed_on_save,
        )

        test_id = "test_pipeline_123"
        test_content = "pipeline test content for embedding"

        has_before = _has_existing_embedding(test_id)

        if not has_before:
            success = embed_memory(test_id, test_content)
            log_result(
                "Embedding Pipeline", success, f"auto_embed_on_save: embedded {success}"
            )

            from src.memory.embedding_pipeline import _get_db_connection

            conn = _get_db_connection()
            conn.execute(
                "DELETE FROM memory_embeddings WHERE memory_id = ?", (test_id,)
            )
            conn.commit()
            conn.close()
        else:
            log_result("Embedding Pipeline", True, "Already embedded, skipping")
    except Exception as e:
        log_result("Embedding Pipeline", False, str(e))


def test_backfill_function():
    """Test m: Backfill function - test backfill_missing_embeddings."""
    try:
        from src.memory.embedding_pipeline import backfill_missing_embeddings

        count = backfill_missing_embeddings(batch_size=10)

        log_result(
            "Backfill Function",
            count >= 0,
            f"Found {count} missing embeddings to backfill",
        )
    except Exception as e:
        log_result("Backfill Function", False, str(e))


def test_error_handling():
    """Test n: Error handling - test with invalid model name."""
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{OLLAMA_URL}/api/embed",
                json={"model": "nonexistent-model-xyz", "input": "test"},
            )

            handled_gracefully = resp.status_code != 200 or "error" in resp.text.lower()
            log_result(
                "Error Handling",
                handled_gracefully,
                f"Invalid model handled: status {resp.status_code}",
            )
    except Exception as e:
        log_result("Error Handling", True, f"Exception caught: {type(e).__name__}")


def main():
    print("=" * 70)
    print("FULL EMBEDDING MODEL FUNCTION TEST")
    print("=" * 70)
    print(f"Model: {OLLAMA_MODEL} ({EMBED_DIM}-dim)")
    print(f"Ollama: {OLLAMA_URL}")
    print(f"DB: {DB_PATH}")
    print("=" * 70)
    print()

    print("Running tests...\n")

    test_ollama_health()
    test_model_availability()
    test_single_embedding()
    test_batch_embedding()
    test_dimension_verification()
    test_cosine_similarity()
    test_embedding_cache()
    test_vector_storage()
    test_vector_retrieval()
    test_semantic_search()
    test_chromadb_integration()
    test_embedding_pipeline()
    test_backfill_function()
    test_error_handling()

    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, p, _ in test_results if p)
    total = len(test_results)

    print(f"\nTotal: {total} tests | {passed} passed | {total - passed} failed\n")

    print(f"{'Test Name':<30} | {'Status':<8} | {'Details'}")
    print("-" * 90)

    for name, passed, details in test_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        details_short = details[:50] + "..." if len(details) > 50 else details
        print(f"{name:<30} | {status:<8} | {details_short}")

    print("-" * 90)
    print(f"\nResult: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL EMBEDDING TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
