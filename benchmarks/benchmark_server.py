#!/usr/bin/env python3
import asyncio
import aiohttp
import time
import statistics


async def send_request(session, prompt, max_tokens=30):
    start = time.time()
    try:
        async with session.post(
            "http://localhost:8081/v1/completions",
            json={"prompt": prompt, "max_tokens": max_tokens},
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            data = await resp.json()
            elapsed = time.time() - start
            tokens = len(data.get("choices", [{}])[0].get("text", "").split())
            return elapsed, tokens
    except Exception as e:
        return time.time() - start, 0


async def benchmark(num_requests, num_parallel):
    async with aiohttp.ClientSession() as session:
        prompts = [f"Write a short story about {i}" for i in range(num_requests)]

        start = time.time()
        tasks = [send_request(session, p) for p in prompts]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start

        individual_times = [r[0] for r in results]
        total_tokens = sum(r[1] for r in results)

        print(f"=== Benchmark: {num_requests} requests, {num_parallel} parallel ===")
        print(f"Total time: {total_time:.2f}s")
        print(f"Avg per request: {statistics.mean(individual_times):.2f}s")
        print(f"Total tokens: {total_tokens}")
        if total_time > 0:
            print(f"Throughput: {total_tokens / total_time:.1f} tok/s")
        print()


if __name__ == "__main__":
    asyncio.run(benchmark(8, 8))
    asyncio.run(benchmark(16, 16))
    asyncio.run(benchmark(32, 32))
