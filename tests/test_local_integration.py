#!/usr/bin/env python3
"""Integration tests for local LLM routing scripts using subprocess."""

import json
import os
import subprocess
import sys
import unittest

BIN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin"
)


def run_script(
    script_name: str, args: list[str] | None = None, env: dict | None = None
) -> subprocess.CompletedProcess:
    """Run a bin script with subprocess and return the result."""
    cmd = [sys.executable, os.path.join(BIN_DIR, script_name)]
    if args:
        cmd.extend(args)
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=run_env)


class TestLocalRouterClassify(unittest.TestCase):
    """Test local-router.py classify functionality end-to-end."""

    def test_classify_simple_task(self):
        result = run_script("local-router.py", ["--task", "explain what is python"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("simple", result.stdout.strip())

    def test_classify_medium_task(self):
        result = run_script("local-router.py", ["--task", "fix bug in code"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("medium", result.stdout.strip())

    def test_classify_complex_task(self):
        result = run_script(
            "local-router.py", ["--task", "design architecture for new system"]
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("complex", result.stdout.strip())

    def test_classify_json_output(self):
        result = run_script(
            "local-router.py", ["--task", "explain basics", "--format", "json"]
        )
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn("classification", data)
        self.assertIn("task", data)
        self.assertEqual(data["task"], "explain basics")

    def test_classify_unknown_task(self):
        result = run_script("local-router.py", ["--task", "xyzrandom123"])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "unknown")

    def test_health_check_unavailable(self):
        result = run_script("local-router.py", ["--health"])
        self.assertIn("Ollama", result.stdout)

    def test_health_check_json(self):
        result = run_script("local-router.py", ["--health", "--format", "json"])
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn("available", data)
        self.assertIsInstance(data["available"], bool)

    def test_list_models_default(self):
        result = run_script("local-router.py", ["--list-models"])
        self.assertEqual(result.returncode, 0)
        self.assertTrue(len(result.stdout.strip()) > 0)

    def test_list_models_json(self):
        result = run_script("local-router.py", ["--list-models", "--format", "json"])
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn("models", data)
        self.assertIsInstance(data["models"], list)


class TestModelFallback(unittest.TestCase):
    """Test model-fallback.py with local-first routing."""

    def test_test_fallback_mode(self):
        result = run_script("model-fallback.py", ["--test-fallback"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("MODEL FALLBACK TEST MODE", result.stdout)
        self.assertIn("TEST COMPLETE", result.stdout)

    def test_fallback_missing_prompt(self):
        result = run_script("model-fallback.py", [])
        self.assertNotEqual(result.returncode, 0)

    def test_fallback_circuit_breaker_output(self):
        result = run_script("model-fallback.py", ["--test-fallback"])
        self.assertIn("Circuit Breaker State:", result.stdout)
        self.assertIn("failures", result.stdout)

    def test_fallback_with_model_list(self):
        result = run_script(
            "model-fallback.py",
            [
                "--prompt",
                "test prompt",
                "--model-list",
                "ollama/llama3.2:3b",
            ],
        )
        self.assertIn("Failed", result.stdout)
        self.assertIn("Failed models", result.stdout)


class TestModelSelector(unittest.TestCase):
    """Test model-selector.py --local flag."""

    def test_local_flag_text_output(self):
        result = run_script(
            "model-selector.py", ["--task", "explain basics", "--local"]
        )
        self.assertEqual(result.returncode, 0)
        self.assertTrue(len(result.stdout.strip()) > 0)

    def test_local_flag_json_output(self):
        result = run_script(
            "model-selector.py",
            [
                "--task",
                "fix a bug",
                "--local",
                "--format",
                "json",
            ],
        )
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn("model", data)
        self.assertIn("local", data)
        self.assertIsInstance(data["local"], bool)
        self.assertIsInstance(data["local_available"], bool)

    def test_offline_flag(self):
        result = run_script("model-selector.py", ["--task", "test", "--offline"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("ollama", result.stdout.strip())

    def test_default_without_local_flag(self):
        result = run_script("model-selector.py", ["--task", "explain what is python"])
        self.assertEqual(result.returncode, 0)
        self.assertTrue(len(result.stdout.strip()) > 0)

    def test_complexity_override(self):
        result = run_script(
            "model-selector.py",
            [
                "--task",
                "test",
                "--complexity",
                "complex",
                "--format",
                "json",
            ],
        )
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertEqual(data["complexity"], "complex")


class TestModelRouter(unittest.TestCase):
    """Test model-router.py local routing."""

    def test_route_simple_task(self):
        result = run_script(
            "model-router.py", ["--task", "explain what is python", "--format", "json"]
        )
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn("model", data)
        self.assertIn("confidence", data)
        self.assertIn("reason", data)
        self.assertIn("local", data)

    def test_route_coding_task(self):
        result = run_script(
            "model-router.py",
            ["--task", "write code for a function", "--format", "json"],
        )
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn("model", data)
        self.assertGreaterEqual(data["confidence"], 0.0)

    def test_route_empty_task(self):
        result = run_script("model-router.py", ["--task", ""])
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage", result.stdout.lower())

    def test_show_rules_json(self):
        result = run_script("model-router.py", ["--rules", "--format", "json"])
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn("categories", data)
        self.assertIn("models", data)
        self.assertIn("escalation_paths", data)
        self.assertIn("local", data)

    def test_show_rules_text(self):
        result = run_script("model-router.py", ["--rules"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("ROUTING RULES", result.stdout)
        self.assertIn("Categories", result.stdout)

    def test_no_task_shows_help(self):
        result = run_script("model-router.py", [])
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage", result.stdout.lower())


class TestLocalPipelineDryRun(unittest.TestCase):
    """Test local-pipeline.py dry-run mode."""

    def test_dry_run_with_steps(self):
        steps = json.dumps(
            [
                {"task": "Step 1: analyze the code"},
                {"task": "Step 2: summarize findings"},
            ]
        )
        result = run_script("local-pipeline.py", ["--steps", steps, "--dry-run"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Pipeline dry-run", result.stdout)
        self.assertIn("analyze the code", result.stdout)
        self.assertIn("summarize findings", result.stdout)

    def test_dry_run_json_output(self):
        steps = json.dumps(
            [
                {"task": "first step", "model": "llama3.2:3b"},
                {"task": "second step"},
            ]
        )
        result = run_script(
            "local-pipeline.py",
            [
                "--steps",
                steps,
                "--dry-run",
                "--format",
                "json",
            ],
        )
        self.assertEqual(result.returncode, 0)
        json_part = result.stdout.split("\n", 1)[1]
        data = json.loads(json_part)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)

    def test_dry_run_with_file(self):
        import tempfile

        pipeline_data = [{"task": "file-based step"}]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(pipeline_data, f)
            temp_path = f.name
        try:
            result = run_script("local-pipeline.py", ["--file", temp_path, "--dry-run"])
            self.assertEqual(result.returncode, 0)
            self.assertIn("file-based step", result.stdout)
        finally:
            os.unlink(temp_path)

    def test_invalid_steps_json(self):
        result = run_script("local-pipeline.py", ["--steps", "not valid json"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Error", result.stderr)

    def test_no_args_shows_help(self):
        result = run_script("local-pipeline.py", [])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("usage", result.stdout.lower())


class TestLocalChainEscalation(unittest.TestCase):
    """Test local-chain.py escalation behavior."""

    def test_escalation_json_output(self):
        result = run_script(
            "local-chain.py",
            [
                "--prompt",
                "test prompt for escalation",
                "--format",
                "json",
            ],
        )
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn("response", data)
        self.assertIn("quality_score", data)
        self.assertIn("escalation_reason", data)
        self.assertIn("attempts", data)

    def test_escalation_text_output(self):
        result = run_script(
            "local-chain.py",
            [
                "--prompt",
                "hello world",
                "--format",
                "text",
            ],
        )
        self.assertEqual(result.returncode, 0)
        self.assertTrue(len(result.stdout.strip()) > 0)

    def test_custom_threshold(self):
        result = run_script(
            "local-chain.py",
            [
                "--prompt",
                "test with custom threshold",
                "--threshold",
                "0.5",
                "--format",
                "json",
            ],
        )
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn("response", data)

    def test_custom_max_retries(self):
        result = run_script(
            "local-chain.py",
            [
                "--prompt",
                "test retries",
                "--max-retries",
                "1",
                "--format",
                "json",
            ],
        )
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn("attempts", data)

    def test_missing_prompt_fails(self):
        result = run_script("local-chain.py", [])
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
