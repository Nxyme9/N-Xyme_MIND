#!/usr/bin/env python3
"""Generate training data mixing positive and negative examples for LoRA training.

This script combines:
- Positive examples (correct tool + appropriate arguments)
- Negative examples (wrong tool selection, no tool needed, etc.)

Based on ToolFormer/ToolLLM/NexusRaven research for tool discrimination.

Usage:
    python scripts/rosetta/generate_training_data.py [--ratio N] [--output FILE]
"""

import json
import random
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPT_DIR = Path(__file__).parent
NEGATIVE_EXAMPLES_FILE = SCRIPT_DIR / "negative_examples.json"


def load_negative_examples() -> List[Dict[str, Any]]:
    """Load negative examples from JSON file."""
    with open(NEGATIVE_EXAMPLES_FILE, "r") as f:
        data = json.load(f)
    return data["negative_examples"]


def load_positive_examples() -> List[Dict[str, Any]]:
    """Load existing positive training examples or generate them."""
    # Try to load existing positive examples
    positive_file = PROJECT_ROOT / "datasets" / "rosetta_full_training.jsonl"
    if positive_file.exists():
        positive = []
        with open(positive_file, "r") as f:
            for line in f:
                positive.append(json.loads(line))
        return positive

    # Otherwise return empty list - we'll generate basic ones
    return []


def generate_basic_positive_examples() -> List[Dict[str, Any]]:
    """Generate basic positive examples if none exist."""

    templates = [
        # Filesystem
        ("read README.md", "read_file", {"path": "README.md"}),
        ("show me config.json", "read_file", {"path": "config.json"}),
        (
            "write hello to test.txt",
            "write_file",
            {"path": "test.txt", "content": "hello"},
        ),
        ("list files in src", "glob", {"pattern": "src/**/*"}),
        ("find all Python files", "glob", {"pattern": "**/*.py"}),
        # Git
        ("check git status", "git_status", {"repo_path": "."}),
        ("show recent commits", "git_log", {"repo_path": ".", "max_count": 5}),
        ("show diff", "git_diff", {"repo_path": ".", "target": "HEAD"}),
        ("list branches", "git_branch", {"repo_path": "."}),
        # GitHub
        ("search GitHub for react", "github_search_repositories", {"query": "react"}),
        ("list issues", "github_list_issues", {"owner": "facebook", "repo": "react"}),
        ("search code for auth", "github_search_code", {"query": "auth"}),
        # Web
        (
            "fetch python docs",
            "webfetch",
            {"url": "https://python.org", "format": "markdown"},
        ),
        ("search web for best practices", "websearch", {"query": "best practices"}),
        # MCP Tools
        (
            "search memory for config",
            "unified-memory_search_memories",
            {"query": "config", "limit": 10},
        ),
        (
            "write to memory",
            "unified-memory_memory_write",
            {"content": "test", "kind": "episodic"},
        ),
        ("get memory stats", "unified-memory_get_memory_stats", {}),
        ("list sessions", "session_list", {"limit": 10}),
        ("search sessions", "session_search", {"query": "auth"}),
        ("get session info", "session_info", {"session_id": "test"}),
        (
            "think about this",
            "sequential-thinking_sequentialthinking",
            {
                "thought": "analyze problem",
                "nextThoughtNeeded": True,
                "thoughtNumber": 1,
                "totalThoughts": 3,
            },
        ),
        ("route this task", "intelligence_route", {"task_description": "fix bug"}),
        (
            "score complexity",
            "intelligence_score_complexity",
            {"task_description": "add feature"},
        ),
        ("run type check", "quality-gates_run_typecheck", {}),
        ("run lint", "quality-gates_run_lint", {}),
        ("run tests", "quality-gates_run_tests", {}),
        ("run all gates", "quality-gates_run_all_gates", {}),
        # Obsidian
        (
            "get Obsidian file",
            "obsidian_obsidian_get_file_contents",
            {"filepath": "test.md"},
        ),
        ("search notes", "obsidian_obsidian_simple_search", {"query": "test"}),
        (
            "append to note",
            "obsidian_obsidian_append_content",
            {"content": "test", "filepath": "test.md"},
        ),
        # Notion
        ("search Notion", "notion_API-post-search", {"query": "test"}),
        ("get Notion page", "notion_API-retrieve-a-page", {"page_id": "test"}),
        # Telegram
        ("send message", "telegram_send_message", {"text": "hello"}),
    ]

    positive = []
    for template, tool, args in templates:
        args_str = ", ".join(f'--{k} "{v}"' for k, v in args.items())
        output = (
            f'[TOOL_CALL]{{tool => "{tool}", args => {{ {args_str} }}}}[/TOOL_CALL]'
        )

        positive.append(
            {
                "input": template,
                "output": output,
                "tool": tool,
                "args": args,
                "type": "positive",
            }
        )

    return positive


def format_tool_call(tool: str, args: Dict) -> str:
    """Format tool call in Rosetta output format."""
    if not args:
        args_str = ""
    else:
        args_str = ", ".join(f'--{k} "{v}"' for k, v in args.items())
    return f'[TOOL_CALL]{{tool => "{tool}", args => {{ {args_str} }}}}[/TOOL_CALL]'


def convert_negative_to_training(example: Dict[str, Any]) -> Dict[str, Any]:
    """Convert negative example to training format."""

    user_request = example["user_request"]
    correct_tool = example.get("correct_tool")
    distractor_tools = example.get("distractor_tools", [])
    reason = example.get("reason", "")

    # For negative examples where no tool is needed
    if correct_tool is None:
        output = "[NO_TOOL_NEEDED]"
    else:
        # The key insight: include CORRECT tool in output for learning
        # but the distractor tools should be presented as options
        # For training, we mark the correct one and list distractors
        output = f'[TOOL_CALL]{{tool => "{correct_tool}", args => {{ }}}}[/TOOL_CALL]'

    return {
        "input": user_request,
        "output": output,
        "correct_tool": correct_tool,
        "distractor_tools": distractor_tools,
        "reason": reason,
        "type": "negative",
        "should_call_tool": correct_tool is not None,
    }


def create_training_pair(
    input_text: str, tool: Optional[str], args: Dict = None, is_positive: bool = True
) -> Dict[str, Any]:
    """Create a training pair in Rosetta format."""

    if is_positive:
        output = format_tool_call(tool, args or {})
        return {
            "input": input_text,
            "output": output,
            "tool": tool,
            "args": args or {},
            "type": "positive",
        }
    else:
        # Negative - no tool needed
        return {
            "input": input_text,
            "output": "[NO_TOOL_NEEDED]",
            "tool": None,
            "args": {},
            "type": "negative",
            "should_call_tool": False,
        }


def generate_mixed_dataset(
    positive_ratio: float = 0.7, total: int = 1000
) -> List[Dict[str, Any]]:
    """Generate mixed positive and negative training data.

    Args:
        positive_ratio: Ratio of positive examples (0.0 to 1.0)
        total: Total number of examples to generate

    Returns:
        List of training pairs
    """

    # Load or generate positive examples
    positives = load_positive_examples()
    if not positives:
        positives = generate_basic_positive_examples()

    # Load negative examples
    negatives_raw = load_negative_examples()
    negatives = [convert_negative_to_training(n) for n in negatives_raw]

    # Calculate counts
    num_positive = int(total * positive_ratio)
    num_negative = total - num_positive

    # Sample and expand
    dataset = []

    # Add positive examples (expand by varying parameters)
    positive_expanded = []
    for _ in range(num_positive):
        base = random.choice(positives)
        positive_expanded.append(base)

    # Add negative examples (sample and repeat)
    negative_expanded = []
    for _ in range(num_negative):
        base = random.choice(negatives)
        negative_expanded.append(base)

    dataset = positive_expanded + negative_expanded
    random.shuffle(dataset)

    return dataset


def save_dataset(dataset: List[Dict], output_file: Path):
    """Save dataset to JSONL format."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        for item in dataset:
            f.write(json.dumps(item) + "\n")

    return len(dataset)


def save_json_format(dataset: List[Dict], output_file: Path):
    """Save dataset in JSON format (for inspection)."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(dataset, f, indent=2)

    return len(dataset)


def main():
    parser = argparse.ArgumentParser(description="Generate training data for LoRA")
    parser.add_argument(
        "--ratio",
        type=float,
        default=0.7,
        help="Ratio of positive examples (default: 0.7)",
    )
    parser.add_argument(
        "--total",
        type=int,
        default=1000,
        help="Total examples to generate (default: 1000)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="datasets/rosetta_training_mixed.jsonl",
        help="Output file path",
    )
    parser.add_argument(
        "--json-output",
        type=str,
        default=None,
        help="Also save JSON format to this path",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility"
    )

    args = parser.parse_args()

    random.seed(args.seed)

    print(
        f"Generating {args.total} training examples ({args.ratio * 100:.0f}% positive)..."
    )

    dataset = generate_mixed_dataset(positive_ratio=args.ratio, total=args.total)

    # Count types
    positive_count = sum(1 for d in dataset if d.get("type") == "positive")
    negative_count = sum(1 for d in dataset if d.get("type") == "negative")

    print(f"  Positive: {positive_count}")
    print(f"  Negative: {negative_count}")

    # Save as JSONL
    output_path = PROJECT_ROOT / args.output
    saved = save_dataset(dataset, output_path)
    print(f"\nSaved {saved} examples to: {output_path}")

    # Save as JSON if requested
    if args.json_output:
        json_path = PROJECT_ROOT / args.json_output
        saved_json = save_json_format(dataset, json_path)
        print(f"Saved JSON format to: {json_path}")

    # Show samples
    print("\n=== Sample Positive Examples ===")
    for item in dataset[:2]:
        if item.get("type") == "positive":
            print(f"  Input:  {item['input']}")
            print(f"  Output: {item['output']}")
            print()

    print("=== Sample Negative Examples ===")
    for item in dataset[:2]:
        if item.get("type") == "negative":
            print(f"  Input:  {item['input']}")
            print(f"  Output: {item['output']}")
            print(f"  Reason: {item.get('reason', 'N/A')}")
            print()


if __name__ == "__main__":
    main()
