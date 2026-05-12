#!/usr/bin/env python3
"""Industry-standard 3-way benchmark: Vanilla vs First Iteration vs Optimized"""

import httpx
import asyncio
import time
import subprocess
import json
import os
import signal

SERVER_PID = None
MODEL = "qwen2.5-0.5b-instruct-q4_k_m.gguf"
MODEL_PATH = f"/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models/{MODEL}"
SERVER_BIN = "/home/nxyme/llama.cpp/build/bin/llama-server"


def kill_server():
    """Kill any existing server"""
    os.system("fuser -k 8080/tcp 2>/dev/null")
    time.sleep(1)


def start_server(flags: str, name: str, log_file: str):
    """Start llama-server with given flags"""
    global SERVER_PID
    kill_server()

    cmd = f"{SERVER_BIN} -m {MODEL_PATH} {flags} -c 4096 -np 8 -cb -t 8 --jinja --port 8080 --host 0.0.0.0"
    print(f"\n{'=' * 60}")
    print(f"Starting: {name}")
    print(f"Flags: {flags}")
    print(f"{'=' * 60}")

    # Start in background
    pid = os.fork()
    if pid == 0:
        # Child process
        with open(log_file, "w") as f:
            os.dup2(f.fileno(), 1)
            os.dup2(f.fileno(), 2)
            os.execv(SERVER_BIN, cmd.split() + flags.split())
    else:
        SERVER_PID = pid
        # Wait for server to be ready
        for _ in range(20):
            try:
                r = httpx.get("http://localhost:8080/health", timeout=2)
                if r.status_code == 200:
                    print(f"✅ {name} ready")
                    return True
            except:
                pass
            time.sleep(1)
        print(f"❌ {name} failed to start")
        return False


async def get_gpu():
    """Get current GPU utilization"""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return float(result.stdout.strip())
    except:
        return 0


async def benchmark(name: str) -> dict:
    """Run benchmark suite"""
    prompts = [
        "Write a short story",
        "Explain quantum physics",
        "What is AI?",
        "Hello world",
        "Count to 10",
    ]

    results = {"name": name, "tests": {}}
    gpu_utils = []

    async with httpx.AsyncClient(timeout=180) as client:
        # Single request
        start = time.time()
        try:
            r = await client.post(
                "http://localhost:8080/chat/completions",
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "user", "content": "Write a short story about a robot"}
                    ],
                    "max_tokens": 100,
                },
            )
            elapsed = time.time() - start
            data = r.json()
            tokens = data.get("usage", {}).get("completion_tokens", 0)
            tok_s = tokens / elapsed if elapsed > 0 else 0
            gpu_utils.append(await get_gpu())
            results["tests"]["single"] = {
                "time_ms": elapsed * 1000,
                "tok_s": tok_s,
                "tokens": tokens,
            }
        except Exception as e:
            results["tests"]["single"] = {"error": str(e)}

        await asyncio.sleep(0.5)

        # Parallel 8
        start = time.time()
        tasks = [
            client.post(
                "http://localhost:8080/chat/completions",
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": p}],
                    "max_tokens": 50,
                },
            )
            for p in prompts * 2
        ]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start
        total_tokens = sum(
            r.json().get("usage", {}).get("completion_tokens", 0)
            for r in results_list
            if hasattr(r, "status_code") and r.status_code == 200
        )
        gpu_utils.append(await get_gpu())
        results["tests"]["parallel_8"] = {
            "time_ms": elapsed * 1000,
            "tok_s": total_tokens / elapsed,
            "tokens": total_tokens,
        }

        await asyncio.sleep(0.5)

        # Parallel 16
        start = time.time()
        tasks = [
            client.post(
                "http://localhost:8080/chat/completions",
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": p}],
                    "max_tokens": 50,
                },
            )
            for p in prompts * 4
        ]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start
        total_tokens = sum(
            r.json().get("usage", {}).get("completion_tokens", 0)
            for r in results_list
            if hasattr(r, "status_code") and r.status_code == 200
        )
        gpu_utils.append(await get_gpu())
        results["tests"]["parallel_16"] = {
            "time_ms": elapsed * 1000,
            "tok_s": total_tokens / elapsed,
            "tokens": total_tokens,
        }

        await asyncio.sleep(0.5)

        # Parallel 32
        start = time.time()
        tasks = [
            client.post(
                "http://localhost:8080/chat/completions",
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": p}],
                    "max_tokens": 50,
                },
            )
            for p in prompts * 7
        ]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start
        total_tokens = sum(
            r.json().get("usage", {}).get("completion_tokens", 0)
            for r in results_list
            if hasattr(r, "status_code") and r.status_code == 200
        )
        gpu_utils.append(await get_gpu())
        results["tests"]["parallel_32"] = {
            "time_ms": elapsed * 1000,
            "tok_s": total_tokens / elapsed,
            "tokens": total_tokens,
        }

    results["avg_gpu"] = sum(gpu_utils) / len(gpu_utils) if gpu_utils else 0
    return results


async def main():
    print("=" * 70)
    print("INDUSTRY-STANDARD 3-WAY BENCHMARK")
    print("Vanilla CPU vs First Iteration (GPU) vs Full Optimized")
    print("=" * 70)

    all_results = {}

    # Test 1: Vanilla (CPU-only)
    if start_server("-ngl 0", "VANILLA (CPU-only)", "/tmp/bench-vanilla.log"):
        await asyncio.sleep(2)
        all_results["vanilla"] = await benchmark("Vanilla CPU-only")
        kill_server()

    # Test 2: First Iteration (Basic GPU)
    if start_server("-ngl 99", "FIRST ITERATION (GPU only)", "/tmp/bench-v1.log"):
        await asyncio.sleep(2)
        all_results["first_iter"] = await benchmark("First Iteration GPU")
        kill_server()

    # Test 3: Full Optimized
    if start_server(
        "-ngl 99 --flash-attn on -ctk q4_0 -ctv q4_0 --no-mmap",
        "FULL OPTIMIZED",
        "/tmp/bench-opt.log",
    ):
        await asyncio.sleep(2)
        all_results["optimized"] = await benchmark("Full Optimized")
        kill_server()

    # Print comparison table
    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS COMPARISON")
    print("=" * 70)

    print(
        f"\n{'Test':<20} {'Single (tok/s)':<15} {'P8 (tok/s)':<15} {'P16 (tok/s)':<15} {'P32 (tok/s)':<15}"
    )
    print("-" * 70)

    for name, data in all_results.items():
        tests = data.get("tests", {})
        single = tests.get("single", {}).get("tok_s", 0)
        p8 = tests.get("parallel_8", {}).get("tok_s", 0)
        p16 = tests.get("parallel_16", {}).get("tok_s", 0)
        p32 = tests.get("parallel_32", {}).get("tok_s", 0)
        print(f"{name:<20} {single:<15.1f} {p8:<15.1f} {p16:<15.1f} {p32:<15.1f}")

    # Calculate improvements
    if "vanilla" in all_results and "first_iter" in all_results:
        v = all_results["vanilla"]["tests"]
        f = all_results["first_iter"]["tests"]

        print("\n" + "=" * 70)
        print("IMPROVEMENTS")
        print("=" * 70)

        for test in ["single", "parallel_8", "parallel_16", "parallel_32"]:
            v_tok = v.get(test, {}).get("tok_s", 1)
            f_tok = f.get(test, {}).get("tok_s", 1)
            improvement = ((f_tok - v_tok) / v_tok) * 100
            print(
                f"{test}: Vanilla {v_tok:.1f} → First Iter {f_tok:.1f} = {improvement:+.1f}%"
            )

    if "first_iter" in all_results and "optimized" in all_results:
        f = all_results["first_iter"]["tests"]
        o = all_results["optimized"]["tests"]

        print("\n" + "-" * 70)

        for test in ["single", "parallel_8", "parallel_16", "parallel_32"]:
            f_tok = f.get(test, {}).get("tok_s", 1)
            o_tok = o.get(test, {}).get("tok_s", 1)
            improvement = ((o_tok - f_tok) / f_tok) * 100
            print(
                f"{test}: First Iter {f_tok:.1f} → Optimized {o_tok:.1f} = {improvement:+.1f}%"
            )

    # Save to JSON
    with open(
        "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/industry_benchmark_results.json", "w"
    ) as f:
        json.dump(all_results, f, indent=2)

    print("\n✅ Results saved to industry_benchmark_results.json")


if __name__ == "__main__":
    asyncio.run(main())
