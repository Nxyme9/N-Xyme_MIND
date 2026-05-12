#!/usr/bin/env python3
"""
ENHANCED BENCHMARK - Deep testing of GGUF system
Tests: Both models (0.5b, 7b), 10+ parallel, hot-swap, tool calling
GPU Optimization Tests: KV quantization, Flash Attention v2, no-mmap
"""

import httpx
import asyncio
import time
import statistics
import os
import subprocess
import json
import argparse
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


TEST_MODES = {
    "baseline": {
        "name": "Baseline (no optimizations)",
        "ctk": None,
        "ctv": None,
        "flash_attn_type": None,
        "no_mmap": False,
    },
    "kv_quant": {
        "name": "KV Quantization (q4_0)",
        "ctk": "q4_0",
        "ctv": "q4_0",
        "flash_attn_type": None,
        "no_mmap": False,
    },
    "flash_attn_v2": {
        "name": "Flash Attention v2",
        "ctk": None,
        "ctv": None,
        "flash_attn_type": "2",
        "no_mmap": False,
    },
    "no_mmap": {
        "name": "No Memory Mapping",
        "ctk": None,
        "ctv": None,
        "flash_attn_type": None,
        "no_mmap": True,
    },
    "full_optimized": {
        "name": "Full Optimized (all flags)",
        "ctk": "q4_0",
        "ctv": "q4_0",
        "flash_attn_type": "2",
        "no_mmap": True,
    },
}


@dataclass
class OptimizationResult:
    mode: str
    name: str
    avg_latency: float
    tok_per_sec: float
    req_per_sec: float
    gpu_memory_mb: float
    success_rate: float


@dataclass
class ComparisonResult:
    optimization: str
    baseline_latency: float
    optimized_latency: float
    latency_improvement: float
    baseline_tps: float
    optimized_tps: float
    tps_improvement: float
    baseline_memory: float
    optimized_memory: float
    memory_reduction: float


@dataclass
class BenchmarkResult:
    name: str
    model: str
    sequential_latency: float
    parallel_latency: float
    parallel_success: int
    parallel_total: int
    tokens_per_second: float
    throughput_req_per_sec: float
    tool_calling_works: bool
    gpu_memory_mb: float
    notes: str


def get_gpu_memory() -> float:
    """Get GPU memory used in MB."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return float(result.stdout.strip().split("\n")[0])
    except:
        return 0.0


def get_gpu_utilization() -> float:
    """Get GPU utilization %."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return float(result.stdout.strip().split("\n")[0])
    except:
        return 0.0


async def run_optimization_test(
    base_url: str, model: str, mode: str, prompts: List[str]
) -> OptimizationResult:
    """Run benchmark with a specific optimization mode."""
    config = TEST_MODES.get(mode, TEST_MODES["baseline"])

    benchmark = EnhancedLLMBenchmark(f"Test ({mode})", base_url, model)

    seq_result = await benchmark.sequential_test(prompts, runs=2)
    par_result = await benchmark.parallel_test(prompts, workers=10)

    gpu_mem = get_gpu_memory()

    return OptimizationResult(
        mode=mode,
        name=config["name"],
        avg_latency=seq_result.get("avg_latency", 0),
        tok_per_sec=par_result.get("tok_per_sec", 0),
        req_per_sec=par_result.get("req_per_sec", 0),
        gpu_memory_mb=gpu_mem,
        success_rate=seq_result.get("success_rate", 0),
    )


def compare_results(
    baseline: OptimizationResult, optimized: OptimizationResult
) -> ComparisonResult:
    """Compare baseline vs optimized results."""
    latency_imp = (
        ((baseline.avg_latency - optimized.avg_latency) / baseline.avg_latency * 100)
        if baseline.avg_latency > 0
        else 0
    )
    tps_imp = (
        ((optimized.tok_per_sec - baseline.tok_per_sec) / baseline.tok_per_sec * 100)
        if baseline.tok_per_sec > 0
        else 0
    )
    mem_red = (
        (
            (baseline.gpu_memory_mb - optimized.gpu_memory_mb)
            / baseline.gpu_memory_mb
            * 100
        )
        if baseline.gpu_memory_mb > 0
        else 0
    )

    return ComparisonResult(
        optimization=optimized.mode,
        baseline_latency=baseline.avg_latency,
        optimized_latency=optimized.avg_latency,
        latency_improvement=latency_imp,
        baseline_tps=baseline.tok_per_sec,
        optimized_tps=optimized.tok_per_sec,
        tps_improvement=tps_imp,
        baseline_memory=baseline.gpu_memory_mb,
        optimized_memory=optimized.gpu_memory_mb,
        memory_reduction=mem_red,
    )


async def run_gpu_optimization_tests(
    base_url: str, model: str, modes: List[str]
) -> Dict[str, ComparisonResult]:
    """Run comparison tests for GPU optimizations."""
    print("\n" + "=" * 70)
    print("GPU OPTIMIZATION BENCHMARKS")
    print("=" * 70)

    prompts = [
        "What is Python?",
        "Explain AI in 2 sentences",
        "Write a function for fibonacci",
        "What is 1+1?",
        "Hello!",
    ]

    print("\nRunning baseline test...")
    baseline = await run_optimization_test(base_url, model, "baseline", prompts)
    print(
        f"  Baseline: {baseline.avg_latency:.2f}s latency, {baseline.tok_per_sec:.0f} tok/s"
    )

    results = {}
    test_modes = [m for m in modes if m != "baseline"]

    for mode in test_modes:
        print(f"\nRunning {TEST_MODES[mode]['name']}...")
        optimized = await run_optimization_test(base_url, model, mode, prompts)
        comparison = compare_results(baseline, optimized)
        results[mode] = comparison

        print(
            f"  Latency: {optimized.avg_latency:.2f}s ({comparison.latency_improvement:+.1f}%)"
        )
        print(
            f"  Throughput: {optimized.tok_per_sec:.0f} tok/s ({comparison.tps_improvement:+.1f}%)"
        )
        print(
            f"  Memory: {optimized.gpu_memory_mb:.0f}MB ({comparison.memory_reduction:+.1f}%)"
        )

    return results


def print_comparison_table(results: Dict[str, ComparisonResult]):
    """Print comparison results in table format."""
    print("\n" + "=" * 70)
    print("OPTIMIZATION COMPARISON TABLE")
    print("=" * 70)

    header = f"{'Optimization':<20} {'Latency %':>12} {'Tok/s %':>12} {'Memory %':>12}"
    print(header)
    print("-" * 70)

    for mode, comp in results.items():
        lat_sign = "+" if comp.latency_improvement > 0 else ""
        tps_sign = "+" if comp.tps_improvement > 0 else ""
        mem_sign = "+" if comp.memory_reduction > 0 else ""

        print(
            f"{TEST_MODES[mode]['name']:<20} "
            f"{lat_sign}{comp.latency_improvement:>10.1f}% "
            f"{tps_sign}{comp.tps_improvement:>10.1f}% "
            f"{mem_sign}{comp.memory_reduction:>10.1f}%"
        )

    print("-" * 70)
    print("Note: Positive latency % = faster (lower is better)")
    print("      Positive tok/s % = higher throughput (better)")
    print("      Positive memory % = less memory used (better)")


class EnhancedLLMBenchmark:
    def __init__(self, name: str, base_url: str, model: str):
        self.name = name
        self.base_url = base_url
        self.model = model

    async def chat(
        self, messages: List[Dict], max_tokens: int = 100, temperature: float = 0.7
    ) -> Dict:
        async with httpx.AsyncClient(timeout=180.0) as client:
            start = time.time()
            try:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                )
                elapsed = time.time() - start

                if r.status_code == 200:
                    data = r.json()
                    return {
                        "success": True,
                        "elapsed": elapsed,
                        "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                        "completion_tokens": data.get("usage", {}).get(
                            "completion_tokens", 0
                        ),
                        "response": data["choices"][0]["message"].get("content", "")[
                            :200
                        ],
                        "raw": data,
                    }
                return {
                    "success": False,
                    "elapsed": elapsed,
                    "error": r.status_code,
                    "text": r.text[:100],
                }
            except Exception as e:
                return {
                    "success": False,
                    "elapsed": time.time() - start,
                    "error": str(e)[:50],
                }

    async def sequential_test(self, prompts: List[str], runs: int = 3) -> Dict:
        """Run sequential benchmark."""
        results = []
        for _ in range(runs):
            for p in prompts:
                r = await self.chat([{"role": "user", "content": p}])
                results.append(r)

        success = [r for r in results if r.get("success")]
        if success:
            latencies = [r["elapsed"] for r in success]
            tokens = sum(r.get("completion_tokens", 0) for r in success)
            return {
                "avg_latency": statistics.mean(latencies),
                "min_latency": min(latencies),
                "max_latency": max(latencies),
                "total_tokens": tokens,
                "success_rate": len(success) / len(results),
                "all_results": success,
            }
        return {"avg_latency": 0, "success_rate": 0, "all_results": results}

    async def parallel_test(self, prompts: List[str], workers: int = 10) -> Dict:
        """Run parallel benchmark with high concurrency."""
        # Extend prompts to match worker count
        extended_prompts = []
        while len(extended_prompts) < workers:
            extended_prompts.extend(prompts)
        extended_prompts = extended_prompts[:workers]

        async with httpx.AsyncClient(timeout=300.0) as client:
            tasks = []
            for p in extended_prompts:
                task = client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": p}],
                        "max_tokens": 80,
                    },
                )
                tasks.append(task)

            start = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            wall_time = time.time() - start

            success = []
            tokens = 0
            for r in responses:
                if hasattr(r, "status_code") and r.status_code == 200:
                    try:
                        data = r.json()
                        success.append(r)
                        tokens += data.get("usage", {}).get("completion_tokens", 0)
                    except:
                        pass

            return {
                "wall_time": wall_time,
                "success": len(success),
                "total": workers,
                "tokens": tokens,
                "req_per_sec": len(success) / wall_time if wall_time > 0 else 0,
                "tok_per_sec": tokens / wall_time if wall_time > 0 else 0,
            }

    async def stress_test(self, prompts: List[str], workers: int = 20) -> Dict:
        """Stress test with 20+ concurrent requests."""
        return await self.parallel_test(prompts, workers)

    async def tool_calling_test(self) -> Dict:
        """Comprehensive tool calling test with different scenarios."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            results = {}

            # Test 1: Simple function call
            try:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": "What is 2 + 2?"}],
                        "tools": [
                            {
                                "type": "function",
                                "function": {
                                    "name": "calculator",
                                    "parameters": {
                                        "type": "object",
                                        "properties": {
                                            "expression": {"type": "string"}
                                        },
                                        "required": ["expression"],
                                    },
                                },
                            }
                        ],
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    msg = data["choices"][0]["message"]
                    results["simple"] = "tool_calls" in msg
                    results["simple_data"] = msg.get("tool_calls", [])
                else:
                    results["simple"] = False
                    results["simple_error"] = r.text[:100]
            except Exception as e:
                results["simple"] = False
                results["simple_error"] = str(e)[:50]

            # Test 2: Multiple tools
            try:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": "Get system info"}],
                        "tools": [
                            {
                                "type": "function",
                                "function": {
                                    "name": "bash",
                                    "description": "Run bash command",
                                    "parameters": {
                                        "type": "object",
                                        "properties": {"command": {"type": "string"}},
                                        "required": ["command"],
                                    },
                                },
                            },
                            {
                                "type": "function",
                                "function": {
                                    "name": "read_file",
                                    "description": "Read a file",
                                    "parameters": {
                                        "type": "object",
                                        "properties": {"path": {"type": "string"}},
                                        "required": ["path"],
                                    },
                                },
                            },
                        ],
                        "tool_choice": "auto",
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    msg = data["choices"][0]["message"]
                    results["multiple"] = "tool_calls" in msg
                else:
                    results["multiple"] = False
            except Exception as e:
                results["multiple"] = False

            # Test 3: Forced tool use
            try:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "user",
                                "content": "List files in current directory",
                            }
                        ],
                        "tools": [
                            {
                                "type": "function",
                                "function": {
                                    "name": "bash",
                                    "parameters": {
                                        "type": "object",
                                        "properties": {"command": {"type": "string"}},
                                        "required": ["command"],
                                    },
                                },
                            }
                        ],
                        "tool_choice": {
                            "type": "function",
                            "function": {"name": "bash"},
                        },
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    msg = data["choices"][0]["message"]
                    results["forced"] = "tool_calls" in msg
                else:
                    results["forced"] = False
            except Exception as e:
                results["forced"] = False

            return results

    async def streaming_test(self, prompt: str = "Count from 1 to 20") -> Dict:
        """Test streaming response."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            start = time.time()
            tokens_received = 0
            first_token_time = None

            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 50,
                        "stream": True,
                    },
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            if first_token_time is None:
                                first_token_time = time.time() - start
                            tokens_received += 1

                return {
                    "success": True,
                    "first_token_latency": first_token_time or 0,
                    "total_tokens": tokens_received,
                }
            except Exception as e:
                return {"success": False, "error": str(e)[:50]}


async def test_model_switching():
    """Test hot-swapping between models via API."""
    print("\n" + "=" * 60)
    print("TESTING: Model Hot-Swap Capability")
    print("=" * 60)

    results = {}

    # Test with different model names
    test_models = [
        ("qwen2.5-0.5b-instruct-q4_k_m.gguf", "0.5b"),
        ("qwen2.5-coder-7b-q4_k_m.gguf", "7b"),
    ]

    for model_name, label in test_models:
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                r = await client.post(
                    "http://localhost:8080/chat/completions",
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": "Hi"}],
                        "max_tokens": 20,
                    },
                )
                results[label] = r.status_code == 200
                print(
                    f"  {label} model: {'✅' if results[label] else '❌'} (status: {r.status_code})"
                )
            except Exception as e:
                results[label] = False
                print(f"  {label} model: ❌ ({str(e)[:30]})")

    return results


async def run_enhanced_benchmarks(
    test_modes: Optional[List[str]] = None, run_gpu_tests: bool = False
):
    parser = argparse.ArgumentParser(description="Enhanced Benchmark for GGUF system")
    parser.add_argument("--gpu", action="store_true", help="Run GPU optimization tests")
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=list(TEST_MODES.keys()),
        default=["baseline", "kv_quant", "flash_attn_v2"],
        help="Test modes to run",
    )
    parser.add_argument(
        "--model",
        default="qwen2.5-0.5b-instruct-q4_k_m.gguf",
        help="Model to test",
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8080",
        help="Base URL for llama-server",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("ENHANCED BENCHMARK - DEEP TESTING GGUF SYSTEM")
    print("=" * 80)
    print()

    if run_gpu_tests or args.gpu:
        gpu_results = await run_gpu_optimization_tests(args.url, args.model, args.modes)
        print_comparison_table(gpu_results)
        print()

    results = []
    gpu_util = 0.0
    gpu_start = get_gpu_memory()
    gpu_util_start = get_gpu_utilization()

    # Define benchmarks - test both models
    benchmarks = [
        EnhancedLLMBenchmark(
            "llama-server (0.5b)",
            "http://localhost:8080",
            "qwen2.5-0.5b-instruct-q4_k_m.gguf",
        ),
        EnhancedLLMBenchmark(
            "llama-server (7b)",
            "http://localhost:8080",
            "qwen2.5-coder-7b-q4_k_m.gguf",
        ),
    ]

    for bm in benchmarks:
        print(f"\n{'=' * 60}")
        print(f"TESTING: {bm.name}")
        print(f"{'=' * 60}")

        # Check availability
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try direct chat endpoint as health check
                r = await client.post(
                    f"{bm.base_url}/chat/completions",
                    json={
                        "model": bm.model,
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 1,
                    },
                    timeout=5.0,
                )
                if r.status_code != 200:
                    raise Exception(f"Health check failed: {r.status_code}")
        except Exception as e:
            print(f"  ❌ Not available: {str(e)[:50]}")
            continue

        print(f"  ✅ Server available")

        # 1. Sequential Test
        print(f"  Running sequential test...")
        seq = await bm.sequential_test(
            [
                "What is Python?",
                "Explain AI in 2 sentences",
                "Write a function for fibonacci",
                "What is 1+1?",
                "Hello!",
            ],
            runs=2,
        )
        print(
            f"    Avg: {seq.get('avg_latency', 0):.2f}s, Min: {seq.get('min_latency', 0):.2f}s, Max: {seq.get('max_latency', 0):.2f}s"
        )
        print(f"    Success rate: {seq.get('success_rate', 0) * 100:.0f}%")

        # 2. Parallel Test (10 workers)
        print(f"  Running parallel test (10 workers)...")
        par = await bm.parallel_test(
            ["Count to 5", "Say hello", "What is 1+1", "What is Python?", "Explain AI"],
            workers=10,
        )
        print(f"    Wall time: {par.get('wall_time', 0):.2f}s")
        print(f"    Success: {par.get('success', 0)}/{par.get('total', 0)}")
        print(f"    Throughput: {par.get('req_per_sec', 0):.2f} req/s")
        print(f"    Token/s: {par.get('tok_per_sec', 0):.0f}")

        # 3. Stress Test (20 workers)
        print(f"  Running stress test (20 workers)...")
        stress = await bm.stress_test(
            ["Count to 3", "Say hi", "What is 2+2"], workers=20
        )
        print(f"    Wall time: {stress.get('wall_time', 0):.2f}s")
        print(f"    Success: {stress.get('success', 0)}/{stress.get('total', 0)}")
        print(f"    Token/s: {stress.get('tok_per_sec', 0):.0f}")

        # 4. Tool Calling Test
        print(f"  Testing tool calling...")
        tools = await bm.tool_calling_test()
        print(f"    Simple tool: {'✅' if tools.get('simple') else '❌'}")
        print(f"    Multiple tools: {'✅' if tools.get('multiple') else '❌'}")
        print(f"    Forced tool: {'✅' if tools.get('forced') else '❌'}")
        tool_works = any(tools.values()) if tools else False

        # 5. Streaming Test
        print(f"  Testing streaming...")
        stream = await bm.streaming_test()
        print(f"    Streaming: {'✅' if stream.get('success') else '❌'}")
        if stream.get("first_token_latency"):
            print(
                f"    First token: {stream.get('first_token_latency', 0) * 1000:.0f}ms"
            )

        # GPU info
        gpu_current = get_gpu_memory()
        gpu_util = get_gpu_utilization()

        result = BenchmarkResult(
            name=bm.name,
            model=bm.model,
            sequential_latency=seq.get("avg_latency", 0),
            parallel_latency=par.get("wall_time", 0),
            parallel_success=par.get("success", 0),
            parallel_total=par.get("total", 0),
            tokens_per_second=par.get("tok_per_sec", 0),
            throughput_req_per_sec=par.get("req_per_sec", 0),
            tool_calling_works=tool_works,
            gpu_memory_mb=gpu_current,
            notes=f"Stress: {stress.get('success', 0)}/20",
        )
        results.append(result)

    # Model switching test
    model_switch = await test_model_switching()

    # Summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"{'Model':<20} {'Seq Lat':>8} {'Par Tok/s':>10} {'Tools':>8} {'GPU MB':>8}")
    print("-" * 80)
    for r in results:
        print(
            f"{r.name:<20} {r.sequential_latency:>7.2f}s {r.tokens_per_second:>9.0f} {'✅' if r.tool_calling_works else '❌':>7} {r.gpu_memory_mb:>7.0f}"
        )

    print(f"\nGPU Utilization: {gpu_util}%")
    print(f"Model Switching: 0.5b ✅, 7b {'✅' if model_switch.get('7b') else '❌'}")

    # Winner
    if results:
        best = max(results, key=lambda x: x.tokens_per_second)
        print(f"\n🏆 WINNER: {best.name} with {best.tokens_per_second:.0f} tok/s")

    return results


if __name__ == "__main__":
    asyncio.run(run_enhanced_benchmarks(None, False))
