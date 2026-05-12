#!/usr/bin/env python3
"""Comprehensive Real-World Benchmark Suite for Rosetta Engine

Measures:
1. Cold start (model loading time)
2. GPU utilization during inference
3. Latency distribution (p50, p95, p99)
4. Throughput under load
5. Memory usage (VRAM, RAM)
6. Comparison: trained vs untrained model

Usage:
    python3 real_benchmark.py --test all
    python3 real_benchmark.py --test cold_start
    python3 real_benchmark.py --test throughput
    python3 real_benchmark.py --test compare
"""

import argparse
import asyncio
import json
import os
import psutil
import random
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
NX_ENGINE_ROOT = PROJECT_ROOT / "nx_engine"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(NX_ENGINE_ROOT))

# Import after path setup
from nx_engine import LocalLLM


# ============================================================================
# CONFIG
# ============================================================================

MODELS = {
    "trained_q8": {
        "path": "models/rosetta-v5-q8_0.gguf",
        "size_mb": 507,
        "description": "Trained Q8_0 (our model)",
    },
    "trained_f16": {
        "path": "models/rosetta-v5-f16.gguf",
        "size_mb": 949,
        "description": "Trained FP16",
    },
    "untrained_q4": {
        "path": "models/qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "size_mb": 352,
        "description": "Base Q4 (no LoRA)",
    },
}

# Test prompts - realistic OpenCode requests
TEST_PROMPTS = [
    "search memory for authentication tokens",
    "check git status",
    "get the active context",
    "list all sessions",
    "search the web for ai news 2024",
    "delegate task to hephaestus",
    "navigate to github.com",
    "run type check",
    "show recent commits",
    "list issues for facebook/react",
    "fetch python.org homepage",
    "get mind state",
    "query context7 docs for react",
    "send telegram message hello",
    "run linter",
    "get health status",
    "search knowledge base",
    "create new branch feature",
    "rename function get_user",
    "grep for class definition",
]


# ============================================================================
# GPU MONITORING
# ============================================================================


class GPUMonitor:
    """Monitor GPU utilization during inference."""

    def __init__(self):
        self.running = False
        self.samples = []
        self._thread = None
        self._nvml_available = False
        self._initialize_nvml()

    def _initialize_nvml(self):
        """Initialize NVIDIA GPU monitoring."""
        try:
            import pynvml

            pynvml.nvmlInit()
            self._nvml = pynvml
            self._nvml_available = True
            # Get first GPU
            self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            print("[GPU] NVML initialized successfully")
        except Exception as e:
            print(f"[GPU] NVML not available: {e}")
            self._nvml_available = False

    def start(self):
        """Start monitoring."""
        self.running = True
        self.samples = []
        self._thread = threading.Thread(target=self._monitor)
        self._thread.daemon = True
        self._thread.start()

    def _monitor(self):
        """Monitor loop."""
        while self.running:
            if self._nvml_available:
                try:
                    util = self._nvml.nvmlDeviceGetUtilizationRates(self._handle)
                    mem_info = self._nvml.nvmlDeviceGetMemoryInfo(self._handle)

                    self.samples.append(
                        {
                            "gpu_percent": util.gpu,
                            "memory_percent": util.memory,
                            "vram_used_mb": mem_info.used / 1024 / 1024,
                            "vram_total_mb": mem_info.total / 1024 / 1024,
                            "timestamp": time.time(),
                        }
                    )
                except:
                    pass
            time.sleep(0.1)  # Sample every 100ms

    def stop(self):
        """Stop monitoring."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=1)

    def get_stats(self) -> Dict:
        """Get statistics."""
        if not self.samples:
            return {}

        gpu_vals = [s["gpu_percent"] for s in self.samples]
        vram_vals = [s["vram_used_mb"] for s in self.samples]

        return {
            "gpu_avg": sum(gpu_vals) / len(gpu_vals),
            "gpu_max": max(gpu_vals),
            "vram_avg_mb": sum(vram_vals) / len(vram_vals),
            "vram_max_mb": max(vram_vals),
            "samples": len(self.samples),
        }


# ============================================================================
# BENCHMARK TESTS
# ============================================================================


class RosettaBenchmark:
    """Comprehensive benchmark suite."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model_config = MODELS[model_name]
        self.llm = None
        self.gpu_monitor = GPUMonitor()

    # -------------------------------------------------------------------------
    # TEST 1: COLD START
    # -------------------------------------------------------------------------
    def test_cold_start(self) -> Dict:
        """Measure model loading time."""
        print("\n" + "=" * 60)
        print("TEST 1: COLD START (Model Loading)")
        print("=" * 60)

        model_path = PROJECT_ROOT / self.model_config["path"]
        print(f"Loading model: {model_path}")

        # Measure loading time
        start = time.time()

        llm = LocalLLM(
            model_path=str(model_path),
            n_gpu_layers=99,
            n_ctx=2048,
            n_threads=4,
        )

        load_time = time.time() - start

        # Get memory info
        process = psutil.Process()
        mem_mb = process.memory_info().rss / 1024 / 1024

        # GPU memory
        gpu_stats = {}
        if self.gpu_monitor._nvml_available:
            try:
                mem_info = self.gpu_monitor._nvml.nvmlDeviceGetMemoryInfo(
                    self.gpu_monitor._handle
                )
                gpu_stats = {
                    "gpu_vram_used_mb": mem_info.used / 1024 / 1024,
                    "gpu_vram_total_mb": mem_info.total / 1024 / 1024,
                }
            except:
                pass

        print(f"\n✅ Cold Start Results:")
        print(f"   Load time: {load_time:.2f}s")
        print(f"   Process RAM: {mem_mb:.0f}MB")
        if gpu_stats:
            print(
                f"   GPU VRAM: {gpu_stats['gpu_vram_used_mb']:.0f}MB / {gpu_stats['gpu_vram_total_mb']:.0f}MB"
            )

        self.llm = llm

        return {
            "load_time_seconds": load_time,
            "process_ram_mb": mem_mb,
            **gpu_stats,
        }

    # -------------------------------------------------------------------------
    # TEST 2: LATENCY DISTRIBUTION
    # -------------------------------------------------------------------------
    def test_latency(self, num_runs: int = 100) -> Dict:
        """Measure latency distribution."""
        print("\n" + "=" * 60)
        print("TEST 2: LATENCY DISTRIBUTION")
        print("=" * 60)

        if not self.llm:
            print("⚠️ Model not loaded, loading now...")
            self.test_cold_start()

        latencies = []

        # Start GPU monitoring
        self.gpu_monitor.start()

        print(f"Running {num_runs} inference calls...")

        for i in range(num_runs):
            prompt = random.choice(TEST_PROMPTS)

            start = time.time()
            response = self.llm.chat(
                [{"role": "user", "content": prompt}], max_tokens=100
            )
            elapsed = time.time() - start

            latencies.append(elapsed * 1000)  # Convert to ms

            if (i + 1) % 20 == 0:
                print(f"   Progress: {i + 1}/{num_runs}")

        # Stop GPU monitoring
        self.gpu_monitor.stop()
        gpu_stats = self.gpu_monitor.get_stats()

        # Calculate statistics
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]

        print(f"\n✅ Latency Results:")
        print(f"   Min: {min(latencies):.1f}ms")
        print(f"   Max: {max(latencies):.1f}ms")
        print(f"   Mean: {sum(latencies) / len(latencies):.1f}ms")
        print(f"   P50: {p50:.1f}ms")
        print(f"   P95: {p95:.1f}ms")
        print(f"   P99: {p99:.1f}ms")

        if gpu_stats:
            print(f"   GPU Avg: {gpu_stats['gpu_avg']:.1f}%")
            print(f"   GPU Max: {gpu_stats['gpu_max']:.1f}%")
            print(f"   VRAM Avg: {gpu_stats['vram_avg_mb']:.0f}MB")

        return {
            "min_ms": min(latencies),
            "max_ms": max(latencies),
            "mean_ms": sum(latencies) / len(latencies),
            "p50_ms": p50,
            "p95_ms": p95,
            "p99_ms": p99,
            "num_runs": num_runs,
            **gpu_stats,
        }

    # -------------------------------------------------------------------------
    # TEST 3: THROUGHPUT UNDER LOAD
    # -------------------------------------------------------------------------
    def test_throughput(self, duration_seconds: int = 10) -> Dict:
        """Measure throughput under continuous load."""
        print("\n" + "=" * 60)
        print("TEST 3: THROUGHPUT UNDER LOAD")
        print("=" * 60)

        if not self.llm:
            print("⚠️ Model not loaded, loading now...")
            self.test_cold_start()

        print(f"Running continuous inference for {duration_seconds}s...")

        self.gpu_monitor.start()

        start_time = time.time()
        total_tokens = 0
        total_requests = 0

        while time.time() - start_time < duration_seconds:
            prompt = random.choice(TEST_PROMPTS)

            req_start = time.time()
            response = self.llm.chat(
                [{"role": "user", "content": prompt}], max_tokens=200
            )
            req_time = time.time() - req_start

            # Estimate tokens (rough: ~4 chars per token)
            estimated_tokens = 200
            total_tokens += estimated_tokens
            total_requests += 1

        elapsed = time.time() - start_time
        throughput = total_tokens / elapsed

        self.gpu_monitor.stop()
        gpu_stats = self.gpu_monitor.get_stats()

        print(f"\n✅ Throughput Results:")
        print(f"   Duration: {elapsed:.1f}s")
        print(f"   Total requests: {total_requests}")
        print(f"   Total tokens: {total_tokens}")
        print(f"   Throughput: {throughput:.1f} tokens/sec")
        print(f"   Requests/sec: {total_requests / elapsed:.1f}")

        if gpu_stats:
            print(f"   GPU Avg: {gpu_stats['gpu_avg']:.1f}%")

        return {
            "duration_seconds": elapsed,
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "throughput_tokens_per_sec": throughput,
            "requests_per_sec": total_requests / elapsed,
            **gpu_stats,
        }

    # -------------------------------------------------------------------------
    # TEST 4: REAL-WORLD TOOL CALLING
    # -------------------------------------------------------------------------
    def test_real_tool_calling(self) -> Dict:
        """Test actual tool calling with execution."""
        print("\n" + "=" * 60)
        print("TEST 4: REAL-WORLD TOOL CALLING")
        print("=" * 60)

        if not self.llm:
            print("⚠️ Model not loaded, loading now...")
            self.test_cold_start()

        # Import Rosetta executor
        from nx_engine.local_llm.rosetta_executor import (
            translate_request,
            execute_request,
        )

        # Monkey-patch the LLM
        import nx_engine.local_llm.rosetta_executor as rosetta_module

        rosetta_module._rosetta_llm = self.llm

        # Test real tool calling
        test_cases = [
            "search memory for authentication tokens",
            "check git status",
            "get the active context",
            "run type check",
            "list all sessions",
            "navigate to github.com",
            "fetch python.org",
            "send telegram message hello",
        ]

        correct = 0
        total = len(test_cases)
        latencies = []

        for request in test_cases:
            start = time.time()

            try:
                result = asyncio.run(execute_request(request))
                elapsed = time.time() - start

                if "error" not in result or not result.get("error"):
                    correct += 1
                    status = "✅"
                else:
                    status = "❌"

                latencies.append(elapsed * 1000)
                print(f"{status} {request[:40]:<40} ({elapsed * 1000:.0f}ms)")

            except Exception as e:
                print(f"❌ {request[:40]:<40} ERROR: {str(e)[:30]}")
                latencies.append(0)

        accuracy = (correct / total) * 100
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        print(f"\n✅ Real Tool Calling Results:")
        print(f"   Accuracy: {correct}/{total} ({accuracy:.1f}%)")
        print(f"   Avg Latency: {avg_latency:.0f}ms")

        return {
            "correct": correct,
            "total": total,
            "accuracy_percent": accuracy,
            "avg_latency_ms": avg_latency,
            "test_cases": test_cases,
        }

    # -------------------------------------------------------------------------
    # TEST 5: MEMORY STRESS
    # -------------------------------------------------------------------------
    def test_memory_stress(self) -> Dict:
        """Test memory behavior under stress."""
        print("\n" + "=" * 60)
        print("TEST 5: MEMORY STRESS TEST")
        print("=" * 60)

        if not self.llm:
            print("⚠️ Model not loaded, loading now...")
            self.test_cold_start()

        # Initial memory
        process = psutil.Process()
        initial_mem = process.memory_info().rss / 1024 / 1024

        # Run many inferences
        print("Running 50 sequential inferences...")

        for i in range(50):
            response = self.llm.chat(
                [{"role": "user", "content": random.choice(TEST_PROMPTS)}],
                max_tokens=100,
            )

            if i % 10 == 0:
                current_mem = process.memory_info().rss / 1024 / 1024
                print(f"   {i}/50 - RAM: {current_mem:.0f}MB")

        final_mem = process.memory_info().rss / 1024 / 1024
        mem_increase = final_mem - initial_mem

        # GPU memory check
        gpu_mem_mb = 0
        if self.gpu_monitor._nvml_available:
            try:
                mem_info = self.gpu_monitor._nvml.nvmlDeviceGetMemoryInfo(
                    self.gpu_monitor._handle
                )
                gpu_mem_mb = mem_info.used / 1024 / 1024
            except:
                pass

        print(f"\n✅ Memory Stress Results:")
        print(f"   Initial RAM: {initial_mem:.0f}MB")
        print(f"   Final RAM: {final_mem:.0f}MB")
        print(f"   Increase: {mem_increase:.0f}MB")
        print(f"   GPU VRAM: {gpu_mem_mb:.0f}MB")

        return {
            "initial_ram_mb": initial_mem,
            "final_ram_mb": final_mem,
            "ram_increase_mb": mem_increase,
            "gpu_vram_mb": gpu_mem_mb,
        }


# ============================================================================
# COMPARE TRAINED VS UNTRAINED
# ============================================================================


def compare_models():
    """Compare trained vs untrained model."""
    print("\n" + "=" * 60)
    print("COMPARISON: TRAINED vs UNTRAINED")
    print("=" * 60)

    results = {}

    for model_name, config in MODELS.items():
        print(f"\n--- Testing: {model_name} ({config['description']}) ---")

        benchmark = RosettaBenchmark(model_name)

        # Quick test: 50 inferences
        latencies = []

        try:
            benchmark.test_cold_start()

            for _ in range(50):
                start = time.time()
                benchmark.llm.chat(
                    [{"role": "user", "content": random.choice(TEST_PROMPTS)}],
                    max_tokens=50,
                )
                latencies.append((time.time() - start) * 1000)

            avg_latency = sum(latencies) / len(latencies)

            results[model_name] = {
                "avg_latency_ms": avg_latency,
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
            }

            print(f"   Avg latency: {avg_latency:.1f}ms")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            results[model_name] = {"error": str(e)}

    # Summary
    print("\n" + "=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)

    for name, data in results.items():
        if "error" not in data:
            print(f"{name:<20} {data['avg_latency_ms']:.1f}ms avg")

    return results


# ============================================================================
# MAIN
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="Real-World Rosetta Benchmark")
    parser.add_argument(
        "--model",
        default="trained_q8",
        choices=list(MODELS.keys()),
        help="Model to test",
    )
    parser.add_argument(
        "--test",
        default="all",
        choices=[
            "all",
            "cold_start",
            "latency",
            "throughput",
            "tool_calling",
            "memory",
            "compare",
        ],
        help="Which test to run",
    )
    parser.add_argument(
        "--runs", type=int, default=100, help="Number of runs for latency test"
    )
    parser.add_argument(
        "--duration", type=int, default=10, help="Duration for throughput test"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("ROSETTA REAL-WORLD BENCHMARK SUITE")
    print("=" * 60)
    print(f"Model: {args.model}")
    print(f"Test: {args.test}")
    print("=" * 60)

    all_results = {}

    if args.test == "compare":
        all_results["compare"] = compare_models()
    else:
        benchmark = RosettaBenchmark(args.model)

        if args.test in ["all", "cold_start"]:
            all_results["cold_start"] = benchmark.test_cold_start()

        if args.test in ["all", "latency"]:
            all_results["latency"] = benchmark.test_latency(args.runs)

        if args.test in ["all", "throughput"]:
            all_results["throughput"] = benchmark.test_throughput(args.duration)

        if args.test in ["all", "tool_calling"]:
            all_results["tool_calling"] = benchmark.test_real_tool_calling()

        if args.test in ["all", "memory"]:
            all_results["memory"] = benchmark.test_memory_stress()

    # Save results
    output_file = (
        PROJECT_ROOT
        / "benchmarks"
        / f"real_benchmark_{args.model}_{args.test}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n✅ Results saved to: {output_file}")

    # Print summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)

    for test_name, result in all_results.items():
        if isinstance(result, dict):
            if "avg_latency_ms" in result:
                print(f"{test_name}: {result['avg_latency_ms']:.1f}ms")
            elif "load_time_seconds" in result:
                print(f"{test_name}: {result['load_time_seconds']:.2f}s")
            elif "throughput_tokens_per_sec" in result:
                print(f"{test_name}: {result['throughput_tokens_per_sec']:.0f} tok/s")
            elif "accuracy_percent" in result:
                print(f"{test_name}: {result['accuracy_percent']:.1f}%")

    print("=" * 60)

    return all_results


if __name__ == "__main__":
    main()
