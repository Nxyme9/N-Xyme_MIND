#!/usr/bin/env python3
"""Benchmark: Compare Cloud vs Local model output quality"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from prompt_templates import get_prompt

OLLAMA_URL = "http://localhost:11434"
OPENCODE_URL = "https://opencode.ai/zen/v1/chat/completions"
GRAPHITI_URL = "http://localhost:8001/json-rpc"

BENCHMARK_TASKS = [
    {
        "id": "bench-arch",
        "title": "Architecture Review",
        "description": "Review this architecture for issues: A microservice system with 5 services, PostgreSQL database, Redis cache, and RabbitMQ message queue. Services communicate via REST APIs and async messages. What are the potential issues and improvements?",
        "agent": "oracle",
        "category": "architecture_review",
    },
    {
        "id": "bench-code",
        "title": "Code Implementation",
        "description": "Write a Python function that implements a thread-safe LRU cache with TTL support. Include type hints and docstrings.",
        "agent": "hephaestus",
        "category": "code_generation",
    },
    {
        "id": "bench-research",
        "title": "Research Query",
        "description": "Compare the pros and cons of using WebSockets vs Server-Sent Events vs Long Polling for real-time web applications. Include performance benchmarks and use case recommendations.",
        "agent": "librarian",
        "category": "research",
    },
    {
        "id": "bench-plan",
        "title": "Strategic Planning",
        "description": "Create a 3-month development roadmap for a habit tracking mobile app. Include MVP features, technical milestones, and risk mitigation strategies.",
        "agent": "prometheus",
        "category": "planning",
    },
]

MODELS = {
    "cloud": "opencode/mimo-v2-pro-free",
    "local-qwen": "qwen2.5:14b",
    "local-coder": "qwen2.5-coder:7b",
}


def call_cloud(model: str, prompt: str) -> dict:
    start = time.time()
    try:
        resp = requests.post(
            OPENCODE_URL,
            json={
                "model": model.replace("opencode/", ""),
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert AI agent. Provide complete, actionable results.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 2000,
            },
            timeout=120,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return {"status": "success", "result": content, "time": time.time() - start}
    except Exception as e:
        return {"status": "failed", "error": str(e), "time": time.time() - start}


def call_local(model: str, prompt: str, temperature: float = 0.7) -> dict:
    start = time.time()
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": 2000},
            },
            timeout=120,
        )
        resp.raise_for_status()
        content = resp.json()["response"]
        return {"status": "success", "result": content, "time": time.time() - start}
    except Exception as e:
        return {"status": "failed", "error": str(e), "time": time.time() - start}


def score_output(task: dict, result: dict) -> dict:
    if result["status"] != "success":
        return {"overall": 0, "completeness": 0, "relevance": 0, "structure": 0, "detail": 0}

    text = result["result"]
    word_count = len(text.split())

    completeness = min(100, word_count / 20)  # 2000 words = 100%
    relevance = (
        80 if any(kw in text.lower() for kw in task["description"].lower().split()[:5]) else 40
    )
    structure = 90 if any(marker in text for marker in ["1.", "2.", "-", "*", "##"]) else 50
    detail = min(100, len(text) / 50)  # 5000 chars = 100%

    overall = completeness * 0.3 + relevance * 0.3 + structure * 0.2 + detail * 0.2
    return {
        "overall": round(overall, 1),
        "completeness": round(completeness, 1),
        "relevance": round(relevance, 1),
        "structure": round(structure, 1),
        "detail": round(detail, 1),
        "word_count": word_count,
        "char_count": len(text),
    }


def run_benchmark():
    results = []

    for task in BENCHMARK_TASKS:
        prompt_data = get_prompt(task["agent"], task["title"], task["description"])
        prompt = f"{prompt_data['system']}\n\n{prompt_data['user']}"

        for model_name, model_id in MODELS.items():
            print(f"Running: {task['id']} × {model_name}...")

            if model_name == "cloud":
                result = call_cloud(model_id, prompt)
            else:
                result = call_local(model_id, prompt, temperature=prompt_data["temperature"])

            scores = score_output(task, result)

            results.append(
                {
                    "task_id": task["id"],
                    "task_title": task["title"],
                    "agent": task["agent"],
                    "model": model_name,
                    "model_id": model_id,
                    "status": result["status"],
                    "time_seconds": round(result["time"], 2),
                    "scores": scores,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

    return results


def print_report(results: list):
    print("\n" + "=" * 80)
    print("BENCHMARK REPORT")
    print("=" * 80)

    by_model = {}
    for r in results:
        model = r["model"]
        if model not in by_model:
            by_model[model] = []
        by_model[model].append(r)

    print("\n--- BY MODEL ---")
    for model, tasks in by_model.items():
        successful = [t for t in tasks if t["status"] == "success"]
        avg_score = (
            sum(t["scores"]["overall"] for t in successful) / len(successful) if successful else 0
        )
        avg_time = sum(t["time_seconds"] for t in successful) / len(successful) if successful else 0
        print(
            f"{model:15} | Success: {len(successful)}/{len(tasks)} | Avg Score: {avg_score:.1f}% | Avg Time: {avg_time:.1f}s"
        )

    print("\n--- BY TASK ---")
    by_task = {}
    for r in results:
        task = r["task_id"]
        if task not in by_task:
            by_task[task] = []
        by_task[task].append(r)

    for task_id, models in by_task.items():
        print(f"\n{task_id}:")
        for m in sorted(models, key=lambda x: x["scores"]["overall"], reverse=True):
            s = m["scores"]
            wc = s.get("word_count", 0)
            print(
                f"  {m['model']:15} | {s['overall']:5.1f}% | {m['time_seconds']:5.1f}s | {wc:4} words"
            )

    print("\n--- QUALITY COMPARISON ---")
    cloud_scores = [
        r["scores"]["overall"]
        for r in results
        if r["model"] == "cloud" and r["status"] == "success"
    ]
    local_scores = [
        r["scores"]["overall"]
        for r in results
        if r["model"] != "cloud" and r["status"] == "success"
    ]

    if cloud_scores and local_scores:
        cloud_avg = sum(cloud_scores) / len(cloud_scores)
        local_avg = sum(local_scores) / len(local_scores)
        diff = cloud_avg - local_avg
        print(f"Cloud avg: {cloud_avg:.1f}%")
        print(f"Local avg: {local_avg:.1f}%")
        print(f"Difference: {diff:+.1f}% ({'cloud better' if diff > 0 else 'local better'})")


if __name__ == "__main__":
    print("Starting benchmark...")
    results = run_benchmark()

    output_file = Path("benchmark-results.json")
    output_file.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved to {output_file}")

    print_report(results)
