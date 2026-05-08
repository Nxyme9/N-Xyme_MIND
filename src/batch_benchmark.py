#!/usr/bin/env python3
"""
Batched Inference Benchmark - Custom Continuous Batching Engine
Measures throughput of parallel requests with continuous batching
"""

import asyncio
import aiohttp
import time
import statistics

BASE_URL = "http://localhost:8080"
MODEL = "qwen2.5-0.5b-instruct-q4_k_m.gguf"

PROMPTS = [
    "Explain the concept of recursion in programming.",
    "What is the difference between a stack and a queue?",
    "Describe how binary search works.",
    "What are the time complexities of common sorting algorithms?",
    "Explain the Observer design pattern.",
    "What is memoization and when is it useful?",
    "How does a hash table work internally?",
    "What is the difference between SQL and NoSQL databases?",
]


async def single_request(session, prompt, request_id):
    start = time.time()
    try:
        async with session.post(
            f"{BASE_URL}/v1/completions",
            json={
                "prompt": prompt,
                "n_predict": 100,
                "temperature": 0.7,
                "stream": False,
            },
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                elapsed = time.time() - start
                content = result.get("choices", [{}])[0].get("text", "")
                tokens = len(content.split())
                return {
                    "id": request_id,
                    "success": True,
                    "elapsed": elapsed,
                    "tokens": tokens,
                    "tps": tokens / elapsed if elapsed > 0 else 0,
                }
            else:
                error = await resp.text()
                return {"id": request_id, "success": False, "error": error[:100]}
    except Exception as e:
        return {"id": request_id, "success": False, "error": str(e)[:100]}


async def run_batch(batch_size, num_batches):
    results = []
    async with aiohttp.ClientSession() as session:
        for batch_idx in range(num_batches):
            batch_prompts = PROMPTS[:batch_size] * (batch_idx + 1)
            tasks = [
                single_request(session, p, f"{batch_idx}_{i}")
                for i, p in enumerate(batch_prompts)
            ]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
    return results


async def main():
    print("=" * 60)
    print("Custom Continuous Batching Engine - Performance Test")
    print("=" * 60)
    print(f"Server: {BASE_URL}")
    print(f"Model: {MODEL}")
    print("Config: -np 8 -cb --flash-attn on -ctk q4_0")
    print("=" * 60)

    print("\n[1] Testing server health...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BASE_URL}/health", timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                print(f"    Server status: {resp.status}")
    except Exception as e:
        print(f"    ERROR: {e}")
        print("    Start server: bash start_llama_server.sh")
        return

    print("\n[2] Running batched inference tests...")
    test_configs = [
        (1, 1),  # Baseline: 1 request
        (4, 2),  # 4 parallel, 2 batches
        (8, 3),  # 8 parallel, 3 batches
    ]

    for batch_size, num_batches in test_configs:
        print(f"\n    Test: {batch_size} parallel requests x {num_batches} batches")

        start = time.time()
        results = await run_batch(batch_size, num_batches)
        total_time = time.time() - start

        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]

        if successful:
            avg_tps = statistics.mean([r.get("tps", 0) for r in successful])
            total_tokens = sum([r.get("tokens", 0) for r in successful])
            print(f"    Results: {len(successful)} success, {len(failed)} failed")
            print(f"    Total time: {total_time:.2f}s")
            print(f"    Total tokens: {total_tokens}")
            print(f"    Average throughput: {avg_tps:.1f} tok/s")
        else:
            print("    All requests failed!")
            if failed:
                print(f"    Error: {failed[0].get('error', 'unknown')}")

    print("\n" + "=" * 60)
    print("Test complete!")


if __name__ == "__main__":
    asyncio.run(main())
