#!/usr/bin/env python3
"""Generate comprehensive training data for Rosetta Stone from MCP tool schemas.

This script generates diverse training pairs covering ALL available MCP tools
for fine-tuning the Rosetta Stone model.

Usage:
    python scripts/generate_full_training_data.py
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).parent.parent


def generate_tool_templates() -> List[Dict[str, Any]]:
    """Generate all tool templates with variations."""
    
    templates = [
        # Memory & Knowledge
        ("search memory for {query}", "memory_search", {"query": "{query}", "limit": 10}),
        ("look up {query} in memory", "memory_search", {"query": "{query}"}),
        ("find info about {query}", "athena_smart_search", {"query": "{query}"}),
        ("search athena for {query}", "athena_smart_search", {"query": "{query}"}),
        ("remember that {content}", "memory_write", {"content": "{content}", "kind": "episodic"}),
        
        # Filesystem
        ("read {path}", "read_file", {"path": "{path}"}),
        ("show me {path}", "read_file", {"path": "{path}"}),
        ("cat {path}", "read_file", {"path": "{path}"}),
        ("write {content} to {path}", "write_file", {"path": "{path}", "content": "{content}"}),
        ("create {path} with {content}", "write_file", {"path": "{path}", "content": "{content}"}),
        ("list files in {path}", "list_directory", {"path": "{path}"}),
        ("ls {path}", "list_directory", {"path": "{path}"}),
        ("find files matching {pattern}", "glob", {"pattern": "{pattern}"}),
        ("search for {pattern} in {path}", "search_files", {"pattern": "{pattern}", "path": "{path}"}),
        
        # Git
        ("check git status", "git_status", {"repo_path": "."}),
        ("git status", "git_status", {"repo_path": "."}),
        ("show git log", "git_log", {"repo_path": ".", "max_count": 10}),
        ("recent commits", "git_log", {"repo_path": ".", "max_count": 5}),
        ("show diff", "git_diff", {"repo_path": ".", "target": "HEAD"}),
        ("what changed", "git_diff", {"repo_path": ".", "target": "HEAD"}),
        ("list branches", "git_branch", {"repo_path": "."}),
        
        # GitHub
        ("search for {repo} on github", "github_search_repositories", {"query": "{repo}"}),
        ("list issues for {owner}/{repo}", "github_list_issues", {"owner": "{owner}", "repo": "{repo}"}),
        ("find code for {query}", "github_search_code", {"query": "{query}"}),
        
        # Web & Docs
        ("fetch {url}", "fetch_url", {"url": "{url}", "format": "markdown"}),
        ("get content from {url}", "fetch_url", {"url": "{url}", "format": "text"}),
        ("get {lib} docs", "context7_query_docs", {"library_id": "/{lib}", "query": "getting started"}),
        ("how to use {lib}", "context7_query_docs", {"library_id": "/{lib}", "query": "how to"}),
        
        # Reasoning
        ("think about {problem}", "sequential_thinking", {"thought": "{problem}", "nextThoughtNeeded": True, "thoughtNumber": 1, "totalThoughts": 3}),
        ("analyze {problem}", "sequential_thinking", {"thought": "analyze: {problem}", "nextThoughtNeeded": True, "thoughtNumber": 1, "totalThoughts": 3}),
        
        # Context
        ("what's the active context", "get_active_context", {}),
        ("get user preferences", "get_user_context", {}),
        
        # Learning
        ("route this task: {task}", "route_task", {"task_description": "{task}"}),
        ("which agent for {task}", "route_task", {"task_description": "{task}"}),
        
        # Health & Quality
        ("check system health", "get_health", {"level": "l0"}),
        ("run health check", "get_health", {"level": "l1"}),
        ("type check", "run_typecheck", {}),
        ("run linter", "run_lint", {}),
        
        # Browser
        ("open {url} in browser", "browser_navigate", {"url": "{url}"}),
        ("go to {url}", "browser_navigate", {"url": "{url}"}),
        ("click {selector}", "browser_click", {"selector": "{selector}"}),
        ("type {text} into {selector}", "browser_type", {"selector": "{selector}", "text": "{text}"}),
    ]
    
    return templates


def generate_variations() -> List[Dict[str, Any]]:
    """Generate variation values for templates."""
    
    return {
        "query": ["security", "authentication", "deployment", "testing", "api", "config", "error handling", "performance", "database", "caching"],
        "path": ["README.md", "src/main.py", "config.json", "package.json", ".env", "src/utils/helper.py", "docs/guide.md", "tests/test_auth.py"],
        "pattern": ["*.py", "*.js", "**/*.ts", "*.json", "**/test_*.py"],
        "content": ["hello world", "test content", "console.log('test')", "# configuration", "const data = {};"],
        "repo": ["facebook/react", "microsoft/vscode", "vercel/next.js", "nodejs/node"],
        "owner": ["facebook", "microsoft", "vercel", "google"],
        "url": ["https://docs.python.org", "https://nodejs.org", "https://react.dev", "https://typescript.dev"],
        "lib": ["react", "python", "typescript", "express", "nextjs", "mongodb"],
        "problem": ["debug this error", "optimize performance", "design api", "fix memory leak", "improve security"],
        "task": ["implement auth", "write tests", "refactor code", "add feature", "fix bug"],
    }


def create_training_pair(template: str, tool: str, args: Dict, variation: Dict) -> Dict:
    """Create a single training pair."""
    
    # Build input
    input_text = template
    args_copy = {}
    
    for key, value in args.items():
        if isinstance(value, str) and "{" in value:
            placeholder = value.replace("{", "").replace("}", "")
            if placeholder in variation:
                input_text = input_text.replace(f"{{{placeholder}}}", variation[placeholder])
                args_copy[key] = variation[placeholder]
            else:
                args_copy[key] = value
        else:
            args_copy[key] = value
    
    # Handle any remaining placeholders in input
    for key, values in variation.items():
        if f"{{{key}}}" in input_text:
            input_text = input_text.replace(f"{{{key}}}", values[0] if isinstance(values, list) else values)
    
    # Format output
    args_str = ", ".join(f'--{k} "{v}"' for k, v in args_copy.items())
    output_text = f"[TOOL_CALL]{{tool => \"{tool}\", args => {{ {args_str} }}}}[/TOOL_CALL]"
    
    return {
        "input": input_text,
        "output": output_text,
        "tool": tool,
        "args": args_copy,
    }


def generate_dataset(num_pairs: int = 500) -> List[Dict]:
    """Generate the full training dataset."""
    
    templates = generate_tool_templates()
    variations = generate_variations()
    
    pairs = []
    used_combinations = set()
    
    while len(pairs) < num_pairs:
        template, tool, args = random.choice(templates)
        
        # Create variation for this template
        variation = {}
        for key, values in variations.items():
            variation[key] = random.choice(values)
        
        pair = create_training_pair(template, tool, args, variation)
        
        # Avoid duplicates
        key = (pair["input"], pair["tool"])
        if key not in used_combinations:
            used_combinations.add(key)
            pairs.append(pair)
    
    return pairs


def main():
    print("Generating comprehensive Rosetta Stone training data...")
    
    pairs = generate_dataset(500)
    
    output_file = PROJECT_ROOT / "datasets" / "rosetta_full_training.jsonl"
    with open(output_file, "w") as f:
        for pair in pairs:
            f.write(json.dumps(pair) + "\n")
    
    print(f"Generated {len(pairs)} training pairs")
    print(f"Saved to: {output_file}")
    
    # Show sample
    print("\nSample pairs:")
    for i, pair in enumerate(pairs[:3]):
        print(f"  {i+1}. Input: {pair['input']}")
        print(f"     Output: {pair['output']}")
        print()


if __name__ == "__main__":
    main()