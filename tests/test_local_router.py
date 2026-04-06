#!/usr/bin/env python3
"""Comprehensive unit tests for LocalRouter."""

import importlib.util
import json
import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN_DIR = os.path.join(PROJECT_ROOT, "bin")
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, BIN_DIR)

spec = importlib.util.spec_from_file_location(
    "local_router",
    os.path.join(PROJECT_ROOT, "bin", "local-router.py")
)
local_router_module = importlib.util.module_from_spec(spec)
sys.modules['local_router'] = local_router_module
spec.loader.exec_module(local_router_module)

LocalRouter = local_router_module.LocalRouter


@pytest.fixture
def router():
    """Create a LocalRouter instance."""
    return LocalRouter(ollama_url="http://localhost:11434")


class TestClassify:
    """Tests for LocalRouter.classify() method."""

    def test_classify_simple_task(self, router):
        """Test classification of simple task (explain this)."""
        result = router.classify("explain this")
        assert result == "simple"

    def test_classify_medium_task(self, router):
        """Test classification of medium task (fix this bug)."""
        result = router.classify("fix this bug")
        assert result == "medium"

    def test_classify_complex_task(self, router):
        """Test classification of complex task (design architecture)."""
        result = router.classify("design architecture")
        assert result == "complex"

    def test_classify_empty_task(self, router):
        """Test classification of empty task."""
        result = router.classify("")
        assert result == "unknown"

    def test_classify_whitespace_only(self, router):
        """Test classification of whitespace-only task."""
        result = router.classify("   ")
        assert result == "unknown"

    def test_classify_none_task(self, router):
        """Test classification of None task."""
        result = router.classify(None)
        assert result == "unknown"

    def test_classify_unknown_task(self, router):
        """Test classification of unknown task (no keyword matches)."""
        result = router.classify("xyz123 random text abc")
        assert result == "unknown"

    def test_classify_case_insensitive(self, router):
        """Test classification is case insensitive."""
        result = router.classify("EXPLAIN THIS COMPLEX ARCHITECTURE")
        assert result == "complex"

    def test_classify_multiple_keywords(self, router):
        """Test classification with multiple matching keywords."""
        result = router.classify("fix the bug and optimize the code")
        assert result == "medium"


class TestIsLocalAvailable:
    """Tests for LocalRouter.is_local_available() method."""

    @patch("local_router.requests.get")
    def test_health_check_ollama_running(self, mock_get, router):
        """Test health check when Ollama is running (200 response)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = router.is_local_available()

        assert result is True
        mock_get.assert_called_once()

    @patch("local_router.requests.get")
    def test_health_check_ollama_down(self, mock_get, router):
        """Test health check when Ollama is down (raises exception)."""
        import requests as req

        mock_get.side_effect = req.RequestException("Connection refused")

        result = router.is_local_available()

        assert result is False

    @patch("local_router.requests.get")
    def test_health_check_timeout(self, mock_get, router):
        """Test health check when request times out."""
        import requests as req

        mock_get.side_effect = req.Timeout()

        result = router.is_local_available()

        assert result is False

    @patch("local_router.requests.get")
    def test_health_check_non_200(self, mock_get, router):
        """Test health check returns false for non-200 status."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_get.return_value = mock_response

        result = router.is_local_available()

        assert result is False


class TestGetLocalModels:
    """Tests for LocalRouter.get_local_models() method."""

    @patch("requests.get")
    def test_get_local_models_returns_list(self, mock_get, router):
        """Test get_local_models returns a list."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.2:3b"},
                {"name": "codellama:7b"},
            ]
        }
        mock_get.return_value = mock_response

        result = router.get_local_models()

        assert isinstance(result, list)
        assert len(result) >= 1
        assert "llama3.2:3b" in result

    @patch.dict(os.environ, {"OLLAMA_MODEL": "custom/model:latest"}, clear=False)
    def test_get_local_models_from_env(self, router):
        """Test get_local_models returns model from OLLAMA_MODEL env var."""
        result = router.get_local_models()

        assert isinstance(result, list)
        assert "custom/model:latest" in result

    @patch("local_router.requests.get")
    def test_get_local_models_fallback(self, mock_get, router):
        """Test get_local_models returns default when request fails."""
        import requests as req

        mock_get.side_effect = req.RequestException()

        result = router.get_local_models()

        assert isinstance(result, list)
        assert router.DEFAULT_MODEL in result


class TestCLI:
    """Tests for CLI interface."""

    def test_cli_task_flag(self):
        """Test CLI with --task flag."""
        result = subprocess.run(
            [sys.executable, "bin/local-router.py", "--task", "explain this"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert result.stdout.strip() in ["simple", "medium", "complex", "unknown"]

    def test_cli_task_json_flag(self):
        """Test CLI with --task and --format json flags."""
        result = subprocess.run(
            [sys.executable, "bin/local-router.py", "--task", "fix bug", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "task" in data
        assert "classification" in data

    def test_cli_health_flag(self):
        """Test CLI with --health flag."""
        result = subprocess.run(
            [sys.executable, "bin/local-router.py", "--health"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode in [0, 1]

    def test_cli_health_json_flag(self):
        """Test CLI with --health and --format json flags."""
        result = subprocess.run(
            [sys.executable, "bin/local-router.py", "--health", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode in [0, 1]
        data = json.loads(result.stdout)
        assert "available" in data

    def test_cli_list_models_flag(self):
        """Test CLI with --list-models flag."""
        result = subprocess.run(
            [sys.executable, "bin/local-router.py", "--list-models"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0

    def test_cli_list_models_json_flag(self):
        """Test CLI with --list-models and --format json flags."""
        result = subprocess.run(
            [sys.executable, "bin/local-router.py", "--list-models", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "models" in data

    def test_cli_json_output(self):
        """Test CLI with --format json for task classification."""
        result = subprocess.run(
            [sys.executable, "bin/local-router.py", "--task", "design system", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["task"] == "design system"
        assert data["classification"] in ["simple", "medium", "complex", "unknown"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
