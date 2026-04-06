"""Hybrid Routing Strategy — Local-first, cloud-fallback LLM routing.

Implements intelligent routing between local and cloud models:
- Simple tasks → Local small model (Llama 3.2 3B)
- Complex reasoning → Local medium model (Llama 3.2 8B)
- Creative tasks → Cloud model (OpenCode Zen)
- Fallback → Next available model in priority chain

Cost-aware routing: prefer local when quality is sufficient.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ModelTier(str, Enum):
    """Model tiers for routing."""

    LOCAL_SMALL = "local_small"  # Llama 3.2 1B/3B
    LOCAL_MEDIUM = "local_medium"  # Llama 3.2 8B, Mistral 7B
    CLOUD_FREE = "cloud_free"  # OpenCode Zen free models
    CLOUD_PREMIUM = "cloud_premium"  # Paid cloud models (future)


class TaskComplexity(str, Enum):
    """Task complexity levels."""

    SIMPLE = "simple"  # Formatting, summarization, simple Q&A
    MEDIUM = "medium"  # Code generation, analysis, multi-step
    COMPLEX = "complex"  # Architecture, debugging, creative


@dataclass
class RoutingDecision:
    """Decision about which model to use."""

    task_complexity: TaskComplexity
    selected_model: str
    selected_tier: ModelTier
    reason: str
    fallback_models: list[str] = field(default_factory=list)
    estimated_cost_usd: float = 0.0
    estimated_latency_ms: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class ModelCapability:
    """Capabilities of a model."""

    name: str
    tier: ModelTier
    complexity_rating: float  # 0-1, how complex tasks it can handle
    cost_per_1m_tokens: float
    avg_latency_ms: float
    context_window: int
    is_available: bool = True
    is_local: bool = True


class HybridRouter:
    """Hybrid LLM routing with local-first, cloud-fallback strategy."""

    def __init__(self):
        """Initialize hybrid router."""
        self.models: dict[str, ModelCapability] = {}
        self._routing_history: list[RoutingDecision] = []
        self._model_performance: dict[str, dict[str, float]] = {}
        self._initialize_models()

    def _initialize_models(self) -> None:
        """Initialize model capabilities."""
        # Local models
        self.models["llama-3.2-1b"] = ModelCapability(
            name="llama-3.2-1b",
            tier=ModelTier.LOCAL_SMALL,
            complexity_rating=0.3,
            cost_per_1m_tokens=0.0,
            avg_latency_ms=500,
            context_window=131072,
            is_local=True,
        )
        self.models["llama-3.2-3b"] = ModelCapability(
            name="llama-3.2-3b",
            tier=ModelTier.LOCAL_SMALL,
            complexity_rating=0.5,
            cost_per_1m_tokens=0.0,
            avg_latency_ms=800,
            context_window=131072,
            is_local=True,
        )
        self.models["llama-3.2-8b"] = ModelCapability(
            name="llama-3.2-8b",
            tier=ModelTier.LOCAL_MEDIUM,
            complexity_rating=0.7,
            cost_per_1m_tokens=0.0,
            avg_latency_ms=1500,
            context_window=131072,
            is_local=True,
        )
        self.models["mistral-7b"] = ModelCapability(
            name="mistral-7b",
            tier=ModelTier.LOCAL_MEDIUM,
            complexity_rating=0.65,
            cost_per_1m_tokens=0.0,
            avg_latency_ms=1200,
            context_window=32768,
            is_local=True,
        )
        self.models["phi-3-mini"] = ModelCapability(
            name="phi-3-mini",
            tier=ModelTier.LOCAL_SMALL,
            complexity_rating=0.45,
            cost_per_1m_tokens=0.0,
            avg_latency_ms=600,
            context_window=128000,
            is_local=True,
        )

        # Cloud models (OpenCode Zen)
        self.models["opencode/qwen3.6-flash-free"] = ModelCapability(
            name="opencode/qwen3.6-flash-free",
            tier=ModelTier.CLOUD_FREE,
            complexity_rating=0.6,
            cost_per_1m_tokens=0.0,
            avg_latency_ms=2000,
            context_window=32768,
            is_local=False,
        )
        self.models["opencode/qwen3.6-coder-free"] = ModelCapability(
            name="opencode/qwen3.6-coder-free",
            tier=ModelTier.CLOUD_FREE,
            complexity_rating=0.8,
            cost_per_1m_tokens=0.0,
            avg_latency_ms=3000,
            context_window=32768,
            is_local=False,
        )
        self.models["opencode/qwen3.6-plus-free"] = ModelCapability(
            name="opencode/qwen3.6-plus-free",
            tier=ModelTier.CLOUD_FREE,
            complexity_rating=0.85,
            cost_per_1m_tokens=0.0,
            avg_latency_ms=4000,
            context_window=32768,
            is_local=False,
        )

    def route_task(
        self,
        task_description: str,
        complexity: TaskComplexity | None = None,
        prefer_local: bool = True,
        max_cost_usd: float = 0.0,
    ) -> RoutingDecision:
        """Route a task to the optimal model.

        Args:
            task_description: Description of the task.
            complexity: Task complexity (auto-detected if None).
            prefer_local: Prefer local models over cloud.
            max_cost_usd: Maximum acceptable cost.

        Returns:
            RoutingDecision with selected model and fallbacks.
        """
        # Auto-detect complexity if not provided
        if complexity is None:
            complexity = self._detect_complexity(task_description)

        # Determine required capability
        required_capability = {
            TaskComplexity.SIMPLE: 0.4,
            TaskComplexity.MEDIUM: 0.6,
            TaskComplexity.COMPLEX: 0.8,
        }[complexity]

        # Find suitable models
        suitable_models = []
        for name, cap in self.models.items():
            if not cap.is_available:
                continue
            if cap.complexity_rating < required_capability:
                continue
            if cap.cost_per_1m_tokens > max_cost_usd and max_cost_usd > 0:
                continue
            suitable_models.append((name, cap))

        if not suitable_models:
            # Fallback to best available model
            best_model = max(
                self.models.values(),
                key=lambda m: m.complexity_rating if m.is_available else -1,
            )
            suitable_models = [(best_model.name, best_model)]

        # Sort by preference (local first, then by performance)
        if prefer_local:
            suitable_models.sort(
                key=lambda x: (
                    0 if x[1].is_local else 1,  # Local first
                    -self._get_performance_score(x[0]),  # Better performance first
                    x[1].cost_per_1m_tokens,  # Lower cost first
                )
            )
        else:
            suitable_models.sort(
                key=lambda x: (
                    -self._get_performance_score(x[0]),
                    x[1].cost_per_1m_tokens,
                )
            )

        selected_name, selected_cap = suitable_models[0]
        fallback_names = [name for name, _ in suitable_models[1:3]]

        reason = self._explain_selection(
            selected_name, selected_cap, complexity, prefer_local
        )

        decision = RoutingDecision(
            task_complexity=complexity,
            selected_model=selected_name,
            selected_tier=selected_cap.tier,
            reason=reason,
            fallback_models=fallback_names,
            estimated_cost_usd=selected_cap.cost_per_1m_tokens,
            estimated_latency_ms=selected_cap.avg_latency_ms,
        )

        self._routing_history.append(decision)
        return decision

    def record_performance(
        self,
        model_name: str,
        task_complexity: TaskComplexity,
        success: bool,
        latency_ms: float,
    ) -> None:
        """Record model performance for learning.

        Args:
            model_name: Model that was used.
            task_complexity: Task complexity.
            success: Whether the task was successful.
            latency_ms: Actual latency.
        """
        if model_name not in self._model_performance:
            self._model_performance[model_name] = {
                "total_tasks": 0,
                "successful_tasks": 0,
                "total_latency_ms": 0.0,
                "by_complexity": {},
            }

        perf = self._model_performance[model_name]
        perf["total_tasks"] += 1
        if success:
            perf["successful_tasks"] += 1
        perf["total_latency_ms"] += latency_ms

        # Track by complexity
        comp_key = task_complexity.value
        if comp_key not in perf["by_complexity"]:
            perf["by_complexity"][comp_key] = {
                "total": 0,
                "successful": 0,
                "total_latency": 0.0,
            }
        comp_perf = perf["by_complexity"][comp_key]
        comp_perf["total"] += 1
        if success:
            comp_perf["successful"] += 1
        comp_perf["total_latency"] += latency_ms

        # Update model capability
        if model_name in self.models:
            self.models[model_name].avg_latency_ms = perf["total_latency_ms"] / max(
                1, perf["total_tasks"]
            )

    def _detect_complexity(self, task_description: str) -> TaskComplexity:
        """Auto-detect task complexity from description.

        Args:
            task_description: Task description.

        Returns:
            Detected TaskComplexity.
        """
        desc_lower = task_description.lower()

        # Complex indicators
        complex_indicators = [
            "architecture",
            "design",
            "refactor",
            "debug",
            "optimize",
            "implement",
            "create",
            "build",
            "system",
            "pipeline",
            "orchestration",
            "integration",
            "migration",
        ]
        complex_count = sum(1 for ind in complex_indicators if ind in desc_lower)

        # Simple indicators
        simple_indicators = [
            "what is",
            "explain",
            "summarize",
            "format",
            "list",
            "simple",
            "basic",
            "quick",
            "short",
        ]
        simple_count = sum(1 for ind in simple_indicators if ind in desc_lower)

        if complex_count >= 2 or len(desc_lower.split()) > 50:
            return TaskComplexity.COMPLEX
        elif simple_count >= 1 and complex_count == 0:
            return TaskComplexity.SIMPLE
        else:
            return TaskComplexity.MEDIUM

    def _get_performance_score(self, model_name: str) -> float:
        """Get performance score for a model.

        Args:
            model_name: Model name.

        Returns:
            Performance score (0-1).
        """
        perf = self._model_performance.get(model_name)
        if not perf or perf["total_tasks"] == 0:
            return 0.5  # Default score

        success_rate = perf["successful_tasks"] / perf["total_tasks"]
        return success_rate

    def _explain_selection(
        self,
        model_name: str,
        capability: ModelCapability,
        complexity: TaskComplexity,
        prefer_local: bool,
    ) -> str:
        """Explain why a model was selected.

        Args:
            model_name: Selected model.
            capability: Model capability.
            complexity: Task complexity.
            prefer_local: Whether local was preferred.

        Returns:
            Explanation string.
        """
        parts = []
        if capability.is_local:
            parts.append("Local model (no API cost)")
        else:
            parts.append("Cloud model")

        parts.append(f"Complexity rating: {capability.complexity_rating:.2f}")
        parts.append(f"Task: {complexity.value}")

        if prefer_local and capability.is_local:
            parts.append("Preferred local model")

        return ", ".join(parts)

    def get_stats(self) -> dict[str, Any]:
        """Get routing statistics."""
        by_tier: dict[str, int] = {}
        by_complexity: dict[str, int] = {}
        for decision in self._routing_history:
            by_tier[decision.selected_tier.value] = (
                by_tier.get(decision.selected_tier.value, 0) + 1
            )
            by_complexity[decision.task_complexity.value] = (
                by_complexity.get(decision.task_complexity.value, 0) + 1
            )

        return {
            "total_routings": len(self._routing_history),
            "by_tier": by_tier,
            "by_complexity": by_complexity,
            "model_performance": {
                name: {
                    "success_rate": round(
                        perf["successful_tasks"] / max(1, perf["total_tasks"]), 4
                    ),
                    "avg_latency_ms": round(
                        perf["total_latency_ms"] / max(1, perf["total_tasks"]), 2
                    ),
                    "total_tasks": perf["total_tasks"],
                }
                for name, perf in self._model_performance.items()
            },
        }


# Global singleton
_hybrid_router = HybridRouter()


def route_task(
    task_description: str,
    complexity: TaskComplexity | None = None,
    prefer_local: bool = True,
    max_cost_usd: float = 0.0,
) -> RoutingDecision:
    """Convenience function to route a task."""
    return _hybrid_router.route_task(
        task_description, complexity, prefer_local, max_cost_usd
    )


def record_performance(
    model_name: str,
    task_complexity: TaskComplexity,
    success: bool,
    latency_ms: float,
) -> None:
    """Convenience function to record performance."""
    _hybrid_router.record_performance(model_name, task_complexity, success, latency_ms)
