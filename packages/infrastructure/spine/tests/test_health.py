"""Tests for SpineHealthProbe 3-layer health checks."""
import unittest
from unittest.mock import Mock, patch, MagicMock

from packages.infrastructure.spine.health import (
    SpineHealthProbe,
    HealthResult,
    FullHealthReport,
)


class TestSpineHealthProbe(unittest.TestCase):
    """Test SpineHealthProbe 3-layer health monitoring."""

    def setUp(self):
        """Set up test probe."""
        self.probe = SpineHealthProbe(
            base_url="http://localhost:11434",
            model="qwen2.5-coder:7b",
            timeout=5,
        )

    def test_default_values(self):
        """Test default configuration values."""
        probe = SpineHealthProbe()
        
        self.assertEqual(probe.base_url, "http://localhost:11434")
        self.assertEqual(probe.model, "qwen2.5-coder:7b")
        self.assertEqual(probe.interval, 30.0)
        self.assertEqual(probe.timeout, 10)

    @patch("packages.infrastructure.spine.health.requests.get")
    def test_check_process_success(self, mock_get):
        """Test process layer when Ollama is running."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "0.1.20"}
        mock_get.return_value = mock_response

        result = self.probe.check_process()

        self.assertTrue(result.healthy)
        self.assertEqual(result.layer, "process")
        self.assertIn("0.1.20", result.message)
        self.assertGreater(result.latency_ms, 0)

    @patch("packages.infrastructure.spine.health.requests.get")
    def test_check_process_connection_error(self, mock_get):
        """Test process layer when Ollama is not running."""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError()

        result = self.probe.check_process()

        self.assertFalse(result.healthy)
        self.assertEqual(result.layer, "process")
        self.assertIn("Cannot connect", result.message)

    @patch("packages.infrastructure.spine.health.requests.get")
    def test_check_process_timeout(self, mock_get):
        """Test process layer when connection times out."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()

        result = self.probe.check_process()

        self.assertFalse(result.healthy)
        self.assertEqual(result.layer, "process")
        self.assertIn("timeout", result.message)

    @patch("packages.infrastructure.spine.health.requests.get")
    def test_check_model_success(self, mock_get):
        """Test model layer when model is available."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "qwen2.5-coder:7b"},
                {"name": "llama3.2:3b"},
            ]
        }
        mock_get.return_value = mock_response

        result = self.probe.check_model()

        self.assertTrue(result.healthy)
        self.assertEqual(result.layer, "model")
        self.assertIn("qwen2.5-coder", result.message)
        self.assertIn("qwen2.5-coder", result.details["available_models"])

    @patch("packages.infrastructure.spine.health.requests.get")
    def test_check_model_not_found(self, mock_get):
        """Test model layer when model is not available."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.2:3b"},
            ]
        }
        mock_get.return_value = mock_response

        result = self.probe.check_model()

        self.assertFalse(result.healthy)
        self.assertEqual(result.layer, "model")
        self.assertIn("not found", result.message)

    @patch("packages.infrastructure.spine.health.requests.get")
    def test_check_model_connection_error(self, mock_get):
        """Test model layer when cannot connect."""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError()

        result = self.probe.check_model()

        self.assertFalse(result.healthy)
        self.assertIn("Cannot connect", result.message)

    @patch("packages.infrastructure.spine.health.requests.post")
    def test_check_responsive_success(self, mock_post):
        """Test responsive layer when model responds."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Hello, I am working!"
        }
        mock_post.return_value = mock_response

        result = self.probe.check_responsive()

        self.assertTrue(result.healthy)
        self.assertEqual(result.layer, "responsive")
        self.assertIn("responds", result.message)
        self.assertIn("Hello", result.details["response_preview"])

    @patch("packages.infrastructure.spine.health.requests.post")
    def test_check_responsive_failure(self, mock_post):
        """Test responsive layer when model fails to respond."""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError()

        result = self.probe.check_responsive()

        self.assertFalse(result.healthy)
        self.assertEqual(result.layer, "responsive")
        self.assertIn("Cannot connect", result.message)

    @patch("packages.infrastructure.spine.health.requests.post")
    def test_check_responsive_timeout(self, mock_post):
        """Test responsive layer when generation times out."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()

        result = self.probe.check_responsive()

        self.assertFalse(result.healthy)
        self.assertIn("timeout", result.message)

    @patch("packages.infrastructure.spine.health.requests.get")
    @patch("packages.infrastructure.spine.health.requests.post")
    def test_is_healthy_all_healthy(self, mock_post, mock_get):
        """Test is_healthy when all 3 layers are healthy."""
        # Mock process layer
        mock_process = Mock()
        mock_process.status_code = 200
        mock_process.json.return_value = {"version": "0.1.20"}
        
        # Mock model layer
        mock_model = Mock()
        mock_model.status_code = 200
        mock_model.json.return_value = {"models": [{"name": "qwen2.5-coder:7b"}]}
        
        # Mock responsive layer
        mock_responsive = Mock()
        mock_responsive.status_code = 200
        mock_responsive.json.return_value = {"response": "pong"}

        mock_get.return_value = mock_process
        mock_post.return_value = mock_responsive
        
        # Need to handle multiple get calls
        self.probe.check_process = Mock(return_value=HealthResult("process", True, 10.0, "OK"))
        self.probe.check_model = Mock(return_value=HealthResult("model", True, 10.0, "OK"))
        self.probe.check_responsive = Mock(return_value=HealthResult("responsive", True, 10.0, "OK"))

        report = self.probe.is_healthy()

        self.assertTrue(report.overall_healthy)
        self.assertTrue(report.process.healthy)
        self.assertTrue(report.model.healthy)
        self.assertTrue(report.responsive.healthy)

    @patch("packages.infrastructure.spine.health.requests.get")
    def test_is_healthy_skips_on_failure(self, mock_get):
        """Test is_healthy skips dependent layers on failure."""
        # Mock process returning unhealthy
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "0.1.20"}
        mock_get.return_value = mock_response
        
        # Override methods to control results
        self.probe.check_process = Mock(return_value=HealthResult("process", False, 10.0, "Process down"))
        
        report = self.probe.is_healthy()

        self.assertFalse(report.overall_healthy)
        self.assertFalse(report.process.healthy)
        # Model should be skipped
        self.assertIn("Skipped", report.model.message)
        # Responsive should be skipped
        self.assertIn("Skipped", report.responsive.message)

    def test_get_status_returns_none_initially(self):
        """Test get_status returns None before any health check."""
        status = self.probe.get_status()
        self.assertIsNone(status)

    @patch("packages.infrastructure.spine.health.requests.get")
    def test_get_status_returns_report(self, mock_get):
        """Test get_status returns last report after health check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "0.1.20"}
        mock_get.return_value = mock_response
        
        # Use mocked results
        self.probe.check_process = Mock(return_value=HealthResult("process", True, 10.0, "OK"))
        self.probe.check_model = Mock(return_value=HealthResult("model", True, 10.0, "OK"))
        self.probe.check_responsive = Mock(return_value=HealthResult("responsive", True, 10.0, "OK"))

        self.probe.is_healthy()
        status = self.probe.get_status()

        self.assertIsNotNone(status)
        self.assertTrue(status.overall_healthy)

    def test_base_url_strips_trailing_slash(self):
        """Test that base URL strips trailing slashes."""
        probe = SpineHealthProbe(base_url="http://localhost:11434/")
        self.assertEqual(probe.base_url, "http://localhost:11434")


class TestHealthResult(unittest.TestCase):
    """Test HealthResult dataclass."""

    def test_creation(self):
        """Test HealthResult creation."""
        result = HealthResult(
            layer="process",
            healthy=True,
            latency_ms=50.5,
            message="All good",
            details={"key": "value"},
        )
        
        self.assertEqual(result.layer, "process")
        self.assertTrue(result.healthy)
        self.assertEqual(result.latency_ms, 50.5)
        self.assertEqual(result.message, "All good")
        self.assertEqual(result.details, {"key": "value"})


class TestFullHealthReport(unittest.TestCase):
    """Test FullHealthReport dataclass."""

    def test_creation(self):
        """Test FullHealthReport creation with defaults."""
        report = FullHealthReport()
        
        self.assertFalse(report.process.healthy)
        self.assertFalse(report.model.healthy)
        self.assertFalse(report.responsive.healthy)
        self.assertFalse(report.overall_healthy)
        self.assertIsInstance(report.timestamp, float)

    def test_creation_with_values(self):
        """Test FullHealthReport creation with custom values."""
        process = HealthResult("process", True, 10.0, "OK")
        model = HealthResult("model", True, 20.0, "Model loaded")
        responsive = HealthResult("responsive", True, 100.0, "Responds")
        
        report = FullHealthReport(
            process=process,
            model=model,
            responsive=responsive,
            overall_healthy=True,
            timestamp=1234567890.0,
        )
        
        self.assertTrue(report.overall_healthy)
        self.assertEqual(report.timestamp, 1234567890.0)


if __name__ == "__main__":
    unittest.main()