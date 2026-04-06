"""Proxy Layer — Bulletproof, lightspeed, accurate, self-learning LLM routing."""

from .api_key_pool import api_key_pool, APIKeyPool
from .vpn_ip_pool import vpn_ip_pool, VPNIPPool
from .router_brain import router_brain, RouterBrain
from .cost_optimizer import cost_tracker, CostTracker
from .learning_engine import learning_engine, LearningEngine
from .intelligent_router import intelligent_router, IntelligentRouter
from .health_monitor import health_monitor, HealthMonitor
from .dead_letter_queue import dead_letter_queue, DeadLetterQueue
from .request_validator import request_validator, RequestValidator
from .lru_cache import lru_semantic_cache, LRUSemanticCache
from .connection_pool import connection_pool, ConnectionPool
from .observability import metrics, alerts, MetricsCollector, AlertManager
from .ab_testing import ab_testing, ABTestingFramework, ABTest
from .feedback import feedback_loop, FeedbackLoop
from .stall_detector import stall_detector, StallDetector
from .key_notifier import key_notifier, KeyNotifier
from .dashboard import dashboard, Dashboard
from .agent_preferences import agent_preferences, AgentPreferences

__all__ = [
    "api_key_pool", "APIKeyPool", "vpn_ip_pool", "VPNIPPool",
    "router_brain", "RouterBrain", "cost_tracker", "CostTracker",
    "learning_engine", "LearningEngine", "intelligent_router", "IntelligentRouter",
    "health_monitor", "HealthMonitor", "dead_letter_queue", "DeadLetterQueue",
    "request_validator", "RequestValidator", "lru_semantic_cache", "LRUSemanticCache",
    "connection_pool", "ConnectionPool", "metrics", "alerts",
    "ab_testing", "ABTestingFramework", "feedback_loop", "FeedbackLoop",
    "stall_detector", "StallDetector", "key_notifier", "KeyNotifier",
    "dashboard", "Dashboard", "agent_preferences", "AgentPreferences",
]

import os
import json
from pathlib import Path

# Load API keys from environment variables (single key per provider)
_opencode_key = os.getenv("OPENCODE_API_KEY", "")
_openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
_google_key = os.getenv("GOOGLE_API_KEY", "")
if _opencode_key: api_key_pool.add_key("opencode", _opencode_key, rpm=60)
if _openrouter_key: api_key_pool.add_key("openrouter", _openrouter_key, rpm=60)
if _google_key: api_key_pool.add_key("google", _google_key, rpm=60)

# Load API keys from keys.json (multi-key support)
_keys_file = Path(__file__).parent.parent.parent / "configs" / "api-keys" / "keys.json"
if _keys_file.exists():
    with open(_keys_file) as _f:
        _keys_config = json.load(_f)
    for _provider, _keys in _keys_config.items():
        for _key_info in _keys:
            _key = _key_info["key"]
            if _key and not _key.startswith("${"):  # Skip unresolved env vars
                api_key_pool.add_key(
                    _provider, _key,
                    rpm=_key_info.get("rpm_limit", 60),
                    tpm=_key_info.get("tpm_limit", 100000)
                )

# Add provider health check endpoints
health_monitor.add_provider("opencode", "https://api.opencode.ai/v1/models", interval=30.0)
health_monitor.add_provider("openrouter", "https://openrouter.ai/api/v1/models", interval=30.0)
health_monitor.add_provider("google", "https://generativelanguage.googleapis.com/v1beta/models", interval=30.0)

health_monitor.start_monitoring()
