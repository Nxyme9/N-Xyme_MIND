#!/usr/bin/env python3
"""Parallel Cloud Training Data Generator - Generate MCP tool training data in parallel.

This script generates training data using multiple parallel workers calling OpenCode Zen.
Focuses on YOUR specific MCP tools from the ecosystem.

Usage:
    python scripts/generate_parallel_training_data.py --workers 4 --total 200
"""

import json
import os
import sys
import argparse
import time
import threading
import queue
from pathlib import Path
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from packages.local_llm.mcp_tool_loader import MCPToolLoader


class MCPToolCaller:
    """Call OpenCode Zen for MCP tool training data."""
    
    SYSTEM_PROMPT = """You are an expert MCP tool calling assistant for N-Xyme_MIND ecosystem.

Your task is to analyze user requests and call the appropriate MCP tool from YOUR specific ecosystem.

MCP TOOLS AVAILABLE (from your actual ecosystem):
{tools_description}

IMPORTANT RULES:
1. ONLY use tools from the list above - these are YOUR real MCP tools
2. Choose the most specific tool for the request
3. Be realistic with arguments - use actual paths, queries, etc.
4. If no tool is needed, respond with plain text
5. Output tool calls in this format: [TOOL_CALL]{tool => "tool_name", args => { --arg1 "value1", --arg2 "value2" }}[/TOOL_CALL]

Example: User asks "find my notes about security" → call memory_search with query="security"
Example: User asks "show me the git status" → call git_status with repo_path="."
"""
    
    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.base_url = "https://opencode.ai/zen/v1"
        self.tools = self._load_tools()
        
    def _load_tools(self) -> List[Dict]:
        loader = MCPToolLoader()
        return loader.get_tools_openai_format()
    
    def _get_tools_description(self) -> str:
        desc = []
        for tool in self.tools:
            func = tool.get("function", {})
            name = func.get("name", "unknown")
            descr = func.get("description", "")
            params = func.get("parameters", {})
            props = params.get("properties", {})
            required = params.get("required", [])
            param_str = ", ".join(required) if required else "none"
            desc.append(f"- {name}: {descr[:100]}... (required: {param_str})")
        return "\n".join(desc[:15])  # Limit to 15 tools to keep context manageable
    
    def _call_api(self, prompt: str) -> Dict:
        headers = {
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/nxyme/N-Xyme_MIND",
            "X-Title": "Rosetta Stone Training",
        }
        
        system = self.SYSTEM_PROMPT.format(tools_description=self._get_tools_description())
        
        data = {
            "model": "minimax-m2.5-free",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 800,
        }
        
        try:
            resp = requests.post(f"{self.base_url}/chat/completions", 
                                headers=headers, json=data, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            return {"content": result["choices"][0]["message"].get("content", ""), "error": None}
        except Exception as e:
            return {"content": "", "error": str(e)}
    
    def _parse_tool_calls(self, content: str) -> List[Dict]:
        import re
        tool_calls = []
        
        # Pattern 1: [TOOL_CALL]{tool => "name", args => { --key "value" }}[/TOOL_CALL]
        pattern1 = r'\[TOOL_CALL\]\s*\{tool\s*=>\s*"([^"]+)",\s*args\s*=>\s*\{([^}]*)\}\}'
        for match in re.finditer(pattern1, content):
            tool_name, args_str = match.groups()
            args = {}
            for key, val in re.findall(r'--(\w+)\s+"([^"]*)"', args_str):
                args[key] = val
            tool_calls.append({"name": tool_name, "args": args})
        
        # Pattern 2: <tool_call><invoke name="name">...
        pattern2 = r'<invoke\s+name="([^"]+)"'
        for match in re.finditer(pattern2, content):
            tool_calls.append({"name": match.group(1), "args": {}})
        
        return tool_calls


def generate_prompts_for_tools() -> List[Dict]:
    """Generate prompts specifically for YOUR MCP tools."""
    loader = MCPToolLoader()
    tools = loader.get_tools_openai_format()
    
    prompts = []
    
    # Tool-specific prompt templates
    tool_prompts = {
        "memory_search": [
            "Search my memory for {topic}",
            "Find information about {topic}",
            "What do I know about {topic}?",
            "Look up {topic} in my knowledge base",
        ],
        "athena_smart_search": [
            "Find code related to {topic}",
            "Search Athena for {topic}",
            "Find project docs about {topic}",
        ],
        "read_file": [
            "Show me the contents of {path}",
            "Read {path} for me",
            "What's in {path}?",
        ],
        "write_file": [
            "Create a file at {path} with content",
            "Write this to {path}",
            "Save this to {path}",
        ],
        "list_directory": [
            "List files in {path}",
            "What's in directory {path}?",
            "Show me {path}",
        ],
        "git_status": [
            "Check git status",
            "Show me modified files",
            "What's the current branch status?",
        ],
        "git_log": [
            "Show recent commits",
            "View commit history",
            "What changed recently?",
        ],
        "git_diff": [
            "Show me the changes",
            "What's different between branches?",
            "View git diff",
        ],
        "github_list_issues": [
            "List issues for {repo}",
            "Show open issues",
            "Check {repo} issues",
        ],
        "fetch_url": [
            "Fetch content from {url}",
            "Get the page at {url}",
            "Retrieve {url}",
        ],
        "context7_query_docs": [
            "How do I use {library}?",
            "Find docs for {library}",
            "Show me {library} examples",
        ],
        "sequential_thinking": [
            "Think through this problem step by step: {problem}",
            "Analyze this: {problem}",
            "Reason about: {problem}",
        ],
        "get_active_context": [
            "What's the current project context?",
            "What are we working on?",
            "Show active context",
        ],
        "route_task": [
            "Which agent should handle: {task}?",
            "Route this task: {task}",
        ],
    }
    
    # Generate diverse prompts for each tool
    topics = ["authentication", "security", "deployment", "testing", "API", "database", 
              "config", "error handling", "memory", "agents", "routing", "MCP"]
    paths = ["src/main.py", "config/app.json", "README.md", "package.json", ".env"]
    repos = ["facebook/react", "microsoft/vscode", "vercel/next.js"]
    urls = ["https://docs.python.org", "https://nodejs.org/api"]
    libraries = ["react", "next.js", "express", "python", "typescript"]
    problems = ["debug this error", "optimize performance", "fix memory leak", "design API"]
    tasks = ["implement auth", "write tests", "refactor code", "create docs"]
    
    for tool_name, templates in tool_prompts.items():
        for template in templates:
            # Replace placeholders with varied values
            prompt = template
            if "{topic}" in prompt:
                prompt = prompt.replace("{topic}", random.choice(topics))
            if "{path}" in prompt:
                prompt = prompt.replace("{path}", random.choice(paths))
            if "{repo}" in prompt:
                prompt = prompt.replace("{repo}", random.choice(repos))
            if "{url}" in prompt:
                prompt = prompt.replace("{url}", random.choice(urls))
            if "{library}" in prompt:
                prompt = prompt.replace("{library}", random.choice(libraries))
            if "{problem}" in prompt:
                prompt = prompt.replace("{problem}", random.choice(problems))
            if "{task}" in prompt:
                prompt = prompt.replace("{task}", random.choice(tasks))
            
            prompts.append({
                "tool_name": tool_name,
                "prompt": prompt,
            })
    
    return prompts


def worker_task(worker_id: int, prompts: List[Dict], output_queue: queue.Queue, 
                rate_limiter: dict, lock: threading.Lock):
    """Worker task that processes prompts."""
    caller = MCPToolCaller(worker_id)
    processed = 0
    
    for item in prompts:
        # Rate limiting
        with lock:
            now = time.time()
            if now - rate_limiter["last_reset"] > 60:
                rate_limiter["count"] = 0
                rate_limiter["last_reset"] = now
            
            if rate_limiter["count"] >= 8:
                wait = 60 - (now - rate_limiter["last_reset"])
                if wait > 0:
                    time.sleep(wait)
                rate_limiter["count"] = 0
                rate_limiter["last_reset"] = time.time()
            rate_limiter["count"] += 1
        
        result = caller._call_api(item["prompt"])
        
        if not result.get("error"):
            tool_calls = caller._parse_tool_calls(result["content"])
            if tool_calls:
                output_queue.put({
                    "tool_name": item["tool_name"],
                    "prompt": item["prompt"],
                    "parsed_calls": tool_calls,
                    "raw_response": result["content"],
                })
                processed += 1
        
        time.sleep(0.3)  # Small delay between requests
    
    return processed


def main():
    parser = argparse.ArgumentParser(description="Generate MCP tool training data in parallel")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers")
    parser.add_argument("--total", type=int, default=200, help="Total prompts to process")
    parser.add_argument("--output", type=str, default="datasets/mcp_tool_calls.jsonl", 
                       help="Output file")
    args = parser.parse_args()
    
    print(f"Generating MCP tool training data with {args.workers} workers...")
    print(f"Target: {args.total} prompts")
    
    # Generate prompts
    all_prompts = generate_prompts_for_tools()
    import random
    random.shuffle(all_prompts)
    all_prompts = all_prompts[:args.total]
    
    print(f"Generated {len(all_prompts)} unique prompts for YOUR MCP tools")
    
    # Split prompts among workers
    chunk_size = len(all_prompts) // args.workers + 1
    prompt_chunks = [all_prompts[i:i+chunk_size] for i in range(0, len(all_prompts), chunk_size)]
    
    # Shared rate limiter
    rate_limiter = {"count": 0, "last_reset": time.time()}
    rate_lock = threading.Lock()
    
    # Output queue
    output_queue = queue.Queue()
    
    # Run workers in parallel
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(worker_task, i, chunk, output_queue, rate_limiter, rate_lock)
            for i, chunk in enumerate(prompt_chunks)
        ]
        
        completed = 0
        for future in as_completed(futures):
            try:
                result = future.result()
                completed += 1
                print(f"Worker {completed}/{args.workers} completed - {result} examples generated")
            except Exception as e:
                print(f"Worker error: {e}")
    
    # Collect results
    results = []
    while not output_queue.empty():
        results.append(output_queue.get())
    
    # Save to file
    output_path = PROJECT_ROOT / args.output
    with open(output_path, "w") as f:
        for item in results:
            f.write(json.dumps(item) + "\n")
    
    elapsed = time.time() - start_time
    
    print(f"\n=== Results ===")
    print(f"Total processed: {len(all_prompts)}")
    print(f"Valid tool calls: {len(results)}")
    print(f"Time: {elapsed:.1f}s")
    print(f"Output: {output_path}")
    
    # Tool coverage
    tool_counts = {}
    for item in results:
        for tc in item["parsed_calls"]:
            name = tc["name"]
            tool_counts[name] = tool_counts.get(name, 0) + 1
    
    print(f"\n=== Tool Coverage ===")
    for name, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
        print(f"  {name}: {count}")


if __name__ == "__main__":
    main()