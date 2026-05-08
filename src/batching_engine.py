#!/usr/bin/env python3
"""
Custom Continuous Batching Engine for llama.cpp
Optimized for AMD 7800X3D CPU + RTX 3080 Ti GPU
"""

import asyncio
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

LLAMA_SERVER_PATH = "/home/nxyme/llama.cpp/build/bin/llama-server"
MODEL_PATH = (
    "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models/TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf"
)


@dataclass
class Request:
    id: str
    prompt: str
    max_tokens: int = 512
    temperature: float = 0.7
    on_token: Optional[Callable] = None
    on_complete: Optional[Callable] = None
    on_error: Optional[Callable] = None


class BatchingEngine:
    def __init__(self, model_path: str = MODEL_PATH, n_parallel: int = 8):
        self.model_path = model_path
        self.n_parallel = n_parallel
        self.server_process = None
        self.base_url = "http://localhost:8089"
        self.running = False
        self._lock = threading.Lock()

    def _build_args(self):
        return [
            LLAMA_SERVER_PATH,
            "-m",
            self.model_path,
            "-c",
            "4096",
            "-np",
            str(self.n_parallel),
            "-cb",
            "-ngl",
            "99",
            "-t",
            "16",
            "--flash-attn",
            "on",
            "-ctk",
            "q4_0",
            "-ctv",
            "q4_0",
            "-b",
            "2048",
            "-ub",
            "512",
            "--port",
            "8089",
        ]

    def start(self):
        if self.running:
            return
        self.server_process = subprocess.Popen(
            self._build_args(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(2)
        self.running = True

    def stop(self):
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
        self.running = False

    async def generate(self, request: Request) -> dict:
        import aiohttp

        payload = {
            "prompt": request.prompt,
            "n_predict": request.max_tokens,
            "temperature": request.temperature,
            "stream": False,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/v1/completions", json=payload
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    if request.on_error:
                        request.on_error(error)
                    return {"error": error}
                result = await resp.json()
                if request.on_complete:
                    request.on_complete(result.get("content", ""))
                return result


async def batch_process(engine: BatchingEngine, prompts: list):
    tasks = []
    for i, prompt in enumerate(prompts):
        req = Request(id=f"req_{i}", prompt=prompt)
        tasks.append(asyncio.create_task(engine.generate(req)))

    results = await asyncio.gather(*tasks)
    return results


if __name__ == "__main__":
    prompts = [
        "Write a story about a robot.",
        "Explain quantum computing in simple terms.",
        "What is the meaning of life?",
        "Describe the process of photosynthesis.",
    ]

    engine = BatchingEngine()
    print("Starting custom batching engine...")
    engine.start()

    print(f"Running parallel batch with {len(prompts)} prompts...")
    start = time.time()
    results = asyncio.run(batch_process(engine, prompts))
    elapsed = time.time() - start

    print(f"\nBatch completed in {elapsed:.2f}s")
    for i, r in enumerate(results):
        if "error" not in r:
            print(f"Request {i}: {len(r.get('content', ''))} chars")
        else:
            print(f"Request {i}: Error - {r['error'][:50]}")

    engine.stop()
    print("Engine stopped.")
