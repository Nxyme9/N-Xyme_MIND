"""Unit tests for model_router.ollama_manager."""

import pytest
from src.model_router.ollama_manager import (
    ModelInfo,
    LoadedModel,
    OllamaManager,
)


class TestModelInfo:
    """Test ModelInfo class."""

    def test_model_info_creation(self):
        """Test ModelInfo creation."""
        info = ModelInfo(
            name="llama2",
            size=3826793472,
            modified_at="2024-01-01T00:00:00Z",
        )
        assert info.name == "llama2"
        assert info.size == 3826793472


class TestLoadedModel:
    """Test LoadedModel class."""

    def test_loaded_model_creation(self):
        """Test LoadedModel creation."""
        model = LoadedModel(
            name="llama2",
            size=1000,
            digest="abc123",
            expires_at="2024-01-01T00:00:00Z",
        )
        assert model.name == "llama2"
        assert model.size == 1000


class TestOllamaManager:
    """Test OllamaManager class."""

    @pytest.fixture
    def ollama_manager(self):
        """Create an OllamaManager instance."""
        return OllamaManager()

    def test_ollama_manager_init(self, ollama_manager):
        """Test OllamaManager initialization."""
        assert ollama_manager is not None


class TestOllamaManagerImports:
    """Test module imports."""

    def test_import_ollama_manager(self):
        """Test OllamaManager can be imported."""
        from src.model_router.ollama_manager import OllamaManager

        assert OllamaManager is not None

    def test_import_model_info(self):
        """Test ModelInfo can be imported."""
        from src.model_router.ollama_manager import ModelInfo

        assert ModelInfo is not None

    def test_import_loaded_model(self):
        """Test LoadedModel can be imported."""
        from src.model_router.ollama_manager import LoadedModel

        assert LoadedModel is not None
