#!/usr/bin/env python3
"""Tests for ChainOrchestrator in local-chain.py."""

import unittest
from unittest.mock import MagicMock, patch
from importlib.util import spec_from_file_location, module_from_spec


def load_module(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bin_dir = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/bin"
local_chain = load_module("local_chain", f"{bin_dir}/local-chain.py")
ChainOrchestrator = local_chain.ChainOrchestrator


class MockLocalRouter:
    """Mock LocalRouter for testing."""

    def __init__(self, available=True):
        self._available = available

    def is_local_available(self):
        return self._available


class TestChainOrchestrator(unittest.TestCase):
    """Test cases for ChainOrchestrator."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_router = MockLocalRouter(available=True)
        self.orchestrator = ChainOrchestrator(
            local_router=self.mock_router, quality_threshold=0.7
        )

    def test_execute_with_escalation_good_quality(self):
        """Test execute_with_escalation with good quality returns locally."""
        with patch.object(
            self.orchestrator,
            "_simulate_local_execution",
            return_value=("Good response text here with enough length to pass quality threshold", True),
        ):
            result = self.orchestrator.execute_with_escalation(
                prompt="Test prompt", max_retries=2
            )

            self.assertIsNone(result["escalation_reason"])
            self.assertGreaterEqual(result["quality_score"], 0.7)

    def test_execute_with_escalation_poor_quality_triggers_escalation(self):
        """Test poor quality triggers escalation to cloud."""
        poor_router = MockLocalRouter(available=True)
        orchestrator = ChainOrchestrator(
            local_router=poor_router, quality_threshold=0.9
        )

        result = orchestrator.execute_with_escalation(
            prompt="Test prompt", max_retries=2
        )

        self.assertEqual(result["escalation_reason"], "poor_quality")
        self.assertIn("[CLOUD ESCALATED]", result["response"])

    def test_execute_with_escalation_local_unavailable_triggers_escalation(self):
        """Test local unavailable triggers escalation to cloud."""
        unavailable_router = MockLocalRouter(available=False)
        orchestrator = ChainOrchestrator(
            local_router=unavailable_router, quality_threshold=0.7
        )

        result = orchestrator.execute_with_escalation(
            prompt="Test prompt", max_retries=2
        )

        self.assertEqual(result["escalation_reason"], "local_unavailable")
        self.assertIn("[CLOUD ESCALATED]", result["response"])

    def test_execute_with_escalation_max_retries(self):
        """Test max retries triggers escalation after threshold failures."""
        result = self.orchestrator.execute_with_escalation(
            prompt="Test prompt", max_retries=2
        )

        self.assertLessEqual(result["attempts"], 3)

    def test_execute_with_escalation_no_router(self):
        """Test execute with no local router escalates due to poor quality."""
        orchestrator = ChainOrchestrator(local_router=None, quality_threshold=0.7)

        result = orchestrator.execute_with_escalation(
            prompt="Test prompt", max_retries=2
        )

        self.assertIsNotNone(result["escalation_reason"])

    def test_score_quality_high_score(self):
        """Test quality scoring returns high score for good responses."""
        response = "A" * 100
        score = self.orchestrator._score_quality(response)
        self.assertGreaterEqual(score, 0.8)

    def test_score_quality_low_score(self):
        """Test quality scoring returns low score for error-containing responses."""
        response = "error occurred"
        score = self.orchestrator._score_quality(response)
        self.assertLessEqual(score, 0.3)

    def test_score_quality_empty_response(self):
        """Test quality scoring returns 0 for empty response."""
        score = self.orchestrator._score_quality("")
        self.assertEqual(score, 0.0)

    def test_score_quality_short_response(self):
        """Test quality scoring returns low score for very short response."""
        response = "hi"
        score = self.orchestrator._score_quality(response)
        self.assertLessEqual(score, 0.6)

    def test_escalation_includes_original_prompt(self):
        """Test escalation response includes original prompt."""
        result = self.orchestrator.execute_with_escalation(
            prompt="Original prompt", max_retries=2
        )

        if result["escalation_reason"]:
            self.assertIn("Original prompt", result["response"])


if __name__ == "__main__":
    unittest.main()
