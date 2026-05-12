#!/usr/bin/env python3
"""
DEEP AUDIT BENCHMARK - Real-time GPU monitoring + bottleneck analysis
"""

import httpx
import asyncio
import time
import subprocess
import threading
from typing import List, Dict

# Metrics collection
gpu_metrics = {
    "samples": [],
    "max_gpu": 0,
    "max_mem": 0,
    "avg_gpu": 0,
}

monitoring = True


def monitor_gpu():
    """Background GPU monitoring."""
    global monitoring, gpu_metrics
    while monitoring:
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,utilization.memory,memory.used,power.draw",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=2,
            )
            parts = result.stdout.strip().split(", ")
            gpu_util = float(parts[0])
            mem_util = float(parts[1])
            mem_used = float(parts[2])
            power = float(parts[3])

            gpu_metrics["samples"].append(
                {
                    "gpu": gpu_util,
                    "mem": mem_util,
                    "mem_mb": mem_used,
                    "power": power,
                    "time": time.time(),
                }
            )
            gpu_metrics["max_gpu"] = max(gpu_metrics["max_gpu"], gpu_util)
            gpu_metrics["max_mem"] = max(gpu_metrics["max_mem"], mem_util)
        except Exception as e:
            pass
        time.sleep(0.1)


def get_gpu_stats() -> Dict:
    """Get GPU statistics."""
    samples = gpu_metrics["samples"]
    if not samples:
        return {"gpu": 0, "mem": 0, "power": 0}

    return {
        "max_gpu": gpu_metrics["max_gpu"],
        "max_mem": gpu_metrics["max_mem"],
        "avg_gpu": sum(s["gpu"] for s in samples) / len(samples),
        "avg_power": sum(s["power"] for s in samples) / len(samples),
        "samples": len(samples),
    }


class DeepBenchmark:
    def __init__(self, name: str, url: str, model: str):
        self.name = name
        self.url = url
        self.model = model

    async def chat(self, prompt: str, max_tokens: int = 80) -> Dict:
        async with httpx.AsyncClient(timeout=120.0) as client:
            start = time.time()
            try:
                r = await client.post(
                    f"{self.url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
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
                    }
                return {"success": False, "error": r.status_code}
            except Exception as e:
                return {"success": False, "error": str(e)[:30]}

    async def parallel_burst(self, prompts: List[str], workers: int = 50) -> Dict:
        """Max burst test - 50+ concurrent requests."""
        global gpu_metrics
        gpu_metrics["samples"] = []
        gpu_metrics["max_gpu"] = 0

        async with httpx.AsyncClient(timeout=180.0) as client:
            tasks = []
            for p in prompts * (workers // len(prompts) + 1):
                tasks.append(
                    client.post(
                        f"{self.url}/chat/completions",
                        json={
                            "model": self.model,
                            "messages": [{"role": "user", "content": p}],
                            "max_tokens": 100,
                        },
                    )
                )

            start = time.time()
            responses = await asyncio.gather(*tasks[:workers], return_exceptions=True)
            wall = time.time() - start

            success = [
                r
                for r in responses
                if hasattr(r, "status_code") and r.status_code == 200
            ]
            tokens = sum(
                r.json().get("usage", {}).get("completion_tokens", 0)
                for r in success
                if r.status_code == 200
            )

            return {
                "wall": wall,
                "success": len(success),
                "total": workers,
                "tokens": tokens,
                "tok_per_sec": tokens / wall if wall > 0 else 0,
                "req_per_sec": len(success) / wall if wall > 0 else 0,
            }

    async def sustained_load(self, duration: int = 10) -> Dict:
        """Sustained load test - continuous requests."""
        global gpu_metrics
        gpu_metrics["samples"] = []
        gpu_metrics["max_gpu"] = 0

        async with httpx.AsyncClient(timeout=300.0) as client:
            start = time.time()
            requests_made = 0
            responses = []

            while time.time() - start < duration:
                task = client.post(
                    f"{self.url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": "Count to 20"}],
                        "max_tokens": 80,
                    },
                )
                responses.append(task)
                requests_made += 1

                if len(responses) >= 10:
                    batch = await asyncio.gather(*responses, return_exceptions=True)
                    responses = []

            if responses:
                await asyncio.gather(*responses, return_exceptions=True)

            wall = time.time() - start
            gpu_stats = get_gpu_stats()

            return {
                "duration": wall,
                "requests": requests_made,
                "req_per_sec": requests_made / wall,
                "gpu_stats": gpu_stats,
            }


async def deep_audit():
    print("=" * 80)
    print("🔍 DEEP AUDIT - REAL BENCHMARKS WITH GPU MONITORING")
    print("=" * 80)

    # Start GPU monitor
    monitor_thread = threading.Thread(target=monitor_gpu, daemon=True)
    monitor_thread.start()

    bm = DeepBenchmark(
        "llama-server", "http://localhost:8080", "qwen2.5-0.5b-instruct-q4_k_m.gguf"
    )

    # Test 1: Single request latency
    print("\n📊 TEST 1: Single Request Latency")
    print("-" * 40)
    latencies = []
    for i in range(5):
        r = await bm.chat("Explain what AI is in one sentence")
        if r["success"]:
            latencies.append(r["elapsed"])
    print(f"  Latencies: {latencies}")
    print(f"  Avg: {sum(latencies) / len(latencies) * 1000:.1f}ms")

    # Test 2: Small burst (10 concurrent)
    print("\n📊 TEST 2: Small Burst (10 concurrent)")
    print("-" * 40)
    gpu_metrics["samples"] = []
    result = await bm.parallel_burst(["Hi", "Hello", "Count to 5"], workers=10)
    gpu = get_gpu_stats()
    print(f"  Wall time: {result['wall']:.2f}s")
    print(f"  Success: {result['success']}/{result['total']}")
    print(f"  Throughput: {result['req_per_sec']:.1f} req/s")
    print(f"  Token/s: {result['tok_per_sec']:.0f}")
    print(f"  GPU max: {gpu['max_gpu']:.0f}%, avg: {gpu['avg_gpu']:.0f}%")

    # Test 3: Medium burst (25 concurrent)
    print("\n📊 TEST 3: Medium Burst (25 concurrent)")
    print("-" * 40)
    gpu_metrics["samples"] = []
    result = await bm.parallel_burst(
        ["Hi", "Hello", "Count to 5", "What is 1+1"], workers=25
    )
    gpu = get_gpu_stats()
    print(f"  Wall time: {result['wall']:.2f}s")
    print(f"  Success: {result['success']}/{result['total']}")
    print(f"  Throughput: {result['req_per_sec']:.1f} req/s")
    print(f"  Token/s: {result['tok_per_sec']:.0f}")
    print(f"  GPU max: {gpu['max_gpu']:.0f}%, avg: {gpu['avg_gpu']:.0f}%")

    # Test 4: MAXIMUM BURST (50 concurrent)
    print("\n📊 TEST 4: MAXIMUM BURST (50 concurrent)")
    print("-" * 40)
    gpu_metrics["samples"] = []
    result = await bm.parallel_burst(
        [
            "Count to 10",
            "Say hello",
            "What is AI?",
            "Explain Python",
            "Write fibonacci",
            "What is 1+1?",
            "Hello!",
            "Hi there",
            "How are you?",
            "Tell me a joke",
        ],
        workers=50,
    )
    gpu = get_gpu_stats()
    print(f"  Wall time: {result['wall']:.2f}s")
    print(f"  Success: {result['success']}/{result['total']}")
    print(f"  Throughput: {result['req_per_sec']:.1f} req/s")
    print(f"  Token/s: {result['tok_per_sec']:.0f}")
    print(f"  GPU max: {gpu['max_gpu']:.0f}%, avg: {gpu['avg_gpu']:.0f}%")
    print(f"  Power avg: {gpu.get('avg_power', 0):.1f}W")

    # Test 5: Sustained load
    print("\n📊 TEST 5: Sustained Load (10 seconds)")
    print("-" * 40)
    result = await bm.sustained_load(duration=10)
    gpu = get_gpu_stats()
    print(f"  Duration: {result['duration']:.1f}s")
    print(f"  Requests: {result['requests']}")
    print(f"  Throughput: {result['req_per_sec']:.1f} req/s")
    print(f"  GPU max: {gpu['max_gpu']:.0f}%")
    print(f"  GPU avg: {gpu['avg_gpu']:.0f}%")

    # Bottleneck analysis
    print("\n" + "=" * 80)
    print("🔬 BOTTLENECK ANALYSIS")
    print("=" * 80)

    # Get nvidia-smi info
    result = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True)
    gpu_name = result.stdout.strip()

    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
    )
    vram = result.stdout.strip() + " MiB"

    print(f"\n🎮 GPU: {gpu_name}")
    print(f"   VRAM: {vram}")

    print(f"\n📈 Current Utilization:")
    print(f"   GPU: {gpu['max_gpu']:.0f}% max, {gpu['avg_gpu']:.0f}% avg")
    print(f"   Memory: {gpu['max_mem']:.0f}%")

    # Theoretical max calculation
    print(f"\n💡 OPTIMIZATION OPPORTUNITIES:")
    if gpu["max_gpu"] < 80:
        print(f"   ⚠️  GPU only at {gpu['max_gpu']:.0f}% - UNDERUTILIZED")
        print(f"   → Could increase batch size or parallel slots")
    if gpu["max_mem"] < 90:
        print(f"   ⚠️  Memory bandwidth not saturated ({gpu['max_mem']:.0f}%)")
        print(f"   → Could use larger context or more layers")

    global monitoring
    monitoring = False

    return gpu


if __name__ == "__main__":
    asyncio.run(deep_audit())
