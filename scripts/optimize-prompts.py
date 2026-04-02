#!/usr/bin/env python3
"""Optimization Benchmark — Test different prompt strategies"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OLLAMA_URL = "http://localhost:11434"

BENCHMARK_TASK = {
    "title": "Architecture Review",
    "description": "Review this architecture for issues: A microservice system with 5 services, PostgreSQL database, Redis cache, and RabbitMQ message queue. Services communicate via REST APIs and async messages. What are the potential issues and improvements?",
}

STRATEGIES = {
    "baseline": {
        "prompt": "You are an expert. Provide complete, actionable results.",
        "temperature": 0.7,
        "max_tokens": 2000,
    },
    "step-by-step": {
        "prompt": "Think step by step. Analyze systematically.",
        "temperature": 0.5,
        "max_tokens": 2000,
    },
    "chain-of-thought": {
        "prompt": "Let's think through this step by step:\n1. First, identify the components\n2. Then, analyze each component\n3. Next, consider interactions\n4. Finally, provide recommendations",
        "temperature": 0.4,
        "max_tokens": 2500,
    },
    "expert-persona": {
        "prompt": "You are a senior software architect with 20 years of experience. You've designed systems handling millions of requests. Review this architecture with your expert eye.",
        "temperature": 0.3,
        "max_tokens": 2000,
    },
    "structured-output": {
        "prompt": "Provide your analysis in this exact format:\n## Critical Issues\n- [Issue 1]\n- [Issue 2]\n## Important Issues\n- [Issue 1]\n## Suggestions\n- [Suggestion 1]\n## Verdict\n[PASS/FAIL/CONDITIONAL]",
        "temperature": 0.3,
        "max_tokens": 2000,
    },
    "combined": {
        "prompt": "You are a senior software architect. Think step by step. Analyze this architecture systematically:\n1. Identify components\n2. Analyze each component\n3. Consider interactions\n4. Provide recommendations\n\nFormat your response with clear sections.",
        "temperature": 0.4,
        "max_tokens": 2500,
    },
}


def run_strategy(name: str, config: dict) -> dict:
    prompt = (
        f"{config['prompt']}\n\nTask: {BENCHMARK_TASK['title']}\n{BENCHMARK_TASK['description']}"
    )

    start = time.time()
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": "qwen2.5-coder:7b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": config["temperature"],
                    "num_predict": config["max_tokens"],
                },
            },
            timeout=120,
        )
        resp.raise_for_status()
        result = resp.json()["response"]
        duration = time.time() - start

        word_count = len(result.split())
        has_structure = any(marker in result for marker in ["##", "1.", "2.", "-", "*"])
        has_verdict = any(
            word in result.upper()
            for word in ["PASS", "FAIL", "CONDITIONAL", "CRITICAL", "IMPORTANT"]
        )

        score = 0
        if word_count > 300:
            score += 30
        if word_count > 500:
            score += 20
        if has_structure:
            score += 25
        if has_verdict:
            score += 25

        return {
            "strategy": name,
            "status": "success",
            "score": score,
            "word_count": word_count,
            "duration": round(duration, 2),
            "has_structure": has_structure,
            "has_verdict": has_verdict,
        }
    except Exception as e:
        return {
            "strategy": name,
            "status": "failed",
            "error": str(e),
            "duration": time.time() - start,
        }


def main():
    print("Running optimization benchmark...")
    results = []

    for name, config in STRATEGIES.items():
        print(f"Testing: {name}...")
        result = run_strategy(name, config)
        results.append(result)
        print(
            f"  Score: {result.get('score', 0)}, Words: {result.get('word_count', 0)}, Time: {result.get('duration', 0)}s"
        )

    print("\n" + "=" * 60)
    print("OPTIMIZATION RESULTS")
    print("=" * 60)

    successful = [r for r in results if r["status"] == "success"]
    successful.sort(key=lambda x: x["score"], reverse=True)

    for r in successful:
        print(
            f"{r['strategy']:20} | Score: {r['score']:3} | Words: {r['word_count']:4} | Time: {r['duration']:5.1f}s"
        )

    best = successful[0] if successful else None
    if best:
        print(f"\nBest strategy: {best['strategy']} (score: {best['score']})")

    Path("optimization-results.json").write_text(json.dumps(results, indent=2))
    print("\nResults saved to optimization-results.json")


if __name__ == "__main__":
    main()
