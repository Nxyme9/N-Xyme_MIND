"""Tests for SpineConfig validation."""
import unittest
from packages.infrastructure.spine.config import SpineConfig


class TestSpineConfig(unittest.TestCase):
    """Test SpineConfig validation and methods."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SpineConfig()
        
        self.assertEqual(config.model_path, "qwen2.5-coder:7b")
        self.assertEqual(config.fallback_models, ["llama3.2:3b"])
        self.assertEqual(config.bind_host, "127.0.0.1")
        self.assertEqual(config.port, 11434)
        self.assertEqual(config.ctx, 8192)
        self.assertEqual(config.gpu_layers, -1)
        self.assertEqual(config.failure_threshold, 3)
        self.assertEqual(config.reset_timeout, 60.0)
        self.assertEqual(config.max_retries, 3)

    def test_custom_values(self):
        """Test custom configuration values."""
        config = SpineConfig(
            model_path="llama3.2:3b",
            fallback_models=["gemma:2b", "mistral:7b"],
            bind_host="0.0.0.0",
            port=8080,
            ctx=4096,
            gpu_layers=32,
            failure_threshold=5,
            reset_timeout=120.0,
            max_retries=5,
        )
        
        self.assertEqual(config.model_path, "llama3.2:3b")
        self.assertEqual(config.fallback_models, ["gemma:2b", "mistral:7b"])
        self.assertEqual(config.bind_host, "0.0.0.0")
        self.assertEqual(config.port, 8080)
        self.assertEqual(config.ctx, 4096)
        self.assertEqual(config.gpu_layers, 32)
        self.assertEqual(config.failure_threshold, 5)
        self.assertEqual(config.reset_timeout, 120.0)
        self.assertEqual(config.max_retries, 5)

    def test_to_dict(self):
        """Test to_dict serialization."""
        config = SpineConfig(model_path="test-model", port=9999)
        result = config.to_dict()
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["model_path"], "test-model")
        self.assertEqual(result["port"], 9999)
        self.assertEqual(result["fallback_models"], ["llama3.2:3b"])
        self.assertEqual(result["bind_host"], "127.0.0.1")

    def test_from_dict(self):
        """Test from_dict deserialization."""
        data = {
            "model_path": "custom-model",
            "fallback_models": ["fallback1"],
            "bind_host": "localhost",
            "port": 1234,
            "ctx": 4096,
            "gpu_layers": 16,
            "failure_threshold": 2,
            "reset_timeout": 30.0,
            "max_retries": 2,
        }
        
        config = SpineConfig.from_dict(data)
        
        self.assertEqual(config.model_path, "custom-model")
        self.assertEqual(config.fallback_models, ["fallback1"])
        self.assertEqual(config.bind_host, "localhost")
        self.assertEqual(config.port, 1234)
        self.assertEqual(config.ctx, 4096)
        self.assertEqual(config.gpu_layers, 16)
        self.assertEqual(config.failure_threshold, 2)
        self.assertEqual(config.reset_timeout, 30.0)
        self.assertEqual(config.max_retries, 2)

    def test_from_dict_partial(self):
        """Test from_dict with partial data ignores unknown keys."""
        data = {
            "model_path": "partial-model",
            "unknown_key": "should be ignored",
        }
        
        config = SpineConfig.from_dict(data)
        
        self.assertEqual(config.model_path, "partial-model")
        # Default values for unspecified fields
        self.assertEqual(config.port, 11434)

    def test_fallback_models_default_factory(self):
        """Test fallback_models uses default factory to avoid mutable default."""
        config1 = SpineConfig()
        config2 = SpineConfig()
        
        # Should be different list instances, not the same
        self.assertIsNot(config1.fallback_models, config2.fallback_models)
        
        # Both should have the expected default
        self.assertEqual(config1.fallback_models, ["llama3.2:3b"])
        self.assertEqual(config2.fallback_models, ["llama3.2:3b"])


if __name__ == "__main__":
    unittest.main()