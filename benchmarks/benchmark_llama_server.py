#!/usr/bin/env python3
"""
Benchmark: Native llama-server vs llama-cpp-python

Tests:
1. Sequential performance
2. Parallel performance (6 concurrent requests)
3. Tool calling capability
4. Throughput comparison
"""

import httpx
import asyncio
import time
import statistics

BASE_URL = "http://localhost:8080/v1"


async def chat(messages, model="qwen2.5-0.5b", max_tokens=100):
    """Make a single chat request."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        start = time.time()
        r = await client.post(
            f"{BASE_URL}/chat/completions",
            json={"model": model, "messages": messages, "max_tokens": max_tokens},
        )
        elapsed = time.time() - start

        if r.status_code == 200:
            data = r.json()
            return {
                "success": True,
                "elapsed": elapsed,
                "tokens": data.get("usage", {}).get("completion_tokens", 0),
            }
        return {"success": False, "elapsed": elapsed, "error": r.text[:100]}


async def test_sequential():
    """Test sequential requests."""
    prompts = [
        [{"role": "user", "content": "Say 'hello'"}],
        [{"role": "user", "content": "What is 2+2?"}],
        [{"role": "user", "content": "Count to 5"}],
    ]

    results = []
    for p in prompts:
        r = await chat(p)
        results.append(r)
        print(f"  Sequential: {r.get('elapsed', 0):.2f}s")

    success = [r for r in results if r.get("success")]
    if success:
        avg = statistics.mean([r["elapsed"] for r in success])
        tokens = sum(r.get("tokens", 0) for r in success)
        print(f"  Avg latency: {avg:.2f}s, Total tokens: {tokens}")
    return results


async def test_parallel(workers=6):
    """Test parallel requests."""
    prompts = [{"role": "user", "content": f"Say '{i}'"} for i in range(workers)]

    async with httpx.AsyncClient(timeout=120.0) as client:
        tasks = [
            client.post(
                f"{BASE_URL}/chat/completions",
                json={"model": "qwen2.5-0.5b", "messages": p, "max_tokens": 50},
            )
            for p in prompts
        ]

        start = time.time()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        wall_time = time.time() - start

        success = [
            r for r in responses if hasattr(r, "status_code") and r.status_code == 200
        ]
        tokens = sum(
            r.json().get("usage", {}).get("completion_tokens", 0) for r in success
        )

        print(f"  Parallel ({workers} requests): {wall_time:.2f}s wall time")
        print(f"    Success: {len(success)}/{workers}")
        print(f"    Throughput: {len(success) / wall_time:.2f} req/s")
        print(f"    Tokens: {tokens}, {tokens / wall_time:.0f} tok/s")

        return {"wall_time": wall_time, "success": len(success), "tokens": tokens}


async def test_tool_calling():
    """Test tool calling."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            f"{BASE_URL}/chat/completions",
            json={
                "model": "qwen2.5-0.5b",
                "messages": [{"role": "user", "content": "List files in current dir"}],
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
            msg = data["choices"][0]["message"]
            if "tool_calls" in msg:
                tc = msg["tool_calls"][0]["function"]
                print(f"  Tool call: {tc['name']}({tc['arguments'][:50]}...)")
                return {"success": True, "tool_call": tc}

        print(f"  Tool call failed: {r.status_code}")
        return {"success": False}


async def main():
    print("=" * 60)
    print("NATIVE LLAMA-SERVER BENCHMARK")
    print("=" * 60)
    print(f"URL: {BASE_URL}")
    print()

    # Check health
    async with httpx.AsyncClient() as client:
        r = await client.get("http://localhost:8080/health")
        print(f"Health: {r.json()}")

    print()
    print("1. SEQUENTIAL TEST")
    await test_sequential()

    print()
    print("2. PARALLEL TEST (6 concurrent)")
    await test_parallel(6)

    print()
    print("3. TOOL CALLING TEST")
    await test_tool_calling()

    print()
    print("=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
