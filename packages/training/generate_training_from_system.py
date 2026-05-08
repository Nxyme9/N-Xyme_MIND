#!/usr/bin/env python3
"""Generate training data from N-Xyme_MIND system activity.

Extracts real task examples from:
- Memory graph (entities, relations)
- Session context
- Delegation logs
- Routing history

Usage:
    python generate_training_from_system.py --output datasets/system_training.jsonl
"""

import json
import argparse
from pathlib import Path
import random
import sqlite3
from typing import List, Dict

PROJECT_ROOT = Path(__file__).parent.parent


def extract_from_memory_graph() -> List[Dict]:
    """Extract training examples from memory graph."""
    examples = []
    entities_path = PROJECT_ROOT / ".context/memory_graph/entities.json"

    if entities_path.exists():
        with open(entities_path) as f:
            data = json.load(f)
            for entity in data.get("entities", [])[:50]:  # Limit to 50
                entity_type = entity.get("type", "")
                name = entity.get("name", "")

                if entity_type in ["task", "agent", "tool"]:
                    # Generate natural task examples
                    examples.append(
                        {
                            "input": f"{name}",
                            "output": f'[TOOL_CALL]{{tool => \'{entity_type}_search\', args => {{ --query "{name}", --limit "5" }}}}[/TOOL_CALL]',
                            "tool_name": f"{entity_type}_search",
                            "category": "memory",
                        }
                    )

    return examples


def extract_from_delegation_logs() -> List[Dict]:
    """Extract training examples from delegation logs."""
    examples = []
    log_dir = PROJECT_ROOT / ".sisyphus/delegation-logs"

    if log_dir.exists():
        for log_file in log_dir.glob("*.json"):
            try:
                with open(log_file) as f:
                    data = json.load(f)
                    for entry in data.get("entries", [])[:10]:
                        task = entry.get("task", "")
                        agent = entry.get("agent", "")

                        if task and agent:
                            examples.append(
                                {
                                    "input": f"Route this task: {task}",
                                    "output": f"[TOOL_CALL]{{tool => 'route_task', args => {{ --task_description \"{task}\" }}}}[/TOOL_CALL]",
                                    "tool_name": "route_task",
                                    "category": "learning",
                                }
                            )
            except Exception:
                pass

    return examples


def extract_from_routing_history() -> List[Dict]:
    """Extract training examples from routing history."""
    examples = []

    # Try to get from context.db
    db_path = PROJECT_ROOT / ".sisyphus/context.db"
    if db_path.exists():
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.execute(
                "SELECT task, preferred_agent FROM session_summary LIMIT 20"
            )
            for row in cursor:
                task, agent = row
                if task and agent:
                    examples.append(
                        {
                            "input": f"{task}",
                            "output": f'[TOOL_CALL]{{tool => \'route_task\', args => {{ --task_description "{task}", --preferred_agent "{agent}" }}}}[/TOOL_CALL]',
                            "tool_name": "route_task",
                            "category": "learning",
                        }
                    )
            conn.close()
        except sqlite3.Error:
            pass

    return examples


def generate_from_tools() -> List[Dict]:
    """Generate training examples from available tools."""
    tools = {
        "memory": [
            (
                "search memory for security",
                "memory_search",
                {"query": "security", "limit": 10},
            ),
            (
                "find context about python",
                "memory_find_context",
                {"task": "python", "context_type": "all"},
            ),
            ("get memory stats", "memory_get_memory_stats", {}),
            (
                "rank memories for coding",
                "memory_rank_memories",
                {"query": "coding", "limit": 5},
            ),
        ],
        "filesystem": [
            ("read file src/main.py", "read_file", {"path": "src/main.py"}),
            (
                "write content to output.txt",
                "write_file",
                {"path": "output.txt", "content": "data"},
            ),
            ("list directory src/", "list_directory", {"path": "src/"}),
            ("find python files", "glob", {"pattern": "**/*.py"}),
            (
                "search for function in code",
                "grep",
                {"pattern": "function", "path": "src/"},
            ),
        ],
        "git": [
            ("check git status", "git_status", {}),
            ("show recent commits", "git_log", {"limit": 10}),
            ("show changes in files", "git_diff", {}),
            ("show current branch", "git_branch", {}),
        ],
        "github": [
            (
                "list issues for facebook/react",
                "github_list_issues",
                {"repo": "facebook/react"},
            ),
            (
                "search code in repo",
                "github_search_code",
                {"query": "useState", "repo": "facebook/react"},
            ),
            (
                "get file from repo",
                "github_get_file_contents",
                {"owner": "facebook", "repo": "react", "path": "README.md"},
            ),
            (
                "create issue",
                "github_create_issue",
                {
                    "owner": "user",
                    "repo": "repo",
                    "title": "Bug found",
                    "body": "description",
                },
            ),
        ],
        "context": [
            ("get active context", "get_active_context", {}),
            ("get user context", "get_user_context", {}),
            ("get product context", "get_product_context", {}),
            ("get constraints", "get_constraints", {}),
        ],
        "mind": [
            ("get mind state", "get_mind_state", {}),
            ("get session history", "get_session_history", {"limit": 10}),
            ("get project manifest", "get_project_manifest", {}),
        ],
        "reasoning": [
            (
                "think about optimization problem",
                "sequential_thinking",
                {"problem": "optimization"},
            ),
        ],
        "quality": [
            ("run typecheck", "run_typecheck", {}),
            ("run linting", "run_lint", {}),
            ("run tests", "run_tests", {}),
            ("scan for secrets", "run_secrets_scan", {}),
        ],
        "triggers": [
            (
                "register trigger /test",
                "trigger_register",
                {"phrase": "/test", "description": "test trigger"},
            ),
            ("list triggers", "trigger_list", {}),
            ("check trigger input", "trigger_check", {"input_text": "/test"}),
            ("execute trigger", "trigger_execute", {"phrase": "/test"}),
        ],
        "orchestration": [
            ("orchestrate workflow", "orchestrate", {"user_input": "build feature"}),
            ("detect state", "detect_state", {"user_input": "help needed"}),
            ("list workflows", "list_workflows", {}),
        ],
        "sqlite": [
            ("query database", "sqlite_query", {"sql": "SELECT * FROM table"}),
            ("list tables", "sqlite_list_tables", {}),
        ],
        "notion": [
            ("search notion", "notion_search", {"query": "task"}),
            ("get page", "notion_get_page", {"page_id": "id"}),
            ("create page", "notion_create_page", {"title": "New", "content": "text"}),
        ],
    }

    examples = []
    for category, tool_list in tools.items():
        for prompt, tool_name, args in tool_list:
            args_str = ", ".join([f'--{k} "{v}"' for k, v in args.items() if v])
            examples.append(
                {
                    "input": prompt,
                    "output": f"[TOOL_CALL]{{tool => '{tool_name}', args => {{ {args_str} }}}}[/TOOL_CALL]",
                    "tool_name": tool_name,
                    "category": category,
                }
            )

    return examples


def main():
    parser = argparse.ArgumentParser(
        description="Generate training data from system activity"
    )
    parser.add_argument(
        "--output", default="datasets/system_training.jsonl", help="Output file"
    )
    parser.add_argument(
        "--max-examples", type=int, default=200, help="Max examples to generate"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("N-XYME_MIND TRAINING DATA GENERATOR")
    print("=" * 60)

    all_examples = []

    # 1. Extract from memory graph
    print("\n[1/5] Extracting from memory graph...")
    memory_examples = extract_from_memory_graph()
    print(f"  Found {len(memory_examples)} examples")
    all_examples.extend(memory_examples)

    # 2. Extract from delegation logs
    print("\n[2/5] Extracting from delegation logs...")
    delegation_examples = extract_from_delegation_logs()
    print(f"  Found {len(delegation_examples)} examples")
    all_examples.extend(delegation_examples)

    # 3. Extract from routing history
    print("\n[3/5] Extracting from routing history...")
    routing_examples = extract_from_routing_history()
    print(f"  Found {len(routing_examples)} examples")
    all_examples.extend(routing_examples)

    # 4. Generate from tool definitions
    print("\n[4/5] Generating from tool templates...")
    tool_examples = generate_from_tools()
    print(f"  Generated {len(tool_examples)} examples")
    all_examples.extend(tool_examples)

    # 5. Add variations for augmentation
    print("\n[5/5] Augmenting with variations...")

    # Add variations by rephrasing prompts
    variations = []
    for ex in all_examples[:50]:  # Take subset
        original = ex["input"]
        # Create variations
        if "search" in original.lower():
            variations.append(
                {
                    "input": original.replace("search", "find"),
                    "output": ex["output"],
                    "tool_name": ex["tool_name"],
                    "category": ex["category"],
                }
            )
        if "get" in original.lower():
            variations.append(
                {
                    "input": original.replace("get", "retrieve"),
                    "output": ex["output"],
                    "tool_name": ex["tool_name"],
                    "category": ex["category"],
                }
            )

    print(f"  Added {len(variations)} variations")
    all_examples.extend(variations)

    # Deduplicate
    seen = set()
    unique_examples = []
    for ex in all_examples:
        key = (ex["input"], ex["tool_name"])
        if key not in seen:
            seen.add(key)
            unique_examples.append(ex)

    # Limit to max examples
    if len(unique_examples) > args.max_examples:
        unique_examples = random.sample(unique_examples, args.max_examples)

    # Save to file
    output_path = PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        for ex in unique_examples:
            f.write(json.dumps(ex) + "\n")

    print(f"\n✓ Saved {len(unique_examples)} training examples to {output_path}")

    # Show category distribution
    categories = {}
    for ex in unique_examples:
        cat = ex.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    print("\nCategory distribution:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
