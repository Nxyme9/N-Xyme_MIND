"""
Cost Tracker MCP — Track AI agent costs and optimize spending

Monitors token usage, detects waste, suggests cheaper alternatives.

Usage:
    tracker = CostTracker()
    tracker.record("ollama", "llama3.2:3b", 100, 50)
    report = tracker.get_report()
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    """A single usage record."""

    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    timestamp: float = field(default_factory=time.time)
    agent: str = ""


# Cost per 1M tokens (USD)
MODEL_COSTS = {
    # Local models (FREE)
    "ollama/llama3.2:3b": {"input": 0.0, "output": 0.0},
    "ollama/qwen2.5-coder:7b": {"input": 0.0, "output": 0.0},
    "ollama/qwen3:8b": {"input": 0.0, "output": 0.0},
    # Cloud models
    "opencode/mimo-v2-pro-free": {"input": 0.0, "output": 0.0},
    "opencode/minimax-m2.5-free": {"input": 0.0, "output": 0.0},
    "openrouter/deepseek/deepseek-r1:free": {"input": 0.0, "output": 0.0},
}


class CostTracker:
    """Track and optimize AI agent costs."""

    def __init__(self):
        self._records: List[UsageRecord] = []
        self._daily_budget: float = 5.0  # USD
        self._monthly_budget: float = 50.0  # USD
        logger.info("CostTracker: Initialized")

    def record(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        agent: str = "",
    ) -> Dict:
        """Record a usage event."""
        cost_key = f"{provider}/{model}"
        costs = MODEL_COSTS.get(cost_key, {"input": 0.0, "output": 0.0})

        cost = (input_tokens / 1_000_000) * costs["input"] + (output_tokens / 1_000_000) * costs[
            "output"
        ]

        record = UsageRecord(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            agent=agent,
        )
        self._records.append(record)

        # Keep last 10000 records
        if len(self._records) > 10000:
            self._records = self._records[-10000:]

        return {
            "cost_usd": cost,
            "is_free": cost == 0.0,
            "provider": provider,
        }

    def get_report(self) -> Dict:
        """Get cost report."""
        total_cost = sum(r.cost_usd for r in self._records)
        total_input = sum(r.input_tokens for r in self._records)
        total_output = sum(r.output_tokens for r in self._records)

        # By provider
        by_provider = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "calls": 0})
        for r in self._records:
            by_provider[r.provider]["cost"] += r.cost_usd
            by_provider[r.provider]["tokens"] += r.input_tokens + r.output_tokens
            by_provider[r.provider]["calls"] += 1

        # By agent
        by_agent = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "calls": 0})
        for r in self._records:
            if r.agent:
                by_agent[r.agent]["cost"] += r.cost_usd
                by_agent[r.agent]["tokens"] += r.input_tokens + r.output_tokens
                by_agent[r.agent]["calls"] += 1

        # Savings from local routing
        local_tokens = sum(
            r.input_tokens + r.output_tokens for r in self._records if "ollama" in r.provider
        )
        cloud_rate = 0.59  # Average cloud cost per 1M tokens
        savings = (local_tokens / 1_000_000) * cloud_rate

        return {
            "total_cost_usd": round(total_cost, 4),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_calls": len(self._records),
            "by_provider": dict(by_provider),
            "by_agent": dict(by_agent),
            "local_percentage": round(local_tokens / (total_input + total_output) * 100, 1)
            if (total_input + total_output) > 0
            else 0,
            "estimated_savings_usd": round(savings, 2),
            "daily_budget": self._daily_budget,
            "monthly_budget": self._monthly_budget,
        }

    def get_optimization_suggestions(self) -> List[str]:
        """Get cost optimization suggestions."""
        suggestions = []

        # Check for expensive models used for simple tasks
        for r in self._records[-100:]:
            if r.cost_usd > 0 and r.input_tokens < 100:
                suggestions.append(
                    f"Consider using local model for short prompts (currently using {r.model})"
                )

        # Check local percentage
        report = self.get_report()
        if report["local_percentage"] < 50:
            suggestions.append("Local routing is below 50% — consider routing more tasks to Ollama")

        return suggestions
