"""
AI Usage and Cost Tracking Service
Agent 5 - AI Integration & Model Management
"""

import time
import logging
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    GROQ = "groq"
    OPENROUTER = "openrouter"


MODEL_PRICING = {
    ModelProvider.OPENAI: {
        "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03, "unit": "1k_tokens"},
        "gpt-4": {"prompt": 0.03, "completion": 0.06, "unit": "1k_tokens"},
        "gpt-3.5-turbo": {"prompt": 0.001, "completion": 0.002, "unit": "1k_tokens"},
    },
    ModelProvider.ANTHROPIC: {
        "claude-3-opus": {"prompt": 0.015, "completion": 0.075, "unit": "1k_tokens"},
        "claude-3-sonnet": {"prompt": 0.003, "completion": 0.015, "unit": "1k_tokens"},
        "claude-3-haiku": {"prompt": 0.00025, "completion": 0.00125, "unit": "1k_tokens"},
    },
    ModelProvider.OLLAMA: {
        "default": {"prompt": 0.0, "completion": 0.0, "unit": "local"},
    },
    ModelProvider.GROQ: {
        "llama-3-70b": {"prompt": 0.0, "completion": 0.0, "unit": "free"},
        "mixtral-8x7b": {"prompt": 0.0, "completion": 0.0, "unit": "free"},
    },
    ModelProvider.OPENROUTER: {
        "default": {"prompt": 0.001, "completion": 0.002, "unit": "1k_tokens"},
    },
}


@dataclass
class UsageRecord:
    id: str
    user_id: str
    project_id: Optional[str]
    provider: ModelProvider
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    latency_ms: int
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UsageSummary:
    user_id: str
    total_requests: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost: float
    by_provider: Dict[str, Dict[str, int | float]]
    by_model: Dict[str, Dict[str, int | float]]


class CostTracker:
    """Track AI usage and calculate costs"""
    
    def __init__(self):
        self.usage_records: List[UsageRecord] = []
        self._record_id = 0
    
    def calculate_cost(
        self,
        provider: ModelProvider,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """Calculate cost based on provider and model pricing"""
        
        provider_pricing = MODEL_PRICING.get(provider, {})
        
        if model in provider_pricing:
            pricing = provider_pricing[model]
        elif provider == ModelProvider.OPENROUTER:
            pricing = provider_pricing.get("default", {"prompt": 0, "completion": 0})
        else:
            logger.warning(f"No pricing found for {provider.value}/{model}, assuming free")
            return 0.0
        
        if pricing.get("unit") in ("local", "free"):
            return 0.0
        
        prompt_cost = (prompt_tokens / 1000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1000) * pricing["completion"]
        
        return round(prompt_cost + completion_cost, 6)
    
    def record_usage(
        self,
        user_id: str,
        provider: ModelProvider,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
        project_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UsageRecord:
        """Record AI usage and calculate cost"""
        
        total_tokens = prompt_tokens + completion_tokens
        cost = self.calculate_cost(provider, model, prompt_tokens, completion_tokens)
        
        self._record_id += 1
        record = UsageRecord(
            id=f"usr_{self._record_id}",
            user_id=user_id,
            project_id=project_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            latency_ms=latency_ms,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        
        self.usage_records.append(record)
        
        logger.debug(
            f"Recorded usage: {user_id} | {provider.value}/{model} | "
            f"{total_tokens} tokens | ${cost:.4f}"
        )
        
        return record
    
    def get_user_usage(
        self,
        user_id: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> UsageSummary:
        """Get usage summary for a user"""
        
        records = [r for r in self.usage_records if r.user_id == user_id]
        
        if start_time:
            records = [r for r in records if r.timestamp >= start_time]
        if end_time:
            records = [r for r in records if r.timestamp <= end_time]
        
        if not records:
            return UsageSummary(
                user_id=user_id,
                total_requests=0,
                total_prompt_tokens=0,
                total_completion_tokens=0,
                total_cost=0.0,
                by_provider={},
                by_model={}
            )
        
        total_prompt = sum(r.prompt_tokens for r in records)
        total_completion = sum(r.completion_tokens for r in records)
        total_cost = sum(r.cost for r in records)
        
        by_provider: Dict[str, Dict[str, int | float]] = {}
        for record in records:
            provider = record.provider.value
            if provider not in by_provider:
                by_provider[provider] = {
                    "requests": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "cost": 0.0
                }
            by_provider[provider]["requests"] += 1
            by_provider[provider]["prompt_tokens"] += record.prompt_tokens
            by_provider[provider]["completion_tokens"] += record.completion_tokens
            by_provider[provider]["cost"] += record.cost
        
        by_model: Dict[str, Dict[str, int | float]] = {}
        for record in records:
            model = record.model
            if model not in by_model:
                by_model[model] = {
                    "requests": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "cost": 0.0
                }
            by_model[model]["requests"] += 1
            by_model[model]["prompt_tokens"] += record.prompt_tokens
            by_model[model]["completion_tokens"] += record.completion_tokens
            by_model[model]["cost"] += record.cost
        
        return UsageSummary(
            user_id=user_id,
            total_requests=len(records),
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_completion,
            total_cost=round(total_cost, 6),
            by_provider=by_provider,
            by_model=by_model
        )
    
    def get_project_usage(self, project_id: str) -> UsageSummary:
        """Get usage summary for a project"""
        
        records = [r for r in self.usage_records if r.project_id == project_id]
        
        if not records:
            return UsageSummary(
                user_id="",
                total_requests=0,
                total_prompt_tokens=0,
                total_completion_tokens=0,
                total_cost=0.0,
                by_provider={},
                by_model={}
            )
        
        user_ids = set(r.user_id for r in records)
        
        total_prompt = sum(r.prompt_tokens for r in records)
        total_completion = sum(r.completion_tokens for r in records)
        total_cost = sum(r.cost for r in records)
        
        by_provider: Dict[str, Dict[str, int | float]] = {}
        for record in records:
            provider = record.provider.value
            if provider not in by_provider:
                by_provider[provider] = {
                    "requests": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "cost": 0.0
                }
            by_provider[provider]["requests"] += 1
            by_provider[provider]["prompt_tokens"] += record.prompt_tokens
            by_provider[provider]["completion_tokens"] += record.completion_tokens
            by_provider[provider]["cost"] += record.cost
        
        by_model: Dict[str, Dict[str, int | float]] = {}
        for record in records:
            model = record.model
            if model not in by_model:
                by_model[model] = {
                    "requests": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "cost": 0.0
                }
            by_model[model]["requests"] += 1
            by_model[model]["prompt_tokens"] += record.prompt_tokens
            by_model[model]["completion_tokens"] += record.completion_tokens
            by_model[model]["cost"] += record.cost
        
        return UsageSummary(
            user_id=list(user_ids)[0] if user_ids else "",
            total_requests=len(records),
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_completion,
            total_cost=round(total_cost, 6),
            by_provider=by_provider,
            by_model=by_model
        )
    
    def get_recent_records(
        self,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[UsageRecord]:
        """Get recent usage records"""
        
        records = self.usage_records
        
        if user_id:
            records = [r for r in records if r.user_id == user_id]
        
        return records[-limit:]


_global_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Get global cost tracker instance"""
    global _global_cost_tracker
    if _global_cost_tracker is None:
        _global_cost_tracker = CostTracker()
    return _global_cost_tracker
