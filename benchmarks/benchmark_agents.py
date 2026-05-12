#!/usr/bin/env python3
"""
GGUF Agent Benchmark - Test parallel agent execution with local GGUF models

Usage:
    python benchmark_agents.py --agents explore,librarian --parallel 5
    python benchmark_agents.py --models gguf/qwen2.5-0.5b,ollama/llama3.2:3b --parallel 3
"""

import argparse
import asyncio
import json
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8081/v1"
HEALTH_URL = "http://localhost:8081/health"

# Test prompts for different agent types
TEST_PROMPTS = {
    "explore": [
        "Find all Python files in packages/ that contain 'llama'",
        "Find files with class definition for ModelRegistry",
        "Search for 'gguf' in the codebase",
        "Find functions that handle embeddings",
        "Find JSON config files in the project",
    ],
    "librarian": [
        "How does llama-cpp-python handle embeddings?",
        "What is the best practice for GGUF quantization?",
        "How to use LoRA adapters with llama.cpp?",
    ],
    "hephaestus": [
        "Write a simple hello world function",
        "Create a basic data class for User",
        "Write a function to calculate fibonacci",
    ],
}


def chat_completion(
    model: str, messages: List[Dict], max_tokens: int = 100
) -> Dict[str, Any]:
    """Make a chat completion request to the GGUF server."""
    url = f"{BASE_URL}/chat/completions"
    data = json.dumps(
        {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
    ).encode()

    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )

    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode())
            elapsed = time.time() - start_time
            return {
                "success": True,
                "model": model,
                "response": result["choices"][0]["message"]["content"][:100],
                "elapsed": elapsed,
                "tokens": result.get("usage", {}).get("total_tokens", 0),
            }
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start_time
        return {
            "success": False,
            "model": model,
            "error": f"HTTP {e.code}: {e.reason}",
            "elapsed": elapsed,
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "success": False,
            "model": model,
            "error": str(e),
            "elapsed": elapsed,
        }


def run_parallel_requests(
    model: str, prompts: List[str], parallel: int = 3
) -> List[Dict]:
    """Run multiple requests in parallel."""
    results = []

    with ThreadPoolExecutor(max_workers=parallel) as executor:
        futures = []
        for prompt in prompts[:parallel]:
            future = executor.submit(
                chat_completion, model, [{"role": "user", "content": prompt}]
            )
            futures.append(future)

        for future in as_completed(futures):
            results.append(future.result())

    return results


def benchmark_model(
    model: str, prompts: List[str], parallel: int = 3, rounds: int = 3
) -> Dict[str, Any]:
    """Benchmark a model with multiple rounds."""
    all_results = []

    for round_num in range(1, rounds + 1):
        print(f"  Round {round_num}/{rounds}...", end=" ", flush=True)
        results = run_parallel_requests(model, prompts, parallel)
        all_results.extend(results)
        print(f"done ({len(results)} requests)")

    successful = [r for r in all_results if r["success"]]
    failed = [r for r in all_results if not r["success"]]

    if successful:
        avg_time = statistics.mean([r["elapsed"] for r in successful])
        total_tokens = sum([r.get("tokens", 0) for r in successful])
        tokens_per_sec = (
            total_tokens / sum([r["elapsed"] for r in successful]) if successful else 0
        )

        return {
            "model": model,
            "total_requests": len(all_results),
            "successful": len(successful),
            "failed": len(failed),
            "avg_time": round(avg_time, 2),
            "total_tokens": total_tokens,
            "tokens_per_sec": round(tokens_per_sec, 2),
            "samples": [r["response"] for r in successful[:2]],
        }
    else:
        return {
            "model": model,
            "total_requests": len(all_results),
            "successful": 0,
            "failed": len(failed),
            "errors": [r.get("error") for r in failed[:3]],
        }


def main():
    parser = argparse.ArgumentParser(description="GGUF Agent Benchmark")
    parser.add_argument(
        "--models",
        type=str,
        default="qwen2.5-0.5b-instruct-q4_k_m",
        help="Comma-separated list of models to test (use model ID, not provider prefix)",
    )
    parser.add_argument(
        "--agents",
        type=str,
        default="explore",
        help="Agent type (explore, librarian, hephaestus)",
    )
    parser.add_argument(
        "--parallel", type=int, default=3, help="Number of parallel requests"
    )
    parser.add_argument(
        "--rounds", type=int, default=3, help="Number of benchmark rounds"
    )
    args = parser.parse_args()

    # Strip provider prefixes like "gguf/" or "ollama/"
    models = [m.split("/")[-1] for m in args.models.split(",")]
    agent_type = args.agents

    print("=" * 60)
    print(f"GGUF Agent Benchmark")
    print("=" * 60)
    print(f"Agent: {agent_type}")
    print(f"Models: {models}")
    print(f"Parallel: {args.parallel}")
    print(f"Rounds: {args.rounds}")
    print("=" * 60)

    # Get prompts for agent type
    prompts = TEST_PROMPTS.get(agent_type, TEST_PROMPTS["explore"])
    print(f"\nPrompts ({len(prompts)}):")
    for i, p in enumerate(prompts[:3], 1):
        print(f"  {i}. {p[:60]}...")

    # Check server health (with retries)
    server_ready = False
    for attempt in range(5):
        try:
            urllib.request.urlopen(HEALTH_URL, timeout=2)
            server_ready = True
            break
        except Exception as e:
            if attempt < 4:
                time.sleep(1)
                continue
            else:
                print(f"\nERROR: GGUF server not running on port 8081: {e}")
                print("Run: ./start_gguf_server.sh")
                return

    # Run benchmarks
    print("\n" + "=" * 60)
    results = []

    for model in models:
        model_name = model.split("/")[-1] if "/" in model else model
        print(f"\nBenchmarking: {model}")

        result = benchmark_model(model, prompts, args.parallel, args.rounds)
        results.append(result)

        if result.get("successful", 0) > 0:
            print(f"  ✓ Avg time: {result['avg_time']}s")
            print(f"  ✓ Tokens: {result.get('total_tokens', 0)}")
            print(f"  ✓ Throughput: {result.get('tokens_per_sec', 0)} tok/s")
        else:
            print(f"  ✗ Failed: {result.get('errors', ['Unknown error'])}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Model':<35} {'Time':>8} {'Tokens':>8} {'Tok/s':>8}")
    print("-" * 60)
    for r in results:
        model_short = r["model"][:30] + "..." if len(r["model"]) > 30 else r["model"]
        if r.get("successful", 0) > 0:
            print(
                f"{model_short:<35} {r['avg_time']:>7}s {r.get('total_tokens', 0):>8} {r.get('tokens_per_sec', 0):>7}"
            )
        else:
            print(f"{model_short:<35} {'FAILED':>8}")
    print("=" * 60)


if __name__ == "__main__":
    main()
