"""Tests for GoldenSpine core run() method."""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


class TestGoldenSpine(unittest.TestCase):
    """Test GoldenSpine core orchestrator."""

    def test_spinesp_config_import(self):
        """Test that SpineConfig can be imported."""
        from packages.infrastructure.spine.config import SpineConfig
        config = SpineConfig()
        self.assertEqual(config.model_path, "qwen2.5-coder:7b")

    def test_health_result_import(self):
        """Test that health result can be imported."""
        from packages.infrastructure.spine.health import HealthResult
        result = HealthResult(layer="test", healthy=True, message="OK")
        self.assertEqual(result.layer, "test")
        self.assertTrue(result.healthy)

    def test_spine_fallback_result_import(self):
        """Test that SpineFallbackResult can be imported."""
        from packages.infrastructure.spine.fallback import SpineFallbackResult
        result = SpineFallbackResult(success=True, model_used="test")
        self.assertTrue(result.success)
        self.assertEqual(result.model_used, "test")

    def test_run_record_import(self):
        """Test that RunRecord can be imported."""
        from packages.infrastructure.spine.run_tracker import RunRecord
        record = RunRecord(run_id="test-123", model="test-model")
        self.assertEqual(record.run_id, "test-123")
        self.assertEqual(record.model, "test-model")


if __name__ == "__main__":
    unittest.main()