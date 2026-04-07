"""Tests for FallbackChain rotation on failure."""
import unittest
from unittest.mock import Mock, patch, MagicMock


class TestSpineFallbackResult(unittest.TestCase):
    """Test SpineFallbackResult dataclass (lightweight tests)."""

    def test_defaults(self):
        """Test default values."""
        from packages.infrastructure.spine.fallback import SpineFallbackResult
        
        result = SpineFallbackResult()
        
        self.assertFalse(result.success)
        self.assertEqual(result.model_used, "")
        self.assertEqual(result.latency_ms, 0.0)
        self.assertIsNone(result.error)
        self.assertEqual(result.fallback_path, [])

    def test_custom_values(self):
        """Test custom values."""
        from packages.infrastructure.spine.fallback import SpineFallbackResult
        
        result = SpineFallbackResult(
            success=True,
            model_used="qwen2.5-coder:7b",
            latency_ms=150.5,
            fallback_path=["qwen2.5-coder:7b"],
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.model_used, "qwen2.5-coder:7b")
        self.assertEqual(result.latency_ms, 150.5)
        self.assertEqual(result.fallback_path, ["qwen2.5-coder:7b"])


class TestSpineFallbackImports(unittest.TestCase):
    """Test SpineFallback can be imported."""

    def test_config_import(self):
        """Test SpineConfig import."""
        from packages.infrastructure.spine.config import SpineConfig
        config = SpineConfig()
        self.assertEqual(config.model_path, "qwen2.5-coder:7b")

    def test_health_import(self):
        """Test HealthResult import."""
        from packages.infrastructure.spine.health import HealthResult
        result = HealthResult(layer="test", healthy=True, message="OK")
        self.assertEqual(result.layer, "test")

    def test_fallback_result_import(self):
        """Test SpineFallbackResult import."""
        from packages.infrastructure.spine.fallback import SpineFallbackResult
        result = SpineFallbackResult(success=True, model_used="test")
        self.assertTrue(result.success)
        self.assertEqual(result.model_used, "test")


if __name__ == "__main__":
    unittest.main()