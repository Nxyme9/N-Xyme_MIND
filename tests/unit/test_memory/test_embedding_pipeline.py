"""Unit tests for memory.embedding_pipeline."""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from src.memory.embedding_pipeline import (
    DB_PATH,
    OLLAMA_URL,
    OLLAMA_MODEL,
    EMBED_DIM,
    _get_db_connection,
    _check_ollama_available,
)


class TestModuleConstants:
    """Test module-level constants."""

    def test_db_path_is_path(self):
        """Test DB_PATH is a Path object."""
        assert isinstance(DB_PATH, Path)

    def test_ollama_url_default(self):
        """Test Ollama URL default."""
        assert OLLAMA_URL == "http://localhost:11434"

    def test_ollama_model_default(self):
        """Test Ollama model default."""
        assert OLLAMA_MODEL == "nomic-embed-text"

    def test_embed_dim(self):
        """Test embedding dimension."""
        assert EMBED_DIM == 768


class TestDBConnection:
    """Test database connection function."""

    def test_get_db_connection_returns_connection(self):
        """Test _get_db_connection returns a connection."""
        conn = _get_db_connection()
        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)
        conn.close()


class TestOllamaCheck:
    """Test Ollama availability check."""

    def test_check_ollama_returns_bool(self):
        """Test _check_ollama_available returns a boolean."""
        result = _check_ollama_available()
        assert isinstance(result, bool)


class TestEmbeddingPipelineImports:
    """Test that module imports work."""

    def test_import_embedding_pipeline(self):
        """Test embedding_pipeline module can be imported."""
        from src.memory import embedding_pipeline

        assert embedding_pipeline is not None

    def test_import_embed_memory_function(self):
        """Test embed_memory function can be imported."""
        from src.memory.embedding_pipeline import embed_memory

        assert embed_memory is not None

    def test_import_embed_batch_function(self):
        """Test embed_batch function can be imported."""
        from src.memory.embedding_pipeline import embed_batch

        assert embed_batch is not None


class TestVectorIndexImports:
    """Test vector_index module imports."""

    def test_import_vector_index(self):
        """Test vector_index module can be imported."""
        from src.memory import vector_index

        assert vector_index is not None

    def test_import_dot_product(self):
        """Test dot_product function can be imported."""
        from src.memory.vector_index import dot_product

        assert dot_product is not None

    def test_import_cosine_similarity(self):
        """Test cosine_similarity function can be imported."""
        from src.memory.vector_index import cosine_similarity

        assert cosine_similarity is not None

    def test_import_l2_distance(self):
        """Test l2_distance function can be imported."""
        from src.memory.vector_index import l2_distance

        assert l2_distance is not None


class TestVectorMath:
    """Test vector math functions."""

    def test_dot_product(self):
        """Test dot product calculation."""
        from src.memory.vector_index import dot_product

        result = dot_product([1, 2, 3], [4, 5, 6])
        assert result == 32  # 1*4 + 2*5 + 3*6

    def test_l2_distance(self):
        """Test L2 distance calculation."""
        from src.memory.vector_index import l2_distance

        result = l2_distance([0, 0], [3, 4])
        assert result == 5.0

    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        from src.memory.vector_index import cosine_similarity

        # Same direction
        result = cosine_similarity([1, 0], [1, 0])
        assert result == 1.0
        # Opposite direction
        result = cosine_similarity([1, 0], [-1, 0])
        assert result == -1.0
        # Orthogonal
        result = cosine_similarity([1, 0], [0, 1])
        assert result == 0.0
