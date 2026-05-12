#!/usr/bin/env python3
"""
COMPREHENSIVE BENCHMARK - Compare ALL LLM Providers

Tests:
1. Native llama-server (port 8080) - NEW SOLUTION
2. llama-cpp-python server (port 8081) - OLD SOLUTION
3. Ollama (port 11434)
4. Cloud (OpenCode/OpenRouter)

Metrics:
- Sequential latency
- Parallel throughput
- Token generation speed
- Resource usage (GPU/CPU)
"""

import httpx
import asyncio
import time
import statistics
import os
import subprocess
import json
import threading
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class GPUStats:
    gpu_util: float = 0
    gpu_util_min: float = 0
    gpu_util_max: float = 0
    gpu_util_avg: float = 0
    memory_mb: float = 0
    memory_mb_min: float = 0
    memory_mb_max: float = 0
    memory_mb_avg: float = 0
    power_watts: float = 0
    power_watts_min: float = 0
    power_watts_max: float = 0
    power_watts_avg: float = 0
    temperature_c: float = 0
    temperature_c_min: float = 0
    temperature_c_max: float = 0
    temperature_c_avg: float = 0
    samples: int = 0


@dataclass
class BenchmarkResult:
    name: str
    sequential_latency: float
    parallel_latency: float
    parallel_success: int
    parallel_total: int
    tokens_per_second: float
    throughput_req_per_sec: float
    tool_calling_works: bool
    gpu_memory_mb: float
    gpu_stats: GPUStats = field(default_factory=GPUStats)
    notes: str


# GPU monitoring state
_monitoring_active = False
_monitoring_thread = None
_gpu_samples = []


def _gpu_monitor_loop():
    """Background thread that samples GPU every 1 second."""
    global _gpu_samples, _monitoring_active
    while _monitoring_active:
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,memory.used,power.draw,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=2,
            )
            parts = result.stdout.strip().split(", ")
            if len(parts) >= 4:
                _gpu_samples.append(
                    {
                        "gpu_util": float(parts[0]),
                        "memory_mb": float(parts[1]),
                        "power_watts": float(parts[2]),
                        "temperature_c": float(parts[3]),
                        "time": time.time(),
                    }
                )
        except Exception:
            pass
        time.sleep(1.0)


def start_gpu_monitoring():
    """Start background GPU monitoring."""
    global _monitoring_active, _monitoring_thread, _gpu_samples
    _gpu_samples = []
    _monitoring_active = True
    _monitoring_thread = threading.Thread(target=_gpu_monitor_loop, daemon=True)
    _monitoring_thread.start()


def stop_gpu_monitoring() -> GPUStats:
    """Stop monitoring and return aggregated stats."""
    global _monitoring_active, _monitoring_thread, _gpu_samples
    _monitoring_active = False
    if _monitoring_thread:
        _monitoring_thread.join(timeout=2)

    if not _gpu_samples:
        return GPUStats()

    gpu_utils = [s["gpu_util"] for s in _gpu_samples]
    mem_mbs = [s["memory_mb"] for s in _gpu_samples]
    powers = [s["power_watts"] for s in _gpu_samples]
    temps = [s["temperature_c"] for s in _gpu_samples]

    return GPUStats(
        gpu_util=max(gpu_utils),
        gpu_util_min=min(gpu_utils),
        gpu_util_max=max(gpu_utils),
        gpu_util_avg=statistics.mean(gpu_utils),
        memory_mb=max(mem_mbs),
        memory_mb_min=min(mem_mbs),
        memory_mb_max=max(mem_mbs),
        memory_mb_avg=statistics.mean(mem_mbs),
        power_watts=max(powers),
        power_watts_min=min(powers),
        power_watts_max=max(powers),
        power_watts_avg=statistics.mean(powers),
        temperature_c=max(temps),
        temperature_c_min=min(temps),
        temperature_c_max=max(temps),
        temperature_c_avg=statistics.mean(temps),
        samples=len(_gpu_samples),
    )


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


class LLMBenchmark:
    def __init__(self, name: str, base_url: str, model: str):
        self.name = name
        self.base_url = base_url
        self.model = model

    async def chat(self, messages: List[Dict], max_tokens: int = 100) -> Dict:
        async with httpx.AsyncClient(timeout=120.0) as client:
            start = time.time()
            try:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": max_tokens,
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
                            :100
                        ],
                    }
                return {"success": False, "elapsed": elapsed, "error": r.status_code}
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
            }
        return {"avg_latency": 0, "success_rate": 0}

    async def parallel_test(self, prompts: List[str], workers: int = 6) -> Dict:
        """Run parallel benchmark."""
        # Extend prompts to match worker count
        extended_prompts = []
        while len(extended_prompts) < workers:
            extended_prompts.extend(prompts)
        extended_prompts = extended_prompts[:workers]

        async with httpx.AsyncClient(timeout=180.0) as client:
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

            success = [
                r
                for r in responses
                if hasattr(r, "status_code") and r.status_code == 200
            ]
            tokens = 0
            if success:
                for r in success:
                    try:
                        tokens += r.json().get("usage", {}).get("completion_tokens", 0)
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

    async def tool_calling_test(self) -> bool:
        """Test if tool calling works."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                # Get available models first to find the right one
                try:
                    r_models = await client.get(f"{self.base_url}/models")
                    if r_models.status_code == 200:
                        models = r_models.json().get("data", [])
                        model_id = models[0]["id"] if models else self.model
                    else:
                        model_id = self.model
                except:
                    model_id = self.model

                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": model_id,
                        "messages": [
                            {"role": "user", "content": "Use bash to list files"}
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
                        "tool_choice": "auto",
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    return "tool_calls" in data["choices"][0]["message"]
            except:
                pass
        return False


async def run_all_benchmarks():
    print("=" * 80)
    print("COMPREHENSIVE LLM BENCHMARK - ALL PROVIDERS")
    print("=" * 80)
    print()

    # Define benchmarks
    benchmarks = [
        # Local servers - use exact model IDs
        LLMBenchmark(
            "Native llama-server (8080)",
            "http://localhost:8080/v1",
            "qwen2.5-0.5b-instruct-q4_k_m.gguf",
        ),
        LLMBenchmark(
            "llama-cpp-python (8081)",
            "http://localhost:8081/v1",
            "qwen2.5-0.5b-instruct-q4_k_m",
        ),
        LLMBenchmark("Ollama (11434)", "http://localhost:11434/v1", "qwen2.5-coder:7b"),
        # Cloud (we'll test with fallback)
    ]

    results = []

    for bm in benchmarks:
        print(f"\n{'=' * 60}")
        print(f"TESTING: {bm.name}")
        print(f"{'=' * 60}")

        # Check if available
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

        # Start GPU monitoring for this benchmark
        start_gpu_monitoring()

        # Get GPU before
        gpu_before = get_gpu_memory()

        # Sequential test
        print(f"  Running sequential test...")
        seq = await bm.sequential_test(
            [
                "What is Python?",
                "Explain AI in 2 sentences",
                "Write a function for fibonacci",
            ],
            runs=2,
        )
        print(f"    Avg latency: {seq.get('avg_latency', 0):.2f}s")

        # Parallel test
        print(f"  Running parallel test (6 workers)...")
        par = await bm.parallel_test(
            ["Count to 5", "Say hello", "What is 1+1"], workers=6
        )
        print(f"    Wall time: {par.get('wall_time', 0):.2f}s")
        print(f"    Success: {par.get('success', 0)}/{par.get('total', 0)}")
        print(f"    Throughput: {par.get('req_per_sec', 0):.2f} req/s")
        print(f"    Token/s: {par.get('tok_per_sec', 0):.0f}")

        # Tool calling
        print(f"  Testing tool calling...")
        tools = await bm.tool_calling_test()
        print(f"    Tool calls: {'✅ YES' if tools else '❌ NO'}")

        # Stop GPU monitoring and get stats
        gpu_stats = stop_gpu_monitoring()

        # GPU after
        gpu_after = get_gpu_memory()

        print(f"  GPU Stats:")
        print(
            f"    Util: {gpu_stats.gpu_util_min:.0f}-{gpu_stats.gpu_util_max:.0f}% (avg {gpu_stats.gpu_util_avg:.0f}%)"
        )
        print(
            f"    Memory: {gpu_stats.memory_mb_min:.0f}-{gpu_stats.memory_mb_max:.0f}MB (avg {gpu_stats.memory_mb_avg:.0f}MB)"
        )
        print(
            f"    Power: {gpu_stats.power_watts_min:.0f}-{gpu_stats.power_watts_max:.0f}W (avg {gpu_stats.power_watts_avg:.1f}W)"
        )
        print(
            f"    Temp: {gpu_stats.temperature_c_min:.0f}-{gpu_stats.temperature_c_max:.0f}C (avg {gpu_stats.temperature_c_avg:.0f}C)"
        )
        print(f"    Samples: {gpu_stats.samples}")

        result = BenchmarkResult(
            name=bm.name,
            sequential_latency=seq.get("avg_latency", 0),
            parallel_latency=par.get("wall_time", 0),
            parallel_success=par.get("success", 0),
            parallel_total=par.get("total", 0),
            tokens_per_second=par.get("tok_per_sec", 0),
            throughput_req_per_sec=par.get("req_per_sec", 0),
            tool_calling_works=tools,
            gpu_memory_mb=gpu_after,
            gpu_stats=gpu_stats,
            notes="",
        )
        results.append(result)

    # Print summary table
    print("\n" + "=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)
    print(
        f"{'Provider':<30} {'Seq Latency':>12} {'Parallel':>10} {'Success':>8} {'Tok/s':>8} {'Tools':>8} {'GPU %':>8} {'GPU Mem':>10}"
    )
    print("-" * 80)
    for r in results:
        print(
            f"{r.name:<30} {r.sequential_latency:>11.2f}s {r.parallel_latency:>9.2f}s {r.parallel_success:>7}/{r.parallel_total:<1} {r.tokens_per_second:>7.0f} {'✅' if r.tool_calling_works else '❌':>7} {r.gpu_stats.gpu_util_max:>7.0f} {r.gpu_stats.memory_mb_max:>9.0f}"
        )

    # GPU metrics detail
    print("\n" + "=" * 80)
    print("GPU METRICS DETAIL")
    print("=" * 80)
    print(
        f"{'Provider':<30} {'GPU Util %':>12} {'Mem MB':>10} {'Power W':>10} {'Temp C':>10} {'Samples':>8}"
    )
    print("-" * 80)
    for r in results:
        print(
            f"{r.name:<30} {r.gpu_stats.gpu_util_avg:>11.1f}% {r.gpu_stats.memory_mb_avg:>9.0f} {r.gpu_stats.power_watts_avg:>9.1f} {r.gpu_stats.temperature_c_avg:>9.0f} {r.gpu_stats.samples:>8}"
        )

    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)

    # Find best parallel
    if results:
        best_parallel = max(results, key=lambda x: x.tokens_per_second)
        best_sequential = min(
            results,
            key=lambda x: x.sequential_latency if x.sequential_latency > 0 else 999,
        )
        best_tools = [r for r in results if r.tool_calling_works]

        print(
            f"  Best parallel throughput: {best_parallel.name} ({best_parallel.tokens_per_second:.0f} tok/s)"
        )
        print(
            f"  Best sequential latency: {best_sequential.name} ({best_sequential.sequential_latency:.2f}s)"
        )
        if best_tools:
            print(f"  Tool calling works: {', '.join([r.name for r in best_tools])}")

    # JSON output
    print("\n" + "=" * 80)
    print("JSON OUTPUT")
    print("=" * 80)
    output = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": [
            {
                "name": r.name,
                "sequential_latency": r.sequential_latency,
                "parallel_latency": r.parallel_latency,
                "parallel_success": r.parallel_success,
                "parallel_total": r.parallel_total,
                "tokens_per_second": r.tokens_per_second,
                "throughput_req_per_sec": r.throughput_req_per_sec,
                "tool_calling_works": r.tool_calling_works,
                "gpu_memory_mb": r.gpu_memory_mb,
                "gpu_stats": {
                    "gpu_util_min": r.gpu_stats.gpu_util_min,
                    "gpu_util_max": r.gpu_stats.gpu_util_max,
                    "gpu_util_avg": r.gpu_stats.gpu_util_avg,
                    "memory_mb_min": r.gpu_stats.memory_mb_min,
                    "memory_mb_max": r.gpu_stats.memory_mb_max,
                    "memory_mb_avg": r.gpu_stats.memory_mb_avg,
                    "power_watts_min": r.gpu_stats.power_watts_min,
                    "power_watts_max": r.gpu_stats.power_watts_max,
                    "power_watts_avg": r.gpu_stats.power_watts_avg,
                    "temperature_c_min": r.gpu_stats.temperature_c_min,
                    "temperature_c_max": r.gpu_stats.temperature_c_max,
                    "temperature_c_avg": r.gpu_stats.temperature_c_avg,
                    "samples": r.gpu_stats.samples,
                },
                "notes": r.notes,
            }
            for r in results
        ],
    }
    print(json.dumps(output, indent=2))

    return results


if __name__ == "__main__":
    asyncio.run(run_all_benchmarks())
