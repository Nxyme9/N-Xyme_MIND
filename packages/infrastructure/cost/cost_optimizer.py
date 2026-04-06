"""
Cost Optimizer — Switch to cheaper models when possible (ported from MIND)

Automatically routes requests to the cheapest available model that can handle the task.

Usage:
    optimizer = CostOptimizer()
    model = optimizer.select_model("simple question")
    # Returns "ollama/llama3.2:3b" (cheapest)
    model = optimizer.select_model("complex architecture design")
    # Returns "opencode/mimo-v2-pro-free" (best quality)
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModelTier:
    """Model tier with cost and capability."""

    name: str
    model: str
    cost_per_1k_tokens: float
    quality: int  # 1-10
    speed: int  # 1-10
    max_context: int
    use_cases: List[str]


# Model tiers sorted by cost (cheapest first)
MODEL_TIERS = [
    ModelTier(
        name="free_local_fast",
        model="ollama/llama3.2:3b",
        cost_per_1k_tokens=0.0,
        quality=6,
        speed=10,
        max_context=4096,
        use_cases=["simple questions", "quick lookups", "formatting"],
    ),
    ModelTier(
        name="free_local_coding",
        model="ollama/qwen2.5-coder:7b",
        cost_per_1k_tokens=0.0,
        quality=7,
        speed=8,
        max_context=32768,
        use_cases=["coding", "refactoring", "code review"],
    ),
    ModelTier(
        name="free_local_reasoning",
        model="ollama/qwen3:8b",
        cost_per_1k_tokens=0.0,
        quality=7,
        speed=7,
        max_context=32768,
        use_cases=["reasoning", "analysis", "planning"],
    ),
    ModelTier(
        name="free_cloud",
        model="opencode/minimax-m2.5-free",
        cost_per_1k_tokens=0.0,
        quality=8,
        speed=6,
        max_context=128000,
        use_cases=["complex tasks", "long context", "multi-step"],
    ),
    ModelTier(
        name="premium_cloud",
        model="opencode/mimo-v2-pro-free",
        cost_per_1k_tokens=0.0,
        quality=9,
        speed=5,
        max_context=128000,
        use_cases=["architecture", "system design", "critical decisions"],
    ),
]


class CostOptimizer:
    """Select cheapest model that can handle the task."""

    def __init__(self):
        self.tiers = MODEL_TIERS
        self._usage: Dict[str, int] = {}
        logger.info(f"CostOptimizer: Initialized ({len(self.tiers)} tiers)")

    def select_model(
        self,
        task_description: str,
        min_quality: int = 5,
        prefer_local: bool = True,
    ) -> str:
        """Select optimal model for task."""
        task_lower = task_description.lower()

        # Detect task type
        task_type = self._detect_task_type(task_lower)

        # Filter tiers by quality
        candidates = [t for t in self.tiers if t.quality >= min_quality]

        # Prefer local if requested
        if prefer_local:
            local = [t for t in candidates if "ollama" in t.model]
            if local:
                candidates = local

        # Match by use case
        for tier in candidates:
            for use_case in tier.use_cases:
                if use_case in task_type:
                    self._usage[tier.model] = self._usage.get(tier.model, 0) + 1
                    return tier.model

        # Default: cheapest that meets quality
        if candidates:
            best = min(candidates, key=lambda t: t.cost_per_1k_tokens)
            self._usage[best.model] = self._usage.get(best.model, 0) + 1
            return best.model

        return "ollama/llama3.2:3b"  # Fallback

    def _detect_task_type(self, text: str) -> List[str]:
        """Detect task type from description."""
        types = []

        if any(w in text for w in ["code", "function", "class", "implement", "debug"]):
            types.append("coding")
        if any(w in text for w in ["analyze", "reason", "think", "explain", "why"]):
            types.append("reasoning")
        if any(w in text for w in ["simple", "quick", "what is", "define"]):
            types.append("simple questions")
        if any(w in text for w in ["architecture", "design", "plan", "system"]):
            types.append("architecture")
        if any(w in text for w in ["review", "check", "validate", "test"]):
            types.append("code review")

        return types or ["simple questions"]

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        total = sum(self._usage.values())
        return {
            "total_calls": total,
            "by_model": {
                model: {
                    "calls": count,
                    "percentage": round(count / total * 100, 1) if total > 0 else 0,
                }
                for model, count in self._usage.items()
            },
        }
