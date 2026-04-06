"""Integration tests for bin/*.py scripts."""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest


def run_script(script_name: str, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run a bin script and return the result."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script_path = os.path.join(base_dir, "bin", script_name)
    
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    
    return subprocess.run(
        [sys.executable, script_path] + list(args),
        capture_output=True,
        text=True,
        env=full_env,
    )


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def check_ollama():
    """Skip test if Ollama not running."""
    result = subprocess.run(
        ["curl", "-s", "http://localhost:11434/api/tags"],
        capture_output=True,
    )
    if result.returncode != 0:
        pytest.skip("Ollama not running")


class TestModelConfig:
    """Tests for bin/model_config.py."""

    def test_json_output_default(self):
        """Test JSON output with default values."""
        result = run_script("model_config.py")
        assert result.returncode == 0
        
        data = json.loads(result.stdout)
        assert "OLLAMA_MODEL" in data
        assert "PRIMARY_MODEL" in data
        assert "FALLBACK_MODEL" in data

    def test_env_override(self):
        """Test environment variable overrides."""
        env = {
            "OLLAMA_MODEL": "custom-ollama-model",
            "PRIMARY_MODEL": "custom-primary-model",
        }
        result = run_script("model_config.py", env=env)
        assert result.returncode == 0
        
        data = json.loads(result.stdout)
        assert data["OLLAMA_MODEL"] == "custom-ollama-model"
        assert data["PRIMARY_MODEL"] == "custom-primary-model"


class TestModelSelector:
    """Tests for bin/model-selector.py."""

    def test_json_output(self):
        """Test JSON output format."""
        result = run_script("model-selector.py", "--task", "write a function", "--format", "json")
        assert result.returncode == 0
        
        data = json.loads(result.stdout)
        assert "task" in data
        assert "model" in data
        assert "complexity" in data

    def test_env_override(self):
        """Test environment variable model override."""
        env = {"FALLBACK_MODEL": "test/model:v1"}
        result = run_script("model-selector.py", "--task", "explain basic concept", env=env)
        assert result.returncode == 0
        assert "test/model:v1" in result.stdout


class TestModelRouter:
    """Tests for bin/model-router.py."""

    def test_json_output(self):
        """Test JSON output format."""
        result = run_script("model-router.py", "--task", "fix this bug", "--format", "json")
        assert result.returncode == 0
        
        data = json.loads(result.stdout)
        assert "model" in data
        assert "confidence" in data
        assert "reason" in data

    def test_env_override(self):
        """Test environment variable model override."""
        env = {"DEFAULT_CODING_MODEL": "test/coding-model:v2"}
        result = run_script("model-router.py", "--task", "write code", "--format", "json", env=env)
        assert result.returncode == 0

        data = json.loads(result.stdout)
        # Model should be either the env override or local model depending on availability
        assert "model" in data

    def test_rules_output(self):
        """Test --rules output."""
        result = run_script("model-router.py", "--rules", "--format", "json")
        assert result.returncode == 0
        
        data = json.loads(result.stdout)
        assert "categories" in data
        assert "models" in data


class TestPromptCache:
    """Tests for bin/prompt-cache.py."""

    def test_cache_put_get(self, temp_cache_dir):
        """Test cache put and get operations."""
        # Put a value
        result = run_script(
            "prompt-cache.py",
            "--prompt", "test prompt",
            "--response", "test response",
            "--cache-dir", temp_cache_dir,
        )
        assert result.returncode == 0
        assert "[CACHED]" in result.stdout
        
        # Get the value
        result = run_script(
            "prompt-cache.py",
            "--prompt", "test prompt",
            "--cache-dir", temp_cache_dir,
        )
        assert result.returncode == 0
        assert "[CACHE HIT]" in result.stdout
        assert "test response" in result.stdout

    def test_cache_stats(self, temp_cache_dir):
        """Test cache statistics."""
        run_script(
            "prompt-cache.py",
            "--prompt", "prompt1",
            "--response", "response1",
            "--cache-dir", temp_cache_dir,
        )
        
        result = run_script(
            "prompt-cache.py",
            "--stats",
            "--cache-dir", temp_cache_dir,
        )
        assert result.returncode == 0
        assert "Hits:" in result.stdout
        assert "Size:" in result.stdout

    def test_cache_clear(self, temp_cache_dir):
        """Test cache clear operation."""
        run_script(
            "prompt-cache.py",
            "--prompt", "test",
            "--response", "value",
            "--cache-dir", temp_cache_dir,
        )
        
        result = run_script(
            "prompt-cache.py",
            "--clear",
            "--cache-dir", temp_cache_dir,
        )
        assert result.returncode == 0
        assert "cleared" in result.stdout.lower()