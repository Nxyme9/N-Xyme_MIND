#!/usr/bin/env python3
"""Generate training data for Rosetta Stone from MCP tool schemas."""

import json
import random
from pathlib import Path
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).parent.parent


def main():
    print("Generating Rosetta Stone training data...")
    
    templates = [
        # Memory & Knowledge
        ("search memory for {q}", "memory_search", {"query": "{q}", "limit": 10}),
        ("find info about {q}", "athena_smart_search", {"query": "{q}"}),
        ("remember {c}", "memory_write", {"content": "{c}", "kind": "episodic"}),
        
        # Filesystem
        ("read {p}", "read_file", {"path": "{p}"}),
        ("show me {p}", "read_file", {"path": "{p}"}),
        ("write {c} to {p}", "write_file", {"path": "{p}", "content": "{c}"}),
        ("list files in {p}", "list_directory", {"path": "{p}"}),
        
        # Git
        ("check git status", "git_status", {"repo_path": "."}),
        ("show git log", "git_log", {"repo_path": ".", "max_count": 10}),
        ("show diff", "git_diff", {"repo_path": ".", "target": "HEAD"}),
        
        # GitHub
        ("list issues for {o}/{r}", "github_list_issues", {"owner": "{o}", "repo": "{r}"}),
        
        # Web & Docs
        ("fetch {u}", "fetch_url", {"url": "{u}", "format": "markdown"}),
        ("get {l} docs", "context7_query_docs", {"library_id": "/{l}", "query": "basics"}),
        
        # Reasoning
        ("think about {p}", "sequential_thinking", {"thought": "{p}", "nextThoughtNeeded": True, "thoughtNumber": 1, "totalThoughts": 3}),
        
        # Context & Routing
        ("get active context", "get_active_context", {}),
        ("route task: {t}", "route_task", {"task_description": "{t}"}),
        
        # Health
        ("check health", "get_health", {"level": "l0"}),
        
        # Browser
        ("open {u}", "browser_navigate", {"url": "{u}"}),
    ]
    
    queries = ["security", "auth", "deploy", "test", "api", "config"]
    paths = ["README.md", "src/main.py", "config.json", "package.json"]
    owners = ["facebook", "microsoft", "vercel"]
    repos = ["react", "vscode", "next.js"]
    urls = ["https://python.org", "https://nodejs.org", "https://react.dev"]
    libs = ["react", "python", "typescript"]
    probs = ["debug error", "optimize", "design API"]
    tasks = ["implement auth", "write tests", "refactor"]
    contents = ["hello world", "test data", "config here"]
    
    values = {
        "q": queries, "p": paths, "o": owners, "r": repos,
        "u": urls, "l": libs, "p": probs, "t": tasks, "c": contents
    }
    
    pairs = []
    for _ in range(300):
        template, tool, args = random.choice(templates)
        input_text = template
        args_out = {}
        
        for k, v in args.items():
            if isinstance(v, str) and "{" in v:
                var = v.replace("{", "").replace("}", "")
                if var in values:
                    val = random.choice(values[var])
                    input_text = input_text.replace(f"{{{var}}}", val)
                    args_out[k] = val
                else:
                    args_out[k] = v
            else:
                args_out[k] = v
        
        # Clean placeholders from input
        input_text = input_text.replace("{", "").replace("}", "")
        
        args_str = ", ".join(f'--{k} "{v}"' for k, v in args_out.items())
        output_text = f"[TOOL_CALL]{{tool => \"{tool}\", args => {{ {args_str} }}}}[/TOOL_CALL]"
        
        pairs.append({"input": input_text, "output": output_text, "tool": tool, "args": args_out})
    
    output_file = PROJECT_ROOT / "datasets" / "rosetta_full_training.jsonl"
    with open(output_file, "w") as f:
        for p in pairs:
            f.write(json.dumps(p) + "\n")
    
    print(f"Generated {len(pairs)} training pairs -> {output_file}")


if __name__ == "__main__":
    main()