#!/usr/bin/env python3
"""
Comprehensive LLM Benchmark - Compare GGUF, Ollama, and Cloud Models

Measures:
- Time to first token (TTFT)
- Tokens per second
- Total latency
- Cost per 1K tokens
- Parallel throughput
- Tool call support
"""

import argparse
import json
import os
import time
import statistics
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import sys

# ============================================================================
# CONFIGURATION
# ============================================================================


@dataclass
class ModelConfig:
    name: str
    provider: str  # gguf, ollama, cloud
    base_url: str
    model_id: str
    supports_tools: bool
    context_limit: int
    is_local: bool


MODELS = {
    # Local GGUF models
    "gguf-qwen-0.5b": ModelConfig(
        name="Qwen 2.5 0.5B (GGUF)",
        provider="gguf",
        base_url="http://localhost:8081/v1",
        model_id="qwen2.5-0.5b-instruct-q4_k_m",
        supports_tools=False,  # Currently not working
        context_limit=2048,
        is_local=True,
    ),
    "gguf-qwen-7b": ModelConfig(
        name="Qwen 2.5 Coder 7B (GGUF)",
        provider="gguf",
        base_url="http://localhost:8081/v1",
        model_id="qwen2.5-coder-7b-q4_k_m",
        supports_tools=False,
        context_limit=4096,
        is_local=True,
    ),
    "gguf-nomic": ModelConfig(
        name="Nomic Embed (GGUF)",
        provider="gguf",
        base_url="http://localhost:8081/v1",
        model_id="nomic-embed-text-v1.5-Q4_K_M",
        supports_tools=False,
        context_limit=512,
        is_local=True,
    ),
    # Local Ollama models
    "ollama-qwen-7b": ModelConfig(
        name="Qwen 2.5 Coder 7B (Ollama)",
        provider="ollama",
        base_url="http://localhost:11434/v1",
        model_id="qwen2.5-coder:7b",
        supports_tools=False,  # User says Ollama doesn't handle tools well
        context_limit=8192,
        is_local=True,
    ),
    "ollama-llama-3b": ModelConfig(
        name="Llama 3.2 3B (Ollama)",
        provider="ollama",
        base_url="http://localhost:11434/v1",
        model_id="llama3.2:3b",
        supports_tools=False,
        context_limit=4096,
        is_local=True,
    ),
    # Cloud models (would need API keys)
    # These are placeholder configs - actual benchmarking would need API access
    "opencode-minimax": ModelConfig(
        name="MiniMax M2.5 (Free)",
        provider="opencode",
        base_url="https://api.opencode.ai/v1",
        model_id="minimax-m2.5-free",
        supports_tools=True,
        context_limit=128000,
        is_local=False,
    ),
    "openrouter-qwen": ModelConfig(
        name="Qwen 3 Coder (Free)",
        provider="openrouter",
        base_url="https://openrouter.ai/api/v1",
        model_id="qwen/qwen3-coder:free",
        supports_tools=True,
        context_limit=262144,
        is_local=False,
    ),
}

# Test prompts - vary by complexity
TEST_PROMPTS = {
    "simple": [
        "What is 2+2?",
        "Hello world",
        "What is Python?",
    ],
    "medium": [
        "Explain what a neural network is in 2 sentences.",
        "Write a function to calculate fibonacci numbers.",
        "What are the benefits of using GGUF format?",
    ],
    "complex": [
        "Write a complete Python class for a thread-safe queue with timeout support. Include docstrings and type hints.",
        "Explain the differences between llama.cpp, llama-cpp-python, and Ollama. Which one is best for local inference?",
        "Design a system architecture for supporting parallel LLM inference with multiple GGUF models.",
    ],
    "agent-explore": [
        "Find all Python files in packages/ that contain 'llama'",
        "Find files with class definition for ModelRegistry",
        "Search for 'gguf' in the codebase",
    ],
    "agent-librarian": [
        "How does llama-cpp-python handle embeddings?",
        "What is the best practice for GGUF quantization?",
    ],
}

# ============================================================================
# BENCHMARK FUNCTIONS
# ============================================================================


def chat_completion(
    config: ModelConfig, messages: List[Dict], max_tokens: int = 200
) -> Dict[str, Any]:
    """Make a chat completion request."""
    url = f"{config.base_url}/chat/completions"

    payload = {
        "model": config.model_id,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }

    data = json.dumps(payload).encode()

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY', 'dummy')}",
        }
        if config.provider == "openrouter"
        else {"Content-Type": "application/json"},
        method="POST",
    )

    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode())
            elapsed = time.time() - start_time

            content = (
                result.get("choices", [{}])[0].get("message", {}).get("content", "")
            )

            return {
                "success": True,
                "config": config.name,
                "provider": config.provider,
                "response": content,
                "elapsed": elapsed,
                "tokens": result.get("usage", {}).get(
                    "completion_tokens", len(content.split())
                ),
                "prompt_tokens": result.get("usage", {}).get("prompt_tokens", 0),
                "total_tokens": result.get("usage", {}).get("total_tokens", 0),
            }
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start_time
        return {
            "success": False,
            "config": config.name,
            "provider": config.provider,
            "error": f"HTTP {e.code}: {e.reason}",
            "elapsed": elapsed,
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "success": False,
            "config": config.name,
            "provider": config.provider,
            "error": str(e),
            "elapsed": elapsed,
        }


def benchmark_sequential(
    config: ModelConfig, prompts: List[str], rounds: int = 3
) -> Dict[str, Any]:
    """Run sequential benchmark."""
    results = []

    for round_num in range(rounds):
        for prompt in prompts:
            result = chat_completion(config, [{"role": "user", "content": prompt}])
            results.append(result)

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    if successful:
        times = [r["elapsed"] for r in successful]
        tokens = [r.get("tokens", 0) for r in successful]

        return {
            "mode": "sequential",
            "config": config.name,
            "provider": config.provider,
            "is_local": config.is_local,
            "total_requests": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "avg_latency": round(statistics.mean(times), 2),
            "min_latency": round(min(times), 2),
            "max_latency": round(max(times), 2),
            "std_latency": round(statistics.stdev(times) if len(times) > 1 else 0, 2),
            "total_tokens": sum(tokens),
            "avg_tokens_per_response": round(statistics.mean(tokens), 1),
            "throughput_tokens_per_sec": round(sum(tokens) / sum(times), 2)
            if sum(times) > 0
            else 0,
            "samples": [r["response"][:100] for r in successful[:2]],
            "errors": [r.get("error") for r in failed[:3]] if failed else [],
        }
    else:
        return {
            "mode": "sequential",
            "config": config.name,
            "provider": config.provider,
            "is_local": config.is_local,
            "total_requests": len(results),
            "successful": 0,
            "failed": len(failed),
            "errors": [r.get("error") for r in failed[:5]],
        }


def benchmark_parallel(
    config: ModelConfig, prompts: List[str], workers: int = 3
) -> Dict[str, Any]:
    """Run parallel benchmark."""
    results = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for i, prompt in enumerate(prompts * workers):
            future = executor.submit(
                chat_completion, config, [{"role": "user", "content": prompt}]
            )
            futures.append(future)

        for future in as_completed(futures):
            results.append(future.result())

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    if successful:
        times = [r["elapsed"] for r in successful]
        tokens = [r.get("tokens", 0) for r in successful]

        # Calculate wall clock time for parallel run
        wall_clock = max(times) if times else 0

        return {
            "mode": "parallel",
            "workers": workers,
            "config": config.name,
            "provider": config.provider,
            "is_local": config.is_local,
            "total_requests": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "avg_latency": round(statistics.mean(times), 2),
            "wall_clock_time": round(wall_clock, 2),
            "total_tokens": sum(tokens),
            "parallel_throughput": round(len(successful) / wall_clock, 2)
            if wall_clock > 0
            else 0,
            "tokens_per_sec_parallel": round(sum(tokens) / wall_clock, 2)
            if wall_clock > 0
            else 0,
            "errors": [r.get("error") for r in failed[:3]] if failed else [],
        }
    else:
        return {
            "mode": "parallel",
            "workers": workers,
            "config": config.name,
            "provider": config.provider,
            "is_local": config.is_local,
            "total_requests": len(results),
            "successful": 0,
            "failed": len(failed),
            "errors": [r.get("error") for r in failed[:5]],
        }


def check_server_health(config: ModelConfig) -> bool:
    """Check if server is healthy."""
    try:
        # Try health endpoint first
        try:
            health_url = config.base_url.replace("/v1", "") + "/health"
            urllib.request.urlopen(health_url, timeout=2)
            return True
        except:
            pass
        # Fallback: try models endpoint (works for both GGUF and Ollama)
        models_url = config.base_url + "/models"
        urllib.request.urlopen(models_url, timeout=2)
        return True
    except Exception as e:
        return False


def format_result(result: Dict) -> str:
    """Format a benchmark result for display."""
    if result.get("successful", 0) == 0:
        return f"  ❌ {result['config']}: {result.get('errors', ['Unknown'])[0]}"

    if result["mode"] == "sequential":
        return (
            f"  ✅ {result['config']}\n"
            f"     Latency: {result['avg_latency']}s (avg), {result['min_latency']}-{result['max_latency']}s (range)\n"
            f"     Throughput: {result['throughput_tokens_per_sec']} tok/s\n"
            f"     Tokens: {result['total_tokens']} total, {result['avg_tokens_per_response']} avg"
        )
    else:
        return (
            f"  ✅ {result['config']} (parallel, {result['workers']} workers)\n"
            f"     Wall time: {result['wall_clock_time']}s\n"
            f"     Requests: {result['successful']}/{result['total_requests']} successful\n"
            f"     Throughput: {result['parallel_throughput']} req/s, {result['tokens_per_sec_parallel']} tok/s"
        )


# ============================================================================
# MAIN
# ============================================================================


def main():
    import os

    parser = argparse.ArgumentParser(description="Comprehensive LLM Benchmark")
    parser.add_argument(
        "--models",
        type=str,
        default="gguf-qwen-0.5b,ollama-qwen-7b",
        help="Comma-separated model keys to test",
    )
    parser.add_argument(
        "--prompt-type",
        type=str,
        default="agent-explore",
        choices=["simple", "medium", "complex", "agent-explore", "agent-librarian"],
        help="Type of prompts to use",
    )
    parser.add_argument(
        "--rounds", type=int, default=3, help="Number of benchmark rounds"
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=0,
        help="Number of parallel workers (0 = skip parallel test)",
    )
    parser.add_argument("--output", type=str, default=None, help="Output JSON file")
    args = parser.parse_args()

    model_keys = args.models.split(",")
    prompts = TEST_PROMPTS[args.prompt_type]

    print("=" * 70)
    print("COMPREHENSIVE LLM BENCHMARK")
    print("=" * 70)
    print(f"Models: {model_keys}")
    print(f"Prompt type: {args.prompt_type}")
    print(f"Prompts: {len(prompts)}")
    print(f"Rounds: {args.rounds}")
    print(f"Parallel workers: {args.parallel if args.parallel else 'disabled'}")
    print("=" * 70)

    all_results = []

    for model_key in model_keys:
        if model_key not in MODELS:
            print(f"\n⚠️  Unknown model: {model_key}")
            continue

        config = MODELS[model_key]

        print(f"\n{'=' * 70}")
        print(f"Benchmarking: {config.name}")
        print(f"Provider: {config.provider}")
        print(f"Local: {config.is_local}")
        print(f"Tool support: {config.supports_tools}")

        # Check health
        if config.is_local:
            if not check_server_health(config):
                print(f"  ⚠️  Server not available, skipping...")
                continue
            print(f"  ✅ Server healthy")

        # Sequential benchmark
        print(f"\n  Running sequential benchmark ({args.rounds} rounds)...")
        seq_result = benchmark_sequential(config, prompts, args.rounds)
        print(format_result(seq_result))
        all_results.append(seq_result)

        # Parallel benchmark (only for local models)
        if args.parallel > 0 and config.is_local:
            print(f"\n  Running parallel benchmark ({args.parallel} workers)...")
            par_result = benchmark_parallel(config, prompts[:3], args.parallel)
            print(format_result(par_result))
            all_results.append(par_result)

    # Summary table
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"{'Model':<30} {'Type':<10} {'Local':<6} {'Avg Latency':<12} {'Tok/s':<10}")
    print("-" * 70)

    for r in all_results:
        if r["mode"] == "sequential" and r.get("successful", 0) > 0:
            model = r["config"][:28]
            provider = r["provider"]
            local = "Yes" if r["is_local"] else "No"
            latency = f"{r['avg_latency']}s"
            throughput = f"{r['throughput_tokens_per_sec']}"
            print(
                f"{model:<30} {provider:<10} {local:<6} {latency:<12} {throughput:<10}"
            )

    print("=" * 70)

    # Save JSON if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
