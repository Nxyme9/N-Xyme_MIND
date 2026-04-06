"""
Tool Call Collector — Records every tool call and auto-optimizes model selection.

Tracks per-model performance (success rate, latency) across a rolling 100-call window
and provides intelligent model selection based on historical performance.

Usage:
    collector = ToolCallCollector()
    collector.record_call("llama3-groq-tool-use:8b", "native", 150, True, "grep")
    metrics = collector.get_metrics()
    best = collector.get_best_model("coding")
"""

import json
import os
import time
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

# Model hierarchy for fallback order
MODEL_HIERARCHY = [
    "llama3-groq-tool-use:8b",  # Primary - best for tool use
    "qwen2.5-coder:7b",  # Coding specialist
    "qwen2.5:14b",  # Accuracy/reasoning
    "granite3.2:8b",  # Speed
]

# Model capabilities for intelligent routing
MODEL_CAPABILITIES = {
    "llama3-groq-tool-use:8b": ["tool_use", "function_calling", "general"],
    "qwen2.5-coder:7b": ["coding", "code_generation", "debugging"],
    "qwen2.5:14b": ["reasoning", "accuracy", "complex_tasks"],
    "granite3.2:8b": ["speed", "fast_response", "simple_tasks"],
}

# Default metrics file path
METRICS_FILE = Path(__file__).parent.parent / "data" / "tool-metrics.jsonl"


@dataclass
class ToolCall:
    """Single tool call record."""

    timestamp: float
    model: str
    tier: str
    latency_ms: float
    success: bool
    tool_name: str


class ToolCallCollector:
    """
    Records every tool call and provides auto-optimization for model selection.

    Features:
    - Rolling 100-call window per model
    - Success rate tracking
    - Average latency tracking
    - Capability-based model selection
    - Persistent JSONL logging

    Usage:
        collector = ToolCallCollector()
        collector.record_call("llama3-groq-tool-use:8b", "native", 150, True, "grep")
        print(collector.get_metrics())
        print(collector.get_best_model("coding"))
    """

    def __init__(self, metrics_file: Optional[Path] = None):
        """
        Initialize the collector.

        Args:
            metrics_file: Optional custom path for metrics JSONL.
                        Defaults to data/tool-metrics.jsonl
        """
        self._calls: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._metrics_file = metrics_file or METRICS_FILE

        # Ensure metrics file directory exists
        self._metrics_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"ToolCallCollector initialized with metrics file: {self._metrics_file}")

    def record_call(
        self, model: str, tier: str, latency_ms: float, success: bool, tool_name: str
    ) -> None:
        """
        Record a single tool call.

        Args:
            model: Model name (e.g., "llama3-groq-tool-use:8b")
            tier: Call tier ("native", "structured", "prompt", "fallback")
            latency_ms: Response time in milliseconds
            success: Whether the call succeeded
            tool_name: Name of the tool that was called
        """
        call = ToolCall(
            timestamp=time.time(),
            model=model,
            tier=tier,
            latency_ms=latency_ms,
            success=success,
            tool_name=tool_name,
        )

        self._calls[model].append(call)
        self._save_call(call)

        logger.debug(
            f"Recorded call: model={model}, tier={tier}, "
            f"latency={latency_ms}ms, success={success}, tool={tool_name}"
        )

    def _save_call(self, call: ToolCall) -> None:
        """Append call to the metrics JSONL file."""
        try:
            with open(self._metrics_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(call)) + "\n")
        except IOError as e:
            logger.warning(f"Failed to save metrics to {self._metrics_file}: {e}")

    def get_metrics(self) -> Dict:
        """
        Get current performance metrics per model.

        Returns:
            Dict with per-model stats including:
            - call_count: Total calls in rolling window
            - success_rate: Percentage of successful calls
            - avg_latency_ms: Average latency
            - tier_breakdown: Calls per tier
            - tool_breakdown: Calls per tool name
        """
        metrics = {}

        for model, calls in self._calls.items():
            if not calls:
                continue

            call_list = list(calls)
            successes = sum(1 for c in call_list if c.success)

            # Tier breakdown
            tier_counts = defaultdict(int)
            for c in call_list:
                tier_counts[c.tier] += 1

            # Tool breakdown
            tool_counts = defaultdict(int)
            for c in call_list:
                tool_counts[c.tool_name] += 1

            metrics[model] = {
                "call_count": len(call_list),
                "success_rate": round((successes / len(call_list)) * 100, 2),
                "avg_latency_ms": round(sum(c.latency_ms for c in call_list) / len(call_list), 2),
                "successes": successes,
                "failures": len(call_list) - successes,
                "tier_breakdown": dict(tier_counts),
                "tool_breakdown": dict(tool_counts),
            }

        return metrics

    def get_best_model(self, capability: Optional[str] = None) -> Optional[str]:
        """
        Get the best performing model based on historical metrics.

        If capability is specified, filters models that support that capability
        and selects the best among them. Otherwise, selects from all models.

        Args:
            capability: Optional capability filter. Options:
                      - "tool_use", "function_calling", "general"
                      - "coding", "code_generation", "debugging"
                      - "reasoning", "accuracy", "complex_tasks"
                      - "speed", "fast_response", "simple_tasks"

        Returns:
            Best model name based on success rate, or None if no data
        """
        metrics = self.get_metrics()

        if not metrics:
            # No data yet - fall back to hierarchy
            if capability:
                return self._get_model_by_capability(capability)
            return MODEL_HIERARCHY[0]

        # Filter by capability if specified
        candidates = []
        if capability:
            for model in MODEL_HIERARCHY:
                caps = MODEL_CAPABILITIES.get(model, [])
                if capability in caps and model in metrics:
                    candidates.append(model)
        else:
            candidates = [m for m in MODEL_HIERARCHY if m in metrics]

        if not candidates:
            # No matching model with data - fall back to hierarchy
            return self._get_model_by_capability(capability) if capability else MODEL_HIERARCHY[0]

        # Select best by success rate, then by latency
        best = None
        best_score = -1

        for model in candidates:
            model_metrics = metrics[model]
            # Score = success_rate - (latency_penalty / 1000)
            # Higher success rate is better, lower latency is better
            latency_penalty = model_metrics["avg_latency_ms"] / 1000
            score = model_metrics["success_rate"] - latency_penalty

            if score > best_score:
                best_score = score
                best = model

        return best or candidates[0]

    def _get_model_by_capability(self, capability: str) -> Optional[str]:
        """Get model by capability from hierarchy."""
        for model in MODEL_HIERARCHY:
            caps = MODEL_CAPABILITIES.get(model, [])
            if capability in caps:
                return model
        return MODEL_HIERARCHY[0]

    def get_model_status(self) -> Dict:
        """
        Get quick status of all tracked models.

        Returns:
            Dict with model names as keys and status info as values
        """
        metrics = self.get_metrics()
        status = {}

        for model in MODEL_HIERARCHY:
            if model in metrics:
                m = metrics[model]
                status[model] = {
                    "available": True,
                    "success_rate": m["success_rate"],
                    "avg_latency": m["avg_latency_ms"],
                    "calls": m["call_count"],
                }
            else:
                status[model] = {
                    "available": False,
                    "success_rate": None,
                    "avg_latency": None,
                    "calls": 0,
                }

        return status

    def reset_model(self, model: str) -> None:
        """
        Reset metrics for a specific model.

        Args:
            model: Model name to reset
        """
        if model in self._calls:
            self._calls[model].clear()
            logger.info(f"Reset metrics for model: {model}")

    def reset_all(self) -> None:
        """Reset all metrics."""
        self._calls.clear()
        logger.info("Reset all metrics")

    def get_recent_calls(self, model: str, limit: int = 10) -> List[Dict]:
        """
        Get recent calls for a specific model.

        Args:
            model: Model name
            limit: Maximum number of calls to return

        Returns:
            List of recent call records as dicts
        """
        if model not in self._calls:
            return []

        calls = list(self._calls[model])[-limit:]
        return [asdict(c) for c in calls]


# Global singleton instance
_collector: Optional[ToolCallCollector] = None


def get_collector() -> ToolCallCollector:
    """Get the global ToolCallCollector instance."""
    global _collector
    if _collector is None:
        _collector = ToolCallCollector()
    return _collector


# Convenience functions
def record_tool_call(
    model: str, tier: str, latency_ms: float, success: bool, tool_name: str
) -> None:
    """Record a tool call using the global collector."""
    get_collector().record_call(model, tier, latency_ms, success, tool_name)


def get_tool_metrics() -> Dict:
    """Get metrics from the global collector."""
    return get_collector().get_metrics()


def get_best_tool_model(capability: Optional[str] = None) -> Optional[str]:
    """Get the best model for tool calling."""
    return get_collector().get_best_model(capability)
