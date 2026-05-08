#!/usr/bin/env python3
"""Model Router - Keyword-based routing utility for selecting optimal models."""

import argparse
import json
import os
import sys
from typing import Dict, Optional
import importlib.util

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from model_keywords import CATEGORIES, ESCALATION_PATHS

# Import LocalRouter from local-router.py (hyphenated filename requires importlib)
_local_router_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local-router.py")
spec = importlib.util.spec_from_file_location("local_router", _local_router_path)
_local_router_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_local_router_module)
LocalRouter = _local_router_module.LocalRouter


class ModelRouter:
    """Routes tasks to optimal models based on keyword matching."""

    CATEGORIES = CATEGORIES
    ESCALATION_PATHS = ESCALATION_PATHS

    def __init__(self, custom_rules: Optional[Dict] = None):
        """Initialize router with routing rules.

        Args:
            custom_rules: Optional custom routing rules to override defaults.
        """
        self._rules = custom_rules or {}
        self.local_router = LocalRouter()
        self._initialize_defaults()

    def _initialize_defaults(self):
        """Set up default model mappings from environment variables."""
        self._rules.setdefault("models", {})
        self._rules["models"].setdefault(
            "simple", os.getenv("FALLBACK_MODEL", "opencode/minimax-m2.5-free")
        )
        self._rules["models"].setdefault(
            "coding", os.getenv("DEFAULT_CODING_MODEL", "qwen2.5-coder:7b")
        )
        self._rules["models"].setdefault(
            "reasoning", os.getenv("PRIMARY_MODEL", "opencode/qwen3.6-plus-free")
        )
        self._rules["models"].setdefault(
            "creative", os.getenv("PRIMARY_MODEL", "opencode/qwen3.6-plus-free")
        )
        self._rules["models"].setdefault(
            "analysis", os.getenv("PRIMARY_MODEL", "opencode/qwen3.6-plus-free")
        )

        self._rules.setdefault("categories", self.CATEGORIES)
        self._rules.setdefault("escalation_paths", self.ESCALATION_PATHS)

    def _calculate_category_score(self, task: str, category: str) -> float:
        """Calculate keyword match score for a category.

        Args:
            task: The task text to analyze.
            category: The category to score against.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        task_lower = task.lower()
        keywords = self._rules.get("categories", {}).get(category, [])

        if not keywords:
            return 0.0

        matches = sum(1 for kw in keywords if kw in task_lower)
        max_score = len(keywords)

        return min(matches / max_score * 5, 1.0)

    def route(self, task: str) -> Dict:
        """Route a task to the optimal model.

        Args:
            task: The task description text.

        Returns:
            Dictionary with 'model', 'confidence', and 'reason' keys.
        """
        if not task or not task.strip():
            return {
                "model": self._rules.get("models", {}).get("simple"),
                "confidence": 0.0,
                "reason": "Empty task, defaulting to simple model",
                "local": False,
            }

        if self.local_router.is_local_available():
            complexity = self.local_router.classify(task)
            if complexity in ("simple", "medium"):
                local_model = self._rules.get("models", {}).get(
                    "simple" if complexity == "simple" else "coding",
                    "qwen2.5-coder:7b"
                )
                return {
                    "model": local_model,
                    "confidence": 0.8 if complexity == "simple" else 0.6,
                    "reason": f"Local routing: {complexity} complexity task routed to local model",
                    "local": True,
                }

        category_scores = {}
        for category in self.CATEGORIES.keys():
            category_scores[category] = self._calculate_category_score(task, category)

        best_category = max(category_scores, key=category_scores.get)
        confidence = category_scores[best_category]

        model = self._rules.get("models", {}).get(
            best_category, "opencode/minimax-m2.5-free"
        )

        reason = f"Matched '{best_category}' category with {len([kw for kw in self.CATEGORIES[best_category] if kw in task.lower()])} keyword(s)"

        if confidence < 0.6:
            reason += " (low confidence - escalation recommended)"

        return {"model": model, "confidence": round(confidence, 3), "reason": reason, "local": False}

    def escalate(self, task: str, previous_model: str) -> Dict:
        """Escalate to a more capable model.

        Args:
            task: The task description.
            previous_model: The model that was previously used.

        Returns:
            Dictionary with 'model', 'confidence', and 'reason' keys.
        """
        current = self.route(task)

        current_category = None
        for cat, model in self._rules.get("models", {}).items():
            if model == previous_model:
                current_category = cat
                break

        if current_category is None:
            current_category = "simple"

        next_category = self.ESCALATION_PATHS.get(current_category, "reasoning")

        escalated_model = self._rules.get("models", {}).get(next_category)

        return {
            "model": escalated_model,
            "confidence": min(current["confidence"] + 0.2, 1.0),
            "reason": f"Escalated from {current_category} to {next_category} category",
        }

    def get_routing_rules(self) -> Dict:
        """Get the current routing configuration.

        Returns:
            Dictionary containing routing rules and model mappings.
        """
        local_available = self.local_router.is_local_available()
        local_models = self.local_router.get_local_models() if local_available else []
        return {
            "categories": self._rules.get("categories", self.CATEGORIES),
            "models": self._rules.get("models", {}),
            "escalation_paths": self._rules.get(
                "escalation_paths", self.ESCALATION_PATHS
            ),
            "local": {
                "available": local_available,
                "models": local_models,
                "simple": local_models[0] if local_models else None,
                "medium": local_models[0] if local_models else None,
            },
        }


def main():
    """Main entry point for CLI interface."""
    parser = argparse.ArgumentParser(
        description="Route tasks to optimal models based on keyword matching",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--task", type=str, default="", help="The task to route to optimal model"
    )
    parser.add_argument(
        "--escalate",
        action="store_true",
        help="Escalate from previous model to more capable",
    )
    parser.add_argument(
        "--model", type=str, default="", help="Previous model (used with --escalate)"
    )
    parser.add_argument(
        "--rules", action="store_true", help="Show routing rules and exit"
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()

    router = ModelRouter()

    if args.rules:
        rules = router.get_routing_rules()
        if args.format == "json":
            print(json.dumps(rules, indent=2))
        else:
            print("=== ROUTING RULES ===\n")
            print("Categories & Keywords:")
            for cat, keywords in rules["categories"].items():
                print(f"  {cat}: {', '.join(keywords[:5])}...")
            print("\nModel Mappings:")
            for cat, model in rules["models"].items():
                print(f"  {cat} -> {model}")
            print("\nEscalation Paths:")
            for from_cat, to_cat in rules["escalation_paths"].items():
                print(f"  {from_cat} -> {to_cat}")
            print("\nLocal Models:")
            local = rules.get("local", {})
            print(f"  Available: {local.get('available', False)}")
            if local.get("models"):
                print(f"  Models: {', '.join(local['models'])}")
                print(f"  Simple: {local.get('simple', 'N/A')}")
                print(f"  Medium: {local.get('medium', 'N/A')}")
            else:
                print("  No local models available (Ollama not running)")
        return

    if not args.task:
        parser.print_help()
        return

    if args.escalate:
        if not args.model:
            print("Error: --model required when using --escalate", file=sys.stderr)
            sys.exit(1)
        result = router.escalate(args.task, args.model)
    else:
        result = router.route(args.task)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"Model: {result['model']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Reason: {result['reason']}")


if __name__ == "__main__":
    main()
