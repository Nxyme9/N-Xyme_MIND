#!/usr/bin/env python3
"""Benchmark: Rosetta Stone vs Direct Tool Calling

Compares:
1. Rosetta Stone approach: user request -> Rosetta model -> tool call -> execute
2. Direct approach: qwen2.5-coder:7b with native tool calling

Usage:
    python scripts/benchmark_rosetta.py
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).parent.parent

# Test cases
TEST_CASES = [
    ("search memory for security", "memory_search"),
    ("show me README.md", "read_file"),
    ("check git status", "git_status"),
    ("list issues for facebook/react", "github_list_issues"),
    ("fetch https://python.org", "fetch_url"),
    ("get health", "get_health"),
    ("list files in src", "list_directory"),
    ("think about debugging", "sequential_thinking"),
    ("get active context", "get_active_context"),
    ("open https://docs.python.org", "browser_navigate"),
]


def call_rosetta(prompt: str) -> tuple:
    """Call Rosetta Stone model - returns (tool_call, latency_ms)."""
    start = time.time()
    result = subprocess.run(
        ["ollama", "run", "rosetta", prompt],
        capture_output=True,
        text=True,
        timeout=30,
    )
    latency = (time.time() - start) * 1000
    
    # Parse tool call
    import re
    pattern = r'\[TOOL_CALL\]\s*\{.*?tool\s*=>\s*"([^"]+)".*?args\s*=>\s*\{([^}]*)\}'
    match = re.search(pattern, result.stdout, re.DOTALL)
    
    if match:
        tool = match.group(1)
        return {"tool": tool, "raw": result.stdout}, latency
    return {"tool": None, "raw": result.stdout}, latency


def call_direct(prompt: str) -> tuple:
    """Call qwen2.5-coder:7b directly with tool instructions - returns (tool_call, latency_ms)."""
    start = time.time()
    
    # Modified prompt that asks for tool call
    system_prompt = """You are a tool calling assistant. When asked to perform a task that requires tools, respond ONLY with a tool call in this exact JSON format:
{"name": "tool_name", "arguments": {"key": "value"}}

Available tools: memory_search, read_file, write_file, list_directory, git_status, git_log, git_diff, github_list_issues, fetch_url, get_health, browser_navigate, sequential_thinking, get_active_context

Respond with JSON only, no other text."""
    
    full_prompt = f"{system_prompt}\n\nUser: {prompt}\nAssistant:"
    
    result = subprocess.run(
        ["ollama", "run", "qwen2.5-coder:7b", full_prompt],
        capture_output=True,
        text=True,
        timeout=30,
    )
    latency = (time.time() - start) * 1000
    
    # Try to parse JSON
    import re
    try:
        # Try to find JSON in response
        json_match = re.search(r'\{[^{}]*"name"[^{}]*\}', result.stdout)
        if json_match:
            data = json.loads(json_match.group())
            return {"tool": data.get("name"), "args": data.get("arguments", {}), "raw": result.stdout}, latency
    except:
        pass
    
    return {"tool": None, "raw": result.stdout}, latency


def evaluate_results(results: List[Dict], name: str) -> Dict:
    """Evaluate results and compute metrics."""
    correct = sum(1 for r in results if r.get("correct"))
    total = len(results)
    avg_latency = sum(r.get("latency_ms", 0) for r in results) / total
    
    return {
        "name": name,
        "accuracy": f"{correct}/{total} ({100*correct/total:.0f}%)",
        "correct": correct,
        "total": total,
        "avg_latency_ms": round(avg_latency, 0),
    }


def run_benchmark():
    """Run the benchmark."""
    print("=" * 60)
    print("ROSETTA STONE vs DIRECT TOOL CALLING BENCHMARK")
    print("=" * 60)
    print(f"\nTest cases: {len(TEST_CASES)}")
    print(f"Model 1: Rosetta Stone (qwen2.5-coder:7b with tool call prompt)")
    print(f"Model 2: Direct (qwen2.5-coder:7b with JSON tool format)")
    print()
    
    rosetta_results = []
    direct_results = []
    
    print("Running tests...")
    print("-" * 60)
    
    for i, (prompt, expected_tool) in enumerate(TEST_CASES):
        print(f"\n[{i+1}/{len(TEST_CASES)}] {prompt}")
        
        # Test Rosetta
        rosetta_call, rosetta_latency = call_rosetta(prompt)
        rosetta_correct = rosetta_call.get("tool") == expected_tool
        rosetta_results.append({
            "prompt": prompt,
            "expected": expected_tool,
            "got": rosetta_call.get("tool"),
            "correct": rosetta_correct,
            "latency_ms": rosetta_latency,
            "raw": rosetta_call.get("raw", "")[:100],
        })
        print(f"  Rosetta: {rosetta_call.get('tool')} ({rosetta_latency:.0f}ms) {'✓' if rosetta_correct else '✗'}")
        
        # Test Direct
        direct_call, direct_latency = call_direct(prompt)
        direct_correct = direct_call.get("tool") == expected_tool
        direct_results.append({
            "prompt": prompt,
            "expected": expected_tool,
            "got": direct_call.get("tool"),
            "correct": direct_correct,
            "latency_ms": direct_latency,
            "raw": direct_call.get("raw", "")[:100],
        })
        print(f"  Direct:  {direct_call.get('tool')} ({direct_latency:.0f}ms) {'✓' if direct_correct else '✗'}")
    
    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    
    rosetta_stats = evaluate_results(rosetta_results, "Rosetta Stone")
    direct_stats = evaluate_results(direct_results, "Direct")
    
    print(f"\n{'Method':<20} {'Accuracy':<15} {'Avg Latency':<15}")
    print("-" * 50)
    print(f"{rosetta_stats['name']:<20} {rosetta_stats['accuracy']:<15} {rosetta_stats['avg_latency_ms']:.0f}ms")
    print(f"{direct_stats['name']:<20} {direct_stats['accuracy']:<15} {direct_stats['avg_latency_ms']:.0f}ms")
    
    print(f"\n📊 Analysis:")
    print(f"  - Rosetta Stone accuracy: {rosetta_stats['accuracy']}")
    print(f"  - Direct tool calling accuracy: {direct_stats['accuracy']}")
    print(f"  - Rosetta avg latency: {rosetta_stats['avg_latency_ms']:.0f}ms")
    print(f"  - Direct avg latency: {direct_stats['avg_latency_ms']:.0f}ms")
    
    # Winner
    if rosetta_stats['correct'] > direct_stats['correct']:
        print(f"\n🏆 WINNER: Rosetta Stone (+{rosetta_stats['correct'] - direct_stats['correct']} correct)")
    elif direct_stats['correct'] > rosetta_stats['correct']:
        print(f"\n🏆 WINNER: Direct (+{direct_stats['correct'] - rosetta_stats['correct']} correct)")
    else:
        print(f"\n🏆 TIE: Both equally accurate")
    
    # Save results
    output = {
        "test_cases": len(TEST_CASES),
        "rosetta": rosetta_stats,
        "direct": direct_stats,
        "details": {
            "rosetta": rosetta_results,
            "direct": direct_results,
        },
    }
    
    output_file = PROJECT_ROOT / "benchmark_results.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    run_benchmark()