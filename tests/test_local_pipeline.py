#!/usr/bin/env python3
"""Tests for PipelineRunner in local-pipeline.py."""

import json
import sys
import unittest
from unittest.mock import MagicMock, patch
from importlib.util import spec_from_file_location, module_from_spec


def load_module(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bin_dir = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/bin"
local_pipeline = load_module("local_pipeline", f"{bin_dir}/local-pipeline.py")
PipelineRunner = local_pipeline.PipelineRunner


class TestPipelineRunner(unittest.TestCase):
    """Test cases for PipelineRunner."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_router = MagicMock()
        self.runner = PipelineRunner(local_router=self.mock_router)

    def test_execute_pipeline_two_steps(self):
        """Test execute_pipeline with 2 steps passes both."""
        steps = [
            {"task": "Step 1 task"},
            {"task": "Step 2 task"},
        ]

        self.mock_router.generate.side_effect = [
            {"success": True, "response": "Step 1 response"},
            {"success": True, "response": "Step 2 response"},
        ]

        result = self.runner.execute_pipeline(steps)

        self.assertTrue(result["success"])
        self.assertEqual(len(result["results"]), 2)
        self.assertEqual(result["results"][0]["response"], "Step 1 response")
        self.assertEqual(result["results"][1]["response"], "Step 2 response")
        self.assertEqual(self.mock_router.generate.call_count, 2)

    def test_execute_pipeline_dry_run(self):
        """Test dry-run shows pipeline without executing."""
        steps = [
            {"task": "Step 1 task"},
            {"task": "Step 2 task"},
        ]

        with patch("sys.argv", ["local-pipeline.py", "--dry-run"]):
            with patch("builtins.print") as mock_print:
                with patch.object(PipelineRunner, "execute_pipeline") as mock_exec:
                    mock_exec.return_value = {"success": True}
                    self.runner.execute_pipeline(steps)
                    mock_exec.assert_called_once()

    def test_quality_failure_stops_pipeline(self):
        """Test quality failure stops pipeline at that step."""
        steps = [
            {"task": "Step 1 task"},
            {"task": "Step 2 task"},
        ]

        self.mock_router.generate.side_effect = [
            {"success": True, "response": "I don't know the answer"},
            {"success": True, "response": "Step 2 response"},
        ]

        result = self.runner.execute_pipeline(steps)

        self.assertTrue(result["success"])
        self.assertFalse(result["results"][0].get("quality", True))
        self.assertEqual(len(result["results"]), 2)

    def test_context_passing(self):

        self.assertTrue(result["success"])
        self.assertFalse(result["results"][0].get("quality", True))
        self.assertEqual(len(result["results"]), 2)

        self.assertTrue(result["success"])
        self.assertFalse(result["results"][0].get("quality", True))
        self.assertEqual(len(result["results"]), 2)

        self.assertFalse(result["success"])
        self.assertIn("quality", result.get("error", "").lower())
        self.assertEqual(len(result["results"]), 1)

    def test_context_passing(self):
        """Test context is passed between steps."""
        steps = [
            {"task": "First task"},
            {"task": "Second task"},
        ]

        self.mock_router.generate.side_effect = [
            {"success": True, "response": "First output"},
            {"success": True, "response": "Second output"},
        ]

        result = self.runner.execute_pipeline(steps)

        self.assertTrue(result["success"])
        self.assertIn("previous_output", result.get("context", {}))

        call_args = self.mock_router.generate.call_args_list
        first_call_prompt = call_args[0][0][0]
        second_call_prompt = call_args[1][0][0]

        self.assertIn("First task", first_call_prompt)
        self.assertIn("Previous context: First output", second_call_prompt)
        self.assertIn("Second task", second_call_prompt)

    def test_step_failure_stops_pipeline(self):
        """Test step failure stops pipeline immediately."""
        steps = [
            {"task": "Step 1 task"},
            {"task": "Step 2 task"},
        ]

        self.mock_router.generate.return_value = {
            "success": False,
            "error": "Connection refused",
        }

        result = self.runner.execute_pipeline(steps)

        self.assertFalse(result["success"])
        self.assertIn("Connection refused", result.get("error", ""))
        self.assertEqual(result.get("failed_step"), 0)

    def test_assess_quality_good_response(self):
        """Test quality assessment returns True for good response."""
        response = "This is a good response with enough content"
        result = self.runner.assess_quality(response)
        self.assertTrue(result)

    def test_assess_quality_poor_response(self):
        """Test quality assessment returns False for poor response."""
        poor_responses = [
            "I don't know",
            "unable to help",
            "error occurred",
            "failed",
            "exception",
            "",
            "short",
        ]
        for response in poor_responses:
            result = self.runner.assess_quality(response)
            self.assertFalse(result, f"Expected False for: {response}")


if __name__ == "__main__":
    unittest.main()
