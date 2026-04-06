"""Unified Intelligent Router — Ties together all routing components."""

import time
import uuid
from typing import Dict, Optional

from .api_key_pool import api_key_pool, APIKeyPool
from .vpn_ip_pool import vpn_ip_pool, VPNIPPool
from .router_brain import router_brain, RouterBrain
from .cost_optimizer import cost_tracker, CostTracker
from .learning_engine import learning_engine, LearningEngine
from .dashboard import dashboard, Dashboard
from .stall_detector import stall_detector
from .key_notifier import key_notifier
from .agent_preferences import agent_preferences, AgentPreferences


class IntelligentRouter:
    """Self-healing, self-optimizing LLM router."""

    def __init__(self):
        self.key_pool = api_key_pool
        self.ip_pool = vpn_ip_pool
        self.brain = router_brain
        self.cost = cost_tracker
        self.learning = learning_engine
        self.prefs = agent_preferences
        self._request_count = 0

    def select_route(
        self,
        prompt: str,
        system_prompt: str = "",
        agent_type: str = "",
        session_id: str = "",
    ) -> dict:
        """Select optimal route for a request."""
        start = time.time()
        if not session_id:
            session_id = str(uuid.uuid4())[:8]

        # 1. Analyze request with router brain
        analysis = self.brain.analyze_request(prompt, system_prompt, agent_type)

        # 2. Get best API key
        provider = "opencode"
        key = self.key_pool.get_best_key(provider)

        # 3. Get best VPN IP (rotate per request)
        ip = self.ip_pool.get_best_ip()

        # 4. Select best model: BRAIN FIRST, then learned, then preferences as fallbacks
        # Priority: analysis.best_model → learned_model → preferences (NOT override!)
        selected_model = analysis.get("best_model")
        selection_reason = "brain"

        # Get agent preferences early (needed for learning check)
        preferred = self.prefs.get_preferred_models(agent_type, session_id)
        avoided = self.prefs.get_avoided_models(agent_type)

        # Fallback 1: Learning engine (only if brain didn't pick one)
        learned_model = self.learning.get_best_model_for(
            ",".join(analysis["categories"]), analysis["complexity"]
        )
        if not selected_model and learned_model and learned_model not in avoided:
            selected_model = learned_model
            selection_reason = "learning"

        # Fallback 2: Agent preferences (only if both brain and learning failed)
        if not selected_model and preferred:
            for model, score in sorted(
                analysis.get("model_scores", {}).items(), key=lambda x: -x[1]
            ):
                if model in preferred and model not in avoided:
                    selected_model = model
                    selection_reason = "preferences"
                    break

        # Final safety: if still no model, use default
        if not selected_model:
            selected_model = "minimax-m2.5"
            selection_reason = "default"

        route = {
            "model": selected_model,
            "selection_reason": selection_reason,  # Track which layer won
            "provider": provider,
            "api_key": key.key[:20] + "..." if key else None,
            "vpn_ip": f"{ip.host}:{ip.port}" if ip else None,
            "analysis": analysis,
            "selection_time_ms": round((time.time() - start) * 1000, 1),
            "agent_type": agent_type,
            "session_id": session_id,
        }

        # Record in dashboard
        dashboard.record_request(
            agent_type,
            session_id,
            selected_model,
            provider,
            route["vpn_ip"],
            route["selection_time_ms"],
            True,
        )

        # Record key usage
        if key:
            key_notifier.record_usage(key.key[:20], requests=1, tokens=len(prompt))

        return route

    def record_success(
        self, route: dict, input_tokens: int, output_tokens: int, latency_ms: float
    ) -> None:
        """Record successful request."""
        self._request_count += 1
        if route.get("vpn_ip"):
            for ip in self.ip_pool._ips:
                if f"{ip.host}:{ip.port}" == route["vpn_ip"]:
                    self.ip_pool.record_success(ip, latency_ms)
                    break
        self.cost.record_usage(
            route["model"], input_tokens, output_tokens, latency_ms, success=True
        )
        prompt_hash = hash(str(route.get("analysis", {}).get("categories", [])))
        self.learning.record_outcome(
            prompt_hash=prompt_hash,
            categories=",".join(route.get("analysis", {}).get("categories", [])),
            complexity=route.get("analysis", {}).get("complexity", "medium"),
            model=route["model"],
            provider=route["provider"],
            ip=route.get("vpn_ip", ""),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            success=True,
            quality_score=0.9,
            cost=0.0,
        )
        dashboard.record_request(
            route.get("agent_type", ""),
            route.get("session_id", ""),
            route["model"],
            route["provider"],
            route.get("vpn_ip", ""),
            latency_ms,
            True,
        )

    def record_failure(
        self, route: dict, error_type: str, latency_ms: float = 0
    ) -> None:
        """Record failed request."""
        self._request_count += 1
        if route.get("vpn_ip"):
            for ip in self.ip_pool._ips:
                if f"{ip.host}:{ip.port}" == route["vpn_ip"]:
                    self.ip_pool.record_failure(ip, error_type)
                    break
        self.cost.record_usage(route["model"], 0, 0, latency_ms, success=False)
        prompt_hash = hash(str(route.get("analysis", {}).get("categories", [])))
        self.learning.record_outcome(
            prompt_hash=prompt_hash,
            categories=",".join(route.get("analysis", {}).get("categories", [])),
            complexity=route.get("analysis", {}).get("complexity", "medium"),
            model=route["model"],
            provider=route["provider"],
            ip=route.get("vpn_ip", ""),
            input_tokens=0,
            output_tokens=0,
            latency_ms=latency_ms,
            success=False,
            error_type=error_type,
            cost=0.0,
        )
        dashboard.record_request(
            route.get("agent_type", ""),
            route.get("session_id", ""),
            route["model"],
            route["provider"],
            route.get("vpn_ip", ""),
            latency_ms,
            False,
            error_type,
        )

    def get_status(self) -> dict:
        """Get full router status."""
        return {
            "total_requests": self._request_count,
            "api_keys": {
                p: self.key_pool.get_pool_status(p)
                for p in self.key_pool.get_all_providers()
            },
            "vpn_ips": self.ip_pool.get_pool_status(),
            "learning": self.learning.get_stats(),
            "cost": self.cost.get_all_stats(),
            "dashboard": dashboard.get_status(),
            "agent_preferences": {k: v for k, v in self.prefs._preferences.items()},
        }


# Global instance
intelligent_router = IntelligentRouter()
