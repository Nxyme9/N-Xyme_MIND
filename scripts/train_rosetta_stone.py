#!/usr/bin/env python3
"""Rosetta Stone Training Pipeline - Train local model to translate user requests to MCP tool calls.

This trains YOUR local model (Qwen2.5-0.5B) to be a "Rosetta Stone" - translating natural language
user requests into proper MCP tool calls for YOUR specific ecosystem.

TRAINING APPROACH:
1. Generate training pairs: simple request → proper tool call
2. Fine-tune local model on these pairs
3. Use as translation layer between user requests and MCP tools

Usage:
    python scripts/train_rosetta_stone.py --generate-data     # Generate training data
    python scripts/train_rosetta_stone.py --train            # Run training
    python scripts/train_rosetta_stone.py --test             # Test the model
"""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any
import subprocess

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def generate_training_dataset():
    """Generate training dataset: simple request → MCP tool call."""
    from packages.local_llm.mcp_tool_loader import MCPToolLoader
    
    loader = MCPToolLoader()
    tools = loader.get_tools_openai_format()
    
    training_pairs = []
    
    # Template: Simple user phrase → Tool call format
    templates = [
        # Memory tools
        ("search memory for {query}", "memory_search", {"query": "{query}", "limit": 10}),
        ("look up {query} in memory", "memory_search", {"query": "{query}"}),
        ("find info about {query}", "athena_smart_search", {"query": "{query}"}),
        ("search athena for {query}", "athena_smart_search", {"query": "{query}"}),
        
        # File tools
        ("read file {path}", "read_file", {"path": "{path}"}),
        ("show me {path}", "read_file", {"path": "{path}"}),
        ("create file at {path}", "write_file", {"path": "{path}", "content": ""}),
        ("list directory {path}", "list_directory", {"path": "{path}"}),
        
        # Git tools
        ("check git status", "git_status", {"repo_path": "."}),
        ("show git log", "git_log", {"repo_path": ".", "max_count": 10}),
        ("show diff", "git_diff", {"repo_path": ".", "target": "HEAD"}),
        
        # GitHub tools
        ("list issues for {repo}", "github_list_issues", {"owner": "", "repo": "{repo}"}),
        
        # Web tools
        ("fetch {url}", "fetch_url", {"url": "{url}", "format": "markdown"}),
        ("get docs for {lib}", "context7_query_docs", {"library_id": "/{lib}", "query": "basics"}),
        
        # Thinking
        ("think about {problem}", "sequential_thinking", {"thought": "{problem}", "nextThoughtNeeded": True, "thoughtNumber": 1, "totalThoughts": 3}),
        
        # Context
        ("what's the active context", "get_active_context", {}),
        ("get user context", "get_user_context", {}),
        
        # Learning/Routing
        ("route task: {task}", "route_task", {"task_description": "{task}"}),
    ]
    
    # Generate variations
    queries = ["security", "authentication", "deployment", "testing", "API", "config", "error handling"]
    paths = ["src/main.py", "README.md", "config.json", "package.json", ".env"]
    repos = ["facebook/react", "microsoft/vscode"]
    urls = ["https://docs.python.org", "https://nodejs.org"]
    libs = ["react", "python", "typescript", "express"]
    problems = ["debug this error", "optimize performance", "design API"]
    tasks = ["implement auth", "write tests", "refactor code"]
    
    for template, tool_name, args in templates:
        for _ in range(10):  # Generate 10 variations per template
            # Create input (simple user request)
            input_text = template
            
            # Replace placeholders - convert args values to strings first
            args_copy = {}
            for k, v in args.items():
                if isinstance(v, str):
                    if "{query}" in v:
                        v = v.replace("{query}", queries[_ % len(queries)])
                    elif "{path}" in v:
                        v = v.replace("{path}", paths[_ % len(paths)])
                    elif "{repo}" in v:
                        v = v.replace("{repo}", repos[_ % len(repos)])
                    elif "{url}" in v:
                        v = v.replace("{url}", urls[_ % len(urls)])
                    elif "{lib}" in v:
                        v = v.replace("{lib}", libs[_ % len(libs)])
                    elif "{problem}" in v:
                        v = v.replace("{problem}", problems[_ % len(problems)])
                    elif "{task}" in v:
                        v = v.replace("{task}", tasks[_ % len(tasks)])
                elif isinstance(v, int):
                    v = v  # Keep as is for limit values
                args_copy[k] = v
            
            if "{query}" in input_text:
                input_text = input_text.replace("{query}", queries[_ % len(queries)])
            elif "{path}" in input_text:
                input_text = input_text.replace("{path}", paths[_ % len(paths)])
            elif "{repo}" in input_text:
                input_text = input_text.replace("{repo}", repos[_ % len(repos)])
            elif "{url}" in input_text:
                input_text = input_text.replace("{url}", urls[_ % len(urls)])
            elif "{lib}" in input_text:
                input_text = input_text.replace("{lib}", libs[_ % len(libs)])
            elif "{problem}" in input_text:
                input_text = input_text.replace("{problem}", problems[_ % len(problems)])
            elif "{task}" in input_text:
                input_text = input_text.replace("{task}", tasks[_ % len(tasks)])
            
            # Clean up empty args
            args_clean = {k: v for k, v in args_copy.items() if v}
            
            # Output format (what the model should generate)
            output_text = f"[TOOL_CALL]{{tool => \"{tool_name}\", args => {{ {', '.join(f'--{k} \"{v}\"' for k, v in args_clean.items())} }}}}[/TOOL_CALL]"
            
            training_pairs.append({
                "input": input_text,
                "output": output_text,
                "tool_name": tool_name,
                "args": args_clean,
            })
    
    # Save dataset
    output_file = PROJECT_ROOT / "datasets" / "rosetta_training.jsonl"
    with open(output_file, "w") as f:
        for pair in training_pairs:
            f.write(json.dumps(pair) + "\n")
    
    print(f"Generated {len(training_pairs)} training pairs")
    print(f"Saved to: {output_file}")
    
    return training_pairs


def prepare_fine_tune_data():
    """Convert to fine-tuning format for Ollama/Unsloth."""
    input_file = PROJECT_ROOT / "datasets" / "rosetta_training.jsonl"
    output_file = PROJECT_ROOT / "datasets" / "rosetta_training.json"
    
    # Read and convert to JSONL for fine-tuning
    with open(input_file) as f:
        data = [json.loads(line) for line in f]
    
    # Format for fine-tuning (instruction tuning style)
    formatted = []
    for item in data:
        formatted.append({
            "messages": [
                {"role": "system", "content": "You are a tool call translator. Convert user requests into MCP tool calls."},
                {"role": "user", "content": item["input"]},
                {"role": "assistant", "content": item["output"]},
            ]
        })
    
    with open(output_file, "w") as f:
        json.dump(formatted, f, indent=2)
    
    print(f"Prepared {len(formatted)} fine-tuning examples")
    return output_file


def train_model():
    """Train the model using Ollama or Unsloth."""
    print("=" * 50)
    print("ROSETTA STONE TRAINING")
    print("=" * 50)
    print("\nTraining approach:")
    print("1. Use Qwen2.5-0.5B-Instruct as base")
    print("2. Fine-tune on your MCP tool call pairs")
    print("3. Result: Local model that translates requests to tool calls")
    print("\nTo train, run:")
    print("  # Option 1: Ollama (simpler)")
    print("  ollama create rosetta -f Modelfile")
    print("")
    print("  # Option 2: Unsloth (faster, better)")
    print("  pip install unsloth")
    print("  python scripts/unsloth_train.py")
    print("")
    print("Training data ready at: datasets/rosetta_training.jsonl")


def test_model():
    """Test the Rosetta Stone model."""
    print("\n=== Rosetta Stone Test ===")
    print("Testing if model correctly translates requests to tool calls\n")
    
    test_cases = [
        ("search memory for security", "memory_search"),
        ("show me README.md", "read_file"),
        ("check git status", "git_status"),
        ("list issues for facebook/react", "github_list_issues"),
        ("fetch https://docs.python.org", "fetch_url"),
    ]
    
    print("Test cases (run after training):")
    for request, expected_tool in test_cases:
        print(f"  Input: '{request}'")
        print(f"  Expected: {expected_tool}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Rosetta Stone Training Pipeline")
    parser.add_argument("--generate-data", action="store_true", help="Generate training data")
    parser.add_argument("--prepare", action="store_true", help="Prepare fine-tuning data")
    parser.add_argument("--train", action="store_true", help="Run training")
    parser.add_argument("--test", action="store_true", help="Test the model")
    args = parser.parse_args()
    
    if args.generate_data:
        generate_training_dataset()
    elif args.prepare:
        prepare_fine_tune_data()
    elif args.train:
        train_model()
    elif args.test:
        test_model()
    else:
        # Run full pipeline
        print("=== Rosetta Stone Pipeline ===\n")
        generate_training_dataset()
        prepare_fine_tune_data()
        train_model()


if __name__ == "__main__":
    main()