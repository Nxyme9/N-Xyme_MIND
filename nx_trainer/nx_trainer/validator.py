"""Dataset validation for pre-flight checks before training.

Validates training data for:
- Required fields (input, output)
- Output format correctness ([TOOL_CALL] wrapper)
- Tool name validity
- Argument format correctness
- No placeholder leakage
- Sequence length estimates
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Valid tool names - must match MCP tool definitions
VALID_TOOLS = {
    # Memory tools
    "memory_search",
    "memory_write",
    "athena_smart_search",
    "learn_memory",
    "unified_memory_search",
    "unified_memory_write",
    "unified_memory_find_context",
    "unified_memory_recall_session",
    "unified_memory_memory_stats",
    "unified_memory_get_capabilities",
    "unified_memory_health_check",
    # File tools
    "read_file",
    "write_file",
    "list_directory",
    # Git tools
    "git_status",
    "git_log",
    "git_diff",
    "git_commit",
    "git_create_branch",
    "github_list_issues",
    "github_search_code",
    "github_create_issue",
    "github_create_pr",
    "github_search_issues",
    "github_search_users",
    "github_get_issue",
    "github_get_pull_request",
    # Web tools
    "fetch_url",
    "browser_navigate",
    "context7_query_docs",
    "websearch",
    "codesearch",
    "look_at",
    # Thinking tools
    "sequential_thinking",
    # Context tools
    "get_active_context",
    "get_health",
    "get_product_context",
    "get_user_context",
    "get_constraints",
    "get_user_profile",
    "get_style_context",
    "get_archive_context",
    "nx_context_get_active",
    "nx_context_get_product",
    "nx_context_get_user",
    # Pipeline/orchestration
    "pipeline_execute_task",
    "pipeline_get_health",
    "pipeline_get_stats",
    "pipeline_list_bmad_workflows",
    "pipeline_run_bmad_workflow",
    "orchestration_spawn",
    "orchestration_task_status",
    "orchestration_orchestrate",
    "orchestration_detect_state",
    "orchestration_list_workflows",
    "orchestration_health_check",
    # Learning/intelligence
    "learn_memory",
    "learn_route_task",
    "learn_status",
    "learn_retrain",
    "learn_get_recommendations",
    "learn_learning_stats",
    "learn_log_outcome",
    "learn_get_outcomes",
    "record_outcome",
    "log_outcome",
    "get_outcomes",
    "intelligence_route",
    "intelligence_score_complexity",
    "intelligence_available_agents",
    "intelligence_get_routing_history",
    # Session pool
    "session_pool_route_task",
    "session_pool_pool_stats",
    "session_pool_warm_pool",
    "session_pool_get_session",
    "session_pool_return_session",
    # Trigger guardian
    "trigger_register",
    "trigger_list",
    "trigger_check",
    "trigger_get_handlers",
    "trigger_log_event",
    "trigger_clear_triggers",
    "trigger_execute_trigger",
    # Notion
    "notion_search",
    "notion_get_page",
    "notion_create_page",
    "notion_get_pages",
    "notion_get_block_children",
    "notion_update_block",
    "notion_delete_block",
    "notion_update_page",
    "notion_move_page",
    "notion_query_database",
    # Skill/system
    "skill_mcp",
    "skill",
    # Routing
    "route_task",
    "score_complexity",
    "available_agents",
}

# Output pattern - use .+? to handle nested braces in values
TOOL_CALL_PATTERN = re.compile(
    r'\[TOOL_CALL\]\{tool\s*=>\s*"([^"]+)"(?:,\s*args\s*=>\s*\{(.+?)\})?\}\[/TOOL_CALL\]'
)

# Placeholder leakage patterns
PLACEHOLDER_PATTERNS = [
    re.compile(r"\{\{[^}]+\}\}"),  # {{placeholder}}
    re.compile(r"<[^>]+>"),  # <placeholder>
    re.compile(r"REPLACE_ME"),  # REPLACE_ME
    re.compile(r"TODO"),  # TODO
    re.compile(r"\$\{[^}]+\}"),  # ${placeholder}
]


class ValidationResult:
    """Single validation issue."""

    def __init__(self, level: str, message: str, line: Optional[int] = None):
        self.level = level  # error, warning, info
        self.message = message
        self.line = line

    def __repr__(self):
        loc = f" (line {self.line})" if self.line else ""
        return f"[{self.level.upper()}] {self.message}{loc}"


class DatasetValidator:
    """Validates training data before training starts."""

    def __init__(self, max_seq_length: int = 2048):
        self.max_seq_length = max_seq_length
        self.issues: List[ValidationResult] = []

    def validate_file(self, data_path: Path) -> Tuple[bool, List[ValidationResult]]:
        """Validate an entire JSONL file.

        Args:
            data_path: Path to JSONL training data

        Returns:
            (is_valid, issues)
        """
        self.issues = []

        # Check file exists
        if not data_path.exists():
            self.issues.append(ValidationResult("error", f"File not found: {data_path}"))
            return False, self.issues

        # Load and validate each line
        try:
            with open(data_path) as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                        self._validate_item(item, line_num)
                    except json.JSONDecodeError as e:
                        self.issues.append(
                            ValidationResult("error", f"Invalid JSON: {e}", line_num)
                        )
        except Exception as e:
            self.issues.append(ValidationResult("error", f"Read error: {e}"))
            return False, self.issues

        # Check for critical errors
        errors = [i for i in self.issues if i.level == "error"]
        is_valid = len(errors) == 0

        return is_valid, self.issues

    def _validate_item(self, item: Dict[str, Any], line_num: int) -> None:
        """Validate a single training example."""
        # Required fields
        if "input" not in item:
            self.issues.append(
                ValidationResult("error", "Missing required field: 'input'", line_num)
            )
        if "output" not in item:
            self.issues.append(
                ValidationResult("error", "Missing required field: 'output'", line_num)
            )

        if "input" not in item or "output" not in item:
            return  # Can't validate further without required fields

        input_text = item["input"]
        output_text = item["output"]

        # Check input is non-empty
        if not input_text or not input_text.strip():
            self.issues.append(ValidationResult("error", "Empty input", line_num))

        # Check output format
        if not self._validate_output_format(output_text, line_num):
            # Issue already added
            pass

        # Check for placeholder leakage
        self._check_placeholders(input_text, "input", line_num)
        self._check_placeholders(output_text, "output", line_num)

        # Estimate sequence length (rough heuristic: ~4 chars per token)
        estimated_tokens = len(input_text) + len(output_text)
        if estimated_tokens > self.max_seq_length * 3:
            self.issues.append(
                ValidationResult(
                    "warning",
                    f"Possible length issue: ~{estimated_tokens // 4} tokens (est.)",
                    line_num,
                )
            )

    def _validate_output_format(self, output: str, line_num: int) -> bool:
        """Validate output has correct [TOOL_CALL] format."""
        match = TOOL_CALL_PATTERN.search(output)

        if not match:
            self.issues.append(
                ValidationResult("error", "Output missing [TOOL_CALL] format wrapper", line_num)
            )
            return False

        tool_name = match.group(1)

        # Check tool name validity
        if tool_name not in VALID_TOOLS:
            self.issues.append(
                ValidationResult("warning", f"Unknown tool: '{tool_name}'", line_num)
            )
            # Don't fail on unknown tools - they might be valid MCP tools

        return True

    def _check_placeholders(self, text: str, field: str, line_num: int) -> None:
        """Check for placeholder leakage in text."""
        for pattern in PLACEHOLDER_PATTERNS:
            if pattern.search(text):
                self.issues.append(
                    ValidationResult(
                        "error",
                        f"Placeholder leakage in {field}: matches {pattern.pattern}",
                        line_num,
                    )
                )

    def validate(self, data: List[Dict[str, Any]]) -> Tuple[bool, List[ValidationResult]]:
        """Validate a list of training examples.

        Args:
            data: List of training examples

        Returns:
            (is_valid, issues)
        """
        self.issues = []

        for idx, item in enumerate(data, 1):
            self._validate_item(item, idx)

        errors = [i for i in self.issues if i.level == "error"]
        is_valid = len(errors) == 0

        return is_valid, self.issues


def validate_dataset(data_path, max_seq_length: int = 2048) -> bool:
    """Convenience function to validate a dataset file.

    Args:
        data_path: Path to training data JSONL (str or Path)
        max_seq_length: Max sequence length for length checks

    Returns:
        True if valid, False otherwise
    """
    # Convert to Path if string
    if isinstance(data_path, str):
        data_path = Path(data_path)

    validator = DatasetValidator(max_seq_length)
    is_valid, issues = validator.validate_file(data_path)

    # Print results
    print(f"\n=== Dataset Validation ===")
    print(f"File: {data_path}")

    if is_valid:
        print("✓ Validation PASSED")
        warnings = [i for i in issues if i.level == "warning"]
        if warnings:
            print(f"  Warnings: {len(warnings)}")
            for w in warnings[:5]:
                print(f"    - {w}")
    else:
        print("✗ Validation FAILED")
        errors = [i for i in issues if i.level == "error"]
        print(f"  Errors: {len(errors)}")
        for e in errors[:10]:
            print(f"    - {e}")

    return is_valid


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        data_path = Path(sys.argv[1])
        validate_dataset(data_path)
    else:
        print("Usage: python -m nx_trainer.validator <data.jsonl>")
