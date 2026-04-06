#!/usr/bin/env python3
import argparse
import importlib.util
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

if importlib.util.find_spec("local_router"):
    local_router = importlib.import_module("local_router")
else:
    local_router = None

from model_keywords import (
    SIMPLE_KEYWORDS,
    MEDIUM_KEYWORDS,
    COMPLEX_KEYWORDS,
)

MODELS = {
    "offline": os.getenv("OFFLINE_MODEL", "ollama/llama3.2:3b"),
    "complex": os.getenv("PRIMARY_MODEL", "openrouter/deepseek/deepseek-r1"),
    "medium": os.getenv("PRIMARY_MODEL", "opencode/qwen3.6-plus-free"),
    "simple": os.getenv("FALLBACK_MODEL", "opencode/minimax-m2.5-free"),
}

LOCAL_MODELS = {
    "simple": os.getenv("LOCAL_SIMPLE_MODEL", "ollama/llama3.2:1b"),
    "medium": os.getenv("LOCAL_MEDIUM_MODEL", "ollama/llama3.2:3b"),
    "complex": os.getenv("LOCAL_COMPLEX_MODEL", "ollama/llama3.2:7b"),
}


def detect_complexity(task: str) -> str:
    task_lower = task.lower()

    complex_score = sum(1 for kw in COMPLEX_KEYWORDS if kw in task_lower)
    medium_score = sum(1 for kw in MEDIUM_KEYWORDS if kw in task_lower)
    simple_score = sum(1 for kw in SIMPLE_KEYWORDS if kw in task_lower)

    scores = {"simple": simple_score, "medium": medium_score, "complex": complex_score}
    return max(scores, key=scores.get)


def get_local_model(complexity: str) -> str:
    if local_router and hasattr(local_router, "get_model_for_complexity"):
        return local_router.get_model_for_complexity(complexity)
    return LOCAL_MODELS.get(complexity, LOCAL_MODELS["simple"])


def main():
    parser = argparse.ArgumentParser(
        description="Intelligently select best model based on task complexity"
    )
    parser.add_argument("--task", type=str, default="", help="The task to perform")
    parser.add_argument(
        "--complexity",
        choices=["simple", "medium", "complex"],
        help="Task complexity (auto-detected if not provided)",
    )
    parser.add_argument("--offline", action="store_true", help="Force local model")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local models based on complexity when available",
    )
    parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )

    args = parser.parse_args()

    local_available = local_router is not None

    if args.offline:
        model = MODELS["offline"]
        complexity = "offline"
    elif args.local and local_available:
        complexity = (
            args.complexity if args.complexity else detect_complexity(args.task)
        )
        model = get_local_model(complexity)
    else:
        complexity = (
            args.complexity if args.complexity else detect_complexity(args.task)
        )
        model = MODELS[complexity]

    if args.format == "json":
        output = {
            "task": args.task,
            "complexity": args.complexity
            if args.complexity
            else detect_complexity(args.task),
            "offline": args.offline,
            "local": args.local,
            "local_available": local_available,
            "model": model,
        }
        print(json.dumps(output, indent=2))
    else:
        print(model)


if __name__ == "__main__":
    main()
