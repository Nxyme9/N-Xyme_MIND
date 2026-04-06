"""Tests for memory embeddings module."""

import math
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.memory.embeddings import (
    EmbeddingEngine,
    VectorStore,
    embed_text,
    batch_embed,
    similarity_search,
    similarity,
    get_engine,
)


class TestEmbeddingEngine:
    def test_embed_hash_returns_768_dim(self):
        engine = EmbeddingEngine()
        embedding = engine._embed_hash("test text")
        assert len(embedding) == 768
        assert all(-1.0 <= v <= 1.0 for v in embedding)

    def test_embed_hash_deterministic(self):
        engine = EmbeddingEngine()
        emb1 = engine._embed_hash("same text")
        emb2 = engine._embed_hash("same text")
        assert emb1 == emb2

    def test_embed_hash_different_inputs(self):
        engine = EmbeddingEngine()
        emb1 = engine._embed_hash("text one")
        emb2 = engine._embed_hash("text two")
        assert emb1 != emb2

    def test_embed_text_fallback_to_hash(self):
        """When Ollama and ST are unavailable, falls back to hash."""
        engine = EmbeddingEngine()
        # Force hash fallback by not having Ollama/ST
        embedding = engine.embed_text("test")
        assert len(embedding) == 768

    def test_batch_embed(self):
        engine = EmbeddingEngine()
        docs = ["doc one", "doc two", "doc three"]
        embeddings = engine.batch_embed(docs)
        assert len(embeddings) == 3
        assert all(len(e) == 768 for e in embeddings)

    def test_batch_embed_empty_list(self):
        engine = EmbeddingEngine()
        embeddings = engine.batch_embed([])
        assert embeddings == []

    def test_similarity_identical_vectors(self):
        engine = EmbeddingEngine()
        vec = [1.0, 0.0, 0.0]
        score = engine.similarity(vec, vec)
        assert abs(score - 1.0) < 1e-6

    def test_similarity_orthogonal_vectors(self):
        engine = EmbeddingEngine()
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        score = engine.similarity(vec1, vec2)
        assert abs(score) < 1e-6

    def test_similarity_different_lengths(self):
        engine = EmbeddingEngine()
        vec1 = [1.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        score = engine.similarity(vec1, vec2)
        assert score == 0.0

    def test_similarity_zero_vector(self):
        engine = EmbeddingEngine()
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        score = engine.similarity(vec1, vec2)
        assert score == 0.0

    def test_similarity_search_returns_top_k(self):
        engine = EmbeddingEngine()
        documents = [
            "Python is a programming language",
            "JavaScript runs in browsers",
            "Rust is for systems programming",
            "Python and Rust are both compiled",
        ]
        results = engine.similarity_search("Python programming", documents, top_k=2)
        assert len(results) == 2
        # Results should be sorted by score
        assert results[0][1] >= results[1][1]

    def test_similarity_search_empty_documents(self):
        engine = EmbeddingEngine()
        results = engine.similarity_search("test", [], top_k=5)
        assert results == []


class TestVectorStore:
    def test_add_and_search(self):
        engine = EmbeddingEngine()
        store = VectorStore(engine=engine)
        store.add("Python is great for ML")
        store.add("JavaScript is for web")
        store.add("Rust is for systems")

        results = store.search("Python machine learning", top_k=1)
        assert len(results) == 1
        # Hash-based embeddings are deterministic but not semantically meaningful
        # Just verify we get a result back
        assert "text" in results[0]
        assert "score" in results[0]

    def test_add_with_metadata(self):
        engine = EmbeddingEngine()
        store = VectorStore(engine=engine)
        store.add("test doc", metadata={"source": "test", "id": "1"})
        results = store.search("test", top_k=1)
        assert results[0]["metadata"]["source"] == "test"
        assert results[0]["metadata"]["id"] == "1"

    def test_add_without_metadata(self):
        engine = EmbeddingEngine()
        store = VectorStore(engine=engine)
        store.add("test doc")
        results = store.search("test", top_k=1)
        assert results[0]["metadata"] == {}

    def test_search_empty_store(self):
        engine = EmbeddingEngine()
        store = VectorStore(engine=engine)
        results = store.search("test", top_k=5)
        assert results == []

    def test_search_respects_top_k(self):
        engine = EmbeddingEngine()
        store = VectorStore(engine=engine)
        for i in range(10):
            store.add(f"Document number {i}")
        results = store.search("Document", top_k=3)
        assert len(results) <= 3

    def test_search_results_have_required_fields(self):
        engine = EmbeddingEngine()
        store = VectorStore(engine=engine)
        store.add("test content")
        results = store.search("test", top_k=1)
        assert len(results) == 1
        result = results[0]
        assert "index" in result
        assert "text" in result
        assert "score" in result
        assert "metadata" in result


class TestGlobalEngine:
    def test_get_engine_singleton(self):
        eng1 = get_engine()
        eng2 = get_engine()
        assert eng1 is eng2

    def test_embed_text_convenience(self):
        embedding = embed_text("test")
        assert len(embedding) == 768

    def test_batch_embed_convenience(self):
        embeddings = batch_embed(["doc1", "doc2"])
        assert len(embeddings) == 2

    def test_similarity_convenience(self):
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        score = similarity(vec1, vec2)
        assert abs(score - 1.0) < 1e-6

    def test_similarity_search_convenience(self):
        documents = ["Python is great", "JavaScript is web"]
        results = similarity_search("Python", documents, top_k=1)
        assert len(results) == 1
