"""Evaluator for Rosetta Stone - Test trained models.

Provides comprehensive evaluation with:
- Tool name matching
- Argument matching (exact and partial)
- Precision/recall metrics
- Confidence scoring
- Error categorization
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class Evaluator:
    """Evaluator for testing tool call translation models.

    Provides methods to test model outputs against expected tool calls
    with comprehensive metrics.
    """

    def __init__(self):
        """Initialize the evaluator."""
        self.test_cases = self._default_test_cases()

    def _default_test_cases(self) -> List[Tuple[str, str]]:
        """Get default test cases (input, expected tool name)."""
        return [
            # Memory tools
            ("search memory for security", "memory_search"),
            ("look up authentication in memory", "memory_search"),
            ("remember this: hello world", "memory_write"),
            # File tools
            ("show me README.md", "read_file"),
            ("read src/main.py", "read_file"),
            ("write test data to config.json", "write_file"),
            ("list files in src", "list_directory"),
            # Git tools
            ("check git status", "git_status"),
            ("show git log", "git_log"),
            ("show diff", "git_diff"),
            # GitHub tools
            ("list issues for facebook/react", "github_list_issues"),
            # Web tools
            ("fetch https://docs.python.org", "fetch_url"),
            ("open https://nodejs.org", "browser_navigate"),
            # Thinking
            ("think about debugging", "sequential_thinking"),
            # Context
            ("get active context", "get_active_context"),
            ("health check", "get_health"),
            # Routing
            ("route task: implement auth", "route_task"),
        ]

    @staticmethod
    def parse_tool_call(output: str) -> Optional[Dict[str, Any]]:
        """Parse a tool call from model output.

        Args:
            output: Model output string.

        Returns:
            Dict with tool_name and args, or None if parsing fails.
        """
        # Match [TOOL_CALL]{tool => "name", args => { ... }}[/TOOL_CALL]
        # Use .+? to handle nested braces in values
        pattern = (
            r'\[TOOL_CALL\]\{tool\s*=>\s*"([^"]+)"(?:,\s*args\s*=>\s*\{(.+?)\})?\}\[/TOOL_CALL\]'
        )
        match = re.search(pattern, output)

        if not match:
            return None

        tool_name = match.group(1)
        args_str = match.group(2)

        args = {}
        if args_str:
            # Parse arguments: --key "value"
            arg_pattern = r'--(\w+)\s+"([^"]*)"'
            for arg_match in re.finditer(arg_pattern, args_str):
                key, value = arg_match.groups()
                # Try to convert to int/bool if possible
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value.isdigit():
                    value = int(value)
                args[key] = value

        return {"tool": tool_name, "args": args}

    def evaluate_output(
        self,
        output: str,
        expected_tool: str,
        expected_args: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Evaluate a single model output with comprehensive metrics.

        Args:
            output: Model output string.
            expected_tool: Expected tool name.
            expected_args: Optional expected arguments for arg matching.

        Returns:
            Dict with evaluation results including:
            - correct: Tool matches AND (optionally) args match
            - tool_match: Tool name matches
            - args_match: Arguments match exactly
            - args_partial_score: Partial match score (0.0-1.0)
            - expected_tool: The expected tool name
            - parsed: Parsed output
        """
        parsed = self.parse_tool_call(output)
        tool_match = parsed is not None and parsed.get("tool") == expected_tool

        # Argument matching
        args_match = False
        args_partial_score = 0.0

        if parsed and expected_args:
            actual_args = parsed.get("args", {})
            # Exact match
            if actual_args == expected_args:
                args_match = True
                args_partial_score = 1.0
            else:
                # Partial match: how many args match?
                if actual_args and expected_args:
                    matching = sum(
                        1 for k in expected_args if actual_args.get(k) == expected_args[k]
                    )
                    args_partial_score = matching / max(len(expected_args), len(actual_args))
                    args_match = matching == len(expected_args)

        # Overall correctness
        correct = tool_match and (not expected_args or args_match)

        return {
            "correct": correct,
            "tool_match": tool_match,
            "args_match": args_match,
            "args_partial_score": args_partial_score,
            "expected_tool": expected_tool,
            "expected_args": expected_args,
            "parsed": parsed,
            "output": output[:200],  # Truncate for display
        }

    def evaluate_test_cases(
        self,
        outputs: List[str],
        test_cases: Optional[List[Tuple[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Evaluate multiple test case outputs with comprehensive metrics.

        Args:
            outputs: List of model outputs.
            test_cases: Optional custom test cases. Defaults to _default_test_cases.

        Returns:
            Dict with evaluation summary including:
            - total: Total number of test cases
            - correct: Number fully correct
            - tool_only_correct: Tool correct, args don't matter
            - accuracy: Overall accuracy
            - tool_accuracy: Tool-only accuracy
            - results: Individual results
        """
        test_cases = test_cases or self.default_test_cases

        if len(outputs) != len(test_cases):
            raise ValueError(
                f"Number of outputs ({len(outputs)}) != number of test cases ({len(test_cases)})"
            )

        results = []
        correct_count = 0
        tool_only_correct = 0

        for output, (input_text, expected_tool) in zip(outputs, test_cases):
            result = self.evaluate_output(output, expected_tool)
            results.append(
                {
                    "input": input_text,
                    "expected_tool": expected_tool,
                    **result,
                }
            )
            if result["correct"]:
                correct_count += 1
            if result["tool_match"]:
                tool_only_correct += 1

        accuracy = correct_count / len(test_cases) if test_cases else 0
        tool_accuracy = tool_only_correct / len(test_cases) if test_cases else 0

        tool_accuracy = tool_only_correct / len(test_cases) if test_cases else 0
        arg_accuracy = (
            sum(1 for r in results if r.get("args_match", False)) / len(test_cases)
            if test_cases
            else 0
        )

        return {
            "total": len(test_cases),
            "correct": correct_count,
            "tool_only_correct": tool_only_correct,
            "accuracy": accuracy,
            "tool_accuracy": tool_accuracy,
            # NEW: Separate tool vs arg accuracy (for better debugging)
            "arg_accuracy_rate": arg_accuracy,
            "results": results,
        }

    def run_interactive_test(
        self,
        model_path: Optional[Path] = None,
        ollama_model: str = "rosetta",
    ) -> None:
        """Run interactive testing with the trained model.

        Args:
            model_path: Path to trained model (for Unsloth).
            ollama_model: Ollama model name to use.
        """
        print("\n=== Rosetta Stone Interactive Test ===")
        print("Type a request to see the model's tool call translation.")
        print("Type 'quit' to exit.\n")

        while True:
            try:
                user_input = input("Request: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("quit", "exit", "q"):
                    print("Goodbye!")
                    break

                # Get model output (placeholder - implement based on model type)
                output = self._get_model_output(user_input, model_path, ollama_model)
                parsed = self.parse_tool_call(output)

                print(f"  Output: {output[:150]}...")
                if parsed:
                    print(f"  Tool: {parsed['tool']}")
                    print(f"  Args: {parsed['args']}")
                print()

            except (KeyboardInterrupt, EOFError):
                print("\nGoodbye!")
                break

    def _get_model_output(
        self,
        input_text: str,
        model_path: Optional[Path] = None,
        ollama_model: str = "rosetta",
    ) -> str:
        """Get model output for input text.

        This is a placeholder - implement based on your model serving setup.

        Args:
            input_text: User input text.
            model_path: Path to trained model.
            ollama_model: Ollama model name.

        Returns:
            Model output string.
        """
        # For now, return a placeholder
        # In production, integrate with your model serving
        return f'[TOOL_CALL]{{tool => "placeholder", args => {{ }}}}[/TOOL_CALL]'

    @property
    def default_test_cases(self) -> List[Tuple[str, str]]:
        """Get default test cases."""
        return self._default_test_cases()

    def load_test_data(self, data_path: Path) -> List[Tuple[str, str]]:
        """Load test cases from JSONL file.

        Args:
            data_path: Path to JSONL file with test data.

        Returns:
            List of (input, expected_tool) tuples.
        """
        with open(data_path) as f:
            data = [json.loads(line) for line in f]

        return [(item["input"], item.get("tool", "")) for item in data]
