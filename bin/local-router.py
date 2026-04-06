#!/usr/bin/env python3
"""Local Router - Local LLM router with health checking and model selection."""

import argparse
import json
import os
import sys
from typing import Optional

import requests

from model_keywords import (
    SIMPLE_KEYWORDS,
    MEDIUM_KEYWORDS,
    COMPLEX_KEYWORDS,
)


class LocalRouter:
    """Router for local LLM operations with health checking."""

    DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    HEALTH_ENDPOINT = "/api/version"
    MODELS_ENDPOINT = "/api/tags"

    def __init__(self, ollama_url: Optional[str] = None):
        self.ollama_url = ollama_url or self.DEFAULT_OLLAMA_URL

    def classify(self, task: str) -> str:
        """Classify task into simple/medium/complex based on keywords."""
        if not task or not task.strip():
            return "unknown"

        task_lower = task.lower()

        complex_score = sum(1 for kw in COMPLEX_KEYWORDS if kw in task_lower)
        medium_score = sum(1 for kw in MEDIUM_KEYWORDS if kw in task_lower)
        simple_score = sum(1 for kw in SIMPLE_KEYWORDS if kw in task_lower)

        scores = {"simple": simple_score, "medium": medium_score, "complex": complex_score}
        max_score = max(scores.values())

        if max_score == 0:
            return "unknown"

        return max(scores, key=scores.get)

    def is_local_available(self, timeout: float = 2.0) -> bool:
        """Check if Ollama is running and available."""
        try:
            response = requests.get(
                f"{self.ollama_url}{self.HEALTH_ENDPOINT}",
                timeout=timeout
            )
            return response.status_code == 200
        except (requests.RequestException, requests.Timeout):
            return False

    def get_local_models(self) -> list[str]:
        """Get list of available local models from Ollama."""
        ollama_model_env = os.getenv("OLLAMA_MODEL")
        if ollama_model_env:
            return [ollama_model_env]

        try:
            response = requests.get(
                f"{self.ollama_url}{self.MODELS_ENDPOINT}",
                timeout=5.0
            )
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except (requests.RequestException, requests.Timeout):
            pass

        return [self.DEFAULT_MODEL]


def main():
    parser = argparse.ArgumentParser(description="Local LLM Router")
    parser.add_argument("--task", type=str, help="Task to classify")
    parser.add_argument("--health", action="store_true", help="Check Ollama health")
    parser.add_argument("--list-models", action="store_true", help="List available models")
    parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )

    args = parser.parse_args()
    router = LocalRouter()

    if args.health:
        available = router.is_local_available()
        if args.format == "json":
            print(json.dumps({"available": available}))
        else:
            print("Ollama is running" if available else "Ollama is unavailable")
        sys.exit(0 if available else 1)

    if args.list_models:
        models = router.get_local_models()
        if args.format == "json":
            print(json.dumps({"models": models}))
        else:
            for model in models:
                print(model)
        sys.exit(0)

    if args.task:
        classification = router.classify(args.task)
        if args.format == "json":
            print(json.dumps({"task": args.task, "classification": classification}))
        else:
            print(classification)
        sys.exit(0)

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
