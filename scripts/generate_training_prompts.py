#!/usr/bin/env python3
"""Training Prompt Generator - Generate diverse prompts from tool schemas.

This script reads tool definitions from mcp_tool_loader.py and generates
varied user prompts for each tool to use in cloud model training data generation.

Usage:
    python scripts/generate_training_prompts.py [--prompts-per-tool N]
"""

import json
import os
import sys
import argparse
import random
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import tool loader
from packages.local_llm.mcp_tool_loader import MCPToolLoader

# Template variations for generating diverse prompts
TEMPLATE_VARIATIONS = {
    "read_file": [
        "Show me the contents of {path}",
        "Read {path}",
        "What's in {path}?",
        "Display the file at {path}",
        "Open and read {path}",
        "I want to see what's in {path}",
        "Can you read {path} for me?",
        "Show the content of {path}",
    ],
    "write_file": [
        "Write this to {path}: {content}",
        "Create a file at {path} with content: {content}",
        "Save the following to {path}: {content}",
        "Write content to {path}",
        "Create {path} containing: {content}",
    ],
    "list_directory": [
        "List files in {path}",
        "What's in the {path} directory?",
        "Show me the contents of {path}",
        "What files are in {path}?",
        "List the directory {path}",
        "Explore {path} and show me what's there",
    ],
    "git_status": [
        "What's the git status?",
        "Show me the current git status",
        "Check git status",
        "What are the current changes?",
        "Are there any uncommitted changes?",
        "Show modified files",
    ],
    "git_log": [
        "Show me the commit history",
        "What are the recent commits?",
        "Show last {count} commits",
        "What's the git log?",
        "List recent commits",
    ],
    "git_diff": [
        "Show me the differences between {target}",
        "What's the diff for {target}?",
        "Compare {target}",
        "Show changes in {target}",
    ],
    "memory_search": [
        "Search memory for {query}",
        "Find information about {query} in memory",
        "Look up {query} in the knowledge base",
        "What do I know about {query}?",
        "Search for {query}",
        "Find any stored info about {query}",
    ],
    "memory_write": [
        "Remember this: {content}",
        "Save to memory: {content}",
        "Store this information: {content}",
        "Write to memory: {content}",
        "Remember that {content}",
    ],
    "github_search_repositories": [
        "Find GitHub repositories about {query}",
        "Search for {query} repositories on GitHub",
        "Find popular {query} projects on GitHub",
        "Search GitHub for {query}",
        "Show me {query} repositories",
    ],
    "github_list_issues": [
        "List open issues in {owner}/{repo}",
        "Show issues for {owner}/{repo}",
        "What issues does {owner}/{repo} have?",
        "List {repo} issues",
    ],
    "fetch_url": [
        "Fetch content from {url}",
        "Get the page at {url}",
        "Retrieve {url}",
        "What's at {url}?",
        "Fetch {url}",
    ],
    "context7_query_docs": [
        "Query {library_id} docs about {query}",
        "Look up {library_id} documentation for {query}",
        "Search {library_id} for {query}",
        "Find {query} in {library_id} docs",
    ],
    "sequential_thinking": [
        "Think through this: {thought}",
        "Let me think about {thought}",
        "I need to reason about {thought}",
        "Analyze: {thought}",
        "Think step by step about {thought}",
    ],
    "get_active_context": [
        "What's the current project context?",
        "Get the active context",
        "What are we working on?",
        "Show current context",
        "What's the current state?",
    ],
    "get_user_context": [
        "What's my user context?",
        "Get user preferences",
        "What are my preferences?",
        "Show user context",
    ],
    "route_task": [
        "Which model should handle: {task}?",
        "Recommend an agent for: {task}",
        "Route this task: {task}",
        "What agent should handle {task}?",
    ],
    "record_outcome": [
        "Record that {task} succeeded",
        "Log: {agent} completed {task}",
        "Record outcome: {task} by {agent}",
        "Note: {task} finished",
    ],
    "sqlite_query": [
        "Query the database: {query}",
        "Run SQL: {query}",
        "Execute: {query}",
    ],
    "get_outcomes": [
        "Show delegation outcomes",
        "What tasks have been delegated?",
        "List recent outcomes",
    ],
}

# Default paths for path-type parameters
DEFAULT_PATHS = [
    "src/main.py",
    "config/settings.json",
    "README.md",
    "package.json",
    "opencode.json",
    "AGENTS.md",
    "packages/local_llm/wrapper.py",
    "tests/test_main.py",
    "docs/README.md",
    ".env.example",
]

# Default content for write operations
DEFAULT_CONTENTS = [
    "Hello World",
    "# Configuration\n\nThis is a config file.",
    "console.log('test');",
    "import os\n\nprint('hello')",
    "# TODO: Implement feature",
]

# Default queries for search tools
DEFAULT_QUERIES = [
    "authentication",
    "database connection",
    "API endpoints",
    "user management",
    "error handling",
    "testing",
    "deployment",
    "security",
]

# Default targets for git diff
DEFAULT_TARGETS = [
    "main..develop",
    "HEAD~1",
    "main",
    "develop",
    "HEAD",
]


def generate_prompts_for_tool(tool_name: str, tool_spec: Dict, count: int = 50) -> List[str]:
    """Generate diverse prompts for a specific tool.
    
    Args:
        tool_name: Name of the tool
        tool_spec: Tool specification with parameters
        count: Number of prompts to generate
        
    Returns:
        List of generated prompts
    """
    prompts = []
    params = tool_spec.get("parameters", {}).get("properties", {})
    required = tool_spec.get("parameters", {}).get("required", [])
    
    # Get templates for this tool
    templates = TEMPLATE_VARIATIONS.get(tool_name, [
        f"Use the {tool_name} tool",
        f"Call {tool_name}",
        f"Execute {tool_name}",
    ])
    
    # Generate prompts by filling in templates
    for _ in range(count):
        template = random.choice(templates)
        
        # Replace placeholders with realistic values
        filled = template
        
        # Replace {path} with realistic paths
        if "{path}" in filled:
            filled = filled.replace("{path}", random.choice(DEFAULT_PATHS))
        
        # Replace {content} with content
        if "{content}" in filled:
            filled = filled.replace("{content}", random.choice(DEFAULT_CONTENTS))
        
        # Replace {query} with queries
        if "{query}" in filled:
            filled = filled.replace("{query}", random.choice(DEFAULT_QUERIES))
        
        # Replace {target} with targets
        if "{target}" in filled:
            filled = filled.replace("{target}", random.choice(DEFAULT_TARGETS))
        
        # Replace {owner}/{repo} with examples
        if "{owner}/{repo}" in filled:
            repos = ["facebook/react", "microsoft/vscode", "vercel/next.js", "tailwindlabs/tailwindcss"]
            filled = filled.replace("{owner}/{repo}", random.choice(repos))
        
        # Replace {library_id} with library IDs
        if "{library_id}" in filled:
            libs = ["/mongodb/mongodb", "/vercel/next.js", "/supabase/supabase", "/facebook/react"]
            filled = filled.replace("{library_id}", random.choice(libs))
        
        # Replace {count} with numbers
        if "{count}" in filled:
            counts = ["5", "10", "20", "50"]
            filled = filled.replace("{count}", random.choice(counts))
        
        # Replace {thought} with thoughts
        if "{thought}" in filled:
            thoughts = [
                "how to optimize a database query",
                "the best architecture for this feature",
                "why the test is failing",
                "how to implement authentication",
                "the root cause of this bug",
            ]
            filled = filled.replace("{thought}", random.choice(thoughts))
        
        # Replace {task} with tasks
        if "{task}" in filled:
            tasks = [
                "generate Python code",
                "fix a bug in the auth module",
                "refactor the database layer",
                "write tests for the API",
                "implement caching",
            ]
            filled = filled.replace("{task}", random.choice(tasks))
        
        # Replace {agent} with agents
        if "{agent}" in filled:
            agents = ["hephaestus", "sisyphus", "oracle", "explore"]
            filled = filled.replace("{agent}", random.choice(agents))
        
        # Replace {url} with URLs
        if "{url}" in filled:
            urls = ["https://docs.python.org", "https://github.com", "https://stackoverflow.com"]
            filled = filled.replace("{url}", random.choice(urls))
        
        prompts.append(filled)
    
    return prompts


def main():
    parser = argparse.ArgumentParser(description="Generate training prompts from tool schemas")
    parser.add_argument("--prompts-per-tool", type=int, default=50, help="Prompts per tool")
    parser.add_argument("--output", type=str, default="datasets/training_prompts.json", help="Output file")
    parser.add_argument("--tools", type=str, nargs="+", help="Specific tools to generate for")
    args = parser.parse_args()
    
    print("Loading tool schemas...")
    loader = MCPToolLoader()
    tools = loader.get_tools_openai_format()
    
    print(f"Found {len(tools)} tools")
    
    all_prompts = {}
    
    for tool in tools:
        func = tool.get("function", {})
        tool_name = func.get("name", "unknown")
        
        # Skip if specific tools requested and this isn't one
        if args.tools and tool_name not in args.tools:
            continue
        
        print(f"Generating {args.prompts_per_tool} prompts for {tool_name}...")
        
        tool_spec = {
            "description": func.get("description", ""),
            "parameters": func.get("parameters", {}),
        }
        
        prompts = generate_prompts_for_tool(
            tool_name, 
            tool_spec, 
            args.prompts_per_tool
        )
        
        all_prompts[tool_name] = {
            "description": func.get("description", ""),
            "parameters": func.get("parameters", {}),
            "prompts": prompts,
            "count": len(prompts)
        }
    
    # Save to file
    output_path = PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(all_prompts, f, indent=2)
    
    total = sum(len(v["prompts"]) for v in all_prompts.values())
    print(f"\nGenerated {total} prompts for {len(all_prompts)} tools")
    print(f"Saved to: {output_path}")
    
    # Also print summary
    print("\n--- Summary ---")
    for tool_name, data in all_prompts.items():
        print(f"  {tool_name}: {data['count']} prompts")


if __name__ == "__main__":
    main()