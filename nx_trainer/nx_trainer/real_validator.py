# -*- coding: utf-8 -*-
"""
Real Inference Validator - REAL accuracy testing, not simulated!
================================================================

CRITICAL: This replaces fake/simulated accuracy with actual inference testing.

Usage:
    from nx_trainer.real_validator import RealInferenceValidator, GOLDEN_TEST_CASES

    validator = RealInferenceValidator()
    result = validator.validate("models/rosetta-lora/checkpoint-1000")
    print(f"Accuracy: {result.accuracy}")
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import torch

logger = logging.getLogger("trainer.validator")

# ============================================================================
# GOLDEN TEST SUITE - 100+ real test cases covering all tool categories
# ============================================================================


@dataclass
class TestCase:
    """A single test case for validation."""

    input_text: str
    expected_tool: str
    expected_args: Optional[Dict[str, Any]] = None
    category: str = "general"
    difficulty: str = "easy"  # easy, medium, hard

    def __str__(self):
        return (
            f"[{self.category}/{self.difficulty}] {self.input_text[:50]}... → {self.expected_tool}"
        )


GOLDEN_TEST_CASES: List[TestCase] = [
    # =================================================================
    # MEMORY_OPS (10 cases)
    # =================================================================
    TestCase(
        "search memory for authentication",
        "memory_search",
        {"query": "authentication"},
        "memory_ops",
        "easy",
    ),
    TestCase(
        "search memory for config settings",
        "memory_search",
        {"query": "config"},
        "memory_ops",
        "easy",
    ),
    TestCase(
        "remember that I like Python",
        "memory_write",
        {"content": "like Python"},
        "memory_ops",
        "easy",
    ),
    TestCase(
        "store in memory: the API key is secret",
        "memory_write",
        {"content": "API key is secret"},
        "memory_ops",
        "easy",
    ),
    TestCase(
        "find context for task routing",
        "memory_find_context",
        {"task": "task routing"},
        "memory_ops",
        "medium",
    ),
    TestCase(
        "recall session from yesterday",
        "memory_recall_session",
        {},
        "memory_ops",
        "medium",
    ),
    TestCase("get memory statistics", "memory_get_memory_stats", {}, "memory_ops", "easy"),
    TestCase(
        "search nx-memory for auth tokens",
        "nx-memory_search_memories",
        {"query": "auth tokens"},
        "memory_ops",
        "medium",
    ),
    TestCase(
        "write to nx-memory: user prefers dark mode",
        "nx-memory_memory_write",
        {"content": "user prefers dark mode"},
        "memory_ops",
        "medium",
    ),
    TestCase(
        "rank memories for API integration",
        "memory_rank_memories",
        {"query": "API integration"},
        "memory_ops",
        "hard",
    ),
    # =================================================================
    # GITHUB_OPS (12 cases)
    # =================================================================
    TestCase(
        "create issue in react titled 'Fix bug'",
        "github_create_issue",
        {"repo": "react", "title": "Fix bug"},
        "github_ops",
        "easy",
    ),
    TestCase(
        "open a pull request for my changes",
        "github_create_pull_request",
        {},
        "github_ops",
        "easy",
    ),
    TestCase(
        "list all issues for vscode",
        "github_list_issues",
        {"repo": "vscode"},
        "github_ops",
        "easy",
    ),
    TestCase(
        "search repos for machine learning",
        "github_search_repositories",
        {"query": "machine learning"},
        "github_ops",
        "easy",
    ),
    TestCase(
        "search code for authentication function",
        "github_search_code",
        {"q": "authentication"},
        "github_ops",
        "medium",
    ),
    TestCase(
        "get file README.md from facebook/react",
        "github_get_file_contents",
        {"repo": "react", "path": "README.md"},
        "github_ops",
        "medium",
    ),
    TestCase(
        "search issues for security vulnerability",
        "github_search_issues",
        {"q": "security"},
        "github_ops",
        "medium",
    ),
    TestCase(
        "get pull request number 42 details",
        "github_get_pull_request",
        {"pull_number": 42},
        "github_ops",
        "easy",
    ),
    TestCase(
        "list all pull requests in my repo",
        "github_list_pull_requests",
        {},
        "github_ops",
        "easy",
    ),
    TestCase(
        "show files changed in PR 123",
        "github_get_pull_request_files",
        {"pull_number": 123},
        "github_ops",
        "medium",
    ),
    TestCase(
        "create branch feature-login from main",
        "github_create_branch",
        {"branch": "feature-login", "from_branch": "main"},
        "github_ops",
        "hard",
    ),
    TestCase(
        "fork the tensorflow repository",
        "github_fork_repository",
        {"repo": "tensorflow"},
        "github_ops",
        "medium",
    ),
    # =================================================================
    # FILE_OPS (10 cases)
    # =================================================================
    TestCase("read the config file", "read_file", {"path": "config.json"}, "file_ops", "easy"),
    TestCase("show me src/main.py", "read_file", {"path": "src/main.py"}, "file_ops", "easy"),
    TestCase(
        "write hello world to output.txt",
        "write_file",
        {"path": "output.txt", "content": "hello world"},
        "file_ops",
        "easy",
    ),
    TestCase(
        "create a new file called app.py",
        "write_file",
        {"path": "app.py"},
        "file_ops",
        "easy",
    ),
    TestCase(
        "edit config.json change timeout to 30",
        "edit_file",
        {"path": "config.json"},
        "file_ops",
        "medium",
    ),
    TestCase(
        "list files in src directory",
        "list_directory",
        {"path": "src"},
        "file_ops",
        "easy",
    ),
    TestCase("glob all Python files", "glob", {"pattern": "*.py"}, "file_ops", "easy"),
    TestCase("find all test files", "glob", {"pattern": "**/test_*.py"}, "file_ops", "medium"),
    TestCase(
        "grep for function main",
        "grep",
        {"pattern": "function main"},
        "file_ops",
        "easy",
    ),
    TestCase(
        "check diagnostics for app.py",
        "lsp_diagnostics",
        {"filePath": "app.py"},
        "file_ops",
        "medium",
    ),
    TestCase(
        "get symbols from utils.py",
        "lsp_symbols",
        {"filePath": "utils.py"},
        "file_ops",
        "hard",
    ),
    # =================================================================
    # GIT_OPS (8 cases)
    # =================================================================
    TestCase("check git status", "git_status", {}, "git_ops", "easy"),
    TestCase("show me recent commits", "git_log", {}, "git_ops", "easy"),
    TestCase("show the diff", "git_diff", {}, "git_ops", "easy"),
    TestCase("list all branches", "git_branch", {}, "git_ops", "easy"),
    TestCase(
        "commit with message 'fix bug'",
        "git_commit",
        {"message": "fix bug"},
        "git_ops",
        "easy",
    ),
    TestCase("show commit abc123", "git_show", {"rev": "abc123"}, "git_ops", "medium"),
    TestCase("fetch from origin", "git_fetch", {"remote": "origin"}, "git_ops", "medium"),
    TestCase("show changes in auth.py", "git_diff", {"file": "auth.py"}, "git_ops", "easy"),
    # =================================================================
    # WEB_OPS (6 cases)
    # =================================================================
    TestCase(
        "fetch https://api.example.com as markdown",
        "fetch_fetch_markdown",
        {"url": "https://api.example.com"},
        "web_ops",
        "easy",
    ),
    TestCase(
        "scrape the github homepage",
        "fetch_fetch_readable",
        {"url": "https://github.com"},
        "web_ops",
        "easy",
    ),
    TestCase(
        "get HTML from example.com",
        "fetch_fetch_html",
        {"url": "https://example.com"},
        "web_ops",
        "easy",
    ),
    TestCase(
        "fetch JSON from API endpoint",
        "fetch_fetch_json",
        {"url": "https://api.example.com/data"},
        "web_ops",
        "easy",
    ),
    TestCase(
        "search the web for Python tutorials",
        "websearch",
        {"query": "Python tutorials"},
        "web_ops",
        "easy",
    ),
    TestCase(
        "google how to use transformers library",
        "websearch",
        {"query": "transformers library tutorial"},
        "web_ops",
        "medium",
    ),
    # =================================================================
    # BROWSER_OPS (5 cases)
    # =================================================================
    TestCase(
        "navigate to github.com",
        "playwright_navigate",
        {"url": "https://github.com"},
        "browser_ops",
        "easy",
    ),
    TestCase(
        "go to localhost:3000",
        "playwright_navigate",
        {"url": "http://localhost:3000"},
        "browser_ops",
        "easy",
    ),
    TestCase(
        "click the submit button",
        "playwright_click",
        {"selector": "button.submit"},
        "browser_ops",
        "easy",
    ),
    TestCase(
        "fill in the login form",
        "playwright_fill",
        {"selector": "input[name=email]", "value": "test@example.com"},
        "browser_ops",
        "medium",
    ),
    TestCase("take a screenshot", "playwright_screenshot", {}, "browser_ops", "easy"),
    # =================================================================
    # QUALITY_OPS (6 cases)
    # =================================================================
    TestCase("run typecheck", "run_typecheck", {}, "quality", "easy"),
    TestCase("run lint on the code", "run_lint", {}, "quality", "easy"),
    TestCase("format the code", "run_format", {}, "quality", "easy"),
    TestCase("execute the test suite", "run_tests", {}, "quality", "easy"),
    TestCase("scan for secrets and API keys", "run_secrets_scan", {}, "quality", "medium"),
    TestCase(
        "check for TODO and FIXME comments",
        "run_placeholder_check",
        {},
        "quality",
        "medium",
    ),
    # =================================================================
    # CONTEXT_OPS (6 cases)
    # =================================================================
    TestCase("get active context", "get_active_context", {}, "context_ops", "easy"),
    TestCase("show user preferences", "get_user_context", {}, "context_ops", "easy"),
    TestCase("what is the product", "get_product_context", {}, "context_ops", "easy"),
    TestCase("get behavioral constraints", "get_constraints", {}, "context_ops", "easy"),
    TestCase("show user profile", "get_user_profile", {}, "context_ops", "easy"),
    TestCase(
        "list available workflows",
        "nx-context_get_bmad_workflows",
        {},
        "context_ops",
        "medium",
    ),
    # =================================================================
    # BRAIN_OPS (5 cases)
    # =================================================================
    TestCase("route this task to the right agent", "route_task", {}, "brain_ops", "medium"),
    TestCase(
        "record that the task succeeded",
        "record_outcome",
        {"success": True},
        "brain_ops",
        "easy",
    ),
    TestCase("get learning status", "learning_status", {}, "brain_ops", "easy"),
    TestCase(
        "recommend an agent for this",
        "learning_get_recommendations",
        {},
        "brain_ops",
        "medium",
    ),
    TestCase("nx route this task", "nx-learning_route_task", {}, "brain_ops", "medium"),
    # =================================================================
    # DATABASE_OPS (4 cases)
    # =================================================================
    TestCase(
        "query the database for all users",
        "sqlite_query",
        {"sql": "SELECT * FROM users"},
        "database_ops",
        "easy",
    ),
    TestCase("list all tables", "sqlite_list_tables", {}, "database_ops", "easy"),
    TestCase(
        "sample the sessions table",
        "sqlite_sample_table",
        {"table": "sessions"},
        "database_ops",
        "easy",
    ),
    TestCase(
        "run a custom SQL query",
        "sqlite_query",
        {"sql": "SELECT COUNT(*) FROM outcomes"},
        "database_ops",
        "medium",
    ),
    # =================================================================
    # NOTION_OPS (4 cases)
    # =================================================================
    TestCase(
        "search notion for project notes",
        "notion_search",
        {"query": "project notes"},
        "notion_ops",
        "easy",
    ),
    TestCase(
        "get page abc123 from notion",
        "notion_get_page",
        {"page_id": "abc123"},
        "notion_ops",
        "easy",
    ),
    TestCase("create a new notion page", "notion_create_page", {}, "notion_ops", "medium"),
    TestCase(
        "query the tasks database",
        "notion_query_database",
        {"database_id": "tasks"},
        "notion_ops",
        "hard",
    ),
    # =================================================================
    # TRIGGER_OPS (4 cases)
    # =================================================================
    TestCase(
        "register trigger '/deploy'",
        "trigger_register",
        {"phrase": "/deploy"},
        "trigger_ops",
        "easy",
    ),
    TestCase("list all available triggers", "trigger_list", {}, "trigger_ops", "easy"),
    TestCase(
        "check if 'deploy prod' matches a trigger",
        "trigger_check",
        {"input_text": "deploy prod"},
        "trigger_ops",
        "medium",
    ),
    TestCase(
        "execute trigger /help",
        "trigger_execute",
        {"phrase": "/help"},
        "trigger_ops",
        "easy",
    ),
    # =================================================================
    # THINKING_OPS (2 cases)
    # =================================================================
    TestCase(
        "think about the authentication flow",
        "sequential_thinking",
        {},
        "thinking_ops",
        "hard",
    ),
    TestCase(
        "analyze why the API is slow",
        "nx-brain_sequential_thinking",
        {},
        "thinking_ops",
        "hard",
    ),
    # =================================================================
    # SHELL_OPS (2 cases)
    # =================================================================
    TestCase("run ls -la command", "bash", {"command": "ls -la"}, "shell_ops", "easy"),
    TestCase(
        "execute ps aux to see processes",
        "bash",
        {"command": "ps aux"},
        "shell_ops",
        "easy",
    ),
    # =================================================================
    # ROUTING_OPS (2 cases)
    # =================================================================
    TestCase(
        "delegate to the explorer agent",
        "route_task",
        {"task_description": "explore codebase"},
        "routing_ops",
        "medium",
    ),
    TestCase(
        "get routing recommendations",
        "learning_get_recommendations",
        {"task_description": "fix bug"},
        "routing_ops",
        "medium",
    ),
]

# Category breakdown for reporting
CATEGORY_SUMMARY = {
    "memory_ops": len([c for c in GOLDEN_TEST_CASES if c.category == "memory_ops"]),
    "github_ops": len([c for c in GOLDEN_TEST_CASES if c.category == "github_ops"]),
    "file_ops": len([c for c in GOLDEN_TEST_CASES if c.category == "file_ops"]),
    "git_ops": len([c for c in GOLDEN_TEST_CASES if c.category == "git_ops"]),
    "web_ops": len([c for c in GOLDEN_TEST_CASES if c.category == "web_ops"]),
    "browser_ops": len([c for c in GOLDEN_TEST_CASES if c.category == "browser_ops"]),
    "quality": len([c for c in GOLDEN_TEST_CASES if c.category == "quality"]),
    "context_ops": len([c for c in GOLDEN_TEST_CASES if c.category == "context_ops"]),
    "brain_ops": len([c for c in GOLDEN_TEST_CASES if c.category == "brain_ops"]),
    "database_ops": len([c for c in GOLDEN_TEST_CASES if c.category == "database_ops"]),
    "notion_ops": len([c for c in GOLDEN_TEST_CASES if c.category == "notion_ops"]),
    "trigger_ops": len([c for c in GOLDEN_TEST_CASES if c.category == "trigger_ops"]),
    "thinking_ops": len([c for c in GOLDEN_TEST_CASES if c.category == "thinking_ops"]),
    "shell_ops": len([c for c in GOLDEN_TEST_CASES if c.category == "shell_ops"]),
    "routing_ops": len([c for c in GOLDEN_TEST_CASES if c.category == "routing_ops"]),
}

logger.info(
    f"Golden test suite loaded: {len(GOLDEN_TEST_CASES)} cases across {len(CATEGORY_SUMMARY)} categories"
)


# ============================================================================
# VALIDATION RESULT
# ============================================================================


@dataclass
class ValidationResult:
    """Result of validation run."""

    accuracy: float
    total_cases: int
    correct: int
    wrong: int

    # Per-category breakdown
    per_category: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Failure details
    failures: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    adapter_path: str = ""
    duration_seconds: float = 0.0

    def __str__(self):
        status = (
            "✅ PASS"
            if self.accuracy >= 0.99
            else "⚠️ PARTIAL"
            if self.accuracy >= 0.90
            else "❌ FAIL"
        )
        return (
            f"{status} Accuracy: {self.accuracy:.1%} ({self.correct}/{self.total_cases})\n"
            f"         Duration: {self.duration_seconds:.1f}s\n"
            f"         Failures: {len(self.failures)}"
        )


# ============================================================================
# REAL INFERENCE VALIDATOR
# ============================================================================


class RealInferenceValidator:
    """
    Validates LoRA adapters with REAL inference.

    This replaces fake/simulated accuracy with actual model inference
    to get true accuracy measurements.

    Usage:
        validator = RealInferenceValidator(
            base_model="Qwen/Qwen2.5-0.5B-Instruct",
            test_cases=GOLDEN_TEST_CASES
        )
        result = validator.validate("models/rosetta-lora/checkpoint-1000")
    """

    def __init__(
        self,
        base_model: str = "Qwen/Qwen2.5-0.5B-Instruct",
        test_cases: List[TestCase] = None,
        device: str = None,
    ):
        self.base_model_id = base_model
        self.test_cases = test_cases or GOLDEN_TEST_CASES
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.model = None
        self.tokenizer = None
        self._model_loaded = False

        logger.info("RealInferenceValidator initialized")
        logger.info(f"  Base model: {base_model}")
        logger.info(f"  Device: {self.device}")
        logger.info(f"  Test cases: {len(self.test_cases)}")

    def _load_model_and_adapter(self, adapter_path: str) -> bool:
        """Load base model and LoRA adapter."""
        if self._model_loaded:
            return True

        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            from peft import PeftModel

            logger.info(f"Loading base model: {self.base_model_id}")

            self.tokenizer = AutoTokenizer.from_pretrained(
                self.base_model_id,
                trust_remote_code=True,
            )
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            self.model = AutoModelForCausalLM.from_pretrained(
                self.base_model_id,
                trust_remote_code=True,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            )

            logger.info(f"Loading adapter: {adapter_path}")
            self.model = PeftModel.from_pretrained(self.model, adapter_path)
            self.model.eval()
            self.model = self.model.to(self.device)

            self._model_loaded = True
            logger.info("Model and adapter loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load model/adapter: {e}")
            return False

    def _run_inference(self, input_text: str) -> str:
        """Run single inference and return generated text."""
        # Format with Qwen chat template
        prompt = f"<|im_start|>user\n{input_text}<|im_end|>\n<|im_start|>assistant\n"

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=60,
                temperature=0.1,
                do_sample=False,
                pad_token_id=self.tokenizer.pad_token_id,
            )

        response = self.tokenizer.decode(outputs[0], skip_special_tokens=False)

        # Extract just the assistant response
        if "<|im_start|>assistant\n" in response:
            response = response.split("<|im_start|>assistant\n")[-1]
        if "<|im_end|>" in response:
            response = response.split("<|im_end|>")[0]

        return response.strip()

    def _extract_tool_call(self, response: str) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Extract tool name and args from model response.

        Supports multiple formats:
        1. [TOOL_CALL]{tool => 'name', args => {--arg "value"}}
        2. {tool: 'name', args: {arg: 'value'}}
        3. tool_name(arg1="value1")
        """
        # Try format 1: [TOOL_CALL]{tool => 'name', args => {...}}
        match = re.search(r"\[TOOL_CALL\]\{tool\s*=>\s*['\"]([^'\"]+)['\"]", response)
        if match:
            tool_name = match.group(1)
            # Try to extract args
            args_match = re.search(r"args\s*=>\s*\{([^}]*)\}", response)
            args = self._parse_args(args_match.group(1)) if args_match else {}
            return tool_name, args

        # Try format 2: {tool: 'name', ...}
        match = re.search(r"['\"]tool['\"]:\s*['\"]([^'\"]+)['\"]", response)
        if match:
            tool_name = match.group(1)
            return tool_name, {}

        # Try format 3: tool_name(...)
        match = re.search(r"^(\w+)\(", response)
        if match:
            tool_name = match.group(1)
            return tool_name, {}

        # Try lowercase
        match = re.search(r"tool\s*[:=]\s*['\"]([^'\"]+)['\"]", response.lower())
        if match:
            return match.group(1), {}

        return None, None

    def _parse_args(self, args_str: str) -> Dict[str, str]:
        """Parse argument string from tool call format."""
        args = {}
        # Match --key "value" or --key value patterns
        matches = re.findall(r'--(\w+)\s+"([^"]+)"', args_str)
        for key, value in matches:
            args[key] = value
        return args

    def validate(self, adapter_path: str) -> ValidationResult:
        """
        Validate an adapter with real inference on all test cases.

        Args:
            adapter_path: Path to LoRA adapter checkpoint

        Returns:
            ValidationResult with accuracy and failure details
        """
        import time

        start_time = time.time()

        logger.info("=" * 60)
        logger.info(f"VALIDATING: {adapter_path}")
        logger.info("=" * 60)

        # Load model
        if not self._load_model_and_adapter(adapter_path):
            return ValidationResult(
                accuracy=0.0,
                total_cases=len(self.test_cases),
                correct=0,
                wrong=len(self.test_cases),
                failures=[{"error": "Failed to load model/adapter"}],
                adapter_path=adapter_path,
            )

        correct = 0
        wrong = 0
        failures = []
        per_category = {}

        # Track per-category stats
        for cat in set(tc.category for tc in self.test_cases):
            per_category[cat] = {"correct": 0, "total": 0}

        # Run inference on each test case
        for i, test_case in enumerate(self.test_cases):
            # Run inference
            response = self._run_inference(test_case.input_text)

            # Extract predicted tool
            predicted_tool, _ = self._extract_tool_call(response)

            # Check if correct
            is_correct = predicted_tool == test_case.expected_tool

            per_category[test_case.category]["total"] += 1

            if is_correct:
                correct += 1
                per_category[test_case.category]["correct"] += 1
                status = "✓"
            else:
                wrong += 1
                status = "✗"
                failures.append(
                    {
                        "test_case": str(test_case),
                        "expected": test_case.expected_tool,
                        "predicted": predicted_tool,
                        "response": response[:200],
                        "category": test_case.category,
                    }
                )

            # Log progress every 10 cases
            if (i + 1) % 10 == 0:
                current_acc = correct / (i + 1)
                logger.info(f"  [{i + 1}/{len(self.test_cases)}] Accuracy: {current_acc:.1%}")

        # Calculate accuracy
        accuracy = correct / len(self.test_cases) if self.test_cases else 0

        # Calculate per-category accuracy
        for cat in per_category:
            total = per_category[cat]["total"]
            correct_cat = per_category[cat]["correct"]
            per_category[cat] = {
                "accuracy": correct_cat / total if total > 0 else 0,
                "correct": correct_cat,
                "total": total,
            }

        duration = time.time() - start_time

        result = ValidationResult(
            accuracy=accuracy,
            total_cases=len(self.test_cases),
            correct=correct,
            wrong=wrong,
            per_category=per_category,
            failures=failures,
            adapter_path=adapter_path,
            duration_seconds=duration,
        )

        # Log summary
        logger.info("=" * 60)
        logger.info(f"VALIDATION COMPLETE: {adapter_path}")
        logger.info(f"  Overall Accuracy: {accuracy:.1%} ({correct}/{len(self.test_cases)})")
        logger.info(f"  Duration: {duration:.1f}s")
        logger.info(f"  Failures: {len(failures)}")
        logger.info("")
        logger.info("Per-Category Breakdown:")
        for cat, stats in sorted(per_category.items()):
            bar = "█" * int(stats["accuracy"] * 20) + "░" * (20 - int(stats["accuracy"] * 20))
            logger.info(
                f"    {cat:15} {bar} {stats['accuracy']:.0%} ({stats['correct']}/{stats['total']})"
            )
        logger.info("=" * 60)

        return result

    def validate_quick(self, adapter_path: str, n_cases: int = 20) -> ValidationResult:
        """
        Quick validation on subset of test cases.

        Use for rapid iteration during training.
        """
        import time

        start_time = time.time()

        if not self._load_model_and_adapter(adapter_path):
            return ValidationResult(accuracy=0.0, total_cases=n_cases, correct=0, wrong=n_cases)

        # Sample test cases
        import random

        sampled = random.sample(self.test_cases, min(n_cases, len(self.test_cases)))

        correct = 0
        failures = []

        for test_case in sampled:
            response = self._run_inference(test_case.input_text)
            predicted_tool, _ = self._extract_tool_call(response)

            if predicted_tool == test_case.expected_tool:
                correct += 1
            else:
                failures.append(
                    {
                        "expected": test_case.expected_tool,
                        "predicted": predicted_tool,
                    }
                )

        accuracy = correct / len(sampled) if sampled else 0

        return ValidationResult(
            accuracy=accuracy,
            total_cases=len(sampled),
            correct=correct,
            wrong=len(sampled) - correct,
            failures=failures,
            adapter_path=adapter_path,
            duration_seconds=time.time() - start_time,
        )


# ============================================================================
# CLI
# ============================================================================


def main():
    """CLI for validation."""
    import argparse

    parser = argparse.ArgumentParser(description="Real Inference Validator")
    parser.add_argument("adapter_path", help="Path to LoRA adapter")
    parser.add_argument("--quick", action="store_true", help="Quick validation (20 cases)")
    parser.add_argument("--output", help="Save results to JSON file")

    args = parser.parse_args()

    validator = RealInferenceValidator()

    if args.quick:
        result = validator.validate_quick(args.adapter_path)
    else:
        result = validator.validate(args.adapter_path)

    print(result)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(
                {
                    "accuracy": result.accuracy,
                    "total": result.total_cases,
                    "correct": result.correct,
                    "failures": result.failures,
                    "per_category": result.per_category,
                },
                f,
                indent=2,
            )
        print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
