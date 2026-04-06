"""
Cost Optimization Engine — Track cost per token, select cheapest route.
"""

import threading
import time
from typing import Dict, Optional

MODEL_COSTS = {
    "qwen3.6-plus": {"input": 0.0, "output": 0.0, "provider": "opencode"},
    "qwen3-coder": {"input": 0.0, "output": 0.0, "provider": "opencode"},
    "nemotron-30b": {"input": 0.0, "output": 0.0, "provider": "openrouter"},
    "nemotron-12b": {"input": 0.0, "output": 0.0, "provider": "openrouter"},
    "minimax-m2.5": {"input": 0.0, "output": 0.0, "provider": "opencode"},
}


class CostTracker:
    """Tracks cost and usage per model."""

    def __init__(self):
        self._usage: Dict[str, dict] = {}
        self._lock = threading.Lock()

    def record_usage(self, model: str, input_tokens: int, output_tokens: int, latency_ms: float, success: bool) -> None:
        with self._lock:
            if model not in self._usage:
                self._usage[model] = {"total_requests": 0, "total_input_tokens": 0, "total_output_tokens": 0,
                    "total_latency_ms": 0.0, "successful_requests": 0, "failed_requests": 0,
                    "avg_latency_ms": 0.0, "success_rate": 1.0, "last_used": 0.0}
            u = self._usage[model]
            u["total_requests"] += 1
            u["total_input_tokens"] += input_tokens
            u["total_output_tokens"] += output_tokens
            u["total_latency_ms"] += latency_ms
            u["avg_latency_ms"] = u["total_latency_ms"] / u["total_requests"]
            if success: u["successful_requests"] += 1
            else: u["failed_requests"] += 1
            u["success_rate"] = u["successful_requests"] / u["total_requests"]
            u["last_used"] = time.time()

    def get_model_stats(self, model: str) -> dict:
        with self._lock:
            u = self._usage.get(model, {})
            cost = MODEL_COSTS.get(model, {"input": 0.0, "output": 0.0})
            total_cost = (u.get("total_input_tokens", 0) * cost["input"] + u.get("total_output_tokens", 0) * cost["output"]) / 1_000_000
            return {"model": model, "cost_per_1m_input": cost["input"], "cost_per_1m_output": cost["output"],
                "estimated_total_cost": round(total_cost, 6), "total_requests": u.get("total_requests", 0),
                "success_rate": round(u.get("success_rate", 1.0), 3), "avg_latency_ms": round(u.get("avg_latency_ms", 0.0), 1),
                "total_tokens": u.get("total_input_tokens", 0) + u.get("total_output_tokens", 0)}

    def get_all_stats(self) -> dict:
        return {model: self.get_model_stats(model) for model in MODEL_COSTS}

    def select_cheapest(self, min_quality: float = 0.0) -> Optional[str]:
        candidates = []
        for model in MODEL_COSTS:
            stats = self.get_model_stats(model)
            score = stats["success_rate"] * 0.6 + (1.0 / (1.0 + stats["avg_latency_ms"] / 1000)) * 0.4
            if score >= min_quality:
                candidates.append((model, score))
        if not candidates: return None
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]


# Global instance
cost_tracker = CostTracker()
