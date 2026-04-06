"""Unified Intelligent Router — Ties together all routing components."""

import json
import os
import sys
import time
import uuid
from pathlib import Path
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
from .health_monitor import health_monitor, HealthMonitor
from .feedback import feedback_loop, FeedbackLoop


class IntelligentRouter:
    """Self-healing, self-optimizing LLM router."""

    def __init__(self):
        self.key_pool = api_key_pool
        self.ip_pool = vpn_ip_pool
        self.brain = router_brain
        self.cost = cost_tracker
        self.learning = learning_engine
        self.prefs = agent_preferences
        self.health = health_monitor
        self.feedback = feedback_loop
        self.stall = stall_detector
        self._request_count = 0
        
        # Cache config at startup to avoid reloading every request
        self._config_cache: dict | None = None
        self._config_cache_time: float = 0
        self._config_cache_ttl: float = 300  # 5 minutes TTL

    def _get_config(self) -> dict:
        """Get config with caching."""
        import time as time_module
        current_time = time_module.time()
        
        # Return cached config if still valid
        if self._config_cache and (current_time - self._config_cache_time) < self._config_cache_ttl:
            return self._config_cache
        
        # Load fresh config
        config_path = Path("opencode.json")
        config = {}
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
            except Exception as e:
                print(f"[Router] Config load error: {e}", file=sys.stderr)
        
        self._config_cache = config
        self._config_cache_time = current_time
        return config

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

        # ============================================================
        # STEP 0: CHECK AGENT CONFIG PREFERENCE (Hybrid Approach)
        # Respect opencode.json router_override.prefer as primary
        # ============================================================
        config_preferred_model = None
        config_fallback_order = []

        # Use cached config
        config = self._get_config()
        agent_config = config.get("agent", {}).get(agent_type, {})
        router_override = agent_config.get("router_override", {})
        config_preferred_model = router_override.get("prefer")
        config_fallback_order = router_override.get("fallback_order", [])

        # If config preference is set, use it (skip brain analysis)
        selected_model = None
        selection_reason = ""
        analysis = {"categories": [], "complexity": "unknown", "model_scores": {}}
        preferred = []
        avoided = []

        if config_preferred_model:
            # Use config preference directly, with fallback chain
            selected_model = config_preferred_model
            selection_reason = "config_prefer"
            
            # Check if preferred model is healthy; if not, use fallback_order
            model_provider_map = {
                "mimo-v2-pro": "opencode", "mimo-v2-omni": "opencode",
                "minimax-m2.5": "opencode", "qwen3.6-plus": "opencode",
                "qwen3-coder": "opencode", "kimi-k2.5": "opencode",
            }
            provider = model_provider_map.get(config_preferred_model.replace("opencode/", "").replace("-free", ""), "opencode")
            
            if not self.health.is_provider_healthy(provider):
                # Provider unhealthy - try fallback_order from config
                for fallback_model in config_fallback_order:
                    fallback_provider = model_provider_map.get(fallback_model.replace("opencode/", "").replace("-free", ""), "opencode")
                    if self.health.is_provider_healthy(fallback_provider):
                        selected_model = fallback_model
                        selection_reason = "config_fallback"
                        break
                else:
                    # No healthy fallback - cascade through tiers
                    selected_model = None  # Will trigger cascading below
                    
                    # Need key and ip for cascading - get them now
                    provider = "opencode"
                    key = self.key_pool.get_best_key(provider)
                    ip = self.ip_pool.get_best_ip()
                    analysis = {"categories": [], "complexity": "unknown", "model_scores": {}}
                    preferred = self.prefs.get_preferred_models(agent_type, session_id)
                    avoided = self.prefs.get_avoided_models(agent_type)
        else:
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
            
            # STEP 4.5: Health check - filter out unhealthy models
            # Check provider health and exclude unhealthy models from selection
            model_provider_map = {
                "mimo-v2-pro": "opencode", "mimo-v2-omni": "opencode",
                "minimax-m2.5": "opencode", "qwen3.6-plus": "opencode",
                "qwen3-coder": "opencode", "kimi-k2.5": "opencode",
            }
            unhealthy_providers = []
            for provider_name in set(model_provider_map.values()):
                # Exclude unhealthy OR stalled providers
                if not self.health.is_provider_healthy(provider_name):
                    unhealthy_providers.append(provider_name)
                elif self.stall.is_provider_stalled(provider_name):
                    unhealthy_providers.append(provider_name)
            
            # If preferred model uses unhealthy/stalled provider, fall back to healthy one
            if selected_model:
                provider = model_provider_map.get(selected_model, "opencode")
                if provider in unhealthy_providers and selected_model == config_preferred_model:
                    # Config model unhealthy - try fallback
                    selected_model = None  # Will trigger fallbacks below
                    selection_reason = "provider_unhealthy"

            # STEP 5: MODEL CASCADING - Try models in order: cheap → medium → expensive
            # Define cascading tiers (each tier tried in order if previous fails)
            model_tiers = [
                # Tier 1: Fast/cheap (local or low-cost)
                ["minimax-m2.5", "qwen3-coder"],
                # Tier 2: Medium capability
                ["qwen3.6-plus", "kimi-k2.5"],
                # Tier 3: High capability (expensive)
                ["mimo-v2-pro", "mimo-v2-omni"],
            ]
            
            # Try cascading if no model selected yet or need fallback
            if not selected_model or selection_reason == "provider_unhealthy":
                for tier in model_tiers:
                    for model in tier:
                        # Skip if avoided or uses unhealthy provider
                        if model in avoided:
                            continue
                        provider = model_provider_map.get(model, "opencode")
                        if provider in unhealthy_providers:
                            continue
                        # Skip if not in preferred (unless no preferences at all)
                        if preferred and model not in preferred:
                            continue
                        selected_model = model
                        selection_reason = f"cascade_tier{model_tiers.index(tier)}"
                        break
                    if selected_model:
                        break

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

            # Get key and ip for route
            route = {
                "model": selected_model,
                "selection_reason": selection_reason,
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

        # Config preference path - get key and ip for route
        provider = "opencode"
        key = self.key_pool.get_best_key(provider)
        ip = self.ip_pool.get_best_ip()

        route = {
            "model": selected_model,
            "selection_reason": selection_reason,
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
            selected_model or "unknown",
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
        
        # Record to learning engine
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
            quality_score=0.1,  # Low quality for failures
            cost=0.0,
        )
        
        # Record to feedback loop (negative signal)
        request_id = route.get("session_id", "")
        self.feedback.submit(
            request_id=request_id,
            model=route["model"],
            provider=route["provider"],
            rating=1,  # Low rating for failure
            comment=f"Failed: {error_type}",
            was_helpful=False,
            response_time_ms=latency_ms,
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
            "health": self.health.get_status(),
            "learning": self.learning.get_stats(),
            "feedback": self.feedback.get_model_rankings()[:5],  # Top 5 models
            "cost": self.cost.get_all_stats(),
            "dashboard": dashboard.get_status(),
            "agent_preferences": {k: v for k, v in self.prefs._preferences.items()},
        }


# Global instance
intelligent_router = IntelligentRouter()
